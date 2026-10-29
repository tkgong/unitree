"""run_gpu_axn.py - GPU (CUDA) throughput of the three-primitive unit's node functions: ChaCha20 block (GGM PRG,
one block = two 32-byte children), BLAKE3 Merkle parent node, BLAKE3 keyed-XOF GGM node (64-byte output),
Monolith-31 Merkle node; the BLAKE3 kernels are checked against a Python BLAKE3 model (official BLAKE3('') KAT).
Needs gpu_prims.dll (build_gpu.sh).  usage: run_gpu_axn.py [log2 nodes]
"""
import ctypes, json, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
LOG2N = int(sys.argv[1]) if len(sys.argv) > 1 else 22
gpu = ctypes.CDLL(os.path.join(HERE, "gpu_prims.dll"))
gpu.gpu_init.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
gpu.gpu_name.restype = ctypes.c_char_p
gpu.gpu_node.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
gpu.bench_gpu_nodes.restype = ctypes.c_double; gpu.bench_gpu_nodes.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
gpu.bench_gpu_tree.restype = ctypes.c_double; gpu.bench_gpu_tree.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
M32 = (1 << 32) - 1
MRC = json.load(open(os.path.join(HERE, "..", "..", "dse", "TOP", "mono_constants.json")))
mrc = b"".join(v.to_bytes(4, "little") for row in MRC for v in row)
assert gpu.gpu_init(bytes(256), mrc) == 0
print("GPU:", gpu.gpu_name().decode())

IV = [0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A, 0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19]
SIGMA = [2, 6, 3, 10, 7, 0, 4, 13, 1, 11, 12, 5, 9, 14, 15, 8]
def rotr(v, n): return ((v >> n) | (v << (32 - n))) & M32
def g(v, a, b, c, d, mx, my):
    v[a] = (v[a] + v[b] + mx) & M32; v[d] = rotr(v[d] ^ v[a], 16); v[c] = (v[c] + v[d]) & M32; v[b] = rotr(v[b] ^ v[c], 12)
    v[a] = (v[a] + v[b] + my) & M32; v[d] = rotr(v[d] ^ v[a], 8); v[c] = (v[c] + v[d]) & M32; v[b] = rotr(v[b] ^ v[c], 7)
def compress16(h, m, block_len, flags):
    v = list(h) + IV[:4] + [0, 0, block_len, flags]; m = list(m)
    for i in range(7):
        g(v, 0, 4, 8, 12, m[0], m[1]); g(v, 1, 5, 9, 13, m[2], m[3]); g(v, 2, 6, 10, 14, m[4], m[5]); g(v, 3, 7, 11, 15, m[6], m[7])
        g(v, 0, 5, 10, 15, m[8], m[9]); g(v, 1, 6, 11, 12, m[10], m[11]); g(v, 2, 7, 8, 13, m[12], m[13]); g(v, 3, 4, 9, 14, m[14], m[15])
        m = [m[SIGMA[j]] for j in range(16)]
    return [v[i] ^ v[i + 8] for i in range(8)] + [v[i + 8] ^ h[i] for i in range(8)]
kat = compress16(IV, [0] * 16, 0, 11)[:8]
assert b"".join(w.to_bytes(4, "little") for w in kat).hex() == "af1349b9f5f9a1a6a0404dea36dcc9499bcb25c9adc112b7cc9a93cae41f3262"
def words(b): return [int.from_bytes(b[4 * i:4 * i + 4], "little") for i in range(len(b) // 4)]
rnd = random.Random(5)
ok_all = True
for p, name in ((5, "BLAKE3 parent node"), (6, "BLAKE3 keyed-XOF GGM node (64 B)")):
    ok = True
    for _ in range(20):
        l, r = rnd.randbytes(32), rnd.randbytes(32)
        o = ctypes.create_string_buffer(64)
        ok &= gpu.gpu_node(p, l, r, o) == 0
        if p == 5: ok &= words(o.raw[:32]) == compress16(IV, words(l + r), 64, 4)[:8]
        else: ok &= words(o.raw) == compress16(words(l), words(r) + [0] * 8, 64, 27)
    ok_all &= ok
    print(f"  {name} vs Python BLAKE3 model (20 random): {'OK' if ok else 'FAIL'}")

# unit: N = 8 ARX blocks per issue, ChaCha 21 issues / block, BLAKE3 14 issues / node, Monolith 25 issues / node (one state per issue)
UNIT = [("ChaCha20 block (GGM PRG: 1 block = 2 children)", 2, 2.0, 21 / 8), ("BLAKE3 Merkle parent node", 5, 1.0, 14 / 8),
        ("BLAKE3 keyed-XOF GGM node (2 children)", 6, 1.0, 14 / 8), ("Monolith-31 Merkle node (1 permutation)", 4, 1.0, 25.0)]
print(f"\n| node function | GPU ns/node (2^{LOG2N} independent) | GPU Mnodes/s | unit cycles/node | unit @1 GHz Mnodes/s | GPU / one unit | units for 10x GPU |")
print("|---|---:|---:|---:|---:|---:|---:|")
for name, p, per, cyc in UNIT:
    ns = gpu.bench_gpu_nodes(p, LOG2N, 10) / per          # prim 2 computes two ChaCha blocks per node
    g_rate = 1e9 / ns; u_rate = 1e9 / cyc
    print(f"| {name} | {ns:.3f} | {g_rate / 1e6:,.0f} | {cyc:.3g} | {u_rate / 1e6:,.0f} | {g_rate / u_rate:.1f}x | {10 * g_rate / u_rate:,.0f} |")
print("\nALL OK" if ok_all else "\nSOME CHECKS FAILED")
