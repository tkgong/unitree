// tb_tree.cpp - Verilator: a depth-2 tree of every kind on the RTL/fsm tops, level by level, against the CPU baselines
// (vec_tree/tree.hex from gen_tree_vectors.py: leaves[32] seed[8] b3_root[8] mono_root[8] cc_leaves[32] b3ggm_leaves[32]).
//   TOP_SHARED: top_shared #(NB 2): BLAKE3 Merkle, Monolith Merkle, ChaCha20 GGM, BLAKE3-XOF GGM
//   TOP_BLAKE3: top_blake3 #(2): BLAKE3 Merkle + GGM     TOP_CHACHA: top_chacha #(2): ChaCha20 GGM     TOP_MONO: Monolith Merkle
// Merkle: level 1 = two parents on two blocks (Monolith: two runs), level 2 = the root. GGM: level 0 = the seed on one
// block (two children), level 1 = two blocks (four leaves).
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <vector>
#include "verilated.h"
#if defined(TOP_MONO)
#include "Vtop_mono.h"
typedef Vtop_mono DUT;
#elif defined(TOP_CHACHA)
#include "Vtop_chacha.h"
typedef Vtop_chacha DUT;
#elif defined(TOP_BLAKE3)
#include "Vtop_blake3.h"
typedef Vtop_blake3 DUT;
#else
#include "Vtop_shared.h"
typedef Vtop_shared DUT;
#endif
static const uint32_t IV[8] = {0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A, 0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19};
static const uint32_t CC[4] = {0x61707865, 0x3320646E, 0x79622D32, 0x6B206574};
enum { PARENT = 4, ROOT = 8, KEYED = 16, START = 1, END = 2 };
static DUT* dut; static uint64_t tcyc = 0; static int bad = 0;
static void tick() { dut->clk = 0; dut->eval(); dut->clk = 1; dut->eval(); tcyc++; }
template <class W> static void setw(W& w, int i, uint32_t v) { w.data()[i] = v; }          // VlWide: 32-bit words
template <class W> static uint32_t getw(const W& w, int i) { return w.data()[i]; }
template <class W> static void set31(W& w, int i, uint32_t v) {                             // element i of a 16 x 31-bit vector
    uint64_t pos = (uint64_t)i * 31; for (int b = 0; b < 31; b++) { uint64_t p = pos + b; uint32_t m = 1u << (p % 32);
        if ((v >> b) & 1) w.data()[p / 32] |= m; else w.data()[p / 32] &= ~m; } }
template <class W> static uint32_t get31(const W& w, int i) {
    uint64_t pos = (uint64_t)i * 31; uint32_t v = 0; for (int b = 0; b < 31; b++) { uint64_t p = pos + b; v |= ((w.data()[p / 32] >> (p % 32)) & 1u) << b; } return v; }
static int run(int prim) {                                                                   // start, wait for done -> cycles
    dut->start = 1;
#ifndef TOP_NAT
    dut->prim = prim;
#endif
    tick(); dut->start = 0; int c = 0;
    while (!dut->done) { tick(); c++; if (c > 1000) { printf("timeout\n"); exit(1); } }
    return c;
}
static void cmp(const char* what, const uint32_t* got, const uint32_t* exp, int n) {
    int e = 0; for (int i = 0; i < n; i++) if (got[i] != exp[i]) e++;
    bad += e; printf("  %-28s %s", what, e ? "MISMATCH" : "OK");
    if (e) printf(" (%d of %d words; got %08x expected %08x)", e, n, got[0], exp[0]);
    printf("\n");
}
#ifndef TOP_MONO
// ---- ARX blocks: load block b with the compress16 / ChaCha framing, run, read 16 output words ----
static void arx_in(int b, const uint32_t* v, const uint32_t* m, const uint32_t* h) {
#ifdef TOP_SHARED
    for (int i = 0; i < 16; i++) { setw(dut->arx_v, b * 16 + i, v[i]); setw(dut->arx_m, b * 16 + i, m[i]); }
    for (int i = 0; i < 8; i++) setw(dut->arx_h, b * 8 + i, h[i]);
#elif defined(TOP_BLAKE3)
    for (int i = 0; i < 16; i++) { setw(dut->in_v, b * 16 + i, v[i]); setw(dut->in_m, b * 16 + i, m[i]); }
    for (int i = 0; i < 8; i++) setw(dut->in_h, b * 8 + i, h[i]);
#else
    for (int i = 0; i < 16; i++) setw(dut->in_v, b * 16 + i, v[i]);
#endif
}
static void arx_out(int b, uint32_t* o) {
#ifdef TOP_SHARED
    for (int i = 0; i < 16; i++) o[i] = getw(dut->arx_out, b * 16 + i);
#else
    for (int i = 0; i < 16; i++) o[i] = getw(dut->out, b * 16 + i);
#endif
}
static void b3_frame(const uint32_t* h, uint32_t flags, uint32_t* v) {                    // v = h | IV[0..3] | 0 | 0 | 64 | flags
    memcpy(v, h, 32); memcpy(v + 8, IV, 16); v[12] = 0; v[13] = 0; v[14] = 64; v[15] = flags;
}
#endif
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    std::vector<uint32_t> W; { FILE* f = fopen("vec_tree/tree.hex", "r"); if (!f) { printf("no vec_tree/tree.hex\n"); return 1; }
        unsigned x; while (fscanf(f, "%x", &x) == 1) W.push_back(x); fclose(f); }
    const uint32_t *leaves = &W[0], *seed = &W[32], *b3_root = &W[40], *mono_root = &W[48], *cc_leaves = &W[56], *b3g_leaves = &W[88];
    dut = new DUT; dut->clk = 0; dut->rst = 1; dut->start = 0; tick(); tick(); dut->rst = 0;
    uint32_t v[16], m[16], o[16], p[2][8], got[32];
#if defined(TOP_SHARED) || defined(TOP_BLAKE3)
    // BLAKE3 Merkle: parents = compress(IV, l || r, PARENT), root with ROOT
    for (int b = 0; b < 2; b++) { b3_frame(IV, PARENT, v); memcpy(m, leaves + 16 * b, 64); arx_in(b, v, m, IV); }
    int c1 = run(1); for (int b = 0; b < 2; b++) { arx_out(b, o); memcpy(p[b], o, 32); }
    b3_frame(IV, PARENT | ROOT, v); memcpy(m, p[0], 32); memcpy(m + 8, p[1], 32); arx_in(0, v, m, IV);
    int c2 = run(1); arx_out(0, o);
    printf("BLAKE3 Merkle depth 2 (official BLAKE3 C library): levels %d + %d cycles\n", c1, c2); cmp("root", o, b3_root, 8);
    // BLAKE3-XOF GGM: node = compress(seed, [idx, idx>>32, level, 0..], KEYED|START|END|ROOT), children = the 16 output words
    b3_frame(seed, KEYED | START | END | ROOT, v); memset(m, 0, 64); arx_in(0, v, m, seed);
    c1 = run(1); arx_out(0, o); memcpy(p[0], o, 32); memcpy(p[1], o + 8, 32);
    for (int b = 0; b < 2; b++) { b3_frame(p[b], KEYED | START | END | ROOT, v); memset(m, 0, 64); m[0] = b; m[2] = 1; arx_in(b, v, m, p[b]); }
    c2 = run(1); for (int b = 0; b < 2; b++) { arx_out(b, o); memcpy(got + 16 * b, o, 64); }
    printf("BLAKE3-XOF GGM depth 2 (blake3_compress_xof): levels %d + %d cycles\n", c1, c2); cmp("4 leaves", got, b3g_leaves, 32);
#endif
#if defined(TOP_SHARED) || defined(TOP_CHACHA)
    // ChaCha20 GGM: node = Block(CC | seed | idx, idx>>32, level, 0), children = the 16 output words
    memcpy(v, CC, 16); memcpy(v + 4, seed, 32); v[12] = 0; v[13] = 0; v[14] = 0; v[15] = 0; arx_in(0, v, v, IV);
    int d1 = run(0); arx_out(0, o); memcpy(p[0], o, 32); memcpy(p[1], o + 8, 32);
    for (int b = 0; b < 2; b++) { memcpy(v, CC, 16); memcpy(v + 4, p[b], 32); v[12] = b; v[13] = 0; v[14] = 1; v[15] = 0; arx_in(b, v, v, IV); }
    int d2 = run(0); for (int b = 0; b < 2; b++) { arx_out(b, o); memcpy(got + 16 * b, o, 64); }
    printf("ChaCha20 GGM depth 2 (cpu_trees scalar): levels %d + %d cycles\n", d1, d2); cmp("4 leaves", got, cc_leaves, 32);
#endif
#if defined(TOP_SHARED) || defined(TOP_MONO)
    // Monolith-31 Merkle: parent = permutation(l || r)[0..7]
    int e1 = 0, e2;
    for (int b = 0; b < 2; b++) {
#ifdef TOP_SHARED
        for (int i = 0; i < 16; i++) set31(dut->mono_x, i, leaves[16 * b + i]);
        e1 += run(2); for (int i = 0; i < 8; i++) p[b][i] = get31(dut->mono_y, i);
#else
        for (int i = 0; i < 16; i++) set31(dut->x, i, leaves[16 * b + i]);
        e1 += run(2); for (int i = 0; i < 8; i++) p[b][i] = get31(dut->y, i);
#endif
    }
#ifdef TOP_SHARED
    for (int i = 0; i < 8; i++) { set31(dut->mono_x, i, p[0][i]); set31(dut->mono_x, 8 + i, p[1][i]); }
    e2 = run(2); for (int i = 0; i < 8; i++) o[i] = get31(dut->mono_y, i);
#else
    for (int i = 0; i < 8; i++) { set31(dut->x, i, p[0][i]); set31(dut->x, 8 + i, p[1][i]); }
    e2 = run(2); for (int i = 0; i < 8; i++) o[i] = get31(dut->y, i);
#endif
    printf("Monolith-31 Merkle depth 2 (Plonky3 p3-monolith): levels 2 x %d + %d cycles\n", e1 / 2, e2); cmp("root", o, mono_root, 8);
#endif
    printf("SUMMARY: %s, %llu cycles simulated, %d mismatching words\n", TOPNAME, (unsigned long long)tcyc, bad);
    delete dut; return bad ? 1 : 0;
}
