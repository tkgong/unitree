// ref_alu.cpp - the HLS ALUs (dse/TOP/alu_core.h) exported one by one, so Python can produce reference vectors for the
// SystemVerilog modules in RTL/ from the very C++ that csynth compiles.
#include "lanes.h"
#include "alu_core.h"
#include <cstdint>
#define EXP extern "C" __declspec(dllexport)

template<int W> static uint64_t add_w(uint64_t a, uint64_t b) { return (uint64_t)alu_add<W>((ap_uint<W>)a, (ap_uint<W>)b); }
template<int W> static uint64_t lend_w(int ext, uint64_t ea, uint64_t eb, uint64_t a, uint64_t b) {
    return (uint64_t)alu_lend<W>(ext != 0, (ap_uint<W>)ea, (ap_uint<W>)eb, (ap_uint<W>)a, (ap_uint<W>)b); }
template<int W> static uint64_t addp_w(uint64_t a, uint64_t b) { return (uint64_t)alu_addp<W>((ap_uint<W>)a, (ap_uint<W>)b); }
template<int W> static uint64_t lendp_w(int ext, uint64_t ea, uint64_t eb, uint64_t a, uint64_t b) {
    return (uint64_t)alu_lendp<W>(ext != 0, (ap_uint<W>)ea, (ap_uint<W>)eb, (ap_uint<W>)a, (ap_uint<W>)b); }
template<int H> static uint64_t fold_h(uint64_t r) { return (uint64_t)alu_fold<H>((ap_uint<32>)r); }
template<int W> static uint64_t negm31_w(uint64_t t) { return (uint64_t)alu_negm31<W>((ap_uint<31>)t); }
template<int R> static uint64_t rot31_r(uint64_t v) { return (uint64_t)rot31<R>((ap_uint<31>)v); }

#define W_CASES(F, ...) switch (W) { case 32: return F<32>(__VA_ARGS__); case 33: return F<33>(__VA_ARGS__); case 34: return F<34>(__VA_ARGS__); \
    case 35: return F<35>(__VA_ARGS__); case 36: return F<36>(__VA_ARGS__); case 37: return F<37>(__VA_ARGS__); case 38: return F<38>(__VA_ARGS__); \
    case 39: return F<39>(__VA_ARGS__); case 40: return F<40>(__VA_ARGS__); case 41: return F<41>(__VA_ARGS__); case 31: return F<31>(__VA_ARGS__); \
    case 62: return F<62>(__VA_ARGS__); case 64: return F<64>(__VA_ARGS__); default: return ~0ull; }

EXP uint64_t ref_add(int W, uint64_t a, uint64_t b) { W_CASES(add_w, a, b) }
EXP uint64_t ref_lend(int W, int ext, uint64_t ea, uint64_t eb, uint64_t a, uint64_t b) { W_CASES(lend_w, ext, ea, eb, a, b) }
EXP uint64_t ref_addp(int W, uint64_t a, uint64_t b) { W_CASES(addp_w, a, b) }
EXP uint64_t ref_lendp(int W, int ext, uint64_t ea, uint64_t eb, uint64_t a, uint64_t b) { W_CASES(lendp_w, ext, ea, eb, a, b) }
EXP uint64_t ref_mul31(uint64_t a, uint64_t b) { return (uint64_t)alu_mul31((ap_uint<31>)a, (ap_uint<31>)b); }
EXP uint64_t ref_mul31_en(int en, uint64_t a, uint64_t b) { return (uint64_t)alu_mul31_en(en != 0, (ap_uint<31>)a, (ap_uint<31>)b); }
EXP uint64_t ref_fold31(uint64_t r) { return (uint64_t)alu_fold31((ap_uint<32>)r); }
EXP uint64_t ref_fold(int H, uint64_t r) {
    switch (H) {
#define C(h) case h: return fold_h<h>(r);
        C(1) C(2) C(3) C(4) C(5) C(6) C(7) C(8) C(9) C(10) C(11) C(12) C(13) C(14) C(15) C(16) C(17) C(18) C(19) C(20)
        C(21) C(22) C(23) C(24) C(25) C(26) C(27) C(28) C(29) C(30)
#undef C
        default: return ~0ull; }
}
EXP uint64_t ref_canon32(uint64_t t) { return (uint64_t)alu_canon<word32_t>((ap_uint<31>)t); }
EXP uint64_t ref_canon31(uint64_t t) { return (uint64_t)alu_canon<ap_uint<31> >((ap_uint<31>)t); }
EXP uint64_t ref_negm31(int W, uint64_t t) { switch (W) { case 31: return negm31_w<31>(t); case 32: return negm31_w<32>(t);
    case 33: return negm31_w<33>(t); case 34: return negm31_w<34>(t); case 35: return negm31_w<35>(t); default: return ~0ull; } }
EXP uint64_t ref_bar31(uint64_t x) { return (uint64_t)alu_bar31((word32_t)x); }
EXP uint64_t ref_bar_chunk8(uint64_t x) { return (uint64_t)alu_bar_chunk<8>((ap_uint<8>)x); }
EXP uint64_t ref_bar_chunk7(uint64_t x) { return (uint64_t)alu_bar_chunk<7>((ap_uint<7>)x); }
EXP uint64_t ref_xor(uint64_t a, uint64_t b) { return (uint64_t)alu_xor((lane_t)a, (lane_t)b); }
EXP uint64_t ref_rot31(int R, uint64_t v) {
    switch (R) {
#define C(r) case r: return rot31_r<r>(v);
        C(0) C(1) C(2) C(3) C(4) C(5) C(6) C(7) C(8) C(9) C(10) C(11) C(12) C(13) C(14) C(15) C(16) C(17) C(18) C(19) C(20)
        C(21) C(22) C(23) C(24) C(25) C(26) C(27) C(28) C(29) C(30)
#undef C
        default: return ~0ull; }
}
