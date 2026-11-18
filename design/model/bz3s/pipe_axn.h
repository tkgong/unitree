#ifndef UNITREE_PIPE_AXN_H
#define UNITREE_PIPE_AXN_H
#ifndef MODES_MASK
#define MODES_MASK 0x16
#endif
#define LANE_MONO_INC "lane_mono_rp1.inc"
#include "level_ops.h"
#include "lane_mono_kl.inc"
#include "lane_mono2_kl.inc"
#include "level_ops_axn.h"
#define AXN_NDP 2
#define AXN_MBASE2 448
#define HAS(m) ((MODES_MASK >> (m)) & 1)
#define HAS_ARX (HAS(M_CHACHA) || HAS(M_BLAKE))
#ifdef AXN_MERKLE
#define AXN_BL 18
#define AXN_MERKLE_FLAG 1
#else
#define AXN_BL (HAS(M_BLAKE) ? 22 : 18)
#define AXN_MERKLE_FLAG 0
#endif
#define AXN_NB 18
#define AXN_NG 4
#define AXN_L0 7
#define AXN_COLOC ((HAS_ARX && HAS(M_MONO) && HAS(M_BLAKE) && !AXN_MERKLE_FLAG) ? 0 : 0)
constexpr int axn_b(int j) { return j < AXN_COLOC ? j * (AXN_BL - 4) : AXN_COLOC * (AXN_BL - 4) + (j - AXN_COLOC) * AXN_BL; }
constexpr int axn_h(int j) { return j < AXN_COLOC ? MONO_BASE + 4 * j : axn_b(j) + 18; }
static constexpr int AXN_BASE = HAS_ARX ? axn_b(18) : 0;
static constexpr int LP_NIO = HAS(M_MONO) ? MONO2_BASE + 8 : AXN_BASE;
static_assert(!(HAS_ARX && HAS(M_MONO)) || AXN_BASE == MONO_BASE, "ARX region must end where the Monolith region starts");
static constexpr int AXN_GLO0 = axn_b(0), AXN_GHI0 = axn_b(5);
static constexpr int AXN_GLO1 = axn_b(5), AXN_GHI1 = axn_b(9);
static constexpr int AXN_GLO2 = axn_b(9), AXN_GHI2 = axn_b(14);
static constexpr int AXN_GLO3 = axn_b(14), AXN_GHI3 = axn_b(18);
static constexpr int AXN_GD[AXN_NG] = {6, 6, 6, 6};
static constexpr int AXN_GN[AXN_NG] = {5, 4, 5, 4};
static constexpr int AXN_BG[AXN_NB] = {0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 3};
static constexpr int AXN_GL0[AXN_NG] = {7, 5, 7, 5};
static constexpr int AXN_GLV[AXN_NG][6] = {{7, 8, 9, 10, 11, 12}, {5, 6, 7, 8, 9, 10}, {7, 8, 9, 10, 11, 12}, {5, 6, 7, 8, 9, 10}};
static constexpr int AXN_GS0[AXN_NG] = {1, 1, 1, 1};
static constexpr int AXN_GCP[AXN_NG] = {0, 0, 1, 1};
static constexpr int AXN_GCH[AXN_NG] = {0, 1, 2, 3};
#define AES_B 1
#define KEC_R 1
#define LP_DEPTH_K 0
#define LP_DEPTH_S 6
#define LP_DEPTH_C 6
#define LP_DEPTH_A 0
#define LP_DEPTH_M 18
static constexpr int maxi(int a, int b) { return a > b ? a : b; }
static constexpr int LV_N1 = maxi(0, HAS(M_MONO) * 471);
static constexpr int LV_N2 = maxi(0, HAS(M_MONO) * 464);
static constexpr int LV_N3 = maxi(0, HAS(M_MONO) * 464);
static constexpr int LV_N4 = maxi(0, HAS(M_MONO) * 456);
static constexpr int LV_N5 = maxi(AXN_BASE, HAS(M_MONO) * 464);
static constexpr int LV_N6 = maxi(AXN_BASE, HAS(M_MONO) * 471);
static constexpr int LV_N7 = maxi(AXN_BASE, HAS(M_MONO) * 485);
static constexpr int LV_N8 = maxi(AXN_BASE, HAS(M_MONO) * 499);
static constexpr int LV_N9 = maxi(AXN_BASE, HAS(M_MONO) * 500);
static constexpr int LV_N10 = maxi(AXN_BASE, HAS(M_MONO) * 495);
static constexpr int LV_N11 = maxi(AXN_BASE, HAS(M_MONO) * 483);
static constexpr int LV_N12 = maxi(AXN_BASE, HAS(M_MONO) * 476);
static constexpr int LV_N13 = maxi(0, HAS(M_MONO) * 470);
static constexpr int LV_N14 = maxi(0, HAS(M_MONO) * 466);
static constexpr int LV_N15 = maxi(0, HAS(M_MONO) * 466);
static constexpr int LV_N16 = maxi(0, HAS(M_MONO) * 466);
static constexpr int LV_N17 = maxi(0, HAS(M_MONO) * 466);
static constexpr int LV_N18 = maxi(0, HAS(M_MONO) * 456);
static constexpr int LV_NMAX = maxi(LP_NIO, maxi(maxi(maxi(maxi(maxi(maxi(maxi(maxi(maxi(maxi(maxi(maxi(maxi(maxi(maxi(maxi(maxi(LV_N1, LV_N2), LV_N3), LV_N4), LV_N5), LV_N6), LV_N7), LV_N8), LV_N9), LV_N10), LV_N11), LV_N12), LV_N13), LV_N14), LV_N15), LV_N16), LV_N17), LV_N18));

void lane_pipe(const lane_t in[LP_NIO], lane_t out[LP_NIO], ap_uint<1> mono, ap_uint<1> mono2, ap_uint<1> htap, ap_uint<1> blake, ap_uint<9> r, ap_uint<9> r2, const ap_uint<9> rg[AXN_NG], ap_uint<1> cfg) {
#pragma HLS INTERFACE mode=ap_ctrl_hs port=return
#pragma HLS ARRAY_PARTITION variable=in complete
#pragma HLS ARRAY_PARTITION variable=out complete
#pragma HLS ARRAY_PARTITION variable=rg complete
#pragma HLS PIPELINE II=1
#pragma HLS BIND_STORAGE variable=MONO_DEC_K type=rom_1p impl=lutram
    (void)cfg; (void)htap; (void)mono2; (void)r2;
#pragma HLS BIND_STORAGE variable=MONO2_DEC_K type=rom_1p impl=lutram
    static lane_t R1[LV_N1 > 0 ? LV_N1 : 1];
#pragma HLS ARRAY_PARTITION variable=R1 complete
    static lane_t R2[LV_N2 > 0 ? LV_N2 : 1];
#pragma HLS ARRAY_PARTITION variable=R2 complete
    static lane_t R3[LV_N3 > 0 ? LV_N3 : 1];
#pragma HLS ARRAY_PARTITION variable=R3 complete
    static lane_t R4[LV_N4 > 0 ? LV_N4 : 1];
#pragma HLS ARRAY_PARTITION variable=R4 complete
    static lane_t R5[LV_N5 > 0 ? LV_N5 : 1];
#pragma HLS ARRAY_PARTITION variable=R5 complete
    static lane_t R6[LV_N6 > 0 ? LV_N6 : 1];
#pragma HLS ARRAY_PARTITION variable=R6 complete
    static lane_t R7[LV_N7 > 0 ? LV_N7 : 1];
#pragma HLS ARRAY_PARTITION variable=R7 complete
    static lane_t R8[LV_N8 > 0 ? LV_N8 : 1];
#pragma HLS ARRAY_PARTITION variable=R8 complete
    static lane_t R9[LV_N9 > 0 ? LV_N9 : 1];
#pragma HLS ARRAY_PARTITION variable=R9 complete
    static lane_t R10[LV_N10 > 0 ? LV_N10 : 1];
#pragma HLS ARRAY_PARTITION variable=R10 complete
    static lane_t R11[LV_N11 > 0 ? LV_N11 : 1];
#pragma HLS ARRAY_PARTITION variable=R11 complete
    static lane_t R12[LV_N12 > 0 ? LV_N12 : 1];
#pragma HLS ARRAY_PARTITION variable=R12 complete
    static lane_t R13[LV_N13 > 0 ? LV_N13 : 1];
#pragma HLS ARRAY_PARTITION variable=R13 complete
    static lane_t R14[LV_N14 > 0 ? LV_N14 : 1];
#pragma HLS ARRAY_PARTITION variable=R14 complete
    static lane_t R15[LV_N15 > 0 ? LV_N15 : 1];
#pragma HLS ARRAY_PARTITION variable=R15 complete
    static lane_t R16[LV_N16 > 0 ? LV_N16 : 1];
#pragma HLS ARRAY_PARTITION variable=R16 complete
    static lane_t R17[LV_N17 > 0 ? LV_N17 : 1];
#pragma HLS ARRAY_PARTITION variable=R17 complete
    static lane_t R18[LV_N18 > 0 ? LV_N18 : 1];
#pragma HLS ARRAY_PARTITION variable=R18 complete
    static ap_uint<9> rr[19];
#pragma HLS ARRAY_PARTITION variable=rr complete
    static ap_uint<8> dd[19];
#pragma HLS ARRAY_PARTITION variable=dd complete
    static ap_uint<1> mp[19];
#pragma HLS ARRAY_PARTITION variable=mp complete
    static ap_uint<8> dd2[19];
#pragma HLS ARRAY_PARTITION variable=dd2 complete
    static ap_uint<1> mp2[19];
#pragma HLS ARRAY_PARTITION variable=mp2 complete
    static ap_uint<9> ar0[19];
#pragma HLS ARRAY_PARTITION variable=ar0 complete
    static ap_uint<1> bk0[19];
#pragma HLS ARRAY_PARTITION variable=bk0 complete
    static ap_uint<9> ar1[19];
#pragma HLS ARRAY_PARTITION variable=ar1 complete
    static ap_uint<1> bk1[19];
#pragma HLS ARRAY_PARTITION variable=bk1 complete
    static ap_uint<9> ar2[19];
#pragma HLS ARRAY_PARTITION variable=ar2 complete
    static ap_uint<1> bk2[19];
#pragma HLS ARRAY_PARTITION variable=bk2 complete
    static ap_uint<9> ar3[19];
#pragma HLS ARRAY_PARTITION variable=ar3 complete
    static ap_uint<1> bk3[19];
#pragma HLS ARRAY_PARTITION variable=bk3 complete
    ap_uint<8> dec = mono ? MONO_DEC_K[r < MONO_NDEC ? (int)r : 0] : (ap_uint<8>)0;
    ap_uint<8> dec2 = mono2 ? MONO2_DEC_K[r2 < MONO2_NDEC ? (int)r2 : 0] : (ap_uint<8>)0;
    for (int i = 0; i < LP_NIO; i++) {
#pragma HLS UNROLL
        lane_t v = 0;
#if HAS_ARX
        if (i >= AXN_GLO0 && i < AXN_GHI0) v = R12[i < LV_N12 ? i : 0];
        if (i >= AXN_GLO1 && i < AXN_GHI1) v = R10[i < LV_N10 ? i : 0];
        if (i >= AXN_GLO2 && i < AXN_GHI2) v = R12[i < LV_N12 ? i : 0];
        if (i >= AXN_GLO3 && i < AXN_GHI3) v = R10[i < LV_N10 ? i : 0];
#endif
#if HAS(M_MONO)
        if (i >= MONO_BASE) v = R18[i < LV_N18 ? i : 0];
        if (AXN_COLOC > 0 && htap && i >= MONO_BASE && i < MONO_BASE + 4 * AXN_COLOC) v = R10[i < LV_N10 ? i : 0];
#endif
        out[i] = v;
    }
    lane_t X1[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=X1 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        X1[l] = 0; }
#if HAS_ARX
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LP_NIO; l++) {
#pragma HLS UNROLL
        X1[l] = in[l]; }
#endif
    word32_t EA1[MONO_LEND_MAX], EB1[MONO_LEND_MAX], EY1[MONO_LEND_MAX], XB1[MONO_XLEND_MAX], XY1[MONO_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA1 complete
#pragma HLS ARRAY_PARTITION variable=EB1 complete
#pragma HLS ARRAY_PARTITION variable=EY1 complete
#pragma HLS ARRAY_PARTITION variable=XB1 complete
#pragma HLS ARRAY_PARTITION variable=XY1 complete
    for (int q = 0; q < MONO_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA1[q] = 0; EB1[q] = 0; EY1[q] = 0; }
    for (int q = 0; q < MONO_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB1[q] = 0; XY1[q] = 0; }
    word32_t EA21[MONO2_LEND_MAX], EB21[MONO2_LEND_MAX], EY21[MONO2_LEND_MAX], XB21[MONO2_XLEND_MAX], XY21[MONO2_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA21 complete
#pragma HLS ARRAY_PARTITION variable=EB21 complete
#pragma HLS ARRAY_PARTITION variable=EY21 complete
#pragma HLS ARRAY_PARTITION variable=XB21 complete
#pragma HLS ARRAY_PARTITION variable=XY21 complete
    for (int q = 0; q < MONO2_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA21[q] = 0; EB21[q] = 0; EY21[q] = 0; }
    for (int q = 0; q < MONO2_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB21[q] = 0; XY21[q] = 0; }
#if HAS(M_MONO)
    lane_t m1[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m1 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m1[l] = 0; }
    monk_lx1(X1, dec, m1, false, EA1, EB1, EY1, XB1, XY1);
    lane_t m21[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m21 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m21[l] = 0; }
    monk2_lx1(X1, dec2, m21, false, EA21, EB21, EY21, XB21, XY21);
#endif
    lane_t N1[LV_N1 > 0 ? LV_N1 : 1];
#pragma HLS ARRAY_PARTITION variable=N1 complete
#if HAS_ARX
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < MONO2_BASE; l++) {
#pragma HLS UNROLL
        N1[l] = (l < 404 && l >= 400) ? X1[l] : m1[l]; }
    for (int l = MONO2_BASE; l < LV_N1; l++) {
#pragma HLS UNROLL
        N1[l] = (l < 456 && l >= 452) ? X1[l] : m21[l]; }
#endif
    lane_t X2[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=X2 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        X2[l] = 0; }
#if HAS_ARX
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N1; l++) {
#pragma HLS UNROLL
        X2[l] = R1[l]; }
#endif
    word32_t EA2[MONO_LEND_MAX], EB2[MONO_LEND_MAX], EY2[MONO_LEND_MAX], XB2[MONO_XLEND_MAX], XY2[MONO_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA2 complete
#pragma HLS ARRAY_PARTITION variable=EB2 complete
#pragma HLS ARRAY_PARTITION variable=EY2 complete
#pragma HLS ARRAY_PARTITION variable=XB2 complete
#pragma HLS ARRAY_PARTITION variable=XY2 complete
    for (int q = 0; q < MONO_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA2[q] = 0; EB2[q] = 0; EY2[q] = 0; }
    for (int q = 0; q < MONO_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB2[q] = 0; XY2[q] = 0; }
    word32_t EA22[MONO2_LEND_MAX], EB22[MONO2_LEND_MAX], EY22[MONO2_LEND_MAX], XB22[MONO2_XLEND_MAX], XY22[MONO2_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA22 complete
#pragma HLS ARRAY_PARTITION variable=EB22 complete
#pragma HLS ARRAY_PARTITION variable=EY22 complete
#pragma HLS ARRAY_PARTITION variable=XB22 complete
#pragma HLS ARRAY_PARTITION variable=XY22 complete
    for (int q = 0; q < MONO2_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA22[q] = 0; EB22[q] = 0; EY22[q] = 0; }
    for (int q = 0; q < MONO2_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB22[q] = 0; XY22[q] = 0; }
#if HAS(M_MONO)
    lane_t m2[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m2 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m2[l] = 0; }
    monk_lx2(X2, dd[1], m2, false, EA2, EB2, EY2, XB2, XY2);
    lane_t m22[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m22 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m22[l] = 0; }
    monk2_lx2(X2, dd2[1], m22, false, EA22, EB22, EY22, XB22, XY22);
#endif
    lane_t N2[LV_N2 > 0 ? LV_N2 : 1];
#pragma HLS ARRAY_PARTITION variable=N2 complete
#if HAS_ARX
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < MONO2_BASE; l++) {
#pragma HLS UNROLL
        N2[l] = (l < 404 && true) ? X2[l] : m2[l]; }
    for (int l = MONO2_BASE; l < LV_N2; l++) {
#pragma HLS UNROLL
        N2[l] = (l < 456 && true) ? X2[l] : m22[l]; }
#endif
    lane_t X3[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=X3 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        X3[l] = 0; }
#if HAS_ARX
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N2; l++) {
#pragma HLS UNROLL
        X3[l] = R2[l]; }
#endif
    word32_t EA3[MONO_LEND_MAX], EB3[MONO_LEND_MAX], EY3[MONO_LEND_MAX], XB3[MONO_XLEND_MAX], XY3[MONO_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA3 complete
#pragma HLS ARRAY_PARTITION variable=EB3 complete
#pragma HLS ARRAY_PARTITION variable=EY3 complete
#pragma HLS ARRAY_PARTITION variable=XB3 complete
#pragma HLS ARRAY_PARTITION variable=XY3 complete
    for (int q = 0; q < MONO_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA3[q] = 0; EB3[q] = 0; EY3[q] = 0; }
    for (int q = 0; q < MONO_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB3[q] = 0; XY3[q] = 0; }
    word32_t EA23[MONO2_LEND_MAX], EB23[MONO2_LEND_MAX], EY23[MONO2_LEND_MAX], XB23[MONO2_XLEND_MAX], XY23[MONO2_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA23 complete
#pragma HLS ARRAY_PARTITION variable=EB23 complete
#pragma HLS ARRAY_PARTITION variable=EY23 complete
#pragma HLS ARRAY_PARTITION variable=XB23 complete
#pragma HLS ARRAY_PARTITION variable=XY23 complete
    for (int q = 0; q < MONO2_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA23[q] = 0; EB23[q] = 0; EY23[q] = 0; }
    for (int q = 0; q < MONO2_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB23[q] = 0; XY23[q] = 0; }
#if HAS(M_MONO)
    lane_t m3[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m3 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m3[l] = 0; }
    monk_lx3(X3, dd[2], m3, false, EA3, EB3, EY3, XB3, XY3);
    lane_t m23[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m23 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m23[l] = 0; }
    monk2_lx3(X3, dd2[2], m23, false, EA23, EB23, EY23, XB23, XY23);
#endif
    lane_t N3[LV_N3 > 0 ? LV_N3 : 1];
#pragma HLS ARRAY_PARTITION variable=N3 complete
#if HAS_ARX
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < MONO2_BASE; l++) {
#pragma HLS UNROLL
        N3[l] = (l < 404 && true) ? X3[l] : m3[l]; }
    for (int l = MONO2_BASE; l < LV_N3; l++) {
#pragma HLS UNROLL
        N3[l] = (l < 456 && true) ? X3[l] : m23[l]; }
#endif
    lane_t X4[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=X4 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        X4[l] = 0; }
#if HAS_ARX
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N3; l++) {
#pragma HLS UNROLL
        X4[l] = R3[l]; }
#endif
    word32_t EA4[MONO_LEND_MAX], EB4[MONO_LEND_MAX], EY4[MONO_LEND_MAX], XB4[MONO_XLEND_MAX], XY4[MONO_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA4 complete
#pragma HLS ARRAY_PARTITION variable=EB4 complete
#pragma HLS ARRAY_PARTITION variable=EY4 complete
#pragma HLS ARRAY_PARTITION variable=XB4 complete
#pragma HLS ARRAY_PARTITION variable=XY4 complete
    for (int q = 0; q < MONO_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA4[q] = 0; EB4[q] = 0; EY4[q] = 0; }
    for (int q = 0; q < MONO_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB4[q] = 0; XY4[q] = 0; }
    word32_t EA24[MONO2_LEND_MAX], EB24[MONO2_LEND_MAX], EY24[MONO2_LEND_MAX], XB24[MONO2_XLEND_MAX], XY24[MONO2_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA24 complete
#pragma HLS ARRAY_PARTITION variable=EB24 complete
#pragma HLS ARRAY_PARTITION variable=EY24 complete
#pragma HLS ARRAY_PARTITION variable=XB24 complete
#pragma HLS ARRAY_PARTITION variable=XY24 complete
    for (int q = 0; q < MONO2_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA24[q] = 0; EB24[q] = 0; EY24[q] = 0; }
    for (int q = 0; q < MONO2_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB24[q] = 0; XY24[q] = 0; }
#if HAS(M_MONO)
    lane_t m4[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m4 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m4[l] = 0; }
    monk_lx4(X4, dd[3], m4, false, EA4, EB4, EY4, XB4, XY4);
    lane_t m24[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m24 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m24[l] = 0; }
    monk2_lx4(X4, dd2[3], m24, false, EA24, EB24, EY24, XB24, XY24);
#endif
    lane_t N4[LV_N4 > 0 ? LV_N4 : 1];
#pragma HLS ARRAY_PARTITION variable=N4 complete
#if HAS_ARX
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < MONO2_BASE; l++) {
#pragma HLS UNROLL
        N4[l] = (l < 404 && false) ? X4[l] : m4[l]; }
    for (int l = MONO2_BASE; l < LV_N4; l++) {
#pragma HLS UNROLL
        N4[l] = (l < 456 && false) ? X4[l] : m24[l]; }
#endif
    lane_t X5[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=X5 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        X5[l] = 0; }
#if HAS_ARX
    for (int l = AXN_GLO1; l < AXN_GHI1; l++) {
#pragma HLS UNROLL
        X5[l] = in[l]; }
    for (int l = AXN_GLO3; l < AXN_GHI3; l++) {
#pragma HLS UNROLL
        X5[l] = in[l]; }
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N4; l++) {
#pragma HLS UNROLL
        X5[l] = R4[l]; }
#endif
    word32_t EA5[MONO_LEND_MAX], EB5[MONO_LEND_MAX], EY5[MONO_LEND_MAX], XB5[MONO_XLEND_MAX], XY5[MONO_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA5 complete
#pragma HLS ARRAY_PARTITION variable=EB5 complete
#pragma HLS ARRAY_PARTITION variable=EY5 complete
#pragma HLS ARRAY_PARTITION variable=XB5 complete
#pragma HLS ARRAY_PARTITION variable=XY5 complete
    for (int q = 0; q < MONO_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA5[q] = 0; EB5[q] = 0; EY5[q] = 0; }
    for (int q = 0; q < MONO_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB5[q] = 0; XY5[q] = 0; }
    word32_t EA25[MONO2_LEND_MAX], EB25[MONO2_LEND_MAX], EY25[MONO2_LEND_MAX], XB25[MONO2_XLEND_MAX], XY25[MONO2_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA25 complete
#pragma HLS ARRAY_PARTITION variable=EB25 complete
#pragma HLS ARRAY_PARTITION variable=EY25 complete
#pragma HLS ARRAY_PARTITION variable=XB25 complete
#pragma HLS ARRAY_PARTITION variable=XY25 complete
    for (int q = 0; q < MONO2_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA25[q] = 0; EB25[q] = 0; EY25[q] = 0; }
    for (int q = 0; q < MONO2_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB25[q] = 0; XY25[q] = 0; }
#if HAS_ARX
    lane_t a5[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=a5 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        a5[l] = 0; }
    axn_ops1<axn_b(5), 0>(X5, rg[1], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EA5 + 0, EB5 + 0);
    axn_ops1<axn_b(6), 0>(X5, rg[1], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EA5 + 4, EB5 + 4);
    axn_ops1<axn_b(7), 0>(X5, rg[1], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EA5 + 8, EB5 + 8);
    axn_ops1<axn_b(8), 0>(X5, rg[1], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EA5 + 12, EB5 + 12);
    axn_ops1<axn_b(14), 1>(X5, rg[3], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EA25 + 0, EB25 + 0);
    axn_ops1<axn_b(15), 1>(X5, rg[3], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EA25 + 4, EB25 + 4);
    axn_ops1<axn_b(16), 1>(X5, rg[3], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EA25 + 8, EB25 + 8);
    axn_ops1<axn_b(17), 1>(X5, rg[3], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EA25 + 12, EB25 + 12);
#endif
#if HAS(M_MONO)
    lane_t m5[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m5 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m5[l] = 0; }
    monk_lx5(X5, dd[4], m5, (HAS_ARX ? !(bool)mp[4] : false), EA5, EB5, EY5, XB5, XY5);
    lane_t m25[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m25 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m25[l] = 0; }
    monk2_lx5(X5, dd2[4], m25, (HAS_ARX ? !(bool)mp2[4] : false), EA25, EB25, EY25, XB25, XY25);
#else
    for (int q = 0; q < 16; q++) {
#pragma HLS UNROLL
        EY5[q] = alu_addp<32>(EA5[q], EB5[q]); }
    for (int q = 0; q < 16; q++) {
#pragma HLS UNROLL
        EY25[q] = alu_addp<32>(EA25[q], EB25[q]); }
#endif
#if HAS_ARX
    axn_fin1<axn_b(5), 0>(X5, rg[1], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EY5 + 0, a5);
    axn_fin1<axn_b(6), 0>(X5, rg[1], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EY5 + 4, a5);
    axn_fin1<axn_b(7), 0>(X5, rg[1], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EY5 + 8, a5);
    axn_fin1<axn_b(8), 0>(X5, rg[1], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EY5 + 12, a5);
    axn_fin1<axn_b(14), 1>(X5, rg[3], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EY25 + 0, a5);
    axn_fin1<axn_b(15), 1>(X5, rg[3], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EY25 + 4, a5);
    axn_fin1<axn_b(16), 1>(X5, rg[3], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EY25 + 8, a5);
    axn_fin1<axn_b(17), 1>(X5, rg[3], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EY25 + 12, a5);
#endif
    lane_t N5[LV_N5 > 0 ? LV_N5 : 1];
#pragma HLS ARRAY_PARTITION variable=N5 complete
#if HAS_ARX
    for (int l = AXN_GLO1; l < AXN_GHI1; l++) {
#pragma HLS UNROLL
        const int bl = (l - (AXN_GLO1)) % AXN_BL; N5[l] = (bl == 0 || bl == 1 || bl == 2 || bl == 3 || bl == 4 || bl == 5 || bl == 6 || bl == 7 || bl == 16 || bl == 17) ? a5[l] : X5[l]; }
    for (int l = AXN_GLO3; l < AXN_GHI3; l++) {
#pragma HLS UNROLL
        const int bl = (l - (AXN_GLO3)) % AXN_BL; N5[l] = (bl == 0 || bl == 1 || bl == 2 || bl == 3 || bl == 4 || bl == 5 || bl == 6 || bl == 7 || bl == 16 || bl == 17) ? a5[l] : X5[l]; }
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < MONO2_BASE; l++) {
#pragma HLS UNROLL
        N5[l] = (l < 404 && true) ? X5[l] : m5[l]; }
    for (int l = MONO2_BASE; l < LV_N5; l++) {
#pragma HLS UNROLL
        N5[l] = (l < 456 && true) ? X5[l] : m25[l]; }
#endif
    lane_t X6[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=X6 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        X6[l] = 0; }
#if HAS_ARX
    for (int l = AXN_GLO1; l < AXN_GHI1; l++) {
#pragma HLS UNROLL
        X6[l] = R5[l]; }
    for (int l = AXN_GLO3; l < AXN_GHI3; l++) {
#pragma HLS UNROLL
        X6[l] = R5[l]; }
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N5; l++) {
#pragma HLS UNROLL
        X6[l] = R5[l]; }
#endif
    word32_t EA6[MONO_LEND_MAX], EB6[MONO_LEND_MAX], EY6[MONO_LEND_MAX], XB6[MONO_XLEND_MAX], XY6[MONO_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA6 complete
#pragma HLS ARRAY_PARTITION variable=EB6 complete
#pragma HLS ARRAY_PARTITION variable=EY6 complete
#pragma HLS ARRAY_PARTITION variable=XB6 complete
#pragma HLS ARRAY_PARTITION variable=XY6 complete
    for (int q = 0; q < MONO_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA6[q] = 0; EB6[q] = 0; EY6[q] = 0; }
    for (int q = 0; q < MONO_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB6[q] = 0; XY6[q] = 0; }
    word32_t EA26[MONO2_LEND_MAX], EB26[MONO2_LEND_MAX], EY26[MONO2_LEND_MAX], XB26[MONO2_XLEND_MAX], XY26[MONO2_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA26 complete
#pragma HLS ARRAY_PARTITION variable=EB26 complete
#pragma HLS ARRAY_PARTITION variable=EY26 complete
#pragma HLS ARRAY_PARTITION variable=XB26 complete
#pragma HLS ARRAY_PARTITION variable=XY26 complete
    for (int q = 0; q < MONO2_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA26[q] = 0; EB26[q] = 0; EY26[q] = 0; }
    for (int q = 0; q < MONO2_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB26[q] = 0; XY26[q] = 0; }
#if HAS_ARX
    lane_t a6[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=a6 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        a6[l] = 0; }
    axn_ops2<axn_b(5), 0>(X6, ar1[5], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[5]), EA6 + 0, EB6 + 0);
    axn_ops2<axn_b(6), 0>(X6, ar1[5], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[5]), EA6 + 4, EB6 + 4);
    axn_ops2<axn_b(7), 0>(X6, ar1[5], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[5]), EA6 + 8, EB6 + 8);
    axn_ops2<axn_b(8), 0>(X6, ar1[5], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[5]), EA6 + 12, EB6 + 12);
    axn_ops2<axn_b(14), 1>(X6, ar3[5], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[5]), EA26 + 0, EB26 + 0);
    axn_ops2<axn_b(15), 1>(X6, ar3[5], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[5]), EA26 + 4, EB26 + 4);
    axn_ops2<axn_b(16), 1>(X6, ar3[5], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[5]), EA26 + 8, EB26 + 8);
    axn_ops2<axn_b(17), 1>(X6, ar3[5], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[5]), EA26 + 12, EB26 + 12);
#endif
#if HAS(M_MONO)
    lane_t m6[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m6 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m6[l] = 0; }
    monk_lx6(X6, dd[5], m6, (HAS_ARX ? !(bool)mp[5] : false), EA6, EB6, EY6, XB6, XY6);
    lane_t m26[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m26 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m26[l] = 0; }
    monk2_lx6(X6, dd2[5], m26, (HAS_ARX ? !(bool)mp2[5] : false), EA26, EB26, EY26, XB26, XY26);
#else
    for (int q = 0; q < 16; q++) {
#pragma HLS UNROLL
        EY6[q] = alu_addp<32>(EA6[q], EB6[q]); }
    for (int q = 0; q < 16; q++) {
#pragma HLS UNROLL
        EY26[q] = alu_addp<32>(EA26[q], EB26[q]); }
#endif
#if HAS_ARX
    axn_fin2<axn_b(5), 0>(X6, ar1[5], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[5]), EY6 + 0, a6);
    axn_fin2<axn_b(6), 0>(X6, ar1[5], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[5]), EY6 + 4, a6);
    axn_fin2<axn_b(7), 0>(X6, ar1[5], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[5]), EY6 + 8, a6);
    axn_fin2<axn_b(8), 0>(X6, ar1[5], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[5]), EY6 + 12, a6);
    axn_fin2<axn_b(14), 1>(X6, ar3[5], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[5]), EY26 + 0, a6);
    axn_fin2<axn_b(15), 1>(X6, ar3[5], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[5]), EY26 + 4, a6);
    axn_fin2<axn_b(16), 1>(X6, ar3[5], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[5]), EY26 + 8, a6);
    axn_fin2<axn_b(17), 1>(X6, ar3[5], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[5]), EY26 + 12, a6);
#endif
    lane_t N6[LV_N6 > 0 ? LV_N6 : 1];
#pragma HLS ARRAY_PARTITION variable=N6 complete
#if HAS_ARX
    for (int l = AXN_GLO1; l < AXN_GHI1; l++) {
#pragma HLS UNROLL
        const int bl = (l - (AXN_GLO1)) % AXN_BL; N6[l] = (bl == 0 || bl == 1 || bl == 2 || bl == 3 || bl == 4 || bl == 5 || bl == 6 || bl == 7) ? a6[l] : X6[l]; }
    for (int l = AXN_GLO3; l < AXN_GHI3; l++) {
#pragma HLS UNROLL
        const int bl = (l - (AXN_GLO3)) % AXN_BL; N6[l] = (bl == 0 || bl == 1 || bl == 2 || bl == 3 || bl == 4 || bl == 5 || bl == 6 || bl == 7) ? a6[l] : X6[l]; }
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < MONO2_BASE; l++) {
#pragma HLS UNROLL
        N6[l] = (l < 404 && true) ? X6[l] : m6[l]; }
    for (int l = MONO2_BASE; l < LV_N6; l++) {
#pragma HLS UNROLL
        N6[l] = (l < 456 && true) ? X6[l] : m26[l]; }
#endif
    lane_t X7[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=X7 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        X7[l] = 0; }
#if HAS_ARX
    for (int l = AXN_GLO0; l < AXN_GHI0; l++) {
#pragma HLS UNROLL
        X7[l] = in[l]; }
    for (int l = AXN_GLO1; l < AXN_GHI1; l++) {
#pragma HLS UNROLL
        X7[l] = R6[l]; }
    for (int l = AXN_GLO2; l < AXN_GHI2; l++) {
#pragma HLS UNROLL
        X7[l] = in[l]; }
    for (int l = AXN_GLO3; l < AXN_GHI3; l++) {
#pragma HLS UNROLL
        X7[l] = R6[l]; }
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N6; l++) {
#pragma HLS UNROLL
        X7[l] = R6[l]; }
#endif
    word32_t EA7[MONO_LEND_MAX], EB7[MONO_LEND_MAX], EY7[MONO_LEND_MAX], XB7[MONO_XLEND_MAX], XY7[MONO_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA7 complete
#pragma HLS ARRAY_PARTITION variable=EB7 complete
#pragma HLS ARRAY_PARTITION variable=EY7 complete
#pragma HLS ARRAY_PARTITION variable=XB7 complete
#pragma HLS ARRAY_PARTITION variable=XY7 complete
    for (int q = 0; q < MONO_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA7[q] = 0; EB7[q] = 0; EY7[q] = 0; }
    for (int q = 0; q < MONO_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB7[q] = 0; XY7[q] = 0; }
    word32_t EA27[MONO2_LEND_MAX], EB27[MONO2_LEND_MAX], EY27[MONO2_LEND_MAX], XB27[MONO2_XLEND_MAX], XY27[MONO2_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA27 complete
#pragma HLS ARRAY_PARTITION variable=EB27 complete
#pragma HLS ARRAY_PARTITION variable=EY27 complete
#pragma HLS ARRAY_PARTITION variable=XB27 complete
#pragma HLS ARRAY_PARTITION variable=XY27 complete
    for (int q = 0; q < MONO2_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA27[q] = 0; EB27[q] = 0; EY27[q] = 0; }
    for (int q = 0; q < MONO2_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB27[q] = 0; XY27[q] = 0; }
#if HAS_ARX
    lane_t a7[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=a7 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        a7[l] = 0; }
    axn_ops1<axn_b(0), 0>(X7, rg[0], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EA7 + 0, EB7 + 0);
    axn_ops1<axn_b(1), 0>(X7, rg[0], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EA7 + 4, EB7 + 4);
    axn_ops1<axn_b(2), 0>(X7, rg[0], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EA7 + 8, EB7 + 8);
    axn_ops1<axn_b(3), 0>(X7, rg[0], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EA7 + 12, EB7 + 12);
    axn_ops1<axn_b(4), 0>(X7, rg[0], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EA7 + 16, EB7 + 16);
    axn_ops3<axn_b(5), 0>(X7, ar1[6], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[6]), EA7 + 20, EB7 + 20);
    axn_ops3<axn_b(6), 0>(X7, ar1[6], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[6]), EA7 + 24, EB7 + 24);
    axn_ops3<axn_b(7), 0>(X7, ar1[6], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[6]), EA7 + 28, EB7 + 28);
    axn_ops3<axn_b(8), 0>(X7, ar1[6], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[6]), EA7 + 32, EB7 + 32);
    axn_ops1<axn_b(9), 1>(X7, rg[2], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EA27 + 0, EB27 + 0);
    axn_ops1<axn_b(10), 1>(X7, rg[2], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EA27 + 4, EB27 + 4);
    axn_ops1<axn_b(11), 1>(X7, rg[2], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EA27 + 8, EB27 + 8);
    axn_ops1<axn_b(12), 1>(X7, rg[2], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EA27 + 12, EB27 + 12);
    axn_ops1<axn_b(13), 1>(X7, rg[2], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EA27 + 16, EB27 + 16);
    axn_ops3<axn_b(14), 1>(X7, ar3[6], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[6]), EA27 + 20, EB27 + 20);
    axn_ops3<axn_b(15), 1>(X7, ar3[6], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[6]), EA27 + 24, EB27 + 24);
    axn_ops3<axn_b(16), 1>(X7, ar3[6], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[6]), EA27 + 28, EB27 + 28);
    axn_ops3<axn_b(17), 1>(X7, ar3[6], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[6]), EA27 + 32, EB27 + 32);
#endif
#if HAS(M_MONO)
    lane_t m7[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m7 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m7[l] = 0; }
    monk_lx7(X7, dd[6], m7, (HAS_ARX ? !(bool)mp[6] : false), EA7, EB7, EY7, XB7, XY7);
    lane_t m27[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m27 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m27[l] = 0; }
    monk2_lx7(X7, dd2[6], m27, (HAS_ARX ? !(bool)mp2[6] : false), EA27, EB27, EY27, XB27, XY27);
#else
    for (int q = 0; q < 36; q++) {
#pragma HLS UNROLL
        EY7[q] = alu_addp<32>(EA7[q], EB7[q]); }
    for (int q = 0; q < 36; q++) {
#pragma HLS UNROLL
        EY27[q] = alu_addp<32>(EA27[q], EB27[q]); }
#endif
#if HAS_ARX
    axn_fin1<axn_b(0), 0>(X7, rg[0], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EY7 + 0, a7);
    axn_fin1<axn_b(1), 0>(X7, rg[0], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EY7 + 4, a7);
    axn_fin1<axn_b(2), 0>(X7, rg[0], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EY7 + 8, a7);
    axn_fin1<axn_b(3), 0>(X7, rg[0], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EY7 + 12, a7);
    axn_fin1<axn_b(4), 0>(X7, rg[0], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EY7 + 16, a7);
    axn_fin3<axn_b(5), 0>(X7, ar1[6], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[6]), EY7 + 20, a7);
    axn_fin3<axn_b(6), 0>(X7, ar1[6], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[6]), EY7 + 24, a7);
    axn_fin3<axn_b(7), 0>(X7, ar1[6], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[6]), EY7 + 28, a7);
    axn_fin3<axn_b(8), 0>(X7, ar1[6], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[6]), EY7 + 32, a7);
    axn_fin1<axn_b(9), 1>(X7, rg[2], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EY27 + 0, a7);
    axn_fin1<axn_b(10), 1>(X7, rg[2], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EY27 + 4, a7);
    axn_fin1<axn_b(11), 1>(X7, rg[2], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EY27 + 8, a7);
    axn_fin1<axn_b(12), 1>(X7, rg[2], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EY27 + 12, a7);
    axn_fin1<axn_b(13), 1>(X7, rg[2], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)blake), EY27 + 16, a7);
    axn_fin3<axn_b(14), 1>(X7, ar3[6], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[6]), EY27 + 20, a7);
    axn_fin3<axn_b(15), 1>(X7, ar3[6], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[6]), EY27 + 24, a7);
    axn_fin3<axn_b(16), 1>(X7, ar3[6], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[6]), EY27 + 28, a7);
    axn_fin3<axn_b(17), 1>(X7, ar3[6], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[6]), EY27 + 32, a7);
#endif
    lane_t N7[LV_N7 > 0 ? LV_N7 : 1];
#pragma HLS ARRAY_PARTITION variable=N7 complete
#if HAS_ARX
    for (int l = AXN_GLO0; l < AXN_GHI0; l++) {
#pragma HLS UNROLL
        const int bl = (l - (AXN_GLO0)) % AXN_BL; N7[l] = (bl == 0 || bl == 1 || bl == 2 || bl == 3 || bl == 4 || bl == 5 || bl == 6 || bl == 7 || bl == 16 || bl == 17) ? a7[l] : X7[l]; }
    for (int l = AXN_GLO1; l < AXN_GHI1; l++) {
#pragma HLS UNROLL
        const int bl = (l - (AXN_GLO1)) % AXN_BL; N7[l] = (bl == 1 || bl == 2 || bl == 5 || bl == 6) ? a7[l] : X7[l]; }
    for (int l = AXN_GLO2; l < AXN_GHI2; l++) {
#pragma HLS UNROLL
        const int bl = (l - (AXN_GLO2)) % AXN_BL; N7[l] = (bl == 0 || bl == 1 || bl == 2 || bl == 3 || bl == 4 || bl == 5 || bl == 6 || bl == 7 || bl == 16 || bl == 17) ? a7[l] : X7[l]; }
    for (int l = AXN_GLO3; l < AXN_GHI3; l++) {
#pragma HLS UNROLL
        const int bl = (l - (AXN_GLO3)) % AXN_BL; N7[l] = (bl == 1 || bl == 2 || bl == 5 || bl == 6) ? a7[l] : X7[l]; }
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < MONO2_BASE; l++) {
#pragma HLS UNROLL
        N7[l] = (l < 404 && true) ? X7[l] : m7[l]; }
    for (int l = MONO2_BASE; l < LV_N7; l++) {
#pragma HLS UNROLL
        N7[l] = (l < 456 && true) ? X7[l] : m27[l]; }
#endif
    lane_t X8[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=X8 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        X8[l] = 0; }
#if HAS_ARX
    for (int l = AXN_GLO0; l < AXN_GHI0; l++) {
#pragma HLS UNROLL
        X8[l] = R7[l]; }
    for (int l = AXN_GLO1; l < AXN_GHI1; l++) {
#pragma HLS UNROLL
        X8[l] = R7[l]; }
    for (int l = AXN_GLO2; l < AXN_GHI2; l++) {
#pragma HLS UNROLL
        X8[l] = R7[l]; }
    for (int l = AXN_GLO3; l < AXN_GHI3; l++) {
#pragma HLS UNROLL
        X8[l] = R7[l]; }
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N7; l++) {
#pragma HLS UNROLL
        X8[l] = R7[l]; }
#endif
    word32_t EA8[MONO_LEND_MAX], EB8[MONO_LEND_MAX], EY8[MONO_LEND_MAX], XB8[MONO_XLEND_MAX], XY8[MONO_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA8 complete
#pragma HLS ARRAY_PARTITION variable=EB8 complete
#pragma HLS ARRAY_PARTITION variable=EY8 complete
#pragma HLS ARRAY_PARTITION variable=XB8 complete
#pragma HLS ARRAY_PARTITION variable=XY8 complete
    for (int q = 0; q < MONO_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA8[q] = 0; EB8[q] = 0; EY8[q] = 0; }
    for (int q = 0; q < MONO_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB8[q] = 0; XY8[q] = 0; }
    word32_t EA28[MONO2_LEND_MAX], EB28[MONO2_LEND_MAX], EY28[MONO2_LEND_MAX], XB28[MONO2_XLEND_MAX], XY28[MONO2_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA28 complete
#pragma HLS ARRAY_PARTITION variable=EB28 complete
#pragma HLS ARRAY_PARTITION variable=EY28 complete
#pragma HLS ARRAY_PARTITION variable=XB28 complete
#pragma HLS ARRAY_PARTITION variable=XY28 complete
    for (int q = 0; q < MONO2_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA28[q] = 0; EB28[q] = 0; EY28[q] = 0; }
    for (int q = 0; q < MONO2_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB28[q] = 0; XY28[q] = 0; }
#if HAS_ARX
    lane_t a8[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=a8 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        a8[l] = 0; }
    axn_ops2<axn_b(0), 0>(X8, ar0[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[7]), EA8 + 0, EB8 + 0);
    axn_ops2<axn_b(1), 0>(X8, ar0[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[7]), EA8 + 4, EB8 + 4);
    axn_ops2<axn_b(2), 0>(X8, ar0[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[7]), EA8 + 8, EB8 + 8);
    axn_ops2<axn_b(3), 0>(X8, ar0[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[7]), EA8 + 12, EB8 + 12);
    axn_ops2<axn_b(4), 0>(X8, ar0[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[7]), EA8 + 16, EB8 + 16);
    axn_ops4<axn_b(5), 0>(X8, ar1[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[7]), EA8 + 20, EB8 + 20);
    axn_ops4<axn_b(6), 0>(X8, ar1[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[7]), EA8 + 24, EB8 + 24);
    axn_ops4<axn_b(7), 0>(X8, ar1[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[7]), EA8 + 28, EB8 + 28);
    axn_ops4<axn_b(8), 0>(X8, ar1[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[7]), EA8 + 32, EB8 + 32);
    axn_ops2<axn_b(9), 1>(X8, ar2[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[7]), EA28 + 0, EB28 + 0);
    axn_ops2<axn_b(10), 1>(X8, ar2[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[7]), EA28 + 4, EB28 + 4);
    axn_ops2<axn_b(11), 1>(X8, ar2[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[7]), EA28 + 8, EB28 + 8);
    axn_ops2<axn_b(12), 1>(X8, ar2[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[7]), EA28 + 12, EB28 + 12);
    axn_ops2<axn_b(13), 1>(X8, ar2[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[7]), EA28 + 16, EB28 + 16);
    axn_ops4<axn_b(14), 1>(X8, ar3[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[7]), EA28 + 20, EB28 + 20);
    axn_ops4<axn_b(15), 1>(X8, ar3[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[7]), EA28 + 24, EB28 + 24);
    axn_ops4<axn_b(16), 1>(X8, ar3[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[7]), EA28 + 28, EB28 + 28);
    axn_ops4<axn_b(17), 1>(X8, ar3[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[7]), EA28 + 32, EB28 + 32);
#endif
#if HAS(M_MONO)
    lane_t m8[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m8 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m8[l] = 0; }
    monk_lx8(X8, dd[7], m8, (HAS_ARX ? !(bool)mp[7] : false), EA8, EB8, EY8, XB8, XY8);
    lane_t m28[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m28 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m28[l] = 0; }
    monk2_lx8(X8, dd2[7], m28, (HAS_ARX ? !(bool)mp2[7] : false), EA28, EB28, EY28, XB28, XY28);
#else
    for (int q = 0; q < 36; q++) {
#pragma HLS UNROLL
        EY8[q] = alu_addp<32>(EA8[q], EB8[q]); }
    for (int q = 0; q < 36; q++) {
#pragma HLS UNROLL
        EY28[q] = alu_addp<32>(EA28[q], EB28[q]); }
#endif
#if HAS_ARX
    axn_fin2<axn_b(0), 0>(X8, ar0[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[7]), EY8 + 0, a8);
    axn_fin2<axn_b(1), 0>(X8, ar0[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[7]), EY8 + 4, a8);
    axn_fin2<axn_b(2), 0>(X8, ar0[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[7]), EY8 + 8, a8);
    axn_fin2<axn_b(3), 0>(X8, ar0[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[7]), EY8 + 12, a8);
    axn_fin2<axn_b(4), 0>(X8, ar0[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[7]), EY8 + 16, a8);
    axn_fin4<axn_b(5), 0>(X8, ar1[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[7]), EY8 + 20, a8);
    axn_fin4<axn_b(6), 0>(X8, ar1[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[7]), EY8 + 24, a8);
    axn_fin4<axn_b(7), 0>(X8, ar1[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[7]), EY8 + 28, a8);
    axn_fin4<axn_b(8), 0>(X8, ar1[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[7]), EY8 + 32, a8);
    axn_fin2<axn_b(9), 1>(X8, ar2[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[7]), EY28 + 0, a8);
    axn_fin2<axn_b(10), 1>(X8, ar2[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[7]), EY28 + 4, a8);
    axn_fin2<axn_b(11), 1>(X8, ar2[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[7]), EY28 + 8, a8);
    axn_fin2<axn_b(12), 1>(X8, ar2[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[7]), EY28 + 12, a8);
    axn_fin2<axn_b(13), 1>(X8, ar2[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[7]), EY28 + 16, a8);
    axn_fin4<axn_b(14), 1>(X8, ar3[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[7]), EY28 + 20, a8);
    axn_fin4<axn_b(15), 1>(X8, ar3[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[7]), EY28 + 24, a8);
    axn_fin4<axn_b(16), 1>(X8, ar3[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[7]), EY28 + 28, a8);
    axn_fin4<axn_b(17), 1>(X8, ar3[7], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[7]), EY28 + 32, a8);
#endif
    lane_t N8[LV_N8 > 0 ? LV_N8 : 1];
#pragma HLS ARRAY_PARTITION variable=N8 complete
#if HAS_ARX
    for (int l = AXN_GLO0; l < AXN_GHI0; l++) {
#pragma HLS UNROLL
        const int bl = (l - (AXN_GLO0)) % AXN_BL; N8[l] = (bl == 0 || bl == 1 || bl == 2 || bl == 3 || bl == 4 || bl == 5 || bl == 6 || bl == 7) ? a8[l] : X8[l]; }
    for (int l = AXN_GLO1; l < AXN_GHI1; l++) {
#pragma HLS UNROLL
        const int bl = (l - (AXN_GLO1)) % AXN_BL; N8[l] = (bl == 0 || bl == 1 || bl == 2 || bl == 3 || bl == 4 || bl == 5 || bl == 6 || bl == 7 || bl == 16 || bl == 17) ? a8[l] : X8[l]; }
    for (int l = AXN_GLO2; l < AXN_GHI2; l++) {
#pragma HLS UNROLL
        const int bl = (l - (AXN_GLO2)) % AXN_BL; N8[l] = (bl == 0 || bl == 1 || bl == 2 || bl == 3 || bl == 4 || bl == 5 || bl == 6 || bl == 7) ? a8[l] : X8[l]; }
    for (int l = AXN_GLO3; l < AXN_GHI3; l++) {
#pragma HLS UNROLL
        const int bl = (l - (AXN_GLO3)) % AXN_BL; N8[l] = (bl == 0 || bl == 1 || bl == 2 || bl == 3 || bl == 4 || bl == 5 || bl == 6 || bl == 7 || bl == 16 || bl == 17) ? a8[l] : X8[l]; }
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < MONO2_BASE; l++) {
#pragma HLS UNROLL
        N8[l] = (l < 404 && true) ? X8[l] : m8[l]; }
    for (int l = MONO2_BASE; l < LV_N8; l++) {
#pragma HLS UNROLL
        N8[l] = (l < 456 && true) ? X8[l] : m28[l]; }
#endif
    lane_t X9[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=X9 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        X9[l] = 0; }
#if HAS_ARX
    for (int l = AXN_GLO0; l < AXN_GHI0; l++) {
#pragma HLS UNROLL
        X9[l] = R8[l]; }
    for (int l = AXN_GLO1; l < AXN_GHI1; l++) {
#pragma HLS UNROLL
        X9[l] = R8[l]; }
    for (int l = AXN_GLO2; l < AXN_GHI2; l++) {
#pragma HLS UNROLL
        X9[l] = R8[l]; }
    for (int l = AXN_GLO3; l < AXN_GHI3; l++) {
#pragma HLS UNROLL
        X9[l] = R8[l]; }
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N8; l++) {
#pragma HLS UNROLL
        X9[l] = R8[l]; }
#endif
    word32_t EA9[MONO_LEND_MAX], EB9[MONO_LEND_MAX], EY9[MONO_LEND_MAX], XB9[MONO_XLEND_MAX], XY9[MONO_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA9 complete
#pragma HLS ARRAY_PARTITION variable=EB9 complete
#pragma HLS ARRAY_PARTITION variable=EY9 complete
#pragma HLS ARRAY_PARTITION variable=XB9 complete
#pragma HLS ARRAY_PARTITION variable=XY9 complete
    for (int q = 0; q < MONO_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA9[q] = 0; EB9[q] = 0; EY9[q] = 0; }
    for (int q = 0; q < MONO_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB9[q] = 0; XY9[q] = 0; }
    word32_t EA29[MONO2_LEND_MAX], EB29[MONO2_LEND_MAX], EY29[MONO2_LEND_MAX], XB29[MONO2_XLEND_MAX], XY29[MONO2_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA29 complete
#pragma HLS ARRAY_PARTITION variable=EB29 complete
#pragma HLS ARRAY_PARTITION variable=EY29 complete
#pragma HLS ARRAY_PARTITION variable=XB29 complete
#pragma HLS ARRAY_PARTITION variable=XY29 complete
    for (int q = 0; q < MONO2_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA29[q] = 0; EB29[q] = 0; EY29[q] = 0; }
    for (int q = 0; q < MONO2_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB29[q] = 0; XY29[q] = 0; }
#if HAS_ARX
    lane_t a9[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=a9 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        a9[l] = 0; }
    axn_ops3<axn_b(0), 0>(X9, ar0[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[8]), EA9 + 0, EB9 + 0);
    axn_ops3<axn_b(1), 0>(X9, ar0[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[8]), EA9 + 4, EB9 + 4);
    axn_ops3<axn_b(2), 0>(X9, ar0[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[8]), EA9 + 8, EB9 + 8);
    axn_ops3<axn_b(3), 0>(X9, ar0[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[8]), EA9 + 12, EB9 + 12);
    axn_ops3<axn_b(4), 0>(X9, ar0[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[8]), EA9 + 16, EB9 + 16);
    axn_ops5<axn_b(5), 0>(X9, ar1[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[8]), EA9 + 20, EB9 + 20);
    axn_ops5<axn_b(6), 0>(X9, ar1[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[8]), EA9 + 24, EB9 + 24);
    axn_ops5<axn_b(7), 0>(X9, ar1[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[8]), EA9 + 28, EB9 + 28);
    axn_ops5<axn_b(8), 0>(X9, ar1[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[8]), EA9 + 32, EB9 + 32);
    axn_ops3<axn_b(9), 1>(X9, ar2[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[8]), EA29 + 0, EB29 + 0);
    axn_ops3<axn_b(10), 1>(X9, ar2[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[8]), EA29 + 4, EB29 + 4);
    axn_ops3<axn_b(11), 1>(X9, ar2[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[8]), EA29 + 8, EB29 + 8);
    axn_ops3<axn_b(12), 1>(X9, ar2[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[8]), EA29 + 12, EB29 + 12);
    axn_ops3<axn_b(13), 1>(X9, ar2[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[8]), EA29 + 16, EB29 + 16);
    axn_ops5<axn_b(14), 1>(X9, ar3[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[8]), EA29 + 20, EB29 + 20);
    axn_ops5<axn_b(15), 1>(X9, ar3[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[8]), EA29 + 24, EB29 + 24);
    axn_ops5<axn_b(16), 1>(X9, ar3[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[8]), EA29 + 28, EB29 + 28);
    axn_ops5<axn_b(17), 1>(X9, ar3[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[8]), EA29 + 32, EB29 + 32);
#endif
#if HAS(M_MONO)
    lane_t m9[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m9 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m9[l] = 0; }
    monk_lx9(X9, dd[8], m9, (HAS_ARX ? !(bool)mp[8] : false), EA9, EB9, EY9, XB9, XY9);
    lane_t m29[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m29 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m29[l] = 0; }
    monk2_lx9(X9, dd2[8], m29, (HAS_ARX ? !(bool)mp2[8] : false), EA29, EB29, EY29, XB29, XY29);
#else
    for (int q = 0; q < 36; q++) {
#pragma HLS UNROLL
        EY9[q] = alu_addp<32>(EA9[q], EB9[q]); }
    for (int q = 0; q < 36; q++) {
#pragma HLS UNROLL
        EY29[q] = alu_addp<32>(EA29[q], EB29[q]); }
#endif
#if HAS_ARX
    axn_fin3<axn_b(0), 0>(X9, ar0[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[8]), EY9 + 0, a9);
    axn_fin3<axn_b(1), 0>(X9, ar0[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[8]), EY9 + 4, a9);
    axn_fin3<axn_b(2), 0>(X9, ar0[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[8]), EY9 + 8, a9);
    axn_fin3<axn_b(3), 0>(X9, ar0[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[8]), EY9 + 12, a9);
    axn_fin3<axn_b(4), 0>(X9, ar0[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[8]), EY9 + 16, a9);
    axn_fin5<axn_b(5), 0>(X9, ar1[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[8]), EY9 + 20, a9);
    axn_fin5<axn_b(6), 0>(X9, ar1[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[8]), EY9 + 24, a9);
    axn_fin5<axn_b(7), 0>(X9, ar1[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[8]), EY9 + 28, a9);
    axn_fin5<axn_b(8), 0>(X9, ar1[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[8]), EY9 + 32, a9);
    axn_fin3<axn_b(9), 1>(X9, ar2[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[8]), EY29 + 0, a9);
    axn_fin3<axn_b(10), 1>(X9, ar2[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[8]), EY29 + 4, a9);
    axn_fin3<axn_b(11), 1>(X9, ar2[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[8]), EY29 + 8, a9);
    axn_fin3<axn_b(12), 1>(X9, ar2[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[8]), EY29 + 12, a9);
    axn_fin3<axn_b(13), 1>(X9, ar2[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[8]), EY29 + 16, a9);
    axn_fin5<axn_b(14), 1>(X9, ar3[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[8]), EY29 + 20, a9);
    axn_fin5<axn_b(15), 1>(X9, ar3[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[8]), EY29 + 24, a9);
    axn_fin5<axn_b(16), 1>(X9, ar3[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[8]), EY29 + 28, a9);
    axn_fin5<axn_b(17), 1>(X9, ar3[8], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[8]), EY29 + 32, a9);
#endif
    lane_t N9[LV_N9 > 0 ? LV_N9 : 1];
#pragma HLS ARRAY_PARTITION variable=N9 complete
#if HAS_ARX
    for (int l = AXN_GLO0; l < AXN_GHI0; l++) {
#pragma HLS UNROLL
        const int bl = (l - (AXN_GLO0)) % AXN_BL; N9[l] = (bl == 1 || bl == 2 || bl == 5 || bl == 6) ? a9[l] : X9[l]; }
    for (int l = AXN_GLO1; l < AXN_GHI1; l++) {
#pragma HLS UNROLL
        const int bl = (l - (AXN_GLO1)) % AXN_BL; N9[l] = (bl == 0 || bl == 3 || bl == 4 || bl == 7) ? a9[l] : X9[l]; }
    for (int l = AXN_GLO2; l < AXN_GHI2; l++) {
#pragma HLS UNROLL
        const int bl = (l - (AXN_GLO2)) % AXN_BL; N9[l] = (bl == 1 || bl == 2 || bl == 5 || bl == 6) ? a9[l] : X9[l]; }
    for (int l = AXN_GLO3; l < AXN_GHI3; l++) {
#pragma HLS UNROLL
        const int bl = (l - (AXN_GLO3)) % AXN_BL; N9[l] = (bl == 0 || bl == 3 || bl == 4 || bl == 7) ? a9[l] : X9[l]; }
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < MONO2_BASE; l++) {
#pragma HLS UNROLL
        N9[l] = (l < 404 && true) ? X9[l] : m9[l]; }
    for (int l = MONO2_BASE; l < LV_N9; l++) {
#pragma HLS UNROLL
        N9[l] = (l < 456 && true) ? X9[l] : m29[l]; }
#endif
    lane_t X10[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=X10 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        X10[l] = 0; }
#if HAS_ARX
    for (int l = AXN_GLO0; l < AXN_GHI0; l++) {
#pragma HLS UNROLL
        X10[l] = R9[l]; }
    for (int l = AXN_GLO1; l < AXN_GHI1; l++) {
#pragma HLS UNROLL
        X10[l] = R9[l]; }
    for (int l = AXN_GLO2; l < AXN_GHI2; l++) {
#pragma HLS UNROLL
        X10[l] = R9[l]; }
    for (int l = AXN_GLO3; l < AXN_GHI3; l++) {
#pragma HLS UNROLL
        X10[l] = R9[l]; }
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N9; l++) {
#pragma HLS UNROLL
        X10[l] = R9[l]; }
#endif
    word32_t EA10[MONO_LEND_MAX], EB10[MONO_LEND_MAX], EY10[MONO_LEND_MAX], XB10[MONO_XLEND_MAX], XY10[MONO_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA10 complete
#pragma HLS ARRAY_PARTITION variable=EB10 complete
#pragma HLS ARRAY_PARTITION variable=EY10 complete
#pragma HLS ARRAY_PARTITION variable=XB10 complete
#pragma HLS ARRAY_PARTITION variable=XY10 complete
    for (int q = 0; q < MONO_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA10[q] = 0; EB10[q] = 0; EY10[q] = 0; }
    for (int q = 0; q < MONO_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB10[q] = 0; XY10[q] = 0; }
    word32_t EA210[MONO2_LEND_MAX], EB210[MONO2_LEND_MAX], EY210[MONO2_LEND_MAX], XB210[MONO2_XLEND_MAX], XY210[MONO2_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA210 complete
#pragma HLS ARRAY_PARTITION variable=EB210 complete
#pragma HLS ARRAY_PARTITION variable=EY210 complete
#pragma HLS ARRAY_PARTITION variable=XB210 complete
#pragma HLS ARRAY_PARTITION variable=XY210 complete
    for (int q = 0; q < MONO2_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA210[q] = 0; EB210[q] = 0; EY210[q] = 0; }
    for (int q = 0; q < MONO2_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB210[q] = 0; XY210[q] = 0; }
#if HAS_ARX
    lane_t a10[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=a10 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        a10[l] = 0; }
    axn_ops4<axn_b(0), 0>(X10, ar0[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[9]), EA10 + 0, EB10 + 0);
    axn_ops4<axn_b(1), 0>(X10, ar0[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[9]), EA10 + 4, EB10 + 4);
    axn_ops4<axn_b(2), 0>(X10, ar0[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[9]), EA10 + 8, EB10 + 8);
    axn_ops4<axn_b(3), 0>(X10, ar0[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[9]), EA10 + 12, EB10 + 12);
    axn_ops4<axn_b(4), 0>(X10, ar0[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[9]), EA10 + 16, EB10 + 16);
    axn_ops6<axn_b(5), 0>(X10, ar1[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[9]), EA10 + 20, EB10 + 20);
    axn_ops6<axn_b(6), 0>(X10, ar1[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[9]), EA10 + 24, EB10 + 24);
    axn_ops6<axn_b(7), 0>(X10, ar1[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[9]), EA10 + 28, EB10 + 28);
    axn_ops6<axn_b(8), 0>(X10, ar1[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[9]), EA10 + 32, EB10 + 32);
    axn_ops4<axn_b(9), 1>(X10, ar2[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[9]), EA210 + 0, EB210 + 0);
    axn_ops4<axn_b(10), 1>(X10, ar2[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[9]), EA210 + 4, EB210 + 4);
    axn_ops4<axn_b(11), 1>(X10, ar2[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[9]), EA210 + 8, EB210 + 8);
    axn_ops4<axn_b(12), 1>(X10, ar2[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[9]), EA210 + 12, EB210 + 12);
    axn_ops4<axn_b(13), 1>(X10, ar2[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[9]), EA210 + 16, EB210 + 16);
    axn_ops6<axn_b(14), 1>(X10, ar3[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[9]), EA210 + 20, EB210 + 20);
    axn_ops6<axn_b(15), 1>(X10, ar3[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[9]), EA210 + 24, EB210 + 24);
    axn_ops6<axn_b(16), 1>(X10, ar3[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[9]), EA210 + 28, EB210 + 28);
    axn_ops6<axn_b(17), 1>(X10, ar3[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[9]), EA210 + 32, EB210 + 32);
#endif
#if HAS(M_MONO)
    lane_t m10[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m10 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m10[l] = 0; }
    monk_lx10(X10, dd[9], m10, (HAS_ARX ? !(bool)mp[9] : false), EA10, EB10, EY10, XB10, XY10);
    lane_t m210[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m210 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m210[l] = 0; }
    monk2_lx10(X10, dd2[9], m210, (HAS_ARX ? !(bool)mp2[9] : false), EA210, EB210, EY210, XB210, XY210);
#else
    for (int q = 0; q < 36; q++) {
#pragma HLS UNROLL
        EY10[q] = alu_addp<32>(EA10[q], EB10[q]); }
    for (int q = 0; q < 36; q++) {
#pragma HLS UNROLL
        EY210[q] = alu_addp<32>(EA210[q], EB210[q]); }
#endif
#if HAS_ARX
    axn_fin4<axn_b(0), 0>(X10, ar0[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[9]), EY10 + 0, a10);
    axn_fin4<axn_b(1), 0>(X10, ar0[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[9]), EY10 + 4, a10);
    axn_fin4<axn_b(2), 0>(X10, ar0[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[9]), EY10 + 8, a10);
    axn_fin4<axn_b(3), 0>(X10, ar0[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[9]), EY10 + 12, a10);
    axn_fin4<axn_b(4), 0>(X10, ar0[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[9]), EY10 + 16, a10);
    axn_fin6<axn_b(5), 0, axn_h(5)>(X10, ar1[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[9]), EY10 + 20, a10);
    axn_fin6<axn_b(6), 0, axn_h(6)>(X10, ar1[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[9]), EY10 + 24, a10);
    axn_fin6<axn_b(7), 0, axn_h(7)>(X10, ar1[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[9]), EY10 + 28, a10);
    axn_fin6<axn_b(8), 0, axn_h(8)>(X10, ar1[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk1[9]), EY10 + 32, a10);
    axn_fin4<axn_b(9), 1>(X10, ar2[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[9]), EY210 + 0, a10);
    axn_fin4<axn_b(10), 1>(X10, ar2[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[9]), EY210 + 4, a10);
    axn_fin4<axn_b(11), 1>(X10, ar2[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[9]), EY210 + 8, a10);
    axn_fin4<axn_b(12), 1>(X10, ar2[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[9]), EY210 + 12, a10);
    axn_fin4<axn_b(13), 1>(X10, ar2[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[9]), EY210 + 16, a10);
    axn_fin6<axn_b(14), 1, axn_h(14)>(X10, ar3[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[9]), EY210 + 20, a10);
    axn_fin6<axn_b(15), 1, axn_h(15)>(X10, ar3[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[9]), EY210 + 24, a10);
    axn_fin6<axn_b(16), 1, axn_h(16)>(X10, ar3[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[9]), EY210 + 28, a10);
    axn_fin6<axn_b(17), 1, axn_h(17)>(X10, ar3[9], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk3[9]), EY210 + 32, a10);
#endif
    lane_t N10[LV_N10 > 0 ? LV_N10 : 1];
#pragma HLS ARRAY_PARTITION variable=N10 complete
#if HAS_ARX
    for (int l = AXN_GLO0; l < AXN_GHI0; l++) {
#pragma HLS UNROLL
        const int bl = (l - (AXN_GLO0)) % AXN_BL; N10[l] = (bl == 0 || bl == 1 || bl == 2 || bl == 3 || bl == 4 || bl == 5 || bl == 6 || bl == 7 || bl == 16 || bl == 17) ? a10[l] : X10[l]; }
    for (int l = AXN_GLO1; l < AXN_GHI1; l++) {
#pragma HLS UNROLL
        const int bl = (l - (AXN_GLO1)) % AXN_BL; N10[l] = (bl == 0 || bl == 1 || bl == 2 || bl == 3 || bl == 4 || bl == 5 || bl == 6 || bl == 7 || bl == 8 || bl == 9 || bl == 10 || bl == 11 || bl == 12 || bl == 13 || bl == 14 || bl == 15) ? a10[l] : X10[l]; }
    for (int l = AXN_GLO2; l < AXN_GHI2; l++) {
#pragma HLS UNROLL
        const int bl = (l - (AXN_GLO2)) % AXN_BL; N10[l] = (bl == 0 || bl == 1 || bl == 2 || bl == 3 || bl == 4 || bl == 5 || bl == 6 || bl == 7 || bl == 16 || bl == 17) ? a10[l] : X10[l]; }
    for (int l = AXN_GLO3; l < AXN_GHI3; l++) {
#pragma HLS UNROLL
        const int bl = (l - (AXN_GLO3)) % AXN_BL; N10[l] = (bl == 0 || bl == 1 || bl == 2 || bl == 3 || bl == 4 || bl == 5 || bl == 6 || bl == 7 || bl == 8 || bl == 9 || bl == 10 || bl == 11 || bl == 12 || bl == 13 || bl == 14 || bl == 15) ? a10[l] : X10[l]; }
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < MONO2_BASE; l++) {
#pragma HLS UNROLL
        N10[l] = (l < 404 && true) ? X10[l] : m10[l]; }
    for (int l = MONO2_BASE; l < LV_N10; l++) {
#pragma HLS UNROLL
        N10[l] = (l < 456 && true) ? X10[l] : m210[l]; }
#endif
    lane_t X11[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=X11 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        X11[l] = 0; }
#if HAS_ARX
    for (int l = AXN_GLO0; l < AXN_GHI0; l++) {
#pragma HLS UNROLL
        X11[l] = R10[l]; }
    for (int l = AXN_GLO2; l < AXN_GHI2; l++) {
#pragma HLS UNROLL
        X11[l] = R10[l]; }
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N10; l++) {
#pragma HLS UNROLL
        X11[l] = R10[l]; }
#endif
    word32_t EA11[MONO_LEND_MAX], EB11[MONO_LEND_MAX], EY11[MONO_LEND_MAX], XB11[MONO_XLEND_MAX], XY11[MONO_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA11 complete
#pragma HLS ARRAY_PARTITION variable=EB11 complete
#pragma HLS ARRAY_PARTITION variable=EY11 complete
#pragma HLS ARRAY_PARTITION variable=XB11 complete
#pragma HLS ARRAY_PARTITION variable=XY11 complete
    for (int q = 0; q < MONO_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA11[q] = 0; EB11[q] = 0; EY11[q] = 0; }
    for (int q = 0; q < MONO_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB11[q] = 0; XY11[q] = 0; }
    word32_t EA211[MONO2_LEND_MAX], EB211[MONO2_LEND_MAX], EY211[MONO2_LEND_MAX], XB211[MONO2_XLEND_MAX], XY211[MONO2_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA211 complete
#pragma HLS ARRAY_PARTITION variable=EB211 complete
#pragma HLS ARRAY_PARTITION variable=EY211 complete
#pragma HLS ARRAY_PARTITION variable=XB211 complete
#pragma HLS ARRAY_PARTITION variable=XY211 complete
    for (int q = 0; q < MONO2_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA211[q] = 0; EB211[q] = 0; EY211[q] = 0; }
    for (int q = 0; q < MONO2_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB211[q] = 0; XY211[q] = 0; }
#if HAS_ARX
    lane_t a11[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=a11 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        a11[l] = 0; }
    axn_ops5<axn_b(0), 0>(X11, ar0[10], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[10]), EA11 + 0, EB11 + 0);
    axn_ops5<axn_b(1), 0>(X11, ar0[10], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[10]), EA11 + 4, EB11 + 4);
    axn_ops5<axn_b(2), 0>(X11, ar0[10], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[10]), EA11 + 8, EB11 + 8);
    axn_ops5<axn_b(3), 0>(X11, ar0[10], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[10]), EA11 + 12, EB11 + 12);
    axn_ops5<axn_b(4), 0>(X11, ar0[10], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[10]), EA11 + 16, EB11 + 16);
    axn_ops5<axn_b(9), 1>(X11, ar2[10], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[10]), EA211 + 0, EB211 + 0);
    axn_ops5<axn_b(10), 1>(X11, ar2[10], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[10]), EA211 + 4, EB211 + 4);
    axn_ops5<axn_b(11), 1>(X11, ar2[10], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[10]), EA211 + 8, EB211 + 8);
    axn_ops5<axn_b(12), 1>(X11, ar2[10], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[10]), EA211 + 12, EB211 + 12);
    axn_ops5<axn_b(13), 1>(X11, ar2[10], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[10]), EA211 + 16, EB211 + 16);
#endif
#if HAS(M_MONO)
    lane_t m11[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m11 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m11[l] = 0; }
    monk_lx11(X11, dd[10], m11, (HAS_ARX ? !(bool)mp[10] : false), EA11, EB11, EY11, XB11, XY11);
    lane_t m211[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m211 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m211[l] = 0; }
    monk2_lx11(X11, dd2[10], m211, (HAS_ARX ? !(bool)mp2[10] : false), EA211, EB211, EY211, XB211, XY211);
#else
    for (int q = 0; q < 20; q++) {
#pragma HLS UNROLL
        EY11[q] = alu_addp<32>(EA11[q], EB11[q]); }
    for (int q = 0; q < 20; q++) {
#pragma HLS UNROLL
        EY211[q] = alu_addp<32>(EA211[q], EB211[q]); }
#endif
#if HAS_ARX
    axn_fin5<axn_b(0), 0>(X11, ar0[10], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[10]), EY11 + 0, a11);
    axn_fin5<axn_b(1), 0>(X11, ar0[10], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[10]), EY11 + 4, a11);
    axn_fin5<axn_b(2), 0>(X11, ar0[10], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[10]), EY11 + 8, a11);
    axn_fin5<axn_b(3), 0>(X11, ar0[10], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[10]), EY11 + 12, a11);
    axn_fin5<axn_b(4), 0>(X11, ar0[10], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[10]), EY11 + 16, a11);
    axn_fin5<axn_b(9), 1>(X11, ar2[10], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[10]), EY211 + 0, a11);
    axn_fin5<axn_b(10), 1>(X11, ar2[10], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[10]), EY211 + 4, a11);
    axn_fin5<axn_b(11), 1>(X11, ar2[10], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[10]), EY211 + 8, a11);
    axn_fin5<axn_b(12), 1>(X11, ar2[10], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[10]), EY211 + 12, a11);
    axn_fin5<axn_b(13), 1>(X11, ar2[10], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[10]), EY211 + 16, a11);
#endif
    lane_t N11[LV_N11 > 0 ? LV_N11 : 1];
#pragma HLS ARRAY_PARTITION variable=N11 complete
#if HAS_ARX
    for (int l = AXN_GLO0; l < AXN_GHI0; l++) {
#pragma HLS UNROLL
        const int bl = (l - (AXN_GLO0)) % AXN_BL; N11[l] = (bl == 0 || bl == 3 || bl == 4 || bl == 7) ? a11[l] : X11[l]; }
    for (int l = AXN_GLO2; l < AXN_GHI2; l++) {
#pragma HLS UNROLL
        const int bl = (l - (AXN_GLO2)) % AXN_BL; N11[l] = (bl == 0 || bl == 3 || bl == 4 || bl == 7) ? a11[l] : X11[l]; }
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < MONO2_BASE; l++) {
#pragma HLS UNROLL
        N11[l] = (l < 404 && true) ? X11[l] : m11[l]; }
    for (int l = MONO2_BASE; l < LV_N11; l++) {
#pragma HLS UNROLL
        N11[l] = (l < 456 && true) ? X11[l] : m211[l]; }
#endif
    lane_t X12[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=X12 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        X12[l] = 0; }
#if HAS_ARX
    for (int l = AXN_GLO0; l < AXN_GHI0; l++) {
#pragma HLS UNROLL
        X12[l] = R11[l]; }
    for (int l = AXN_GLO2; l < AXN_GHI2; l++) {
#pragma HLS UNROLL
        X12[l] = R11[l]; }
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N11; l++) {
#pragma HLS UNROLL
        X12[l] = R11[l]; }
#endif
    word32_t EA12[MONO_LEND_MAX], EB12[MONO_LEND_MAX], EY12[MONO_LEND_MAX], XB12[MONO_XLEND_MAX], XY12[MONO_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA12 complete
#pragma HLS ARRAY_PARTITION variable=EB12 complete
#pragma HLS ARRAY_PARTITION variable=EY12 complete
#pragma HLS ARRAY_PARTITION variable=XB12 complete
#pragma HLS ARRAY_PARTITION variable=XY12 complete
    for (int q = 0; q < MONO_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA12[q] = 0; EB12[q] = 0; EY12[q] = 0; }
    for (int q = 0; q < MONO_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB12[q] = 0; XY12[q] = 0; }
    word32_t EA212[MONO2_LEND_MAX], EB212[MONO2_LEND_MAX], EY212[MONO2_LEND_MAX], XB212[MONO2_XLEND_MAX], XY212[MONO2_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA212 complete
#pragma HLS ARRAY_PARTITION variable=EB212 complete
#pragma HLS ARRAY_PARTITION variable=EY212 complete
#pragma HLS ARRAY_PARTITION variable=XB212 complete
#pragma HLS ARRAY_PARTITION variable=XY212 complete
    for (int q = 0; q < MONO2_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA212[q] = 0; EB212[q] = 0; EY212[q] = 0; }
    for (int q = 0; q < MONO2_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB212[q] = 0; XY212[q] = 0; }
#if HAS_ARX
    lane_t a12[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=a12 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        a12[l] = 0; }
    axn_ops6<axn_b(0), 0>(X12, ar0[11], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[11]), EA12 + 0, EB12 + 0);
    axn_ops6<axn_b(1), 0>(X12, ar0[11], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[11]), EA12 + 4, EB12 + 4);
    axn_ops6<axn_b(2), 0>(X12, ar0[11], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[11]), EA12 + 8, EB12 + 8);
    axn_ops6<axn_b(3), 0>(X12, ar0[11], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[11]), EA12 + 12, EB12 + 12);
    axn_ops6<axn_b(4), 0>(X12, ar0[11], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[11]), EA12 + 16, EB12 + 16);
    axn_ops6<axn_b(9), 1>(X12, ar2[11], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[11]), EA212 + 0, EB212 + 0);
    axn_ops6<axn_b(10), 1>(X12, ar2[11], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[11]), EA212 + 4, EB212 + 4);
    axn_ops6<axn_b(11), 1>(X12, ar2[11], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[11]), EA212 + 8, EB212 + 8);
    axn_ops6<axn_b(12), 1>(X12, ar2[11], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[11]), EA212 + 12, EB212 + 12);
    axn_ops6<axn_b(13), 1>(X12, ar2[11], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[11]), EA212 + 16, EB212 + 16);
#endif
#if HAS(M_MONO)
    lane_t m12[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m12 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m12[l] = 0; }
    monk_lx12(X12, dd[11], m12, (HAS_ARX ? !(bool)mp[11] : false), EA12, EB12, EY12, XB12, XY12);
    lane_t m212[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m212 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m212[l] = 0; }
    monk2_lx12(X12, dd2[11], m212, (HAS_ARX ? !(bool)mp2[11] : false), EA212, EB212, EY212, XB212, XY212);
#else
    for (int q = 0; q < 20; q++) {
#pragma HLS UNROLL
        EY12[q] = alu_addp<32>(EA12[q], EB12[q]); }
    for (int q = 0; q < 20; q++) {
#pragma HLS UNROLL
        EY212[q] = alu_addp<32>(EA212[q], EB212[q]); }
#endif
#if HAS_ARX
    axn_fin6<axn_b(0), 0, axn_h(0)>(X12, ar0[11], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[11]), EY12 + 0, a12);
    axn_fin6<axn_b(1), 0, axn_h(1)>(X12, ar0[11], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[11]), EY12 + 4, a12);
    axn_fin6<axn_b(2), 0, axn_h(2)>(X12, ar0[11], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[11]), EY12 + 8, a12);
    axn_fin6<axn_b(3), 0, axn_h(3)>(X12, ar0[11], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[11]), EY12 + 12, a12);
    axn_fin6<axn_b(4), 0, axn_h(4)>(X12, ar0[11], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk0[11]), EY12 + 16, a12);
    axn_fin6<axn_b(9), 1, axn_h(9)>(X12, ar2[11], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[11]), EY212 + 0, a12);
    axn_fin6<axn_b(10), 1, axn_h(10)>(X12, ar2[11], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[11]), EY212 + 4, a12);
    axn_fin6<axn_b(11), 1, axn_h(11)>(X12, ar2[11], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[11]), EY212 + 8, a12);
    axn_fin6<axn_b(12), 1, axn_h(12)>(X12, ar2[11], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[11]), EY212 + 12, a12);
    axn_fin6<axn_b(13), 1, axn_h(13)>(X12, ar2[11], ((((MODES_MASK) & 0x06) == 0x02) ? true : (((MODES_MASK) & 0x06) == 0x04) ? false : (bool)bk2[11]), EY212 + 16, a12);
#endif
    lane_t N12[LV_N12 > 0 ? LV_N12 : 1];
#pragma HLS ARRAY_PARTITION variable=N12 complete
#if HAS_ARX
    for (int l = AXN_GLO0; l < AXN_GHI0; l++) {
#pragma HLS UNROLL
        const int bl = (l - (AXN_GLO0)) % AXN_BL; N12[l] = (bl == 0 || bl == 1 || bl == 2 || bl == 3 || bl == 4 || bl == 5 || bl == 6 || bl == 7 || bl == 8 || bl == 9 || bl == 10 || bl == 11 || bl == 12 || bl == 13 || bl == 14 || bl == 15) ? a12[l] : X12[l]; }
    for (int l = AXN_GLO2; l < AXN_GHI2; l++) {
#pragma HLS UNROLL
        const int bl = (l - (AXN_GLO2)) % AXN_BL; N12[l] = (bl == 0 || bl == 1 || bl == 2 || bl == 3 || bl == 4 || bl == 5 || bl == 6 || bl == 7 || bl == 8 || bl == 9 || bl == 10 || bl == 11 || bl == 12 || bl == 13 || bl == 14 || bl == 15) ? a12[l] : X12[l]; }
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < MONO2_BASE; l++) {
#pragma HLS UNROLL
        N12[l] = (l < 404 && true) ? X12[l] : m12[l]; }
    for (int l = MONO2_BASE; l < LV_N12; l++) {
#pragma HLS UNROLL
        N12[l] = (l < 456 && true) ? X12[l] : m212[l]; }
#endif
    lane_t X13[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=X13 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        X13[l] = 0; }
#if HAS_ARX
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N12; l++) {
#pragma HLS UNROLL
        X13[l] = R12[l]; }
#endif
    word32_t EA13[MONO_LEND_MAX], EB13[MONO_LEND_MAX], EY13[MONO_LEND_MAX], XB13[MONO_XLEND_MAX], XY13[MONO_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA13 complete
#pragma HLS ARRAY_PARTITION variable=EB13 complete
#pragma HLS ARRAY_PARTITION variable=EY13 complete
#pragma HLS ARRAY_PARTITION variable=XB13 complete
#pragma HLS ARRAY_PARTITION variable=XY13 complete
    for (int q = 0; q < MONO_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA13[q] = 0; EB13[q] = 0; EY13[q] = 0; }
    for (int q = 0; q < MONO_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB13[q] = 0; XY13[q] = 0; }
    word32_t EA213[MONO2_LEND_MAX], EB213[MONO2_LEND_MAX], EY213[MONO2_LEND_MAX], XB213[MONO2_XLEND_MAX], XY213[MONO2_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA213 complete
#pragma HLS ARRAY_PARTITION variable=EB213 complete
#pragma HLS ARRAY_PARTITION variable=EY213 complete
#pragma HLS ARRAY_PARTITION variable=XB213 complete
#pragma HLS ARRAY_PARTITION variable=XY213 complete
    for (int q = 0; q < MONO2_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA213[q] = 0; EB213[q] = 0; EY213[q] = 0; }
    for (int q = 0; q < MONO2_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB213[q] = 0; XY213[q] = 0; }
#if HAS(M_MONO)
    lane_t m13[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m13 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m13[l] = 0; }
    monk_lx13(X13, dd[12], m13, false, EA13, EB13, EY13, XB13, XY13);
    lane_t m213[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m213 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m213[l] = 0; }
    monk2_lx13(X13, dd2[12], m213, false, EA213, EB213, EY213, XB213, XY213);
#endif
    lane_t N13[LV_N13 > 0 ? LV_N13 : 1];
#pragma HLS ARRAY_PARTITION variable=N13 complete
#if HAS_ARX
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < MONO2_BASE; l++) {
#pragma HLS UNROLL
        N13[l] = (l < 404 && true) ? X13[l] : m13[l]; }
    for (int l = MONO2_BASE; l < LV_N13; l++) {
#pragma HLS UNROLL
        N13[l] = (l < 456 && true) ? X13[l] : m213[l]; }
#endif
    lane_t X14[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=X14 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        X14[l] = 0; }
#if HAS_ARX
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N13; l++) {
#pragma HLS UNROLL
        X14[l] = R13[l]; }
#endif
    word32_t EA14[MONO_LEND_MAX], EB14[MONO_LEND_MAX], EY14[MONO_LEND_MAX], XB14[MONO_XLEND_MAX], XY14[MONO_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA14 complete
#pragma HLS ARRAY_PARTITION variable=EB14 complete
#pragma HLS ARRAY_PARTITION variable=EY14 complete
#pragma HLS ARRAY_PARTITION variable=XB14 complete
#pragma HLS ARRAY_PARTITION variable=XY14 complete
    for (int q = 0; q < MONO_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA14[q] = 0; EB14[q] = 0; EY14[q] = 0; }
    for (int q = 0; q < MONO_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB14[q] = 0; XY14[q] = 0; }
    word32_t EA214[MONO2_LEND_MAX], EB214[MONO2_LEND_MAX], EY214[MONO2_LEND_MAX], XB214[MONO2_XLEND_MAX], XY214[MONO2_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA214 complete
#pragma HLS ARRAY_PARTITION variable=EB214 complete
#pragma HLS ARRAY_PARTITION variable=EY214 complete
#pragma HLS ARRAY_PARTITION variable=XB214 complete
#pragma HLS ARRAY_PARTITION variable=XY214 complete
    for (int q = 0; q < MONO2_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA214[q] = 0; EB214[q] = 0; EY214[q] = 0; }
    for (int q = 0; q < MONO2_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB214[q] = 0; XY214[q] = 0; }
#if HAS(M_MONO)
    lane_t m14[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m14 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m14[l] = 0; }
    monk_lx14(X14, dd[13], m14, false, EA14, EB14, EY14, XB14, XY14);
    lane_t m214[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m214 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m214[l] = 0; }
    monk2_lx14(X14, dd2[13], m214, false, EA214, EB214, EY214, XB214, XY214);
#endif
    lane_t N14[LV_N14 > 0 ? LV_N14 : 1];
#pragma HLS ARRAY_PARTITION variable=N14 complete
#if HAS_ARX
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < MONO2_BASE; l++) {
#pragma HLS UNROLL
        N14[l] = (l < 404 && true) ? X14[l] : m14[l]; }
    for (int l = MONO2_BASE; l < LV_N14; l++) {
#pragma HLS UNROLL
        N14[l] = (l < 456 && true) ? X14[l] : m214[l]; }
#endif
    lane_t X15[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=X15 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        X15[l] = 0; }
#if HAS_ARX
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N14; l++) {
#pragma HLS UNROLL
        X15[l] = R14[l]; }
#endif
    word32_t EA15[MONO_LEND_MAX], EB15[MONO_LEND_MAX], EY15[MONO_LEND_MAX], XB15[MONO_XLEND_MAX], XY15[MONO_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA15 complete
#pragma HLS ARRAY_PARTITION variable=EB15 complete
#pragma HLS ARRAY_PARTITION variable=EY15 complete
#pragma HLS ARRAY_PARTITION variable=XB15 complete
#pragma HLS ARRAY_PARTITION variable=XY15 complete
    for (int q = 0; q < MONO_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA15[q] = 0; EB15[q] = 0; EY15[q] = 0; }
    for (int q = 0; q < MONO_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB15[q] = 0; XY15[q] = 0; }
    word32_t EA215[MONO2_LEND_MAX], EB215[MONO2_LEND_MAX], EY215[MONO2_LEND_MAX], XB215[MONO2_XLEND_MAX], XY215[MONO2_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA215 complete
#pragma HLS ARRAY_PARTITION variable=EB215 complete
#pragma HLS ARRAY_PARTITION variable=EY215 complete
#pragma HLS ARRAY_PARTITION variable=XB215 complete
#pragma HLS ARRAY_PARTITION variable=XY215 complete
    for (int q = 0; q < MONO2_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA215[q] = 0; EB215[q] = 0; EY215[q] = 0; }
    for (int q = 0; q < MONO2_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB215[q] = 0; XY215[q] = 0; }
#if HAS(M_MONO)
    lane_t m15[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m15 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m15[l] = 0; }
    monk_lx15(X15, dd[14], m15, false, EA15, EB15, EY15, XB15, XY15);
    lane_t m215[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m215 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m215[l] = 0; }
    monk2_lx15(X15, dd2[14], m215, false, EA215, EB215, EY215, XB215, XY215);
#endif
    lane_t N15[LV_N15 > 0 ? LV_N15 : 1];
#pragma HLS ARRAY_PARTITION variable=N15 complete
#if HAS_ARX
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < MONO2_BASE; l++) {
#pragma HLS UNROLL
        N15[l] = (l < 404 && true) ? X15[l] : m15[l]; }
    for (int l = MONO2_BASE; l < LV_N15; l++) {
#pragma HLS UNROLL
        N15[l] = (l < 456 && true) ? X15[l] : m215[l]; }
#endif
    lane_t X16[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=X16 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        X16[l] = 0; }
#if HAS_ARX
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N15; l++) {
#pragma HLS UNROLL
        X16[l] = R15[l]; }
#endif
    word32_t EA16[MONO_LEND_MAX], EB16[MONO_LEND_MAX], EY16[MONO_LEND_MAX], XB16[MONO_XLEND_MAX], XY16[MONO_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA16 complete
#pragma HLS ARRAY_PARTITION variable=EB16 complete
#pragma HLS ARRAY_PARTITION variable=EY16 complete
#pragma HLS ARRAY_PARTITION variable=XB16 complete
#pragma HLS ARRAY_PARTITION variable=XY16 complete
    for (int q = 0; q < MONO_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA16[q] = 0; EB16[q] = 0; EY16[q] = 0; }
    for (int q = 0; q < MONO_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB16[q] = 0; XY16[q] = 0; }
    word32_t EA216[MONO2_LEND_MAX], EB216[MONO2_LEND_MAX], EY216[MONO2_LEND_MAX], XB216[MONO2_XLEND_MAX], XY216[MONO2_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA216 complete
#pragma HLS ARRAY_PARTITION variable=EB216 complete
#pragma HLS ARRAY_PARTITION variable=EY216 complete
#pragma HLS ARRAY_PARTITION variable=XB216 complete
#pragma HLS ARRAY_PARTITION variable=XY216 complete
    for (int q = 0; q < MONO2_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA216[q] = 0; EB216[q] = 0; EY216[q] = 0; }
    for (int q = 0; q < MONO2_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB216[q] = 0; XY216[q] = 0; }
#if HAS(M_MONO)
    lane_t m16[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m16 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m16[l] = 0; }
    monk_lx16(X16, dd[15], m16, false, EA16, EB16, EY16, XB16, XY16);
    lane_t m216[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m216 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m216[l] = 0; }
    monk2_lx16(X16, dd2[15], m216, false, EA216, EB216, EY216, XB216, XY216);
#endif
    lane_t N16[LV_N16 > 0 ? LV_N16 : 1];
#pragma HLS ARRAY_PARTITION variable=N16 complete
#if HAS_ARX
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < MONO2_BASE; l++) {
#pragma HLS UNROLL
        N16[l] = (l < 404 && true) ? X16[l] : m16[l]; }
    for (int l = MONO2_BASE; l < LV_N16; l++) {
#pragma HLS UNROLL
        N16[l] = (l < 456 && true) ? X16[l] : m216[l]; }
#endif
    lane_t X17[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=X17 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        X17[l] = 0; }
#if HAS_ARX
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N16; l++) {
#pragma HLS UNROLL
        X17[l] = R16[l]; }
#endif
    word32_t EA17[MONO_LEND_MAX], EB17[MONO_LEND_MAX], EY17[MONO_LEND_MAX], XB17[MONO_XLEND_MAX], XY17[MONO_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA17 complete
#pragma HLS ARRAY_PARTITION variable=EB17 complete
#pragma HLS ARRAY_PARTITION variable=EY17 complete
#pragma HLS ARRAY_PARTITION variable=XB17 complete
#pragma HLS ARRAY_PARTITION variable=XY17 complete
    for (int q = 0; q < MONO_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA17[q] = 0; EB17[q] = 0; EY17[q] = 0; }
    for (int q = 0; q < MONO_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB17[q] = 0; XY17[q] = 0; }
    word32_t EA217[MONO2_LEND_MAX], EB217[MONO2_LEND_MAX], EY217[MONO2_LEND_MAX], XB217[MONO2_XLEND_MAX], XY217[MONO2_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA217 complete
#pragma HLS ARRAY_PARTITION variable=EB217 complete
#pragma HLS ARRAY_PARTITION variable=EY217 complete
#pragma HLS ARRAY_PARTITION variable=XB217 complete
#pragma HLS ARRAY_PARTITION variable=XY217 complete
    for (int q = 0; q < MONO2_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA217[q] = 0; EB217[q] = 0; EY217[q] = 0; }
    for (int q = 0; q < MONO2_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB217[q] = 0; XY217[q] = 0; }
#if HAS(M_MONO)
    lane_t m17[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m17 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m17[l] = 0; }
    monk_lx17(X17, dd[16], m17, false, EA17, EB17, EY17, XB17, XY17);
    lane_t m217[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m217 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m217[l] = 0; }
    monk2_lx17(X17, dd2[16], m217, false, EA217, EB217, EY217, XB217, XY217);
#endif
    lane_t N17[LV_N17 > 0 ? LV_N17 : 1];
#pragma HLS ARRAY_PARTITION variable=N17 complete
#if HAS_ARX
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < MONO2_BASE; l++) {
#pragma HLS UNROLL
        N17[l] = (l < 404 && true) ? X17[l] : m17[l]; }
    for (int l = MONO2_BASE; l < LV_N17; l++) {
#pragma HLS UNROLL
        N17[l] = (l < 456 && true) ? X17[l] : m217[l]; }
#endif
    lane_t X18[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=X18 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        X18[l] = 0; }
#if HAS_ARX
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N17; l++) {
#pragma HLS UNROLL
        X18[l] = R17[l]; }
#endif
    word32_t EA18[MONO_LEND_MAX], EB18[MONO_LEND_MAX], EY18[MONO_LEND_MAX], XB18[MONO_XLEND_MAX], XY18[MONO_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA18 complete
#pragma HLS ARRAY_PARTITION variable=EB18 complete
#pragma HLS ARRAY_PARTITION variable=EY18 complete
#pragma HLS ARRAY_PARTITION variable=XB18 complete
#pragma HLS ARRAY_PARTITION variable=XY18 complete
    for (int q = 0; q < MONO_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA18[q] = 0; EB18[q] = 0; EY18[q] = 0; }
    for (int q = 0; q < MONO_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB18[q] = 0; XY18[q] = 0; }
    word32_t EA218[MONO2_LEND_MAX], EB218[MONO2_LEND_MAX], EY218[MONO2_LEND_MAX], XB218[MONO2_XLEND_MAX], XY218[MONO2_XLEND_MAX];
#pragma HLS ARRAY_PARTITION variable=EA218 complete
#pragma HLS ARRAY_PARTITION variable=EB218 complete
#pragma HLS ARRAY_PARTITION variable=EY218 complete
#pragma HLS ARRAY_PARTITION variable=XB218 complete
#pragma HLS ARRAY_PARTITION variable=XY218 complete
    for (int q = 0; q < MONO2_LEND_MAX; q++) {
#pragma HLS UNROLL
        EA218[q] = 0; EB218[q] = 0; EY218[q] = 0; }
    for (int q = 0; q < MONO2_XLEND_MAX; q++) {
#pragma HLS UNROLL
        XB218[q] = 0; XY218[q] = 0; }
#if HAS(M_MONO)
    lane_t m18[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m18 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m18[l] = 0; }
    monk_lx18(X18, dd[17], m18, false, EA18, EB18, EY18, XB18, XY18);
    lane_t m218[LV_NMAX];
#pragma HLS ARRAY_PARTITION variable=m218 complete
    for (int l = 0; l < LV_NMAX; l++) {
#pragma HLS UNROLL
        m218[l] = 0; }
    monk2_lx18(X18, dd2[17], m218, false, EA218, EB218, EY218, XB218, XY218);
#endif
    lane_t N18[LV_N18 > 0 ? LV_N18 : 1];
#pragma HLS ARRAY_PARTITION variable=N18 complete
#if HAS_ARX
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < MONO2_BASE; l++) {
#pragma HLS UNROLL
        N18[l] = (l < 404 && false) ? X18[l] : m18[l]; }
    for (int l = MONO2_BASE; l < LV_N18; l++) {
#pragma HLS UNROLL
        N18[l] = (l < 456 && false) ? X18[l] : m218[l]; }
#endif
#if HAS_ARX
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N18; l++) {
#pragma HLS UNROLL
        R18[l] = N18[l]; }
#endif
#if HAS_ARX
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N17; l++) {
#pragma HLS UNROLL
        R17[l] = N17[l]; }
#endif
#if HAS_ARX
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N16; l++) {
#pragma HLS UNROLL
        R16[l] = N16[l]; }
#endif
#if HAS_ARX
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N15; l++) {
#pragma HLS UNROLL
        R15[l] = N15[l]; }
#endif
#if HAS_ARX
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N14; l++) {
#pragma HLS UNROLL
        R14[l] = N14[l]; }
#endif
#if HAS_ARX
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N13; l++) {
#pragma HLS UNROLL
        R13[l] = N13[l]; }
#endif
#if HAS_ARX
    for (int l = AXN_GLO0; l < AXN_GHI0; l++) {
#pragma HLS UNROLL
        R12[l] = N12[l]; }
    for (int l = AXN_GLO2; l < AXN_GHI2; l++) {
#pragma HLS UNROLL
        R12[l] = N12[l]; }
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N12; l++) {
#pragma HLS UNROLL
        R12[l] = N12[l]; }
#endif
#if HAS_ARX
    for (int l = AXN_GLO0; l < AXN_GHI0; l++) {
#pragma HLS UNROLL
        R11[l] = N11[l]; }
    for (int l = AXN_GLO2; l < AXN_GHI2; l++) {
#pragma HLS UNROLL
        R11[l] = N11[l]; }
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N11; l++) {
#pragma HLS UNROLL
        R11[l] = N11[l]; }
#endif
#if HAS_ARX
    for (int l = AXN_GLO0; l < AXN_GHI0; l++) {
#pragma HLS UNROLL
        R10[l] = N10[l]; }
    for (int l = AXN_GLO1; l < AXN_GHI1; l++) {
#pragma HLS UNROLL
        R10[l] = N10[l]; }
    for (int l = AXN_GLO2; l < AXN_GHI2; l++) {
#pragma HLS UNROLL
        R10[l] = N10[l]; }
    for (int l = AXN_GLO3; l < AXN_GHI3; l++) {
#pragma HLS UNROLL
        R10[l] = N10[l]; }
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N10; l++) {
#pragma HLS UNROLL
        R10[l] = N10[l]; }
#endif
#if HAS_ARX
    for (int l = AXN_GLO0; l < AXN_GHI0; l++) {
#pragma HLS UNROLL
        R9[l] = N9[l]; }
    for (int l = AXN_GLO1; l < AXN_GHI1; l++) {
#pragma HLS UNROLL
        R9[l] = N9[l]; }
    for (int l = AXN_GLO2; l < AXN_GHI2; l++) {
#pragma HLS UNROLL
        R9[l] = N9[l]; }
    for (int l = AXN_GLO3; l < AXN_GHI3; l++) {
#pragma HLS UNROLL
        R9[l] = N9[l]; }
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N9; l++) {
#pragma HLS UNROLL
        R9[l] = N9[l]; }
#endif
#if HAS_ARX
    for (int l = AXN_GLO0; l < AXN_GHI0; l++) {
#pragma HLS UNROLL
        R8[l] = N8[l]; }
    for (int l = AXN_GLO1; l < AXN_GHI1; l++) {
#pragma HLS UNROLL
        R8[l] = N8[l]; }
    for (int l = AXN_GLO2; l < AXN_GHI2; l++) {
#pragma HLS UNROLL
        R8[l] = N8[l]; }
    for (int l = AXN_GLO3; l < AXN_GHI3; l++) {
#pragma HLS UNROLL
        R8[l] = N8[l]; }
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N8; l++) {
#pragma HLS UNROLL
        R8[l] = N8[l]; }
#endif
#if HAS_ARX
    for (int l = AXN_GLO0; l < AXN_GHI0; l++) {
#pragma HLS UNROLL
        R7[l] = N7[l]; }
    for (int l = AXN_GLO1; l < AXN_GHI1; l++) {
#pragma HLS UNROLL
        R7[l] = N7[l]; }
    for (int l = AXN_GLO2; l < AXN_GHI2; l++) {
#pragma HLS UNROLL
        R7[l] = N7[l]; }
    for (int l = AXN_GLO3; l < AXN_GHI3; l++) {
#pragma HLS UNROLL
        R7[l] = N7[l]; }
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N7; l++) {
#pragma HLS UNROLL
        R7[l] = N7[l]; }
#endif
#if HAS_ARX
    for (int l = AXN_GLO1; l < AXN_GHI1; l++) {
#pragma HLS UNROLL
        R6[l] = N6[l]; }
    for (int l = AXN_GLO3; l < AXN_GHI3; l++) {
#pragma HLS UNROLL
        R6[l] = N6[l]; }
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N6; l++) {
#pragma HLS UNROLL
        R6[l] = N6[l]; }
#endif
#if HAS_ARX
    for (int l = AXN_GLO1; l < AXN_GHI1; l++) {
#pragma HLS UNROLL
        R5[l] = N5[l]; }
    for (int l = AXN_GLO3; l < AXN_GHI3; l++) {
#pragma HLS UNROLL
        R5[l] = N5[l]; }
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N5; l++) {
#pragma HLS UNROLL
        R5[l] = N5[l]; }
#endif
#if HAS_ARX
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N4; l++) {
#pragma HLS UNROLL
        R4[l] = N4[l]; }
#endif
#if HAS_ARX
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N3; l++) {
#pragma HLS UNROLL
        R3[l] = N3[l]; }
#endif
#if HAS_ARX
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N2; l++) {
#pragma HLS UNROLL
        R2[l] = N2[l]; }
#endif
#if HAS_ARX
#endif
#if HAS(M_MONO)
    for (int l = MONO_BASE; l < LV_N1; l++) {
#pragma HLS UNROLL
        R1[l] = N1[l]; }
#endif
    for (int k = 18; k >= 2; k--) {
#pragma HLS UNROLL
        rr[k] = rr[k-1]; dd[k] = dd[k-1]; mp[k] = mp[k-1]; }
    rr[1] = r; dd[1] = dec; mp[1] = mono;
    for (int k = 18; k >= 2; k--) {
#pragma HLS UNROLL
        dd2[k] = dd2[k-1]; mp2[k] = mp2[k-1]; }
    dd2[1] = dec2; mp2[1] = mono2;
    for (int k = 12; k >= 8; k--) {
#pragma HLS UNROLL
        ar0[k] = ar0[k-1]; bk0[k] = bk0[k-1]; }
    ar0[7] = rg[0]; bk0[7] = blake;
    for (int k = 10; k >= 6; k--) {
#pragma HLS UNROLL
        ar1[k] = ar1[k-1]; bk1[k] = bk1[k-1]; }
    ar1[5] = rg[1]; bk1[5] = blake;
    for (int k = 12; k >= 8; k--) {
#pragma HLS UNROLL
        ar2[k] = ar2[k-1]; bk2[k] = bk2[k-1]; }
    ar2[7] = rg[2]; bk2[7] = blake;
    for (int k = 10; k >= 6; k--) {
#pragma HLS UNROLL
        ar3[k] = ar3[k-1]; bk3[k] = bk3[k-1]; }
    ar3[5] = rg[3]; bk3[5] = blake;
}
#endif
