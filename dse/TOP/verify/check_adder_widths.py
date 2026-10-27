"""Static check: every adder the bz generator emits has a width W that holds the worst-case sum of its operands,
so the W-bit result is the exact integer sum (no wrap); every reduction (lo31 + hi) fits 32 bits; the end-around fold
alu_fold<H> is exact for all inputs; lent adders are >= 32 bits so the ARX side gets (a + b) mod 2^32.
Runs gen_lane_mono6.py with build_bz.sh's options (output to scratch) and inspects its node graph."""
import os, sys, runpy, random, re
TOP = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SCR = os.path.dirname(os.path.abspath(__file__))
os.environ.update(MONO_SQMUL="1", MONO_P2="1", MONO_P2_MUL3="1", MONO_P2_A1="1", MONO_LEND_ANY="1", MONO_LEND_RED="1",
                  MONO_LEND_MOD="1", MONO_BASE="1188",
                  MONO_LEND="2:12,3:12,4:12,5:16,6:28,7:56,8:72,9:72,10:64,11:40,12:28,13:12,14:4,15:4,16:8,17:8,18:8",
                  MONO_OUT=os.path.join(SCR, "chk_lane_mono_kl.inc"))
sys.path.insert(0, TOP)
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    g = runpy.run_path(os.path.join(TOP, "gen_lane_mono6.py"), run_name="gen")
nbits = g["nbits"]; P = (1 << 31) - 1
def obound(o):
    n, j, neg = o; b = n.bound << j
    return ((1 << nbits(b)) - 1) if neg else b
nodes = {}
for lst in (g["d"].hw, g["sqnodes"], g["p2nodes"]):
    for n in lst: nodes[n.id] = n
for n in list(nodes.values()):
    gg = getattr(n, "guest", None)
    if gg is not None: nodes[gg.id] = gg
bad = []; cnt = {}; widths = {}
for n in nodes.values():
    k = n.kind; cnt[k] = cnt.get(k, 0) + 1
    if k == "add":
        worst = sum(obound(o) for o in n.ops)
        W = nbits(n.bound); widths[W] = widths.get(W, 0) + 1
        if worst > n.bound: bad.append(("add bound < worst-case operand sum", n.id, worst, n.bound))
        if worst >= (1 << W): bad.append(("add overflows its width", n.id, W, worst))
        gst = getattr(n, "guest", None)
        if gst is not None:                                  # hosted Poseidon2 value computed on this W-bit adder
            gw = sum(obound(o) for o in gst.ops) if gst.kind == "add" else P + (1 << (nbits(gst.src.bound) - 31)) - 1
            if gw >= (1 << W): bad.append(("guest overflows host width", n.id, W, gw))
    if k in ("red", "fold", "pre", "pf"):
        Ws = nbits(n.src.bound) if k in ("red", "fold") else 62
        hw = Ws - 31
        if not (1 <= hw <= 31): bad.append(("reduction high part width", n.id, Ws))
        if P + (1 << hw) - 1 >= (1 << 32): bad.append(("lo31 + hi exceeds 32 bits", n.id, Ws))
    if k == "fold":
        Ws = nbits(n.src.bound); hw = Ws - 31
        if not (1 <= hw <= 30): bad.append(("fold H out of range", n.id, hw))
# alu_fold<H> exactness: r = lo + hi (lo < 2^31, hi < 2^H); C code: t[30:H] = r[30:H], t[H-1:0] = (r[H-1:0] + r[31]) mod 2^H.
# Claim t == lo + hi - r[31] * (2^31 - 1) (i.e. the M31 end-around carry, exact, no lost carry). Proof by the bound
# r[31] = 1 -> r - 2^31 <= 2^H - 2, then checked on the extremes and random values for every H in use.
def c_fold(r, H):
    lowmask = (1 << H) - 1
    hi_part = r & (((1 << 31) - 1) & ~lowmask)
    return hi_part | (((r & lowmask) + (r >> 31)) & lowmask)
Hs = sorted(set(nbits(n.src.bound) - 31 for n in nodes.values() if n.kind == "fold"))
for n in nodes.values():                                     # the red nodes fold with alu_fold<4>: exact iff hi < 2^4, i.e. src width <= 35
    if n.kind == "red" and nbits(n.src.bound) - 31 > 4: bad.append(("red fold<4> may lose a carry", n.id, nbits(n.src.bound)))
Hs = sorted(set(Hs) | {4})
rnd = random.Random(1); nfold = 0
for H in Hs:
    his = [0, 1, (1 << H) - 1, (1 << H) - 2] + [rnd.randrange(1 << H) for _ in range(2000)]
    los = [0, 1, P - 1, P, P - (1 << H) + 1] + [rnd.randrange(1 << 31) for _ in range(2000)]
    for lo in los:
        for hi in his[:6] + rnd.sample(his, 20):
            r = lo + hi; t = c_fold(r, H); nfold += 1
            if t != r - (r >> 31) * P or t > P or (t % P) != (lo + hi) % P: bad.append(("fold", H, lo, hi)); break
# lent adders in the emitted file: width >= 32, ARX gets the low 32 bits
src = open(os.environ["MONO_OUT"]).read()
lw = [int(w) for w in re.findall(r"alu_lend<(\d+)>", src)]
if min(lw) < 32: bad.append(("lent adder narrower than 32", min(lw)))
ey_ok = len(re.findall(r"EY\[\d+\] = \(word32_t\)", src))
same = open(os.path.join(TOP, "bz", "lane_mono_kl.inc")).read() == src
print("nodes by kind:", dict(sorted(cnt.items())))
print("M31 adder widths (bits: count):", dict(sorted(widths.items())))
print(f"fold H values in use {Hs}, {nfold:,} fold cases checked")
print(f"lent adders {len(lw)}, widths {sorted(set(lw))}, EY low-32 writes {ey_ok}; regenerated file identical to bz/lane_mono_kl.inc: {same}")
print("VIOLATIONS:", len(bad)); [print("  ", b) for b in bad[:20]]
