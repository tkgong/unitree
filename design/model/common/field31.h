#ifndef UNITREE_FIELD31_H
#define UNITREE_FIELD31_H
#include "lanes.h"

static const word32_t P_M31 = 0x7FFFFFFFu;
static const word32_t P_BB  = 0x78000001u;
static const word32_t P_KB  = 0x7F000001u;

static inline word32_t m31_fold32(word32_t s) {
#pragma HLS INLINE
    return (word32_t)((s & P_M31) + (s >> 31));
}
static inline word32_t m31_reduce62(ap_uint<62> x) {
#pragma HLS INLINE
    word32_t lo = (word32_t)x.range(30, 0);
    word32_t hi = (word32_t)x.range(61, 31);
    return m31_fold32((word32_t)(lo + hi));
}
static inline word32_t m31_neg(word32_t x) {
#pragma HLS INLINE
    return (word32_t)(x ^ P_M31);
}
template<int N> static inline word32_t m31_mul2exp(word32_t x) {
#pragma HLS INLINE
    if (N == 0) return x;
    return (word32_t)(((x << N) | (x >> (31 - N))) & P_M31);
}

template<int K>
static inline word32_t monty_reduce(ap_uint<64> x, word32_t P) {
#pragma HLS INLINE
    word32_t x_lo = (word32_t)x.range(31, 0);
    word32_t x_hi = (word32_t)x.range(63, 32);
    word32_t t = (word32_t)(x_lo + (x_lo << K) + (x_lo << 31));
    ap_uint<64> T = (ap_uint<64>)t;
    ap_uint<64> u = (T << 31) + T - (T << K);
    word32_t u_hi = (word32_t)u.range(63, 32);
    word32_t r0 = (word32_t)(x_hi - u_hi);
    bool borrow = (x_hi < u_hi);
    return (word32_t)(r0 + (borrow ? P : (word32_t)0));
}

static inline word32_t monty_add_corr(word32_t s, word32_t P, word32_t negP) {
#pragma HLS INLINE
    bool ge = (s >= P);
    return (word32_t)(s + (ge ? negP : (word32_t)0));
}
#endif
