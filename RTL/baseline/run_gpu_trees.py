"""run_gpu_trees.py - GPU (CUDA) benchmark of the three-primitive tree workloads, level by level with device-resident data:
  GGM trees: BLAKE3 keyed-XOF, ChaCha20      Merkle trees: BLAKE3, Monolith-31
1. correctness of every GPU tree against the Python models (same framing as RTL/compiler/compile_tree.py)
2. GPU time per tree / ns per node / Mnodes/s for 2^10 .. 2^22 leaves
3. (--unit) the same trees compiled onto the HLS unit (compile_tree.py on dse/TOP/verify/ld_16.dll): cycles -> time
   at 1 GHz, GPU / one unit, units for 10x the GPU
Needs gpu_trees.dll (build_gpu_trees.sh).   usage: run_gpu_trees.py [--unit] [max log2 size, default 22]
"""
import ctypes, json, os, random, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "dse", "TOP", "verify"))
from models import *
HERE = os.path.dirname(os.path.abspath(__file__))            # (models.py exports its own HERE)
UNIT = "--unit" in sys.argv
MAXL = int([a for a in sys.argv[1:] if not a.startswith("--")][0]) if [a for a in sys.argv[1:] if not a.startswith("--")] else 22
gpu = ctypes.CDLL(os.path.join(HERE, "gpu_trees.dll"))
gpu.gpu_init.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
gpu.gpu_name.restype = ctypes.c_char_p
for f in ("bench_ggm", "bench_merkle"):
    getattr(gpu, f).restype = ctypes.c_double; getattr(gpu, f).argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
gpu.ggm_run.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p]
gpu.merkle_run.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p]
MRC = json.load(open(os.path.join(HERE, "..", "..", "dse", "TOP", "mono_constants.json")))
assert gpu.gpu_init(bytes(256), b"".join(v.to_bytes(4, "little") for row in MRC for v in row)) == 0
print("GPU:", gpu.gpu_name().decode())
CC_CONST = [0x61707865, 0x3320646e, 0x79622d32, 0x6b206574]
rnd = random.Random(3)
def words(b): return [int.from_bytes(b[4 * i:4 * i + 4], "little") for i in range(len(b) // 4)]
def wbytes(w): return b"".join(x.to_bytes(4, "little") for x in w)


def ggm_ref(p, seed, depth):
    level = [seed]
    for lv in range(depth):
        nxt = []
        for i, s in enumerate(level):
            if p == 1: o = compress16(s, [i & M32, i >> 32, lv] + [0] * 13, 0, 64, KEYED_HASH | CHUNK_START | CHUNK_END | ROOT)
            else: o = cc_block(CC_CONST + s + [i & M32, i >> 32, lv, 0])
            nxt += [o[:8], o[8:16]]
        level = nxt
    return level


def merkle_ref(p, leaves):
    level = leaves
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            l, r = level[i], level[i + 1]
            nxt.append(mono(l + r)[:8] if p == 4 else compress16(IV, l + r, 0, 64, PARENT | (ROOT if len(level) == 2 else 0))[:8])
        level = nxt
    return level[0]


ok_all = True
for p, name in ((1, "BLAKE3 keyed-XOF GGM"), (2, "ChaCha20 GGM")):
    seed = [rnd.getrandbits(32) for _ in range(8)]
    out = ctypes.create_string_buffer(64 * 32)
    ok = gpu.ggm_run(p, 6, wbytes(seed), out) == 0
    got = [words(out.raw[32 * i:32 * i + 32]) for i in range(64)]
    ok &= got == ggm_ref(p, seed, 6)
    ok_all &= ok; print(f"  {name} depth 6 (64 leaves) vs Python model: {'OK' if ok else 'FAIL'}")
for p, name in ((1, "BLAKE3 Merkle"), (4, "Monolith-31 Merkle")):
    leaves = [[rnd.randrange(P) for _ in range(8)] for _ in range(64)]
    out = ctypes.create_string_buffer(32)
    ok = gpu.merkle_run(p, 6, b"".join(wbytes(l) for l in leaves), out) == 0
    ok &= words(out.raw) == merkle_ref(p, leaves)
    ok_all &= ok; print(f"  {name} 2^6 leaves, root vs Python model: {'OK' if ok else 'FAIL'}")

WORK = [("BLAKE3-XOF GGM", "ggm", 1, "ggm blake3"), ("ChaCha20 GGM", "ggm", 2, "ggm chacha"),
        ("BLAKE3 Merkle", "merkle", 1, "merkle blake3"), ("Monolith-31 Merkle", "merkle", 4, "merkle mono")]
SIZES = [s for s in (10, 14, 18, 22) if s <= MAXL]
print(f"\n| tree | size | nodes | GPU us / tree | GPU ns / node | GPU Mnodes/s |")
print("|---|---:|---:|---:|---:|---:|")
gres = {}
for name, kind, p, _ in WORK:
    for s in SIZES:
        reps = 50 if s <= 14 else (10 if s <= 18 else 3)
        ns = (gpu.bench_ggm if kind == "ggm" else gpu.bench_merkle)(p, s, reps)
        nodes = (1 << s) - 1
        gres[(name, s)] = ns * nodes / 1e3
        print(f"| {name} | 2^{s} | {nodes:,} | {ns * nodes / 1e3:,.1f} | {ns:.3f} | {1e3 / ns:,.0f} |")

if UNIT:
    PY = sys.executable
    DLL = os.path.join(HERE, "..", "..", "dse", "TOP", "verify", "ld_16.dll")
    CT = os.path.join(HERE, "..", "compiler", "compile_tree.py")
    USZ = {"ggm": [10, 14, 18, 22], "merkle": [10, 14, 18, 22]}          # 18, 22: scaled from the 2^14 (2^12 Monolith) schedule, 97-99% utilisation
    print(f"\n| tree | size | unit cycles (compiled schedule) | unit us @ 1 GHz | GPU us | one unit vs GPU (GPU time / unit time) | units for 10x GPU |")
    print("|---|---:|---:|---:|---:|---:|---:|")
    for name, kind, p, req in WORK:
        for s in USZ[kind]:
            if s not in SIZES: continue
            s_run = min(s, 12 if (kind == "merkle" and p == 4) else 14)
            out = subprocess.run([PY, CT, DLL] + req.split() + [str(s_run)], capture_output=True, text=True).stdout
            m = re.search(r"cycles\s+([\d,]+)", out); okm = re.search(r"reference: (OK|FAIL)", out)
            if not m: print(f"| {name} | 2^{s} | (compile_tree failed) |"); continue
            cyc = int(m.group(1).replace(",", ""))
            if s_run != s: cyc = cyc * ((1 << s) - 1) // ((1 << s_run) - 1)      # scaled from the largest simulated size (streaming regime)
            u_us = cyc / 1e3; g_us = gres[(name, s)]
            print(f"| {name} | 2^{s} | {cyc:,}{' (scaled from 2^%d)' % s_run if s_run != s else ''} {okm.group(1) if okm else ''} | {u_us:,.1f} | {g_us:,.1f} | {g_us / u_us:.2f}x | {max(1, -(-10 * u_us // g_us)) if g_us > 0 else 0:,.0f} |")
print("\nALL OK" if ok_all else "\nSOME CHECKS FAILED")
