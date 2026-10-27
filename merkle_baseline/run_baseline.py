"""run_baseline.py - driver of baseline.dll (merklecpp + the five primitives, portable and optimised).
1. known-answer tests (NIST / RFC vectors, Monolith vs the Python model)
2. every node function (portable 0..4 and optimised 5..9) vs an independent Python implementation
3. merklecpp roots of 8-leaf trees vs a Python binary tree
4. throughput: ns per node alone, inside merklecpp (2^LOG2N leaves) and on all CPU threads,
   against the unified HLS unit (issues per node at II = 1, FPGA 300 MHz and ASIC 1 GHz clocks).
usage: run_baseline.py [dll] [log2 leaves]
"""
import ctypes, hashlib, json, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
DLL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "baseline.dll")
LOG2N = int(sys.argv[2]) if len(sys.argv) > 2 else 20
d = ctypes.CDLL(os.path.abspath(DLL))
d.prim_name.restype = ctypes.c_char_p
d.bench_tree.restype = ctypes.c_double
d.bench_tree.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint64]
d.bench_hash.restype = ctypes.c_double
d.bench_hash.argtypes = [ctypes.c_int, ctypes.c_longlong, ctypes.c_char_p]
d.bench_hash_mt.restype = ctypes.c_double
d.bench_hash_mt.argtypes = [ctypes.c_int, ctypes.c_longlong, ctypes.c_int]
d.node.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
d.leaves.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_char_p]
d.raw_sha3.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p]
d.raw_chacha.argtypes = [ctypes.c_char_p, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_char_p]
d.raw_aes.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
d.raw_aes_ni.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
d.raw_mono.argtypes = [ctypes.POINTER(ctypes.c_uint32)]
P = (1 << 31) - 1
NAMES = [d.prim_name(p).decode() for p in range(10)]
DS = [d.digest_size(p) for p in range(10)]
THREADS = d.cpu_threads()
ok_all = True
def report(name, ok):
    global ok_all
    ok_all &= ok; print(f"  {name}: {'OK' if ok else 'FAIL'}")

# ---------------- Python reference implementations ----------------
def rotl32(v, n): return ((v << n) | (v >> (32 - n))) & 0xFFFFFFFF
def chacha_block(key, ctr, nonce):
    s = [0x61707865, 0x3320646e, 0x79622d32, 0x6b206574] + [int.from_bytes(key[4*i:4*i+4], "little") for i in range(8)] + [ctr] + [int.from_bytes(nonce[4*i:4*i+4], "little") for i in range(3)]
    x = list(s)
    def qr(a, b, c, dd):
        x[a] = (x[a] + x[b]) & 0xFFFFFFFF; x[dd] = rotl32(x[dd] ^ x[a], 16); x[c] = (x[c] + x[dd]) & 0xFFFFFFFF; x[b] = rotl32(x[b] ^ x[c], 12)
        x[a] = (x[a] + x[b]) & 0xFFFFFFFF; x[dd] = rotl32(x[dd] ^ x[a], 8); x[c] = (x[c] + x[dd]) & 0xFFFFFFFF; x[b] = rotl32(x[b] ^ x[c], 7)
    for _ in range(10):
        qr(0, 4, 8, 12); qr(1, 5, 9, 13); qr(2, 6, 10, 14); qr(3, 7, 11, 15)
        qr(0, 5, 10, 15); qr(1, 6, 11, 12); qr(2, 7, 8, 13); qr(3, 4, 9, 14)
    return b"".join(((x[i] + s[i]) & 0xFFFFFFFF).to_bytes(4, "little") for i in range(16))
def gf_mul(a, b):
    p = 0
    for _ in range(8):
        if b & 1: p ^= a
        hi = a & 0x80; a = (a << 1) & 0xFF
        if hi: a ^= 0x1b
        b >>= 1
    return p
SBOX = [0] * 256
for a in range(256):
    inv = next((b for b in range(1, 256) if gf_mul(a, b) == 1), 0) if a else 0
    v, s = inv, inv
    for _ in range(4):
        v = ((v << 1) | (v >> 7)) & 0xFF; s ^= v
    SBOX[a] = s ^ 0x63
def xt(x): return ((x << 1) ^ (0x1b if x & 0x80 else 0)) & 0xFF
def aes128(key, pt):
    rk = [list(key)]
    rcon = 1
    for r in range(1, 11):
        prev = rk[-1]
        t = [SBOX[prev[13]] ^ rcon, SBOX[prev[14]], SBOX[prev[15]], SBOX[prev[12]]]; rcon = xt(rcon)
        w = [prev[i] ^ t[i] for i in range(4)]
        for i in range(4, 16): w.append(prev[i] ^ w[i - 4])
        rk.append(w)
    s = [pt[i] ^ rk[0][i] for i in range(16)]
    for r in range(1, 11):
        t = [SBOX[v] for v in s]
        s = [t[4 * ((c + row) & 3) + row] for c in range(4) for row in range(4)]
        if r < 10:
            for c in range(4):
                a0, a1, a2, a3 = s[4*c:4*c+4]
                s[4*c:4*c+4] = [xt(a0) ^ xt(a1) ^ a1 ^ a2 ^ a3, a0 ^ xt(a1) ^ xt(a2) ^ a2 ^ a3, a0 ^ a1 ^ xt(a2) ^ xt(a3) ^ a3, xt(a0) ^ a0 ^ a1 ^ a2 ^ xt(a3)]
        s = [s[i] ^ rk[r][i] for i in range(16)]
    return bytes(s)
MRC = json.load(open(os.path.join(HERE, "..", "dse", "TOP", "mono_constants.json")))
ROW = [61402, 17845, 26798, 59689, 12021, 40901, 41351, 27521, 56951, 12034, 53865, 43244, 7454, 33823, 28750, 1108]
def rot(x, n, w): return ((x << n) | (x >> (w - n))) & ((1 << w) - 1)
def bar_chunk(x, w):
    t = x ^ (rot(~x & ((1 << w) - 1), 1, w) & rot(x, 2, w) & (rot(x, 3, w) if w == 8 else (1 << w) - 1)); return rot(t, 1, w)
def bar31(x):
    return bar_chunk(x & 0xFF, 8) | (bar_chunk((x >> 8) & 0xFF, 8) << 8) | (bar_chunk((x >> 16) & 0xFF, 8) << 16) | (bar_chunk(x >> 24, 7) << 24)
def concrete(x): return [sum(ROW[k] * x[(i + k) % 16] for k in range(16)) % P for i in range(16)]
def mono(x):
    x = concrete(x)
    for k in range(6):
        x = [bar31(v) for v in x[:8]] + x[8:]
        x = [x[0]] + [(x[i] + x[i-1] * x[i-1]) % P for i in range(1, 16)]
        x = concrete(x)
        if k < 5: x = [(v + MRC[k][i]) % P for i, v in enumerate(x)]
    return x
def py_node(p, l, r):
    p %= 5
    if p == 0: return hashlib.sha3_256(l + r).digest()
    if p == 1: return hashlib.sha256(l + r).digest()
    if p == 2:
        h1 = chacha_block(l, int.from_bytes(r[0:4], "little"), r[4:16])[:32]
        return chacha_block(h1, int.from_bytes(r[16:20], "little"), r[20:32])[:32]
    if p == 3:
        c = aes128(l, r); return bytes(a ^ b for a, b in zip(c, r))
    x = [int.from_bytes(l[4*i:4*i+4], "little") for i in range(8)] + [int.from_bytes(r[4*i:4*i+4], "little") for i in range(8)]
    return b"".join(v.to_bytes(4, "little") for v in mono(x)[:8])

# ---------------- 1. known-answer tests ----------------
print("known-answer tests")
o = ctypes.create_string_buffer(64)
d.raw_sha3(b"abc", 3, o); report("SHA3-256('abc')", o.raw[:32].hex() == "3a985da74fe225b2045c172d6bd390bd855f086e3e9d525b46bfe24511431532")
d.raw_chacha(bytes(range(32)), 1, bytes.fromhex("000000090000004a00000000"), o)
report("ChaCha20 block RFC 8439 2.3.2", o.raw[:16].hex() == "10f1e7e4d13b5915500fdd1fa32071c4")
k, pt = bytes.fromhex("000102030405060708090a0b0c0d0e0f"), bytes.fromhex("00112233445566778899aabbccddeeff")
d.raw_aes(k, pt, o); report("AES-128 FIPS-197 C.1 (portable)", o.raw[:16].hex() == "69c4e0d86a7b0430d8cdb78070b4c55a")
d.raw_aes_ni(k, pt, o); report("AES-128 FIPS-197 C.1 (AES-NI)", o.raw[:16].hex() == "69c4e0d86a7b0430d8cdb78070b4c55a")
x = (ctypes.c_uint32 * 16)(*range(16)); d.raw_mono(x)
report("Monolith-31 permutation vs Python model", list(x)[:8] == mono(list(range(16)))[:8])

# ---------------- 2. node functions vs Python ----------------
print("node functions vs Python (20 random pairs each)")
rnd = random.Random(3)
def rand_digest(p):
    return b"".join((rnd.getrandbits(31) % P).to_bytes(4, "little") for _ in range(DS[p] // 4))
for p in range(10):
    ok = True
    for _ in range(20):
        l, r = rand_digest(p), rand_digest(p)
        out = ctypes.create_string_buffer(32); d.node(p, l, r, out)
        ok &= out.raw[:DS[p]] == py_node(p, l, r)
    report(NAMES[p], ok)

# ---------------- 3. Merkle roots of 8-leaf trees ----------------
print("merklecpp roots vs a Python binary tree (8 leaves)")
for p in range(10):
    buf = ctypes.create_string_buffer(8 * DS[p]); d.leaves(p, 8, 0, buf)
    lv = [buf.raw[i * DS[p]:(i + 1) * DS[p]] for i in range(8)]
    while len(lv) > 1: lv = [py_node(p, lv[i], lv[i + 1]) for i in range(0, len(lv), 2)]
    root = ctypes.create_string_buffer(32); d.bench_tree(p, 3, 0, root, 0)
    report(NAMES[p], root.raw[:DS[p]] == lv[0])

# ---------------- 4. throughput ----------------
HW = [("SHA3-256", 24, 12), ("SHA-256", 130, 130), ("ChaCha20", 42, 42), ("AES-128 DM", 11, 11), ("Monolith-31", 220, 25)]
UTIL = 0.98                     # tree-scheduling utilisation measured in dse/SCHED (4096-leaf chunks)
print(f"\nCPU: {THREADS} hardware threads. HLS unit: II = 1, one issue per cycle, utilisation {UTIL:.0%} (dse/SCHED).")
print(f"\n| primitive | CPU portable ns/node | CPU optimised ns/node | in merklecpp (2^{LOG2N} leaves) ns/node | all {THREADS} threads ns/node | unit issues/node (best variant) | unit FPGA 300 MHz Mnodes/s | unit ASIC 1 GHz Mnodes/s | unit @1 GHz vs 1 core | unit @1 GHz vs {THREADS} threads |")
print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
rows = []
for p in range(5):
    name, iss, iss_best = HW[p]
    ns_plain = d.bench_hash(p, 1 << 19, o)
    ns_fast = d.bench_hash(p + 5, 1 << 20, o)
    root = ctypes.create_string_buffer(32)
    sec = d.bench_tree(p + 5, LOG2N, 0, root, 0)
    ns_tree = sec * 1e9 / ((1 << LOG2N) - 1)
    ns_mt = d.bench_hash_mt(p + 5, 1 << 19, THREADS)
    fpga = 300e6 * UTIL / iss_best; asic = 1e9 * UTIL / iss_best
    rows.append((name, ns_plain, ns_fast, ns_tree, ns_mt, iss, iss_best, fpga, asic))
    print(f"| {name} | {ns_plain:,.0f} | {ns_fast:,.0f} | {ns_tree:,.0f} | {ns_mt:,.1f} | {iss} ({iss_best}) | {fpga / 1e6:,.1f} | {asic / 1e6:,.1f} | {asic * ns_fast / 1e9:,.1f}x | {asic * ns_mt / 1e9:,.2f}x |")
print("\nALL OK" if ok_all else "\nSOME CHECKS FAILED")
