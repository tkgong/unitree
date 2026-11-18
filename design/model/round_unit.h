#ifndef UNITREE_ROUND_UNIT_H
#define UNITREE_ROUND_UNIT_H
#include "alu.h"

#define M_KECCAK 0
#define M_SHA    1
#define M_CHACHA 2
#define M_AES    3
#define M_MONO   4
#define M_P2     5

#ifndef MODES_MASK
#define MODES_MASK 0x1F
#endif

static const lane_t KRC[24] = {
 0x0000000000000001ULL,0x0000000000008082ULL,0x800000000000808AULL,0x8000000080008000ULL,
 0x000000000000808BULL,0x0000000080000001ULL,0x8000000080008081ULL,0x8000000000008009ULL,
 0x000000000000008AULL,0x0000000000000088ULL,0x0000000080008009ULL,0x000000008000000AULL,
 0x000000008000808BULL,0x800000000000008BULL,0x8000000000008089ULL,0x8000000000008003ULL,
 0x8000000000008002ULL,0x8000000000000080ULL,0x000000000000800AULL,0x800000008000000AULL,
 0x8000000080008081ULL,0x8000000000008080ULL,0x0000000080000001ULL,0x8000000080008008ULL};
static const word32_t K256[64] = {
0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
static const byte_t RCON[12] = {0x00,0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1B,0x36,0x6C};
static const lane_t P2_RC[22][8] = {
#include "p2_constants.inc"
};

static const word32_t MONO_ROW[16] = {61402, 17845, 26798, 59689, 12021, 40901, 41351, 27521,
                                      56951, 12034, 53865, 43244, 7454, 33823, 28750, 1108};
static const lane_t MONO_RC[5][8] = {
#include "mono_constants.inc"
};
#include "mono_csd.inc"
static inline lane_t cmul_sel(int k, word32_t x) {
#pragma HLS INLINE
    switch (k) {
        case 0: return cmul<0>(x);
        case 1: return cmul<1>(x);
        case 2: return cmul<2>(x);
        case 3: return cmul<3>(x);
        case 4: return cmul<4>(x);
        case 5: return cmul<5>(x);
        case 6: return cmul<6>(x);
        case 7: return cmul<7>(x);
        case 8: return cmul<8>(x);
        case 9: return cmul<9>(x);
        case 10: return cmul<10>(x);
        case 11: return cmul<11>(x);
        case 12: return cmul<12>(x);
        case 13: return cmul<13>(x);
        case 14: return cmul<14>(x);
        case 15: return cmul<15>(x);
        default: return 0;
    }
}
#define CMUL_K(k, x) cmul_sel(k, x)
#ifndef MONO_SPLIT
#define MONO_SPLIT 4
#endif
#ifndef MONO_ISSUES
#define MONO_ISSUES (7 * MONO_SPLIT + 6)
#endif

#define IDX(x,y) ((x)+5*(y))
#define RHOPI(x,y,rr) B[IDX((y),(2*(x)+3*(y))%5)] = rotl64<rr>(A[IDX((x),(y))])

static inline void qr_pair(lane_t &a, lane_t &b, lane_t &c, lane_t &d) {
#pragma HLS INLINE
    const lane_t Z = 0;
    a = alu_a(a, b, Z, A_ADD2); d = rotl2x32<16>(alu_a(d, a, Z, A_XOR));
    c = alu_a(c, d, Z, A_ADD2); b = rotl2x32<12>(alu_a(b, c, Z, A_XOR));
    a = alu_a(a, b, Z, A_ADD2); d = rotl2x32<8>(alu_a(d, a, Z, A_XOR));
    c = alu_a(c, d, Z, A_ADD2); b = rotl2x32<7>(alu_a(b, c, Z, A_XOR));
}
static inline word32_t sbox5(word32_t x) {
#pragma HLS INLINE
    word32_t x2 = alu_e(alu_d(x, x));
    word32_t x4 = alu_e(alu_d(x2, x2));
    return alu_e(alu_d(x4, x));
}
static inline void p2_external(lane_t L[8]) {
#pragma HLS INLINE
    const lane_t Z = 0;
    lane_t G[8];
#pragma HLS ARRAY_PARTITION variable=G complete
    for (int g = 0; g < 4; g++) {
#pragma HLS UNROLL
        word32_t a0 = LO(L[2*g]), a1 = HI(L[2*g]), a2 = LO(L[2*g+1]), a3 = HI(L[2*g+1]);
        lane_t T  = alu_a(pk(a0, a2), pk(a1, a3), Z, A_ADDF);
        lane_t T4 = alu_a(T, swap_halves(T), Z, A_ADDF);
        lane_t U  = alu_a(T4, pk(a1, a3), Z, A_ADDF);
        lane_t Y02 = alu_a(U, T, Z, A_ADDF);
        lane_t Y13 = alu_a(U, pk(m31_mul2exp<1>(a2), m31_mul2exp<1>(a0)), Z, A_ADDF);
        G[2*g]   = pk(LO(Y02), LO(Y13));
        G[2*g+1] = pk(HI(Y02), HI(Y13));
    }
    lane_t C01 = alu_a(alu_a(G[0], G[2], Z, A_ADDF), alu_a(G[4], G[6], Z, A_ADDF), Z, A_ADDF);
    lane_t C23 = alu_a(alu_a(G[1], G[3], Z, A_ADDF), alu_a(G[5], G[7], Z, A_ADDF), Z, A_ADDF);
    for (int g = 0; g < 4; g++) {
#pragma HLS UNROLL
        L[2*g]   = alu_a(G[2*g],   C01, Z, A_ADDF);
        L[2*g+1] = alu_a(G[2*g+1], C23, Z, A_ADDF);
    }
}

#ifndef SLOT_UNIT
static inline void round_issue(const lane_t sin[25], lane_t sout[25], ap_uint<3> mode, ap_uint<9> r, ap_uint<1> cfg) {
#pragma HLS INLINE
#pragma HLS BIND_STORAGE variable=MONO_RC type=rom_1p impl=lutram
#pragma HLS BIND_STORAGE variable=P2_RC type=rom_1p impl=lutram
#pragma HLS BIND_STORAGE variable=KRC type=rom_1p impl=lutram
#pragma HLS BIND_STORAGE variable=K256 type=rom_1p impl=lutram
#pragma HLS BIND_STORAGE variable=RCON type=rom_1p impl=lutram
    const lane_t Z = 0;
    lane_t S[25];
#pragma HLS ARRAY_PARTITION variable=S complete
    for (int i = 0; i < 25; i++) {
#pragma HLS UNROLL
        S[i] = sin[i];
    }

    if (false) {
    }
#if MODES_MASK & 1
    else if (mode == M_KECCAK && r < 24) {
        lane_t C[5], D[5], A[25], B[25];
#pragma HLS ARRAY_PARTITION variable=C complete
#pragma HLS ARRAY_PARTITION variable=D complete
#pragma HLS ARRAY_PARTITION variable=A complete
#pragma HLS ARRAY_PARTITION variable=B complete
        for (int x = 0; x < 5; x++) {
#pragma HLS UNROLL
            lane_t c3 = alu_a(S[IDX(x,0)], S[IDX(x,1)], S[IDX(x,2)], A_XOR3);
            C[x] = alu_a(c3, S[IDX(x,3)], S[IDX(x,4)], A_XOR3);
        }
        for (int x = 0; x < 5; x++) {
#pragma HLS UNROLL
            D[x] = alu_a(C[(x+4)%5], rotl64<1>(C[(x+1)%5]), Z, A_XOR);
        }
        for (int i = 0; i < 25; i++) {
#pragma HLS UNROLL
            A[i] = alu_a(S[i], D[i%5], Z, A_XOR);
        }
        RHOPI(0,0,0); RHOPI(0,1,36); RHOPI(0,2,3); RHOPI(0,3,41); RHOPI(0,4,18);
        RHOPI(1,0,1); RHOPI(1,1,44); RHOPI(1,2,10); RHOPI(1,3,45); RHOPI(1,4,2);
        RHOPI(2,0,62); RHOPI(2,1,6); RHOPI(2,2,43); RHOPI(2,3,15); RHOPI(2,4,61);
        RHOPI(3,0,28); RHOPI(3,1,55); RHOPI(3,2,25); RHOPI(3,3,21); RHOPI(3,4,56);
        RHOPI(4,0,27); RHOPI(4,1,20); RHOPI(4,2,39); RHOPI(4,3,8);  RHOPI(4,4,14);
        for (int y = 0; y < 5; y++) {
#pragma HLS UNROLL
            for (int x = 0; x < 5; x++) {
#pragma HLS UNROLL
                S[IDX(x,y)] = alu_b(B[IDX(x,y)], B[IDX((x+1)%5,y)], B[IDX((x+2)%5,y)], B_CHI);
            }
        }
        S[0] = alu_a(S[0], KRC[r.range(4,0)], Z, A_XOR);
    }
#endif
#if MODES_MASK & 2
    else if (mode == M_SHA && r <= 64) {
        if (r < 64) {
            word32_t a = LO(S[0]), b = HI(S[0]), c = LO(S[1]), d = HI(S[1]);
            word32_t e = LO(S[2]), f = HI(S[2]), g = LO(S[3]), h = HI(S[3]);
            lane_t X   = pk(a, e);
            lane_t SIG = alu_a(rotr2<2,6>(X), rotr2<13,11>(X), rotr2<22,25>(X), A_XOR3);
            lane_t MC  = alu_b(pk(a, e), pk(b, f), pk(c, g), B_MAJCH);
            lane_t T   = alu_a(SIG, MC, Z, A_ADD2);
            lane_t HK  = alu_a(pk(0, h), pk(0, K256[r.range(5,0)]), Z, A_ADD2);
            lane_t HKW = alu_a(HK, pk(0, LO(S[4])), Z, A_ADD2);
            lane_t T12 = alu_a(T, HKW, Z, A_ADD2);
            lane_t AA  = alu_a(T12, swap_halves(T12), Z, A_ADD2);
            lane_t EE  = alu_a(pk(d, 0), pk(HI(T12), 0), Z, A_ADD2);
            word32_t W0 = LO(S[4]), W1 = HI(S[4]), W9 = HI(S[8]), W14 = LO(S[11]);
            lane_t SS = alu_a(pk(rotr32<7>(W1), rotr32<17>(W14)), pk(rotr32<18>(W1), rotr32<19>(W14)),
                              pk((word32_t)(W1 >> 3), (word32_t)(W14 >> 10)), A_XOR3);
            lane_t Q1 = alu_a(pk(W0, W9), SS, Z, A_ADD2);
            lane_t Q2 = alu_a(Q1, swap_halves(Q1), Z, A_ADD2);
            S[0] = pk(LO(AA), a); S[1] = pk(b, c); S[2] = pk(LO(EE), e); S[3] = pk(f, g);
            for (int k = 0; k < 7; k++) {
#pragma HLS UNROLL
                S[4+k] = pk(HI(S[4+k]), LO(S[5+k]));
            }
            S[11] = pk(HI(S[11]), LO(Q2));
        } else {
            for (int i = 0; i < 4; i++) {
#pragma HLS UNROLL
                S[12+i] = alu_a(S[12+i], S[i], Z, A_ADD2);
                S[i] = S[12+i];
            }
        }
    }
#endif
#if MODES_MASK & 4
    else if (mode == M_CHACHA && r <= 20) {
        if (r < 20) {
            bool diag = r[0];
            lane_t a1 = S[0], c1 = diag ? S[5] : S[4];
            lane_t b1 = diag ? pk(HI(S[2]), LO(S[3])) : S[2];
            lane_t d1 = diag ? pk(HI(S[7]), LO(S[6])) : S[6];
            lane_t a2 = S[1], c2 = diag ? S[4] : S[5];
            lane_t b2 = diag ? pk(HI(S[3]), LO(S[2])) : S[3];
            lane_t d2 = diag ? pk(HI(S[6]), LO(S[7])) : S[7];
            qr_pair(a1, b1, c1, d1);
            qr_pair(a2, b2, c2, d2);
            S[0] = a1; S[1] = a2;
            if (diag) {
                S[5] = c1; S[4] = c2;
                S[2] = pk(HI(b2), LO(b1)); S[3] = pk(HI(b1), LO(b2));
                S[6] = pk(HI(d1), LO(d2)); S[7] = pk(HI(d2), LO(d1));
            } else {
                S[4] = c1; S[5] = c2; S[2] = b1; S[3] = b2; S[6] = d1; S[7] = d2;
            }
        } else {
            for (int i = 0; i < 8; i++) {
#pragma HLS UNROLL
                S[i] = alu_a(S[i], S[8+i], Z, A_ADD2);
            }
        }
    }
#endif
#if MODES_MASK & 8
    else if (mode == M_AES && (r <= 10 || (r == 11 && cfg[0]))) {
        if (r <= 10) {
            for (int k = 0; k < 4; k++) {
#pragma HLS UNROLL
                lane_t V[2], K[2];
#pragma HLS ARRAY_PARTITION variable=V complete
#pragma HLS ARRAY_PARTITION variable=K complete
                K[0] = S[8+2*k]; K[1] = S[9+2*k];
                if (r == 0) {
                    V[0] = S[2*k]; V[1] = S[2*k+1];
                } else {
                    byte_t st[16], t[16];
#pragma HLS ARRAY_PARTITION variable=st complete
#pragma HLS ARRAY_PARTITION variable=t complete
                    for (int i = 0; i < 16; i++) {
#pragma HLS UNROLL
                        st[i] = S[2*k + (i>>3)].range(8*(i&7)+7, 8*(i&7));
                    }
                    for (int c = 0; c < 4; c++) {
#pragma HLS UNROLL
                        for (int rr = 0; rr < 4; rr++) {
#pragma HLS UNROLL
                            t[4*c+rr] = alu_c(st[4*((c+rr)&3)+rr], C_AES);
                        }
                    }
                    for (int j = 0; j < 2; j++) {
#pragma HLS UNROLL
                        lane_t T;
                        for (int i = 0; i < 8; i++) {
#pragma HLS UNROLL
                            T.range(8*i+7, 8*i) = t[8*j+i];
                        }
                        lane_t Sx  = alu_a(T, rotcol8<1>(T), Z, A_XOR);
                        lane_t ALL = alu_a(Sx, rotcol8<2>(T), rotcol8<3>(T), A_XOR3);
                        lane_t VA  = alu_a(T, ALL, Z, A_XOR);
                        lane_t O   = alu_b(VA, Sx, Z, B_PXOR);
                        V[j] = (r == 10) ? T : O;
                    }
                }
                S[2*k]   = alu_a(V[0], K[0], Z, A_XOR);
                S[2*k+1] = alu_a(V[1], K[1], Z, A_XOR);
                word32_t w3 = HI(K[1]);
                word32_t sw;
                sw.range(7, 0)   = alu_c(w3.range(15, 8), C_AES);
                sw.range(15, 8)  = alu_c(w3.range(23, 16), C_AES);
                sw.range(23, 16) = alu_c(w3.range(31, 24), C_AES);
                sw.range(31, 24) = alu_c(w3.range(7, 0), C_AES);
                ap_uint<4> ri = r.range(3, 0) + 1;
                word32_t tt = sw ^ (word32_t)RCON[ri];
                lane_t T0 = alu_a(K[0], pk(tt, 0), Z, A_XOR);
                lane_t T1 = alu_a(T0, pk(0, LO(T0)), Z, A_XOR);
                lane_t T2 = alu_a(K[1], pk(HI(T1), 0), Z, A_XOR);
                lane_t T3 = alu_a(T2, pk(0, LO(T2)), Z, A_XOR);
                S[8+2*k] = T1; S[9+2*k] = T3;
            }
        } else {
            for (int i = 0; i < 8; i++) {
#pragma HLS UNROLL
                S[i] = alu_a(S[i], S[16+i], Z, A_XOR);
            }
        }
    }
#endif
#if MODES_MASK & 16
    else if (mode == M_MONO && r < MONO_ISSUES) {
        const int SP = MONO_SPLIT, NO = 16 / MONO_SPLIT;
        bool init = (r < SP);
        ap_uint<7> q = init ? (ap_uint<7>)0 : (ap_uint<7>)(r - SP);
        ap_uint<4> k = q / (SP + 1);
        ap_uint<4> j = q % (SP + 1);
        bool bb = !init && (j == 0);
        ap_uint<4> part = init ? (ap_uint<4>)r : (ap_uint<4>)(j - 1);
        bool last = (part == SP - 1);
        bool addrc = last && !init && (k < 5);
        word32_t x[16];
#pragma HLS ARRAY_PARTITION variable=x complete
        for (int i = 0; i < 8; i++) {
#pragma HLS UNROLL
            x[2*i] = LO(S[i]); x[2*i+1] = HI(S[i]);
        }
        if (bb) {
            for (int i = 0; i < 8; i++) {
#pragma HLS UNROLL
                word32_t y;
                y.range(7, 0)   = alu_c(x[i].range(7, 0), C_BAR8);
                y.range(15, 8)  = alu_c(x[i].range(15, 8), C_BAR8);
                y.range(23, 16) = alu_c(x[i].range(23, 16), C_BAR8);
                y.range(30, 24) = alu_c((byte_t)x[i].range(30, 24), C_BAR7).range(6, 0);
                y[31] = 0;
                x[i] = y;
            }
            word32_t sq[16];
#pragma HLS ARRAY_PARTITION variable=sq complete
            sq[0] = 0;
            for (int i = 1; i < 16; i++) {
#pragma HLS UNROLL
                sq[i] = alu_e(alu_d(x[i-1], x[i-1]));
            }
            for (int i = 0; i < 8; i++) {
#pragma HLS UNROLL
                S[i] = alu_a(pk(x[2*i], x[2*i+1]), pk(sq[2*i], sq[2*i+1]), Z, A_ADDF);
            }
        } else {
            word32_t out[16];
#pragma HLS ARRAY_PARTITION variable=out complete
            for (int i = 0; i < 16; i++) {
#pragma HLS UNROLL
                out[i] = (i < 8) ? LO(S[8 + i/2]) : HI(S[8 + i/2]);
            }
            for (int i = 0; i < 16; i++) {
#pragma HLS UNROLL
                out[i] = (i & 1) ? HI(S[8 + i/2]) : LO(S[8 + i/2]);
            }
            for (int o = 0; o < NO; o++) {
#pragma HLS UNROLL
                ap_uint<4> i = part * NO + o;
                lane_t acc[16];
#pragma HLS ARRAY_PARTITION variable=acc complete
                for (int kk = 0; kk < 16; kk++) {
#pragma HLS UNROLL
                    word32_t xs = x[(ap_uint<4>)(i + kk)];
                    acc[kk] = CMUL_K(kk, xs);
                }
                for (int step = 1; step < 16; step *= 2) {
#pragma HLS UNROLL
                    for (int kk = 0; kk + step < 16; kk += 2 * step) {
#pragma HLS UNROLL
                        acc[kk] = alu_a(acc[kk], acc[kk + step], Z, A_ADD64);
                    }
                }
                word32_t v = alu_e((ap_uint<62>)acc[0].range(61, 0));
                for (int i2 = 0; i2 < 16; i2++) {
#pragma HLS UNROLL
                    if (i2 == i) out[i2] = v;
                }
            }
            if (last) {
                for (int i = 0; i < 8; i++) {
#pragma HLS UNROLL
                    lane_t v = pk(out[2*i], out[2*i+1]);
                    S[i] = addrc ? alu_a(v, MONO_RC[k][i], Z, A_ADDF) : v;
                }
            } else {
                for (int i = 0; i < 8; i++) {
#pragma HLS UNROLL
                    S[8 + i] = pk(out[2*i], out[2*i+1]);
                }
            }
        }
    }
#endif
#if MODES_MASK & 32
    else if (mode == M_P2 && r <= 22) {
        lane_t L[8];
#pragma HLS ARRAY_PARTITION variable=L complete
        for (int k = 0; k < 8; k++) {
#pragma HLS UNROLL
            L[k] = S[k];
        }
        bool full = (r >= 1 && r <= 4) || (r >= 19 && r <= 22);
        ap_uint<5> rc = (r == 0) ? (ap_uint<5>)0 : (ap_uint<5>)(r - 1);
        if (r == 0) {
            p2_external(L);
        } else if (full) {
            for (int k = 0; k < 8; k++) {
#pragma HLS UNROLL
                lane_t y = alu_a(L[k], P2_RC[rc][k], Z, A_ADDF);
                L[k] = pk(sbox5(LO(y)), sbox5(HI(y)));
            }
            p2_external(L);
        } else {
            lane_t y = alu_a(L[0], pk(LO(P2_RC[rc][0]), 0), Z, A_ADDF);
            L[0] = pk(sbox5(LO(y)), HI(L[0]));
            lane_t p0 = alu_a(L[0], L[1], Z, A_ADDF), p1 = alu_a(L[2], L[3], Z, A_ADDF);
            lane_t p2 = alu_a(L[4], L[5], Z, A_ADDF), p3 = alu_a(L[6], L[7], Z, A_ADDF);
            lane_t q0 = alu_a(p0, p1, Z, A_ADDF), q1 = alu_a(p2, p3, Z, A_ADDF);
            lane_t SE = alu_a(q0, q1, Z, A_ADDF);
            lane_t SUM = alu_a(SE, swap_halves(SE), Z, A_ADDF);
            lane_t D0 = pk(m31_neg(m31_mul2exp<1>(LO(L[0]))), m31_mul2exp<0>(HI(L[0])));
            L[0] = alu_a(SUM, D0, Z, A_ADDF);
            L[1] = alu_a(SUM, m31rot2<1,2>(L[1]), Z, A_ADDF);
            L[2] = alu_a(SUM, m31rot2<3,4>(L[2]), Z, A_ADDF);
            L[3] = alu_a(SUM, m31rot2<5,6>(L[3]), Z, A_ADDF);
            L[4] = alu_a(SUM, m31rot2<7,8>(L[4]), Z, A_ADDF);
            L[5] = alu_a(SUM, m31rot2<10,12>(L[5]), Z, A_ADDF);
            L[6] = alu_a(SUM, m31rot2<13,14>(L[6]), Z, A_ADDF);
            L[7] = alu_a(SUM, m31rot2<15,16>(L[7]), Z, A_ADDF);
        }
        for (int k = 0; k < 8; k++) {
#pragma HLS UNROLL
            S[k] = L[k];
        }
    }
#endif
    for (int i = 0; i < 25; i++) {
#pragma HLS UNROLL
        sout[i] = S[i];
    }
}
#endif
#endif
