"""dp_vec.py - test vectors for mono_dp18 alone (tb_dp.cpp): random states x (16 elements <= p), one traversal r = 0..6
each: r = 0 Concrete only; r >= 1 Bars (elements 0..7), Bricks, Concrete, + RC[r-1] for r <= 5 (dse/TOP/verify/models.py).
    python dp_vec.py > dp_vec.txt"""
import os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "dse", "TOP", "verify"))
import models as M
P = M.P
random.seed(7)
for n in range(140):
    r = n % 7
    x = [random.randrange(P + 1) for _ in range(16)]
    xc = [v % P for v in x]
    if r == 0: y = M.concrete(xc)
    else:
        t = [M.bar31(v) for v in xc[:8]] + xc[8:]
        t = [t[0]] + [(t[i] + t[i - 1] * t[i - 1]) % P for i in range(1, 16)]
        y = M.concrete(t)
        if r <= 5: y = [(v + M.MRC[r - 1][i]) % P for i, v in enumerate(y)]
    print(f"{r:x} " + " ".join(f"{v:x}" for v in x) + " " + " ".join(f"{v:x}" for v in y))
