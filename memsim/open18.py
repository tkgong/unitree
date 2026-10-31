"""open18.py - opening q leaves of a 2^18 tree on the CPU, the GPU and the unit: time and energy (dana336).

One opened set per tree, the same on the three platforms: Merkle = the authentication paths of q random leaves (the leaves,
and the sibling of every path node that is not itself on an opened path), GGM = the co-path seeds of q punctured leaves
(the sibling at every level of every path, minus path nodes). Every platform outputs the merged set, 32 B per node, in
(level, index) order; the GPU's output is checked against the CPU's stored tree node by node.
  CPU   cpu_trees.so: the tree stored with every level (16.8 MB), 16 threads gather the set (cpu_open); 8 trees one after
        the other = 8 cores' worth of work. RAPL is root-only on dana336: no CPU energy.
  GPU   gpu_trees2.so: 8 trees stored with every level (134 MB, device resident), one gather kernel over the 8 sets
        (open_bench); board power from nvidia-smi during a >= 5 s loop of the kernel, idle measured before.
  unit  one core, 2 GDDR6 channels, the adaptive store policy (memsim/results/policy18.md): ARX K = 4 (the 4 levels above
        the leaves are not stored; ARX Merkle K = 5), Monolith K = 0 (everything stored).
          (a) the stored nodes of the set are read and the opened set is written out as the proof, one mixed stream through
              the Ramulator2 GDDR6 model (hbm.batch, block layout, 2 channels, cycle level);
          (b) K > 0: the unstored nodes are recomputed by a compiled program on the unit model, cycle by cycle, bit-exact:
              Merkle: the 2^K-leaf subtrees that hold the needed siblings, as one Merkle program over those subtrees
              (leafmap=: the leaves read from their scattered DRAM addresses through the same GDDR6 model; the tree above
              the subtrees is computed too: the padding to a power of two and that top are counted as overhead);
              GGM: the K expansions per path from the stored level-(K + 1) path node, as independent depth-1 GGM trees at
              the unit's throughput (the chain's K - 1 dependent latencies are added once).
          Cycles = (a) + (b), run one after the other (no overlap claimed). Energy = idle power x (a) + the program's
          measured power (benchmark/power/power.md, shared unit) x (b); the DRAM's energy is not in it (the GPU's board
          power includes its GDDR6).
  Speedup: 8 cores open 8 trees at once, so the unit's time for 8 trees = one core's cycles at 1 GHz, against the GPU's
  one call over 8 trees and the CPU's 8 trees in sequence.
    cd memsim && python3 open18.py [q,q,..] [reps=20]        -> results/open18.md, results/open18.json
"""
import ctypes, json, os, random, subprocess, sys, threading, time
from array import array
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
import hbm
SZ, T, CH = 18, 8, 2
QS = [int(x) for x in sys.argv[1].split(",")] if len(sys.argv) > 1 and sys.argv[1][0].isdigit() else [16, 64, 256, 1024, 4096, 16384]
REPS = int(next((a[5:] for a in sys.argv[1:] if a.startswith("reps=")), "20"))
CT = os.path.join(REPO, "RTL", "compiler", "compile_tree.py"); TOP = os.path.join(REPO, "dse", "TOP"); SO = "verify/lz3s_16.so"
OUT = os.path.join(HERE, "results"); os.makedirs(OUT, exist_ok=True)
# (request, primitive, kind of cpu_trees / gpu_trees2, cpu impl, K, measured power of the shared unit on this program, W)
PROGS = [("merkle", "blake3", 1, 0, 5, 3.66), ("ggm", "chacha", 3, 2, 4, 3.49), ("ggm", "blake3", 2, 2, 4, 3.42), ("merkle", "mono", 4, 1, 0, 3.77)]
if "rigid" in sys.argv[1:]:                                                           # the ablation's rigid store policies: ARX's K on Monolith, keep-everything on ARX
    PROGS = [("merkle", "mono", 4, 1, 4, 3.77), ("merkle", "blake3", 1, 0, 0, 3.66), ("ggm", "chacha", 3, 2, 0, 3.49), ("ggm", "blake3", 2, 2, 0, 3.42)]
SUF = "_rigid" if "rigid" in sys.argv[1:] else ""
NAME = {1: "BLAKE3 Merkle", 2: "BLAKE3 GGM", 3: "ChaCha20 GGM", 4: "Monolith-31 Merkle"}
IDLE_W = {}                                                                           # unit idle power (syn/work_t10/pw_idle.txt)
for ln in open(os.path.join(REPO, "RTL", "syn", "work_t10", "pw_idle.txt")) if os.path.exists(os.path.join(REPO, "RTL", "syn", "work_t10", "pw_idle.txt")) else []:
    if " idle: " in ln: IDLE_W[ln.split()[0]] = float(ln.split("= ")[1].split()[0])
P_IDLE = IDLE_W.get("shared", 0.0)

def opened(req, qs, K):
    """-> (all opened nodes (the proof), stored nodes to read, unstored (recomputed) nodes), (level above the leaves, index)"""
    path = {(l, i >> l) for i in qs for l in range(SZ + 1)}
    need = {(l, (i >> l) ^ 1) for i in qs for l in range(SZ)} - path
    if req == "merkle": need |= {(0, i) for i in qs}
    low = {(l, j) for (l, j) in need if 1 <= l <= K}
    return need, need - low, low

ROWB, HBLK = 1024, 4                                                                  # the block layout of compile_tree.py (stored nodes)
def blocks_in_band(b): top = 1 + (b + 1) * HBLK; return (1 << (SZ - top)) if top <= SZ else 1
BANDB = [0]
for b in range((SZ - 1) // HBLK + 1): BANDB.append(BANDB[-1] + blocks_in_band(b) * ROWB)
def addr(l, j):
    if l == 0: return j * 32
    base = -(-(1 << SZ) * 32 // ROWB) * ROWB
    b = (l - 1) // HBLK; top = 1 + (b + 1) * HBLK; d = top - l; anc = j >> d if top <= SZ else 0
    return base + BANDB[b] + anc * ROWB + ((1 << d) - 2 + (j - (anc << d))) * 32
PROOF = 512 << 20                                                                     # the proof is written here, sequentially

def unit_open(req, prim, K, qs, tag):
    """-> dict: the unit's cycles. Merkle: one compiled program (compile_tree.py open: stored siblings read, unstored ones
    recomputed, every path hashed to the committed root, the proof written; closed loop on the GDDR6 model). GGM: (a) the
    co-path stream, (b) the recompute of the K unstored levels."""
    need, stored, low = opened(req, qs, K)
    if req == "merkle":
        cmd = ["python3", CT, SO, "open", prim, str(SZ), f"q={len(qs)}", "sram=32", f"gddr={CH}", f"store=k{K}" if K else "store=all", "audit"]
        out = subprocess.run(cmd, cwd=TOP, capture_output=True, text=True).stdout
        cyc = next((int(ln.split()[1].replace(",", "")) for ln in out.splitlines() if ln.startswith("  cycles")), None)
        ut = next((ln for ln in out.splitlines() if ln.startswith("  engine utilization")), "")
        util = [float(x.split(":")[1]) for x in ut.split("(")[0].replace("  engine utilization  ", "").split(",") if ":" in x]
        assert cyc is not None and "reference: OK" in out and "audit               OK" in out, out[-3000:]
        comp = int(next(ln for ln in out.splitlines() if ln.startswith("request:")).split("compressions")[0].split(",")[-1].strip().replace(",", ""))
        return {"opened": len(need), "read": len(need) - len(low) + (0 if K == 0 else sum(1 for _ in low)), "written": len(need), "recomputed": len(low), "cyc_stream": 0,
                "act": 0, "row_hit": 0, "lat_avg": 0, "cyc_prog": cyc, "prog_nodes": comp, "prog_overhead": 0.0, "prog": " ".join(cmd[3:]), "util": sum(util) / len(util) if util else 0}
    exp = set()
    if req == "ggm" and low:                                                          # the path nodes expanded: lam 2 .. K + 1 of the paths with unstored siblings
        for (l, j) in low:
            for m in range(l + 1, K + 2): exp.add((m, j >> (m - l)))
        stored |= {(K + 1, j) for (m, j) in exp if m == K + 1}                       # the stored level-(K + 1) path nodes are read
    rd = sorted(stored, key=lambda x: addr(*x)); wr = sorted(need)
    addrs, flags = [], []
    G = 512; wf = 0                                                                   # the proof is staged in the SRAM (16 KB) and written in bursts of G nodes:
    for k in range(len(rd)):                                                          # fewer read / write turnarounds than one write per read (q = 4096 Monolith:
        addrs.append(addr(*rd[k])); flags.append(False)                               # 77,105 -> 58,083 cycles; reads alone 36,491)
        if (k + 1) % G == 0:
            for w in range(wf, min(wf + G, len(wr))): addrs.append(PROOF + w * 32); flags.append(True)
            wf = min(wf + G, len(wr))
    for w in range(wf, len(wr)): addrs.append(PROOF + w * 32); flags.append(True)
    cyc_a, st, lat = hbm.batch(addrs, channels=CH, mapper="RoBaRaCoCh", write=flags, port=CH, nbl=2, kind="gddr")
    r = {"opened": len(need), "read": len(rd), "written": len(wr), "recomputed": len(low), "cyc_stream": cyc_a,
         "act": st["ACT"], "row_hit": st["row_hit"], "lat_avg": (sum(lat) / len(lat)) if lat else 0, "cyc_prog": 0, "prog_nodes": 0, "prog_overhead": 0.0, "prog": "", "util": 1.0}
    if not low: return r
    n = len(exp)
    cmd = ["python3", CT, SO, "ggm", prim, "1", f"x{n}"]
    r["prog_nodes"] = n; r["prog_overhead"] = 0.0
    r["prog"] = " ".join(cmd[2:])
    out = subprocess.run(cmd, cwd=TOP, capture_output=True, text=True).stdout
    cyc = next((int(ln.split()[1].replace(",", "")) for ln in out.splitlines() if ln.startswith("  cycles")), None)
    assert cyc is not None and "reference: OK" in out, out[-2000:]
    r["cyc_prog"] = cyc + (K - 1) * 98
    return r

def path_lists(sets_leaves, T):
    """-> (leaf store offsets, n_l[0..SZ], src_all) for the GPU's level-synchronous path hashing over T trees: level l holds
    the distinct path nodes (tree-major); a source is a computed node's position in level l-1, or a stored sibling (bit 63)."""
    leaf, n_l, src = [], [0] * (SZ + 1), []
    cur = []                                                                          # (tree, idx) of level l-1, sorted; positions = list order
    for t, qs in enumerate(sets_leaves):
        for i in sorted(set(qs)): cur.append((t, i)); leaf.append(gpu.open_off(0) + (t << SZ) + i)
    n_l[0] = len(cur)
    for l in range(1, SZ + 1):
        up = []
        for (t, j) in cur:
            if not up or up[-1] != (t, j >> 1): up.append((t, j >> 1))
        pos = {x: p for p, x in enumerate(cur)}
        for (t, j) in up:
            for c in (0, 1):
                ch = (t, 2 * j + c)
                src.append(pos[ch] if ch in pos else ((1 << 63) | (gpu.open_off(l - 1) + (t << (SZ - l + 1)) + 2 * j + c)))
        n_l[l] = len(up); cur = up
    return leaf, n_l, src

class GpuPower:                                                                       # nvidia-smi sampler (RTL/baseline/run_energy.py)
    def __init__(self):
        self.s = []; self.p = subprocess.Popen(["nvidia-smi", "--query-gpu=power.draw.instant", "--format=csv,noheader,nounits", "-lms", "20"], stdout=subprocess.PIPE, text=True)
        threading.Thread(target=self.rd, daemon=True).start()
    def rd(self):
        for line in self.p.stdout:
            try: self.s.append((time.time(), float(line.strip())))
            except ValueError: pass
    def mean(self, t0, t1):
        v = [w for t, w in self.s if t0 <= t <= t1]; return sum(v) / len(v), len(v)

U32P = ctypes.POINTER(ctypes.c_uint32)
cpu = ctypes.CDLL(os.path.join(REPO, "RTL", "baseline", "cpu", "cpu_trees.so"))
cpu.cpu_store_build.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, U32P]
cpu.cpu_store_node.restype = U32P; cpu.cpu_store_node.argtypes = [ctypes.c_int, ctypes.c_uint64]
cpu.cpu_open.restype = ctypes.c_double; cpu.cpu_open.argtypes = [ctypes.c_int, ctypes.c_size_t, U32P, ctypes.POINTER(ctypes.c_uint64), U32P]
gpu = ctypes.CDLL(os.path.join(REPO, "RTL", "baseline", "gpu_trees2.so"))
gpu.gpu_init.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
MRC = json.load(open(os.path.join(TOP, "mono_constants.json")))                       # the Monolith round constants into the GPU's constant memory
assert gpu.gpu_init(bytes(256), b"".join(v.to_bytes(4, "little") for row in MRC for v in row)) == 0
gpu.open_build.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, U32P]
gpu.open_off.restype = ctypes.c_uint64; gpu.open_off.argtypes = [ctypes.c_int]
gpu.open_bench.restype = ctypes.c_double; gpu.open_bench.argtypes = [ctypes.c_size_t, ctypes.POINTER(ctypes.c_uint64), ctypes.c_int, U32P]
U64P = ctypes.POINTER(ctypes.c_uint64)
gpu.open_paths_build.argtypes = [ctypes.c_int, ctypes.c_size_t, U64P, U64P, U64P]
gpu.open_paths_bench.restype = ctypes.c_double; gpu.open_paths_bench.argtypes = [ctypes.c_int, ctypes.c_int, U32P]
cpu.cpu_open_paths.restype = ctypes.c_double; cpu.cpu_open_paths.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, U64P, U32P, ctypes.c_int]
def u64(a): return (ctypes.c_uint64 * len(a)).from_buffer(a)
def u32(a): return (ctypes.c_uint32 * len(a)).from_buffer(a)
THREADS = os.cpu_count() or 16
cpu.cpu_init(THREADS)
pw = GpuPower(); time.sleep(3.0); t0 = time.time(); time.sleep(3.0); GPU_IDLE, _ = pw.mean(t0, time.time())
print(f"GPU idle {GPU_IDLE:.1f} W; unit idle {P_IDLE:.3f} W (vectorless, no data toggling; 0 = pw_idle.txt missing)")

rows = []
for (req, prim, kind, impl, K, PW) in PROGS:
    rng = random.Random(0x5EED ^ kind)
    n = 1 << SZ
    merkle = req == "merkle"
    ins = [array("I", (rng.getrandbits(31) for _ in range(n * 8 if merkle else 8))) for t in range(T)]   # the trees' inputs
    allin = array("I"); [allin.extend(x) for x in ins]
    assert gpu.open_build(kind, SZ, T, u32(allin)) == 0, "GPU build"
    time.sleep(2.0); ti0 = time.time(); time.sleep(3.0); GPU_IDLE, _ = pw.mean(ti0, time.time())   # the idle power right before this program's measurements (the GPU's idle state drifts)
    for q in QS:
        qsets = [sorted(random.Random(7 + 1000 * t + q).sample(range(n), q)) for t in range(T)]
        sets = [sorted(opened(req, qs, K)[0]) for qs in qsets]
        # ---- unit: tree 0's set (the trees are statistically identical) ----
        u = unit_open(req, prim, K, qsets[0], f"{req}_{prim}_q{q}")
        u_cyc = u["cyc_stream"] + u["cyc_prog"]
        u_nj = P_IDLE * u["cyc_stream"] + (P_IDLE + (PW - P_IDLE) * u["util"]) * u["cyc_prog"]   # W x ns = nJ; the program's power scaled by its engine utilization
        # ---- GPU: the 8 sets in one gather (the proof), then (Merkle) the paths hashed to the roots, level by level ----
        offs = array("Q")
        for t, s in enumerate(sets):
            offs.extend(gpu.open_off(l) + (t << (SZ - l)) + j for (l, j) in s)
        ntot = len(offs); gout = array("I", bytes(ntot * 32))
        g_ns = gpu.open_bench(ntot, u64(offs), REPS, u32(gout)); assert g_ns > 0, "GPU gather"
        reps_e = max(REPS, int(5e9 / g_ns)); te0 = time.time(); gpu.open_bench(ntot, u64(offs), reps_e, None); te1 = time.time()
        g_w, _ = pw.mean(te0, te1); g_j = (g_w - GPU_IDLE) * (te1 - te0) / reps_e; g_jb = g_w * (te1 - te0) / reps_e
        g_ns_paths = 0.0; groots = None
        if merkle:
            leaf, n_l, src = path_lists(qsets, T)
            la, na, sa = array("Q", leaf), array("Q", n_l), array("Q", src)
            assert gpu.open_paths_build(SZ, len(la), u64(la), u64(na), u64(sa)) == 0, "GPU paths build"
            groots = array("I", bytes(T * 32))
            g_ns_paths = gpu.open_paths_bench(kind, REPS, u32(groots)); assert g_ns_paths > 0, "GPU paths"
            reps_p = max(REPS, int(5e9 / g_ns_paths)); tp0 = time.time(); gpu.open_paths_bench(kind, reps_p, None); tp1 = time.time()
            g_wp, _ = pw.mean(tp0, tp1); g_j += (g_wp - GPU_IDLE) * (tp1 - tp0) / reps_p; g_jb += g_wp * (tp1 - tp0) / reps_p
        g_tot = g_ns + g_ns_paths; g_uj_tree = g_j / T * 1e6; g_uj_board = g_jb / T * 1e6
        # ---- CPU: tree by tree, all threads: the gather, then (Merkle) the paths; the GPU's gather and roots checked against the CPU's stored tree ----
        c_ns = c_ns_paths = 0.0; bad = 0; k0 = 0
        for t in range(T):
            cpu.cpu_store_build(kind, impl, SZ, u32(ins[t]))
            s = sets[t]; lv = array("I", (l for (l, j) in s)); ix = array("Q", (j for (l, j) in s)); cout = array("I", bytes(len(s) * 32))
            c_ns += cpu.cpu_open(REPS, len(s), u32(lv), u64(ix), u32(cout))
            for k, (l, j) in enumerate(s):
                node = cpu.cpu_store_node(l, j)
                if gout[(k0 + k) * 8:(k0 + k + 1) * 8] != array("I", node[:8]) or cout[k * 8:(k + 1) * 8] != array("I", node[:8]): bad += 1
            k0 += len(s)
            if merkle:
                ql = array("Q", qsets[t]); croot = array("I", bytes(32))
                c_ns_paths += cpu.cpu_open_paths(kind, impl, SZ, q, u64(ql), u32(croot), REPS)
                root = array("I", cpu.cpu_store_node(SZ, 0)[:8])
                if croot != root or groots[t * 8:(t + 1) * 8] != root: bad += 1000
        c_tot = c_ns + c_ns_paths
        row = {"program": NAME[kind], "q": q, "K": K, "opened_per_tree": len(sets[0]), **u, "unit_cycles_8_trees": u_cyc, "unit_nJ_per_tree": u_nj,
               "gpu_ns_gather": g_ns, "gpu_ns_paths": g_ns_paths, "gpu_ns_8_trees": g_tot, "gpu_uJ_per_tree_above_idle": g_uj_tree, "gpu_uJ_per_tree_board": g_uj_board,
               "cpu_ns_gather": c_ns, "cpu_ns_paths": c_ns_paths, "cpu_ns_8_trees": c_tot, "cpu_threads": THREADS,
               "speedup_vs_gpu": g_tot / u_cyc, "speedup_vs_cpu": c_tot / u_cyc, "energy_gpu_above_idle_over_unit": (g_uj_tree * 1e3) / u_nj if u_nj else 0, "check_bad": bad}
        rows.append(row)
        print(f"{NAME[kind]:19} q={q:6} opened {len(sets[0]):6}/tree: unit {u['cyc_stream']:>7,} + {u['cyc_prog']:>8,} = {u_cyc:>8,} cyc ({u_nj / 1e3:7.1f} uJ/tree); "
              f"GPU {g_ns / 1e3:7.1f} + {g_ns_paths / 1e3:7.1f} = {g_tot / 1e3:8.1f} us/8 trees ({g_uj_tree:7.1f} uJ/tree above idle); CPU {c_ns / 1e3:7.1f} + {c_ns_paths / 1e3:8.1f} us/8 trees; "
              f"vs GPU {g_tot / u_cyc:5.2f}x, vs CPU {c_tot / u_cyc:6.1f}x; check {'OK' if bad == 0 else f'{bad} BAD'}", flush=True)
json.dump(rows, open(os.path.join(OUT, f"open18{SUF}.json"), "w"), indent=1)
L = [f"# Opening q leaves of a 2^18 tree: CPU / GPU / unit (dana336, {time.strftime('%Y-%m-%d')})", "",
     f"See the docstring of `memsim/open18.py` for the method. Unit: one core per tree, 2 GDDR6 channels, 1 GHz, adaptive K (ARX Merkle 5, ARX GGM 4, Monolith 0); unit idle power {P_IDLE:.3f} W "
     f"(vectorless, no data toggling), program power from `power.md`; the DRAM's energy is not in the unit's number. GPU: RTX 3070, 8 trees per call, idle {GPU_IDLE:.1f} W. CPU: i7-10700K, {THREADS} threads, 8 trees in sequence; no energy (RAPL root-only).", "",
     "| program | q | opened nodes / tree | recomputed | unit cycles: GGM stream + program / Merkle open program (engine utilization) | unit us (8 trees) | unit uJ / tree | GPU us gather + paths (8 trees) | GPU uJ / tree above idle (board) | CPU us gather + paths (8 trees) | vs GPU | vs CPU | energy vs GPU above idle | check |",
     "|---|---:|---:|---:|---|---:|---:|---|---:|---|---:|---:|---:|---|"]
for r in rows:
    L.append(f"| {r['program']} | {r['q']:,} | {r['opened_per_tree']:,} | {r['recomputed']:,} | " + (f"{r['cyc_stream']:,} + {r['cyc_prog']:,}" if r['cyc_stream'] else f"{r['cyc_prog']:,} ({100 * r['util']:.0f}%)") +
             f" | {r['unit_cycles_8_trees'] / 1e3:.1f} | {r['unit_nJ_per_tree'] / 1e3:.1f} | {r['gpu_ns_gather'] / 1e3:.1f} + {r['gpu_ns_paths'] / 1e3:.1f} = {r['gpu_ns_8_trees'] / 1e3:.1f} | {r['gpu_uJ_per_tree_above_idle']:.1f} ({r['gpu_uJ_per_tree_board']:.1f}) | {r['cpu_ns_gather'] / 1e3:.1f} + {r['cpu_ns_paths'] / 1e3:.1f} = {r['cpu_ns_8_trees'] / 1e3:.1f} | {r['speedup_vs_gpu']:.2f}x | {r['speedup_vs_cpu']:.1f}x | {r['energy_gpu_above_idle_over_unit']:.1f}x | {'OK' if r['check_bad'] == 0 else 'BAD'} |")
open(os.path.join(OUT, f"open18{SUF}.md"), "w").write("\n".join(L) + "\n")
cpu.cpu_stop()
