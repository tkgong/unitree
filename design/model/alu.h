#ifndef UNITREE_ALU_H
#define UNITREE_ALU_H
#include "lanes.h"
#include "field31.h"

#ifdef ALU_INLINE
#define ALU_ATTR _Pragma("HLS INLINE")
#else
#define ALU_ATTR _Pragma("HLS INLINE off")
#endif

#define A_XOR   0
#define A_XOR3  1
#define A_ADD2  2
#define A_ADDF  3
#define A_ADD64 4
static inline lane_t gap_chain(lane_t a, lane_t b, bool wide) {
#pragma HLS INLINE
    ap_uint<65> A = ((ap_uint<65>)a.range(63, 32) << 33) | ((ap_uint<65>)(wide ? 1 : 0) << 32) | (ap_uint<65>)a.range(31, 0);
    ap_uint<65> B = ((ap_uint<65>)b.range(63, 32) << 33) | (ap_uint<65>)b.range(31, 0);
    ap_uint<65> R = A + B;
    lane_t r; r.range(31, 0) = R.range(31, 0); r.range(63, 32) = R.range(64, 33); return r;
}
template<int M>
static lane_t alu_a_t(lane_t a, lane_t b, lane_t c, ap_uint<3> op) {
    ALU_ATTR
    const bool HX  = (M & (1 << A_XOR)) != 0,  HX3 = (M & (1 << A_XOR3)) != 0;
    const bool H2  = (M & (1 << A_ADD2)) != 0, HF  = (M & (1 << A_ADDF)) != 0, H64 = (M & (1 << A_ADD64)) != 0;
    const bool HASX = HX || HX3, HASA = H2 || HF || H64;
    lane_t x = 0, s = 0;
    if (HASX) {
        if (HX && HX3) x = a ^ b ^ ((op == A_XOR3) ? c : (lane_t)0);
        else if (HX3)  x = a ^ b ^ c;
        else           x = a ^ b;
    }
    if (HASA) {
        bool wide = H64 && (!(H2 || HF) || op == A_ADD64);
        s = gap_chain(a, b, wide);
        if (HF) {
            bool fold = !(H2 || H64) || op == A_ADDF;
            if (fold) { s.range(31, 0) = m31_fold32(s.range(31, 0)); s.range(63, 32) = m31_fold32(s.range(63, 32)); }
        }
    }
    if (HASX && HASA) return (op == A_XOR || op == A_XOR3) ? x : s;
    return HASX ? x : s;
}
static lane_t alu_a(lane_t a, lane_t b, lane_t c, ap_uint<3> op) {
    ALU_ATTR
    return alu_a_t<0x1F>(a, b, c, op);
}

#define B_CHI   0
#define B_CH    1
#define B_MAJ   2
#define B_MAJCH 3
#define B_PXOR  4
static lane_t alu_b(lane_t a, lane_t b, lane_t c, ap_uint<3> fn) {
    ALU_ATTR
    lane_t chi = a ^ ((~b) & c);
    lane_t ch  = (a & b) ^ ((~a) & c);
    lane_t maj = (a & b) ^ (a & c) ^ (b & c);
    lane_t majch; majch.range(31, 0) = maj.range(31, 0); majch.range(63, 32) = ch.range(63, 32);
    lane_t xt;
    for (int i = 0; i < 8; i++) {
#pragma HLS UNROLL
        byte_t v = b.range(8 * i + 7, 8 * i);
        byte_t t = (byte_t)(v << 1);
        xt.range(8 * i + 7, 8 * i) = v[7] ? (byte_t)(t ^ 0x1B) : t;
    }
    lane_t pxor = a ^ xt;
    switch (fn) {
        case B_CHI:   return chi;
        case B_CH:    return ch;
        case B_MAJ:   return maj;
        case B_MAJCH: return majch;
        default:      return pxor;
    }
}

#define C_AES  0
#define C_BAR8 1
#define C_BAR7 2
static const byte_t SBOX_PAGES[768] = {
#include "aes_sbox.inc"
,
#include "bar8.inc"
,
#include "bar7.inc"
};
static byte_t alu_c(byte_t x, ap_uint<2> page) {
#pragma HLS INLINE off
#pragma HLS BIND_STORAGE variable=SBOX_PAGES type=rom_1p impl=lutram
    ap_uint<10> a = ((ap_uint<10>)page << 8) | x;
    return SBOX_PAGES[(unsigned)a];
}

static const byte_t SBOX_AES_T[256] = {
#include "aes_sbox.inc"
};
static const byte_t SBOX_BAR8_T[256] = {
#include "bar8.inc"
};
static const byte_t SBOX_BAR7_T[256] = {
#include "bar7.inc"
};
static byte_t alu_c_aes(byte_t x) {
#pragma HLS INLINE off
#pragma HLS BIND_STORAGE variable=SBOX_AES_T type=rom_1p impl=lutram
    return SBOX_AES_T[(unsigned)x]; }
static byte_t alu_c_bar8(byte_t x) {
#pragma HLS INLINE off
#pragma HLS BIND_STORAGE variable=SBOX_BAR8_T type=rom_1p impl=lutram
    return SBOX_BAR8_T[(unsigned)x]; }
static byte_t alu_c_bar7(byte_t x) {
#pragma HLS INLINE off
#pragma HLS BIND_STORAGE variable=SBOX_BAR7_T type=rom_1p impl=lutram
    return SBOX_BAR7_T[(unsigned)x]; }

static ap_uint<62> alu_d(word32_t a, word32_t b) {
    ALU_ATTR
    ap_uint<62> p = (ap_uint<62>)a.range(30, 0) * (ap_uint<62>)b.range(30, 0);
#pragma HLS BIND_OP variable=p op=mul impl=fabric
    return p;
}

static word32_t alu_e(ap_uint<62> x) {
    ALU_ATTR
    return m31_reduce62(x);
}

static inline lane_t pk(word32_t lo, word32_t hi) {
#pragma HLS INLINE
    lane_t r; r.range(31, 0) = lo; r.range(63, 32) = hi; return r;
}
static inline word32_t LO(lane_t x) {
#pragma HLS INLINE
    return x.range(31, 0); }
static inline word32_t HI(lane_t x) {
#pragma HLS INLINE
    return x.range(63, 32); }
static inline lane_t swap_halves(lane_t x) {
#pragma HLS INLINE
    return pk(HI(x), LO(x)); }
template<int NL, int NH> static inline lane_t rotr2(lane_t x) {
#pragma HLS INLINE
    return pk(rotr32<NL>(LO(x)), rotr32<NH>(HI(x))); }
template<int KL, int KH> static inline lane_t m31rot2(lane_t x) {
#pragma HLS INLINE
    return pk(m31_mul2exp<KL>(LO(x)), m31_mul2exp<KH>(HI(x))); }
static inline lane_t m31neg2(lane_t x) {
#pragma HLS INLINE
    return x ^ (lane_t)0x7FFFFFFF7FFFFFFFULL; }
template<int N> static inline lane_t rotcol8(lane_t x) {
#pragma HLS INLINE
    lane_t r;
    for (int c = 0; c < 2; c++) {
#pragma HLS UNROLL
        for (int i = 0; i < 4; i++) {
#pragma HLS UNROLL
            int src = (i + N) & 3;
            r.range(32 * c + 8 * i + 7, 32 * c + 8 * i) = x.range(32 * c + 8 * src + 7, 32 * c + 8 * src);
        }
    }
    return r;
}
#endif
