// lanes.h - shared types and constant-amount rotation helpers for the unitree DSE.
// Every rotation is a template on the amount so Vitis HLS never infers a barrel shifter.
#ifndef UNITREE_LANES_H
#define UNITREE_LANES_H
#include <ap_int.h>
typedef ap_uint<64> lane_t;
typedef ap_uint<32> word32_t;
typedef ap_uint<8>  byte_t;

template<int N> inline lane_t rotl64(lane_t x) {
#pragma HLS INLINE
    if (N == 0) return x;
    return (x << N) | (x >> (64 - N));
}
template<int N> inline word32_t rotl32(word32_t x) {
#pragma HLS INLINE
    if (N == 0) return x;
    return (x << N) | (x >> (32 - N));
}
template<int N> inline word32_t rotr32(word32_t x) {
#pragma HLS INLINE
    if (N == 0) return x;
    return (x >> N) | (x << (32 - N));
}
// 2x32 SIMD rotate-left of both halves of a lane by the same amount.
template<int N> inline lane_t rotl2x32(lane_t x) {
#pragma HLS INLINE
    word32_t lo = x.range(31, 0), hi = x.range(63, 32);
    lane_t r;
    r.range(31, 0)  = rotl32<N>(lo);
    r.range(63, 32) = rotl32<N>(hi);
    return r;
}
template<int N> inline lane_t rotr2x32(lane_t x) {
#pragma HLS INLINE
    word32_t lo = x.range(31, 0), hi = x.range(63, 32);
    lane_t r;
    r.range(31, 0)  = rotr32<N>(lo);
    r.range(63, 32) = rotr32<N>(hi);
    return r;
}
// 8x8 SIMD rotate-left inside every byte of a lane.
template<int N> inline lane_t rotl8x8(lane_t x) {
#pragma HLS INLINE
    lane_t r;
    for (int b = 0; b < 8; b++) {
#pragma HLS UNROLL
        byte_t v = x.range(8 * b + 7, 8 * b);
        byte_t o = (N == 0) ? v : (byte_t)((v << N) | (v >> (8 - N)));
        r.range(8 * b + 7, 8 * b) = o;
    }
    return r;
}
#endif
