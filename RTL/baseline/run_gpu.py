"""run_gpu.py - measure the GPU (CUDA) throughput of the five node functions and compare with the CPU and
with the unified HLS unit. Needs baseline.dll (CPU) and gpu_prims.dll (build_gpu.sh).
1. every GPU node function vs the CPU DLL (20 random pairs)
2. GPU ns/node for independent nodes (2^22 nodes) and for a level-by-level Merkle build (2^22 leaves)
3. table against CPU (optimised, 1 core / all threads) and the unified unit at 300 MHz / 1 GHz
usage: run_gpu.py [log2 nodes]
"""
import ctypes, json, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
LOG2N = int(sys.argv[1]) if len(sys.argv) > 1 else 22
cpu = ctypes.CDLL(os.path.join(HERE, "baseline.dll"))
gpu = ctypes.CDLL(os.path.join(HERE, "gpu_prims.dll"))
cpu.node.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
cpu.bench_hash.restype = ctypes.c_double; cpu.bench_hash.argtypes = [ctypes.c_int, ctypes.c_longlong, ctypes.c_char_p]
cpu.bench_hash_mt.restype = ctypes.c_double; cpu.bench_hash_mt.argtypes = [ctypes.c_int, ctypes.c_longlong, ctypes.c_int]
cpu.prim_name.restype = ctypes.c_char_p
gpu.gpu_init.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
gpu.gpu_name.restype = ctypes.c_char_p
gpu.gpu_node.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
gpu.bench_gpu_nodes.restype = ctypes.c_double; gpu.bench_gpu_nodes.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
gpu.bench_gpu_tree.restype = ctypes.c_double; gpu.bench_gpu_tree.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
P = (1 << 31) - 1
NAMES = ["SHA3-256", "SHA-256", "ChaCha20 (2 blocks)", "AES-128 DM", "Monolith-31"]
DS = [32, 32, 32, 16, 32]

# AES S-box and Monolith constants for the GPU constant memory (same construction as prims.h)
def gf_mul(a, b):
    p = 0
    for _ in range(8):
        if b & 1: p ^= a
        hi = a & 0x80; a = (a << 1) & 0xFF
        if hi: a ^= 0x1b
        b >>= 1
    return p
sbox = bytearray(256)
for a in range(256):
    inv = next((b for b in range(1, 256) if gf_mul(a, b) == 1), 0) if a else 0
    v, s = inv, inv
    for _ in range(4):
        v = ((v << 1) | (v >> 7)) & 0xFF; s ^= v
    sbox[a] = s ^ 0x63
MRC = json.load(open(os.path.join(HERE, "..", "..", "dse", "TOP", "mono_constants.json")))
mrc = b"".join(v.to_bytes(4, "little") for row in MRC for v in row)
rc = gpu.gpu_init(bytes(sbox), mrc)
assert rc == 0, f"gpu_init failed {rc}"
print("GPU:", gpu.gpu_name().decode())

# ---------------- 1. GPU node functions vs the CPU DLL ----------------
print("GPU node functions vs CPU (20 random pairs each)")
rnd = random.Random(11)
ok_all = True
for p in range(5):
    ok = True
    for _ in range(20):
        l = b"".join((rnd.getrandbits(31) % P).to_bytes(4, "little") for _ in range(DS[p] // 4))
        r = b"".join((rnd.getrandbits(31) % P).to_bytes(4, "little") for _ in range(DS[p] // 4))
        a = ctypes.create_string_buffer(32); b = ctypes.create_string_buffer(32)
        cpu.node(p, l, r, a); e = gpu.gpu_node(p, l, r, b)
        ok &= (e == 0) and a.raw[:DS[p]] == b.raw[:DS[p]]
    ok_all &= ok
    print(f"  {NAMES[p]}: {'OK' if ok else 'FAIL'}")

# ---------------- 2/3. throughput ----------------
HW = [("SHA3-256", 24, 12), ("SHA-256", 130, 130), ("ChaCha20", 42, 42), ("AES-128 DM", 11, 11), ("Monolith-31", 220, 25)]
UTIL = 0.98
THREADS = cpu.cpu_threads()
o = ctypes.create_string_buffer(64)
print(f"\n| primitive | GPU ns/node (independent, 2^{LOG2N}) | GPU Mnodes/s | GPU Merkle level-by-level ns/node | CPU 1 core ns | CPU {THREADS} thr ns | unit issues/node | unit @300 MHz Mnodes/s | unit @1 GHz Mnodes/s | GPU / unit@1GHz | units for 10x GPU |")
print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
rows = []
for p in range(5):
    g_ns = gpu.bench_gpu_nodes(p, LOG2N, 10)
    g_tree = gpu.bench_gpu_tree(p, LOG2N, 5)
    c1 = cpu.bench_hash(p + 5, 1 << 20, o)
    cm = cpu.bench_hash_mt(p + 5, 1 << 19, THREADS)
    name, iss, iss_best = HW[p]
    u300 = 300e6 * UTIL / iss_best; u1g = 1e9 * UTIL / iss_best
    gpu_rate = 1e9 / g_ns
    rows.append((name, g_ns, g_tree, c1, cm, iss_best, u1g, gpu_rate))
    print(f"| {name} | {g_ns:.2f} | {gpu_rate / 1e6:,.0f} | {g_tree:.2f} | {c1:,.0f} | {cm:.1f} | {iss} ({iss_best}) | {u300 / 1e6:,.1f} | {u1g / 1e6:,.1f} | {gpu_rate / u1g:,.0f}x | {10 * gpu_rate / u1g:,.0f} |")
print("\nALL OK" if ok_all else "\nSOME CHECKS FAILED")
