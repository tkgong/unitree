#ifndef UNITREE_LEVEL_OPS_H
#define UNITREE_LEVEL_OPS_H
#define SLOT_UNIT 1
#include "round_unit.h"
#ifndef LANE_MONO_INC
#define LANE_MONO_INC "lane_mono_rp1.inc"
#endif
#ifndef AES_B
#define AES_B 4
#endif
#include LANE_MONO_INC

static inline lane_t add2(lane_t a, lane_t b) {
#pragma HLS INLINE
    return pk((word32_t)(LO(a) + LO(b)), (word32_t)(HI(a) + HI(b)));
}
#ifdef SBOX_BITSLICED
#include "sbox_bitsliced.h"
#endif
#ifdef SBOX_LOGIC
#include "sbox_logic.h"
static inline byte_t sbox(byte_t x) {
#pragma HLS INLINE
    return sbox_logic(x);
}
#else
static byte_t sbox(byte_t x) {
#pragma HLS INLINE off
#pragma HLS LATENCY max=0
#pragma HLS BIND_STORAGE variable=SBOX_AES_T type=rom_1p impl=lutram
    return SBOX_AES_T[(unsigned)x];
}
#endif

static inline void kec_l1(const lane_t S[], lane_t M[]) {
#pragma HLS INLINE
    for (int i = 0; i < 25; i++) {
#pragma HLS UNROLL
        M[i] = S[i];
    }
    for (int x = 0; x < 5; x++) {
#pragma HLS UNROLL
        M[25 + x] = S[IDX(x,0)] ^ S[IDX(x,1)] ^ S[IDX(x,2)];
    }
}
static inline void kec_l2(const lane_t S[], lane_t M[]) {
#pragma HLS INLINE
    for (int i = 0; i < 25; i++) {
#pragma HLS UNROLL
        M[i] = S[i];
    }
    for (int x = 0; x < 5; x++) {
#pragma HLS UNROLL
        M[25 + x] = S[25 + x] ^ S[IDX(x,3)] ^ S[IDX(x,4)];
    }
}
static inline void kec_l3(const lane_t S[], lane_t M[]) {
#pragma HLS INLINE
    for (int i = 0; i < 25; i++) {
#pragma HLS UNROLL
        M[i] = S[i];
    }
    for (int x = 0; x < 5; x++) {
#pragma HLS UNROLL
        M[25 + x] = S[25 + (x+4)%5] ^ rotl64<1>(S[25 + (x+1)%5]);
    }
}
static inline void kec_l4(const lane_t S[], lane_t M[]) {
#pragma HLS INLINE
    lane_t A[25], B[25];
    for (int i = 0; i < 25; i++) {
#pragma HLS UNROLL
        A[i] = S[i] ^ S[25 + i%5];
    }
    RHOPI(0,0,0); RHOPI(0,1,36); RHOPI(0,2,3); RHOPI(0,3,41); RHOPI(0,4,18);
    RHOPI(1,0,1); RHOPI(1,1,44); RHOPI(1,2,10); RHOPI(1,3,45); RHOPI(1,4,2);
    RHOPI(2,0,62); RHOPI(2,1,6); RHOPI(2,2,43); RHOPI(2,3,15); RHOPI(2,4,61);
    RHOPI(3,0,28); RHOPI(3,1,55); RHOPI(3,2,25); RHOPI(3,3,21); RHOPI(3,4,56);
    RHOPI(4,0,27); RHOPI(4,1,20); RHOPI(4,2,39); RHOPI(4,3,8);  RHOPI(4,4,14);
    for (int i = 0; i < 25; i++) {
#pragma HLS UNROLL
        M[i] = B[i];
    }
}
static inline void kec_l5(const lane_t B[], ap_uint<9> r, lane_t M[]) {
#pragma HLS INLINE
#pragma HLS BIND_STORAGE variable=KRC type=rom_1p impl=lutram
    for (int y = 0; y < 5; y++) {
#pragma HLS UNROLL
        for (int x = 0; x < 5; x++) {
#pragma HLS UNROLL
            M[IDX(x,y)] = B[IDX(x,y)] ^ (~B[IDX((x+1)%5,y)] & B[IDX((x+2)%5,y)]);
        }
    }
    M[0] = M[0] ^ KRC[r.range(4,0)];
}

static inline void sha_l1(const lane_t S[], ap_uint<9> r, lane_t M[]) {
#pragma HLS INLINE
#pragma HLS BIND_STORAGE variable=K256 type=rom_1p impl=lutram
    word32_t a = LO(S[0]), b = HI(S[0]), c = LO(S[1]);
    word32_t e = LO(S[2]), f = HI(S[2]), g = LO(S[3]), h = HI(S[3]);
    word32_t W1 = HI(S[4]), W14 = LO(S[11]);
    for (int i = 0; i < 16; i++) {
#pragma HLS UNROLL
        M[i] = S[i];
    }
    M[16] = pk(rotr32<2>(a) ^ rotr32<13>(a) ^ rotr32<22>(a), rotr32<6>(e) ^ rotr32<11>(e) ^ rotr32<25>(e));
    M[17] = pk((a & b) ^ (a & c) ^ (b & c), (e & f) ^ (~e & g));
    M[18] = pk(0, h + K256[r.range(5,0)]);
    M[19] = pk(rotr32<7>(W1) ^ rotr32<18>(W1) ^ (word32_t)(W1 >> 3), rotr32<17>(W14) ^ rotr32<19>(W14) ^ (word32_t)(W14 >> 10));
}
static inline void sha_l2_ops(const lane_t S[], word32_t EA[], word32_t EB[]) {
#pragma HLS INLINE
    EA[0] = LO(S[16]); EB[0] = LO(S[17]);
    EA[1] = HI(S[16]); EB[1] = HI(S[17]);
    EA[2] = HI(S[18]); EB[2] = LO(S[4]);
    EA[3] = LO(S[4]);  EB[3] = LO(S[19]);
    EA[4] = HI(S[8]);  EB[4] = HI(S[19]);
}
static inline void sha_l2_fin(const lane_t S[], const word32_t Y[], lane_t M[]) {
#pragma HLS INLINE
    for (int i = 0; i < 16; i++) {
#pragma HLS UNROLL
        M[i] = S[i];
    }
    M[16] = pk(Y[0], Y[1]); M[17] = pk(0, Y[2]); M[18] = pk(Y[3], Y[4]);
}
static inline void sha_l3_ops(const lane_t S[], word32_t EA[], word32_t EB[]) {
#pragma HLS INLINE
    EA[0] = LO(S[16]); EB[0] = LO(S[17]);
    EA[1] = HI(S[16]); EB[1] = HI(S[17]);
    EA[2] = LO(S[18]); EB[2] = HI(S[18]);
}
static inline void sha_l3_fin(const lane_t S[], const word32_t Y[], lane_t M[]) {
#pragma HLS INLINE
    for (int i = 0; i < 16; i++) {
#pragma HLS UNROLL
        M[i] = S[i];
    }
    M[16] = pk(Y[0], Y[1]); M[17] = pk(Y[2], Y[2]);
}
static inline void sha_l4_ops(const lane_t S[], word32_t EA[], word32_t EB[]) {
#pragma HLS INLINE
    EA[0] = LO(S[16]); EB[0] = HI(S[16]);
    EA[1] = HI(S[1]);  EB[1] = HI(S[16]);
}
static inline void sha_l4_fin(const lane_t S[], const word32_t Y[], lane_t M[]) {
#pragma HLS INLINE
    for (int i = 0; i < 16; i++) {
#pragma HLS UNROLL
        M[i] = S[i];
    }
    M[16] = pk(Y[0], Y[0]); M[17] = pk(Y[1], 0); M[18] = S[17];
}
static inline void sha_l5(const lane_t S[], ap_uint<9> r, lane_t M[]) {
#pragma HLS INLINE
    bool ff = (r == 64);
    word32_t a = LO(S[0]), b = HI(S[0]), c = LO(S[1]), e = LO(S[2]), f = HI(S[2]), g = LO(S[3]);
    lane_t u[16];
    u[0] = pk(LO(S[16]), a); u[1] = pk(b, c); u[2] = pk(LO(S[17]), e); u[3] = pk(f, g);
    for (int k = 0; k < 7; k++) {
#pragma HLS UNROLL
        u[4+k] = pk(HI(S[4+k]), LO(S[5+k]));
    }
    u[11] = pk(HI(S[11]), LO(S[18]));
    for (int i = 12; i < 16; i++) {
#pragma HLS UNROLL
        u[i] = S[i];
    }
    for (int i = 0; i < 4; i++) {
#pragma HLS UNROLL
        lane_t hs = add2(S[12+i], S[i]);
        M[i] = ff ? hs : u[i];
        M[12+i] = ff ? hs : u[12+i];
    }
    for (int i = 4; i < 12; i++) {
#pragma HLS UNROLL
        M[i] = ff ? S[i] : u[i];
    }
}

static inline void cc_l1_ops(const lane_t S[], word32_t EA[], word32_t EB[]) {
#pragma HLS INLINE
    EA[0] = LO(S[0]); EB[0] = LO(S[1]); EA[1] = HI(S[0]); EB[1] = HI(S[1]);
    EA[2] = LO(S[4]); EB[2] = LO(S[5]); EA[3] = HI(S[4]); EB[3] = HI(S[5]);
}
static inline void cc_l1_fin(const lane_t S[], ap_uint<9> r, const word32_t Y[], lane_t M[]) {
#pragma HLS INLINE
    bool ff = (r == 20);
    for (int i = 0; i < 16; i++) {
#pragma HLS UNROLL
        M[i] = S[i];
    }
    if (!ff) { M[0] = pk(Y[0], Y[1]); M[4] = pk(Y[2], Y[3]); }
}
static inline void cc_l3_ops(const lane_t S[], word32_t EA[], word32_t EB[]) {
#pragma HLS INLINE
    EA[0] = LO(S[2]); EB[0] = LO(S[3]); EA[1] = HI(S[2]); EB[1] = HI(S[3]);
    EA[2] = LO(S[6]); EB[2] = LO(S[7]);
}
static inline void cc_l3_fin(const lane_t S[], ap_uint<9> r, const word32_t Y[], lane_t M[]) {
#pragma HLS INLINE
    bool ff = (r == 20);
    for (int i = 0; i < 16; i++) {
#pragma HLS UNROLL
        M[i] = S[i];
    }
    if (!ff) { M[2] = pk(Y[0], Y[1]); M[6] = pk(Y[2], (word32_t)(HI(S[6]) + HI(S[7]))); }
}
template<int RA> static inline void cc_add(const lane_t S[], ap_uint<9> r, lane_t M[]) {
#pragma HLS INLINE
    bool ff = (r == 20);
    for (int i = 0; i < 16; i++) {
#pragma HLS UNROLL
        M[i] = S[i];
    }
    if (!ff) { M[RA] = add2(S[RA], S[RA + 1]); M[RA + 4] = add2(S[RA + 4], S[RA + 5]); }
}
template<int RA> static inline void cc_d(const lane_t S[], ap_uint<9> r, lane_t M[]) {
#pragma HLS INLINE
    bool ff = (r == 20);
    for (int i = 0; i < 16; i++) {
#pragma HLS UNROLL
        M[i] = S[i];
    }
    if (!ff) { M[3] = rotl2x32<RA>(S[3] ^ S[0]); M[7] = rotl2x32<RA>(S[7] ^ S[4]); }
}
template<int RA> static inline void cc_b(const lane_t S[], ap_uint<9> r, lane_t M[]) {
#pragma HLS INLINE
    bool ff = (r == 20);
    for (int i = 0; i < 16; i++) {
#pragma HLS UNROLL
        M[i] = S[i];
    }
    if (!ff) { M[1] = rotl2x32<RA>(S[1] ^ S[2]); M[5] = rotl2x32<RA>(S[5] ^ S[6]); }
}
static inline void cc_l8(const lane_t S[], ap_uint<9> r, lane_t M[]) {
#pragma HLS INLINE
    bool diag = r[0], ff = (r == 20);
    lane_t a1 = S[0], c1 = S[2], d1 = S[3], a2 = S[4], c2 = S[6], d2 = S[7];
    lane_t b1 = rotl2x32<7>(S[1] ^ S[2]), b2 = rotl2x32<7>(S[5] ^ S[6]);
    lane_t o[8];
    o[0] = a1; o[4] = a2; o[2] = c2; o[6] = c1;
    if (!diag) {
        o[1] = pk(HI(b1), LO(b2)); o[5] = pk(HI(b2), LO(b1));
        o[3] = pk(HI(d2), LO(d1)); o[7] = pk(HI(d1), LO(d2));
    } else {
        o[1] = pk(HI(b2), LO(b1)); o[5] = pk(HI(b1), LO(b2));
        o[3] = pk(HI(d1), LO(d2)); o[7] = pk(HI(d2), LO(d1));
    }
    for (int i = 0; i < 8; i++) {
#pragma HLS UNROLL
        M[i] = ff ? add2(S[i], S[8+i]) : o[i];
        M[8+i] = S[8+i];
    }
}
#define CC_COLUMN_ORDER 1

#define AB AES_B
#define AC ((AES_B + 1) / 2)
#define AT(k,j) (2*(k)+(j))
#define AKL(k,j) (2*AB + 2*(k)+(j))
#define APT(k,j) (4*AB + 2*(k)+(j))
#define ASW(k) (6*AB + (k)/2)
#define AX1(k,j) (6*AB + AC + 2*(k)+(j))
#define AKT(k,j) (8*AB + AC + 2*(k)+(j))
#define AX2(k,j) (10*AB + AC + 2*(k)+(j))
#define A_NL (12*AB + AC)
static inline lane_t xtime8(lane_t v) {
#pragma HLS INLINE
    lane_t xt;
    for (int i = 0; i < 8; i++) {
#pragma HLS UNROLL
        byte_t b = v.range(8*i+7, 8*i);
        byte_t sh = (byte_t)(b << 1);
        xt.range(8*i+7, 8*i) = b[7] ? (byte_t)(sh ^ 0x1B) : sh;
    }
    return xt;
}
static inline void aes_l1(const lane_t S[], ap_uint<9> r, lane_t M[]) {
#pragma HLS INLINE
    bool dm = (r == 11), r0 = (r == 0);
    for (int k = 0; k < AC; k++) {
#pragma HLS UNROLL
        M[6*AB + k] = 0;
    }
    for (int k = 0; k < AB; k++) {
#pragma HLS UNROLL
        byte_t st[16], t[16];
        for (int i = 0; i < 16; i++) {
#pragma HLS UNROLL
            st[i] = S[AT(k, i>>3)].range(8*(i&7)+7, 8*(i&7));
        }
        word32_t w3 = HI(S[AKL(k,1)]);
        word32_t sw;
#ifdef SBOX_BITSLICED
        byte_t g[20], o[20];
        for (int c = 0; c < 4; c++) {
#pragma HLS UNROLL
            for (int rr = 0; rr < 4; rr++) {
#pragma HLS UNROLL
                g[4*c+rr] = st[4*((c+rr)&3)+rr];
            }
        }
        g[16] = w3.range(15, 8); g[17] = w3.range(23, 16); g[18] = w3.range(31, 24); g[19] = w3.range(7, 0);
        sbox_bytes<20>(g, o);
        for (int i = 0; i < 16; i++) {
#pragma HLS UNROLL
            t[i] = o[i];
        }
        sw.range(7, 0) = o[16]; sw.range(15, 8) = o[17]; sw.range(23, 16) = o[18]; sw.range(31, 24) = o[19];
#else
        for (int c = 0; c < 4; c++) {
#pragma HLS UNROLL
            for (int rr = 0; rr < 4; rr++) {
#pragma HLS UNROLL
                t[4*c+rr] = sbox(st[4*((c+rr)&3)+rr]);
            }
        }
        sw.range(7, 0)   = sbox(w3.range(15, 8));
        sw.range(15, 8)  = sbox(w3.range(23, 16));
        sw.range(23, 16) = sbox(w3.range(31, 24));
        sw.range(31, 24) = sbox(w3.range(7, 0));
#endif
        for (int j = 0; j < 2; j++) {
#pragma HLS UNROLL
            lane_t T;
            for (int i = 0; i < 8; i++) {
#pragma HLS UNROLL
                T.range(8*i+7, 8*i) = t[8*j+i];
            }
            M[AT(k,j)] = dm ? (lane_t)(S[AT(k,j)] ^ S[APT(k,j)]) : r0 ? S[AT(k,j)] : T;
            M[AKL(k,j)] = S[AKL(k,j)];
            M[APT(k,j)] = S[APT(k,j)];
        }
        if (k & 1) M[ASW(k)].range(63, 32) = sw; else M[ASW(k)].range(31, 0) = sw;
    }
}
static inline void aes_l2(const lane_t S[], ap_uint<9> r, lane_t M[]) {
#pragma HLS INLINE
#pragma HLS BIND_STORAGE variable=RCON type=rom_1p impl=lutram
    ap_uint<4> ri = r.range(3, 0) + 1;
    for (int k = 0; k < AB; k++) {
#pragma HLS UNROLL
        for (int j = 0; j < 2; j++) {
#pragma HLS UNROLL
            M[AT(k,j)] = S[AT(k,j)]; M[AKL(k,j)] = S[AKL(k,j)]; M[APT(k,j)] = S[APT(k,j)];
            M[AX1(k,j)] = S[AT(k,j)] ^ rotcol8<1>(S[AT(k,j)]);
        }
        word32_t sw = (k & 1) ? HI(S[ASW(k)]) : LO(S[ASW(k)]);
        word32_t tt = sw ^ (word32_t)RCON[ri];
        M[AKT(k,0)] = S[AKL(k,0)] ^ pk(tt, 0);
    }
}
static inline void aes_l3(const lane_t S[], lane_t M[]) {
#pragma HLS INLINE
    for (int k = 0; k < AB; k++) {
#pragma HLS UNROLL
        for (int j = 0; j < 2; j++) {
#pragma HLS UNROLL
            M[AT(k,j)] = S[AT(k,j)]; M[AKL(k,j)] = S[AKL(k,j)]; M[APT(k,j)] = S[APT(k,j)]; M[AX1(k,j)] = S[AX1(k,j)];
            M[AX2(k,j)] = S[AX1(k,j)] ^ rotcol8<2>(S[AT(k,j)]) ^ rotcol8<3>(S[AT(k,j)]);
        }
        M[AKT(k,0)] = S[AKT(k,0)] ^ pk(0, LO(S[AKT(k,0)]));
    }
}
static inline void aes_l4(const lane_t S[], lane_t M[]) {
#pragma HLS INLINE
    for (int k = 0; k < AB; k++) {
#pragma HLS UNROLL
        for (int j = 0; j < 2; j++) {
#pragma HLS UNROLL
            M[AT(k,j)] = S[AT(k,j)]; M[AKL(k,j)] = S[AKL(k,j)]; M[APT(k,j)] = S[APT(k,j)];
            M[AX1(k,j)] = xtime8(S[AX1(k,j)]);
            M[AX2(k,j)] = S[AT(k,j)] ^ S[AX2(k,j)];
        }
        M[AKT(k,0)] = S[AKT(k,0)];
        M[AKT(k,1)] = S[AKL(k,1)] ^ pk(HI(S[AKT(k,0)]), 0);
    }
}
static inline void aes_l5(const lane_t S[], ap_uint<9> r, lane_t M[]) {
#pragma HLS INLINE
    bool keep = (r == 0) || (r == 10) || (r == 11);
    for (int k = 0; k < AB; k++) {
#pragma HLS UNROLL
        for (int j = 0; j < 2; j++) {
#pragma HLS UNROLL
            M[AT(k,j)] = keep ? S[AT(k,j)] : (lane_t)(S[AX2(k,j)] ^ S[AX1(k,j)]);
            M[AKL(k,j)] = S[AKL(k,j)]; M[APT(k,j)] = S[APT(k,j)];
        }
        M[AKT(k,0)] = S[AKT(k,0)];
        M[AKT(k,1)] = S[AKT(k,1)] ^ pk(0, LO(S[AKT(k,1)]));
    }
}
static inline void aes_l6(const lane_t S[], ap_uint<9> r, lane_t M[]) {
#pragma HLS INLINE
    bool dm = (r == 11);
    for (int k = 0; k < AB; k++) {
#pragma HLS UNROLL
        for (int j = 0; j < 2; j++) {
#pragma HLS UNROLL
            M[AT(k,j)] = dm ? S[AT(k,j)] : (lane_t)(S[AT(k,j)] ^ S[AKL(k,j)]);
            M[AKL(k,j)] = dm ? S[AKL(k,j)] : S[AKT(k,j)];
            M[APT(k,j)] = S[APT(k,j)];
        }
    }
}
#endif
