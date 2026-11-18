import ctypes, heapq, math, os, random, sys
REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
VER = os.path.join(REPO, "model", "verify")
sys.path.insert(0, VER)
from models import *

DLL, REQ = os.path.abspath(sys.argv[1]), sys.argv[2]
lib = ctypes.CDLL(DLL)
info = lib.lp_info
NB, NIO, BASE, BL, MERKLE_ONLY, COLOC, NG, NLV = info(1), info(9), info(10), info(11), info(12), info(13), info(14), info(15)
BB = [info(1000 + 2 * j) for j in range(NB)]
HB = [info(1001 + 2 * j) for j in range(NB)]
BG = [info(2000 + j) for j in range(NB)]
GD = [info(3000 + g) for g in range(NG)]
GL0 = [info(3200 + g) for g in range(NG)]
GBLK = [[j for j in range(NB) if BG[j] == g] for g in range(NG)]
GLO = [min(BB[j] for j in GBLK[g]) for g in range(NG)]
GHI = [max(BB[j] + (18 if j < COLOC else BL) for j in GBLK[g]) for g in range(NG)]
GS0 = [info(4000 + g) for g in range(NG)]
GCH = [info(4100 + g) for g in range(NG)]
CH = []
for g in range(NG):
    while len(CH) <= GCH[g]: CH.append([])
    CH[GCH[g]].append(g)
for c in CH: c.sort(key=lambda g: GS0[g])
DM = info(6); KM = DM + 1
NDP = info(18) or 1; BASES = [BASE] + ([info(17)] if NDP == 2 else [])
P2 = info(19) == 1
if P2:
    from pos2_prog import P2Prog, P2ProgPacked, P2ProgMul3, P2ProgMul3A1, mono_issue_lanes, words as p2words, lanes as p2lanes
    MUL3 = info(28) == 1
    if info(29) == 1: P2ProgMul3 = P2ProgMul3A1
    if info(30):
        from pos2_prog import P2ProgEng
        P2ProgMul3 = P2ProgEng
    P2CODES = {"SQD": info(20), "LE": info(21), "LI": info(22), "R_SQ": info(23), "R_INIT": info(24), "R_X5E": info(25), "R_X5I": info(26)}
    MONO_IN = mono_issue_lanes
else:
    MONO_IN = mono_lanes
NENG = info(30) if P2 else 0
if NENG: EBASE, ELAT = info(31), info(32)
NISS = {1: 14, 2: 14, 4: info(0)}
RV = lambda x: x | 256 if x == 13 else x
ARR = ctypes.c_uint64 * NIO
IG = ctypes.c_int * NG
stepx = lib.lp_step_x
stepx.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, IG, ARR, ARR]
if NENG:
    IEN = ctypes.c_int * NENG
    stepe = lib.lp_step_e
    stepe.argtypes = [ctypes.c_int] * 6 + [IG, IEN, ARR, ARR]
rnd = random.Random(2026 + int(next((a[5:] for a in sys.argv[5:] if a.startswith("seed=")), "0")))
NOROOT = "noroot" in sys.argv[5:]
LEAVES_F = next((a[7:] for a in sys.argv[5:] if a.startswith("leaves=")), "")
LEAVES_IT = (ln.split() for ln in open(LEAVES_F)) if LEAVES_F else None
ROOTOUT_F = next((a[8:] for a in sys.argv[5:] if a.startswith("rootout=")), "")
GL0, GJ0 = (int(x) for x in next((a[6:] for a in sys.argv[5:] if a.startswith("gbase=")), "0:0").split(":"))
SEEDIN_F = next((a[7:] for a in sys.argv[5:] if a.startswith("seedin=")), "")
LEAFOUT_F = next((a[8:] for a in sys.argv[5:] if a.startswith("leafout=")), "")
CC_CONST = [0x61707865, 0x3320646e, 0x79622d32, 0x6b206574]
MNAME = {1: "BLAKE3", 2: "ChaCha20", 4: "Monolith-31", 5: "Poseidon2-M31"}
LEAD = 2

class Node:
    __slots__ = ("id", "kind", "prim", "level", "idx", "kids", "parent", "mparent", "result", "done", "root", "res", "cons", "wr", "nw", "freed", "tk", "nwr", "rinf", "pw", "paddr")
    def __init__(s, id, kind, prim, level, idx):
        s.id, s.kind, s.prim, s.level, s.idx, s.kids, s.parent, s.mparent, s.result, s.done, s.root = id, kind, prim, level, idx, [], None, None, None, False, False
        s.pw, s.paddr = False, None
        s.res = s.cons = s.wr = s.nw = s.freed = s.tk = False
        s.rinf = False
        s.nwr = 0
    @property
    def needs_h(s): return s.kind == "g" and s.prim == 1

def build_merkle(log2n, prim, nodes):
    leaves = []
    for i in range(1 << log2n):
        nd = Node(len(nodes), "leaf", prim, 0, i); nd.done = True
        nd.result = [rnd.randrange(P) for _ in range(8)] if prim in (4, 5) else [rnd.getrandbits(32) for _ in range(8)]
        if LEAVES_IT: nd.result = [int(x, 16) for x in next(LEAVES_IT)]
        nodes.append(nd); leaves.append(nd)
    return build_merkle_over(leaves, prim, nodes)

def build_merkle_over(leaves, prim, nodes):
    level, parents, lv = leaves, [], 0
    while len(level) > 1:
        lv += 1; nxt = []
        for i in range(0, len(level), 2):
            p = Node(len(nodes), "m", prim, lv, i // 2); p.kids = [level[i], level[i + 1]]
            level[i].mparent = p; level[i + 1].mparent = p
            nodes.append(p); nxt.append(p); parents.append(p)
        level = nxt
    level[0].root = True
    return parents, level[0]

def build_forest_merkle(k, m, prim, nodes):
    level, parents = [], []
    for i in range(1 << (k + m)):
        nd = Node(len(nodes), "leaf", prim, 0, i); nd.done = True
        nd.result = [rnd.randrange(P) for _ in range(8)] if prim in (4, 5) else [rnd.getrandbits(32) for _ in range(8)]
        if LEAVES_IT: nd.result = [int(x, 16) for x in next(LEAVES_IT)]
        nodes.append(nd); level.append(nd)
    for lv in range(1, k + 1):
        nxt = []
        for i in range(0, len(level), 2):
            p = Node(len(nodes), "m", prim, lv, i // 2); p.kids = [level[i], level[i + 1]]
            level[i].mparent = p; level[i + 1].mparent = p
            nodes.append(p); nxt.append(p); parents.append(p)
        level = nxt
    for x in level: x.root = True
    return parents, level

def build_forest_ggm(k, m, prim, nodes):
    roots = []
    for tt in range(1 << m):
        r_ = Node(len(nodes), "g", prim, m, tt); r_.result = [rnd.getrandbits(32) for _ in range(8)]; r_.done = True
        if SEEDIN_F: r_.result = [int(x, 16) for x in open(SEEDIN_F).read().split("\n")[GJ0 + tt].split()]
        nodes.append(r_); roots.append(r_)
    frontier = roots
    for lv in range(m + 1, m + k + 1):
        nxt = []
        for p in frontier:
            for c in range(2):
                nd = Node(len(nodes), "g", prim, lv, 2 * p.idx + c); nd.parent = p; p.kids.append(nd); nodes.append(nd); nxt.append(nd)
        frontier = nxt
    return roots, frontier

def gcoord(nd):
    l = nd.level - CUT; j = nd.idx & ((1 << l) - 1) if CUT else nd.idx
    return j + (GJ0 << l), l + GL0

def build_open(log2n, prim, q, K, nodes, proof_base):
    n = 1 << log2n
    val = [[([rnd.randrange(P) for _ in range(8)] if prim in (4, 5) else [rnd.getrandbits(32) for _ in range(8)]) for _ in range(n)]]
    for l in range(1, log2n + 1):
        val.append([merkle_fn(prim, val[l - 1][2 * j], val[l - 1][2 * j + 1], l == log2n) for j in range(n >> l)])
    qs = sorted(random.Random(7 + q).sample(range(n), q))
    path = {(l, i >> l) for i in qs for l in range(log2n + 1)}
    need = {(l, (i >> l) ^ 1) for i in qs for l in range(log2n)} - path
    need |= {(0, i) for i in qs}
    made, parents, seq = {}, [], [0]
    def get(l, j, compute):
        if (l, j) in made: return made[(l, j)]
        if l == 0: compute = False
        if not compute:
            nd = Node(len(nodes), "leaf", prim, l, j); nd.done = True; nd.result = val[l][j]; nodes.append(nd)
        else:
            nd = Node(len(nodes), "m", prim, l, j); nodes.append(nd)
            on = (l, j) in path
            nd.kids = [get(l - 1, 2 * j + c, compute=(l - 1, 2 * j + c) in path or (not on) or (1 <= l - 1 <= K and (l - 1, 2 * j + c) in need)) for c in (0, 1)]
            for k in nd.kids: k.mparent = nd
            parents.append(nd)
        if (l, j) in need: nd.pw = True; nd.paddr = proof_base + 32 * seq[0]; seq[0] += 1
        made[(l, j)] = nd
        return nd
    root = get(log2n, 0, True); root.root = True
    assert root.result is None and val[log2n][0] is not None
    inputs = [nd for nd in nodes if nd.kind == "leaf"]
    return parents, root, val[log2n][0], inputs, len(need)

def build_ggm(depth, prim, nodes):
    root = Node(len(nodes), "g", prim, 0, 0); root.result = [rnd.getrandbits(32) for _ in range(8)]; root.done = True
    if SEEDIN_F: root.result = [int(x, 16) for x in open(SEEDIN_F).read().split("\n")[GJ0].split()]
    nodes.append(root); frontier = [root]
    for lv in range(1, depth + 1):
        nxt = []
        for p in frontier:
            for c in range(2):
                nd = Node(len(nodes), "g", prim, lv, 2 * p.idx + c); nd.parent = p; p.kids.append(nd); nodes.append(nd); nxt.append(nd)
        frontier = nxt
    return root, frontier

def merkle_fn(prim, l, r, is_root):
    if prim == 4: return mono(l + r)[:8]
    if prim == 5: return pos2(l + r)[:8]
    return compress16(IV, l + r, 0, 64, PARENT | (ROOT if is_root else 0))[:8]

def ggm_fn(prim, seed, level, idx):
    if prim == 2: o = cc_block(CC_CONST + seed + [idx & M32, (idx >> 32) & M32, level, 0])
    else: o = compress16(seed, [idx & M32, (idx >> 32) & M32, level] + [0] * 13, 0, 64, KEYED_HASH | CHUNK_START | CHUNK_END | ROOT)
    return o[:8], o[8:16]

def node_in(nd):
    if nd.kind == "m":
        l, r = nd.kids[0].result, nd.kids[1].result
        if nd.prim in (4, 5): return MONO_IN(l + r), None
        L = b3_lanes(IV, l + r, 0, 64, PARENT | (ROOT if nd.root and not NOROOT else 0), 22); return L[:18], L[18:22]
    gi, gl = gcoord(nd)
    if nd.prim == 2: return cc_lanes(CC_CONST + nd.result + [gi & M32, (gi >> 32) & M32, gl, 0], 18), None
    L = b3_lanes(nd.result, [gi & M32, (gi >> 32) & M32, gl] + [0] * 13, 0, 64, KEYED_HASH | CHUNK_START | CHUNK_END | ROOT, 22)
    return L[:18], L[18:22]

def out_words(lanes, prim):
    if prim in (4, 5): return mono_words(lanes)
    return cc_words(lanes) if prim == 2 else b3_words(lanes)

nodes = []
ready = {1: [], 2: [], 4: [], 5: []}
_seq = 0
def rkey(nd):
    if nd.prim in (4, 5): return (-nd.level, nd.idx) if ORDER == "deep" else (0,)
    return (0 if nd.kind == "m" else 1, (nd.level if ORDER == "fifo" else -nd.level), nd.idx)
def rpush(nd):
    global _seq; _seq += 1; heapq.heappush(ready[nd.prim], (rkey(nd), _seq, nd))
roots, work_total, MSLOTS, ORDER = [], 0, 0, "deep"
NT = int(next((a[1:] for a in sys.argv[5:] if a.startswith("x")), "1"))
TOPL = int(next((a[3:] for a in sys.argv[5:] if a.startswith("top")), "8"))
ORDER = next((a for a in sys.argv[5:] if a in ("deep", "fifo")), "deep")
PACK = "nopack" not in sys.argv[5:] and not (P2 and MUL3)
MEMSIM = any(a.startswith("sram=") for a in sys.argv[5:])
OPENREQ = REQ == "open"
if OPENREQ:
    REQ = "merkle"
    OPENQ = int(next((a[2:] for a in sys.argv[5:] if a.startswith("q=")), "64"))
    _st = next((a[6:] for a in sys.argv[5:] if a.startswith("store=")), "all")
    OPENK = int(_st[1:]) if _st.startswith("k") else 0
    PROOF_BASE = 512 << 20
BATCH = MEMSIM and NT > 1
CUT = 0
if BATCH:
    assert NT & (NT - 1) == 0 and not OPENREQ, "a batch with the memory model: xT with T a power of two, commit only"
    CUT = NT.bit_length() - 1
if REQ == "merkle":
    prim = {"blake3": 1, "mono": 4, "pos2": 5}[sys.argv[3]]; SZ = int(sys.argv[4])
    assert prim != 5 or P2, "this unit has no Poseidon2 issues"
    if BATCH:
        parents, rts_ = build_forest_merkle(SZ, CUT, prim, nodes); roots += rts_; work_total += len(parents); SZ += CUT
    for _ in range(0 if BATCH else NT):
        if OPENREQ:
            parents, root, OPEN_ROOT, OPEN_INPUTS, OPEN_PROOF = build_open(SZ, prim, OPENQ, OPENK, nodes, PROOF_BASE); roots.append(root)
            for p_ in parents:
                if all(k.kind == "leaf" for k in p_.kids) and not MEMSIM: rpush(p_)
        else:
            parents, root = build_merkle(SZ, prim, nodes); roots.append(root)
            for p_ in parents:
                if p_.level == 1 and not MEMSIM: rpush(p_)
        work_total += len(parents)
    MSLOTS = (48 if (prim == 5 and PACK) else 64 if (prim == 5 and NENG) else KM) if prim in (4, 5) else 0
    def top(nd): return nd.level > SZ - TOPL
elif REQ == "ggm":
    prim = {"blake3": 1, "chacha": 2}[sys.argv[3]]; SZ = int(sys.argv[4])
    if BATCH:
        groots, leaves = build_forest_ggm(SZ, CUT, prim, nodes); work_total += NT * ((1 << SZ) - 1); SZ += CUT
    for _ in range(0 if BATCH else NT):
        groot, leaves = build_ggm(SZ, prim, nodes); work_total += (1 << SZ) - 1
        if not MEMSIM: rpush(groot)
    if not BATCH: groots = [groot]
    GDEPTH = {prim: SZ}
    def top(nd): return nd.level <= TOPL
else:
    sys.exit(f"unknown request '{REQ}': a program is one Merkle or one GGM request of one primitive (see usage)")
GDEPTH = globals().get("GDEPTH", {})
LTOP = SZ - CUT
BLAKE = 1 if prim in (1, 4) else 0
NCH = len(CH)
ALT = prim == 2
assert not (MSLOTS and any(ready[p] for p in (1, 2))), "a program holds either Monolith states or ARX blocks, never both"

if MEMSIM:
    from collections import deque
    assert NT == 1 or BATCH
    SRAM_KB = float(next(a[5:] for a in sys.argv[5:] if a.startswith("sram=")))
    BW = float(next((a[3:] for a in sys.argv[5:] if a.startswith("bw=")), "256"))
    HCH = int(next((a[4:] for a in sys.argv[5:] if a.startswith("hbm=")), "0"))
    GCH = int(next((a[5:] for a in sys.argv[5:] if a.startswith("gddr=")), "0"))
    HKIND = "gddr" if GCH > 0 else "hbm"
    HCH = HCH or GCH
    HBMSIM = HCH > 0
    if HBMSIM:
        sys.path.insert(0, os.path.join(REPO, "memsim"))
        import hbm as hbmlib
        HMAP = next((a[5:] for a in sys.argv[5:] if a.startswith("hmap=")), "RoBaRaCoCh")
        HPORT = int(next((a[6:] for a in sys.argv[5:] if a.startswith("hport=")), str(HCH)))
        HLAY = next((a[5:] for a in sys.argv[5:] if a.startswith("hlay=")), "block")
        HNBL = int(next((a[5:] for a in sys.argv[5:] if a.startswith("hnbl=")), "2"))
        HBMX = hbmlib.GDDR6(HCH, HMAP, HNBL) if HKIND == "gddr" else hbmlib.HBM(HCH, HMAP, HNBL)
        BW = float(HBMX.peak)
    rsent = {}; rlat = [0, 0, 0]
    REC = next((a[4:] for a in sys.argv[5:] if a.startswith("rec=")), "")
    BGF = next((a[3:] for a in sys.argv[5:] if a.startswith("bg=")), "")
    rec_log = []
    BG = []
    if BGF:
        fn, nb = BGF.rsplit(":", 1)
        trc = [(int(l[0]), int(l[1]), int(l[2])) for l in (ln.split() for ln in open(fn))]
        BG = [[deque(trc), 0, (k + 1) << 26] for k in range(int(nb))]
    BGTAG = 1 << 40
    POLICY = next((a[7:] for a in sys.argv[5:] if a.startswith("policy=")), "auto")
    ROWB = 1024
    HBLK = (ROWB // 32 + 2).bit_length() - 2
    if prim in (1, 2):
        P_L = max(sum(GD[g] + 1 for g in sp) for sp in CH) * NISS[prim]
        P_TH = sum(len(GBLK[sp[0]]) for sp in CH) / NISS[prim]
        P_W = sum(len(GBLK[sp[0]]) * sum(GD[g] + 1 for g in sp) for sp in CH)
    else:
        P_L, P_TH, P_W = KM * NISS[4], len(BASES) / NISS[4], 2 * MSLOTS
    P_R = BW * HBMX.SUSTAINED if HBMSIM else BW
    P_RT = HBMX.rt_cycles if HBMSIM else 0
    P_TURN = HBMX.turn_cycles if HBMSIM else 0
    P_WD = HBMX.wdrain_cycles if HBMSIM else 0
    P_CAP = int(SRAM_KB * 1024) // 32
    P_C = ((1 << SZ) - 1) / P_TH
    def p_dram(K):
        wr = 32 * ((1 << (SZ - K)) - (1 if REQ == "merkle" else 2))
        return (32 * (1 << SZ) + wr) / P_R + (wr / ROWB * P_TURN if REQ == "merkle" else 0)
    P_K = next((K for K in range(SZ) if p_dram(K) <= P_C), SZ - 1)
    def g_res(tk): return (2 << tk) - 1 + (LTOP - tk)
    def g_ws(tk, K):
        sub = ((1 << tk) - 1) / P_TH
        n_open = tk * P_L / sub
        occ = (1 << tk) + 1 + (((1 << (tk - K)) - 1) if tk > K else 0)
        ahead = (LTOP - tk) * P_L / sub
        return n_open * occ + ahead + g_res(tk)
    if REQ == "merkle":
        rho = 32 * P_TH / P_R
        tk_win = (math.ceil(math.log2(P_TH * P_RT / (1 - rho))) - 1 if P_RT else 0) if rho < 1 else SZ
        tk_cap = max(1, (P_CAP - P_W).bit_length() - 2)
        P_TK = max(1, min(max(tk_win, math.ceil(math.log2(P_W)) + 1), tk_cap))
    else:
        cand = range(1, max(2, LTOP))
        P_TK = next((tk for tk in cand if g_ws(tk, P_K) <= P_CAP), min(cand, key=lambda tk: g_ws(tk, P_K)))
    AUTO = POLICY == "auto" and not OPENREQ
    STORE = next((a[6:] for a in sys.argv[5:] if a.startswith("store=")), ("all" if P_K == 0 else f"k{P_K}") if AUTO else "all")
    TILE_ARG = next((a[5:] for a in sys.argv[5:] if a.startswith("tile=")), None)
    if AUTO:
        print(f"  policy auto: theta {P_TH:.3f} nodes/cycle, L {P_L}, W {P_W}, DRAM {P_R:.1f} B/cycle, SRAM {P_CAP} slots -> "
              f"store={STORE}, tile={TILE_ARG or P_TK}" + (" (given)" if TILE_ARG else ""))
    if OPENREQ: STORE = "out"
    KSK = int(STORE[1:]) if STORE.startswith("k") else (0 if STORE == "all" else 1 << 30)
    def stored(l):
        if REQ == "merkle": return l == LTOP or (1 <= l < LTOP and l > KSK)
        return l == 0 or KSK < l < LTOP
    CAP = int(SRAM_KB * 1024) // 32
    AUDIT = "audit" in sys.argv[5:]
    RTOP = int(next((a[3:] for a in sys.argv[5:] if a.startswith("top") and a[3:].isdigit()), "0"))
    def resident(x): return RTOP > 0 and lam(x) > SZ - RTOP
    if REQ == "merkle":
        TK = max(1, min(SZ, int(TILE_ARG or (P_TK if AUTO else (CAP // 4).bit_length() - 1)))); WT = 2
    WIN = int(next((a[4:] for a in sys.argv[5:] if a.startswith("win=")), str((1 << 20) if OPENREQ else 1)))
    GSCHED = next((a[7:] for a in sys.argv[5:] if a.startswith("gsched=")), "dfs")
    WFLY = (2 * MSLOTS) if prim in (4, 5) else sum(len(GBLK[spans[0]]) * sum(GD[g] + 1 for g in spans) for spans in CH)
    AHEAD = int(next((a[6:] for a in sys.argv[5:] if a.startswith("ahead=")), "0"))
    INORD = next((a[8:] for a in sys.argv[5:] if a.startswith("inorder=")), "tdeep")
    GATE = next((a[5:] for a in sys.argv[5:] if a.startswith("gate=")), "res")
    MORD = next((a[5:] for a in sys.argv[5:] if a.startswith("mord=")), "dfs")
    if REQ == "merkle": pass
    elif GSCHED == "dfs":
        WT = int(next((a[3:] for a in sys.argv[5:] if a.startswith("wt=")), "2"))
        TK = max(1, min(SZ, int(TILE_ARG or (P_TK if AUTO else 4 if GATE == "res" else (CAP // (2 * WT)).bit_length() - 1))))
        LAFIX = AHEAD
    else:
        TK = max(1, min(SZ, int(next((a[5:] for a in sys.argv[5:] if a.startswith("tile=")), "6")), (CAP // 8).bit_length() - 1))
        WT = 0
    def tile_of(nd):
        if REQ == "merkle": return (((nd.idx + 1) << nd.level) - 1) >> TK
        return (nd.idx << (SZ - nd.level)) >> TK
    BOOST = int(next((a[6:] for a in sys.argv[5:] if a.startswith("boost=")), "8"))
    def rkey(nd):
        h = max(0, (SZ - TK) - nd.level) if REQ == "ggm" else 0
        if REQ == "merkle" and MORD == "bfs": return (tile_of(nd), nd.level, nd.idx)
        if REQ == "ggm" and GSCHED == "dfs" and INORD == "tdeep":
            return (-1, tile_of(nd), -nd.level) if h else (0, tile_of(nd), -nd.level)
        if REQ == "ggm" and GSCHED == "dfs" and INORD == "deep":
            return (-(1 << 20), tile_of(nd), -nd.level) if h else (-nd.level, tile_of(nd), nd.idx)
        if REQ == "ggm" and GSCHED == "dfs" and INORD == "fifo":
            return (1, tile_of(nd), 0) if nd.level == SZ - TK else (0, _seq, 0)
        if REQ == "ggm" and GSCHED == "dfs": return (tile_of(nd) - (AHEAD if h else 0), nd.level if INORD == "bfs" else -nd.level, nd.idx)
        return (tile_of(nd) - BOOST * h, -nd.level, nd.idx)
    used = used_max = 0; hbm_rd = hbm_wr = 0; dma_cycles = 0; racc = wacc = 0.0
    fly = wpend = 0; brk_max = (0, 0, 0); brk_sum = [0, 0, 0]; brk_n = 0
    from collections import OrderedDict
    OROWS = int(next((a[6:] for a in sys.argv[5:] if a.startswith("orows=")), "32"))
    LAYOUTS = ("level", "tile", "block")
    def lam(nd): return nd.level if REQ == "merkle" else SZ - nd.level
    def blocks_in_band(b):
        top = 1 + (b + 1) * HBLK
        return (1 << (SZ - top)) if top <= SZ else 1
    BANDB = [0]
    for b in range((SZ - 1) // HBLK + 1): BANDB.append(BANDB[-1] + blocks_in_band(b) * ROWB)
    LMF = next((a[8:] for a in sys.argv[5:] if a.startswith("leafmap=")), "")
    LEAFMAP = [int(x) for x in open(LMF).read().split()] if LMF else None
    LMK = (SZ - (len(LEAFMAP).bit_length() - 1)) if LEAFMAP else 0
    def addr(layout, l, j):
        if l == 0: return (LEAFMAP[j >> LMK] + (j & ((1 << LMK) - 1)) * 32) if LEAFMAP else j * 32
        base = -(-(1 << SZ) * 32 // ROWB) * ROWB
        if layout == "level": return base + ((1 << SZ) - (1 << (SZ - l + 1)) + j) * 32
        if layout == "tile":
            tk = min(TK, SZ)
            if l <= tk:
                t = j >> (tk - l); w = (1 << tk) - (1 << (tk - l + 1)) + (j & ((1 << (tk - l)) - 1))
                return base + (t * ((1 << tk) - 1) + w) * 32
            return base + ((1 << (SZ - tk)) * ((1 << tk) - 1) + (1 << (SZ - tk)) - (1 << (SZ - l + 1)) + j) * 32
        b = (l - 1) // HBLK; top = 1 + (b + 1) * HBLK; d = top - l
        anc = j >> d if top <= SZ else 0
        return base + BANDB[b] + anc * ROWB + ((1 << d) - 2 + (j - (anc << d))) * 32
    class Rows:
        def __init__(s): s.o, s.act = OrderedDict(), 0
        def touch(s, row):
            if row in s.o: s.o.move_to_end(row); return
            s.act += 1; s.o[row] = 1
            if len(s.o) > OROWS: s.o.popitem(last=False)
    WROWS = {L: Rows() for L in LAYOUTS}; RROWS = Rows()
    rq, wq = deque(), deque()
    cur_tile = 0; tile_left = {}
    ADM = float(next((a[4:] for a in sys.argv[5:] if a.startswith("adm=")), "0.5"))
    open_hi, open_budget = -1, 0
    def gopen(tl):
        if GSCHED == "dfs" and GATE == "res": return True
        return tl < cur_tile + WT if (GSCHED == "dfs" and GATE == "wt") else admit(tl)
    SGATE = next((a[6:] for a in sys.argv[5:] if a.startswith("sgate=")), "0")
    LAGE = next((a[5:] for a in sys.argv[5:] if a.startswith("lage=")), "min")
    LAH = next((a[4:] for a in sys.argv[5:] if a.startswith("lah=")), "max")
    tstart = {}; tdone = []
    LRATE = next((a[6:] for a in sys.argv[5:] if a.startswith("lrate=")), "meas")
    def la(nd):
        if LAFIX: return LAFIX
        h = (SZ - TK) - nd.level if LAH == "node" else LTOP - TK
        age = TK * LMAX if LAGE == "min" else max(t - tstart.get(cur_tile, t), TK * LMAX)
        rate = THETA / ((1 << TK) - 1)
        if LRATE == "meas" and len(tdone) > 1:
            win = TK * LMAX + (SZ - TK) * LMAX; k = len(tdone) - 1
            while k > 0 and t - tdone[k - 1] <= win: k -= 1
            if t - tdone[k] > 0: rate = min(rate, (len(tdone) - 1 - k) / max(1, t - tdone[k]))
        return max(1, int(rate * (age + h * LMAX)) + 1)
    la_rng = [1 << 30, 0]
    def lawin(nd):
        w = la(nd); la_rng[0] = min(la_rng[0], w); la_rng[1] = max(la_rng[1], w); return w
    hold = {}; hold_max = [0, 0]
    def hkey(x): return tile_of(x) if REQ == "ggm" and lam(x) <= TK else -1
    def hadd(x, v):
        k = hkey(x); hold[k] = hold.get(k, 0) + v
        if v > 0:
            i = 1 if k < 0 else 0; hold_max[i] = max(hold_max[i], hold[k])
    def groom(nd):
        RES = g_res(TK)
        stack = REQ == "ggm" and nd.level < SZ - TK and SGATE == "w2"
        ok = used + gneed(nd) <= (CAP if tile_of(nd) <= cur_tile else CAP - RES - (2 * WFLY if stack else 0))
        if used + gneed(nd) > CAP: refused[0] = True
        return ok
    def admit(tl):
        global open_hi, open_budget
        while open_hi < tl and open_budget + (1 << TK) <= int(CAP * ADM):
            open_hi += 1; open_budget += 1 << TK
        return open_hi >= tl
    if REQ == "merkle":
        if OPENREQ:
            for j in range(1 << (SZ - TK)): tile_left[j] = 0
        for lf in sorted((k for p_ in nodes if p_.kind == "m" for k in p_.kids if k.kind == "leaf"), key=lambda x: (tile_of(x), -x.level, x.idx)):
            rq.append(lf); tile_left[tile_of(lf)] = tile_left.get(tile_of(lf), 0) + 1
    else:
        rq.extend(groots)
        for j in range(1 << (SZ - TK)): tile_left[j] = 1 << TK
    def seed_wait(x):
        if REQ != "ggm" or not CUT or tile_of(x) <= cur_tile: return False
        RES = g_res(TK)
        ahead = la(x) + math.ceil((P_WD + P_RT) * THETA / ((1 << TK) - 1))
        return tile_of(x) > cur_tile + ahead or used + 1 > CAP - RES - 2 * WFLY
    HANDIN = "handin" in sys.argv[5:]
    handq = deque(rq) if HANDIN else deque(); handed = set(); hand_n = len(handq); hand_st = [0, not HANDIN]
    def mem_free(x):
        global used
        if x.cons and (not x.nw or x.wr) and not x.freed and not resident(x):
            used -= 1; x.freed = True
            if AUDIT: hadd(x, -1)
    def peak():
        global used_max, brk_max
        if used > used_max: used_max = used; brk_max = (fly, wpend, used - fly - wpend)
    def chk():
        assert used <= CAP, f"SRAM over capacity: {used} > {CAP} at cycle {t}"
    def gneed(nd):
        return 2 - (1 if (not nd.nw or nd.wr) and not resident(nd) else 0)
    def mroom(nd, delay=0):
        fr = sum(1 for k in nd.kids if (not k.nw or k.wr) and not resident(k) and not (k.pw and not k.wr))
        ok = used + 1 - (min(fr, 1) if delay else fr) <= CAP
        if not ok: refused[0] = True
        return ok
    pend_free = {}
    def pop_fit(h):
        side, nd = [], None
        while h:
            e = heapq.heappop(h)
            if mroom(e[2]): nd = e[2]; break
            side.append(e)
        for e in side: heapq.heappush(h, e)
        return nd
    def mem_take(nd, delay=0):
        global used, cur_tile, fly, wpend
        fly += 1 if nd.kind == "m" else 2
        if REQ == "ggm" and nd.level == SZ - TK: tstart.setdefault(tile_of(nd), t)
        if AUDIT:
            if nd.kind == "m": assert all(k.res and not k.freed for k in nd.kids) and not nd.tk, "Merkle parent issued without both children on chip"
            else: assert nd.res and not nd.freed and not any(k.tk for k in nd.kids), "GGM node issued without its seed on chip"
        if nd.kind == "m": nd.tk = True
        else:
            for k in nd.kids:
                k.tk = True
                if AUDIT: hadd(k, 1)
        if nd.kind == "m":
            took = False
            for k in nd.kids:
                k.cons = True
                if k.pw and k.kind == "leaf" and not k.nw: k.nw = True; wpend += 1; wq.append(k)
                if delay and (not k.nw or k.wr) and not resident(k):
                    if took: pend_free.setdefault(t + delay, []).append(k)
                    else: took = True; mem_free(k)
                else: mem_free(k)
                if k.kind == "leaf": tile_left[tile_of(k)] -= 1
            while tile_left.get(cur_tile, 1) == 0: cur_tile += 1
            used += 1; peak()
        else:
            nd.cons = True; mem_free(nd); used += 2
        peak()
        if AUDIT: chk()
    STAGE = "stage=0" not in sys.argv[5:]
    stage = {}; staged = 0; partial_rows = 0
    rheld = set(); lastw = [-(1 << 30)]
    ddir = ["r"]; wburst = [0]
    def dram_order(hand_wait):
        rd = bool(rq) and not hand_wait and not seed_wait(rq[0]) and used + 1 <= CAP and not (REQ == "merkle" and tile_of(rq[0]) > cur_tile + WIN)
        if rq and not hand_wait and used + 1 > CAP: refused[0] = True
        if ddir[0] == "w" and (not wq or wburst[0] <= 0): ddir[0] = "r"
        if rheld: rd = True
        if ddir[0] == "r" and wq and not rd: ddir[0] = "w"; wburst[0] = len(wq)
        return (rq,) if ddir[0] == "r" else (wq,)
    flushed = set()
    refused = [False]; relief_n = [0]
    def relief():
        global staged, partial_rows
        if refused[0] and not wq and stage:
            kf = max(stage, key=lambda kk: len(stage[kk]) / row_full(lam(stage[kk][0])))
            g = stage.pop(kf); wq.extend(sorted(g, key=lambda y: addr("block", lam(y), y.idx))); staged -= len(g); partial_rows += 1; flushed.add(kf); relief_n[0] += 1
        refused[0] = False
    def row_full(l):
        if l == 0: return min(ROWB // 32, 1 << SZ)
        b = (l - 1) // HBLK; top = 1 + (b + 1) * HBLK
        if top <= SZ: return sum(1 << d for d in range(1, HBLK + 1) if stored(top - d))
        return sum(1 << (SZ - l2) for l2 in range(b * HBLK + 1, SZ + 1) if stored(l2))
    def mem_out(x, store):
        global fly, wpend, staged, partial_rows
        if AUDIT: assert x.tk and x.res, "result without a reserved slot"
        x.nw = store; fly -= 1; wpend += store
        if store and STAGE and (STORE != "out" or lam(x) == 0):
            k = addr("block", lam(x), x.idx) // ROWB
            if k in flushed: wq.append(x); mem_free(x); return
            g = stage.setdefault(k, [])
            g.append(x); staged += 1
            if len(g) == row_full(lam(x)): wq.extend(sorted(stage.pop(k), key=lambda y: addr("block", lam(y), y.idx))); staged -= len(g)
        elif store: wq.append(x)
        mem_free(x)
    def dma():
        global racc, wacc, used, used_max, hbm_rd, hbm_wr, dma_cycles, open_budget, wpend, brk_max, brk_n
        b = BW; act = False
        relief()
        while handq and b >= 32: b -= 32; handed.add(handq.popleft().id); act = True; hand_st[0] = t; hand_st[1] = not handq
        for q in dram_order(bool(HANDIN and rq and rq[0].id not in handed)):
            while q and b > 0:
                x = q[0]
                if q is rq and seed_wait(x): break
                if q is rq and used + 1 > CAP: refused[0] = True
                if q is rq and (used + 1 > CAP or (REQ == "merkle" and tile_of(x) > cur_tile + WIN) or (HANDIN and x.id not in handed)): break
                acc = racc if q is rq else wacc
                if b < 32 - acc:
                    acc += b; b = 0; act = True
                    if q is rq: racc = acc
                    else: wacc = acc
                    break
                b -= 32 - acc; act = True; q.popleft()
                if q is rq:
                    if AUDIT: assert not x.res, "read twice"
                    racc = 0; hbm_rd += 32; used += 1; x.res = True; peak()
                    if AUDIT: hadd(x, 1)
                    if AUDIT: chk()
                    RROWS.touch(addr("level", lam(x), x.idx) // ROWB)
                    if REQ == "merkle":
                        if all(k.res for k in x.mparent.kids): rpush(x.mparent)
                    else: rpush(x)
                else:
                    if AUDIT: assert x.res and x.nw and not x.wr, "write of a value not computed / not to be written / twice"
                    wacc = 0; hbm_wr += 32; x.wr = True; x.nwr += 1; mem_free(x); wpend -= 1; wburst[0] -= 1
                    for L in LAYOUTS: WROWS[L].touch(addr(L, lam(x), x.idx) // ROWB)
                    if REQ == "ggm" and x.level == SZ: open_budget -= 1
        brk = (fly, wpend, used - fly - wpend)
        for i in range(3): brk_sum[i] += brk[i]
        brk_n += 1
        used_max = max(used_max, used); dma_cycles += act
        if AUDIT and t % 997 == 0:
            n_ = sum(1 for x in nodes if (x.res or x.tk or x.rinf) and not x.freed)
            assert n_ == used, f"SRAM count {used} != {n_} slots held by node states at cycle {t}"
    def dma_hbm():
        global used, used_max, hbm_rd, hbm_wr, dma_cycles, open_budget, wpend, brk_n
        n = 0; act = False
        relief()
        for bgq in BG:
            bq, lag, off = bgq; k = 0
            while bq and bq[0][0] + lag <= t and k < HPORT:
                if HBMX.send(bq[0][1] + off, bq[0][2] == 1, BGTAG): bq.popleft(); k += 1
                else: bgq[1] += 1; break
        while handq and n < HPORT:
            x = handq[0]
            if not HBMX.send(addr(HLAY if x.level and REQ == "merkle" else "level", lam(x), x.idx), True, BGTAG): break
            handq.popleft(); handed.add(x.id); n += 1; act = True
        for q in dram_order(not hand_st[1]):
            while q and n < HPORT:
                x = q[0]
                if q is rq:
                    if seed_wait(x): break
                    if used + 1 > CAP: refused[0] = True
                    if used + 1 > CAP or (REQ == "merkle" and tile_of(x) > cur_tile + WIN) or not hand_st[1]: break
                    a = addr(HLAY if x.level and REQ == "merkle" else "level", lam(x), x.idx)
                    if not HBMX.send(a, False, x.id): break
                    if AUDIT: assert not x.res and not x.rinf, "read twice"
                    q.popleft(); n += 1; act = True
                    if REC: rec_log.append((t, a, 0))
                    used += 1; x.rinf = True; rsent[x.id] = t; peak()
                    if t - lastw[0] <= P_WD: rheld.add(x.id)
                    if AUDIT: hadd(x, 1); chk()
                    RROWS.touch(a // ROWB)
                else:
                    wa = x.paddr if x.paddr is not None else addr(HLAY, lam(x), x.idx)
                    if not HBMX.send(wa, True, x.id): break
                    if AUDIT: assert x.res and x.nw and not x.wr, "write of a value not computed / not to be written / twice"
                    q.popleft(); n += 1; act = True
                    if REC: rec_log.append((t, wa, 1))
                    hbm_wr += 32; x.wr = True; x.nwr += 1; mem_free(x); wpend -= 1; wburst[0] -= 1; lastw[0] = t
                    for L in LAYOUTS: WROWS[L].touch(addr(L, lam(x), x.idx) // ROWB)
                    if REQ == "ggm" and x.level == SZ: open_budget -= 1
        for tag in HBMX.tick():
            if tag >= BGTAG: continue
            x = nodes[tag]; x.rinf = False; x.res = True; hbm_rd += 32; rheld.discard(tag)
            d = t + 1 - rsent.pop(tag); rlat[0] += 1; rlat[1] += d; rlat[2] = max(rlat[2], d)
            if REQ == "merkle":
                if all(k.res for k in x.mparent.kids): rpush(x.mparent)
            else: rpush(x)
        if not hand_st[1] and not handq and HBMX.cmd("WR") + HBMX.cmd("WRA") >= hand_n:
            hand_st[0] = t; hand_st[1] = True
        brk = (fly, wpend, used - fly - wpend)
        for i in range(3): brk_sum[i] += brk[i]
        brk_n += 1
        used_max = max(used_max, used); dma_cycles += act or bool(rsent) or not hand_st[1]
        if AUDIT and t % 997 == 0:
            n_ = sum(1 for x in nodes if (x.res or x.tk or x.rinf) and not x.freed)
            assert n_ == used, f"SRAM count {used} != {n_} slots held by node states at cycle {t}"

mslots = [[None] * KM for _ in BASES]
mused = [0] * len(BASES)
rings = []
for spans in CH:
    Ks = [GD[g] + 1 for g in spans]; cs = [sum(Ks[:i]) for i in range(len(spans))]
    rings.append({"K": sum(Ks), "spans": spans, "c": cs, "slots": [None] * sum(Ks), "blocks": GBLK[spans[0]], "lblocks": GBLK[spans[-1]],
                  "lo": GLO[spans[0]], "hi": GHI[spans[0]], "llo": GLO[spans[-1]], "lhi": GHI[spans[-1]]})
plan = [{} for _ in rings]
if MEMSIM:
    LMAX = max(R["K"] for R in rings) * NISS[prim] if prim in (1, 2) else KM * NISS[4]
    THETA = (sum(len(R["blocks"]) for R in rings) / NISS[prim]) if prim in (1, 2) else (len(BASES) / NISS[4])
prog = []
live, live_max = 0, 0
live_top, live_top_max, hbm_bytes = 0, 0, 0
mem_reads = mem_writes = 0
prev = [0] * NIO
t = 0
usehchain = bool(COLOC) and MSLOTS == 0
pprog = [[] for _ in BASES]
pack = [{"members": [], "stage": 0, "due": None} for _ in BASES]
busy = lambda: any(pprog) or any(s is not None for ring in mslots for s in ring) or any(s is not None for R in rings for s in R["slots"]) or any(p for p in plan) or (MEMSIM and bool(rq or wq or rsent))

def pick(n, allow_h):
    grp, prims = [], (1, 2)
    i = 0
    while i < n:
        if MEMSIM and REQ == "ggm" and used + 1 > CAP: refused[0] = True; break
        cand = None
        for prim in prims:
            side = []
            while ready[prim]:
                if MEMSIM and REQ == "ggm" and ready[prim][0][2].level >= SZ - TK and not gopen(tile_of(ready[prim][0][2])): break
                e = heapq.heappop(ready[prim])
                if e[2].needs_h and not allow_h[i]: side.append(e); continue
                if MEMSIM and REQ == "merkle" and not mroom(e[2], LEAD): side.append(e); continue
                if MEMSIM and REQ == "ggm" and GSCHED == "dfs" and GATE == "res" and not groom(e[2]): side.append(e); continue
                if MEMSIM and REQ == "ggm" and used + gneed(e[2]) > CAP: refused[0] = True; side.append(e); continue
                if MEMSIM and REQ == "ggm" and GSCHED == "dfs" and INORD in ("fifo", "deep", "tdeep") and e[2].level < SZ - TK and tile_of(e[2]) > cur_tile + lawin(e[2]): side.append(e); continue
                cand = (prim, e); break
            for e in side: heapq.heappush(ready[prim], e)
            if cand: break
        if cand is None: break
        grp.append(cand[1][2]); i += 1
        if MEMSIM: mem_take(cand[1][2], LEAD)
        prims = (cand[0],)
    return grp

def finish(nd, o):
    global live, live_top, hbm_bytes, cur_tile
    if nd.kind == "m":
        nd.result = o[:8]; nd.done = True; live += 1
        if top(nd): live_top += 1
        else: hbm_bytes += 32
        p = nd.mparent
        if MEMSIM:
            nd.res = True
            if nd.root: nd.cons = True
            mem_out(nd, stored(lam(nd)) or nd.root or nd.pw)
        if p is not None and all((k.res if MEMSIM else k.done) for k in p.kids): rpush(p)
    else:
        k0, k1 = nd.kids
        k0.result, k1.result = o[:8], o[8:16]; k0.done = k1.done = True; live += 2
        for kk in (k0, k1):
            if kk.level < GDEPTH[nd.prim] and top(kk): live_top += 1
            elif kk.level < GDEPTH[nd.prim]: hbm_bytes += 32
            else: hbm_bytes += 32
        if MEMSIM:
            for kk in (k0, k1):
                kk.res = True; leaf = kk.level == GDEPTH[nd.prim]
                if leaf: kk.cons = True; tile_left[kk.idx >> TK] -= 1
                mem_out(kk, stored(lam(kk)))
            while tile_left.get(cur_tile, 1) == 0: cur_tile += 1; tdone.append(t)
        if k0.level < GDEPTH[nd.prim]: rpush(k1); rpush(k0)
        elif k0.mparent is not None: rpush(k0.mparent)

OPENONLY = MEMSIM and "openonly" in sys.argv[5:]
TRACE_F = next((a[6:] for a in sys.argv[5:] if a.startswith("trace=")), "")
TRF = open(TRACE_F, "w") if TRACE_F else None
if TRF: TRF.write(f"H {NIO} {NG}" + chr(10))
tr_cp, tr_fr, tr_ck = [], [], []
def T_CP(dlo, n, slo):
    if TRF: tr_cp.append((dlo, n, slo))
def T_FR(lo, vals):
    if TRF: tr_fr.append((lo, list(vals)))
def T_CK(lo, n, mode):
    if TRF: tr_ck.append((lo, n, mode, [prev[lo + i] for i in range(n)]))
while (any(ready.values()) or busy()) and not OPENONLY:
    rec = {"t": t, "mono": 0, "issue": [], "mem": [], "fin": [], "memm": [], "finm": []}
    if MEMSIM:
        for x in pend_free.pop(t, []): mem_free(x)
        dma_hbm() if HBMSIM else dma()
    lanes = [0] * NIO
    rg = [0] * NG; mono_now = [0] * len(BASES); r = [0] * len(BASES)
    for d, B in enumerate(BASES):
        j = t % KM; s = mslots[d][j]
        if s is not None:
            if s["r"] + 1 < NISS[4]:
                s["r"] += 1; mono_now[d] = 1; r[d] = s["r"]; lanes[B:B + 8] = prev[B:B + 8]; T_CP(B, 8, B)
                if P2: lanes[B:B + 24] = mono_issue_lanes(mono_words(prev[B:B + 8]))
                rec["issue"].append(("PIPE", f"M{d}", s["r"], [s["node"].id]))
            else:
                T_CK(B, 8, 1); finish(s["node"], out_words(prev[B:B + 8], 4)); mem_writes += 1; rec["finm"].append((d, s["node"]))
                mslots[d][j] = None; s = None; mused[d] -= 1
        if s is None and mused[d] < MSLOTS and ready[4] and (nd := (pop_fit(ready[4]) if MEMSIM else heapq.heappop(ready[4])[2])) is not None:
            mslots[d][j] = {"node": nd, "r": 0}; mused[d] += 1
            if MEMSIM: mem_take(nd)
            body, _ = node_in(nd); lanes[B:B + len(body)] = body; mono_now[d] = 1; r[d] = 0; T_FR(B, body)
            mem_reads += 2; live -= sum(1 for k in nd.kids if k.kind != "leaf")
            rec["issue"].append(("MEM", f"M{d}", 0, [nd.id])); rec["memm"].append((d, nd))
    for d, B in enumerate(BASES):
        g = pack[d]
        if not (MSLOTS and (ready[5] or pprog[d])): continue
        for q in pprog[d]:
            if q["due"] == t:
                q["pg"].take(p2words(prev[B + q["tap"]:B + q["tap"] + 8])); q["due"] = None
                if q["pg"].done():
                    finish(q["node"], q["pg"].s[:8]); mem_writes += 1; q["dead"] = True
        pprog[d] = [q for q in pprog[d] if not q.get("dead")]
        if g["due"] == t:
            Y = p2words(prev[B + 8:B + 16])
            for k, m in enumerate(g["members"]): m["pg"].take_pack(Y[(k + 1) % 16])
            g["due"] = None
            if g["stage"] == 3:
                for m in g["members"]: m["inpack"] = False
                g["members"] = []; g["stage"] = 0
        if g["stage"] == 0:
            for q in pprog[d]:
                if len(g["members"]) >= 16: break
                if q["due"] is None and not q.get("inpack") and not q["pg"].done() and q["pg"].step()[0] == "PK":
                    g["members"].append(q); q["inpack"] = True
        q = None; dopack = False
        if g["members"] and g["due"] is None and (0 < g["stage"] < 3 or len(g["members"]) == 16): dopack = True
        else:
            cand = [q_ for q_ in pprog[d] if q_["due"] is None and q_.get("edue") is None and not q_.get("inpack") and q_["pg"].step()[0] != "PK"
                    and not (NENG and q_["pg"].on_engine())]
            if cand: q = cand[0]
            elif len(pprog[d]) < MSLOTS and ready[5] and (nd := (pop_fit(ready[5]) if MEMSIM else heapq.heappop(ready[5])[2])) is not None:
                l_, r_ = nd.kids[0].result, nd.kids[1].result
                if MEMSIM: mem_take(nd)
                q = {"node": nd, "pg": (P2ProgMul3 if MUL3 else P2ProgPacked if PACK else P2Prog)(l_ + r_, P2CODES), "due": None, "tap": 0}; pprog[d].append(q)
                mem_reads += 2; live -= sum(1 for k in nd.kids if k.kind != "leaf")
            elif g["members"] and g["due"] is None and g["stage"] == 0: dopack = True
        if dopack:
            z = [0] * 16; bw = list(z); cw = list(z)
            for k, m in enumerate(g["members"]): bw[k], cw[k] = m["pg"].pack_ops()
            lanes[B:B + 24] = p2lanes(z) + p2lanes(bw) + p2lanes(cw); mono_now[d] = 1; r[d] = P2CODES["R_SQ"]
            g["stage"] += 1; g["due"] = t + P2CODES["SQD"] + 1
            rec["issue"].append(("P2PK", f"M{d}", g["stage"], [m["node"].id for m in g["members"]]))
        elif q is not None:
            rr_, ln, lev, tap = q["pg"].issue()
            lanes[B:B + 24] = ln; mono_now[d] = 1; r[d] = rr_; q["due"] = t + lev + 1; q["tap"] = tap
            rec["issue"].append(("P2", f"M{d}", q["pg"].i, [q["node"].id]))
    er = [0] * max(NENG, 1)
    for e in range(NENG):
        for d in range(len(BASES)):
            for q in pprog[d]:
                if q.get("edue") == t and q.get("eng") == e:
                    q["pg"].take(p2words(prev[EBASE + 8 * e:EBASE + 8 * e + 8])); q["edue"] = None
        pick_ = None
        for d in range(len(BASES)):
            for q in pprog[d]:
                if q["due"] is None and q.get("edue") is None and not q["pg"].done() and q["pg"].on_engine(): pick_ = q; break
            if pick_: break
        if pick_ is not None:
            row, ln = pick_["pg"].eng_issue(); lanes[EBASE + 8 * e:EBASE + 8 * e + 8] = ln; er[e] = row
            pick_["edue"] = t + ELAT + 1; pick_["eng"] = e
            rec["issue"].append(("P2E", f"E{e}", row, [pick_["node"].id]))
    rec["mono"] = sum(mono_now)
    if ALT:
        for ri in range(NCH // 2):
            R0, R1 = rings[ri], rings[ri + NCH // 2]; j = t % R0["K"]
            s0, s1 = R0["slots"][j], R1["slots"][j]
            if s0 is not None: s0["src"] = ri
            if s1 is not None: s1["src"] = ri + NCH // 2
            R0["slots"][j], R1["slots"][j] = s1, s0
    for ri, R in enumerate(rings):
        K = R["K"]; j = t % K; s = R["slots"][j]; lo, hi = R["lo"], R["hi"]; g0 = R["spans"][0]
        if s is not None:
            S_ = rings[s.get("src", ri)]
            if s["r"] + 1 < max(NISS[nd.prim] for nd in s["nodes"]):
                lanes[lo:hi] = prev[S_["llo"]:S_["lhi"]]; T_CP(lo, hi - lo, S_["llo"])
                s["r"] += 1; rg[g0] = RV(s["r"])
                rec["issue"].append(("PIPE", ri, s["r"], [nd.id for nd in s["nodes"]]))
            else:
                for b, nd in enumerate(s["nodes"]):
                    jb = S_["lblocks"][b]; T_CK(BB[jb], 18, 0); finish(nd, out_words(prev[BB[jb]:BB[jb] + 18], nd.prim)); mem_writes += 1; rec["fin"].append((jb, nd))
                R["slots"][j] = None; s = None
        if s is None and t in plan[ri]:
            grp = plan[ri].pop(t)
            R["slots"][j] = {"nodes": grp, "r": 0}
            rec["issue"].append(("MEM", ri, 0, [nd.id for nd in grp])); rg[g0] = 0
            for b, nd in enumerate(grp):
                body, h = node_in(nd); bi = R["blocks"][b]; rec["mem"].append((bi, nd))
                lanes[BB[bi]:BB[bi] + len(body)] = body; T_FR(BB[bi], body)
                if h is not None and not (bi < COLOC): lanes[HB[bi]:HB[bi] + 4] = h; T_FR(HB[bi], h)
                if nd.kind == "m":
                    mem_reads += 2; live -= sum(1 for k in nd.kids if k.kind != "leaf")
                    for k in nd.kids:
                        if k.kind != "leaf" and top(k): live_top -= 1
                        elif k.kind == "leaf": hbm_bytes += 32
                else:
                    mem_reads += 1; live -= 1 if nd.level > 0 else 0
                    if nd.level > 0 and top(nd): live_top -= 1
        for i in range(1, len(R["spans"])):
            p = (t - R["c"][i]) % K; sp = R["slots"][p]
            if sp is None: continue
            gi, gp = R["spans"][i], R["spans"][i - 1]
            lanes[GLO[gi]:GHI[gi]] = prev[GLO[gp]:GHI[gp]]; T_CP(GLO[gi], GHI[gi] - GLO[gi], GLO[gp]); rg[gi] = RV(sp["r"])
    tp = t + LEAD
    for ri, R in enumerate(rings):
        if ALT and ri >= NCH // 2: continue
        K = R["K"]; sp = (rings[ri + NCH // 2] if ALT else R)["slots"][tp % K]
        if tp in plan[ri]: continue
        if not (sp is None or sp["r"] + 1 >= max(NISS[nd.prim] for nd in sp["nodes"])): continue
        if sp is None and tp % K == t % K and R["slots"][t % K] is not None: continue
        n = len(R["blocks"])
        allow_h = [(usehchain or bi >= COLOC) for bi in R["blocks"]]
        grp = pick(n, allow_h)
        if grp: plan[ri][tp] = grp
    htap = 0
    if usehchain:
        if not any(mono_now): lanes[BASE:BASE + 8] = prev[BASE:BASE + 8]; T_CP(BASE, 8, BASE); htap = 1
        if tp in plan[0]:
            for b, nd in enumerate(plan[0][tp]):
                if b < COLOC:
                    body, h = node_in(nd)
                    if h is not None: lanes[BASE + 4 * b:BASE + 4 * b + 4] = h; T_FR(BASE + 4 * b, h)
    live_max = max(live_max, live); live_top_max = max(live_top_max, live_top); ready_max = max(globals().get('ready_max', 0), len(ready[1]) + len(ready[2]) + len(ready[4]))
    rec["ctrl"] = (list(mono_now), list(r), list(rg), htap)
    if TRF:
        rgv = 0
        for g in range(NG): rgv |= (rg[g] & 511) << (9 * g)
        TRF.write(f"T {mono_now[0]} {mono_now[1] if NDP == 2 else 0} {htap} {BLAKE} {r[0]} {r[1] if NDP == 2 else 0} {rgv:x}" + chr(10))
        for lo, n, mode, vals in tr_ck: TRF.write(f"E {lo} {n} {mode} " + " ".join(f"{v:x}" for v in vals) + chr(10))
        for lo, vals in tr_fr: TRF.write(f"F {lo} " + " ".join(f"{v:x}" for v in vals) + chr(10))
        for dlo, n, slo in tr_cp: TRF.write(f"P {dlo} {n} {slo}" + chr(10))
        tr_cp.clear(); tr_fr.clear(); tr_ck.clear()
    o = ARR()
    if NENG: stepe(mono_now[0], mono_now[1] if NDP == 2 else 0, htap, BLAKE, r[0], r[1] if NDP == 2 else 0, IG(*rg), IEN(*er), ARR(*lanes), o)
    else: stepx(mono_now[0], mono_now[1] if NDP == 2 else 0, htap, BLAKE, r[0], r[1] if NDP == 2 else 0, IG(*rg), ARR(*lanes), o)
    prev = list(o); t += 1
    prog.append(rec)
    if MEMSIM:
        if rec["issue"] or dma_cycles != globals().get("_dma_seen", -1): _last_act = t; _dma_seen = dma_cycles
        elif t - globals().get("_last_act", 0) > 20000: sys.exit(f"memory model: no progress since cycle {_last_act} (SRAM {used}/{CAP} slots)")

def open_phase(qs):
    path = {(l, i >> l) for i in qs for l in range(SZ + 1)}
    need = {(l, (i >> l) ^ 1) for i in qs for l in range(SZ)} - path
    if REQ == "merkle": need |= {(0, i) for i in qs}
    hashes = 0
    if REQ == "merkle" and KSK:
        low = {(l, j) for (l, j) in need if 1 <= l <= KSK and l <= SZ - RTOP}
        need -= low
        for (l, j) in low: need |= {(0, (j << l) + i) for i in range(1 << l)}; hashes += (1 << l) - 1
    if REQ == "ggm" and KSK:
        K1 = min(KSK + 1, SZ)
        low = {(l, j) for (l, j) in need if 1 <= l <= KSK and l <= SZ - RTOP}
        need -= low
        need |= {(K1, j >> (K1 - l)) for (l, j) in low}
        hashes = len({(m, j >> (m - l)) for (l, j) in low for m in range(l + 1, K1 + 1)})
    return sorted((l, j) for (l, j) in need if l <= SZ - RTOP), hashes
OPEN = [int(x) for x in next((a[5:] for a in sys.argv[5:] if a.startswith("open=")), "").split(",") if x]
def print_open():
    print(f"  open ({'authentication paths' if REQ == 'merkle' else 'GGM punctures, co-path seeds'}, tree 2^{SZ}; top {RTOP} levels resident on chip; 1 KB rows; HBM {BW:g} B/cycle)")
    THR = {1: NB / 14, 2: NB / 14, 4: len(BASES) / 7, 5: 0.222}[prim]
    print(f"    {'q':>5} {'nodes read':>10} {'per leaf':>8} {'HBM KB':>8} {'HBM cyc':>8} {'recomp':>7} {'est.cyc':>7} | row activations " + " ".join(f"{L:>7}" for L in LAYOUTS) + " | per opened leaf " + " ".join(f"{L:>6}" for L in LAYOUTS))
    orng = random.Random(7)
    for q in OPEN:
        qs = sorted(orng.sample(range(1 << SZ), min(q, 1 << SZ)))
        rd, hs = open_phase(qs)
        acts = [len({addr(L, l, j) // ROWB for (l, j) in rd}) for L in LAYOUTS]
        print(f"    {q:>5} {len(rd):>10,} {len(rd) / q:>8.1f} {len(rd) * 32 / 1024:>8.1f} {len(rd) * 32 / BW:>8,.0f} {hs:>7,} {hs / THR:>7,.0f} | {'':15} " + " ".join(f"{a:>7,}" for a in acts) + " | " + " " * 15 + " ".join(f"{a / q:>6.1f}" for a in acts))
        if HBMSIM:
            res = []
            for L in LAYOUTS:
                cyc, st, lat = hbmlib.batch(sorted(addr(L, l, j) for (l, j) in rd), HCH, HMAP, port=HPORT, nbl=HNBL, kind=HKIND)
                res.append(f"{L} {cyc:,} cycles ({len(rd) * 32 / cyc:.1f} B/cycle, ACT {st['ACT']:,}, row hit {100 * st['row_hit']:.0f}%, latency avg {sum(lat) / max(1, len(lat)):.0f})")
            print(f"          HBM2 {HCH} ch: " + "; ".join(res))
if OPENONLY:
    print(f"request: {REQ} {MNAME[prim]} 2^{SZ}, open only (no commit run)")
    if SZ <= 14:
        for L in LAYOUTS:
            A = [addr(L, l, j) for l in range(SZ + 1) for j in range(1 << (SZ - l))]
            assert len(set(A)) == len(A) and all(x % 32 == 0 for x in A), L
            if L == "block": assert all(addr(L, l, j ^ 1) // 64 == addr(L, l, j) // 64 for l in range(1, SZ) for j in range(1 << (SZ - l))), "pairs"
        print(f"  layouts: {', '.join(LAYOUTS)}: all {2 ** (SZ + 1) - 1:,} nodes at distinct addresses; block layout: sibling pairs share a 64 B burst")
    print_open(); sys.exit(0)

sys.setrecursionlimit(200000)
ok = True
for nd in nodes:
    if nd.kind == "g" and nd.level < GDEPTH.get(nd.prim, -1):
        gi_, gl_ = gcoord(nd); c0, c1 = ggm_fn(nd.prim, nd.result, gl_, gi_)
        ok &= nd.kids[0].done and nd.kids[1].done and nd.kids[0].result == c0 and nd.kids[1].result == c1
def ref(nd):
    if nd.kind != "m": return nd.result
    return merkle_fn(nd.prim, ref(nd.kids[0]), ref(nd.kids[1]), nd.root and not NOROOT)
for root in roots:
    ok &= root.done and ref(root) == root.result
    if OPENREQ: ok &= root.result == OPEN_ROOT
ok &= all(nd.done and nd.result == merkle_fn(nd.prim, nd.kids[0].result, nd.kids[1].result, nd.root and not NOROOT) for nd in nodes if nd.kind == "m")

cycles = len(prog)
mono_issues = sum(r["mono"] for r in prog)
exec_issues = [sum(1 for r in prog for i in r["issue"] if i[1] == ri) for ri in range(len(rings))]
ring_nt = [sum(len(i[3]) for r in prog for i in r["issue"] if i[1] == ri) for ri in range(len(rings))]
util = [f"ring {ri}: {ring_nt[ri] / (len(R['blocks']) * cycles):.4f}" for ri, R in enumerate(rings) if ring_nt[ri]]
if mono_issues: util.append(f"Monolith: {mono_issues / (len(BASES) * cycles):.4f}")
desc = {"merkle": lambda: f"{NT} x {MNAME[prim]} Merkle 2^{LTOP} leaves ({ORDER})", "ggm": lambda: f"{NT} x {MNAME[prim]} GGM depth {LTOP} ({ORDER})"}[REQ]()
if OPENREQ: desc = f"open of {OPENQ} leaves of a {MNAME[prim]} Merkle 2^{SZ} (K = {OPENK}): {len(OPEN_INPUTS):,} inputs read, {work_total:,} compressions ({sum(1 for nd in nodes if nd.kind == 'm' and nd.level <= OPENK):,} at the {OPENK} unstored levels), {OPEN_PROOF:,} proof values written"
print(f"request: {desc}   unit: {NDP} Monolith ring(s) of {KM} slots x {NISS[4]} traversals; ARX rings {[(len(R['blocks']), R['K']) for R in rings]} (blocks, period = sum over spans of latency + 1)")
print(f"  nodes computed      {work_total:,}")
print(f"  cycles              {cycles:,}   (Monolith issues {mono_issues:,}; ARX ring traversals {exec_issues})")
print(f"  engine utilization  {', '.join(util)}   (node traversals issued / (blocks x cycles); Monolith issues / (datapaths x cycles))")
print(f"  throughput          {work_total / cycles:.3f} nodes/cycle")
print(f"  memory traffic      {mem_reads:,} reads, {mem_writes:,} writes of 32 B ({32 * (mem_reads + mem_writes) / cycles:.1f} B/cycle); live buffer high-water {live_max:,} x 32 B")
print(f"  pending queue       high-water {ready_max:,} ready nodes waiting for a slot (seeds / parents not yet issued)")
if not MEMSIM: print(f"  on-chip residents   high-water {live_top_max:,} results of the top {TOPL} levels (x 32 B = {live_top_max * 32 / 1024:,.1f} KB); HBM traffic {hbm_bytes / 1e6:,.2f} MB = {hbm_bytes / cycles:,.1f} B/cycle")
if MEMSIM: assert not stage, f"{len(stage)} rows never completed"
if MEMSIM and OPEN: print_open()
if MEMSIM and AUDIT:
    def must_write(nd):
        if REQ == "merkle": return (nd.kind == "m" and (stored(lam(nd)) or nd.root)) or nd.pw
        return nd.level > 0 and stored(lam(nd))
    nw_ = sum(1 for nd in nodes if must_write(nd))
    assert all(nd.nwr == (1 if must_write(nd) else 0) and nd.nw == must_write(nd) for nd in nodes if nd.kind != "leaf" or nd.pw), "a node written not exactly once iff stored"
    assert hbm_wr == 32 * nw_, (hbm_wr, nw_)
    assert hbm_rd == 32 * (len(OPEN_INPUTS) if OPENREQ else (1 << SZ) if REQ == "merkle" else NT), hbm_rd
    assert not rq and not wq and not rsent and fly == 0 and wpend == 0, (len(rq), len(wq), len(rsent), fly, wpend)
    nres = sum(1 for nd in nodes if resident(nd) and nd.res and not nd.freed)
    assert used == nres and all(nd.freed or resident(nd) for nd in nodes if nd.res or nd.tk), (used, nres)
    assert used_max <= CAP, (used_max, CAP)
    if REQ == "ggm" and GSCHED == "dfs" and GATE == "res":
        RES_ = g_res(TK)
        assert hold_max[0] <= (2 << TK) - 1 <= RES_, (hold_max, TK, RES_)
        print(f"  audit (liveness)    OK: max slots held by one subtree {hold_max[0]} <= bound 2^(TK+1) - 1 = {(2 << TK) - 1} <= reserve {RES_}; stack held at most {hold_max[1]}; rows released by a full SRAM {relief_n[0]}")
    print(f"  audit               OK: SRAM <= capacity after every change, recount from node states every 997 cycles, {nw_:,} values written once each "
          f"({hbm_wr / 1e6:.2f} MB), {hbm_rd // 32:,} reads, every issue had its inputs on chip and its outputs reserved, end: {used} resident slots")
    if OPEN:
        V = {(lam(nd), nd.idx): nd for nd in nodes}
        orng = random.Random(7)
        for q in OPEN:
            qs = sorted(orng.sample(range(1 << SZ), min(q, 1 << SZ)))
            rd, hs = open_phase(qs); RD = set(rd)
            assert all(l == 0 or stored(l) or (REQ == "ggm" and l == SZ) for (l, j) in RD), "open reads a node that is not in HBM"
            assert not any(l > SZ - RTOP for (l, j) in RD) if RTOP else True
            have = lambda l, j: (l, j) in RD or (RTOP and l > SZ - RTOP)
            nh = 0
            if REQ == "merkle":
                memo = {}
                def val(l, j):
                    global nh
                    if have(l, j): return V[(l, j)].result
                    assert 1 <= l <= KSK, f"sibling ({l},{j}) neither read nor recomputable"
                    if (l, j) not in memo:
                        L, R_ = val(l - 1, 2 * j), val(l - 1, 2 * j + 1); nh += 1
                        memo[(l, j)] = merkle_fn(prim, L, R_, False)
                    return memo[(l, j)]
                assert all(have(0, i) for i in qs), "opened leaf not read"
                known = {(0, i): V[(0, i)].result for i in qs}
                for l in range(SZ):
                    for p in sorted({i >> (l + 1) for i in qs}):
                        L, R_ = (known[(l, c)] if (l, c) in known else val(l, c) for c in (2 * p, 2 * p + 1))
                        known[(l + 1, p)] = merkle_fn(prim, L, R_, l + 1 == SZ)
                        assert known[(l + 1, p)] == V[(l + 1, p)].result, f"path node ({l + 1},{p}) wrong"
                assert nh == hs, (nh, hs)
                print(f"  open audit q={q:<5} OK: {len(qs)} authentication paths rebuilt to the root from {len(RD):,} reads + {nh:,} recomputed hashes")
            else:
                path = {(l, i >> l) for i in qs for l in range(SZ + 1)}
                T = {(l, (i >> l) ^ 1) for i in qs for l in range(SZ)} - path
                exp = set()
                for (l, j) in T:
                    if have(l, j): continue
                    assert 1 <= l <= KSK, f"co-path seed ({l},{j}) neither read nor regenerable"
                    K1 = min(KSK + 1, SZ); m, jj = K1, j >> (K1 - l)
                    assert have(m, jj), "regeneration root not read"
                    seed = V[(m, jj)].result
                    while m > l:
                        c = ggm_fn(prim, seed, SZ - m + GL0, jj + (GJ0 << (SZ - m))); exp.add((m, jj))
                        m -= 1; jj = j >> (m - l); seed = c[jj & 1]
                    assert seed == V[(l, j)].result, "regenerated seed wrong"
                assert len(exp) == hs, (len(exp), hs)
                cover = [0] * (1 << SZ)
                for (l, j) in T:
                    for x in range(j << l, (j + 1) << l): cover[x] += 1
                QS = set(qs)
                assert all(cover[x] == (0 if x in QS else 1) for x in range(1 << SZ)), "co-path does not cover all-but-q exactly once"
                print(f"  open audit q={q:<5} OK: {len(T):,} co-path seeds cover all {(1 << SZ) - len(qs):,} unpunctured leaves exactly once, none of the {len(qs)} punctured; "
                      f"obtained from {len(RD):,} reads + {len(exp):,} regeneration expansions, values match")
if MEMSIM:
    print(f"    write stream rows ({OROWS} open rows; " + ("block rows staged in SRAM, written whole" if STAGE else "each node written when computed") + "): " + ", ".join(f"{L} {WROWS[L].act:,} activations ({hbm_wr // max(1, WROWS[L].act):,} B each)" for L in LAYOUTS) + f"; leaf / seed reads {RROWS.act:,}")
    print(f"  memory model        SRAM {SRAM_KB:,.0f} KB = {CAP:,} x 32 B, tiles of 2^{TK} leaves, {'2 open (double buffer)' if REQ == 'merkle' else ((f'DFS order, a tile opens while the SRAM keeps the oldest tile its reserve, nodes above the tiles {AHEAD} tiles ahead' if GATE == 'res' else f'{WT} open, DFS order, nodes above the tiles {AHEAD} tiles ahead') if GSCHED == 'dfs' else 'open while their unwritten leaves fit half the SRAM')}, HBM {BW:g} B/cycle, store={STORE}")
    if STAGE: print(f"    row staging       rows wait in the SRAM until complete; {partial_rows:,} rows written partial (the SRAM was full and no write was on its way)")

    print(f"    pipeline holds    W = {WFLY} nodes (ring slots of the primitive); GGM lookahead {('fixed ' + str(LAFIX)) if REQ == 'ggm' and LAFIX else (f'theta (age + h L_max) / (2^TK - 1) from the simulated state, theta {THETA:.3f}, L_max {LMAX}, window {la_rng[0]}..{la_rng[1]} subtrees') if REQ == 'ggm' else '-'}")
    print(f"    SRAM high-water   {used_max:,} x 32 B = {used_max * 32 / 1024:,.1f} KB (capacity {CAP * 32 / 1024:,.0f} KB)")
    kb = lambda v: f"{v * 32 / 1024:,.1f}"
    print(f"    SRAM breakdown KB at the high-water / time average: results in flight (reserved) {kb(brk_max[0])} / {kb(brk_sum[0] / brk_n)}, "
          f"waiting for the HBM write {kb(brk_max[1])} / {kb(brk_sum[1] / brk_n)}, inputs waiting for their consumer {kb(brk_max[2])} / {kb(brk_sum[2] / brk_n)}")
    print(f"    HBM               read {hbm_rd / 1e6:,.2f} MB, write {hbm_wr / 1e6:,.2f} MB = {(hbm_rd + hbm_wr) / cycles:,.1f} B/cycle average; transferring in {dma_cycles:,} of {cycles:,} cycles ({100 * dma_cycles / cycles:.0f}%)")
    if HANDIN: print(f"    handoff           {hand_n} inputs computed by other PEs: written into this PE's DRAM channels ({32 * hand_n:,} B) and read only after the DRAM has issued those writes (the last one at cycle {hand_st[0]})")
    if HBMSIM:
        drain = 0
        while HBMX.cmd("WR") + HBMX.cmd("WRA") < hbm_wr // 32 and drain < 1_000_000: HBMX.tick(); drain += 1
        st = HBMX.stats()
        print(f"    DRAM model        {HBMX.describe()}; SRAM side sends <= {HPORT} accesses/cycle; stored nodes in the {HLAY} layout")
        if REC: open(REC, "w").write("".join(f"{a} {b} {c}\n" for a, b, c in rec_log))
        if BG: print(f"    other cores       {len(BG)} cores replaying {BGF.rsplit(':', 1)[0]} on the same DRAM (addresses 64 MB apart); "
                     f"behind their recorded pace by {[b[1] for b in BG]} cycles at the end, {sum(len(b[0]) for b in BG):,} of their accesses not yet sent")
        print(f"    {('GDDR6' if HKIND == 'gddr' else 'HBM2'):<5} commands    ACT {st['ACT']:,}  PRE {st['PRE'] + st['PREA']:,}  RD {st['RD'] + st['RDA']:,}  WR {st['WR'] + st['WRA']:,}  REFab {st['REFab']:,}; "
              f"row hit {100 * st['row_hit']:.1f}%, {st['B_per_act']:,.0f} B per activation; write buffers drained {drain} cycles after the last cycle")
        print(f"    {('GDDR6' if HKIND == 'gddr' else 'HBM2'):<5} read latency {rlat[1] / max(1, rlat[0]):.1f} cycles average, {rlat[2]} max (send to data on chip, {rlat[0]:,} reads)")
if TRF: TRF.write("Z" + chr(10)); TRF.close(); print(f"  trace               {TRACE_F}: {cycles:,} cycles")
print(f"  instruction stream  {cycles:,} words; per cycle: mono + blake bit + round indices + block/state addresses" + (" + h words" if usehchain else ""))
print(f"  check: all GGM leaves / Merkle roots and parents vs Python reference: {'OK' if ok else 'FAIL'}")
if ROOTOUT_F: open(ROOTOUT_F, "w").write("".join(" ".join(f"{w:x}" for w in root.result) + "\n" for root in roots))
if REQ == "ggm" and (LEAFOUT_F or "leafsha" in sys.argv[5:]):
    gl = sorted((nd for nd in nodes if nd.kind == "g" and nd.level == SZ), key=lambda nd: nd.id)
    if LEAFOUT_F: open(LEAFOUT_F, "w").write("".join(" ".join(f"{w:x}" for w in nd.result) + "\n" for nd in gl))
    if "leafsha" in sys.argv[5:]:
        import hashlib
        print(f"  leaves sha256: {hashlib.sha256(b''.join(w.to_bytes(4, 'little') for nd in gl for w in nd.result)).hexdigest()}")
