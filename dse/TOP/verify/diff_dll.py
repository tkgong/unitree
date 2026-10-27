"""diff_dll.py old.dll new.dll [cycles] [seed] - drive two builds of lane_pipe with the same random per-cycle controls and
inputs (every lane random, every control random: mono, mono2, htap, blake, r, r2, rg[], er[]) and compare every output
lane of every cycle."""
import ctypes, random, sys
old, new = sys.argv[1], sys.argv[2]
N = int(sys.argv[3]) if len(sys.argv) > 3 else 3000
seed = int(sys.argv[4]) if len(sys.argv) > 4 else 1
L = [ctypes.CDLL(p) for p in (old, new)]
for l in L: l.lp_info.restype = ctypes.c_int
info = [[l.lp_info(k) for k in (9, 14)] for l in L]
assert info[0] == info[1], info
NIO, NG = info[0]
try: NE = [l.lp_info(30) for l in L]
except Exception: NE = [0, 0]
NE = NE[0]
ARR = ctypes.c_ulonglong * NIO; IG = ctypes.c_int * max(NG, 1); IE = ctypes.c_int * max(NE, 1)
for l in L:
    l.lp_step_e.argtypes = [ctypes.c_int] * 6 + [IG, IE, ARR, ARR]
rnd = random.Random(seed)
bad = 0
for t in range(N):
    sparse = rnd.random() < 0.5                   # half of the cycles: realistic-looking sparse controls
    c = [rnd.randrange(2), rnd.randrange(2), rnd.randrange(2), rnd.randrange(2),
         rnd.randrange(8) if sparse else rnd.randrange(512), rnd.randrange(8) if sparse else rnd.randrange(512)]
    rg = IG(*[(rnd.randrange(14) | (256 if rnd.random() < 0.1 else 0)) if sparse else rnd.randrange(512) for _ in range(max(NG, 1))])
    er = IE(*[rnd.randrange(16) for _ in range(max(NE, 1))])
    a = ARR(*[rnd.getrandbits(64) for _ in range(NIO)])
    o = [ARR(), ARR()]
    for i, l in enumerate(L): l.lp_step_e(*c, rg, er, a, o[i])
    if list(o[0]) != list(o[1]):
        d = [i for i in range(NIO) if o[0][i] != o[1][i]]
        bad += 1
        if bad <= 3: print(f"cycle {t}: {len(d)} lanes differ, first {d[:8]}")
print(f"{old.split('/')[-1]} vs {new.split('/')[-1]}: {N} cycles x {NIO} lanes, {NG} groups, {NE} engines: " + ("IDENTICAL" if bad == 0 else f"{bad} cycles DIFFER"))
