"""cells.py - the register cells of one PE: every register word as R3 = op(sources of the previous level).
ARX (arx_steps.py on symbols): level s = 1..6 of a block group, word (block, lane, half); the sources of a level-s word
are words of level s-1 (level 0 = the input lanes). The op and the sources of a word depend on the primitive and the
traversal (r, CP); a word's cell is the set of its (sources, op) over all traversals of the primitive.
Monolith (kara_pkg.sv + mono_dp18.sv): level L = 1..18, registers with their width and their level L-1 sources."""
import os, re, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from arx_steps import step, schedule

# ---------------- ARX ----------------
class Sym:
    """a combinational expression over the previous level's words"""
    __slots__ = ("op", "args", "src")
    def __init__(self, op, args, src): self.op, self.args, self.src = op, args, src
    def key(self):
        return (self.op,) + tuple(a.key() if isinstance(a, Sym) else a for a in self.args)


class SymBE:
    @staticmethod
    def add(a, b): return Sym("add", (a, b), a.src | b.src)
    @staticmethod
    def xor(a, b): return Sym("xor", (a, b), a.src | b.src)
    @staticmethod
    def rotl(a, n): return Sym(f"rotl{n}", (a,), a.src) if n else a


def leaf(l, h): return Sym("reg", ((l, h),), frozenset([(l, h)]))


def arx_cells(prim, CP):
    """cells[s][(lane, half)] = {(sources, op key)} over the traversals of prim on block-group copy CP"""
    cells = {s: collections.defaultdict(set) for s in range(1, 7)}
    trav = [(c, r) for c, r in schedule(prim) if prim == "blake3" or c == CP]
    for _, r in trav:
        for s in range(1, 7):
            sv = [(leaf(l, 0), leaf(l, 1)) for l in range(22)]
            out = step(s, CP, sv, prim == "blake3", r, SymBE)
            for l in range(22):
                for h in range(2):
                    e = out[l][h]
                    cells[s][(l, h)].add((e.src, e.key()))
    return cells


# ---------------- Monolith ----------------
def mono_regs():
    """registers of one Monolith datapath: name -> (level, width, sources); sources are register names of level-1"""
    s = open(os.path.join(HERE, "..", "..", "src", "shared", "kara_pkg.sv")).read()
    tab = lambda name, w: [int(x, 16) for x in re.findall(rf"{w}'h([0-9a-f]+)",
                           s[s.index(f"{name} = {{"):s.index("};", s.index(f"{name} = {{"))])][::-1]
    node, mul, out = tab("NODE_TAB", 50), tab("MUL_TAB", 26), tab("OUT_TAB", 21)
    R = {}
    for i in range(16):                                           # L1..L4 (mono_dp18): xb1, xb2, xb3, br; L2-L3 squarer
        R[f"xb1.{i}"] = (1, 31, ("in",))
        R[f"xb2.{i}"] = (2, 31, (f"xb1.{i}",))
        R[f"xb3.{i}"] = (3, 31, (f"xb2.{i}",))
    for i in range(1, 16):
        R[f"sq1.{i}"] = (2, 124, (f"xb1.{i-1}",))                # stage-1 Dadda rows (4 x 31 bits, an estimate of the width)
        R[f"sq2.{i}"] = (3, 62, (f"sq1.{i}",))
    R["br.0"] = (4, 31, ("xb3.0",))
    for i in range(1, 16):
        R[f"br.{i}"] = (4, 31, (f"xb3.{i}", f"sq2.{i}"))
    F = lambda t, hi, lo: (t >> lo) & ((1 << (hi - lo + 1)) - 1)
    lvl = {}
    def at(nid, L):                                               # the register holding node nid at level L (delay stage)
        d = L - lvl[nid]
        return f"n{nid}" if d == 0 else f"n{nid}.d{d}"
    for nid, t in enumerate(node):
        kd, lv = F(t, 49, 47), F(t, 46, 42)
        if lv: lvl[nid] = lv
    redlv = {}
    for m, t in enumerate(mul):
        IN = F(t, 25, 16)
        redlv[m] = lvl[IN] + 1
        R[f"rq{m}"] = (lvl[IN] + 1, 31, (at(IN, lvl[IN]),))
    for nid, t in enumerate(node):
        kd, lv, w, A, B, life = F(t, 49, 47), F(t, 46, 42), F(t, 41, 36), F(t, 35, 26), F(t, 24, 15), F(t, 4, 0)
        if lv == 0 or kd == 5: continue
        if kd == 2:                                               # CSD leaf: wiring of rq A, registered delays if life
            lvl[nid] = lv
            for d in range(1, 4 if life >= 1 else 1):
                R[f"n{nid}.d{d}"] = (lv + d, 31, ((f"rq{A}" if d == 1 else f"n{nid}.d{d-1}"),))
            continue
        if kd == 0:
            srcs = (f"br.{A % 8}", f"br.{A % 8 + 8}")
        else:
            def operand(o):
                ko = F(node[o], 49, 47)
                if ko == 5: return None                           # constant K (selected by r, registered a level early)
                if ko == 2:                                       # a leaf: rq (same level as the leaf) or its delay
                    d = lv - 1 - lvl[o]
                    return f"rq{F(node[o], 35, 26)}" if d == 0 else f"n{o}.d{d}"
                return at(o, lv - 1)
            srcs = tuple(x for x in (operand(A), operand(B)) if x)
        R[f"n{nid}"] = (lv, w, srcs)
        for d in range(1, min(life, 3) + 1):
            R[f"n{nid}.d{d}"] = (lv + d, w, (f"n{nid}" if d == 1 else f"n{nid}.d{d-1}",))
    for i, t in enumerate(out):                                   # output folds, delayed to L18
        OID, OL = F(t, 20, 11), F(t, 10, 6)
        R[f"of{i}"] = (OL + 1, 31, (at(OID, OL),))
        for L in range(OL + 2, 19):
            R[f"of{i}.d{L}"] = (L, 31, (f"of{i}" if L == OL + 2 else f"of{i}.d{L-1}",))
    return R


if __name__ == "__main__":
    for prim in ("chacha", "blake3"):
        for CP in (0, 1):
            c = arx_cells(prim, CP)
            nsrc = collections.Counter()
            for s in c:
                for k, v in c[s].items():
                    nsrc[(len(v), max(len(x[0]) for x in v))] += 1
            print(prim, "CP", CP, "words x (distinct cells, max sources):", dict(sorted(nsrc.items())))
    R = mono_regs()
    bits = collections.Counter(); n = collections.Counter()
    for k, (L, w, src) in R.items(): bits[L] += w; n[L] += 1
    print("Monolith registers per level (bits):", [bits[L] for L in range(1, 19)], "total", sum(bits.values()))
