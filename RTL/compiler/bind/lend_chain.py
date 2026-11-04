"""lend_chain.py - the lend binding of the shared unit's Monolith datapath (kara_pkg LEND_TAB): which of the PE's 216 ARX
adders each lent Monolith adder uses, chosen so that the ARX operand path itself delivers one operand.

The Monolith programs run the ARX controls of BLAKE3 (blake = 1, r = 0). Then, in every block and sum word w, the ARX adder
of step 2 reads the sum of step 1 (lane 16 / 17, the same cycle), step 5 reads the sum of step 4, and step 5 / 6 read the
sum of step 2 / 3 two levels later (arx_steps.py, traced below). A Monolith adder C that reads adder P directly (delay 0,
not complemented) is placed at step 2 (5) with P at step 1 (4) of the same block and word: C's operand from P is the
ARX operand (no lend select on it). Likewise a read with delay 2 at steps 2 -> 5, 3 -> 6.
The lent set: the matched pairs (narrowest first), then the narrowest other adders up to 216. Positions: a pair at
(1, 2) or (4, 5), whichever leaves fewer delays without an ARX move (pe_map lfree); the others at steps 3 and 6 (delays
first at step 3).
    python3 lend_chain.py            -> prints the LEND_TAB entries (entry NN-1 first) and the counts
"""
import os, re, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from arx_steps import step
from cells import SymBE, leaf, Sym

src = open(os.path.join(HERE, "..", "..", "src", "shared", "kara_pkg.sv")).read()
T = [int(v, 16) for v in re.findall(r"50'h([0-9a-f]+)", re.search(r"NODE_TAB = \{(.*?)\};", src, re.S).group(1))][::-1]
NN = len(T)
N = [dict(kind=t >> 47, L=(t >> 42) & 31, W=(t >> 36) & 63, A=(t >> 26) & 1023, nA=(t >> 25) & 1, B=(t >> 15) & 1023,
          nB=(t >> 14) & 1, life=t & 31) for t in T]
isadd = lambda n: n["L"] != 0 and n["kind"] not in (2, 5)
ADD = [i for i, n in enumerate(N) if isadd(n)]

# ---- the ARX operand sources under the Monolith controls: (consumer step, word) <- (producer step, word, delay) ----
def word(e): return e.args[0] if isinstance(e, Sym) and e.op == "reg" else None
class TagBE(SymBE):                                         # records the adds of a step in call order: sum w = EY[w]
    adds = []
    @staticmethod
    def add(a, b):
        e = SymBE.add(a, b); TagBE.adds.append(e); return e
def sources(CP):
    outs, tags = {}, {}
    for s in range(1, 7):
        sv = [(leaf(l, 0), leaf(l, 1)) for l in range(22)]
        TagBE.adds = []
        outs[s] = step(s, CP, sv, True, 0, TagBE)
        tags[s] = list(TagBE.adds)
        assert len(tags[s]) == 4
    def origin(s, w):                                       # level-s word w: the sum it is a (moved) copy of
        d = 0
        while s >= 1:
            e = outs[s][w[0]][w[1]]
            for k, t in enumerate(tags[s]):
                if e is t: return s, k, d
            w = word(e)
            if w is None: return None
            s -= 1; d += 1
        return None
    res = {}
    for s in range(2, 7):
        for k, e in enumerate(tags[s]):
            for side, a in zip("ab", e.args):
                w = word(a)
                o = origin(s - 1, w) if w else None
                if o: res[(s, k, side)] = o
    return res
S0, S1 = sources(0), sources(1)
SRC = {k: v for k, v in S0.items() if S1.get(k) == v}       # the same in both block-group copies
assert SRC == S0 == S1, "the operand sources differ between the copies"
LINKS = sorted({(v[0], k[0], v[2], k[2]) for k, v in SRC.items() if v[1] == k[1]})   # (prod step, cons step, delay, side)
assert all(v[1] == k[1] for k, v in SRC.items()), "a source changes the sum word"

# ---- candidate pairs ----
def reads(c, d):
    n = N[c]
    if n["kind"] == 0: return []
    out = []
    for side in "AB":
        p = n[side]
        if 0 <= p < NN and isadd(N[p]) and n["n" + side] == 0 and n["L"] - N[p]["L"] - 1 == d and p != c: out.append(p)
    return out
E0 = [(p, c) for c in ADD for p in reads(c, 0)]
taken, PAIRS = set(), []
for p, c in sorted(E0, key=lambda e: (N[e[0]]["W"] + N[e[1]]["W"], e)):
    if p not in taken and c not in taken: PAIRS.append((p, c)); taken |= {p, c}
NCOL = 9 * 4                                                # columns: (block, sum word)
PAIRS = PAIRS[:2 * NCOL]
lent = {i for pc in PAIRS for i in pc}
E2 = [(p, c) for c in ADD for p in reads(c, 2)]             # delay-2 reads: step 3 -> step 6 of a column
PAIRS2 = []
for p, c in sorted(E2, key=lambda e: (N[e[0]]["W"] + N[e[1]]["W"], e)):
    if p not in lent and c not in lent and max(N[p]["W"], N[c]["W"]) <= 33 and len(PAIRS2) < NCOL:
        PAIRS2.append((p, c)); lent |= {p, c}
for i in sorted(ADD, key=lambda i: (N[i]["W"], i)):
    if len(lent) >= 216: break
    lent.add(i)

def nonfree(i, s):                                          # delays of a lent sum at step s without an ARX move
    life = N[i]["life"]
    free = {1: 1, 2: 2, 3: 2, 4: 2, 5: 1, 6: 0}[s]
    return max(0, life - free) * N[i]["W"]

# ---- positions: ld = group base + (s - 1) * 4 nb + b * 4 + w; columns (g, b, w) ----
cols = [(0, b, w) for b in range(5) for w in range(4)] + [(1, b, w) for b in range(4) for w in range(4)]
def ld_of(g, s, b, w): return (0 if g == 0 else 120) + (s - 1) * 4 * (5 if g == 0 else 4) + b * 4 + w
pos = {}
free_pairs = [(c, lo) for c in cols for lo in (1, 4)]
order = sorted(PAIRS, key=lambda pc: -abs((nonfree(pc[0], 1) + nonfree(pc[1], 2)) - (nonfree(pc[0], 4) + nonfree(pc[1], 5))))
for p, c in order:
    best = min(free_pairs, key=lambda cl: nonfree(p, cl[1]) + nonfree(c, cl[1] + 1))
    free_pairs.remove(best)
    (g, b, w), lo = best
    pos[p], pos[c] = ld_of(g, lo, b, w), ld_of(g, lo + 1, b, w)
for k, (p, c) in enumerate(PAIRS2):                         # a delay-2 pair: step 3 and step 6 of column k
    g, b, w = cols[k]
    pos[p], pos[c] = ld_of(g, 3, b, w), ld_of(g, 6, b, w)
rest = sorted(lent - set(pos), key=lambda i: (-N[i]["life"], i))
assert not free_pairs and not PAIRS2, "the leaf placement below assumes every step 1/2/4/5 position holds a pair"
# the rest at steps 3 (the nodes with delays: free there) and 6. A node C there whose operand X is a plain leaf (delay 0,
# no complement) of reduction m gets m's register in the ARX operand word of its position (step 3 / 6: level 2 / 5,
# lane 2 / 6, half w % 2), rotated by the leaf's amount: then X is the ARX operand (no lend select). One word per
# reduction (max bipartite matching); a step-6 word only where the column's step-3 sum has no second delay (that delay
# is the same word, ldpos).
S3, S6 = rest[:36], rest[36:]
assert all(N[i]["life"] == 0 for i in S6)
def leafops(i):
    out = []
    for side in "AB":
        p = N[i][side]
        if p < NN and N[p]["kind"] == 2 and N[i]["L"] - N[p]["L"] - 1 == 0 and not N[i]["n" + side] and not N[p]["nA"]:
            out.append((side, N[p]["A"], N[p]["B"]))
    return out
mt = {}                                                     # reduction m -> (node, side, rotation)
def aug(i, seen):
    for side, m, rot in leafops(i):
        if m in seen: continue
        seen.add(m)
        if m not in mt or aug(mt[m][0], seen): mt[m] = (i, side, rot); return True
    return False
for i in sorted(rest, key=lambda i: (len(leafops(i)), i)): aug(i, set())
lm = {v[0]: (m, v[1], v[2]) for m, v in mt.items()}        # node -> (reduction, side, rotation)
m6 = [i for i in S6 if i in lm]
ok3 = sorted([i for i in S3 if N[i]["life"] < 2], key=lambda i: i)
while len(m6) > len(ok3): del lm[m6.pop()]                  # not enough step-3 partners without a second delay
oth3 = [i for i in S3 if i not in ok3[:len(m6)]]
cols3 = cols                                               # column k: step-3 node, step-6 node
pair36 = list(zip(ok3[:len(m6)], m6)) + list(zip(oth3, [i for i in S6 if i not in m6]))
assert len(pair36) == 36
for (g, b, w), (n3, n6) in zip(cols3, pair36):
    pos[n3], pos[n6] = ld_of(g, 3, b, w), ld_of(g, 6, b, w)
assert len(pos) == 216 and len(set(pos.values())) == 216

# ---- matched operands: the ARX path delivers operand X of lent node C ----
def step_w(ld):
    q, nb = (ld, 5) if ld < 120 else (ld - 120, 4)
    return q // (4 * nb) + 1, (q // 4) % nb, q % 4, 0 if ld < 120 else 1
match = {}
for c, ldc in pos.items():
    s, b, w, g = step_w(ldc)
    for side in "AB":
        p = N[c][side]
        if N[c]["kind"] == 0 or N[c]["n" + side] or p not in pos: continue
        d = N[c]["L"] - N[p]["L"] - 1
        sp, bp, wp, gp = step_w(pos[p])
        if (gp, bp, wp) == (g, b, w) and any(l[0] == sp and l[1] == s and l[2] == d for l in LINKS):
            match.setdefault(c, set()).add(side)
nlink = sum(len(v) for v in match.values())
# the leaf matches: OPW_TAB, one entry per operand word of a PE (lane index oi = group base 0 / 20 + 4 b + 2 (level 5) +
# (lane 6), word ow = 2 oi + half): {used, reduction m[5:0], rotation[4:0]}
opw = [0] * 72
for i, (m, side, rot) in lm.items():
    s, b, w, g = step_w(pos[i])
    assert s in (3, 6)
    oi = (0 if g == 0 else 20) + 4 * b + (2 if s == 6 else 0) + (1 if w >= 2 else 0)
    opw[2 * oi + w % 2] = 1 << 11 | m << 5 | rot
    match.setdefault(i, set()).add(side)
nm = sum(len(v) for v in match.values())
print(f"// links {LINKS}", file=sys.stderr)
print(f"// pairs {len(PAIRS)}, matched operands {nm} ({nlink} sums, {len(lm)} leaves: {len([i for i in lm if i in S3])} "
      f"at step 3), lent widths {collections.Counter(N[i]['W'] for i in lent)}, "
      f"delays without a move (bits) {sum(nonfree(i, step_w(pos[i])[0]) for i in pos)}", file=sys.stderr)
ent = []
for i in range(NN):
    ld = pos.get(i, 511)
    m = match.get(i, set())
    ent.append(("B" in m) << 10 | ("A" in m) << 9 | ld)
lines = []
for k in range(NN - 1, -1, -8):
    lines.append("        " + ", ".join(f"11'h{ent[j]:03x}" for j in range(k, max(k - 8, -1), -1)))
print("LEND_TAB")
print(",\n".join(lines))
print("OPW_TAB")
print(",\n".join("        " + ", ".join(f"12'h{opw[j]:03x}" for j in range(k, max(k - 8, -1), -1)) for k in range(71, -1, -8)))
