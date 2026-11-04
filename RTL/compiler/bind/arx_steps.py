"""arx_steps.py - the six ARX steps of one block (RTL/src/shared/axn_step.sv, arx_group.sv), transcribed per 32-bit word
so that the same code runs on integers (bit-exact check against the reference models) and on symbols (the cell graph:
every register word of a level as R3 = op(R1, R2) of the previous level).
A lane is a pair (lo, hi) of words; a block is 22 lanes (rows A 0,4  B 1,5  C 2,6  D 3,7, message / copy 8..15, T 16,17,
h 18..21). Controls of one traversal: blake, r (diag = r[0], r8 = r[8]), CP = the copy of the block group (0 or 1)."""

M32 = (1 << 32) - 1
LAY = 1   # 1: the shared unit's ChaCha20 layout (axn_step.sv LAY = 1): copy 0's step 6 leaves the rows at C0 A1 D2 B3, copy 1's
          # steps 1 / 2 read the lanes BLAKE3 reads (step 1: A' to lane 1, D' to T; step 2: C + D on lanes 0 / T, the xor
          # with lane 3: no select on the step-2 operands, no second xor); 0: the
          # natural layout (the ChaCha20-only unit)


class Int:                                     # integer backend
    @staticmethod
    def add(a, b): return (a + b) & M32
    @staticmethod
    def xor(a, b): return a ^ b
    @staticmethod
    def rotl(a, n): return ((a << n) | (a >> (32 - n))) & M32 if n else a


def lane_add(be, a, b): return (be.add(a[0], b[0]), be.add(a[1], b[1]))
def lane_xor(be, a, b): return (be.xor(a[0], b[0]), be.xor(a[1], b[1]))
def lane_rotl(be, a, n): return (be.rotl(a[0], n), be.rotl(a[1], n))


def prow(x, lo, hi):
    """P on one row (lo = columns 0,1, hi = columns 2,3): returns (olo, ohi)"""
    if x == 0: return (lo[0], hi[1]), (hi[0], lo[1])
    if x == 1: return (lo[1], lo[0]), (hi[1], hi[0])
    if x == 2: return (hi[0], lo[1]), (lo[0], hi[1])
    return (hi[1], hi[0]), (lo[1], lo[0])


def wmask(s, l):
    if s in (1, 4): return l < 8 or l in (16, 17)
    if s == 2: return l < 8
    if s == 3: return l in (1, 2, 5, 6)
    if s == 5: return l in (0, 3, 4, 7)
    return l < 16


def step(s, CP, sv, blake, r, be):
    """one ARX step of one block: lanes of level s-1 -> lanes of level s"""
    bk, diag, r8 = blake, bool(r & 1), bool(r & 256)
    ff = CP == 1 and not bk and r8                       # ChaCha20 feed-forward traversal
    msg = bk or ff
    last = bk and r8
    cc = not bk and not ff
    g = CP == 1 or bk
    perm = bk and diag
    # ---- operands (axn_ops) ----
    lay1 = LAY and CP == 1
    if s == 1:
        a0, a1 = sv[1], sv[5]
        b0 = (sv[12] if diag else sv[8]) if bk else (sv[3] if lay1 else sv[0])
        b1 = (sv[14] if diag else sv[10]) if bk else (sv[7] if lay1 else sv[4])
    elif s == 2:
        if CP == 0: a0, a1, b0, b1 = sv[0], sv[4], (sv[16] if bk else sv[1]), (sv[17] if bk else sv[5])
        elif lay1: a0, a1, b0, b1 = sv[0], sv[4], sv[16], sv[17]
        else: a0, a1, b0, b1 = (sv[0] if bk else sv[2]), (sv[4] if bk else sv[6]), (sv[16] if bk else sv[3]), (sv[17] if bk else sv[7])
    elif s == 3:
        a0, a1, b0, b1 = sv[2], sv[6], (sv[8] if ff else sv[3]), (sv[10] if ff else sv[7])
    elif s == 4:
        a0, a1 = sv[1], sv[5]
        b0 = (sv[13] if diag else sv[9]) if msg else sv[0]; b1 = (sv[15] if diag else sv[11]) if msg else sv[4]
    elif s == 5:
        a0, a1 = sv[0], sv[4]
        b0 = sv[16] if bk else (sv[12] if ff else sv[1]); b1 = sv[17] if bk else (sv[14] if ff else sv[5])
    else:
        a0, a1, b0, b1 = (sv[9] if ff else sv[2]), (sv[11] if ff else sv[6]), sv[3], sv[7]
    s1, s2 = lane_add(be, a0, b0), lane_add(be, a1, b1)
    # ---- results (axn_fin) ----
    xa, xb = (sv[1], sv[5]) if s in (3, 6) else (sv[2], sv[6]) if (s == 1 and lay1) else (sv[3], sv[7])
    x1, x2 = lane_xor(be, xa, s1), lane_xor(be, xb, s2)
    R = lambda v, n: lane_rotl(be, v, n)
    m = {}
    if s == 1 and lay1:                                  # A at 1, B 3, C 0, D 2 -> A' to T, D' to 1
        m[16], m[17] = (s1, s2) if bk else (R(x1, 8), R(x2, 8))
        m[0], m[4], m[2], m[6], m[3], m[7] = sv[0], sv[4], sv[2], sv[6], sv[3], sv[7]
        m[1] = sv[1] if bk else s1; m[5] = sv[5] if bk else s2
    elif s == 2 and lay1:                                # C at 0, D T, A 1, B 3 -> C0 D1 A2 B3 after P
        b1, b2 = R(x1, 7), R(x2, 7)
        pc, pd, pa, pb = prow(2, s1, s2), prow(3, sv[16], sv[17]), prow(0, sv[1], sv[5]), prow(1, b1, b2)
        m[0] = s1 if bk else pc[0]; m[4] = s2 if bk else pc[1]
        m[1] = sv[1] if bk else pd[0]; m[5] = sv[5] if bk else pd[1]
        m[2] = sv[2] if bk else pa[0]; m[6] = sv[6] if bk else pa[1]
        m[3] = R(x1, 16) if bk else pb[0]; m[7] = R(x2, 16) if bk else pb[1]
    elif s == 1:
        m[16], m[17] = s1, s2
        if CP == 0:
            m[0] = sv[0] if bk else sv[2]; m[4] = sv[4] if bk else sv[6]
            m[1] = sv[1] if bk else R(x1, 16); m[5] = sv[5] if bk else R(x2, 16)
            m[2] = sv[2] if bk else s1; m[6] = sv[6] if bk else s2
            m[3] = sv[3] if bk else sv[1]; m[7] = sv[7] if bk else sv[5]
        else:
            m[0] = sv[0] if bk else s1; m[4] = sv[4] if bk else s2
            m[1], m[5], m[2], m[6] = sv[1], sv[5], sv[2], sv[6]
            m[3] = sv[3] if bk else R(x1, 8); m[7] = sv[7] if bk else R(x2, 8)
    elif s == 2:
        if CP == 0:
            m[0], m[4] = s1, s2
            m[3] = R(x1, 16) if bk else R(x1, 12); m[7] = R(x2, 16) if bk else R(x2, 12)
            m[1], m[5], m[2], m[6] = sv[1], sv[5], sv[2], sv[6]
        else:
            y1, y2 = lane_xor(be, sv[1], s1), lane_xor(be, sv[5], s2)
            b1, b2 = R(y1, 7), R(y2, 7)
            pc, pd, pa, pb = prow(2, s1, s2), prow(3, sv[3], sv[7]), prow(0, sv[0], sv[4]), prow(1, b1, b2)
            m[0] = s1 if bk else pc[0]; m[4] = s2 if bk else pc[1]
            m[1] = sv[1] if bk else pd[0]; m[5] = sv[5] if bk else pd[1]
            m[2] = sv[2] if bk else pa[0]; m[6] = sv[6] if bk else pa[1]
            m[3] = R(x1, 16) if bk else pb[0]; m[7] = R(x2, 16) if bk else pb[1]
    elif s == 3:
        m[2], m[6] = s1, s2
        c1, c2 = (R(x1, 8), R(x2, 8)) if CP == 0 else (R(x1, 16), R(x2, 16))
        m[1] = R(x1, 20) if bk else (sv[1] if ff else c1)
        m[5] = R(x2, 20) if bk else (sv[5] if ff else c2)
    elif s == 4:
        m[16], m[17] = s1, s2
        if CP == 0:
            b1, b2 = R(x1, 7), R(x2, 7)
            pa, pb, pc, pd = prow(0, sv[2], sv[6]), prow(1, b1, b2), prow(2, s1, s2), prow(3, sv[1], sv[5])
            m[0] = pa[0] if cc else sv[0]; m[4] = pa[1] if cc else sv[4]
            m[1] = pb[0] if cc else sv[1]; m[5] = pb[1] if cc else sv[5]
            m[2] = pc[0] if cc else sv[2]; m[6] = pc[1] if cc else sv[6]
            m[3] = pd[0] if cc else sv[3]; m[7] = pd[1] if cc else sv[7]
        else:
            m[0] = sv[2] if cc else sv[0]; m[4] = sv[6] if cc else sv[4]
            m[1] = R(x1, 12) if cc else sv[1]; m[5] = R(x2, 12) if cc else sv[5]
            m[2] = s1 if cc else sv[2]; m[6] = s2 if cc else sv[6]
            m[3] = sv[1] if cc else sv[3]; m[7] = sv[5] if cc else sv[7]
    elif s == 5:
        m[0], m[4] = s1, s2
        c1, c2 = (R(x1, 16), R(x2, 16)) if CP == 0 else (R(x1, 8), R(x2, 8))
        m[3] = R(x1, 24) if bk else (sv[3] if ff else c1)
        m[7] = R(x2, 24) if bk else (sv[7] if ff else c2)
    else:
        b61 = R(x1, 25) if bk else (s1 if ff else (R(x1, 12) if CP == 0 else R(x1, 7)))
        b62 = R(x2, 25) if bk else (s2 if ff else (R(x2, 12) if CP == 0 else R(x2, 7)))
        c61, c62 = (sv[2], sv[6]) if ff else (s1, s2)
        p6a, p6b, p6c, p6d = prow(0, sv[0], sv[4]), prow(1, b61, b62), prow(2, c61, c62), prow(3, sv[3], sv[7])
        if g:
            o = [p6a[0], p6b[0], p6c[0], p6d[0], p6a[1], p6b[1], p6c[1], p6d[1]]
        elif LAY:                                        # copy 0 (ChaCha20): C0 A1 D2 B3, the layout copy 1 starts from
            o = [c61, sv[0], sv[3], b61, c62, sv[4], sv[7], b62]
        else:
            o = [sv[0], b61, c61, sv[3], sv[4], b62, c62, sv[7]]
        if last:
            X = lambda a, b: lane_xor(be, a, b)
            z =[X(o[0], o[2]), X(o[4], o[6]), X(o[1], o[3]), X(o[5], o[7]),
                 X(o[2], sv[18]), X(o[6], sv[19]), X(o[3], sv[20]), X(o[7], sv[21])]
            for i in range(8): m[i] = z[i]
        else:
            for i in range(8): m[i] = o[i]
        if perm:
            p = [(sv[8][1], sv[9][1]), (sv[10][1], sv[14][1]), (sv[11][1], sv[10][0]), (sv[8][0], sv[15][0]),
                 (sv[9][0], sv[13][1]), (sv[15][1], sv[12][0]), (sv[13][0], sv[14][0]), (sv[12][1], sv[11][0])]
            for i in range(8): m[8 + i] = p[i]
        else:
            for i in range(8): m[8 + i] = sv[8 + i]
    return [m[l] if wmask(s, l) else sv[l] for l in range(22)]


def traversal(lanes, CP, blake, r, be=Int):
    for s in range(1, 7):
        lanes = step(s, CP, lanes, blake, r, be)
    return lanes


def schedule(prim):
    """(CP, r) of each traversal: BLAKE3 14 half-rounds on either copy; ChaCha20 alternates the copies, CP 0 first"""
    if prim == "blake3":
        return [(0, t if t < 13 else 13 | 256) for t in range(14)]
    return [(t % 2, t if t < 13 else 13 | 256) for t in range(14)]
