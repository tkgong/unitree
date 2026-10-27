// alu_core.h - the ALUs of the TOP unit (bz, bz3) and of its natural comparison units (pwe, nat38c).
// Every arithmetic or logic operator of the datapaths (gen_lane_mono6.py output), the ARX steps (level_ops_axn.h), the
// ARX-only adders (gen_pipe_axn.py output) and the Poseidon2 engines (p2_engine.h) is a call of one of these functions.
// What stays outside is wiring: constant rotations (rot31, rotl2x32), lane packing (pk, LO, HI), the permutations
// P / sigma, the << j shifts and the ~ / ^ p inversions of Concrete operands, and the 2-way selects of the control bits.
//
//   ALU-ADD   alu_add<W>        W-bit lendable adder: the Concrete adders of the two datapaths (912 in bz / bz3).
//                               A non-inlined module, so every call site is one adder instance.
//             alu_lend<W>       its operand select: the ARX operands (EA, EB) when ext (no datapath issue at this
//                               level), else the datapath's own; the sum goes back to the ARX block as EY.
//             alu_lendp<W>      the same select in front of a private (inlined) adder, for builds without
//                               MONO_LEND_MOD
//   ALU-ADP   alu_addp<W>       W-bit private adder: engine part sums and constants, ARX-only builds' adders, the
//                               datapath adders that are not lent
//   ALU-MUL   alu_mul31         31 x 31 -> 62 multiplier (Bricks squares, x^2 x^4 x^5)
//             alu_mul31_en      the same, 0 when the issue has no Bricks
//   ALU-FLD   alu_fold<H>       M31 end-around carry of a 32-bit sum r: the low H bits of r + r[31]; alu_fold31: the
//                               whole 31-bit word
//             alu_canon<T>      p -> 0 (canonical M31)
//             alu_negm31<W>     p - t (t <= p), the W-bit operand of an add
//   ALU-BAR   alu_bar31         Monolith Bars S-box on one 31-bit element (8 / 8 / 8 / 7-bit chunks)
//   ALU-XOR   alu_xor           64-bit xor: the ARX blocks' own logic
//   wiring    rot31<R>          31-bit rotation = 2^R * x mod p
#pragma once
#include "lanes.h"

static const ap_uint<31> ALU_P31 = 0x7FFFFFFFu;   // 2^31 - 1

// ---- ALU-ADD ----
template<int W> static ap_uint<W> alu_add(ap_uint<W> a, ap_uint<W> b) {
#pragma HLS INLINE off
    return a + b;
}
template<int W> static inline ap_uint<W> alu_lend(bool ext, ap_uint<W> ea, ap_uint<W> eb, ap_uint<W> a, ap_uint<W> b) {
#pragma HLS INLINE
    ap_uint<W> la = ext ? ea : a;
    ap_uint<W> lb = ext ? eb : b;
    return alu_add<W>(la, lb);
}
// ---- ALU-ADP ----
template<int W> static inline ap_uint<W> alu_addp(ap_uint<W> a, ap_uint<W> b) {
#pragma HLS INLINE
    return a + b;
}
template<int W> static inline ap_uint<W> alu_lendp(bool ext, ap_uint<W> ea, ap_uint<W> eb, ap_uint<W> a, ap_uint<W> b) {
#pragma HLS INLINE
    ap_uint<W> la = ext ? ea : a;
    ap_uint<W> lb = ext ? eb : b;
    return alu_addp<W>(la, lb);
}
// ---- ALU-MUL ----
static inline ap_uint<62> alu_mul31(ap_uint<31> a, ap_uint<31> b) {
#pragma HLS INLINE
    return (ap_uint<62>)((ap_uint<62>)a * (ap_uint<62>)b);
}
static inline ap_uint<62> alu_mul31_en(bool en, ap_uint<31> a, ap_uint<31> b) {
#pragma HLS INLINE
    return en ? (ap_uint<62>)((ap_uint<62>)a * (ap_uint<62>)b) : (ap_uint<62>)0;
}
// ---- ALU-FLD ----
static inline ap_uint<31> alu_fold31(ap_uint<32> r) {
#pragma HLS INLINE
    return (ap_uint<31>)((ap_uint<31>)r.range(30, 0) + (ap_uint<31>)r[31]);
}
template<int H> static inline ap_uint<31> alu_fold(ap_uint<32> r) {   // H < 31
#pragma HLS INLINE
    ap_uint<31> t;
    t.range(30, H) = r.range(30, H);
    t.range(H - 1, 0) = (ap_uint<H>)((ap_uint<H>)r.range(H - 1, 0) + (ap_uint<H>)r[31]);
    return t;
}
template<typename T> static inline T alu_canon(ap_uint<31> t) {
#pragma HLS INLINE
    return (t == ALU_P31) ? (T)0 : (T)t;
}
template<int W> static inline ap_uint<W> alu_negm31(ap_uint<31> t) {
#pragma HLS INLINE
    return (ap_uint<W>)(ALU_P31 - t);
}
// ---- ALU-BAR ----
template<int W> static inline ap_uint<W> alu_bar_chunk(ap_uint<W> x) {
#pragma HLS INLINE
    ap_uint<W> nx = ~x;
    ap_uint<W> r1 = (nx << 1) | (nx >> (W - 1));
    ap_uint<W> r2 = (x << 2) | (x >> (W - 2));
    ap_uint<W> r3 = (x << 3) | (x >> (W - 3));
    ap_uint<W> t = x ^ (W == 7 ? (ap_uint<W>)(r1 & r2) : (ap_uint<W>)(r1 & r2 & r3));   // the 7-bit chunk has two rotations
    return (t << 1) | (t >> (W - 1));
}
static inline word32_t alu_bar31(word32_t x) {
#pragma HLS INLINE
    word32_t y = 0;
    y.range(7, 0)   = alu_bar_chunk<8>(x.range(7, 0));
    y.range(15, 8)  = alu_bar_chunk<8>(x.range(15, 8));
    y.range(23, 16) = alu_bar_chunk<8>(x.range(23, 16));
    y.range(30, 24) = alu_bar_chunk<7>(x.range(30, 24));
    return y;
}
// ---- ALU-XOR ----
static inline lane_t alu_xor(lane_t a, lane_t b) {
#pragma HLS INLINE
    return a ^ b;
}
// ---- wiring ----
template<int R> static inline ap_uint<31> rot31(ap_uint<31> v) {
#pragma HLS INLINE
    if (R == 0) return v;
    return (ap_uint<31>)((v << R) | (v >> (31 - R)));
}
