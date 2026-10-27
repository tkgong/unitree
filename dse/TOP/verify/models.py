"""models.py - Python reference models of the three node functions (BLAKE3 compress, ChaCha20 block, Monolith-31)
and the lane packing of pipe_axn.h (one ARX block = BL lanes; Monolith state at lanes BASE..BASE+7)."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
M32, P = (1 << 32) - 1, (1 << 31) - 1
CP = [0, 2, 4, 6, 1, 3, 5, 7]            # lane i holds words (2*CP[i], 2*CP[i]+1): column order (a b c d of columns 0,1 then 2,3)


def pk(lo, hi): return (lo & M32) | ((hi & M32) << 32)
def rotl(v, n): return ((v << n) | (v >> (32 - n))) & M32
def rotr(v, n): return ((v >> n) | (v << (32 - n))) & M32


# ---------------- BLAKE3 ----------------
IV = [0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A, 0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19]
SIGMA = [2, 6, 3, 10, 7, 0, 4, 13, 1, 11, 12, 5, 9, 14, 15, 8]
CHUNK_START, CHUNK_END, PARENT, ROOT, KEYED_HASH = 1, 2, 4, 8, 16


def g(v, a, b, c, d, mx, my):
    v[a] = (v[a] + v[b] + mx) & M32; v[d] = rotr(v[d] ^ v[a], 16); v[c] = (v[c] + v[d]) & M32; v[b] = rotr(v[b] ^ v[c], 12)
    v[a] = (v[a] + v[b] + my) & M32; v[d] = rotr(v[d] ^ v[a], 8); v[c] = (v[c] + v[d]) & M32; v[b] = rotr(v[b] ^ v[c], 7)


def compress16(h, m, counter, block_len, flags):
    v = list(h[:8]) + IV[:4] + [counter & M32, (counter >> 32) & M32, block_len, flags]
    m = list(m)
    for i in range(7):
        g(v, 0, 4, 8, 12, m[0], m[1]); g(v, 1, 5, 9, 13, m[2], m[3]); g(v, 2, 6, 10, 14, m[4], m[5]); g(v, 3, 7, 11, 15, m[6], m[7])
        g(v, 0, 5, 10, 15, m[8], m[9]); g(v, 1, 6, 11, 12, m[10], m[11]); g(v, 2, 7, 8, 13, m[12], m[13]); g(v, 3, 4, 9, 14, m[14], m[15])
        m = [m[SIGMA[j]] for j in range(16)]
    return [v[i] ^ v[i + 8] for i in range(8)] + [v[i + 8] ^ h[i] for i in range(8)]


def b3_lanes(h, m, counter, block_len, flags, BL):
    """input lanes of one BLAKE3 block (BL = 22 with the chaining-value lanes, 18 without)"""
    v = list(h[:8]) + IV[:4] + [counter & M32, (counter >> 32) & M32, block_len, flags]
    L = [pk(v[2 * CP[i]], v[2 * CP[i] + 1]) for i in range(8)]
    L += [pk(m[0], m[2]), pk(m[1], m[3]), pk(m[4], m[6]), pk(m[5], m[7]), pk(m[8], m[14]), pk(m[9], m[15]), pk(m[12], m[10]), pk(m[13], m[11])]   # diagonal half: P column order
    L += [0, 0]
    if BL == 22: L += [pk(h[2 * i], h[2 * i + 1]) for i in range(4)]
    return L


def b3_words(lanes):
    """16 output words of one block: lanes 0..3 = cv (v[0..7]^v[8..15]), lanes 4..7 = XOF second half"""
    return [w for k in range(8) for w in (lanes[k] & M32, lanes[k] >> 32)]


# ---------------- ChaCha20 ----------------
def cc_block(words):
    x = list(words)
    def qr(a, b, c, d):
        x[a] = (x[a] + x[b]) & M32; x[d] = rotl(x[d] ^ x[a], 16); x[c] = (x[c] + x[d]) & M32; x[b] = rotl(x[b] ^ x[c], 12)
        x[a] = (x[a] + x[b]) & M32; x[d] = rotl(x[d] ^ x[a], 8); x[c] = (x[c] + x[d]) & M32; x[b] = rotl(x[b] ^ x[c], 7)
    for _ in range(10):
        qr(0, 4, 8, 12); qr(1, 5, 9, 13); qr(2, 6, 10, 14); qr(3, 7, 11, 15)
        qr(0, 5, 10, 15); qr(1, 6, 11, 12); qr(2, 7, 8, 13); qr(3, 4, 9, 14)
    return [(x[i] + words[i]) & M32 for i in range(16)]


def _row(words, x): return pk(words[4 * x], words[4 * x + 1]), pk(words[4 * x + 2], words[4 * x + 3])
def _prow(x, lo, hi):
    """P (column <-> diagonal involution) of one row of two lanes: hardware column j <- column (x - j) mod 4"""
    LO_, HI_ = (lambda v: v & M32), (lambda v: v >> 32)
    if x == 0: return pk(LO_(lo), HI_(hi)), pk(LO_(hi), HI_(lo))
    if x == 1: return pk(HI_(lo), LO_(lo)), pk(HI_(hi), LO_(hi))
    if x == 2: return pk(LO_(hi), HI_(lo)), pk(LO_(lo), HI_(hi))
    return pk(HI_(hi), LO_(hi)), pk(HI_(lo), LO_(lo))


def cc_lanes(words, BL):
    """ChaCha20 block: rows a b c d in A B C D (lanes 0..7, column order), the input copy for the feed-forward in
    a (8,10) b (9,11) c (12,14) d (13,15)"""
    L = [pk(words[2 * CP[i]], words[2 * CP[i] + 1]) for i in range(8)]
    (a0, a1), (b0, b1), (c0, c1), (d0, d1) = (_row(words, x) for x in range(4))
    return L + [a0, b0, a1, b1, c0, d0, c1, d1] + [0] * (BL - 16)


def cc_words(lanes):
    """the 16 output words after the last traversal (lanes of one block, >= 18): A = P_a(c), B = P_b(b), C = P_c(a), T = d"""
    a = _prow(2, lanes[2], lanes[6]); b = _prow(1, lanes[1], lanes[5]); c = _prow(0, lanes[0], lanes[4]); d = (lanes[16], lanes[17])
    return [w for lo, hi in (a, b, c, d) for w in (lo & M32, lo >> 32, hi & M32, hi >> 32)]


# ---------------- Monolith-31 ----------------
MRC = json.load(open(os.path.join(HERE, "..", "mono_constants.json")))
ROW = [61402, 17845, 26798, 59689, 12021, 40901, 41351, 27521, 56951, 12034, 53865, 43244, 7454, 33823, 28750, 1108]


def _rot(x, n, w): return ((x << n) | (x >> (w - n))) & ((1 << w) - 1)
def _bar_chunk(x, w):
    t = x ^ (_rot(~x & ((1 << w) - 1), 1, w) & _rot(x, 2, w) & (_rot(x, 3, w) if w == 8 else (1 << w) - 1)); return _rot(t, 1, w)
def bar31(x):
    return _bar_chunk(x & 0xFF, 8) | (_bar_chunk((x >> 8) & 0xFF, 8) << 8) | (_bar_chunk((x >> 16) & 0xFF, 8) << 16) | (_bar_chunk(x >> 24, 7) << 24)
def concrete(x): return [sum(ROW[k] * x[(i + k) % 16] for k in range(16)) % P for i in range(16)]
def mono(x):
    x = concrete(x)
    for k in range(6):
        x = [bar31(v) for v in x[:8]] + x[8:]
        x = [x[0]] + [(x[i] + x[i-1] * x[i-1]) % P for i in range(1, 16)]
        x = concrete(x)
        if k < 5: x = [(v + MRC[k][i]) % P for i, v in enumerate(x)]
    return x


def mono_lanes(x): return [pk(x[2 * k], x[2 * k + 1]) for k in range(8)]
def mono_words(lanes): return [v % P for k in range(8) for v in (lanes[k] & M32, lanes[k] >> 32)]


# ---------------- Poseidon2-M31 (Plonky3 p3-mersenne-31 0.8.0: width 16, x^5, 4 + 14 + 4 rounds, constants in pos2_constants.json) ----------------
import json as _json, os as _os
P2C = _json.load(open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "pos2_constants.json")))
P2_SHIFTS = P2C["diag_shifts"]
def _p2_m4(x):
    a, b, c, d = x
    t01 = a + b; t23 = c + d; t0123 = t01 + t23; t01123 = t0123 + b; t01233 = t0123 + d
    return [(t01123 + t01) % P, (t01123 + 2 * c) % P, (t01233 + t23) % P, (t01233 + 2 * a) % P]
def p2_ext(x):
    m = sum((_p2_m4(x[4 * c:4 * c + 4]) for c in range(4)), [])
    s = [sum(m[4 * c + j] for c in range(4)) % P for j in range(4)]
    return [(m[i] + s[i % 4]) % P for i in range(16)]
def p2_int(x):
    part = sum(x[1:]) % P; full = (part + x[0]) % P
    return [(part - x[0]) % P] + [(full + (x[i] << P2_SHIFTS[i - 1])) % P for i in range(1, 16)]
def p2_sbox(v): v2 = v * v % P; return v2 * v2 % P * v % P
def pos2(x):
    x = p2_ext(x)
    for rc in P2C["external_initial"]: x = p2_ext([p2_sbox((v + r) % P) for v, r in zip(x, rc)])
    for rc in P2C["internal"]: x = p2_int([p2_sbox((x[0] + rc) % P)] + x[1:])
    for rc in P2C["external_final"]: x = p2_ext([p2_sbox((v + r) % P) for v, r in zip(x, rc)])
    return x
# the round-constant rows the unit's M_E / M_I networks inject (M_E rows: after the initial layer and after every external
# round; M_I rows: after every internal round; the row added after a round holds the NEXT round's constants)
P2E_ROWS = [P2C["external_initial"][0]] + P2C["external_initial"][1:4] + [[P2C["internal"][0]] + [0] * 15] + P2C["external_final"][1:4] + [[0] * 16]
P2I_ROWS = [[P2C["internal"][r + 1]] + [0] * 15 for r in range(13)] + [P2C["external_final"][0]]
