// field31.h - 31-bit field arithmetic on 2x31-packed 64-bit lanes.
// Packing (per spec): element LO in lane bits [30:0], HI in [62:32];
// lane bits 31 and 63 are the spare/carry bits, so each element sits entirely
// inside one 32-bit half and the bit-32 carry kill of the ADD73 slice separates
// them. Constants and sequences are taken from the Plonky3 reference behaviour.
#ifndef UNITREE_FIELD31_H
#define UNITREE_FIELD31_H
#include "lanes.h"

static const word32_t P_M31 = 0x7FFFFFFFu;  // 2^31 - 1
static const word32_t P_BB  = 0x78000001u;  // 2^31 - 2^27 + 1
static const word32_t P_KB  = 0x7F000001u;  // 2^31 - 2^24 + 1

// ---- Mersenne31 ----
// Add-fold: s <= 2P fits 32 bits; r = s[30:0] + s[31] lands back in [0,P].
static inline word32_t m31_fold32(word32_t s) {
#pragma HLS INLINE
    return (word32_t)((s & P_M31) + (s >> 31));
}
// Reduce a 62-bit product: fold the two 31-bit halves, then fold again.
static inline word32_t m31_reduce62(ap_uint<62> x) {
#pragma HLS INLINE
    word32_t lo = (word32_t)x.range(30, 0);
    word32_t hi = (word32_t)x.range(61, 31);
    return m31_fold32((word32_t)(lo + hi));
}
// Negation is a bitwise NOT of the 31 bits; multiply/divide by 2^k are rotations.
static inline word32_t m31_neg(word32_t x) {
#pragma HLS INLINE
    return (word32_t)(x ^ P_M31);
}
template<int N> static inline word32_t m31_mul2exp(word32_t x) {
#pragma HLS INLINE
    if (N == 0) return x;
    return (word32_t)(((x << N) | (x >> (31 - N))) & P_M31);
}

// ---- Montgomery fields (BabyBear / KoalaBear) ----
// MU = P^-1 mod 2^32 is 2^31 + 2^k + 1 for both, so t = x_lo * MU needs no
// multiplier: it is a shift-add. Likewise u = t*P = (t<<31) + t - (t<<k).
template<int K>   // K = 27 for BabyBear, 24 for KoalaBear
static inline word32_t monty_reduce(ap_uint<64> x, word32_t P) {
#pragma HLS INLINE
    word32_t x_lo = (word32_t)x.range(31, 0);
    word32_t x_hi = (word32_t)x.range(63, 32);
    // MU = P^-1 mod 2^32 = 2^31 + 2^K + 1 for both fields, so t = x_lo * MU is a
    // three-operand shift-add rather than a multiplier array.
    word32_t t = (word32_t)(x_lo + (x_lo << K) + (x_lo << 31));
    // P = 2^31 - 2^K + 1, so u = t*P = (t<<31) + t - (t<<K): also shift-add only.
    ap_uint<64> T = (ap_uint<64>)t;
    ap_uint<64> u = (T << 31) + T - (T << K);
    word32_t u_hi = (word32_t)u.range(63, 32);
    word32_t r0 = (word32_t)(x_hi - u_hi);
    bool borrow = (x_hi < u_hi);
    return (word32_t)(r0 + (borrow ? P : (word32_t)0));
}

// Conditional subtract after an add: add the masked constant 2^32 - P.
static inline word32_t monty_add_corr(word32_t s, word32_t P, word32_t negP) {
#pragma HLS INLINE
    bool ge = (s >= P);
    return (word32_t)(s + (ge ? negP : (word32_t)0));
}
#endif
