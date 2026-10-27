// shim_axn.cpp - DLL entry for pipe_axn.h (wide I/O: LP_NIO lanes): one call = one clock of the pipeline.
// The unit has no mode: every call carries its operation control (mono, htap, blake, round indices).
// A program runs one primitive on one tree kind (Merkle or GGM).
#include "pipe_axn.h"
// mono2 / r2: the second Monolith datapath (lanes AXN_MBASE2..), when AXN_NDP == 2; ignored otherwise
// er: round index of each Poseidon2 internal-round engine (P2ENG_N engines, lanes P2ENG_BASE + 8 e ..)
extern "C" __declspec(dllexport) void lp_step_e(int mono, int mono2, int htap, int blake, int r, int r2, const int* rg, const int* er,
                                                const unsigned long long* in, unsigned long long* out) {
    lane_t a[LP_NIO], b[LP_NIO];
    ap_uint<9> rr[AXN_NG];
    for (int g = 0; g < AXN_NG; g++) rr[g] = (ap_uint<9>)rg[g];
    for (int i = 0; i < LP_NIO; i++) a[i] = in[i];
#ifdef P2ENG_N
    ap_uint<4> ee[P2ENG_N];
    for (int e = 0; e < P2ENG_N; e++) ee[e] = (ap_uint<4>)(er ? er[e] : 0);
    lane_pipe(a, b, (ap_uint<1>)mono, (ap_uint<1>)mono2, (ap_uint<1>)htap, (ap_uint<1>)blake, (ap_uint<9>)r, (ap_uint<9>)r2, rr, (ap_uint<1>)0, ee);
#else
    (void)er;
    lane_pipe(a, b, (ap_uint<1>)mono, (ap_uint<1>)mono2, (ap_uint<1>)htap, (ap_uint<1>)blake, (ap_uint<9>)r, (ap_uint<9>)r2, rr, (ap_uint<1>)0);
#endif
    for (int i = 0; i < LP_NIO; i++) out[i] = (unsigned long long)b[i];
}
extern "C" __declspec(dllexport) void lp_step_x(int mono, int mono2, int htap, int blake, int r, int r2, const int* rg,
                                                const unsigned long long* in, unsigned long long* out) {
    lp_step_e(mono, mono2, htap, blake, r, r2, rg, nullptr, in, out);
}
// the operation bits of a whole issue from the primitive (1 BLAKE3, 2 ChaCha20, 4 Monolith); both Monolith datapaths in lockstep
extern "C" __declspec(dllexport) void lp_step_g(int mode, const int* rg, int r, const unsigned long long* in, unsigned long long* out) {
    lp_step_x(mode == 4, mode == 4, mode != 4, mode == 1, r, r, rg, in, out);
}
extern "C" __declspec(dllexport) void lp_step(int mode, int cfg, int r, const unsigned long long* in, unsigned long long* out) {   // all groups at round r
    int rg[AXN_NG];
    for (int g = 0; g < AXN_NG; g++) rg[g] = r;
    (void)cfg;
    lp_step_g(mode, rg, r, in, out);
}
extern "C" __declspec(dllexport) int lp_info(int what) {
    if (what == 0) return MONO_NISS;
    if (what == 1) return AXN_NB;
    if (what == 9) return LP_NIO;
    if (what == 10) return MONO_BASE;
    if (what == 11) return AXN_BL;
    if (what == 12) return AXN_MERKLE_FLAG;
    if (what == 13) return AXN_COLOC;
    if (what == 14) return AXN_NG;
    if (what == 15) return LP_DEPTH_M;                                        // number of pipeline levels
    if (what == 17) return AXN_MBASE2;                                        // state lanes of the second Monolith datapath (0: none)
    if (what == 18) return AXN_NDP;                                           // Monolith datapaths (states issued per cycle)
#ifdef MONO_P2
    if (what == 19) return 1;                                                 // Poseidon2 issues available on the Monolith datapath(s)
    if (what == 20) return MONO_SQD;                                          // Y tap level (out lanes BASE+8..)
    if (what == 21) return MONO_P2_LE;                                        // M_E tap level (out lanes BASE+16..)
    if (what == 22) return MONO_P2_LI;                                        // M_I tap level (out lanes BASE+24..)
    if (what == 23) return MONO_P2_R_SQ;                                      // r codes of the Poseidon2 issue kinds
    if (what == 24) return MONO_P2_R_INIT;
    if (what == 25) return MONO_P2_R_X5E;
    if (what == 26) return MONO_P2_R_X5I;
#ifdef MONO_P2_MUL3
    if (what == 28) return MONO_P2_MUL3;                                      // three multiplier ranks: 23-issue program
#endif
#ifdef MONO_P2_A1
    if (what == 29) return MONO_P2_A1;                                        // state lanes only (no B / C operands)
#endif
#ifdef MONO_ONLY_P2
    if (what == 27) return MONO_ONLY_P2;                                      // natural Poseidon2 unit: no Bars / Concrete (no Monolith issues)
#endif
#endif
#ifdef P2ENG_N
    if (what == 30) return P2ENG_N;                                           // Poseidon2 internal-round engines
    if (what == 31) return P2ENG_BASE;                                        // their lanes: P2ENG_BASE + 8 e
    if (what == 32) return P2ENG_LAT;                                         // calls from issue to result
#endif
    if (what >= 1000 && what < 1000 + 2 * AXN_NB) return (what - 1000) % 2 == 0 ? axn_b((what - 1000) / 2) : axn_h((what - 1000) / 2);   // block base / h lanes
    if (what >= 2000 && what < 2000 + AXN_NB) return AXN_BG[what - 2000];        // group of block
    if (what >= 3000 && what < 3000 + AXN_NG) return AXN_GD[what - 3000];        // latency of group
    if (what >= 3100 && what < 3100 + AXN_NG) return AXN_GN[what - 3100];        // blocks of group
    if (what >= 3200 && what < 3200 + AXN_NG) return AXN_GL0[what - 3200];       // entry level of group
    if (what >= 3300 && what < 3300 + 6 * AXN_NG) return AXN_GLV[(what - 3300) / 6][(what - 3300) % 6];   // step levels of group (0: in another span)
    if (what >= 4000 && what < 4000 + AXN_NG) return AXN_GS0[what - 4000];       // first step of group (span)
    if (what >= 4100 && what < 4100 + AXN_NG) return AXN_GCH[what - 4100];       // chain of group
    const int D[5] = {LP_DEPTH_K, LP_DEPTH_S, LP_DEPTH_C, LP_DEPTH_A, LP_DEPTH_M};
    if (what >= 2 && what <= 6) return D[what - 2];
    return 0;
}
