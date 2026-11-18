import ctypes, json, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "design", "model", "verify"))
from models import compress16, cc_block, mono, pos2, IV, PARENT, ROOT, KEYED_HASH, CHUNK_START, CHUNK_END, M32
CC_CONST = [0x61707865, 0x3320646E, 0x79622D32, 0x6B206574]
ONLY = [int(k) for k in next((a[7:] for a in sys.argv[1:] if a.startswith("--only=")), "1,2,3,4,5").split(",")]
SIZES = [int(k) for k in next((a[8:] for a in sys.argv[1:] if a.startswith("--sizes=")), "").split(",") if k]
sys.argv = [a for a in sys.argv if not a.startswith("--")]
MAXL = int(sys.argv[1]) if len(sys.argv) > 1 else 22
g = ctypes.CDLL(os.path.join(HERE, "gpu_trees2.dll" if os.name == "nt" else "gpu_trees2.so"))
U32P = ctypes.POINTER(ctypes.c_uint32)
g.gpu_init.argtypes = [ctypes.c_char_p, ctypes.c_char_p]; g.gpu_name.restype = ctypes.c_char_p
g.tree2_run.argtypes = [ctypes.c_int] * 5 + [U32P, U32P]
g.tree2_bench.restype = ctypes.c_double; g.tree2_bench.argtypes = [ctypes.c_int] * 6 + [ctypes.POINTER(ctypes.c_double)]
MRC = json.load(open(os.path.join(HERE, "..", "..", "design", "model", "mono_constants.json")))
assert g.gpu_init(bytes(256), b"".join(v.to_bytes(4, "little") for row in MRC for v in row)) == 0
A = lambda v: (ctypes.c_uint32 * len(v))(*v)
NAME = {1: "BLAKE3 Merkle", 2: "BLAKE3-XOF GGM", 3: "ChaCha20 GGM", 4: "Monolith-31 Merkle", 5: "Poseidon2-M31 Merkle"}

def merkle_ref(kind, leaves):
    lv = [leaves[8 * i: 8 * i + 8] for i in range(len(leaves) // 8)]
    while len(lv) > 1:
        root = len(lv) == 2
        lv = [(pos2 if kind == 5 else mono)(lv[i] + lv[i + 1])[:8] if kind in (4, 5) else compress16(IV, lv[i] + lv[i + 1], 0, 64, PARENT | (ROOT if root else 0))[:8]
              for i in range(0, len(lv), 2)]
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
    print(s); lines.append(s)
SUF = "" if os.name == "nt" else "_linux"
out("# GPU tree baselines, tuned (RTX 3070, " + ("CUDA 12.6" if os.name == "nt" else "nvcc 11.8, driver 570") + ", sm_86)\n")
out(f"GPU: {g.gpu_name().decode()}. Variants: **per-level** = one launch per tree level, the original gpu_trees.cu kernels "
    "(Monolith with 64-bit constants); **fused+opt** = the top (Merkle) / head (GGM) levels with <= 256 nodes per tree in one launch in shared "
    "memory, Monolith MDS on 32-bit operands; **x8** = 8 independent trees per program. Kernel time with device-resident data "
    "(cudaEvent over the whole program); PCIe = copy of the program's leaves from pinned memory, one direction.\n")
out("## Correctness")
rng = random.Random(11); allok = True
for kind in ONLY:
    for opt, fuse in ((0, 0), (1, 1), (0, 1), (1, 0)):
        if kind != 4 and opt: continue
        for L in ((1, 6, 9) if kind in (4, 5) else (1, 6, 9, 10)):
            for T in (1, 3, 8):
                if kind in (4, 5) and L == 9 and T > 3: continue
                if kind in (1, 4, 5):
                    leaves = [rng.randrange(1 << 31) for _ in range(T * (8 << L))]
                    r = (ctypes.c_uint32 * (8 * T))()
                    e = g.tree2_run(kind, opt, fuse, L, T, A(leaves), r)
                    want = [w for t in range(T) for w in merkle_ref(kind, leaves[t * (8 << L):(t + 1) * (8 << L)])]
                else:
                    seeds = [rng.randrange(1 << 31) for _ in range(8 * T)]
                    r = (ctypes.c_uint32 * (T * (8 << L)))()
                    e = g.tree2_run(kind, opt, fuse, L, T, A(seeds), r)
                    want = [w for t in range(T) for w in ggm_ref(kind, seeds[8 * t:8 * t + 8], L)]
                ok = e == 0 and list(r) == want; allok &= ok
                if not ok: out(f"  FAIL {NAME[kind]} 2^{L} x{T} opt {opt} fuse {fuse} (err {e})")
out(f"- every variant (per-level / fused, 1 / 3 / 8 trees, Monolith with both MDS forms), trees of 2^1, 2^6, 2^9, 2^10 vs the Python models: {'OK' if allok else 'FAIL'}\n")

out("## ns per node and Mnodes/s")
out("")
out("| tree | size | per-level, 1 tree ns/node | fused+opt, 1 tree ns/node | fused+opt, x8 ns/node | x8 Mnodes/s | PCIe of x8 leaves ms |")
out("|---|---:|---:|---:|---:|---:|---:|")
REPS = {10: 400, 14: 100, 18: 20, 22: 4}
for L_ in SIZES: REPS.setdefault(L_, 400 if L_ <= 10 else 100 if L_ <= 14 else 20 if L_ <= 18 else 8 if L_ <= 21 else 4)
res = {}
for kind in ONLY:
    for L in (SIZES or [l for l in (10, 14, 18, 22) if l <= MAXL]):
        row = []
        for opt, fuse, T in ((0, 0, 1), (1, 1, 1), (1, 1, 8)):
            reps = max(1, REPS[L] // T)
            pc = ctypes.c_double(0)
            ns = min(g.tree2_bench(kind, opt, fuse, L, T, reps, ctypes.byref(pc)) for _ in range(3))
            row.append((ns, pc.value))
        res[(kind, L)] = row
        out(f"| {NAME[kind]} | 2^{L} | {row[0][0]:.3f} | {row[1][0]:.3f} | {row[2][0]:.3f} | {1e3 / row[2][0]:,.0f} | {row[2][1]:.2f} |")
jp = os.path.join(HERE, f"gpu_trees2{SUF}.json")
old = json.load(open(jp)) if os.path.exists(jp) else {}
old.update({f"{k[0]}_{k[1]}": v for k, v in res.items()}); json.dump(old, open(jp, "w"))
SUF += ("_s" + "_".join(map(str, SIZES))) if SIZES else ""
open(os.path.join(HERE, f"RESULTS_GPU_TREES2{SUF}.md" if ONLY == [1, 2, 3, 4, 5] else f"RESULTS_GPU_TREES2{SUF}_k{''.join(map(str, ONLY))}.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("ALL OK" if allok else "CHECK FAILED")
