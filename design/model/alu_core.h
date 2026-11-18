#pragma once
#include "lanes.h"

static const ap_uint<31> ALU_P31 = 0x7FFFFFFFu;

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
static inline ap_uint<62> alu_mul31(ap_uint<31> a, ap_uint<31> b) {
#pragma HLS INLINE
    return (ap_uint<62>)((ap_uint<62>)a * (ap_uint<62>)b);
}
static inline ap_uint<62> alu_mul31_en(bool en, ap_uint<31> a, ap_uint<31> b) {
#pragma HLS INLINE
    return en ? (ap_uint<62>)((ap_uint<62>)a * (ap_uint<62>)b) : (ap_uint<62>)0;
}
static inline ap_uint<31> alu_fold31(ap_uint<32> r) {
#pragma HLS INLINE
    return (ap_uint<31>)((ap_uint<31>)r.range(30, 0) + (ap_uint<31>)r[31]);
}
template<int H> static inline ap_uint<31> alu_fold(ap_uint<32> r) {
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
template<int W> static inline ap_uint<W> alu_bar_chunk(ap_uint<W> x) {
#pragma HLS INLINE
    ap_uint<W> nx = ~x;
    ap_uint<W> r1 = (nx << 1) | (nx >> (W - 1));
    ap_uint<W> r2 = (x << 2) | (x >> (W - 2));
    ap_uint<W> r3 = (x << 3) | (x >> (W - 3));
    ap_uint<W> t = x ^ (W == 7 ? (ap_uint<W>)(r1 & r2) : (ap_uint<W>)(r1 & r2 & r3));
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
static inline lane_t alu_xor(lane_t a, lane_t b) {
#pragma HLS INLINE
    return a ^ b;
}
template<int R> static inline ap_uint<31> rot31(ap_uint<31> v) {
#pragma HLS INLINE
    if (R == 0) return v;
    return (ap_uint<31>)((v << R) | (v >> (31 - R)));
}
