"""gen_lane_mono6.py - emit lane_mono_kl.inc: Monolith-31 with the Bricks squares on their OWN pipelined adder chains, so
ONE traversal = one full round (Bars -> Bricks -> Concrete -> + round constants): 7 traversals per permutation
(the initial Concrete, then 6 rounds) instead of the 25 of gen_lane_mono5.py (which ran the squares on the leaves of the
Concrete trees, 5 per traversal).

Square stage (levels 1..SQD): x_k^2 = sum_{i<31} x_k[i] * rot_i(x_k) mod p (31 gated rotations, 2^i x = rot_i(x) mod p),
summed on NCH parallel accumulation chains (one 2-operand adder per chain per level, 31 adders ... 30 adders per
square), the chain heads combined by a balanced tree, then y_{k+1} = x_{k+1} + x_k^2 folded to < p and written to the
state lanes. The Concrete (Plonky3 Karatsuba conv16, kara_dag.py: 41 constant multiplications as CSD rotate-add trees
on lazily reduced values, 14 adder levels) follows at levels SQD+1..SQD+14 and reads the post-Bricks state.
Every adder of width >= 32 (chain, combine, bricks, Concrete tree, reduction / fold first adders) can be lent to the
ARX blocks (ext / EA / EB / EY ports, selected operands, non-inlined alu_add<W> modules, alu_core.h).
Levels: one adder depth per level. Lanes BASE..BASE+7 = the 16 elements (2 per lane); all partial values are
bit-packed from lane BASE+8 up, one layout per level.
env: MONO_BASE, MONO_LEND (level:count,...), MONO_OUT, MONO_LEND_ANY=1, MONO_LEND_RED=1, MONO_LEND_MOD=1, MONO_NCH (default 4)
"""
import json, os, random, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kara_dag as KD
from kara_dag import P, nbits, rot, Node

K = 1
BASE = int(os.environ.get("MONO_BASE", "0"))                  # state lanes BASE..BASE+7, partial sums packed above
LEND = {int(a.split(":")[0]): int(a.split(":")[1]) for a in os.environ.get("MONO_LEND", "").split(",") if a}   # level: adders lent (ext/EA/EB/EY)
OUTNAME = os.environ.get("MONO_OUT", "")
LEND_ANY = os.environ.get("MONO_LEND_ANY", "") == "1"              # lend any 2-operand adder, not only register-fed ones
LEND_RED = os.environ.get("MONO_LEND_RED", "") == "1"              # also lend the 32-bit reduction / fold first adders (low31 + high)
LEND_MOD = os.environ.get("MONO_LEND_MOD", "") == "1"              # lent adders as non-inlined alu_add<W> modules: HLS cannot duplicate them per branch
NCH = int(os.environ.get("MONO_NCH", "4"))                         # accumulation chains per square
SQMUL = os.environ.get("MONO_SQMUL", "") == "1"                    # squares as 31x31 multipliers (level 1) + lo/hi pre-fold adder (level 2) instead of adder chains
P2 = os.environ.get("MONO_P2", "") == "1"                          # Poseidon2-M31 on the same datapath: B / C operand lanes, 16 multipliers, brk, M_E / M_I networks + taps
ONLY_P2 = os.environ.get("MONO_ONLY_P2", "") == "1"                # the natural Poseidon2 unit: no Bars, no Concrete
assert P2 or not ONLY_P2
assert not P2 or SQMUL, "MONO_P2 needs MONO_SQMUL=1 (the multipliers)"
HOST = P2 and not ONLY_P2 and os.environ.get("MONO_P2_HOST", "1") == "1"   # M_E / M_I on the Concrete adders and lanes (pos select)
MUL3 = P2 and os.environ.get("MONO_P2_MUL3", "") == "1"                  # three multiplier ranks: x^5 in one pass
A1 = MUL3 and os.environ.get("MONO_P2_A1", "") == "1"                    # state lanes only: no B / C operands, chain from A, S-box on slot 0
PREFIX = os.environ.get("MONO_PREFIX", "monk")                     # function prefix (monk_lx<k>); a second datapath uses e.g. monk2 / MONO2
DEFPFX = os.environ.get("MONO_DEF", "MONO")                        # macro / constant prefix (MONO_K_D, MONO_BASE, MONO_KC, ...)
XLEND = {}
MRC = json.load(open(os.path.join(HERE, "mono_constants.json")))
NRC = 7                                                          # rc index: 0..4 rounds with constants, 5 last round, 6 initial


# ---------------- reference ----------------
def rot_w(x, n, w): return ((x << n) | (x >> (w - n))) & ((1 << w) - 1)
def bar_chunk(x, w):
    t = x ^ (rot_w(~x & ((1 << w) - 1), 1, w) & rot_w(x, 2, w) & (rot_w(x, 3, w) if w == 8 else (1 << w) - 1)); return rot_w(t, 1, w)
def bar31(x):
    return bar_chunk(x & 0xFF, 8) | (bar_chunk((x >> 8) & 0xFF, 8) << 8) | (bar_chunk((x >> 16) & 0xFF, 8) << 16) | (bar_chunk(x >> 24, 7) << 24)
def concrete(x): return [sum(KD.ROW[k] * x[(i + k) % 16] for k in range(16)) % P for i in range(16)]
def mono_ref(x):
    x = concrete(x)
    for k in range(6):
        x = [bar31(v) for v in x[:8]] + x[8:]
        x = [x[0]] + [(x[i] + x[i - 1] * x[i - 1]) % P for i in range(1, 16)]
        x = concrete(x)
        if k < 5: x = [(v + MRC[k][i]) % P for i, v in enumerate(x)]
    return x


# ---------------- DAG: Concrete ----------------
d = KD.build()
outs = KD.finish(d, {})
S = KD.coefficients(d)
for m in d.muls: m.sq = None
for lf in [n for n in d.hw if n.kind == "leaf"]: lf.gate = None

# constant-injection mults: 16 independent columns of S (mod P), prefer leaf counts not a power of two
def inv(a): return pow(a, P - 2, P)
basis, chosen_c = [], []
pref = sorted(d.muls, key=lambda m: (len(m.leaves) & (len(m.leaves) - 1) == 0, m.id))
for m in pref:
    col = [S[i].get(m.id, 0) % P for i in range(16)]
    v = list(col)
    for piv, bv in basis:
        if v[piv]:
            f = v[piv]
            v = [(a - f * b) % P for a, b in zip(v, bv)]
    nz = [i for i in range(16) if v[i]]
    if nz:
        piv = nz[0]; f = inv(v[piv]); v = [a * f % P for a in v]
        basis.append((piv, v)); chosen_c.append(m)
    if len(chosen_c) == 16: break
assert len(chosen_c) == 16
outs = KD.finish(d, {m.id: 1 for m in chosen_c})
S = KD.coefficients(d)
for m in d.muls:
    for lf in m.extra: lf.gate = None
folds = []
for i in range(16):
    f = Node("fold", src=outs[i], bound=P); f.depth = outs[i].depth + 1; f.tag = ("out", i); d.hw.append(f); folds.append(f)
d.hw.sort(key=lambda n: n.id)
chw = list(d.hw)                                                  # Concrete hardware nodes
CDEPTH = max(f.depth for f in folds)
xnodes = sorted([n for n in chw if n.kind == "x"], key=lambda n: n.j)
assert [n.j for n in xnodes] == list(range(16))

# ---------------- DAG: square stage (Bricks) ----------------
sqnodes = []
BRF = []                                                          # fold node holding y_{k+1} = x_{k+1} + x_k^2, k = 0..14
YF = []                                                           # P2: fold node holding Y_k = (brk ? A[k] : 0) + B[k-1] * C[k-1], k = 0..15
PREN = []
if P2:
    for k in range(16):
        q = Node("mulx", src=xnodes[k], bound=(P - 1) * (P - 1)); q.depth = 1; q.srcb = k; sqnodes.append(q)        # 62-bit product B[k] * C[k]
        if MUL3: root = Node("pf", src=q, bound=P); root.depth = 2; sqnodes.append(root); PREN.append(root)          # lo31 + hi31 (lendable) then + carry: 31 bits
        else: root = Node("pre", src=q, bound=(1 << 32) - 2); root.depth = 2; sqnodes.append(root); PREN.append(root)     # lo31 + hi31 (32 bits, lendable)
    for k in range(16):
        g = Node("leaf", src=xnodes[k], k=0, bound=P); g.brk = True; g.depth = 0; sqnodes.append(g)                  # brk ? A[k] : 0
        pr = PREN[(k - 1) % 16]
        if A1:                                                    # y_k = x_k + (pos ? 0 : x_{k-1}^2); y_0 = x_0 (Monolith Bricks)
            pz = Node("leaf", src=pr, k=0, bound=P); pz.pzero = True; pz.k0 = (k == 0); pz.depth = 0; sqnodes.append(pz)
            br = Node("add", ops=[(g, 0, False), (pz, 0, False)], bound=P + pz.bound); br.depth = 3; sqnodes.append(br)
        else:
            br = Node("add", ops=[(g, 0, False), (pr, 0, False)], bound=P + pr.bound); br.depth = 3; sqnodes.append(br)
        f = Node("fold", src=br, bound=P); f.depth = 4; f.tag = ("br", k); sqnodes.append(f); YF.append(f)
X5N, CWN = [], []
if MUL3:
    for k in (range(0) if A1 else range(16)):
        c = Node("cw", bound=P); c.depth = 1; c.k = k; c.chain = True; sqnodes.append(c); CWN.append(c)          # C word, carried to rank 3
    for k in range(16):
        m2 = Node("mulx", src=PREN[k], bound=(P * P if A1 else (P - 1) * (P - 1))); m2.depth = 3; m2.opa = PREN[k]; m2.opb = PREN[k]; m2.chain = True; sqnodes.append(m2)
        p2_ = Node("pf", src=m2, bound=P); p2_.depth = 4; p2_.chain = True; sqnodes.append(p2_)
        m3 = Node("mulx", src=p2_, bound=(P * P if A1 else (P - 1) * (P - 1))); m3.depth = 5; m3.opa = p2_; m3.opb = (xnodes[k] if A1 else CWN[k]); m3.chain = True; sqnodes.append(m3)
        p3_ = Node("pf", src=m3, bound=P); p3_.depth = 6; p3_.chain = True; sqnodes.append(p3_); X5N.append(p3_)
for k in (range(0) if P2 else range(15)):
    xk = xnodes[k]
    if SQMUL:
        q = Node("mulx", src=xk, bound=(P - 1) * (P - 1)); q.depth = 1; sqnodes.append(q)                 # 62-bit product x_k * x_k
        root = Node("pre", src=q, bound=(1 << 32) - 2); root.depth = 2; sqnodes.append(root)              # lo31 + hi31 (32 bits, lendable)
    else:
        chains = [[] for _ in range(NCH)]
        for i in range(31):
            lf = Node("leaf", src=xk, k=i, bound=P); lf.sq2 = True; lf.gate = i; lf.depth = 0
            chains[i % NCH].append(lf); sqnodes.append(lf)
        heads = []
        for ch in chains:
            acc = ch[0]
            for t in ch[1:]:
                add = Node("add", ops=[(acc, 0, False), (t, 0, False)], bound=acc.bound + t.bound); add.depth = acc.depth + 1
                sqnodes.append(add); acc = add
            heads.append(acc)
        root = KD._tree(sqnodes, [(h, 0, False) for h in heads])
    br = Node("add", ops=[(xnodes[k + 1], 0, False), (root, 0, False)], bound=P + root.bound); br.depth = root.depth + 1; sqnodes.append(br)
    f = Node("fold", src=br, bound=P); f.depth = br.depth + 1; f.tag = ("br", k + 1); sqnodes.append(f); BRF.append(f)
SQD = max(n.depth for n in sqnodes if not getattr(n, "chain", False))
p2nodes, EF, IF, E_CONST, I_CONST = [], [], [], [], []
if P2:
    P2C = json.load(open(os.path.join(HERE, "verify", "pos2_constants.json")))
    def xl(j, k=0, neg=False):                                    # rotl31 / complement of post-Bricks word j, as a leaf
        lf = Node("leaf", src=xnodes[j], k=k, neg=neg, bound=P); lf.xsrc = True; lf.depth = 0; p2nodes.append(lf); return lf
    def _negleaf():                                               # p - x^5_15 (M_I, MUL3)
        lf = Node("leaf", src=X5N[0 if A1 else 15], k=0, neg=True, bound=P); lf.x5i = True; lf.depth = 0; p2nodes.append(lf); return lf
    def cst(tab, i):                                              # round-constant leaf (ROM row chosen by the issue's dec)
        lf = Node("leaf", bound=P); lf.const = True; lf.p2c = (tab, i); lf.depth = 0; p2nodes.append(lf)
        (E_CONST if tab == "E" else I_CONST).append(lf); return lf
    def add2(a, b, ja=0, jb=0): return KD._tree(p2nodes, [(a, ja, False), (b, jb, False)])
    # M_E: Plonky3 mds_light_permutation (M4 = circ(2,3,1,1) per chunk of 4, then + the chunk sums), input i = Y_{(i+1) mod 16}
    def yi(i):
        if not MUL3: return xnodes[(i + 1) % 16]
        lf = Node("leaf", src=X5N[i], k=0, bound=P); lf.x5e = i; lf.depth = 0; p2nodes.append(lf); return lf   # ini ? X[i] : x^5_i
    def yi0():                                                    # M_I input 0: the internal S-box runs on slot 15
        lf = Node("leaf", src=X5N[0 if A1 else 15], k=0, bound=P); lf.x5i = True; lf.depth = 0; p2nodes.append(lf); return lf
    m4 = []
    for c in range(4):
        a, b, cc, dd = [yi(4 * c + t) for t in range(4)]
        t01 = add2(a, b); t23 = add2(cc, dd); t0123 = add2(t01, t23); t01123 = add2(t0123, b); t01233 = add2(t0123, dd)
        m4 += [add2(t01123, t01), add2(t01123, cc, 0, 1), add2(t01233, t23), add2(t01233, a, 0, 1)]
    SUMS = [KD._tree(p2nodes, [(m4[4 * c + j], 0, False) for c in range(4)]) for j in range(4)]
    for i in range(16):
        w = add2(m4[i], cst("E", i)); y = add2(w, SUMS[i % 4])
        f = Node("fold", src=y, bound=P); f.depth = y.depth + 1; f.p2net = True; f.tag = ("E", i); p2nodes.append(f); EF.append(f)
    # M_I: y_0 = (sum_{i>=1} Y_i) + (p - Y_0) + rc_0; y_i = (sum_j Y_j) + rotl(Y_i, s_i) + rc_i
    part = KD._tree(p2nodes, [(xnodes[i], 0, False) for i in range(1, 16)])
    full = add2(part, yi0() if MUL3 else xnodes[0])
    ys = [add2(part, add2(xl(0, 0, True) if not MUL3 else _negleaf(), cst("I", 0)))]
    for i in range(1, 16): ys.append(add2(full, add2(xl(i, P2C["diag_shifts"][i - 1]), cst("I", i))))
    fd = max(y.depth for y in ys) + 1
    for i, y in enumerate(ys):
        f = Node("fold", src=y, bound=P); f.depth = fd; f.p2net = True; f.tag = ("I", i); p2nodes.append(f); IF.append(f)
    P2D = max(EF[0].depth, fd)
    for n in p2nodes: n.p2 = True
P2S, HOSTOF, P2LV = 0, {}, {}
if HOST:
    cap = {}
    for h in chw:
        if h.kind == "add": cap.setdefault(h.depth + SQD, []).append(h)
    for L in cap: cap[L].sort(key=lambda h: nbits(h.bound))
    used = set()
    def p2_avail(n):                                              # level after which every input of n is available
        ls = [SQD]
        srcs = [a for (a, j, neg) in n.ops] if n.kind == "add" else [n.src]
        for a in srcs:
            if a.kind == "add" and getattr(a, "p2", False): ls.append(P2LV[a.id])
            elif a.kind == "leaf" and (getattr(a, "x5e", None) is not None or getattr(a, "x5i", False)): ls.append(a.src.depth)
        return max(ls)
    def take(L, need):
        h = next((h for h in cap.get(L, []) if h.id not in used and nbits(h.bound) >= need), None)
        if h is not None: used.add(h.id)
        return h
    for g in sorted([n for n in p2nodes if n.kind in ("add", "fold")], key=lambda n: (n.depth, n.id)):
        L = p2_avail(g) + 1; need = 32 if g.kind == "fold" else nbits(g.bound)
        while True:
            h = take(L, need)
            if h is not None: break
            L += 1; assert L <= SQD + CDEPTH, "the Concrete adders cannot host the Poseidon2 additions"
        HOSTOF[g.id] = h; P2LV[g.id] = L
    P2LE, P2LI = max(P2LV[f.id] for f in EF), max(P2LV[f.id] for f in IF)
    for g in [n for n in p2nodes if n.kind in ("add", "fold")]: g.host = HOSTOF[g.id]; g.host.guest = g
    print(f"Poseidon2 linear layers hosted on {len(HOSTOF)} Concrete adders; taps at levels {P2LE} (M_E) / {P2LI} (M_I)")
P2B = X5N[0].depth if MUL3 else SQD                              # the level the Poseidon2 networks read from (chain output or the state lanes)
D = (P2B + P2D) if ONLY_P2 else SQD + CDEPTH
d.hw = (sqnodes + p2nodes) if ONLY_P2 else (chw + sqnodes + p2nodes)
# roles (for the netlist dump): square terms / chains / combine / bricks / bricks fold; Concrete pre-adds / CSD trees / post-adds / reductions / output folds
ROLE = {}
for n in sqnodes:
    if n.kind == "leaf": ROLE[n.id] = "term"
    elif n.kind == "mulx": ROLE[n.id] = "mulx"
    elif n.kind == "pre": ROLE[n.id] = "sqpre"
    elif n.kind == "fold": ROLE[n.id] = "bricksfold"
    elif n.kind in ("cw", "pf"): ROLE[n.id] = n.kind
    elif n.ops[0][0].kind == "x": ROLE[n.id] = "bricks"
    elif any(a.kind == "leaf" for a, j, neg in n.ops): ROLE[n.id] = "chain"
    else: ROLE[n.id] = "combine"
for n in chw:
    if n.kind == "add": ROLE[n.id] = "pre" if n in d.pre else ("tree" if n.mul is not None else "post")
    elif n.kind == "red": ROLE[n.id] = "red"
    elif n.kind == "fold": ROLE[n.id] = "outfold"
    elif n.kind == "x": ROLE[n.id] = "x"
    else: ROLE[n.id] = "const" if n.const else "leaf"
LENTQ = {}
hw_sq = set(n.id for n in sqnodes)


# ---------------- evaluation (Python model of the hardware) ----------------
def fold_out(v, W):
    hw = W - 31
    assert v < (1 << W)
    r = (v & P) + (v >> 31)
    if r >> 31: assert (r & P) < (1 << hw) - 1
    t = (r & P) + (r >> 31)
    return 0 if t == P else t


def _t31(r): return (r & P) + (r >> 31)                           # 32-bit lazy value -> 31-bit lazy (<= p), as the chain folds do
def _f31(r):                                                     # 32-bit lazy value -> canonical
    t = (r & P) + (r >> 31); return 0 if t == P else t
def _eval_nodes(nodes, xin, val, bricks, constval, xb=None, xc=None, brk=True, ini=False, pos=False):
    for n in nodes:
        k = n.kind
        if k == "x": v = xin[n.j]
        elif k == "cw": v = xc[n.k]
        elif k == "pf": v = _t31((val[n.src.id] & P) + (val[n.src.id] >> 31)) if A1 else _f31((val[n.src.id] & P) + (val[n.src.id] >> 31))
        elif k == "mulx" and getattr(n, "opa", None) is not None: v = val[n.opa.id] * val[n.opb.id] if (bricks or A1) else 0
        elif k == "mulx": v = ((xb[n.src.j] * xc[n.srcb]) if (P2 and not A1) else xin[n.src.j] * xin[n.src.j]) if bricks else 0
        elif k == "pre": v = (val[n.src.id] & P) + (val[n.src.id] >> 31)
        elif k == "red": v = KD.fold_red(val[n.src.id])
        elif k == "leaf":
            if getattr(n, "sq2", False):
                xv = xin[n.src.j]; v = rot(xv, n.k) if (bricks and (xv >> n.k) & 1) else 0
            elif getattr(n, "brk", False): v = xin[n.src.j] if (brk or A1) else 0
            elif getattr(n, "pzero", False): v = 0 if (pos or n.k0) else val[n.src.id]
            elif getattr(n, "x5e", None) is not None: v = xin[n.x5e] if ini else val[n.src.id]
            elif getattr(n, "x5i", False):
                v = val[n.src.id]
                if n.neg: v = P - v
            elif n.const: v = (constval or {}).get(n.id, 0)
            else:
                v = rot(val[n.src.id], n.k)
                if n.neg: v = P - v
            assert 0 <= v <= P
        elif k == "add":
            v = 0
            for (a, j, neg) in n.ops:
                t = val[a.id] << j
                if neg:
                    W = nbits(a.bound << j); assert t < (1 << W); t = (1 << W) - 1 - t
                v += t
            assert v <= n.bound, (n.kind, getattr(n, 'role', None), n.id, n.depth, v, n.bound)
        elif k == "fold":
            v = fold_out(val[n.src.id], nbits(n.src.bound))
        val[n.id] = v


def evaluate(x, bricks, constval=None, xb=None, xc=None, brk=True, ini=False, pos=False):
    """x: the 16 state words after Bars -> values of every node: the square stage reads x (P2: the products read the
    operand words xb, xc; Monolith: xb = x, xc = x with x_15 = 0), the Concrete / M_E / M_I read the post-Bricks state y"""
    val = {}
    if P2:
        xb = list(x) if xb is None else xb; xc = (list(x[:15]) + [0]) if xc is None else xc
    _eval_nodes(xnodes, x, val, bricks, constval, xb, xc, brk, ini, pos)
    _eval_nodes(sqnodes, x, val, bricks, constval, xb, xc, brk, ini, pos)
    y = [val[YF[k].id] for k in range(16)] if P2 else [x[0]] + [val[BRF[k].id] for k in range(15)]
    _eval_nodes(chw, y, val, bricks, constval, xb, xc, brk, ini)
    if P2: _eval_nodes(p2nodes, y, val, bricks, constval, xb, xc, brk, ini)
    return val


rnd = random.Random(7)
offs = None
for t in (range(0) if ONLY_P2 else range(3)):
    x = [rnd.randrange(P) for _ in range(16)]
    val = evaluate(x, False)
    o = [(val[folds[i].id] - concrete(x)[i]) % P for i in range(16)]
    assert offs is None or o == offs
    offs = o
def solve(rows, rhs):
    """rows[i] = 16 coefficients (mod P), returns c with rows . c = rhs"""
    A = [[a % P for a in r] + [b % P] for r, b in zip(rows, rhs)]
    n = 16
    for c in range(n):
        p = next(r for r in range(c, n) if A[r][c])
        A[c], A[p] = A[p], A[c]
        f = inv(A[c][c]); A[c] = [a * f % P for a in A[c]]
        for r in range(n):
            if r != c and A[r][c]:
                g = A[r][c]; A[r] = [(a - g * b) % P for a, b in zip(A[r], A[c])]
    return [A[r][n] for r in range(n)]
rows = [[S[i].get(m.id, 0) for m in chosen_c] for i in range(16)]
KC = []
for r in range(NRC):
    rc = MRC[r] if r < 5 else [0] * 16
    KC.append([0] * 16 if ONLY_P2 else solve(rows, [(rc[i] - offs[i]) % P for i in range(16)]))
KC.append([0] * 16)
constval = [{m.extra[0].id: KC[r][t] for t, m in enumerate(chosen_c)} for r in range(NRC + 1)]


# ---------------- issue schedule and the Python model ----------------
def dec_byte(bricks, bars, rc, brk=None, pe=0, pi=0, pos=0, ini=0): return bricks | (bars << 1) | (rc << 2) | ((int(P2) if brk is None else brk) << 5) | (pe << 6) | (pi << 10) | (pos << 14) | (ini << 15)
DEC = [dec_byte(0, 0, 6)] + [dec_byte(1, 1, r) for r in range(6)]
NISS = len(DEC)
R_SQ = R_INIT = R_X5E = R_X5I = 0
if MUL3:                                                          # x^5 in one pass: INIT (M_E of the input), X5E rows 1..8, X5I rows 0..13
    R_INIT = len(DEC); DEC.append(dec_byte(0, 0, 7, brk=1, pe=0, pos=1, ini=1))
    R_X5E = len(DEC); DEC += [dec_byte(1, 0, 7, brk=0, pe=row, pos=1) for row in range(1, 9)]
    R_X5I = len(DEC); DEC += [dec_byte(1, 0, 7, brk=1, pe=8, pi=row, pos=1) for row in range(14)]
elif P2:                                                          # the Poseidon2 issue kinds (software picks them per issue; see verify/pos2_prog.py)
    R_SQ = len(DEC); DEC.append(dec_byte(1, 0, 7, brk=0, pe=8, pos=1))
    R_INIT = len(DEC); DEC.append(dec_byte(0, 0, 7, brk=1, pe=0, pos=1))
    R_X5E = len(DEC); DEC += [dec_byte(1, 0, 7, brk=0, pe=row, pos=1) for row in range(1, 9)]
    R_X5I = len(DEC); DEC += [dec_byte(1, 0, 7, brk=1, pe=8, pi=row, pos=1) for row in range(14)]
NDEC = len(DEC)
DECW = 16 if P2 else 8


def model_issue(st, dec):
    bricks, bars, rc, brk = dec & 1, (dec >> 1) & 1, (dec >> 2) & 7, (dec >> 5) & 1
    st = list(st)
    if bars: st[:8] = [bar31(v) for v in st[:8]]
    val = evaluate(st, bricks, constval[rc], brk=brk)
    return [val[folds[i].id] for i in range(16)]
for t in (range(0) if ONLY_P2 else range(3)):
    x = [rnd.randrange(P) for _ in range(16)]
    st = list(x)
    for dec in DEC[:NISS]: st = model_issue(st, dec)
    assert st == mono_ref(x), "Python model of the issue schedule does not match the reference"
if not ONLY_P2: print(f"Python model: {NISS}-issue schedule (one round per traversal) matches the Monolith reference")
if P2:
    sys.path.insert(0, os.path.join(HERE, "verify"))
    from pos2_prog import P2Prog, P2ProgMul3, words as _words, STEPS as _STEPS, STEPS_M as _STEPS_M
    if MUL3: P2Prog, _STEPS = P2ProgMul3, _STEPS_M
    if A1:
        from pos2_prog import P2ProgMul3A1; P2Prog = P2ProgMul3A1
    from models import pos2, P2E_ROWS, P2I_ROWS
    def cv(dec):
        rc, pe, pi = (dec >> 2) & 7, (dec >> 6) & 15, (dec >> 10) & 15
        d_ = dict(constval[rc]); d_.update({lf.id: P2E_ROWS[pe][i] for i, lf in enumerate(E_CONST)}); d_.update({lf.id: P2I_ROWS[pi][i] for i, lf in enumerate(I_CONST)})
        return d_
    codes = {"R_SQ": R_SQ, "R_INIT": R_INIT, "R_X5E": R_X5E, "R_X5I": R_X5I, "SQD": SQD, "LE": SQD + EF[0].depth, "LI": SQD + IF[0].depth}
    for t in range(2):
        x = [rnd.randrange(P) for _ in range(16)]; pg = P2Prog(x, codes)
        while not pg.done():
            r_, ln, lev, tap = pg.issue(); dec = DEC[r_]
            A, B, C = _words(ln[0:8]), _words(ln[8:16]), _words(ln[16:24])
            val = evaluate(A, dec & 1, cv(dec), xb=B, xc=C, brk=(dec >> 5) & 1, ini=(dec >> 15) & 1, pos=(dec >> 14) & 1)
            o = [val[(YF if tap == 8 else EF if tap == 16 else IF)[k].id] for k in range(16)]
            assert o == pg.expected_tap(), f"Poseidon2 issue {pg.i} {_STEPS[pg.i]}: hardware model differs from the step model"
            pg.take(o)
        assert pg.s == pos2(x), "Python model of the Poseidon2 program does not match the Plonky3 reference"
    print(f"Python model: the {len(_STEPS)}-issue Poseidon2 program (taps at levels {SQD} / {codes['LE']} / {codes['LI']}) matches the Plonky3 reference")


# ---------------- levels, liveness, layout ----------------
lvl = {}
for n in d.hw:
    if getattr(n, "p2", False) and n.kind in ("add", "fold"): lvl[n.id] = P2LV[n.id] if HOST else n.depth + P2B
    elif n.kind in ("add", "red", "mulx", "pre", "pf", "cw"): lvl[n.id] = n.depth + (0 if n.id in hw_sq else SQD)
    elif n.kind == "fold": lvl[n.id] = n.depth if n.id in hw_sq else (n.depth + SQD if getattr(n, "p2net", False) else D)
    elif n.kind == "x": lvl[n.id] = 0
    else: lvl[n.id] = None
consumer = {}
reads = {}
def rd(n, L): reads.setdefault(n.id, set()).add(L)
for n in d.hw:
    if n.kind == "add":
        for (a, j, neg) in n.ops:
            if a.kind == "leaf":
                consumer[a.id] = n
                if not a.const: rd(a.src, lvl[n.id])
            elif a.kind != "x": rd(a, lvl[n.id])
    elif n.kind in ("red", "pre", "pf"): rd(n.src, lvl[n.id])
    elif n.kind == "mulx" and getattr(n, "opa", None) is not None: rd(n.opa, lvl[n.id]); rd(n.opb, lvl[n.id])
    elif n.kind == "fold": rd(n.src, lvl[n.id])
if HOST and os.environ.get("MONO_P2_STAT"):                      # register extension caused by the guests (diagnostic)
    own_end = {h.id: max(reads.get(h.id, {lvl[h.id]})) for h in chw if h.kind == "add"}
    guests = [n for n in p2nodes if n.kind in ("add", "fold")]
    g_end = {g.id: max(reads.get(g.id, set()) | {P2LE if (g.kind == "fold" and g in EF) else (P2LI if g.kind == "fold" else P2LV[g.id])}) for g in guests}
    ext = sum(max(0, g_end[g.id] - max(own_end[g.host.id], P2LV[g.id])) * nbits(g.bound) for g in guests)
    life = sum((g_end[g.id] - P2LV[g.id]) * nbits(g.bound) for g in guests)
    # best re-assignment per level: guests with the longest lifetimes get the hosts whose own value already lives longest
    best = 0
    for L in sorted(set(P2LV[g.id] for g in guests)):
        gl = sorted([g for g in guests if P2LV[g.id] == L], key=lambda g: -g_end[g.id]); hl = list(cap.get(L, []))
        for g in gl:
            need = 32 if g.kind == "fold" else nbits(g.bound)
            ok = [h for h in hl if nbits(h.bound) >= need]
            if not ok: best += (g_end[g.id] - L) * nbits(g.bound); continue
            cov = [h for h in ok if own_end[h.id] >= g_end[g.id]]
            h = min(cov, key=lambda h: own_end[h.id]) if cov else max(ok, key=lambda h: own_end[h.id])
            hl.remove(h); best += max(0, g_end[g.id] - max(own_end[h.id], L)) * nbits(g.bound)
    print(f"P2STAT: guest lifetimes {life:,} bits ({life / 64:.0f} lane-levels); host-slot extension now {ext:,} bits ({ext / 64:.0f} lane-levels), "
          f"best re-assignment at the same levels {best:,} bits ({best / 64:.0f} lane-levels); guests per level "
          f"{ {L: sum(1 for g in guests if P2LV[g.id] == L) for L in sorted(set(P2LV[g.id] for g in guests))} }; Concrete adds per level {[len(cap.get(L, [])) for L in range(1, D + 1)]}")
if HOST:
    for g in [n for n in p2nodes if n.kind in ("add", "fold")]:
        for L in reads.get(g.id, ()): rd(g.host, L)
    for f in EF: rd(f.host, P2LE)
    for f in IF: rd(f.host, P2LI)
live = {b: [] for b in range(1, D)}
for n in d.hw:
    if n.kind in ("add", "red", "mulx", "pre", "pf", "cw") and n.id in reads and n.id not in HOSTOF:
        for b in range(lvl[n.id], max(reads[n.id])):
            live[b].append(n)
off, lanes = {}, {}
for b in range(1, D):
    pos = 64 * (BASE + 8); off[b] = {}
    for n in sorted(live[b], key=lambda n: n.id):
        off[b][n.id] = pos; pos += nbits(n.bound)
    lanes[b] = BASE + 8 + (pos - 64 * (BASE + 8) + 63) // 64
lanes[D] = BASE + 8
LE = LI = TAPE = TAPI = 0
if P2:                                                            # 8 tap lanes for the 16 folded outputs of each network at its last level
    LE = max(lvl[f.id] for f in EF); TAPE = lanes[LE]; lanes[LE] += 8
    LI = max(lvl[f.id] for f in IF); TAPI = lanes[LI]; lanes[LI] += 8
    assert HOST or (all(lvl[f.id] == LE for f in EF) and all(lvl[f.id] == LI for f in IF))
adds = [n for n in d.hw if n.kind == "add"]
wide = {b: sum(1 for n in d.hw if n.kind in ("add", "red", "fold", "pre") and lvl[n.id] == b and nbits(n.bound) >= 32 and (n.kind != "fold" or n.id in hw_sq)) for b in range(1, D + 1)}
print(f"square stage {SQD} levels (NCH={NCH}), Concrete {CDEPTH} levels, D={D}; adders >= 32 bits per level: {[wide[b] for b in range(1, D + 1)]} (total {sum(wide.values())}); "
      f"lanes per level {[lanes[b] for b in range(1, D + 1)]}")


# ---------------- C++ emission ----------------
if P2 and "P2E_ROWS" not in globals():
    sys.path.insert(0, os.path.join(HERE, "verify")); from models import P2E_ROWS, P2I_ROWS
L = []
emit = L.append


def put(R, o, w, v):
    out, done = [], 0
    while done < w:
        l, b = divmod(o + done, 64)
        take = min(64 - b, w - done)
        out.append(f"{R}[{l}].range({b + take - 1}, {b}) = {v}.range({done + take - 1}, {done});")
        done += take
    return out


def get(R, o, w, dst):
    out, done = [f"ap_uint<{w}> {dst};"], 0
    while done < w:
        l, b = divmod(o + done, 64)
        take = min(64 - b, w - done)
        out.append(f"{dst}.range({done + take - 1}, {done}) = {R}[{l}].range({b + take - 1}, {b});")
        done += take
    return out


def W(n): return nbits(n.bound)
def name(n):
    if getattr(n, "host", None) is not None and n.kind == "add": return f"n{n.host.id}"
    if n.kind == "x": return f"(ap_uint<31>)X[{n.j}].range(30, 0)"
    if n.kind in ("fold", "pf"): return f"f{n.id}"
    return f"{'lf' if n.kind == 'leaf' else 'n'}{n.id}"


emit("// lane_mono_k.inc - GENERATED by gen_lane_mono6.py: Monolith-31, one round per traversal (Bars, Bricks on own adder chains, Karatsuba Concrete)")
emit(f"#define MONO_K_D {D}\n#define MONO_K_ADDERS {K}\n#define MONO_SQD {SQD}")
for b in range(1, D + 1): emit(f"#define MONO_K_N{b} {lanes[b]}")
emit(f"#define MONO_BASE {BASE}\n#define MONO_LEND_MAX {max(list(LEND.values()) + [1])}")
for b in range(1, D + 1): emit(f"#define MONO_LEND_{b} {LEND.get(b, 0)}")
emit(f"#define MONO_XLEND_MAX 1")
for b in range(1, D + 1): emit(f"#define MONO_XLEND_{b} 0")
LENT, LRANK, ALLRANK = {}, {}, {}
emit(f"#undef MONO_NISS\n#define MONO_NISS {NISS}\n#define MONO_NDEC {NDEC}\n#define MONO_DEC_W {DECW}")
if P2:
    emit(f"#define MONO_P2 1\n#define MONO_ONLY_P2 {1 if ONLY_P2 else 0}\n#define MONO_P2_HOST {1 if HOST else 0}\n#define MONO_P2_MUL3 {1 if MUL3 else 0}\n#define MONO_P2_A1 {1 if A1 else 0}\n#define MONO_P2_LE {LE}\n#define MONO_P2_LI {LI}\n#define MONO_P2_TAPE {TAPE}\n#define MONO_P2_TAPI {TAPI}")
    emit(f"#define MONO_P2_R_SQ {R_SQ}\n#define MONO_P2_R_INIT {R_INIT}\n#define MONO_P2_R_X5E {R_X5E}\n#define MONO_P2_R_X5I {R_X5I}")
    emit("static const ap_uint<31> MONO_P2E[9][16] = {" + ",".join("{" + ",".join(f"{c}u" for c in row) + "}" for row in P2E_ROWS) + "};")
    emit("static const ap_uint<31> MONO_P2I[14][16] = {" + ",".join("{" + ",".join(f"{c}u" for c in row) + "}" for row in P2I_ROWS) + "};")
emit(f"static const ap_uint<{DECW}> MONO_DEC_K[{NDEC}] = {{" + ",".join(map(str, DEC)) + "};")
emit("static const ap_uint<31> MONO_KC[8][16] = {" + ",".join("{" + ",".join(f"{c}u" for c in row) + "}" for row in KC) + "};")
emit("static const ap_uint<31> MONO_P31 = 0x7FFFFFFFu;")
emit('#include "alu_core.h"            // every operator below is an ALU call (alu_lend / alu_add, alu_mul31, alu_fold, alu_bar31, ...)')
emit("#ifndef UNITREE_LEVEL_OPS_H     // pk comes from level_ops.h when it is present")
emit("""static inline lane_t pk(word32_t lo, word32_t hi) {
#pragma HLS INLINE
    lane_t r; r.range(31, 0) = lo; r.range(63, 32) = hi; return r;
}""")
emit("#endif")
LENDF = "alu_lend" if LEND_MOD else "alu_lendp"      # lent adders: non-inlined alu_add<W> modules (HLS cannot duplicate them per branch)

bylevel = {b: [] for b in range(1, D + 1)}
for n in d.hw:
    if n.kind in ("add", "red", "fold", "mulx", "pre", "pf", "cw"): bylevel[lvl[n.id]].append(n)
for b in range(1, D + 1):
    emit(f"static inline void monk_lx{b}(const lane_t S[], ap_uint<{DECW}> dec, lane_t M[], bool ext, const word32_t EA[], const word32_t EB[], word32_t EY[], const word32_t XB[], word32_t XY[]) {{\n#pragma HLS INLINE")
    emit("#pragma HLS BIND_STORAGE variable=MONO_KC type=rom_1p impl=lutram")
    if P2: emit("#pragma HLS BIND_STORAGE variable=MONO_P2E type=rom_1p impl=lutram\n#pragma HLS BIND_STORAGE variable=MONO_P2I type=rom_1p impl=lutram")
    emit("    (void)ext; (void)EA; (void)EB; (void)EY; (void)XB; (void)XY;")
    lent_here = 0
    lent_ids = []
    emit(f"    for (int l = 0; l < MONO_K_N{b}; l++) {{\n#pragma HLS UNROLL\n        M[l] = (l >= {BASE} && l < {BASE + 8}) ? S[l] : (lane_t)0; }}")
    emit("    bool sq = dec[0], bars = dec[1]; ap_uint<3> rc = dec.range(4, 2);")
    emit("    (void)sq; (void)bars; (void)rc;")
    if P2: emit("    bool brk = dec[5]; ap_uint<4> ce = dec.range(9, 6); ap_uint<4> ci2 = dec.range(13, 10); bool pos = dec[14]; bool ini = dec[15]; (void)brk; (void)ce; (void)ci2; (void)pos; (void)ini;")
    emit("    word32_t X[16];\n    for (int i = 0; i < 8; i++) {\n#pragma HLS UNROLL\n        X[2*i] = S[" + str(BASE) + " + i].range(31, 0); X[2*i+1] = S[" + str(BASE) + " + i].range(63, 32); }")
    if b == 1 and P2 and not A1:
        emit("    word32_t XOB[16], XOC[16];\n    for (int i = 0; i < 8; i++) {\n#pragma HLS UNROLL\n        XOB[2*i] = S[" + str(BASE + 8) + " + i].range(31, 0); XOB[2*i+1] = S[" + str(BASE + 8) + " + i].range(63, 32);"
             "\n        XOC[2*i] = S[" + str(BASE + 16) + " + i].range(31, 0); XOC[2*i+1] = S[" + str(BASE + 16) + " + i].range(63, 32); }")
    if b == 1 and P2 and not ONLY_P2 and not A1:
        # the Monolith round squares the post-Bars state: the operand copies in the B / C lanes get the Bars too (same bars bit)
        emit("    if (bars) {" + chr(10) + "        for (int i = 0; i < 8; i++) {" + chr(10) + "#pragma HLS UNROLL" + chr(10) + "            XOB[i] = alu_bar31(XOB[i]); XOC[i] = alu_bar31(XOC[i]); }" + chr(10) + "    }")
    if b == 1 and not ONLY_P2:
        emit("    if (bars) {\n        for (int i = 0; i < 8; i++) {\n#pragma HLS UNROLL\n            X[i] = alu_bar31(X[i]); }\n"
             "        for (int i = 0; i < 4; i++) {\n#pragma HLS UNROLL\n            M[" + str(BASE) + " + i] = pk(X[2*i], X[2*i+1]); }\n    }")
    emit("    ap_uint<3> ci = rc; (void)ci;")
    # reads
    prev = live.get(b - 1, [])
    cur = set(n.id for n in live.get(b, []))
    for n in sorted(prev, key=lambda n: n.id):
        if b in reads.get(n.id, ()) or n.id in cur:
            for ln in get("S", off[b - 1][n.id], W(n), name(n)): emit("    " + ln)
    for n in sorted(prev, key=lambda n: n.id):
        if n.id in cur:
            for ln in put("M", off[b][n.id], W(n), name(n)): emit("    " + ln)
    # compute
    made_in = set()
    def has_neg(n): return n.kind == "add" and any(neg or (a.kind == "leaf" and a.neg) for (a, j, neg) in n.ops)
    def lend_rank(n):
        if n.kind != "add" or len(n.ops) != 2: return 3
        rng = [(j, nbits(a.bound << j)) for (a, j, neg) in n.ops]
        ov = min(r[1] for r in rng) - max(r[0] for r in rng)
        return 0 if ov >= 31 else (1 if ov >= 20 else 2)
    ALLRANK[b] = [lend_rank(n) for n in bylevel[b] if n.kind == "add"]
    order = sorted(bylevel[b], key=lambda n: (n.depth, lend_rank(n), has_neg(n), n.id))
    want = LEND.get(b, 0)
    cand = [n.id for n in order if n.kind == "add" and getattr(n, "host", None) is None and (LEND_ANY or all((a.kind != "add") or (lvl[a.id] < b) for (a, j, neg) in n.ops))]
    lendset = set(cand[:want])
    if LEND_RED and len(lendset) < want:
        lendset |= set([n.id for n in order if n.kind in ("red", "fold", "pre", "pf") and getattr(n, "host", None) is None][:want - len(lendset)])
    def red_add(n, s, Ws):
        global lent_here
        if n.id in lendset:
            q = lent_here; lent_here += 1; lent_ids.append(n.id); LRANK.setdefault(b, []).append(3); LENTQ[n.id] = q
            emit(f"    ap_uint<32> r{n.id} = {LENDF}<32>(ext, EA[{q}], EB[{q}], {name(s)}.range(30, 0), {name(s)}.range({Ws - 1}, 31));")
            emit(f"    EY[{q}] = (word32_t)r{n.id};")
        else:
            emit(f"    ap_uint<32> r{n.id} = alu_addp<32>({name(s)}.range(30, 0), {name(s)}.range({Ws - 1}, 31));")
    for n in order:
        if n.kind == "cw":
            emit(f"    ap_uint<31> n{n.id} = (ap_uint<31>)XOC[{n.k}].range(30, 0);")
        elif n.kind == "pf":                                         # lo31 + hi31 (lendable) then + carry, canonical
            red_add(n, n.src, 62)
            emit(f"    ap_uint<31> t{n.id} = alu_fold31(r{n.id});")
            if A1: emit(f"    word32_t f{n.id} = (word32_t)t{n.id};")                       # lazy (<= p): the networks fold at the taps
            else: emit(f"    word32_t f{n.id} = alu_canon<word32_t>(t{n.id});")
        elif n.kind == "mulx" and getattr(n, "opa", None) is not None:
            emit(f"    ap_uint<31> xa{n.id} = (ap_uint<31>){name(n.opa)}, xb{n.id} = (ap_uint<31>){name(n.opb)};")
            if A1: emit(f"    ap_uint<62> n{n.id} = alu_mul31(xa{n.id}, xb{n.id});")
            else: emit(f"    ap_uint<62> n{n.id} = alu_mul31_en(sq, xa{n.id}, xb{n.id});")
        elif n.kind == "mulx":
            # Bricks square as a 31x31 -> 62 multiplier (fabric), zero when the traversal has no Bricks
            if P2 and not A1:
                emit(f"    ap_uint<31> xa{n.id} = (ap_uint<31>)XOB[{n.src.j}].range(30, 0), xb{n.id} = (ap_uint<31>)XOC[{n.srcb}].range(30, 0);")
                emit(f"    ap_uint<62> n{n.id} = alu_mul31_en(sq, xa{n.id}, xb{n.id});")
            else:
                emit(f"    ap_uint<31> xa{n.id} = (ap_uint<31>)X[{n.src.j}].range(30, 0);")
                emit(f"    ap_uint<62> n{n.id} = alu_mul31_en(sq, xa{n.id}, xa{n.id});")
        elif n.kind == "pre":
            s_ = n.src
            red_add(n, s_, 62)
            emit(f"    ap_uint<32> n{n.id} = r{n.id};")
        elif n.kind == "red":
            s = n.src; Ws = W(s)
            red_add(n, s, Ws)
            emit(f"    ap_uint<31> n{n.id} = alu_fold<4>(r{n.id});")
        elif n.kind == "fold" and getattr(n, "host", None) is not None: continue
        elif n.kind == "fold":
            s = n.src; Ws = W(s); hw = Ws - 31
            assert 1 <= hw <= 30
            red_add(n, s, Ws)
            emit(f"    ap_uint<31> t{n.id} = alu_fold<{hw}>(r{n.id});")
            emit(f"    word32_t f{n.id} = alu_canon<word32_t>(t{n.id});")
        elif getattr(n, "host", None) is not None: continue    # a hosted Poseidon2 value: emitted with its host adder
        else:   # add: first its leaf operands
          def add_ops(n):
            for (a, j, neg) in n.ops:
                if a.kind != "leaf": continue
                if getattr(a, "sq2", False):
                    # Bricks square term: x_k[i] ? rot_i(x_k) : 0, off when the traversal has no Bricks (initial Concrete)
                    emit(f"    ap_uint<31> {name(a)} = (sq && X[{a.src.j}][{a.k}]) ? rot31<{a.k}>((ap_uint<31>)X[{a.src.j}].range(30, 0)) : (ap_uint<31>)0;")
                    continue
                if getattr(a, "pzero", False):
                    emit(f"    ap_uint<31> {name(a)} = " + ("(ap_uint<31>)0;" if a.k0 else f"pos ? (ap_uint<31>)0 : (ap_uint<31>)f{a.src.id};")); continue
                if getattr(a, "brk", False):
                    if A1: emit(f"    ap_uint<31> {name(a)} = (ap_uint<31>)X[{a.src.j}].range(30, 0);")
                    else: emit(f"    ap_uint<31> {name(a)} = brk ? (ap_uint<31>)X[{a.src.j}].range(30, 0) : (ap_uint<31>)0;")
                    continue
                if getattr(a, "x5e", None) is not None:
                    emit(f"    ap_uint<31> {name(a)} = ini ? (ap_uint<31>)X[{a.x5e}].range(30, 0) : (ap_uint<31>)f{a.src.id};"); continue
                if getattr(a, "x5i", False):
                    e = f"(ap_uint<31>)f{a.src.id}"
                    if a.neg: e = f"(ap_uint<31>)({e} ^ MONO_P31)"
                    emit(f"    ap_uint<31> {name(a)} = {e};"); continue
                if getattr(a, "p2c", None):
                    tab, ti = a.p2c; emit(f"    ap_uint<31> {name(a)} = MONO_P2{tab}[{'ce' if tab == 'E' else 'ci2'}][{ti}];"); continue
                if getattr(a, "xsrc", False):
                    e = f"rot31<{a.k}>((ap_uint<31>)X[{a.src.j}].range(30, 0))"
                    if a.neg: e = f"(ap_uint<31>)({e} ^ MONO_P31)"
                    emit(f"    ap_uint<31> {name(a)} = {e};"); continue
                m = a.mul
                if a.const:
                    t = chosen_c.index(m)
                    emit(f"    ap_uint<31> {name(a)} = MONO_KC[ci][{t}];")
                    continue
                inn = f"n{m.red.id}"
                e = f"rot31<{a.k}>({inn})"
                if a.neg: e = f"(ap_uint<31>)({e} ^ MONO_P31)"
                emit(f"    ap_uint<31> {name(a)} = {e};")
            ops = []
            for (a, j, neg) in n.ops:
                Wa = nbits(a.bound << j)
                if j == 0 and not neg: ops.append(f"(ap_uint<{W(n)}>){name(a)}"); continue
                tn = f"o{n.id}_{len(ops)}"
                emit(f"    ap_uint<{Wa}> {tn} = ((ap_uint<{Wa}>){name(a)}) << {j};")
                if neg:
                    emit(f"    ap_uint<{Wa}> {tn}n = ~{tn};"); tn += "n"
                ops.append(f"(ap_uint<{W(n)}>){tn}")
            return ops
          ops = add_ops(n)
          g = getattr(n, "guest", None)
          if g is not None:                                   # the Poseidon2 value this adder computes in a Poseidon2 issue
            Wh = W(n)
            if g.kind == "add":
                gops = [f"(ap_uint<{Wh}>){o}" for o in add_ops(g)]
            else:
                gs = g.src; Ws = W(gs)
                gops = [f"(ap_uint<{Wh}>){name(gs)}.range(30, 0)", f"(ap_uint<{Wh}>){name(gs)}.range({Ws - 1}, 31)"]
            # flat statements (Vitis's front end crashes on nested ?: with range casts inside)
            emit(f"    ap_uint<{Wh}> ga{n.id} = {gops[0]}; ap_uint<{Wh}> gb{n.id} = {gops[1]};")
            emit(f"    ap_uint<{Wh}> ha{n.id} = {ops[0]}; ap_uint<{Wh}> hb{n.id} = {ops[1]};")
            emit(f"    ap_uint<{Wh}> sa{n.id} = pos ? ga{n.id} : ha{n.id}; ap_uint<{Wh}> sb{n.id} = pos ? gb{n.id} : hb{n.id};")
            ops = [f"sa{n.id}", f"sb{n.id}"]
          if n.id in lendset:
                q = lent_here; lent_here += 1; lent_ids.append(n.id); LRANK.setdefault(b, []).append(lend_rank(n)); LENTQ[n.id] = q
                emit(f"    ap_uint<{W(n)}> n{n.id} = {LENDF}<{W(n)}>(ext, EA[{q}], EB[{q}], {ops[0]}, {ops[1]});")
                emit(f"    EY[{q}] = (word32_t)n{n.id}.range(31, 0);")
          else:
                emit(f"    ap_uint<{W(n)}> n{n.id} = alu_addp<{W(n)}>({ops[0]}, {ops[1]});")

    if b == SQD:
        # Bricks result -> state lanes (y_0 = x_0; y_{k+1} = x_{k+1} + x_k^2 reduced); the Concrete reads them from here on
        emit("    word32_t NY[16];")
        if P2:
            for k in range(16): emit(f"    NY[{k}] = f{YF[k].id};")
        else:
            emit("    NY[0] = X[0];")
            for k in range(15): emit(f"    NY[{k + 1}] = f{BRF[k].id};")
        emit("    for (int i = 0; i < 8; i++) {\n#pragma HLS UNROLL\n        M[" + str(BASE) + " + i] = pk(NY[2*i], NY[2*i+1]); }")
    # writes
    for n in bylevel[b]:
        if n.id in cur:
            for ln in put("M", off[b][n.id], W(n), name(n)): emit("    " + ln)
    def fold_tails(net):                                         # hosted folds: increment + canonicalisation from the stored 32-bit sums
        for g in net:
            Ws = W(g.src); hw = Ws - 31
            emit(f"    ap_uint<32> r{g.id} = n{g.host.id};")
            emit(f"    ap_uint<31> t{g.id} = alu_fold<{hw}>(r{g.id});")
            emit(f"    word32_t f{g.id} = alu_canon<word32_t>(t{g.id});")
    if P2 and b == LE:
        if HOST: fold_tails(EF)
        for i in range(8): emit(f"    M[{TAPE + i}] = pk(f{EF[2 * i].id}, f{EF[2 * i + 1].id});")
    if P2 and b == LI:
        if HOST: fold_tails(IF)
        for i in range(8): emit(f"    M[{TAPI + i}] = pk(f{IF[2 * i].id}, f{IF[2 * i + 1].id});")
    if b == D and not ONLY_P2:
        emit("    word32_t NP[16];")
        fo = {f.tag: f for f in folds}
        for p in range(16): emit(f"    NP[{p}] = f{fo[('out', p)].id};")
        emit("    for (int i = 0; i < 8; i++) {\n#pragma HLS UNROLL\n        M[" + str(BASE) + " + i] = pk(NP[2*i], NP[2*i+1]); }")
    emit("}")
    emit(f"static inline void monk_l{b}(const lane_t S[], ap_uint<{DECW}> dec, lane_t M[]) {{\n#pragma HLS INLINE\n    word32_t EA[MONO_LEND_MAX], EB[MONO_LEND_MAX], EY[MONO_LEND_MAX], XB[MONO_XLEND_MAX], XY[MONO_XLEND_MAX];\n    monk_lx{b}(S, dec, M, false, EA, EB, EY, XB, XY);\n}}")
    LENT[b] = lent_here
for b, want in LEND.items():
    assert LENT.get(b, 0) == want, f"level {b}: only {LENT.get(b, 0)} lendable adders, {want} requested"
DUMP = os.environ.get("MONO_DUMP", "")
if DUMP:
    import json
    chwset = set(n.id for n in chw)
    def srcid(a, consumer):
        # the Concrete reads the post-Bricks state: x_j (j >= 1) comes from the Bricks fold of element j
        if a.kind == "x": return BRF[a.j - 1].id if (consumer in chwset and 1 <= a.j <= len(BRF)) else a.id
        return a.id
    nodes, edges = [], []
    for n in d.hw:
        if n.kind in ("leaf",): continue
        nodes.append({"id": n.id, "kind": n.kind, "role": ROLE.get(n.id, n.kind), "level": lvl.get(n.id), "W": nbits(n.bound) if n.kind != "x" else 31,
                      "q": LENTQ.get(n.id), "tag": list(n.tag) if getattr(n, "tag", None) else None, "j": n.j if n.kind == "x" else None,
                      "c": (n.mul.c if (n.kind == "add" and n.mul is not None) else None), "mul": (n.mul.id if (n.kind == "add" and n.mul is not None) else None)})
        if n.kind == "add":
            for a, j, neg in n.ops:
                if a.kind == "leaf":
                    if a.const: edges.append({"src": None, "dst": n.id, "w": "const"}); continue
                    w = (f"rot{a.k}" if a.k else "") + ("~" if a.neg else "") + (f"<<{j}" if j else "") + (" -" if neg else "") + (" gated" if getattr(a, "sq2", False) else "")
                    edges.append({"src": srcid(a.src, n.id), "dst": n.id, "w": w.strip() or "wire"})
                else:
                    edges.append({"src": srcid(a, n.id), "dst": n.id, "w": ((f"<<{j}" if j else "") + (" -" if neg else "")).strip() or "wire"})
        elif n.kind in ("red", "pre", "fold"): edges.append({"src": srcid(n.src, n.id), "dst": n.id, "w": "lo31 + hi"})
        elif n.kind == "mulx": edges.append({"src": n.src.id, "dst": n.id, "w": "x * x"})
    json.dump({"D": D, "SQD": SQD, "BASE": BASE, "nodes": nodes, "edges": edges, "brf": [f.id for f in (YF if P2 else BRF)], "outs": [f.id for f in folds], "x": [n.id for n in xnodes]},
              open(DUMP, "w", encoding="utf-8"))
    print(f"netlist dump: {len(nodes)} nodes, {len(edges)} edges -> {DUMP}")
OUT = OUTNAME or "lane_mono_k6.inc"
TXT = "\n".join(L) + "\n"
if PREFIX != "monk": TXT = TXT.replace("monk_", PREFIX + "_")
if DEFPFX != "MONO":
    import re as _re
    TXT = _re.sub(r"\bMONO_", DEFPFX + "_", TXT)
open(os.path.join(HERE, OUT), "w", newline="\n").write(TXT)
print(f"{OUT} written: {D} levels, lanes {[lanes[b] for b in range(1, D + 1)]}, issues {NISS}")
print("lent adders per level: " + ", ".join(f"{b}: {LENT[b]}" for b in range(1, D + 1) if LENT.get(b, 0)))
