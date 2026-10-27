"""gen_pipe_axn.py -> pipe_axn.h: the three-primitive unit with EVERY ChaCha20 / BLAKE3 addition on Monolith's adders.
  ChaCha20 (GGM) / BLAKE3 (Merkle node, or keyed-XOF GGM node) blocks run their six ARX steps (level_ops_axn.h) on
  six pipeline levels; the 4 adds of every block step are executed by adders of the Monolith level function of
  that pipeline level (lane_mono_kl.inc, ext/EA/EB/EY ports). The ARX side has NO adders of its own.
  GROUPS: several block groups may use DIFFERENT level sets so that the idle Monolith adders of every level get
    used: group g = (levels L1<..<L6, N_g blocks). Its blocks enter at L1 straight from the input vector, pass the
    levels in between (registers only) and leave from the L6 register: latency D_g = L6 - L1 + 1; every group is its
    own slot ring in the sequencer (D_g + 1 slots), all rings issue every cycle into one input vector, each ring with
    its own round index rg[g].
  Monolith-31 Karatsuba, K = 1 (14 levels), lanes from MONO_BASE up.
  COLOC (0..2): that many blocks of group 0 keep their BLAKE3 chaining-value lanes (h) in Monolith's 8 state lanes
    (pure pass-throughs at levels 2..13): h rides through Monolith's registers with no select; the sequencer delivers
    h two cycles before the block's issue, the output port taps R(L1+3) for those lanes in ARX mode (one select per lane).
  The lane regions are otherwise disjoint: no register lane has two producers, no per-lane mode selects. Only the
  lanes live at a level are written (a group's lanes exist only inside its span), so dead lanes cost nothing.
  Wide I/O: LP_NIO lanes. One call = one clock. Single-primitive builds (MODES_MASK) fold every mode flag to a
  constant; a build without BLAKE3 (or with -DAXN_MERKLE) has 18-lane blocks, an ARX-only build private adders.
usage: gen_pipe_axn.py [N] [A0] [COLOC] [--groups=L1,..,L6:N;L1,..,L6:N;...]
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
pos = [a for a in sys.argv[1:] if not a.startswith("--")]
N = int(pos[0]) if len(pos) > 0 else 8
A0 = int(pos[1]) if len(pos) > 1 else 3
COLOC = int(pos[2]) if len(pos) > 2 else 0
gspec = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--groups=")), "")
# --groups=<chain>;<chain>...  chain = <span>+<span>...:<blocks>, span = consecutive levels. A chain is one block set whose six
# ARX steps run over its spans in order; every span is a GROUP of its own (own lanes, own round input rg, own ring): the
# sequencer takes a block out after the last level of a span and re-issues it into the next span's lanes, so steps on
# non-consecutive levels cost no pass-through registers (lanes exist only on the span's levels).
GROUPS, GSTEP0, GCHAIN, GSPAN = [], [], [], []
if gspec:
    for ci, gs in enumerate(gspec.split(";")):
        spans, nb = gs.split(":"); nb = int(nb); step = 1
        for si, sp in enumerate(spans.split("+")):
            lv = [int(x) for x in sp.split(",")]
            assert lv == list(range(lv[0], lv[0] + len(lv))), f"span {sp}: levels must be consecutive"
            GROUPS.append((lv, nb)); GSTEP0.append(step); GCHAIN.append(ci); GSPAN.append(si); step += len(lv)
        assert step == 7, f"chain {gs}: its spans must cover the six steps"
else: GROUPS = [(list(range(A0, A0 + 6)), N)]; GSTEP0 = [1]; GCHAIN = [0]; GSPAN = [0]
for lv, n in GROUPS: assert n >= 1
# two copies of the chains (the first half and the second half of --groups, identical): ChaCha20 traversals alternate
# between them (copy 0: steps S0..S3, round end, S0 S1; copy 1: S2 S3, round end, S0..S3, round end), BLAKE3 uses either
NCH = max(GCHAIN) + 1
if NCH % 2 == 0 and [(lv, n) for g, (lv, n) in enumerate(GROUPS) if GCHAIN[g] < NCH // 2] == [(lv, n) for g, (lv, n) in enumerate(GROUPS) if GCHAIN[g] >= NCH // 2]:
    CPY = [0 if GCHAIN[g] < NCH // 2 else 1 for g in range(len(GROUPS))]
else:                                                       # no mirrored copies: no ChaCha20 in this build (Monolith / Poseidon2 / BLAKE3 only)
    CPY = [0] * len(GROUPS); print("note: chains not in two identical copies -> ChaCha20 unsupported in this build")
assert 0 <= COLOC <= min(2, GROUPS[0][1])
NB = sum(n for _, n in GROUPS)
BASE = 22 * NB - 4 * COLOC                           # ARX region size in the unified build = MONO_BASE
MONO2 = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mono2=")), "")    # second Monolith datapath (its .inc)
PLAN = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--plan=")), "")      # k:n,... lendable adders per level per datapath
NENG = int(next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--p2eng=")), "0"))   # Poseidon2 internal-round engines (p2_engine.h)
NDP = 2 if (MONO2 or PLAN) else 1
need = {}
for lv, n in GROUPS:
    for k in lv: need[k] = need.get(k, 0) + 4 * n
if PLAN:
    # assign each (level, group) to a datapath: datapath 0 while it has room, else datapath 1; print the two MONO_LEND strings
    avail = {int(a.split(":")[0]): int(a.split(":")[1]) for a in PLAN.split(",") if a}
    cap = [dict(avail), dict(avail)]; lend = [{}, {}]
    for k in sorted(need):
        for g, (lv, n) in enumerate(GROUPS):
            if k not in lv: continue
            d = 0 if cap[0].get(k, 0) >= 4 * n else 1
            assert cap[d].get(k, 0) >= 4 * n, f"level {k}: group {g} needs {4 * n}, datapaths have {cap[0].get(k, 0)} / {cap[1].get(k, 0)} left"
            cap[d][k] -= 4 * n; lend[d][k] = lend[d].get(k, 0) + 4 * n
    for d in range(2): print(f"MONO_LEND datapath {d}: " + ",".join(f"{k}:{v}" for k, v in sorted(lend[d].items())) + f"   (total {sum(lend[d].values())})")
    sys.exit(0)
src = open(os.path.join(HERE, "lane_mono_kl.inc")).read()
MD = int(re.search(r"#define MONO_K_D (\d+)", src).group(1))
MN = {k: int(re.search(rf"#define MONO_K_N{k} (\d+)", src).group(1)) for k in range(1, MD + 1)}
assert int(re.search(r"#define MONO_BASE (\d+)", src).group(1)) == BASE, f"regenerate lane_mono_kl.inc with MONO_BASE={BASE}"
LEND = {k: int(re.search(rf"#define MONO_LEND_{k} (\d+)", src).group(1)) for k in range(1, MD + 1)}
_sqd = re.search(r"#define MONO_SQD (\d+)", src); SQD = int(_sqd.group(1)) if _sqd else 0    # gen_lane_mono6: Bricks rewrite the state lanes at this level
def _p2(src_, pfx):                                                # Poseidon2 taps of a datapath (gen_lane_mono6 MONO_P2=1)
    if not re.search(rf"#define {pfx}_P2 1", src_): return None
    return {k: int(re.search(rf"#define {pfx}_P2_{k} (\d+)", src_).group(1)) for k in ("LE", "LI", "TAPE", "TAPI")}
P2 = _p2(src, "MONO")
_dw = re.search(r"#define MONO_DEC_W (\d+)", src); DECW = int(_dw.group(1)) if _dw else 8
NDECM = "MONO_NDEC" if re.search(r"#define MONO_NDEC ", src) else "MONO_NISS"
P2B = 32 if P2 else 8                                              # lanes of a datapath's I/O region: state + (B, C operands in; Y, E, I taps out)
if NDP == 2:
    src2 = open(os.path.join(HERE, MONO2)).read()
    assert int(re.search(r"#define MONO2_K_D (\d+)", src2).group(1)) == MD
    MN2 = {k: int(re.search(rf"#define MONO2_K_N{k} (\d+)", src2).group(1)) for k in range(1, MD + 1)}
    BASE2 = int(re.search(r"#define MONO2_BASE (\d+)", src2).group(1))
    assert BASE2 == max(MN.values()), f"regenerate {MONO2} with MONO_BASE={max(MN.values())} (the widest level of datapath 1)"
    LEND2 = {k: int(re.search(rf"#define MONO2_LEND_{k} (\d+)", src2).group(1)) for k in range(1, MD + 1)}
    _sqd2 = re.search(r"#define MONO2_SQD (\d+)", src2); SQD2 = int(_sqd2.group(1)) if _sqd2 else 0
    P2_2 = _p2(src2, "MONO2"); assert (P2 is None) == (P2_2 is None), "both datapaths must be generated alike (MONO_P2)"
    NDECM2 = "MONO2_NDEC" if re.search(r"#define MONO2_NDEC ", src2) else "MONO2_NISS"
    MNTOP = MN2
else:
    MN2, BASE2, LEND2, SQD2, MNTOP = {}, 0, {}, 0, MN
# datapath of every (level, group) and the lending offset inside that datapath's ports: datapath 0 first, then 1
DP, OFF = {}, {}
used = [{}, {}]
for k in sorted(need):
    for g, (lv, n) in enumerate(GROUPS):
        if k not in lv: continue
        d = 0 if used[0].get(k, 0) + 4 * n <= LEND.get(k, 0) else 1
        DP[(k, g)] = d; OFF[(k, g)] = used[d].get(k, 0); used[d][k] = used[d].get(k, 0) + 4 * n
need1 = {k: used[0].get(k, 0) for k in need}; need2 = {k: used[1].get(k, 0) for k in need}
for k in need:
    assert need1[k] <= LEND.get(k, 0) and need2[k] <= LEND2.get(k, 0), f"level {k}: need {need1[k]} / {need2[k]} lent adders, datapaths lend {LEND.get(k, 0)} / {LEND2.get(k, 0)}"
assert max(lv[-1] for lv, _ in GROUPS) <= MD
assert GROUPS[0][0][0] >= 3 or COLOC == 0, "co-located h needs group 0 to enter at level 3 or later"
NLV = MD
PROD = {1: list(range(8)) + [16, 17], 2: list(range(8)), 3: [1, 2, 5, 6], 4: list(range(8)) + [16, 17], 5: [0, 3, 4, 7], 6: list(range(16))}
ADUMP = os.environ.get("AXN_DUMP", "")
if ADUMP:
    import json
    steps = []
    for (k, g), q0 in sorted(OFF.items()):
        lv, n = GROUPS[g]; j = GSTEP0[g] + lv.index(k)
        steps.append({"level": k, "group": g, "chain": GCHAIN[g], "span": GSPAN[g], "step": j, "dp": DP[(k, g)], "q0": q0, "blocks": n})
    json.dump({"groups": [{"levels": lv, "blocks": n, "step0": GSTEP0[g], "chain": GCHAIN[g]} for g, (lv, n) in enumerate(GROUPS)], "steps": steps,
               "PROD": {str(k): v for k, v in PROD.items()}}, open(ADUMP, "w", encoding="utf-8"))
    print(f"ARX dump: {len(steps)} (level, group) steps -> {ADUMP}")
# block layout: group 0 first (its first COLOC blocks have 18 lanes), then the other groups; all bases compile-time
blocks = []                                          # (group, index in group, python base lane, h lane base or None)
base = 0
for g, (lv, n) in enumerate(GROUPS):
    for b in range(n):
        col = (g == 0 and b < COLOC)
        blocks.append((g, b, base, None if col else base + 18))
        base += 18 if col else 22
assert base == BASE
GFIRST = [min(bi for bi, (gg, b, bs, hb) in enumerate(blocks) if gg == g) for g in range(len(GROUPS))]
GLAST = [max(bi for bi, (gg, b, bs, hb) in enumerate(blocks) if gg == g) for g in range(len(GROUPS))]
GLO = [f"AXN_GLO{g}" for g in range(len(GROUPS))]                    # compile-time lane bounds of each group (constexpr variables:
GHI = [f"AXN_GHI{g}" for g in range(len(GROUPS))]                    #  loop bounds must not be function calls or HLS cannot unroll)
live = {k: [g for g, (lv, n) in enumerate(GROUPS) if lv[0] <= k <= lv[-1]] for k in range(1, MD + 1)}   # groups whose lanes exist at level k


def BLK(bi, g, b, k):
    """the BLAKE3/ChaCha flag at level k: a constant in single-primitive builds, else the issue's blake bit (one per
    issue: a program runs one primitive), taken at the group's entry level and pipelined with the group (bk{g})"""
    bit = "blake" if GROUPS[g][0][0] == k else f"bk{g}[{k-1}]"
    return f"((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool){bit})"

o = []
w = o.append
w(f"// pipe_axn.h - GENERATED by gen_pipe_axn.py: ChaCha20/BLAKE3 {NB} blocks per issue in {len(GROUPS)} group(s) " + "; ".join(f"levels {lv[0]}..{lv[-1]} ({','.join(map(str, lv))}) x{n}" for lv, n in GROUPS))
w(f"// every add on Monolith-31 Karatsuba K=1 adders; disjoint lane regions (ARX 0..AXN_BASE-1, Monolith {BASE}..); COLOC={COLOC}")
w("#ifndef UNITREE_PIPE_AXN_H\n#define UNITREE_PIPE_AXN_H")
w("#ifndef MODES_MASK\n#define MODES_MASK 0x16\n#endif")
w('#define LANE_MONO_INC "lane_mono_rp1.inc"\n#include "level_ops.h"\n#include "lane_mono_kl.inc"' + (f'\n#include "{MONO2}"' if NDP == 2 else "") + '\n#include "level_ops_axn.h"')
w(f"#define AXN_NDP {NDP}\n#define AXN_MBASE2 {BASE2}")
ENGB = (BASE2 if NDP == 2 else BASE) + P2B
if NENG:
    assert P2, "--p2eng needs the Poseidon2 datapaths (MONO_P2)"
    sys.path.insert(0, os.path.join(HERE, "verify")); from models import P2I_ROWS
    w("static const ap_uint<31> P2ENG_C[14][16] = {" + ", ".join("{" + ", ".join(str(v) for v in row) + "}" for row in P2I_ROWS) + "};   // models.P2I_ROWS")
    w(f'#include "p2_engine.h"\n#define P2ENG_N {NENG}\n#define P2ENG_BASE {ENGB}')
w("#define HAS(m) ((MODES_MASK >> (m)) & 1)\n#define HAS_ARX (HAS(M_CHACHA) || HAS(M_BLAKE))")
w("#ifdef AXN_MERKLE\n#define AXN_BL 18\n#define AXN_MERKLE_FLAG 1\n#else\n#define AXN_BL (HAS(M_BLAKE) ? 22 : 18)\n#define AXN_MERKLE_FLAG 0\n#endif")
w(f"#define AXN_NB {NB}\n#define AXN_NG {len(GROUPS)}\n#define AXN_L0 {GROUPS[0][0][0]}")
w(f"#define AXN_COLOC ((HAS_ARX && HAS(M_MONO) && HAS(M_BLAKE) && !AXN_MERKLE_FLAG) ? {COLOC} : 0)   // group-0 blocks whose h lanes live in Monolith's state lanes")
w("constexpr int axn_b(int j) { return j < AXN_COLOC ? j * (AXN_BL - 4) : AXN_COLOC * (AXN_BL - 4) + (j - AXN_COLOC) * AXN_BL; }   // block base lane")
w("constexpr int axn_h(int j) { return j < AXN_COLOC ? MONO_BASE + 4 * j : axn_b(j) + 18; }                                      // h lanes of block j")
w(f"static constexpr int AXN_BASE = HAS_ARX ? axn_b({NB}) : 0;")
w("static constexpr int LP_NIO = HAS(M_MONO) ? " + (f"MONO2_BASE + {P2B}" if NDP == 2 else f"MONO_BASE + {P2B}") + (f" + {8 * NENG}" if NENG else "") + " : AXN_BASE;")
w('static_assert(!(HAS_ARX && HAS(M_MONO)) || AXN_BASE == MONO_BASE, "ARX region must end where the Monolith region starts");')
for g in range(len(GROUPS)): w(f"static constexpr int AXN_GLO{g} = axn_b({GFIRST[g]}), AXN_GHI{g} = axn_b({GLAST[g] + 1});")
w("static constexpr int AXN_GD[AXN_NG] = {" + ", ".join(str(lv[-1] - lv[0] + 1) for lv, _ in GROUPS) + "};   // latency of each group")
w("static constexpr int AXN_GN[AXN_NG] = {" + ", ".join(str(n) for _, n in GROUPS) + "};               // blocks of each group")
w("static constexpr int AXN_BG[AXN_NB] = {" + ", ".join(str(g) for g, b, bs, hb in blocks) + "};        // group of each block")
w("static constexpr int AXN_GL0[AXN_NG] = {" + ", ".join(str(lv[0]) for lv, _ in GROUPS) + "};             // entry level of each group")
def glv6(g):
    lv = GROUPS[g][0]; out = [0] * 6
    for i, L in enumerate(lv): out[GSTEP0[g] - 1 + i] = L
    return out
w("static constexpr int AXN_GLV[AXN_NG][6] = {" + ", ".join("{" + ", ".join(map(str, glv6(g))) + "}" for g in range(len(GROUPS))) + "};   // level of each step (0: the step is in another span of the chain)")
w("static constexpr int AXN_GS0[AXN_NG] = {" + ", ".join(map(str, GSTEP0)) + "};             // first step of each group (span)")
w("static constexpr int AXN_GCP[AXN_NG] = {" + ", ".join(map(str, CPY)) + "};             // copy of each group (ChaCha20 alternates copies 0 / 1)")
w("static constexpr int AXN_GCH[AXN_NG] = {" + ", ".join(map(str, GCHAIN)) + "};             // chain of each group; a chain's groups are listed in span order")
w(f"#define AES_B 1\n#define KEC_R 1")
w(f"#define LP_DEPTH_K 0\n#define LP_DEPTH_S {GROUPS[0][0][-1] - GROUPS[0][0][0] + 1}\n#define LP_DEPTH_C {GROUPS[0][0][-1] - GROUPS[0][0][0] + 1}\n#define LP_DEPTH_A 0\n#define LP_DEPTH_M {MD}")
w("static constexpr int maxi(int a, int b) { return a > b ? a : b; }")
for k in range(1, NLV + 1):
    arx = "AXN_BASE" if live[k] else "0"
    w(f"static constexpr int LV_N{k} = maxi({arx}, HAS(M_MONO) * {MNTOP[k]});")
w("static constexpr int LV_NMAX = maxi(LP_NIO, " + "maxi(" * (NLV - 1) + "LV_N1" + "".join(f", LV_N{k})" for k in range(2, NLV + 1)) + ");")
w(f"""
// NO MODE. A program runs one primitive on one tree kind (Merkle or GGM); per-cycle operation control from the
// instruction (the sequencer's compiled program):
//   mono     : a Monolith state is issued this cycle; it owns the adders of level k at cycle (now + k - 1)
//   htap     : the output port shows the co-located h lanes (R(L0+3)) instead of Monolith's output on the state lanes
//   blake    : the issue's blocks are BLAKE3 nodes (rotations 16/20/24/25, sigma, finalisation), else ChaCha20 blocks
//   r / rg[g]: round index of the Monolith state / of each block group
// mono travels with its issue through the levels; a level's adders serve the Monolith state when the pipelined mono
// bit is set, else the ARX blocks. The ARX write-back is a wire (no gating): a Monolith state and an ARX step never
// meet at one level because a program holds only one of them.
void lane_pipe(const lane_t in[LP_NIO], lane_t out[LP_NIO], ap_uint<1> mono, ap_uint<1> mono2, ap_uint<1> htap, ap_uint<1> blake, ap_uint<9> r, ap_uint<9> r2, const ap_uint<9> rg[AXN_NG], ap_uint<1> cfg{", const ap_uint<4> er[P2ENG_N]" if NENG else ""}) {{
#pragma HLS INTERFACE mode=ap_ctrl_hs port=return
#pragma HLS ARRAY_PARTITION variable=in complete
#pragma HLS ARRAY_PARTITION variable=out complete
#pragma HLS ARRAY_PARTITION variable=rg complete
#pragma HLS PIPELINE II=1
#pragma HLS BIND_STORAGE variable=MONO_DEC_K type=rom_1p impl=lutram
    (void)cfg; (void)htap; (void)mono2; (void)r2;""")
if NDP == 2: w("#pragma HLS BIND_STORAGE variable=MONO2_DEC_K type=rom_1p impl=lutram")
if NENG:
    w("#pragma HLS ARRAY_PARTITION variable=er complete")
    w(f"    lane_t eo[{8 * NENG}];\n#pragma HLS ARRAY_PARTITION variable=eo complete")
    w("#if HAS(M_MONO)")
    for e in range(NENG):
        w(f"    lane_t ei{e}[8], eo{e}[8];\n#pragma HLS ARRAY_PARTITION variable=ei{e} complete\n#pragma HLS ARRAY_PARTITION variable=eo{e} complete")
        w(f"    for (int k = 0; k < 8; k++) {{\n#pragma HLS UNROLL\n        ei{e}[k] = in[P2ENG_BASE + {8 * e} + k]; }}")
        w(f"    p2eng<{e}>(ei{e}, er[{e}], eo{e});")
        w(f"    for (int k = 0; k < 8; k++) {{\n#pragma HLS UNROLL\n        eo[{8 * e} + k] = eo{e}[k]; }}")
    w("#else")
    w(f"    for (int k = 0; k < {8 * NENG}; k++) {{\n#pragma HLS UNROLL\n        eo[k] = 0; }}")
    w("#endif")
for k in range(1, NLV + 1):
    w(f"    static lane_t R{k}[LV_N{k} > 0 ? LV_N{k} : 1];\n#pragma HLS ARRAY_PARTITION variable=R{k} complete")
w(f"    static ap_uint<9> rr[{NLV + 1}];\n#pragma HLS ARRAY_PARTITION variable=rr complete")
w(f"    static ap_uint<{DECW}> dd[{NLV + 1}];\n#pragma HLS ARRAY_PARTITION variable=dd complete")
w(f"    static ap_uint<1> mp[{NLV + 1}];\n#pragma HLS ARRAY_PARTITION variable=mp complete")           # mono bit pipelined with the Monolith state
if NDP == 2:
    w(f"    static ap_uint<{DECW}> dd2[{NLV + 1}];\n#pragma HLS ARRAY_PARTITION variable=dd2 complete")
    w(f"    static ap_uint<1> mp2[{NLV + 1}];\n#pragma HLS ARRAY_PARTITION variable=mp2 complete")
for g in range(len(GROUPS)):
    w(f"    static ap_uint<9> ar{g}[{NLV + 1}];\n#pragma HLS ARRAY_PARTITION variable=ar{g} complete")
    w(f"    static ap_uint<1> bk{g}[{NLV + 1}];\n#pragma HLS ARRAY_PARTITION variable=bk{g} complete")   # the issue's blake bit, pipelined with the group from its entry level
w(f"    ap_uint<{DECW}> dec = mono ? MONO_DEC_K[r < {NDECM} ? (int)r : 0] : (ap_uint<{DECW}>)0;   // no Monolith state issued: no Bars / squares / constants on the state lanes")
if NDP == 2: w(f"    ap_uint<{DECW}> dec2 = mono2 ? MONO2_DEC_K[r2 < {NDECM2} ? (int)r2 : 0] : (ap_uint<{DECW}>)0;")
# output: every block's lanes from its group's exit-level register, Monolith lanes from R14; co-located h from R(L0+3)
w(f"""    for (int i = 0; i < LP_NIO; i++) {{
#pragma HLS UNROLL
        lane_t v = 0;""")
w("#if HAS_ARX")
for g, (lv, n) in enumerate(GROUPS):
    w(f"        if (i >= {GLO[g]} && i < {GHI[g]}) v = R{lv[-1]}[i < LV_N{lv[-1]} ? i : 0];")
w("#endif")
taps = ""
if P2:                                                             # Poseidon2 taps: Y (state lanes after the Bricks level), M_E, M_I outputs
    taps += (f"        if (i >= MONO_BASE + 8 && i < MONO_BASE + 16) v = R{SQD}[MONO_BASE + (i - MONO_BASE - 8)];\n"
             f"        if (i >= MONO_BASE + 16 && i < MONO_BASE + 24) v = R{P2['LE']}[{P2['TAPE']} + (i - MONO_BASE - 16)];\n"
             f"        if (i >= MONO_BASE + 24 && i < MONO_BASE + 32) v = R{P2['LI']}[{P2['TAPI']} + (i - MONO_BASE - 24)];\n")
    if NDP == 2:
        taps += (f"        if (i >= MONO2_BASE + 8 && i < MONO2_BASE + 16) v = R{SQD2}[MONO2_BASE + (i - MONO2_BASE - 8)];\n"
                 f"        if (i >= MONO2_BASE + 16 && i < MONO2_BASE + 24) v = R{P2_2['LE']}[{P2_2['TAPE']} + (i - MONO2_BASE - 16)];\n"
                 f"        if (i >= MONO2_BASE + 24 && i < MONO2_BASE + 32) v = R{P2_2['LI']}[{P2_2['TAPI']} + (i - MONO2_BASE - 24)];\n")
engtap = f"        if (i >= P2ENG_BASE) v = eo[i >= P2ENG_BASE ? i - P2ENG_BASE : 0];\n" if NENG else ""
w(f"""#if HAS(M_MONO)
        if (i >= MONO_BASE) v = R{MD}[i < LV_N{MD} ? i : 0];
{taps}{engtap}        if (AXN_COLOC > 0 && htap && i >= MONO_BASE && i < MONO_BASE + 4 * AXN_COLOC) v = R{GROUPS[0][0][0] + 3}[i < LV_N{GROUPS[0][0][0] + 3} ? i : 0];
#endif
        out[i] = v;
    }}""")
for k in range(1, NLV + 1):
    dk = "dec" if k == 1 else f"dd[{k-1}]"
    active = [(g, GSTEP0[g] + lv.index(k)) for g, (lv, n) in enumerate(GROUPS) if k in lv]      # groups doing an ARX step here
    w(f"    // ---- level {k}" + (" (ARX steps: " + ", ".join(f"group {g} step {j}" for g, j in active) + ")" if active else "") + " ----")
    # X: only the lanes live at this level: each live group's lanes (from the input at its entry level, else from the
    # previous register) and the Monolith region
    w(f"    lane_t X{k}[LV_NMAX];\n#pragma HLS ARRAY_PARTITION variable=X{k} complete")
    w(f"    for (int l = 0; l < LV_NMAX; l++) {{\n#pragma HLS UNROLL\n        X{k}[l] = 0; }}")          # dead lanes: defined (constant), no logic
    w("#if HAS_ARX")
    for g in live[k]:
        src_r = "in" if GROUPS[g][0][0] == k else f"R{k-1}"
        w(f"    for (int l = {GLO[g]}; l < {GHI[g]}; l++) {{\n#pragma HLS UNROLL\n        X{k}[l] = {src_r}[l]; }}")
    w("#endif")
    if k == 1: w(f"#if HAS(M_MONO)\n    for (int l = MONO_BASE; l < LP_NIO; l++) {{\n#pragma HLS UNROLL\n        X1[l] = in[l]; }}\n#endif")
    else: w(f"#if HAS(M_MONO)\n    for (int l = MONO_BASE; l < LV_N{k-1}; l++) {{\n#pragma HLS UNROLL\n        X{k}[l] = R{k-1}[l]; }}\n#endif")
    w(f"    word32_t EA{k}[MONO_LEND_MAX], EB{k}[MONO_LEND_MAX], EY{k}[MONO_LEND_MAX], XB{k}[MONO_XLEND_MAX], XY{k}[MONO_XLEND_MAX];")
    for v in ("EA", "EB", "EY", "XB", "XY"): w(f"#pragma HLS ARRAY_PARTITION variable={v}{k} complete")
    w(f"    for (int q = 0; q < MONO_LEND_MAX; q++) {{\n#pragma HLS UNROLL\n        EA{k}[q] = 0; EB{k}[q] = 0; EY{k}[q] = 0; }}")
    w(f"    for (int q = 0; q < MONO_XLEND_MAX; q++) {{\n#pragma HLS UNROLL\n        XB{k}[q] = 0; XY{k}[q] = 0; }}")
    if NDP == 2:
        w(f"    word32_t EA2{k}[MONO2_LEND_MAX], EB2{k}[MONO2_LEND_MAX], EY2{k}[MONO2_LEND_MAX], XB2{k}[MONO2_XLEND_MAX], XY2{k}[MONO2_XLEND_MAX];")
        for v in ("EA2", "EB2", "EY2", "XB2", "XY2"): w(f"#pragma HLS ARRAY_PARTITION variable={v}{k} complete")
        w(f"    for (int q = 0; q < MONO2_LEND_MAX; q++) {{\n#pragma HLS UNROLL\n        EA2{k}[q] = 0; EB2{k}[q] = 0; EY2{k}[q] = 0; }}")
        w(f"    for (int q = 0; q < MONO2_XLEND_MAX; q++) {{\n#pragma HLS UNROLL\n        XB2{k}[q] = 0; XY2{k}[q] = 0; }}")
    if active:
        w(f"#if HAS_ARX\n    lane_t a{k}[LV_NMAX];\n#pragma HLS ARRAY_PARTITION variable=a{k} complete")
        w(f"    for (int l = 0; l < LV_NMAX; l++) {{\n#pragma HLS UNROLL\n        a{k}[l] = 0; }}")
        for g, j in active:
            rk = f"rg[{g}]" if GROUPS[g][0][0] == k else f"ar{g}[{k-1}]"
            for bi, (gg, b, bs, hb) in enumerate(blocks):
                if gg != g: continue
                q = OFF[(k, g)] + 4 * b; ea, eb = (f"EA{k}", f"EB{k}") if DP[(k, g)] == 0 else (f"EA2{k}", f"EB2{k}")
                w(f"    axn_ops{j}<axn_b({bi}), {CPY[g]}>(X{k}, {rk}, {BLK(bi, g, b, k)}, {ea} + {q}, {eb} + {q});")
        w("#endif")
    w(f"#if HAS(M_MONO)\n    lane_t m{k}[LV_NMAX];\n#pragma HLS ARRAY_PARTITION variable=m{k} complete")
    w(f"    for (int l = 0; l < LV_NMAX; l++) {{\n#pragma HLS UNROLL\n        m{k}[l] = 0; }}")
    monok = "mono" if k == 1 else f"mp[{k-1}]"                                 # the mono bit of the issue at this level
    ext = f"(HAS_ARX ? !(bool){monok} : false)" if active else "false"
    w(f"    monk_lx{k}(X{k}, {dk}, m{k}, {ext}, EA{k}, EB{k}, EY{k}, XB{k}, XY{k});")
    if NDP == 2:
        dk2 = "dec2" if k == 1 else f"dd2[{k-1}]"; monok2 = "mono2" if k == 1 else f"mp2[{k-1}]"
        ext2 = f"(HAS_ARX ? !(bool){monok2} : false)" if active else "false"
        w(f"    lane_t m2{k}[LV_NMAX];\n#pragma HLS ARRAY_PARTITION variable=m2{k} complete")
        w(f"    for (int l = 0; l < LV_NMAX; l++) {{\n#pragma HLS UNROLL\n        m2{k}[l] = 0; }}")
        w(f"    monk2_lx{k}(X{k}, {dk2}, m2{k}, {ext2}, EA2{k}, EB2{k}, EY2{k}, XB2{k}, XY2{k});")
    if active:
        w(f"#else\n    for (int q = 0; q < {need1[k]}; q++) {{\n#pragma HLS UNROLL\n        EY{k}[q] = alu_addp<32>(EA{k}[q], EB{k}[q]); }}")   # ARX-only build: private adders (ALU-ADP)
        if NDP == 2 and need2[k]: w(f"    for (int q = 0; q < {need2[k]}; q++) {{\n#pragma HLS UNROLL\n        EY2{k}[q] = alu_addp<32>(EA2{k}[q], EB2{k}[q]); }}")
    w("#endif")
    if active:
        w("#if HAS_ARX")
        for g, j in active:
            rk = f"rg[{g}]" if GROUPS[g][0][0] == k else f"ar{g}[{k-1}]"
            for bi, (gg, b, bs, hb) in enumerate(blocks):
                if gg != g: continue
                q = OFF[(k, g)] + 4 * b
                ey = f"EY{k}" if DP[(k, g)] == 0 else f"EY2{k}"
                if j == 6: w(f"    axn_fin6<axn_b({bi}), {CPY[g]}, axn_h({bi})>(X{k}, {rk}, {BLK(bi, g, b, k)}, {ey} + {q}, a{k});")
                else: w(f"    axn_fin{j}<axn_b({bi}), {CPY[g]}>(X{k}, {rk}, {BLK(bi, g, b, k)}, {ey} + {q}, a{k});")
        w("#endif")
    # register inputs, live lanes only: per live group (produced lanes of its step at this level, else pass), Monolith region
    w(f"    lane_t N{k}[LV_N{k} > 0 ? LV_N{k} : 1];\n#pragma HLS ARRAY_PARTITION variable=N{k} complete")
    w("#if HAS_ARX")
    for g in live[k]:
        lv = GROUPS[g][0]
        if k in lv:
            j = GSTEP0[g] + lv.index(k)
            cond = " || ".join(f"bl == {p}" for p in PROD[j])
            if g == 0 and COLOC > 0:
                bl = "(l < AXN_COLOC * (AXN_BL - 4)) ? (l % (AXN_BL - 4)) : ((l - AXN_COLOC * (AXN_BL - 4)) % AXN_BL)"
            else:
                bl = f"(l - ({GLO[g]})) % AXN_BL"
            # the write-back is a wire: a program holds one primitive (one tree kind), so an ARX traversal never meets
            # a Monolith state on a level and nothing is gated at run time
            w(f"    for (int l = {GLO[g]}; l < {GHI[g]}; l++) {{\n#pragma HLS UNROLL\n        const int bl = {bl}; N{k}[l] = ({cond}) ? a{k}[l] : X{k}[l]; }}")
        else:
            w(f"    for (int l = {GLO[g]}; l < {GHI[g]}; l++) {{\n#pragma HLS UNROLL\n        N{k}[l] = X{k}[l]; }}")
    w("#endif")
    # state lanes pass unless the level rewrites them: level 1 (Bars, lanes BASE..BASE+3), the Bricks level (MONO_SQD, all 8), the last
    mpass = f"(l < {BASE + 8} && {'l >= ' + str(BASE + 4) if k == 1 else ('false' if k in (MD, SQD) else 'true')})"
    if NDP == 1:
        w(f"#if HAS(M_MONO)\n    for (int l = MONO_BASE; l < LV_N{k}; l++) {{\n#pragma HLS UNROLL\n        N{k}[l] = {mpass} ? X{k}[l] : m{k}[l]; }}\n#endif")
    else:
        mpass2 = f"(l < {BASE2 + 8} && {'l >= ' + str(BASE2 + 4) if k == 1 else ('false' if k in (MD, SQD2) else 'true')})"
        w(f"#if HAS(M_MONO)\n    for (int l = MONO_BASE; l < MONO2_BASE; l++) {{\n#pragma HLS UNROLL\n        N{k}[l] = {mpass} ? X{k}[l] : m{k}[l]; }}")
        w(f"    for (int l = MONO2_BASE; l < LV_N{k}; l++) {{\n#pragma HLS UNROLL\n        N{k}[l] = {mpass2} ? X{k}[l] : m2{k}[l]; }}\n#endif")
# register writes AFTER every level has read the old register values (one clock = one call), live lanes only
for k in range(NLV, 0, -1):
    w("#if HAS_ARX")
    for g in live[k]:
        w(f"    for (int l = {GLO[g]}; l < {GHI[g]}; l++) {{\n#pragma HLS UNROLL\n        R{k}[l] = N{k}[l]; }}")
    w("#endif")
    w(f"#if HAS(M_MONO)\n    for (int l = MONO_BASE; l < LV_N{k}; l++) {{\n#pragma HLS UNROLL\n        R{k}[l] = N{k}[l]; }}\n#endif")
w(f"    for (int k = {NLV}; k >= 2; k--) {{\n#pragma HLS UNROLL\n        rr[k] = rr[k-1]; dd[k] = dd[k-1]; mp[k] = mp[k-1]; }}\n    rr[1] = r; dd[1] = dec; mp[1] = mono;")
if NDP == 2: w(f"    for (int k = {NLV}; k >= 2; k--) {{\n#pragma HLS UNROLL\n        dd2[k] = dd2[k-1]; mp2[k] = mp2[k-1]; }}\n    dd2[1] = dec2; mp2[1] = mono2;")
for g, (lv, n) in enumerate(GROUPS):
    w(f"    for (int k = {lv[-1]}; k >= {lv[0] + 1}; k--) {{\n#pragma HLS UNROLL\n        ar{g}[k] = ar{g}[k-1]; bk{g}[k] = bk{g}[k-1]; }}\n    ar{g}[{lv[0]}] = rg[{g}]; bk{g}[{lv[0]}] = blake;")
w("}\n#endif")
open(os.path.join(HERE, "pipe_axn.h"), "w", newline="\n").write("\n".join(o) + "\n")
print(f"pipe_axn.h written: {NB} blocks in {len(GROUPS)} groups {[(lv, n) for lv, n in GROUPS]}, lent adders per level {need}, COLOC={COLOC}, BASE={BASE}, NIO={BASE + 8}")
