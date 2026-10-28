"""build_prog.py - the programs and the expected values of one accelerator run (RTL/fsm/accel_top, tb_accel.cpp):
    python build_prog.py merkle blake3|mono <SZ> <TK>      python build_prog.py ggm chacha|blake3 <SZ> <TK>
Compiles the tile / subtree program (compile_tree.py ... hw=, Merkle with noroot) and the top program, writes
prog_<req>_<prim>_<SZ>_<TK>/{tile,top}/ and vec.hex: the leaves (Merkle, 2^SZ x 8 words) or the seed, and the expected
root (Merkle, from the CPU baseline: BLAKE3 C library / Plonky3 Monolith) or the 2^SZ leaves (GGM, cpu_trees.dll)."""
import ctypes, os, random, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
TOP = os.path.join(HERE, "..", "..", "..", "dse", "TOP"); MB = os.path.join(HERE, "..", "..", "..", "merkle_baseline")
sys.path.insert(0, os.path.join(TOP, "verify"))
from models import M32
PY = sys.executable
req, prim, SZ, TK = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
name = f"prog_{req}_{prim}_{SZ}_{TK}"; out = os.path.join(HERE, name); os.makedirs(out, exist_ok=True)
DLL = os.path.join(TOP, "verify", "lz3_16.dll")
def compile_(depth, sub, extra):
    d = os.path.join(out, sub)
    r = subprocess.run([PY, "-X", "utf8", os.path.join(TOP, "verify", "compile_tree.py"), DLL, req, prim, str(depth), f"hw={d}"] + extra,
                       capture_output=True, text=True, cwd=os.path.join(TOP, "verify"))
    line = [l for l in r.stdout.splitlines() if "hardware program" in l or "check:" in l]
    assert any("OK" in l for l in line), r.stdout[-2000:] + r.stderr[-2000:]
    print(f"  {sub}: " + line[0].split(": ", 1)[1])
    return d
compile_(TK, "tile", ["noroot"] if req == "merkle" else [])
compile_(SZ - TK, "top", [])
# the data and the CPU expectation
U32P = ctypes.POINTER(ctypes.c_uint32); A = lambda v: (ctypes.c_uint32 * len(v))(*v)
cpu = ctypes.CDLL(os.path.join(MB, "cpu", "cpu_trees.dll")); cpu.cpu_init.argtypes = [ctypes.c_int]; cpu.cpu_init(1)
cpu.cpu_tree.restype = ctypes.c_double; cpu.cpu_tree.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, U32P, U32P]
rng = random.Random(11)
if req == "merkle":
    leaves = [rng.randrange(1 << 31) for _ in range(8 << SZ)]
    if prim == "blake3":
        r_ = A([0] * 8); cpu.cpu_tree(1, 0, SZ, 1, A(leaves), r_); exp = list(r_); src = "official BLAKE3 C library"
    else:
        p3 = ctypes.CDLL(os.path.join(MB, "p3mono", "p3mono.dll"))
        p3.p3_mono_tree.restype = ctypes.c_double; p3.p3_mono_tree.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, U32P, U32P]
        r_ = A([0] * 8); p3.p3_mono_tree(SZ, 1, 1, A(leaves), r_); exp = list(r_); src = "Plonky3 p3-monolith"
    data = leaves
else:
    seed = [rng.randrange(1 << 31) for _ in range(8)]
    r_ = A([0] * (8 << SZ)); cpu.cpu_tree(3 if prim == "chacha" else 2, 0, SZ, 1, A(seed), r_); exp = list(r_)
    src = "cpu_trees.dll " + ("ChaCha20 scalar" if prim == "chacha" else "blake3_compress_xof")
    data = seed
with open(os.path.join(out, "vec.hex"), "w") as f:
    for w in data + exp: f.write(f"{w & M32:08x}\n")
with open(os.path.join(out, "meta.txt"), "w") as f:
    f.write(f"req {req}\nprim {prim}\nsz {SZ}\ntk {TK}\nndata {len(data)}\nnexp {len(exp)}\nsource {src}\n")
    for sub in ("tile", "top"):
        m = dict(l.split(" ", 1) for l in open(os.path.join(out, sub, "meta.txt")) if " " in l)
        f.write(f"{sub}_cycles {m['cycles'].strip()}\n")
print(f"{name}: expected from {src}; {len(data)} data words, {len(exp)} expected words")
