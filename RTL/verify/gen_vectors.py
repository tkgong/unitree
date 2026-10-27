"""Reference vectors for D:\\unitree\\RTL from the HLS C++ ALUs (ref_alu.dll = alu_core.h exported). One file per module
instance, NV lines, each line = the 64-bit fields (inputs..., expected output) as 16 hex digits each, MSB field first."""
import ctypes, os, random
HERE = os.path.dirname(os.path.abspath(__file__)); VEC = os.path.join(HERE, "vec"); os.makedirs(VEC, exist_ok=True)
L = ctypes.CDLL(os.path.join(HERE, "ref_alu.dll"))      # built by run_tb.sh from ref_alu.cpp + dse/TOP/alu_core.h
U = ctypes.c_uint64; I = ctypes.c_int
for n, args in {"ref_add": (I, U, U), "ref_lend": (I, I, U, U, U, U), "ref_addp": (I, U, U), "ref_lendp": (I, I, U, U, U, U),
                "ref_mul31": (U, U), "ref_mul31_en": (I, U, U), "ref_fold31": (U,), "ref_fold": (I, U), "ref_canon32": (U,),
                "ref_canon31": (U,), "ref_negm31": (I, U), "ref_bar31": (U,), "ref_bar_chunk8": (U,), "ref_bar_chunk7": (U,),
                "ref_xor": (U, U), "ref_rot31": (I, U)}.items():
    f = getattr(L, n); f.argtypes = args; f.restype = U
NV = 4096; P = (1 << 31) - 1
rnd = random.Random(20261027)
def edges(W): return sorted(set(v for v in (0, 1, 2, (1 << W) - 1, (1 << W) - 2, 1 << (W - 1), (1 << (W - 1)) - 1, P, P + 1, (1 << 32) - 1, 1 << 32) if v < (1 << W)))
def fill(rows, mk):
    while len(rows) < NV: rows.append(mk())
    return rows[:NV]
def write(name, rows):
    with open(os.path.join(VEC, name + ".hex"), "w") as f:
        for r in rows: f.write("".join(f"{v:016x}" for v in r) + "\n")
    assert len(rows) == NV, name
total = 0
for W in range(32, 42):
    e = edges(W); rows = [(a, b, L.ref_add(W, a, b)) for a in e for b in e]
    write(f"add_{W}", fill(rows, lambda: (lambda a, b: (a, b, L.ref_add(W, a, b)))(rnd.getrandbits(W), rnd.getrandbits(W))))
    rows = [(a, b, L.ref_addp(W, a, b)) for a in e for b in e]
    write(f"addp_{W}", fill(rows, lambda: (lambda a, b: (a, b, L.ref_addp(W, a, b)))(rnd.getrandbits(W), rnd.getrandbits(W))))
    for nm, fn in (("lend", L.ref_lend), ("lendp", L.ref_lendp)):
        rows = [(x, ea, eb, a, b, fn(W, x, ea, eb, a, b)) for x in (0, 1) for ea in e[:4] for eb in e[-4:] for a in e[-3:] for b in e[:3]]
        def mk(fn=fn):
            x = rnd.getrandbits(1); ea, eb, a, b = (rnd.getrandbits(W) for _ in range(4)); return (x, ea, eb, a, b, fn(W, x, ea, eb, a, b))
        write(f"{nm}_{W}", fill(rows, mk))
    total += 4
e31 = [0, 1, 2, P, P - 1, 1 << 30, (1 << 30) - 1, (1 << 30) + 1]
rows = [(a, b, L.ref_mul31(a, b)) for a in e31 for b in e31]
write("mul31", fill(rows, lambda: (lambda a, b: (a, b, L.ref_mul31(a, b)))(rnd.getrandbits(31), rnd.getrandbits(31))))
rows = [(en, a, b, L.ref_mul31_en(en, a, b)) for en in (0, 1) for a in e31 for b in e31]
write("mul31_en", fill(rows, lambda: (lambda en, a, b: (en, a, b, L.ref_mul31_en(en, a, b)))(rnd.getrandbits(1), rnd.getrandbits(31), rnd.getrandbits(31))))
e32 = [0, 1, P - 1, P, P + 1, (1 << 32) - 1, (1 << 32) - 2, 1 << 31]
rows = [(r, L.ref_fold31(r)) for r in e32] + [(lo + hi, L.ref_fold31(lo + hi)) for lo in (0, 1, P - 1, P) for hi in (0, 1, P - 1, P)]
write("fold31", fill(rows, lambda: (lambda r: (r, L.ref_fold31(r)))(rnd.getrandbits(32))))
for H in range(1, 31):
    rows = [(r, L.ref_fold(H, r)) for r in e32] + [(lo + hi, L.ref_fold(H, lo + hi)) for lo in (0, 1, P - (1 << H) + 1, P - 1, P) for hi in (0, 1, (1 << H) - 2, (1 << H) - 1)]
    write(f"fold_{H}", fill(rows, lambda: (lambda r: (r, L.ref_fold(H, r)))(rnd.getrandbits(32))))
total += 30 + 3
for W, fn in ((32, L.ref_canon32), (31, L.ref_canon31)):
    rows = [(t, fn(t)) for t in e31]
    write(f"canon_{W}", fill(rows, lambda fn=fn: (lambda t: (t, fn(t)))(rnd.getrandbits(31))))
for W in range(31, 36):
    rows = [(t, L.ref_negm31(W, t)) for t in e31]
    write(f"negm31_{W}", fill(rows, lambda: (lambda t: (t, L.ref_negm31(W, t)))(rnd.getrandbits(31))))
rows = [(x, L.ref_bar_chunk8(x)) for x in range(256)] * 16                    # exhaustive
write("bar_chunk_8", rows)
rows = [(x, L.ref_bar_chunk7(x)) for x in range(128)] * 32                    # exhaustive
write("bar_chunk_7", rows)
rows = [(x, L.ref_bar31(x)) for x in (0, 1, P, 1 << 31, (1 << 32) - 1, 0x80808080, 0x7F7F7F7F)]
write("bar31", fill(rows, lambda: (lambda x: (x, L.ref_bar31(x)))(rnd.getrandbits(32))))
rows = [(a, b, L.ref_xor(a, b)) for a in (0, (1 << 64) - 1, 1 << 63) for b in (0, (1 << 64) - 1, 1)]
write("xor", fill(rows, lambda: (lambda a, b: (a, b, L.ref_xor(a, b)))(rnd.getrandbits(64), rnd.getrandbits(64))))
for R in range(31):
    rows = [(v, L.ref_rot31(R, v)) for v in e31]
    write(f"rot31_{R}", fill(rows, lambda: (lambda v: (v, L.ref_rot31(R, v)))(rnd.getrandbits(31))))
total += 2 + 5 + 3 + 1 + 31
print(f"{total} vector files x {NV} vectors in {VEC}")
