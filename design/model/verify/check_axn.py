import ctypes, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from models import *
DLL, MASK = os.path.abspath(sys.argv[1]), int(sys.argv[2], 0)
lib = ctypes.CDLL(DLL)
info = lib.lp_info
NB, NIO, BASE, BL, MERKLE, COLOC, NG = info(1), info(9), info(10), info(11), info(12), info(13), info(14)
BB = [info(1000 + 2 * j) for j in range(NB)]
HB = [info(1001 + 2 * j) for j in range(NB)]
BG = [info(2000 + j) for j in range(NB)]
GD = [info(3000 + g) for g in range(NG)]
GBLK = [[j for j in range(NB) if BG[j] == g] for g in range(NG)]
GLO = [min(BB[j] for j in GBLK[g]) for g in range(NG)]
GHI = [max(BB[j] + (18 if (j < COLOC) else BL) for j in GBLK[g]) for g in range(NG)]
GS0 = [info(4000 + g) for g in range(NG)]
GCH = [info(4100 + g) for g in range(NG)]
CH = []
for g in range(NG):
    while len(CH) <= GCH[g]: CH.append([])
    CH[GCH[g]].append(g)
for c in CH: c.sort(key=lambda g: GS0[g])
DEPTH = {1: info(3), 2: info(4), 4: info(6)}
NDP = info(18) or 1; BASES = [BASE] + ([info(17)] if NDP == 2 else [])
P2 = info(19) == 1
if P2:
    from pos2_prog import P2Prog, P2ProgMul3, P2ProgMul3A1, mono_issue_lanes, words as p2words, STEPS as P2STEPS, STEPS_M as P2STEPS_M
    if info(28) == 1: P2Prog, P2STEPS = P2ProgMul3, P2STEPS_M
    if info(29) == 1: P2Prog = P2ProgMul3A1
    P2CODES = {"SQD": info(20), "LE": info(21), "LI": info(22), "R_SQ": info(23), "R_INIT": info(24), "R_X5E": info(25), "R_X5I": info(26)}
NISS = {1: 14, 2: 14, 4: info(0)}
RV = lambda x: x | 256 if x == 13 else x
ARR = ctypes.c_uint64 * NIO
IARR = ctypes.c_int * NG
step = lib.lp_step
step.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ARR, ARR]
stepg = lib.lp_step_g
stepg.argtypes = [ctypes.c_int, IARR, ctypes.c_int, ARR, ARR]
print(f"  {NB} blocks per issue in {NG} group(s) = {len(CH)} chain(s) (blocks {[len(b) for b in GBLK]}, latencies {GD}, chains {CH}), block lanes {BL}{' (Merkle only)' if MERKLE else ''}, "
      f"{NIO} I/O lanes, Monolith datapaths at lanes {BASES}, co-located h blocks {COLOC}, Monolith issues {NISS[4]}")
jr = random.Random(7)
total_ok = True

def report(name, ok):
    global total_ok
    total_ok &= ok; print(f"  {name}: {'OK' if ok else 'FAIL'}")

def rand_lanes(mode):
    if mode == 4:
        L = [0] * NIO
        for B in BASES:
            for k in range(8): L[B + k] = pk(jr.randrange(P), jr.randrange(P))
            if P2: L[B:B + 24] = mono_issue_lanes(mono_words(L[B:B + 8]))
        return L
    return [jr.getrandbits(64) for _ in range(NIO)]

def run(mode, lanes, hpre=None, gt=0):
    n = NISS[mode]
    if mode == 4:
        D = DEPTH[4]; K = D + 1
        st = [list(lanes)] + [rand_lanes(4) for _ in range(K - 1)]
        iss = [0] * K; prev = None; t = 0
        while True:
            j = t % K
            if t >= K:
                st[j] = list(prev); iss[j] += 1
                if P2:
                    for B in BASES: st[j][B:B + 24] = mono_issue_lanes(mono_words(st[j][B:B + 8]))
                if j == 0 and iss[0] == n: return st[0]
            b = ARR(); step(4, 0, iss[j] % n, ARR(*st[j]), b)
            prev = list(b); t += 1
    rings = []
    for ci, spans in enumerate(CH):
        Ks = [GD[g] + 1 for g in spans]; K = sum(Ks); cs = [sum(Ks[:i]) for i in range(len(spans))]
        rings.append({"K": K, "spans": spans, "c": cs, "st": [(list(lanes) if (ci == gt and j == 0) else rand_lanes(mode)) for j in range(K)], "iss": [0] * K})
    NCH = len(CH)
    mate = (lambda ci: (ci + NCH // 2) % NCH) if mode == 2 else (lambda ci: ci)
    prev = [0] * NIO
    if hpre is not None:
        for _ in range(2):
            pre = [0] * NIO; pre[BASE:BASE + 8] = hpre
            b = ARR(); step(mode, 0, 0, ARR(*pre), b); prev = list(b)
    t = 0
    while True:
        L = [0] * NIO
        L[BASE:BASE + 8] = prev[BASE:BASE + 8]
        if hpre is not None and t == rings[0]["K"] - 2: L[BASE:BASE + 8] = hpre
        rg = [0] * NG
        for ci, R in enumerate(rings):
            K = R["K"]; j = t % K; g0 = R["spans"][0]; gL = R["spans"][-1]
            if t >= K:
                gM = rings[mate(ci)]["spans"][-1]
                R["st"][j][GLO[g0]:GHI[g0]] = prev[GLO[gM]:GHI[gM]]; R["iss"][j] += 1
                if ci == gt and j == 0 and R["iss"][0] == n:
                    gF = rings[mate(ci) if (n - 1) % 2 else ci]["spans"][-1]
                    res = list(prev); res[GLO[g0]:GHI[g0]] = prev[GLO[gF]:GHI[gF]]; return res
            L[GLO[g0]:GHI[g0]] = R["st"][j][GLO[g0]:GHI[g0]]
            rg[g0] = RV(R["iss"][j] % n)
            for i in range(1, len(R["spans"])):
                p = (t - R["c"][i]) % K; gi, gp = R["spans"][i], R["spans"][i - 1]
                L[GLO[gi]:GHI[gi]] = prev[GLO[gp]:GHI[gp]]; rg[gi] = RV(R["iss"][p] % n)
        b = ARR(); stepg(mode, IARR(*rg), rg[0], ARR(*L), b)
        prev = list(b); t += 1

def place(items, gt):
    L = [0] * NIO; hpre = [0] * 8; coloc = False
    for i, (body, h) in enumerate(items):
        j = GBLK[gt][i]
        L[BB[j]:BB[j] + len(body)] = body
        if h is not None:
            if j < COLOC: hpre[4 * j:4 * j + 4] = h; coloc = True
            else: L[HB[j]:HB[j] + 4] = h
    return L, (hpre if coloc else None)

def b3_body(h, m, counter, block_len, flags):
    L = b3_lanes(h, m, counter, block_len, flags, 22)
    return L[:18], L[18:22]

def b3_out(o, j): return [w for k in range(8) for w in (o[BB[j] + k] & M32, o[BB[j] + k] >> 32)]
def cc_out(o, j): return cc_words(o[BB[j]:BB[j] + 18])

if MASK & 2:
    kat = compress16(IV, [0] * 16, 0, 0, 11)[:8]
    report("BLAKE3('') KAT (model)", b"".join(w.to_bytes(4, "little") for w in kat).hex() == "af1349b9f5f9a1a6a0404dea36dcc9499bcb25c9adc112b7cc9a93cae41f3262")
    for gt in range(len(CH)):
        g0 = CH[gt][0]; nb = len(GBLK[g0])
        nodes = ([(IV, [0] * 16, 0, 0, 11)] if gt == 0 else []) + [(IV, [jr.getrandbits(32) for _ in range(16)], 0, 64, 4 | (8 if j % 2 else 0)) for j in range(nb - (1 if gt == 0 else 0))]
        L, hpre = place([b3_body(*nd) if not MERKLE else (b3_lanes(*nd, 18), None) for nd in nodes], g0)
        o = run(1, L, hpre, gt)
        ok = all(b3_out(o, GBLK[g0][i])[:8] == compress16(*nodes[i])[:8] for i in range(nb))
        for t in range(10):
            nodes = [(IV, [jr.getrandbits(32) for _ in range(16)], 0, 64, 4) for j in range(nb)]
            L, hpre = place([b3_body(*nd) if not MERKLE else (b3_lanes(*nd, 18), None) for nd in nodes], g0)
            o = run(1, L, hpre, gt)
            ok &= all(b3_out(o, GBLK[g0][i])[:8] == compress16(*nodes[i])[:8] for i in range(nb))
        report(f"BLAKE3 Merkle parent nodes, chain {gt} ({nb} blocks, span latencies {[GD[g] for g in CH[gt]]}){' incl. BLAKE3 KAT' if gt == 0 else ''}, 11 issues", ok)
        if not MERKLE:
            ok = True
            for t in range(10):
                nodes = [([jr.getrandbits(32) for _ in range(8)], [jr.getrandbits(32)] + [0] * 15, 0, 64, 16 | 1 | 2 | 8) for j in range(nb)]
                L, hpre = place([b3_body(*nd) for nd in nodes], g0)
                o = run(1, L, hpre, gt)
                ok &= all(b3_out(o, GBLK[g0][i]) == compress16(*nodes[i]) for i in range(nb))
            report(f"BLAKE3 keyed-XOF GGM nodes (64-byte output), chain {gt}{' (h via Monolith state lanes for %d blocks)' % COLOC if (gt == 0 and COLOC) else ''}, 10 issues", ok)

if MASK & 4:
    key = list(range(32)); words = [0x61707865, 0x3320646e, 0x79622d32, 0x6b206574] + [int.from_bytes(bytes(key[4*i:4*i+4]), "little") for i in range(8)] + [1, 0x09000000, 0x4a000000, 0]
    for gt in range(len(CH) // 2):
        g0 = CH[gt][0]; nb = len(GBLK[g0])
        sts = ([words] if gt == 0 else []) + [[jr.getrandbits(32) for _ in range(16)] for _ in range(nb - (1 if gt == 0 else 0))]
        L, _ = place([(cc_lanes(s, 18), None) for s in sts], g0)
        o = run(2, L, None, gt)
        if gt == 0: report("ChaCha20 RFC 8439 2.3.2 block KAT (group 0, block 0)", cc_out(o, 0)[:4] == [0xe4e7f110, 0x15593bd1, 0x1fdd0f50, 0xc47120a3])
        ok = all(cc_out(o, GBLK[g0][i]) == cc_block(sts[i]) for i in range(nb))
        for t in range(10):
            sts = [[jr.getrandbits(32) for _ in range(16)] for _ in range(nb)]
            L, _ = place([(cc_lanes(s, 18), None) for s in sts], g0)
            o = run(2, L, None, gt)
            ok &= all(cc_out(o, GBLK[g0][i]) == cc_block(sts[i]) for i in range(nb))
        report(f"ChaCha20 blocks vs model, chains {gt} / {gt + len(CH) // 2} ({nb} blocks, span latencies {[GD[g] for g in CH[gt]]}), 11 issues of 14 traversals", ok)

ONLY_P2 = P2 and info(27) == 1
if MASK & 16 and not ONLY_P2:
    for d, B in enumerate(BASES):
        ok = True
        for t in range(50):
            x = [jr.randrange(P) for _ in range(16)]
            L = rand_lanes(4)
            if P2: L[B:B + 24] = mono_issue_lanes(x)
            else: L[B:B + 8] = mono_lanes(x)
            o = run(4, L)
            ok &= mono_words(o[B:B + 8]) == mono(x)
        report(f"Monolith-31 t=16 vs model, datapath {d} (lanes {B}..), 50 random states", ok)
if MASK & 16 and P2:
    for d, B in enumerate(BASES):
        ok = True; delays = {}
        for t in range(20):
            x = [jr.randrange(P) for _ in range(16)]; pg = P2Prog(x, P2CODES)
            while not pg.done():
                r, ln, lev, tap = pg.issue(); exp = pg.expected_tap(); kind = P2STEPS[pg.i][0]
                L = rand_lanes(4); L[B:B + 24] = ln
                o = ARR(); step(4, 0, r, ARR(*L), o)
                got = None
                for c in range(1, lev + 3):
                    o = ARR(); step(0, 0, 0, ARR(*([0] * NIO)), o)
                    w = p2words(list(o)[B + tap:B + tap + 8])
                    if w == exp and got is None: got = (c, w)
                if got is None or got[0] != lev: ok = False; break
                delays[kind] = (lev, got[0]); pg.take(got[1])
            if not ok: break
            ok &= pg.s == pos2(x)
        report(f"Poseidon2-M31 t=16 vs Plonky3 model, datapath {d}: 20 random states x {len(P2STEPS)} issues, taps (level, calls after issue) {delays}", ok)
if MASK & 16 and P2 and info(30) > 0:
    from pos2_prog import P2ProgEng
    NE, EB, ELAT = info(30), info(31), info(32)
    IE = ctypes.c_int * NE
    stepe = lib.lp_step_e
    stepe.argtypes = [ctypes.c_int] * 6 + [IARR, IE, ARR, ARR]
    for e in range(NE):
        d = e % len(BASES); B = BASES[d]; ok = True; seen = set()
        for t in range(10):
            x = [jr.randrange(P) for _ in range(16)]; pg = P2ProgEng(x, P2CODES)
            while not pg.done():
                exp = pg.expected_tap()
                if pg.on_engine():
                    row, ln = pg.eng_issue(); er = [0] * NE; er[e] = row
                    L = rand_lanes(4); L[EB + 8 * e:EB + 8 * e + 8] = ln
                    o = ARR(); stepe(0, 0, 0, 0, 0, 0, IARR(*([0] * NG)), IE(*er), ARR(*L), o)
                    got = None
                    for c in range(1, ELAT + 3):
                        o = ARR(); stepe(0, 0, 0, 0, 0, 0, IARR(*([0] * NG)), IE(*([0] * NE)), ARR(*([0] * NIO)), o)
                        w = p2words(list(o)[EB + 8 * e:EB + 8 * e + 8])
                        if w == exp and got is None: got = (c, w)
                    if got is None or got[0] != ELAT: ok = False; break
                    seen.add("ENG"); pg.take(got[1])
                else:
                    r, ln, lev, tap = pg.issue()
                    L = rand_lanes(4); L[B:B + 24] = ln
                    o = ARR(); step(4, 0, r, ARR(*L), o)
                    got = None
                    for c in range(1, lev + 3):
                        o = ARR(); step(0, 0, 0, ARR(*([0] * NIO)), o)
                        w = p2words(list(o)[B + tap:B + tap + 8])
                        if w == exp and got is None: got = (c, w)
                    if got is None or got[0] != lev: ok = False; break
                    pg.take(got[1])
            if not ok: break
            ok &= pg.s == pos2(x)
        report(f"Poseidon2-M31 with internal-round engine {e} (lanes {EB + 8 * e}.., latency {ELAT}) + datapath {d}: 10 random states, 9 datapath issues + 14 engine rounds", ok)
print("ALL OK" if total_ok else "SOME CHECKS FAILED")
