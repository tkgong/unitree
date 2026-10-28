"""gen_tree_vectors.py - a depth-2 tree of every kind from the CPU baselines (merkle_baseline), as the expected values of the
Verilator check of the RTL/fsm tops (tb_tree.cpp):
  BLAKE3 Merkle   4 leaves -> root        official BLAKE3 C library (cpu_trees.dll, kind 1)
  Monolith Merkle 4 leaves -> root        Plonky3 p3-monolith (p3mono.dll) and the scalar C++ (cpu_trees.dll, kind 4)
  ChaCha20 GGM    seed -> 4 leaves        cpu_trees.dll kind 3
  BLAKE3-XOF GGM  seed -> 4 leaves        official blake3_compress_xof (cpu_trees.dll, kind 2)
Each is also checked against the Python models here. Output: vec_tree/tree.hex, 32-bit words one per line:
  leaves[32] seed[8] b3_root[8] mono_root[8] cc_leaves[32] b3ggm_leaves[32]"""
import ctypes, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, "..", "..", "..", "merkle_baseline")
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "dse", "TOP", "verify"))
from models import compress16, cc_block, mono, IV, PARENT, ROOT, KEYED_HASH, CHUNK_START, CHUNK_END, M32
CC_CONST = [0x61707865, 0x3320646E, 0x79622D32, 0x6B206574]
U32P = ctypes.POINTER(ctypes.c_uint32)
A = lambda vals: (ctypes.c_uint32 * len(vals))(*vals)
cpu = ctypes.CDLL(os.path.join(MB, "cpu", "cpu_trees.dll"))
p3 = ctypes.CDLL(os.path.join(MB, "p3mono", "p3mono.dll"))
cpu.cpu_tree.restype = ctypes.c_double; cpu.cpu_tree.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, U32P, U32P]
cpu.cpu_init.argtypes = [ctypes.c_int]; cpu.cpu_init(1)
p3.p3_mono_tree.restype = ctypes.c_double; p3.p3_mono_tree.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, U32P, U32P]

rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 7)
leaves = [rng.randrange(1 << 31) for _ in range(32)]
seed = [rng.randrange(1 << 31) for _ in range(8)]
L = [leaves[8 * i: 8 * i + 8] for i in range(4)]

r = A([0] * 8); cpu.cpu_tree(1, 0, 2, 1, A(leaves), r); b3_root = list(r)
r = A([0] * 8); p3.p3_mono_tree(2, 1, 1, A(leaves), r); mono_root = list(r)
r = A([0] * 8); cpu.cpu_tree(4, 0, 2, 1, A(leaves), r); mono_root_cpp = list(r)
r = A([0] * 32); cpu.cpu_tree(3, 0, 2, 1, A(seed), r); cc_leaves = list(r)
r = A([0] * 32); cpu.cpu_tree(2, 0, 2, 1, A(seed), r); b3g_leaves = list(r)

# Python models (the framings of compile_tree.py)
p = [compress16(IV, L[0] + L[1], 0, 64, PARENT)[:8], compress16(IV, L[2] + L[3], 0, 64, PARENT)[:8]]
assert compress16(IV, p[0] + p[1], 0, 64, PARENT | ROOT)[:8] == b3_root, "BLAKE3 Merkle: CPU library != Python model"
pm = [mono(L[0] + L[1])[:8], mono(L[2] + L[3])[:8]]
assert mono(pm[0] + pm[1])[:8] == mono_root == mono_root_cpp, "Monolith Merkle: Plonky3 / C++ / Python model differ"
c0 = cc_block(CC_CONST + seed + [0, 0, 0, 0]); cl = [c0[:8], c0[8:16]]
cl2 = []
for i, s in enumerate(cl):
    o = cc_block(CC_CONST + s + [i, 0, 1, 0]); cl2 += [o[:8], o[8:16]]
assert [w for s in cl2 for w in s] == cc_leaves, "ChaCha GGM: CPU != Python model"
g0 = compress16(seed, [0, 0, 0] + [0] * 13, 0, 64, KEYED_HASH | CHUNK_START | CHUNK_END | ROOT); gl = [g0[:8], g0[8:16]]
gl2 = []
for i, s in enumerate(gl):
    o = compress16(s, [i, 0, 1] + [0] * 13, 0, 64, KEYED_HASH | CHUNK_START | CHUNK_END | ROOT); gl2 += [o[:8], o[8:16]]
assert [w for s in gl2 for w in s] == b3g_leaves, "BLAKE3 GGM: CPU library != Python model"

os.makedirs(os.path.join(HERE, "vec_tree"), exist_ok=True)
words = leaves + seed + b3_root + mono_root + cc_leaves + b3g_leaves
open(os.path.join(HERE, "vec_tree", "tree.hex"), "w").write("".join(f"{w & M32:08x}\n" for w in words))
print(f"depth-2 trees from the CPU baselines: BLAKE3 Merkle root {b3_root[0]:08x}.., Monolith root (Plonky3 = C++) {mono_root[0]:08x}.., "
      f"ChaCha GGM leaves {cc_leaves[0]:08x}.., BLAKE3 GGM leaves {b3g_leaves[0]:08x}..; all equal to the Python models; {len(words)} words -> vec_tree/tree.hex")
