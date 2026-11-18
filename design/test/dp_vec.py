import os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "model", "verify"))
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
