// p2_engine.h - Poseidon2-M31 internal-round engine (Plonky3 p3-mersenne-31 0.8.0, width 16, x^5).
// One internal round per call (II = 1), P2ENG_LAT levels: the state x (16 canonical words in 8 lanes, x0 already holds
// this round's constant) and the round index r enter; out (P2ENG_LAT calls later):
//     t = x0^5;  part = x1 + .. + x15;  y0 = part - t;  y_i = part + t + 2^s_i * x_i;  y += C[r]   (canonical)
// C[r] = models.P2I_ROWS[r]: the next internal round's constant on y0, or (r = 13) the first final external round's
// 16 constants. The engines are separate from the two Monolith / Poseidon2 datapaths: the datapaths run the initial
// linear layer and the 8 external rounds (9 issues per permutation), the engines the 14 internal rounds.
#ifndef UNITREE_P2_ENGINE_H
#define UNITREE_P2_ENGINE_H
#define P2ENG_LAT 10
#include "alu_core.h"            // ALU-MUL (3 per engine), ALU-ADP (part sums, row constants), ALU-FLD; 2^s rotations are wiring
static const ap_uint<31> P2E_P = 0x7FFFFFFF;
static const int P2E_S[16] = {0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 13, 14, 15, 16};   // 2^s_i, i >= 1 (index 0 unused)

static inline ap_uint<31> p2e_fold62(ap_uint<62> v) {             // <= p (lazy: p stands for 0)
#pragma HLS INLINE
    ap_uint<32> r = alu_addp<32>(v.range(30, 0), v.range(61, 31));
    return alu_fold31(r);
}
template<int S> static inline ap_uint<31> p2e_rot(ap_uint<31> x) {   // 2^S * x mod p (S < 31)
#pragma HLS INLINE
    return rot31<S>(x);
}
static inline ap_uint<31> p2e_canon(ap_uint<36> z) {               // < 2^36 -> canonical
#pragma HLS INLINE
    ap_uint<32> v = alu_addp<32>(z.range(30, 0), z.range(35, 31));
    ap_uint<31> w = alu_fold31(v);
    return alu_canon<ap_uint<31> >(w);
}

// in: 8 lanes of the state, r: round index; o: the engine's output (the round issued P2ENG_LAT calls ago)
template<int E> static inline void p2eng(const lane_t in[8], ap_uint<4> r, lane_t o[8]) {
#pragma HLS INLINE
    // ---- pipeline registers (values at the end of each level) ----
    static ap_uint<62> m1; static ap_uint<31> f1; static ap_uint<62> m2; static ap_uint<31> f2; static ap_uint<62> m3; static ap_uint<31> t6;
    static ap_uint<31> x0[4];                                   // x0 at the end of levels 1..4 (rank-3 operand at level 5)
    static ap_uint<32> s1[7]; static ap_uint<31> s1x;           // level 1: pair sums x1+x2 .. x13+x14, x15
    static ap_uint<33> s2[4]; static ap_uint<34> s3[2]; static ap_uint<35> pt4; static ap_uint<32> pt[2];   // pt: folded part, levels 5..6
    static ap_uint<31> xr[8][16];                               // 2^s_i * x_i, levels 1..8 (index 1..15)
    static ap_uint<33> full7, y07;                              // level 7
    static ap_uint<34> y8[16];                                  // level 8
    static ap_uint<35> z9[16];                                  // level 9
    static ap_uint<31> o10[16];                                 // level 10
    static ap_uint<4> rr[10];
#pragma HLS ARRAY_PARTITION variable=x0 complete
#pragma HLS ARRAY_PARTITION variable=s1 complete
#pragma HLS ARRAY_PARTITION variable=s2 complete
#pragma HLS ARRAY_PARTITION variable=s3 complete
#pragma HLS ARRAY_PARTITION variable=pt complete
#pragma HLS ARRAY_PARTITION variable=xr complete dim=0
#pragma HLS ARRAY_PARTITION variable=y8 complete
#pragma HLS ARRAY_PARTITION variable=z9 complete
#pragma HLS ARRAY_PARTITION variable=o10 complete
#pragma HLS ARRAY_PARTITION variable=rr complete
    for (int k = 0; k < 8; k++) {
#pragma HLS UNROLL
        o[k] = pk((word32_t)o10[2 * k], (word32_t)o10[2 * k + 1]);
    }
    ap_uint<31> x[16];
#pragma HLS ARRAY_PARTITION variable=x complete
    for (int k = 0; k < 8; k++) {
#pragma HLS UNROLL
        x[2 * k] = (ap_uint<31>)LO(in[k]).range(30, 0); x[2 * k + 1] = (ap_uint<31>)HI(in[k]).range(30, 0);
    }
    // ---- level 10: canonical outputs ----
    ap_uint<31> n10[16];
    for (int i = 0; i < 16; i++) {
#pragma HLS UNROLL
        n10[i] = p2e_canon((ap_uint<36>)z9[i]);
    }
    // ---- level 9: + the row constants ----
    ap_uint<35> n9[16];
    for (int i = 0; i < 16; i++) {
#pragma HLS UNROLL
        n9[i] = alu_addp<35>(y8[i], P2ENG_C[rr[7] < 14 ? (int)rr[7] : 0][i]);
    }
    // ---- level 8: y_i = full + 2^s_i x_i, y0 ----
    ap_uint<34> n8[16];
    n8[0] = (ap_uint<34>)y07;
    for (int i = 1; i < 16; i++) {
#pragma HLS UNROLL
        n8[i] = alu_addp<34>(full7, xr[6][i]);
    }
    // ---- level 7: full = part + t, y0 = part + (p - t) ----
    ap_uint<33> nfull = alu_addp<33>(pt[1], t6), ny0 = alu_addp<33>(pt[1], alu_negm31<33>(t6));
    // ---- level 6: t = fold(m3) ----
    ap_uint<31> nt6 = p2e_fold62(m3);
    // ---- level 5: m3 = f2 * x0, fold the part ----
    ap_uint<62> nm3 = alu_mul31(f2, x0[3]);
    ap_uint<32> npt5 = alu_addp<32>(pt4.range(30, 0), pt4.range(34, 31));
    // ---- level 4: f2 = fold(m2), part ----
    ap_uint<31> nf2 = p2e_fold62(m2);
    ap_uint<35> npt4 = alu_addp<35>(s3[0], s3[1]);
    // ---- level 3: m2 = f1^2 ----
    ap_uint<62> nm2 = alu_mul31(f1, f1);
    ap_uint<34> ns3[2] = {alu_addp<34>(s2[0], s2[1]), alu_addp<34>(s2[2], s2[3])};
    // ---- level 2: f1 = fold(m1) ----
    ap_uint<31> nf1 = p2e_fold62(m1);
    ap_uint<33> ns2[4];
    ns2[0] = alu_addp<33>(s1[0], s1[1]); ns2[1] = alu_addp<33>(s1[2], s1[3]);
    ns2[2] = alu_addp<33>(s1[4], s1[5]); ns2[3] = alu_addp<33>(s1[6], s1x);
    // ---- level 1: m1 = x0^2, pair sums, 2^s_i x_i ----
    ap_uint<62> nm1 = alu_mul31(x[0], x[0]);
    ap_uint<32> ns1[7];
    for (int k = 0; k < 7; k++) {
#pragma HLS UNROLL
        ns1[k] = alu_addp<32>(x[2 * k + 1], x[2 * k + 2]);
    }
    ap_uint<31> nxr[16];
    nxr[0] = 0;
    nxr[1] = p2e_rot<0>(x[1]);   nxr[2] = p2e_rot<1>(x[2]);   nxr[3] = p2e_rot<2>(x[3]);   nxr[4] = p2e_rot<3>(x[4]);
    nxr[5] = p2e_rot<4>(x[5]);   nxr[6] = p2e_rot<5>(x[6]);   nxr[7] = p2e_rot<6>(x[7]);   nxr[8] = p2e_rot<7>(x[8]);
    nxr[9] = p2e_rot<8>(x[9]);   nxr[10] = p2e_rot<10>(x[10]); nxr[11] = p2e_rot<12>(x[11]); nxr[12] = p2e_rot<13>(x[12]);
    nxr[13] = p2e_rot<14>(x[13]); nxr[14] = p2e_rot<15>(x[14]); nxr[15] = p2e_rot<16>(x[15]);
    // ---- register writes ----
    for (int i = 0; i < 16; i++) {
#pragma HLS UNROLL
        o10[i] = n10[i]; z9[i] = n9[i]; y8[i] = n8[i];
    }
    full7 = nfull; y07 = ny0; t6 = nt6; m3 = nm3; f2 = nf2; m2 = nm2; f1 = nf1; m1 = nm1;
    pt[1] = pt[0]; pt[0] = npt5; pt4 = npt4;
    s3[0] = ns3[0]; s3[1] = ns3[1];
    for (int k = 0; k < 4; k++) {
#pragma HLS UNROLL
        s2[k] = ns2[k];
    }
    for (int k = 0; k < 7; k++) {
#pragma HLS UNROLL
        s1[k] = ns1[k];
    }
    s1x = x[15];
    x0[3] = x0[2]; x0[2] = x0[1]; x0[1] = x0[0]; x0[0] = x[0];
    for (int l = 7; l >= 1; l--) {
#pragma HLS UNROLL
        for (int i = 1; i < 16; i++) {
#pragma HLS UNROLL
            xr[l][i] = xr[l - 1][i];
        }
    }
    for (int i = 1; i < 16; i++) {
#pragma HLS UNROLL
        xr[0][i] = nxr[i];
    }
    for (int l = 9; l >= 1; l--) {
#pragma HLS UNROLL
        rr[l] = rr[l - 1];
    }
    rr[0] = r;
}
#endif
