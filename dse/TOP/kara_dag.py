"""kara_dag.py - the Monolith-31 Concrete layer (16x16 circulant MDS over Mersenne31) as the Plonky3
Karatsuba conv16 (41 constant multiplications) lowered to a hardware DAG:
  * pre-adds (cyclic even/odd split, Karatsuba x0+x1) and post-adds as two-input adders on lazily
    reduced values; single-use intermediate sums are flattened into their consumer and every sum is a
    balanced tree ordered by operand readiness; negation is the bitwise complement of the operand
    (2^W-1-a), whose constant offset is folded into the round constants;
  * one fold+increment reduction (w[30:0] + w[34:31], then a 4-bit increment) in front of every
    constant multiplication, so the CSD digits become plain 31-bit rotations (complemented for -1);
  * outputs: fold (v[30:0] + v[39:31]), 9-bit increment, canonicalise (P -> 0).
build() -> Dag; finish(d, extra) builds the trees.  Running the file prints the analysis (adders,
depth, live registers per level for K adders per level, which outputs can carry the Bricks squares).
"""
import heapq, itertools, random, sys
P = (1 << 31) - 1
INV2 = (P + 1) // 2
ROW = [61402, 17845, 26798, 59689, 12021, 40901, 41351, 27521, 56951, 12034, 53865, 43244, 7454, 33823, 28750, 1108]


def csd(c):
    c %= P; d = []; b = 0
    while c:
        if c & 1:
            s = 2 - (c & 3); d.append((b % 31, s)); c -= s
        c >>= 1; b += 1
    return d


def nbits(b):
    return max(1, int(b).bit_length())


def rot(v, k):
    return ((v << k) | (v >> (31 - k))) & P if k else v


class Node:
    n = 0

    def __init__(self, kind, **kw):
        self.kind = kind; self.id = Node.n; Node.n += 1
        self.terms = kw.get("terms")        # sum (symbolic): [[coef, node], ...]
        self.src = kw.get("src")            # red / leaf / mul: source node
        self.c = kw.get("c")                # mul: constant
        self.k = kw.get("k", 0); self.neg = kw.get("neg", False)   # leaf: rotation / complement
        self.ops = kw.get("ops")            # add: [(node, shift, neg), (node, shift, neg)]
        self.j = kw.get("j")                # x: element; leaf: index inside the mult
        self.bound = kw.get("bound", 0); self.depth = 0
        self.mul = None                     # leaf / add inside a mult tree
        self.hw = None                      # symbolic sum / mul -> the hardware node holding its value
        self.ismul = False
        self.const = False

    def __repr__(self):
        return f"{self.kind}{self.id}"


# ---------------- symbolic construction ----------------
def S(terms):
    return Node("sum", terms=[list(t) for t in terms])


def conv_cyclic(xs, cs):
    n = len(xs)
    if n == 1:
        return [Node("mul", src=xs[0], c=cs[0] % P)]
    h = n // 2
    u = [S([(1, xs[i]), (1, xs[i + h])]) for i in range(h)]
    v = [S([(1, xs[i]), (-1, xs[i + h])]) for i in range(h)]
    cy = conv_cyclic(u, [(cs[i] + cs[i + h]) * INV2 % P for i in range(h)])
    nc = negacyclic(v, [(cs[i] - cs[i + h]) * INV2 % P for i in range(h)])
    return [S([(1, cy[i]), (1, nc[i])]) for i in range(h)] + [S([(1, cy[i]), (-1, nc[i])]) for i in range(h)]


def linear(xs, cs):
    n = len(xs)
    if n == 1:
        return [Node("mul", src=xs[0], c=cs[0] % P)]
    h = n // 2
    p0 = linear(xs[:h], cs[:h]); p1 = linear(xs[h:], cs[h:])
    p2 = linear([S([(1, xs[i]), (1, xs[i + h])]) for i in range(h)], [(cs[i] + cs[i + h]) % P for i in range(h)])
    res = [[] for _ in range(2 * n - 1)]
    for i in range(2 * h - 1):
        res[i].append((1, p0[i])); res[i + 2 * h].append((1, p1[i]))
    for i in range(2 * h - 1):
        res[i + h] += [(1, p2[i]), (-1, p0[i]), (-1, p1[i])]
    return [S(r) for r in res]


def negacyclic(xs, cs):
    n = len(xs)
    if n == 1:
        return [Node("mul", src=xs[0], c=cs[0] % P)]
    lin = linear(xs, cs)
    return [S([(1, lin[j]), (-1, lin[j + n])]) if j + n < 2 * n - 1 else S([(1, lin[j])]) for j in range(n)]


class Dag:
    pass


def _obound(o):
    n, j, neg = o
    b = n.bound << j
    return ((1 << nbits(b)) - 1) if neg else b


def _tree(hw, operands, mul=None):
    """balanced adder tree over (node, shift, neg) operands, earliest-ready first"""
    heap = [(o[0].depth, i, o) for i, o in enumerate(operands)]
    heapq.heapify(heap)
    cnt = len(heap)
    while len(heap) > 1:
        d1, _, a = heapq.heappop(heap); d2, _, b = heapq.heappop(heap)
        add = Node("add", ops=[a, b], bound=_obound(a) + _obound(b))
        add.depth = max(d1, d2) + 1; add.mul = mul
        hw.append(add); cnt += 1
        heapq.heappush(heap, (add.depth, cnt, (add, 0, False)))
    return heap[0][2][0]


def _opnd(coef, node):
    """(hwnode, shift, neg) operands of a symbolic term with coefficient +-2^j (others split)"""
    out = []; neg = coef < 0; a = -coef if neg else coef; j = 0
    while a:
        if a & 1: out.append((node.hw, j, neg))
        a >>= 1; j += 1
    return out


def build():
    Node.n = 0
    X = [Node("x", j=j, bound=P) for j in range(16)]
    xs = [X[(-j) % 16] for j in range(16)]              # reversed input: correlation -> convolution
    conv = conv_cyclic(xs, ROW)
    outs = [conv[(-i) % 16] for i in range(16)]         # out[i] = sum_k ROW[k] x[(i+k) % 16]
    seen, order = set(), []
    def visit(n):
        if n.id in seen: return
        seen.add(n.id)
        if n.kind == "sum":
            for _, t in n.terms: visit(t)
        elif n.kind == "mul":
            visit(n.src)
        order.append(n)
    for o in outs: visit(o)
    sums = [n for n in order if n.kind == "sum"]
    muls = [n for n in order if n.kind == "mul"]

    # ---- flatten: aliases, single-use sums inlined, coefficients merged ----
    def resolve(coef, n):
        while n.kind == "sum" and len(n.terms) == 1:
            coef *= n.terms[0][0]; n = n.terms[0][1]
        return coef, n
    changed = True
    while changed:
        changed = False
        for s in sums:
            s.terms = [list(resolve(c, t)) for c, t in s.terms]
        for m in muls:
            c, n = resolve(1, m.src)
            if n is not m.src: m.src = n; m.c = m.c * c % P; changed = True
        uses = {}
        for s in sums:
            for _, t in s.terms: uses[t.id] = uses.get(t.id, 0) + 1
        mulin = {m.src.id for m in muls}
        for s in sums:
            new = []
            for c, t in s.terms:
                if t.kind == "sum" and uses.get(t.id, 0) == 1 and t.id not in mulin and len(t.terms) > 1:
                    new += [[c * c2, t2] for c2, t2 in t.terms]; changed = True
                else:
                    new.append([c, t])
            merged = {}
            for c, t in new:
                merged[t.id] = [merged.get(t.id, [0, t])[0] + c, t]
            s.terms = [[c, t] for c, t in merged.values() if c]
            if len(s.terms) != len(new): changed = True
        alive = set()
        def mark(n):
            if n.id in alive: return
            alive.add(n.id)
            if n.kind == "sum":
                for _, t in n.terms: mark(t)
            elif n.kind == "mul": mark(n.src)
        for o in outs: mark(o)
        sums = [s for s in sums if s.id in alive]
    for o in outs:
        assert o.kind == "sum" and len(o.terms) >= 2

    # ---- lowering: inputs, pre-add sums, reductions, CSD leaves (trees are built in finish) ----
    hw = []
    for n in order:
        if n.kind == "x":
            n.hw = n; hw.append(n)
    def lower_sum(s):
        if s.hw is not None: return
        for _, t in s.terms:
            if t.kind == "sum": lower_sum(t)
        ops = []
        for c, t in s.terms:
            assert t.kind != "mul"
            ops += _opnd(c, t)
        s.hw = _tree(hw, ops)
    for m in muls:
        src = m.src
        if src.kind == "sum":
            lower_sum(src)
            red = Node("red", src=src.hw, bound=P); red.depth = src.hw.depth + 1
            hw.append(red)
        else:
            red = src.hw
        m.red = red; m.digits = csd(m.c); m.extra = []
        m.leaves = []
        for i, (k, sg) in enumerate(m.digits):
            lf = Node("leaf", src=red, k=k, neg=(sg < 0), bound=P, j=i); lf.depth = red.depth; lf.mul = m
            hw.append(lf); m.leaves.append(lf)
    d = Dag()
    d.X, d.outs_sym, d.sums, d.muls, d.order, d.hw = X, outs, sums, muls, order, hw
    d.pre = [n for n in hw if n.kind == "add"]
    return d


def finish(d, extra):
    """extra[m.id] = number of constant/injection leaves added to mult m; builds the mult trees and the
    post-add network; returns the output root nodes."""
    for m in d.muls:
        for lf in m.extra: d.hw.remove(lf)
        m.extra = []
        for i in range(extra.get(m.id, 0)):
            lf = Node("leaf", src=m.red, k=0, neg=False, bound=P, j=len(m.leaves) + i); lf.depth = m.red.depth
            lf.mul = m; lf.const = True; d.hw.append(lf); m.extra.append(lf)
    d.hw = [n for n in d.hw if n.kind != "add" or n in d.pre]
    for s in d.sums:
        if s.hw is not None and s.hw not in d.pre and s.hw.kind == "add": s.hw = None
    for m in d.muls:
        m.hw = _tree(d.hw, [(lf, 0, False) for lf in m.leaves + m.extra], mul=m)
        m.hw.ismul = True; m.hw.mulnode = m
    def lower_sum(s):
        if s.hw is not None: return
        for _, t in s.terms:
            if t.kind == "sum": lower_sum(t)
        ops = []
        for c, t in s.terms: ops += _opnd(c, t)
        s.hw = _tree(d.hw, ops)
    for s in d.sums: lower_sum(s)
    d.outs = [o.hw for o in d.outs_sym]
    d.hw.sort(key=lambda n: n.id)
    d.depth = max(o.depth for o in d.outs) + 1        # + output fold
    return d.outs


# ---------------- evaluation ----------------
def fold_red(v):
    r = (v & P) + (v >> 31)
    assert r < (1 << 31) + 16, "mult-input reduction bound"
    if r >> 31: assert (r & P) < 15
    return (r & P) + (r >> 31)


def fold_out(v):
    assert v < (1 << 40), "output fold bound"
    r = (v & P) + (v >> 31)
    if r >> 31: assert (r & P) < 511
    t = (r & P) + (r >> 31)
    return 0 if t == P else t


def evaluate(d, x, leafval=None):
    """hardware values of every node; leafval(leaf) overrides the CSD leaves (square issues)"""
    val = {}
    for n in d.hw:
        k = n.kind
        if k == "x": v = x[n.j]
        elif k == "red": v = fold_red(val[n.src.id])
        elif k == "leaf":
            if leafval is not None: v = leafval(n)
            else:
                v = 0 if n.const else rot(val[n.src.id], n.k)
                if n.neg: v = P - v
            assert 0 <= v <= P
        elif k == "add":
            v = 0
            for (a, j, neg) in n.ops:
                t = val[a.id] << j
                if neg:
                    W = nbits(a.bound << j); assert t < (1 << W); t = (1 << W) - 1 - t
                v += t
            assert v <= n.bound
        val[n.id] = v
    return val


def coefficients(d):
    """S[i][m.id]: integer coefficient of mult m's value in output i (post-add network)"""
    vec = {}
    def get(n):
        if n.id in vec: return vec[n.id]
        if n.ismul: r = {n.mulnode.id: 1}
        else:
            r = {}
            for (a, j, neg) in n.ops:
                for m, c in get(a).items():
                    r[m] = r.get(m, 0) + (-c if neg else c) * (1 << j)
        r = {m: c for m, c in r.items() if c}
        vec[n.id] = r
        return r
    return [get(o) for o in d.outs]


def analyse(d, K=2):
    """levels for K adders per level; nodes live across each register boundary"""
    lvl = {}
    for n in d.hw:
        if n.kind in ("add", "red"): lvl[n.id] = (n.depth + K - 1) // K
        elif n.kind == "x": lvl[n.id] = 0
        else: lvl[n.id] = None
    D = (d.depth + K - 1) // K                     # level of the output fold
    reads = {}
    def rd(n, L): reads.setdefault(n.id, set()).add(L)
    for n in d.hw:
        if n.kind == "add":
            for (a, j, neg) in n.ops:
                if a.kind == "leaf": rd(a.src, lvl[n.id])
                else: rd(a, lvl[n.id])
        elif n.kind == "red": rd(n.src, lvl[n.id])
    for o in d.outs: rd(o, D)
    live = {b: [] for b in range(1, D)}
    for n in d.hw:
        if n.kind in ("add", "red") and n.id in reads:
            for b in range(lvl[n.id], max(reads[n.id])):
                live[b].append(n)
    bitsb = {b: sum(nbits(n.bound) for n in live[b]) for b in live}
    return lvl, D, reads, live, bitsb


if __name__ == "__main__":
    d = build()
    outs = finish(d, {})
    adds = [n for n in d.hw if n.kind == "add"]
    reds = [n for n in d.hw if n.kind == "red"]
    leaves = [n for n in d.hw if n.kind == "leaf"]
    tadd = [n for n in adds if n.mul is not None]
    print(f"mults {len(d.muls)}, CSD leaves {len(leaves)}, tree adds {len(tadd)}, pre/post adds {len(adds) - len(tadd)}, "
          f"reductions {len(reds)}, output folds 16 -> adders total {len(adds) + len(reds) + 16}")
    wid = {}
    for n in adds + reds: wid[nbits(n.bound)] = wid.get(nbits(n.bound), 0) + 1
    print("adder result widths:", dict(sorted(wid.items())))
    print("max mult-input width", max(nbits(r.src.bound) for r in reds), " max output width", max(nbits(o.bound) for o in outs))
    print("adder depth (incl. output fold):", d.depth)
    rnd = random.Random(5)
    offs = None
    for t in range(4):
        x = [rnd.randrange(P) for _ in range(16)]
        val = evaluate(d, x)
        direct = [sum(ROW[k] * x[(i + k) % 16] for k in range(16)) % P for i in range(16)]
        o = [(fold_out(val[outs[i].id]) - direct[i]) % P for i in range(16)]
        assert offs is None or o == offs, "offset is not constant"
        offs = o
    print("Concrete offsets constant over x: OK")
    zero = evaluate(d, [0] * 16, leafval=lambda lf: 0)
    offsq = [fold_out(zero[outs[i].id]) for i in range(16)]
    print("square-issue offsets:", offsq[:4], "...")
    for K in (1, 2, 3):
        lvl, D, reads, live, bitsb = analyse(d, K)
        print(f"K={K}: levels {D}, live bits per boundary {[bitsb[b] for b in range(1, D)]}")
        print(f"      lanes {[8 + (bitsb[b] + 63) // 64 for b in range(1, D)]}, sum bits {sum(bitsb.values())}")
    S = coefficients(d)
    cap = {m.id: len(m.leaves) for m in d.muls}
    print("coefficient values:", sorted({c for row in S for c in row.values()}))
    print("mults per output:", [len(r) for r in S])
    for k in (5, 4, 3, 2):
        best = None
        for O in itertools.combinations(range(16), k):
            caps = []
            for i in O:
                el = [m for m, c in S[i].items() if c in (1, -1, 2, -2, 4, -4) and all(m not in S[i2] for i2 in O if i2 != i)]
                caps.append(sum(cap[m] for m in el))
            if best is None or min(caps) > best[0]: best = (min(caps), O, caps)
        print(f"{k} squares/issue: best outputs {best[1]} eligible leaf capacity {best[2]} (need 49 each)")
