// level_ops_axn_flat.h - level_ops_axn.h with no macros (no include guard, M_BLAKE, AXN_LANES or #ifndef AXN_MERKLE);
// ChaCha20 (GGM) and BLAKE3 (Merkle node, or keyed-XOF GGM node) on SIX ARX steps per traversal,
// N independent blocks per issue (lockstep); every add runs on a lent Monolith adder (operands EA/EB out, sums EY back).
// One block = 22 lanes at base B. A ROW is two lanes (lo = columns 0,1, hi = columns 2,3):
//   rows A (0,4)  B (1,5)  C (2,6)  D (3,7)   T (16,17) temporaries   H (18..21) BLAKE3 chaining value
//   8..15 BLAKE3 message: 8 (m0|m2) 9 (m1|m3) 10 (m4|m6) 11 (m5|m7) 12 (m8|m14) 13 (m9|m15) 14 (m12|m10) 15 (m13|m11)
//         ChaCha20: the input copy for the feed-forward, a (8,10) b (9,11) c (12,14) d (13,15)
//
// BLAKE3, one half-round (four G) per traversal, 14 traversals per node:
//   1 T = B + m1 | 2 A += T, D = rotr16(D ^ A) | 3 C += D, B = rotr12(B ^ C) | 4 T = B + m2 | 5 A += T, D = rotr8(D ^ A) |
//   6 C += D, B = rotr7(B ^ C), P (column <-> diagonal), sigma after a diagonal half, finalisation at r = 13 | 256.
// Round index r: traversal 0..13; the last traversal carries bit 8 (r = 13 | 256), tested as one bit.
// ChaCha20, 1.5 rounds per traversal, 14 traversals per block (20 rounds = 80 add steps + 4 feed-forward steps = 84 = 14 x 6):
//   every step is one ChaCha add step (a += b, d = rotl(d ^ a) / c += d, b = rotl(b ^ c)), so all 24 lent adders of a block
//   work in every traversal. The traversals alternate between the two copies of the block groups (CP = 0: steps S0..S3,
//   round end, S0 S1; CP = 1: S2 S3, round end, S0..S3, round end); the rotations and the round-end P are wired per copy.
//   ChaCha's rows sit in layout L0 (a b c d in A B C D) or L1 (c d a b in A B C D) so that most steps reuse BLAKE3's
//   adder operands, destination and xor-rotate rows. The last traversal (CP = 1, r = 13) does the feed-forward on
//   steps 3..6 (a in C, d in T, c in A, b in B), then P: the output layout is undone by software (models.cc_words).
// P: the column <-> diagonal involution, row x: hardware column j <- column (x - j) mod 4 (x = 0 a, 1 b, 2 c, 3 d).
#pragma once
// (no global mode: every block carries its own BLAKE3/ChaCha bit, see gen_pipe_axn.py BLK())
#include "alu_core.h"            // ALU-XOR: the blocks' only own logic; every add is an ALU-ADD of a datapath (EA / EB / EY)

static inline void words(lane_t a, lane_t b, word32_t E[]) {
#pragma HLS INLINE
    E[0] = LO(a); E[1] = HI(a); E[2] = LO(b); E[3] = HI(b);
}
template<int X> static inline void prow(lane_t lo, lane_t hi, lane_t& olo, lane_t& ohi) {
#pragma HLS INLINE
    if (X == 0)      { olo = pk(LO(lo), HI(hi)); ohi = pk(LO(hi), HI(lo)); }
    else if (X == 1) { olo = pk(HI(lo), LO(lo)); ohi = pk(HI(hi), LO(hi)); }
    else if (X == 2) { olo = pk(LO(hi), HI(lo)); ohi = pk(LO(lo), HI(hi)); }
    else             { olo = pk(HI(hi), LO(hi)); ohi = pk(HI(lo), LO(lo)); }
}
template<int CP> static inline bool axn_ff(ap_uint<9> r, bool blake) {        // ChaCha feed-forward traversal (r = 13 | 256)
#pragma HLS INLINE
    return CP == 1 && !blake && r[8];
}

// ---- step 1: BLAKE3 T = B + m1 | ChaCha a-type: a' = b + a, d' = rotl(d ^ a') (CP 0: rotl16, L0 -> L1; CP 1: rotl8, L0)
template<int B, int CP> static inline void axn_ops1(const lane_t S[], ap_uint<9> r, bool blake, word32_t EA[], word32_t EB[]) {
#pragma HLS INLINE
    const lane_t sv0 = S[B + 0], sv1 = S[B + 1], sv4 = S[B + 4], sv5 = S[B + 5], sv8 = S[B + 8], sv10 = S[B + 10], sv12 = S[B + 12], sv14 = S[B + 14];
    bool diag = r[0];
    words(sv1, sv5, EA);
    words(blake ? (diag ? sv12 : sv8) : sv0, blake ? (diag ? sv14 : sv10) : sv4, EB);
}
template<int B, int CP> static inline void axn_fin1(const lane_t S[], ap_uint<9> r, bool blake, const word32_t EY[], lane_t M[]) {
#pragma HLS INLINE
    const lane_t sv0 = S[B + 0], sv1 = S[B + 1], sv2 = S[B + 2], sv3 = S[B + 3], sv4 = S[B + 4], sv5 = S[B + 5], sv6 = S[B + 6], sv7 = S[B + 7];
    lane_t s1 = pk(EY[0], EY[1]), s2 = pk(EY[2], EY[3]);
    M[B + 16] = s1; M[B + 17] = s2;
    lane_t x1 = alu_xor(sv3, s1), x2 = alu_xor(sv7, s2);
    if (CP == 0) {
        M[B + 0] = blake ? sv0 : sv2;             M[B + 4] = blake ? sv4 : sv6;
        M[B + 1] = blake ? sv1 : rotl2x32<16>(x1);     M[B + 5] = blake ? sv5 : rotl2x32<16>(x2);
        M[B + 2] = blake ? sv2 : s1;                   M[B + 6] = blake ? sv6 : s2;
        M[B + 3] = blake ? sv3 : sv1;             M[B + 7] = blake ? sv7 : sv5;
    } else {
        M[B + 0] = blake ? sv0 : s1;                   M[B + 4] = blake ? sv4 : s2;
        M[B + 1] = sv1;                                M[B + 5] = sv5;
        M[B + 2] = sv2;                                M[B + 6] = sv6;
        M[B + 3] = blake ? sv3 : rotl2x32<8>(x1);      M[B + 7] = blake ? sv7 : rotl2x32<8>(x2);
    }
}
// ---- step 2: BLAKE3 A += T, D = rotr16(D ^ A) | ChaCha c-type (CP 0: L1, c in A, d in B, b in D, rotl12;
//      CP 1: L0, c in C, d in D, b in B, rotl7, round end: P, L0 -> L1)
template<int B, int CP> static inline void axn_ops2(const lane_t S[], ap_uint<9> r, bool blake, word32_t EA[], word32_t EB[]) {
#pragma HLS INLINE
    const lane_t sv0 = S[B + 0], sv1 = S[B + 1], sv2 = S[B + 2], sv3 = S[B + 3], sv4 = S[B + 4], sv5 = S[B + 5], sv6 = S[B + 6], sv7 = S[B + 7], sv16 = S[B + 16], sv17 = S[B + 17];
    if (CP == 0) { words(sv0, sv4, EA); words(blake ? sv16 : sv1, blake ? sv17 : sv5, EB); }
    else { words(blake ? sv0 : sv2, blake ? sv4 : sv6, EA); words(blake ? sv16 : sv3, blake ? sv17 : sv7, EB); }
}
template<int B, int CP> static inline void axn_fin2(const lane_t S[], ap_uint<9> r, bool blake, const word32_t EY[], lane_t M[]) {
#pragma HLS INLINE
    const lane_t sv0 = S[B + 0], sv1 = S[B + 1], sv2 = S[B + 2], sv3 = S[B + 3], sv4 = S[B + 4], sv5 = S[B + 5], sv6 = S[B + 6], sv7 = S[B + 7];
    lane_t s1 = pk(EY[0], EY[1]), s2 = pk(EY[2], EY[3]);
    lane_t xd1 = alu_xor(sv3, s1), xd2 = alu_xor(sv7, s2);
    if (CP == 0) {
        M[B + 0] = s1; M[B + 4] = s2;
        M[B + 3] = blake ? rotl2x32<16>(xd1) : rotl2x32<12>(xd1); M[B + 7] = blake ? rotl2x32<16>(xd2) : rotl2x32<12>(xd2);
        M[B + 1] = sv1; M[B + 5] = sv5; M[B + 2] = sv2; M[B + 6] = sv6;
    } else {
        lane_t b1 = rotl2x32<7>(alu_xor(sv1, s1)), b2 = rotl2x32<7>(alu_xor(sv5, s2));
        lane_t pa0, pa4, pb0, pb4, pc0, pc4, pd0, pd4;
        prow<2>(s1, s2, pc0, pc4);                          // c' -> A
        prow<3>(sv3, sv7, pd0, pd4);              // d  -> B
        prow<0>(sv0, sv4, pa0, pa4);              // a  -> C
        prow<1>(b1, b2, pb0, pb4);                          // b' -> D
        M[B + 0] = blake ? s1 : pc0;                        M[B + 4] = blake ? s2 : pc4;
        M[B + 1] = blake ? sv1 : pd0;                  M[B + 5] = blake ? sv5 : pd4;
        M[B + 2] = blake ? sv2 : pa0;                  M[B + 6] = blake ? sv6 : pa4;
        M[B + 3] = blake ? rotl2x32<16>(xd1) : pb0;         M[B + 7] = blake ? rotl2x32<16>(xd2) : pb4;
    }
}
// ---- step 3: C += D, B = rot(B ^ C) for both (ChaCha a-type in L1: a in C, b in D, d in B; CP 0 rotl8, CP 1 rotl16)
//      feed-forward: C (a) += copy a, B passes
template<int B, int CP> static inline void axn_ops3(const lane_t S[], ap_uint<9> r, bool blake, word32_t EA[], word32_t EB[]) {
#pragma HLS INLINE
    const lane_t sv2 = S[B + 2], sv3 = S[B + 3], sv6 = S[B + 6], sv7 = S[B + 7], sv8 = S[B + 8], sv10 = S[B + 10];
    bool ff = axn_ff<CP>(r, blake);
    words(sv2, sv6, EA);
    words(ff ? sv8 : sv3, ff ? sv10 : sv7, EB);
}
template<int B, int CP> static inline void axn_fin3(const lane_t S[], ap_uint<9> r, bool blake, const word32_t EY[], lane_t M[]) {
#pragma HLS INLINE
    const lane_t sv1 = S[B + 1], sv5 = S[B + 5];
    bool ff = axn_ff<CP>(r, blake);
    lane_t s1 = pk(EY[0], EY[1]), s2 = pk(EY[2], EY[3]);
    M[B + 2] = s1; M[B + 6] = s2;
    lane_t x1 = alu_xor(sv1, s1), x2 = alu_xor(sv5, s2);
    lane_t c1 = CP == 0 ? rotl2x32<8>(x1) : rotl2x32<16>(x1), c2 = CP == 0 ? rotl2x32<8>(x2) : rotl2x32<16>(x2);
    M[B + 1] = blake ? rotl2x32<20>(x1) : (ff ? sv1 : c1);
    M[B + 5] = blake ? rotl2x32<20>(x2) : (ff ? sv5 : c2);
}
// ---- step 4: BLAKE3 T = B + m2 | ChaCha c-type in L1 (c in A, d in B, b in D): c' = d + c, b' = rotl(b ^ c'), L1 -> L0
//      (CP 0: rotl7, round end: P; CP 1: rotl12) | feed-forward: T = B (d) + copy d (the m2 lanes 13, 15), rows pass
template<int B, int CP> static inline void axn_ops4(const lane_t S[], ap_uint<9> r, bool blake, word32_t EA[], word32_t EB[]) {
#pragma HLS INLINE
    const lane_t sv0 = S[B + 0], sv1 = S[B + 1], sv4 = S[B + 4], sv5 = S[B + 5], sv9 = S[B + 9], sv11 = S[B + 11], sv13 = S[B + 13], sv15 = S[B + 15];
    bool diag = r[0], msg = blake || axn_ff<CP>(r, blake);
    words(sv1, sv5, EA);
    words(msg ? (diag ? sv13 : sv9) : sv0, msg ? (diag ? sv15 : sv11) : sv4, EB);
}
template<int B, int CP> static inline void axn_fin4(const lane_t S[], ap_uint<9> r, bool blake, const word32_t EY[], lane_t M[]) {
#pragma HLS INLINE
    const lane_t sv0 = S[B + 0], sv1 = S[B + 1], sv2 = S[B + 2], sv3 = S[B + 3], sv4 = S[B + 4], sv5 = S[B + 5], sv6 = S[B + 6], sv7 = S[B + 7];
    bool cc = !blake && !axn_ff<CP>(r, blake);
    lane_t s1 = pk(EY[0], EY[1]), s2 = pk(EY[2], EY[3]);
    M[B + 16] = s1; M[B + 17] = s2;
    lane_t x1 = alu_xor(sv3, s1), x2 = alu_xor(sv7, s2);
    if (CP == 0) {
        lane_t b1 = rotl2x32<7>(x1), b2 = rotl2x32<7>(x2);
        lane_t pa0, pa4, pb0, pb4, pc0, pc4, pd0, pd4;
        prow<0>(sv2, sv6, pa0, pa4);              // a  -> A
        prow<1>(b1, b2, pb0, pb4);                          // b' -> B
        prow<2>(s1, s2, pc0, pc4);                          // c' -> C
        prow<3>(sv1, sv5, pd0, pd4);              // d  -> D
        M[B + 0] = cc ? pa0 : sv0; M[B + 4] = cc ? pa4 : sv4;
        M[B + 1] = cc ? pb0 : sv1; M[B + 5] = cc ? pb4 : sv5;
        M[B + 2] = cc ? pc0 : sv2; M[B + 6] = cc ? pc4 : sv6;
        M[B + 3] = cc ? pd0 : sv3; M[B + 7] = cc ? pd4 : sv7;
    } else {
        M[B + 0] = cc ? sv2 : sv0;                M[B + 4] = cc ? sv6 : sv4;
        M[B + 1] = cc ? rotl2x32<12>(x1) : sv1;        M[B + 5] = cc ? rotl2x32<12>(x2) : sv5;
        M[B + 2] = cc ? s1 : sv2;                      M[B + 6] = cc ? s2 : sv6;
        M[B + 3] = cc ? sv1 : sv3;                M[B + 7] = cc ? sv5 : sv7;
    }
}
// ---- step 5: A += (BLAKE3 T | ChaCha B), D = rot(D ^ A) (ChaCha a-type in L0; CP 0 rotl16, CP 1 rotl8)
//      feed-forward: A (c) += copy c, D passes
template<int B, int CP> static inline void axn_ops5(const lane_t S[], ap_uint<9> r, bool blake, word32_t EA[], word32_t EB[]) {
#pragma HLS INLINE
    const lane_t sv0 = S[B + 0], sv1 = S[B + 1], sv4 = S[B + 4], sv5 = S[B + 5], sv12 = S[B + 12], sv14 = S[B + 14], sv16 = S[B + 16], sv17 = S[B + 17];
    bool ff = axn_ff<CP>(r, blake);
    words(sv0, sv4, EA);
    words(blake ? sv16 : (ff ? sv12 : sv1), blake ? sv17 : (ff ? sv14 : sv5), EB);
}
template<int B, int CP> static inline void axn_fin5(const lane_t S[], ap_uint<9> r, bool blake, const word32_t EY[], lane_t M[]) {
#pragma HLS INLINE
    const lane_t sv3 = S[B + 3], sv7 = S[B + 7];
    bool ff = axn_ff<CP>(r, blake);
    lane_t s1 = pk(EY[0], EY[1]), s2 = pk(EY[2], EY[3]);
    M[B + 0] = s1; M[B + 4] = s2;
    lane_t x1 = alu_xor(sv3, s1), x2 = alu_xor(sv7, s2);
    lane_t c1 = CP == 0 ? rotl2x32<16>(x1) : rotl2x32<8>(x1), c2 = CP == 0 ? rotl2x32<16>(x2) : rotl2x32<8>(x2);
    M[B + 3] = blake ? rotl2x32<24>(x1) : (ff ? sv3 : c1);
    M[B + 7] = blake ? rotl2x32<24>(x2) : (ff ? sv7 : c2);
}
// ---- step 6: C += D, B = rot(B ^ C) (ChaCha c-type in L0; CP 0 rotl12, CP 1 rotl7); then P: BLAKE3 always, ChaCha on
//      CP 1 (round end); BLAKE3: sigma after a diagonal half, finalisation + XOF second half at r = 13
//      feed-forward: B = copy b + D (b), C passes
template<int B, int CP> static inline void axn_ops6(const lane_t S[], ap_uint<9> r, bool blake, word32_t EA[], word32_t EB[]) {
#pragma HLS INLINE
    const lane_t sv2 = S[B + 2], sv3 = S[B + 3], sv6 = S[B + 6], sv7 = S[B + 7], sv9 = S[B + 9], sv11 = S[B + 11];
    bool ff = axn_ff<CP>(r, blake);
    words(ff ? sv9 : sv2, ff ? sv11 : sv6, EA);
    words(sv3, sv7, EB);
}
template<int B, int CP, int H> static inline void axn_fin6(const lane_t S[], ap_uint<9> r, bool blake, const word32_t EY[], lane_t M[]) {   // H: the block's h lanes
#pragma HLS INLINE
    const lane_t sv0 = S[B + 0], sv1 = S[B + 1], sv2 = S[B + 2], sv3 = S[B + 3], sv4 = S[B + 4], sv5 = S[B + 5], sv6 = S[B + 6], sv7 = S[B + 7], sv8 = S[B + 8], sv9 = S[B + 9], sv10 = S[B + 10], sv11 = S[B + 11], sv12 = S[B + 12], sv13 = S[B + 13], sv14 = S[B + 14], sv15 = S[B + 15];
    bool diag = r[0], ff = axn_ff<CP>(r, blake), last = blake && r[8];         // last half-round: r = 13 | 256
    lane_t s1 = pk(EY[0], EY[1]), s2 = pk(EY[2], EY[3]);
    lane_t x1 = alu_xor(sv1, s1), x2 = alu_xor(sv5, s2);
    lane_t k1 = CP == 0 ? rotl2x32<12>(x1) : rotl2x32<7>(x1), k2 = CP == 0 ? rotl2x32<12>(x2) : rotl2x32<7>(x2);
    lane_t a1 = sv0, a2 = sv4, d1 = sv3, d2 = sv7;
    lane_t b1 = blake ? rotl2x32<25>(x1) : (ff ? s1 : k1), b2 = blake ? rotl2x32<25>(x2) : (ff ? s2 : k2);
    lane_t c1 = ff ? sv2 : s1, c2 = ff ? sv6 : s2;
    lane_t pa0, pa4, pb0, pb4, pc0, pc4, pd0, pd4;
    prow<0>(a1, a2, pa0, pa4); prow<1>(b1, b2, pb0, pb4); prow<2>(c1, c2, pc0, pc4); prow<3>(d1, d2, pd0, pd4);
    bool g = (CP == 1) || blake;
    lane_t o[8];
    o[0] = g ? pa0 : a1; o[4] = g ? pa4 : a2; o[1] = g ? pb0 : b1; o[5] = g ? pb4 : b2;
    o[2] = g ? pc0 : c1; o[6] = g ? pc4 : c2; o[3] = g ? pd0 : d1; o[7] = g ? pd4 : d2;
    for (int i = 0; i < 8; i++) {
#pragma HLS UNROLL
        M[B + i] = o[i];
    }
    if (last) {
        M[B + 0] = alu_xor(o[0], o[2]); M[B + 1] = alu_xor(o[4], o[6]); M[B + 2] = alu_xor(o[1], o[3]); M[B + 3] = alu_xor(o[5], o[7]);
        // XOF second half (GGM: two children per node; a Merkle node ignores lanes 4..7)
        M[B + 4] = alu_xor(o[2], S[H + 0]); M[B + 5] = alu_xor(o[6], S[H + 1]); M[B + 6] = alu_xor(o[3], S[H + 2]); M[B + 7] = alu_xor(o[7], S[H + 3]);
    }
    lane_t p[8];                                                  // sigma = 2 6 3 10 7 0 4 13 1 11 12 5 9 14 15 8 on the lane layout above
    p[0] = pk(HI(sv8), HI(sv9));
    p[1] = pk(HI(sv10), HI(sv14));
    p[2] = pk(HI(sv11), LO(sv10));
    p[3] = pk(LO(sv8), LO(sv15));
    p[4] = pk(LO(sv9), HI(sv13));
    p[5] = pk(HI(sv15), LO(sv12));
    p[6] = pk(LO(sv13), LO(sv14));
    p[7] = pk(HI(sv12), LO(sv11));
    bool perm = blake && diag;
    for (int i = 0; i < 8; i++) {
#pragma HLS UNROLL
        M[B + 8 + i] = perm ? p[i] : S[B + 8 + i];
    }
}
