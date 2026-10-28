"""run_cpu_trees.py - CPU baselines for the unit's four tree workloads (i7-12700K): correctness against the Python
models of dse/TOP/verify (the framings of compile_tree.py), then ns/node for 2^10..2^22 on 1 and 20 threads.
    python run_cpu_trees.py [max_log2]          -> RESULTS_CPU_TREES.md
Implementations
  BLAKE3 Merkle     official BLAKE3 C 1.8.2: blake3_hash_many on the parents of a level (AVX2, 8 parents per call)
  BLAKE3-XOF GGM    official BLAKE3 C 1.8.2: blake3_compress_xof per node (SSE4.1)  |  ours: 8-way SoA (AVX2)
  ChaCha20 GGM      ours: scalar block per node                                    |  ours: 8-way SoA (AVX2)
  Monolith-31       Plonky3 p3-monolith 0.8.0 (Rust, rayon)  |  ours: scalar C++  |  ours: 8-way SoA (AVX2)
"""
import ctypes, os, random, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "dse", "TOP", "verify"))
from models import compress16, cc_block, mono, pos2, IV, PARENT, ROOT, KEYED_HASH, CHUNK_START, CHUNK_END, M32
CC_CONST = [0x61707865, 0x3320646E, 0x79622D32, 0x6B206574]
ONLY = [int(k) for k in next((a[7:] for a in sys.argv[1:] if a.startswith("--only=")), "1,2,3,4,5").split(",")]
sys.argv = [a for a in sys.argv if not a.startswith("--")]
MAXL = int(sys.argv[1]) if len(sys.argv) > 1 else 22
THREADS = os.cpu_count() or 20

cpu = ctypes.CDLL(os.path.join(HERE, "cpu_trees.dll" if os.name == "nt" else "cpu_trees.so"))
p3 = ctypes.CDLL(os.path.join(HERE, "..", "p3mono", "p3mono.dll" if os.name == "nt" else "target/release/libp3mono.so"))
U32P = ctypes.POINTER(ctypes.c_uint32)
cpu.cpu_tree.restype = ctypes.c_double; cpu.cpu_tree.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, U32P, U32P]
cpu.cpu_init.argtypes = [ctypes.c_int]
p3.p3_mono_tree.restype = ctypes.c_double; p3.p3_mono_tree.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, U32P, U32P]
p3.p3_pos2_tree.restype = ctypes.c_double; p3.p3_pos2_tree.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, U32P, U32P]
A = lambda vals: (ctypes.c_uint32 * len(vals))(*vals)
NUL = ctypes.cast(None, U32P)

# ---------------- references ----------------
def merkle_ref(kind, leaves):
    lv = [leaves[8 * i: 8 * i + 8] for i in range(len(leaves) // 8)]
    while len(lv) > 1:
        root = len(lv) == 2
        nxt = []
        for i in range(0, len(lv), 2):
            l, r = lv[i], lv[i + 1]
            nxt.append((pos2 if kind == 5 else mono)(l + r)[:8] if kind in (4, 5) else compress16(IV, l + r, 0, 64, PARENT | (ROOT if root else 0))[:8])
        lv = nxt
    return lv[0]
def ggm_ref(kind, seed, depth):
    lv = [seed]
    for level in range(depth):
        nxt = []
        for idx, s in enumerate(lv):
            if kind == 3: o = cc_block(CC_CONST + s + [idx & M32, (idx >> 32) & M32, level, 0])
            else: o = compress16(s, [idx & M32, (idx >> 32) & M32, level] + [0] * 13, 0, 64, KEYED_HASH | CHUNK_START | CHUNK_END | ROOT)
            nxt += [o[:8], o[8:16]]
        lv = nxt
    return [w for s in lv for w in s]

lines = []
def out(s=""):
    print(s, flush=True); lines.append(s)

LINUX = os.name != "nt"                                     # Linux (dana336): build_cpu_linux.sh, results *_linux
SUF = "_linux" if LINUX else ""
CPU_NAME = next((l.split(":", 1)[1].strip() for l in open("/proc/cpuinfo") if l.startswith("model name")), "?") if LINUX else "i7-12700K, 12 cores / 20 threads"
out(f"# CPU tree baselines ({CPU_NAME}, {THREADS} threads)\n")
out("Same node framings as dse/TOP/verify/compile_tree.py and the GPU trees (gpu_trees.cu); leaves / seeds are 31-bit words.")
out(f"Official BLAKE3 C library 1.8.2: blake3_hash_many processes {cpu.cpu_b3_simd_degree()} inputs per call on this CPU.")
out(("Built with gcc / g++-13 -O3 -march=native and cargo 1.93 -C target-cpu=native (Plonky3)" if LINUX else
     "Built with clang 19 -O3 -march=native (C/C++) and rustc 1.95 -C target-cpu=native (Plonky3)") + "; timing excludes buffer allocation and input generation.\n")

# ---------------- checks ----------------
out("## Correctness")
cpu.cpu_init(1)
KAT_IN = list(range(16))
KAT = [609156607, 290107110, 1900746598, 1734707571, 2050994835, 1648553244, 1307647296, 1941164548, 1707113065, 1477714255, 1170160793, 93800695, 769879348, 375548503, 1989726444, 1349325635]
o = (ctypes.c_uint32 * 16)(); p3.p3_mono_perm(A(KAT_IN), o); ok_p3 = list(o) == KAT
o2 = (ctypes.c_uint32 * 16)(); cpu.cpu_mono_perm(A(KAT_IN), o2); ok_c = list(o2) == KAT
out(f"- Monolith-31 permutation of [0..15] = reference test vector (Plonky3 KAT): Plonky3 {'OK' if ok_p3 else 'FAIL'}, our C++ {'OK' if ok_c else 'FAIL'}, Python model {'OK' if mono(KAT_IN) == KAT else 'FAIL'}")
rng = random.Random(7); allok = ok_p3 and ok_c
IMPLS = {1: [(0, "official BLAKE3 C, hash_many")], 2: [(0, "official BLAKE3 C, compress_xof"), (1, "ours, 8-way SoA")],
         3: [(0, "ours, scalar"), (1, "ours, 8-way SoA"), (2, "ours, AVX2 intrinsics")], 4: [("p3", "Plonky3 p3-monolith 0.8.0"), (0, "ours, scalar"), (1, "ours, 8-way SoA")],
         5: [("p3p", "Plonky3 p3-mersenne-31 Poseidon2 0.8.0")]}
NAME = {1: "BLAKE3 Merkle", 2: "BLAKE3-XOF GGM", 3: "ChaCha20 GGM", 4: "Monolith-31 Merkle", 5: "Poseidon2-M31 Merkle"}
P3TREE = {"p3": p3.p3_mono_tree, "p3p": p3.p3_pos2_tree}
for T in (1, THREADS):
    cpu.cpu_init(T)
    for kind in [k for k in (1, 4, 5) if k in ONLY]:
        for L in (1, 6, 9):
            leaves = [rng.randrange(1 << 31) for _ in range(8 << L)]
            want = merkle_ref(kind, leaves)
            for impl, nm in IMPLS[kind]:
                r = (ctypes.c_uint32 * 8)()
                if impl in P3TREE: cpu.cpu_stop(); P3TREE[impl](L, 1, T, A(leaves), r); cpu.cpu_init(T)
                else: cpu.cpu_tree(kind, impl, L, 1, A(leaves), r)
                ok = list(r) == want; allok &= ok
                if not ok: out(f"  FAIL {NAME[kind]} 2^{L} {nm} threads {T}")
    for kind in [k for k in (2, 3) if k in ONLY]:
        for D in (1, 6, 9):
            seed = [rng.randrange(1 << 31) for _ in range(8)]
            want = ggm_ref(kind, seed, D)
            for impl, nm in IMPLS[kind]:
                r = (ctypes.c_uint32 * (8 << D))()
                cpu.cpu_tree(kind, impl, D, 1, A(seed), r)
                ok = list(r) == want; allok &= ok
                if not ok: out(f"  FAIL {NAME[kind]} depth {D} {nm} threads {T}")
out(f"- every implementation, Merkle roots of 2^1 / 2^6 / 2^9 leaves and all GGM leaves of depth 1 / 6 / 9, on 1 and {THREADS} threads, vs the Python models: {'OK' if allok else 'FAIL'}\n")

# ---------------- timing ----------------
out("## ns per node (lower is better) and Mnodes/s")
out("")
TL = [1, 16, THREADS]
out("| tree | size | implementation | 1 thread ns/node | 16 threads ns/node | %d threads ns/node | best Mnodes/s (threads) |" % THREADS)
out("|---|---:|---|---:|---:|---:|---:|")
REPS = {10: 400, 14: 40, 18: 4, 22: 1}
best = {}
JS = []
for kind in ONLY:
    for L in [l for l in (10, 14, 18, 22) if l <= MAXL]:
        for impl, nm in IMPLS[kind]:
            res = []
            for T in TL:
                reps = (max(1, REPS[L] // 4) if T == 1 else max(2, REPS[L])) if L >= 14 else REPS[L]
                if impl in P3TREE: cpu.cpu_stop()          # no C++ pool threads while rayon runs
                else: cpu.cpu_init(T)
                run = (lambda: P3TREE[impl](L, reps, T, NUL, NUL)) if impl in P3TREE else (lambda: cpu.cpu_tree(kind, impl, L, reps, NUL, NUL))
                run()                                     # warm-up (pages, pool, caches)
                res.append(min(run() for _ in range(5 if L < 22 else 3)))
            bi = min(range(len(TL)), key=lambda i: res[i])
            out(f"| {NAME[kind]} | 2^{L} | {nm} | {res[0]:.2f} | {res[1]:.3f} | {res[2]:.3f} | {1e3 / res[bi]:,.0f} ({TL[bi]}) |")
            JS.append({"kind": kind, "L": L, "impl": str(impl), "name": nm, "ns": dict(zip(map(str, TL), res)), "best_ns": res[bi], "best_threads": TL[bi]})
            res = [res[0], res[bi]]
            k = (kind, L)
            if k not in best or res[1] < best[k][0]: best[k] = (res[1], nm, res[0])
cpu.cpu_stop()
out("\n## Best CPU implementation per tree (best of 1 / 16 / %d threads)\n" % THREADS)
out("| tree | size | best implementation | ns/node | Mnodes/s | tree time us |")
out("|---|---:|---|---:|---:|---:|")
for (kind, L), (ns, nm, ns1) in sorted(best.items()):
    out(f"| {NAME[kind]} | 2^{L} | {nm} | {ns:.3f} | {1e3 / ns:,.0f} | {ns * ((1 << L) - 1) / 1e3:,.1f} |")
open(os.path.join(HERE, "..", f"RESULTS_CPU_TREES{SUF}.md" if ONLY == [1, 2, 3, 4, 5] else f"RESULTS_CPU_TREES{SUF}_k{''.join(map(str, ONLY))}.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
import json
jp = os.path.join(HERE, f"cpu_trees{SUF}.json"); old = json.load(open(jp)) if os.path.exists(jp) else {"threads": THREADS, "rows": []}
old["rows"] = [r for r in old["rows"] if r["kind"] not in ONLY] + JS; json.dump(old, open(jp, "w"))
print("ALL OK" if allok else "CHECK FAILED")
