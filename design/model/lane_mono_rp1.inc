#define MONO_NA 28
#define MONO_NB 20
#define MONO_NC 18
#define MONO_ND 16
#define MONO_NISS 220
#define MONO_NE1 4
#define MONO_NE2 5
#define MONO_NE3 3
#define MONO_NE4 2
static const ap_uint<8> MONO_DEC[220] = {5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,21,133,69,69,69,69,69,69,69,69,69,69,69,69,69,69,69,69,37,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,16,133,69,69,69,69,69,69,69,69,69,69,69,69,69,69,69,69,37,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,17,133,69,69,69,69,69,69,69,69,69,69,69,69,69,69,69,69,37,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,18,133,69,69,69,69,69,69,69,69,69,69,69,69,69,69,69,69,37,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,19,133,69,69,69,69,69,69,69,69,69,69,69,69,69,69,69,69,37,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,20,133,69,69,69,69,69,69,69,69,69,69,69,69,69,69,69,69,37,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,21};

template<int W> static inline ap_uint<W> bar_chunk(ap_uint<W> x) {
#pragma HLS INLINE
    ap_uint<W> nx = ~x;
    ap_uint<W> r1 = (nx << 1) | (nx >> (W - 1));
    ap_uint<W> r2 = (x << 2) | (x >> (W - 2));
    ap_uint<W> r3 = (x << 3) | (x >> (W - 3));
    ap_uint<W> t = x ^ (W == 7 ? (ap_uint<W>)(r1 & r2) : (ap_uint<W>)(r1 & r2 & r3));
    return (t << 1) | (t >> (W - 1));
}
static inline word32_t bar31(word32_t x) {
#pragma HLS INLINE
    word32_t y = 0;
    y.range(7, 0)   = bar_chunk<8>(x.range(7, 0));
    y.range(15, 8)  = bar_chunk<8>(x.range(15, 8));
    y.range(23, 16) = bar_chunk<8>(x.range(23, 16));
    y.range(30, 24) = bar_chunk<7>(x.range(30, 24));
    return y;
}
static inline void sq_terms(word32_t x, ap_uint<31> t[47]) {
#pragma HLS INLINE
    ap_uint<16> xl = x.range(15, 0);
    ap_uint<15> xh = x.range(30, 16);
    for (int i = 0; i < 16; i++) {
#pragma HLS UNROLL
        ap_uint<31> a = (ap_uint<31>)xl << i;
        t[i] = xl[i] ? a : (ap_uint<31>)0;
    }
    for (int i = 0; i < 15; i++) {
#pragma HLS UNROLL
        ap_uint<31> a = (ap_uint<31>)xh << i;
        ap_uint<31> r = (a << 1) | (a >> 30);
        t[16 + i] = xh[i] ? r : (ap_uint<31>)0;
    }
    for (int i = 0; i < 16; i++) {
#pragma HLS UNROLL
        ap_uint<31> a = (ap_uint<31>)xh << i;
        ap_uint<31> r = (a << 17) | (a >> 14);
        t[31 + i] = xl[i] ? r : (ap_uint<31>)0;
    }
}
static inline void mono_s1(const lane_t S[25], ap_uint<8> dec, lane_t M[MONO_NA], bool ext, const word32_t EA[], const word32_t EB[], word32_t EY[]) {
#pragma HLS INLINE
    bool bars = dec[7], sq = dec[6];
    word32_t X[16];
    for (int i = 0; i < 8; i++) {
#pragma HLS UNROLL
        X[2*i] = S[i].range(31, 0); X[2*i+1] = S[i].range(63, 32); }
    for (int l = 0; l < MONO_NA; l++) {
#pragma HLS UNROLL
        M[l] = (l < 16) ? S[l] : (lane_t)0; }
    (void)bars;
    ap_uint<31> q0[47];
    sq_terms(X[0], q0);
    ap_uint<31> t0_0 = sq ? q0[0] : (ap_uint<31>)m31_mul2exp<1>(X[0]);
    ap_uint<31> t0_1 = sq ? q0[1] : (ap_uint<31>)(m31_mul2exp<3>(X[0]) ^ P_M31);
    ap_uint<31> t0_2 = sq ? q0[2] : (ap_uint<31>)(m31_mul2exp<5>(X[0]) ^ P_M31);
    ap_uint<31> t0_3 = sq ? q0[3] : (ap_uint<31>)(m31_mul2exp<12>(X[0]) ^ P_M31);
    ap_uint<31> t0_4 = sq ? q0[4] : (ap_uint<31>)m31_mul2exp<16>(X[0]);
    ap_uint<31> t0_5 = sq ? q0[5] : (ap_uint<31>)m31_mul2exp<0>(X[1]);
    ap_uint<31> t0_6 = sq ? q0[6] : (ap_uint<31>)m31_mul2exp<2>(X[1]);
    ap_uint<31> t0_7 = sq ? q0[7] : (ap_uint<31>)(m31_mul2exp<4>(X[1]) ^ P_M31);
    ap_uint<31> t0_8 = sq ? q0[8] : (ap_uint<31>)(m31_mul2exp<6>(X[1]) ^ P_M31);
    ap_uint<31> t0_9 = sq ? q0[9] : (ap_uint<31>)(m31_mul2exp<9>(X[1]) ^ P_M31);
    ap_uint<31> t0_10 = sq ? q0[10] : (ap_uint<31>)m31_mul2exp<11>(X[1]);
    ap_uint<31> t0_11 = sq ? q0[11] : (ap_uint<31>)m31_mul2exp<14>(X[1]);
    ap_uint<31> t0_12 = sq ? q0[12] : (ap_uint<31>)(m31_mul2exp<1>(X[2]) ^ P_M31);
    ap_uint<31> t0_13 = sq ? q0[13] : (ap_uint<31>)(m31_mul2exp<4>(X[2]) ^ P_M31);
    ap_uint<31> t0_14 = sq ? q0[14] : (ap_uint<31>)(m31_mul2exp<6>(X[2]) ^ P_M31);
    ap_uint<31> t0_15 = sq ? q0[15] : (ap_uint<31>)m31_mul2exp<8>(X[2]);
    ap_uint<31> t0_16 = sq ? q0[16] : (ap_uint<31>)m31_mul2exp<11>(X[2]);
    ap_uint<31> t0_17 = sq ? q0[17] : (ap_uint<31>)(m31_mul2exp<13>(X[2]) ^ P_M31);
    ap_uint<31> t0_18 = sq ? q0[18] : (ap_uint<31>)m31_mul2exp<15>(X[2]);
    ap_uint<31> t0_19 = sq ? q0[19] : (ap_uint<31>)m31_mul2exp<0>(X[3]);
    ap_uint<31> t0_20 = sq ? q0[20] : (ap_uint<31>)m31_mul2exp<3>(X[3]);
    ap_uint<31> t0_21 = sq ? q0[21] : (ap_uint<31>)m31_mul2exp<5>(X[3]);
    ap_uint<31> t0_22 = sq ? q0[22] : (ap_uint<31>)m31_mul2exp<8>(X[3]);
    ap_uint<31> t0_23 = sq ? q0[23] : (ap_uint<31>)m31_mul2exp<11>(X[3]);
    ap_uint<31> t0_24 = sq ? q0[24] : (ap_uint<31>)(m31_mul2exp<13>(X[3]) ^ P_M31);
    ap_uint<31> t0_25 = sq ? q0[25] : (ap_uint<31>)m31_mul2exp<16>(X[3]);
    ap_uint<31> t0_26 = sq ? q0[26] : (ap_uint<31>)m31_mul2exp<0>(X[4]);
    ap_uint<31> t0_27 = sq ? q0[27] : (ap_uint<31>)m31_mul2exp<2>(X[4]);
    ap_uint<31> t0_28 = sq ? q0[28] : (ap_uint<31>)(m31_mul2exp<4>(X[4]) ^ P_M31);
    ap_uint<31> t0_29 = sq ? q0[29] : (ap_uint<31>)(m31_mul2exp<8>(X[4]) ^ P_M31);
    ap_uint<31> t0_30 = sq ? q0[30] : (ap_uint<31>)(m31_mul2exp<12>(X[4]) ^ P_M31);
    ap_uint<31> t0_31 = sq ? q0[31] : (ap_uint<31>)m31_mul2exp<14>(X[4]);
    ap_uint<31> t0_32 = sq ? q0[32] : (ap_uint<31>)m31_mul2exp<0>(X[5]);
    ap_uint<31> t0_33 = sq ? q0[33] : (ap_uint<31>)m31_mul2exp<2>(X[5]);
    ap_uint<31> t0_34 = sq ? q0[34] : (ap_uint<31>)(m31_mul2exp<6>(X[5]) ^ P_M31);
    ap_uint<31> t0_35 = sq ? q0[35] : (ap_uint<31>)m31_mul2exp<13>(X[5]);
    ap_uint<31> t0_36 = sq ? q0[36] : (ap_uint<31>)m31_mul2exp<15>(X[5]);
    ap_uint<31> t0_37 = sq ? q0[37] : (ap_uint<31>)(m31_mul2exp<0>(X[6]) ^ P_M31);
    ap_uint<31> t0_38 = sq ? q0[38] : (ap_uint<31>)m31_mul2exp<3>(X[6]);
    ap_uint<31> t0_39 = sq ? q0[39] : (ap_uint<31>)(m31_mul2exp<7>(X[6]) ^ P_M31);
    ap_uint<31> t0_40 = sq ? q0[40] : (ap_uint<31>)m31_mul2exp<9>(X[6]);
    ap_uint<31> t0_41 = sq ? q0[41] : (ap_uint<31>)m31_mul2exp<13>(X[6]);
    ap_uint<31> t0_42 = sq ? q0[42] : (ap_uint<31>)m31_mul2exp<15>(X[6]);
    ap_uint<31> t0_43 = sq ? q0[43] : (ap_uint<31>)m31_mul2exp<0>(X[7]);
    ap_uint<31> t0_44 = sq ? q0[44] : (ap_uint<31>)(m31_mul2exp<7>(X[7]) ^ P_M31);
    ap_uint<31> t0_45 = sq ? q0[45] : (ap_uint<31>)(m31_mul2exp<10>(X[7]) ^ P_M31);
    ap_uint<31> t0_46 = sq ? q0[46] : (ap_uint<31>)(m31_mul2exp<12>(X[7]) ^ P_M31);
    ap_uint<31> t0_47 = sq ? (ap_uint<31>)0 : (ap_uint<31>)m31_mul2exp<15>(X[7]);
    ap_uint<31> t0_48 = sq ? (ap_uint<31>)0 : (ap_uint<31>)(m31_mul2exp<0>(X[8]) ^ P_M31);
    ap_uint<31> t0_49 = sq ? (ap_uint<31>)0 : (ap_uint<31>)(m31_mul2exp<3>(X[8]) ^ P_M31);
    ap_uint<31> t0_50 = sq ? (ap_uint<31>)0 : (ap_uint<31>)m31_mul2exp<7>(X[8]);
    ap_uint<31> t0_51 = sq ? (ap_uint<31>)0 : (ap_uint<31>)(m31_mul2exp<9>(X[8]) ^ P_M31);
    ap_uint<31> t0_52 = sq ? (ap_uint<31>)0 : (ap_uint<31>)(m31_mul2exp<13>(X[8]) ^ P_M31);
    ap_uint<31> t0_53 = sq ? (ap_uint<31>)0 : (ap_uint<31>)m31_mul2exp<16>(X[8]);
    ap_uint<31> t0_54 = sq ? (ap_uint<31>)0 : (ap_uint<31>)m31_mul2exp<1>(X[9]);
    ap_uint<31> t0_55 = sq ? (ap_uint<31>)0 : (ap_uint<31>)(m31_mul2exp<8>(X[9]) ^ P_M31);
    ap_uint<31> t0_56 = sq ? (ap_uint<31>)0 : (ap_uint<31>)(m31_mul2exp<12>(X[9]) ^ P_M31);
    ap_uint<31> t0_57 = sq ? (ap_uint<31>)0 : (ap_uint<31>)m31_mul2exp<14>(X[9]);
    ap_uint<31> t0_58 = sq ? (ap_uint<31>)0 : (ap_uint<31>)m31_mul2exp<0>(X[10]);
    ap_uint<31> t0_59 = sq ? (ap_uint<31>)0 : (ap_uint<31>)m31_mul2exp<3>(X[10]);
    ap_uint<31> t0_60 = sq ? (ap_uint<31>)0 : (ap_uint<31>)(m31_mul2exp<5>(X[10]) ^ P_M31);
    ap_uint<31> t0_61 = sq ? (ap_uint<31>)0 : (ap_uint<31>)m31_mul2exp<7>(X[10]);
    ap_uint<31> t0_62 = sq ? (ap_uint<31>)0 : (ap_uint<31>)m31_mul2exp<9>(X[10]);
    ap_uint<31> t0_63 = sq ? (ap_uint<31>)0 : (ap_uint<31>)m31_mul2exp<12>(X[10]);
    ap_uint<31> t0_64 = sq ? (ap_uint<31>)0 : (ap_uint<31>)(m31_mul2exp<14>(X[10]) ^ P_M31);
    ap_uint<31> t0_65 = sq ? (ap_uint<31>)0 : (ap_uint<31>)m31_mul2exp<16>(X[10]);
    ap_uint<31> t0_66 = sq ? (ap_uint<31>)0 : (ap_uint<31>)(m31_mul2exp<2>(X[11]) ^ P_M31);
    ap_uint<31> t0_67 = sq ? (ap_uint<31>)0 : (ap_uint<31>)(m31_mul2exp<4>(X[11]) ^ P_M31);
    ap_uint<31> t0_68 = sq ? (ap_uint<31>)0 : (ap_uint<31>)m31_mul2exp<8>(X[11]);
    ap_uint<31> t0_69 = sq ? (ap_uint<31>)0 : (ap_uint<31>)m31_mul2exp<11>(X[11]);
    ap_uint<31> t0_70 = sq ? (ap_uint<31>)0 : (ap_uint<31>)m31_mul2exp<13>(X[11]);
    ap_uint<31> t0_71 = sq ? (ap_uint<31>)0 : (ap_uint<31>)m31_mul2exp<15>(X[11]);
    ap_uint<31> t0_72 = sq ? (ap_uint<31>)0 : (ap_uint<31>)(m31_mul2exp<1>(X[12]) ^ P_M31);
    ap_uint<31> t0_73 = sq ? (ap_uint<31>)0 : (ap_uint<31>)m31_mul2exp<5>(X[12]);
    ap_uint<31> t0_74 = sq ? (ap_uint<31>)0 : (ap_uint<31>)m31_mul2exp<8>(X[12]);
    ap_uint<31> t0_75 = sq ? (ap_uint<31>)0 : (ap_uint<31>)(m31_mul2exp<10>(X[12]) ^ P_M31);
    ap_uint<31> t0_76 = sq ? (ap_uint<31>)0 : (ap_uint<31>)m31_mul2exp<13>(X[12]);
    ap_uint<31> t0_77 = sq ? (ap_uint<31>)0 : (ap_uint<31>)(m31_mul2exp<0>(X[13]) ^ P_M31);
    ap_uint<31> t0_78 = sq ? (ap_uint<31>)0 : (ap_uint<31>)m31_mul2exp<5>(X[13]);
    ap_uint<31> t0_79 = sq ? (ap_uint<31>)0 : (ap_uint<31>)m31_mul2exp<10>(X[13]);
    ap_uint<31> t0_80 = sq ? (ap_uint<31>)0 : (ap_uint<31>)m31_mul2exp<15>(X[13]);
    ap_uint<31> t0_81 = sq ? (ap_uint<31>)0 : (ap_uint<31>)(m31_mul2exp<1>(X[14]) ^ P_M31);
    ap_uint<31> t0_82 = sq ? (ap_uint<31>)0 : (ap_uint<31>)m31_mul2exp<4>(X[14]);
    ap_uint<31> t0_83 = sq ? (ap_uint<31>)0 : (ap_uint<31>)m31_mul2exp<6>(X[14]);
    ap_uint<31> t0_84 = sq ? (ap_uint<31>)0 : (ap_uint<31>)(m31_mul2exp<12>(X[14]) ^ P_M31);
    ap_uint<31> t0_85 = sq ? (ap_uint<31>)0 : (ap_uint<31>)m31_mul2exp<15>(X[14]);
    ap_uint<31> t0_86 = sq ? (ap_uint<31>)0 : (ap_uint<31>)m31_mul2exp<2>(X[15]);
    ap_uint<31> t0_87 = sq ? (ap_uint<31>)0 : (ap_uint<31>)m31_mul2exp<4>(X[15]);
    ap_uint<31> t0_88 = sq ? (ap_uint<31>)0 : (ap_uint<31>)m31_mul2exp<6>(X[15]);
    ap_uint<31> t0_89 = sq ? (ap_uint<31>)0 : (ap_uint<31>)m31_mul2exp<10>(X[15]);
    ap_uint<32> s1o0_0_0a = ext ? (ap_uint<32>)EA[0] : (ap_uint<32>)t0_0;
    ap_uint<32> s1o0_0_0b = ext ? (ap_uint<32>)EB[0] : (ap_uint<32>)t0_1;
    ap_uint<32> s1o0_0_0 = s1o0_0_0a + s1o0_0_0b;
    EY[0] = s1o0_0_0.range(31, 0);
    ap_uint<32> s1o0_0_1a = ext ? (ap_uint<32>)EA[1] : (ap_uint<32>)t0_2;
    ap_uint<32> s1o0_0_1b = ext ? (ap_uint<32>)EB[1] : (ap_uint<32>)t0_3;
    ap_uint<32> s1o0_0_1 = s1o0_0_1a + s1o0_0_1b;
    EY[1] = s1o0_0_1.range(31, 0);
    ap_uint<32> s1o0_0_2a = ext ? (ap_uint<32>)EA[2] : (ap_uint<32>)t0_4;
    ap_uint<32> s1o0_0_2b = ext ? (ap_uint<32>)EB[2] : (ap_uint<32>)t0_5;
    ap_uint<32> s1o0_0_2 = s1o0_0_2a + s1o0_0_2b;
    EY[2] = s1o0_0_2.range(31, 0);
    ap_uint<32> s1o0_0_3a = ext ? (ap_uint<32>)EA[3] : (ap_uint<32>)t0_6;
    ap_uint<32> s1o0_0_3b = ext ? (ap_uint<32>)EB[3] : (ap_uint<32>)t0_7;
    ap_uint<32> s1o0_0_3 = s1o0_0_3a + s1o0_0_3b;
    EY[3] = s1o0_0_3.range(31, 0);
    ap_uint<32> s1o0_0_4 = (ap_uint<32>)t0_8 + (ap_uint<32>)t0_9;
    ap_uint<32> s1o0_0_5 = (ap_uint<32>)t0_10 + (ap_uint<32>)t0_11;
    ap_uint<32> s1o0_0_6 = (ap_uint<32>)t0_12 + (ap_uint<32>)t0_13;
    ap_uint<32> s1o0_0_7 = (ap_uint<32>)t0_14 + (ap_uint<32>)t0_15;
    ap_uint<32> s1o0_0_8 = (ap_uint<32>)t0_16 + (ap_uint<32>)t0_17;
    ap_uint<32> s1o0_0_9 = (ap_uint<32>)t0_18 + (ap_uint<32>)t0_19;
    ap_uint<32> s1o0_0_10 = (ap_uint<32>)t0_20 + (ap_uint<32>)t0_21;
    ap_uint<32> s1o0_0_11 = (ap_uint<32>)t0_22 + (ap_uint<32>)t0_23;
    ap_uint<32> s1o0_0_12 = (ap_uint<32>)t0_24 + (ap_uint<32>)t0_25;
    ap_uint<32> s1o0_0_13 = (ap_uint<32>)t0_26 + (ap_uint<32>)t0_27;
    ap_uint<32> s1o0_0_14 = (ap_uint<32>)t0_28 + (ap_uint<32>)t0_29;
    ap_uint<32> s1o0_0_15 = (ap_uint<32>)t0_30 + (ap_uint<32>)t0_31;
    ap_uint<32> s1o0_0_16 = (ap_uint<32>)t0_32 + (ap_uint<32>)t0_33;
    ap_uint<32> s1o0_0_17 = (ap_uint<32>)t0_34 + (ap_uint<32>)t0_35;
    ap_uint<32> s1o0_0_18 = (ap_uint<32>)t0_36 + (ap_uint<32>)t0_37;
    ap_uint<32> s1o0_0_19 = (ap_uint<32>)t0_38 + (ap_uint<32>)t0_39;
    ap_uint<32> s1o0_0_20 = (ap_uint<32>)t0_40 + (ap_uint<32>)t0_41;
    ap_uint<32> s1o0_0_21 = (ap_uint<32>)t0_42 + (ap_uint<32>)t0_43;
    ap_uint<32> s1o0_0_22 = (ap_uint<32>)t0_44 + (ap_uint<32>)t0_45;
    ap_uint<32> s1o0_0_23 = (ap_uint<32>)t0_46 + (ap_uint<32>)t0_47;
    ap_uint<32> s1o0_0_24 = (ap_uint<32>)t0_48 + (ap_uint<32>)t0_49;
    ap_uint<32> s1o0_0_25 = (ap_uint<32>)t0_50 + (ap_uint<32>)t0_51;
    ap_uint<32> s1o0_0_26 = (ap_uint<32>)t0_52 + (ap_uint<32>)t0_53;
    ap_uint<32> s1o0_0_27 = (ap_uint<32>)t0_54 + (ap_uint<32>)t0_55;
    ap_uint<32> s1o0_0_28 = (ap_uint<32>)t0_56 + (ap_uint<32>)t0_57;
    ap_uint<32> s1o0_0_29 = (ap_uint<32>)t0_58 + (ap_uint<32>)t0_59;
    ap_uint<32> s1o0_0_30 = (ap_uint<32>)t0_60 + (ap_uint<32>)t0_61;
    ap_uint<32> s1o0_0_31 = (ap_uint<32>)t0_62 + (ap_uint<32>)t0_63;
    ap_uint<32> s1o0_0_32 = (ap_uint<32>)t0_64 + (ap_uint<32>)t0_65;
    ap_uint<32> s1o0_0_33 = (ap_uint<32>)t0_66 + (ap_uint<32>)t0_67;
    ap_uint<32> s1o0_0_34 = (ap_uint<32>)t0_68 + (ap_uint<32>)t0_69;
    ap_uint<32> s1o0_0_35 = (ap_uint<32>)t0_70 + (ap_uint<32>)t0_71;
    ap_uint<32> s1o0_0_36 = (ap_uint<32>)t0_72 + (ap_uint<32>)t0_73;
    ap_uint<32> s1o0_0_37 = (ap_uint<32>)t0_74 + (ap_uint<32>)t0_75;
    ap_uint<32> s1o0_0_38 = (ap_uint<32>)t0_76 + (ap_uint<32>)t0_77;
    ap_uint<32> s1o0_0_39 = (ap_uint<32>)t0_78 + (ap_uint<32>)t0_79;
    ap_uint<32> s1o0_0_40 = (ap_uint<32>)t0_80 + (ap_uint<32>)t0_81;
    ap_uint<32> s1o0_0_41 = (ap_uint<32>)t0_82 + (ap_uint<32>)t0_83;
    ap_uint<32> s1o0_0_42 = (ap_uint<32>)t0_84 + (ap_uint<32>)t0_85;
    ap_uint<32> s1o0_0_43 = (ap_uint<32>)t0_86 + (ap_uint<32>)t0_87;
    ap_uint<32> s1o0_0_44 = (ap_uint<32>)t0_88 + (ap_uint<32>)t0_89;
    ap_uint<33> s1o0_1_0 = (ap_uint<33>)s1o0_0_0 + (ap_uint<33>)s1o0_0_1;
    ap_uint<33> s1o0_1_1 = (ap_uint<33>)s1o0_0_2 + (ap_uint<33>)s1o0_0_3;
    ap_uint<33> s1o0_1_2 = (ap_uint<33>)s1o0_0_4 + (ap_uint<33>)s1o0_0_5;
    ap_uint<33> s1o0_1_3 = (ap_uint<33>)s1o0_0_6 + (ap_uint<33>)s1o0_0_7;
    ap_uint<33> s1o0_1_4 = (ap_uint<33>)s1o0_0_8 + (ap_uint<33>)s1o0_0_9;
    ap_uint<33> s1o0_1_5 = (ap_uint<33>)s1o0_0_10 + (ap_uint<33>)s1o0_0_11;
    ap_uint<33> s1o0_1_6 = (ap_uint<33>)s1o0_0_12 + (ap_uint<33>)s1o0_0_13;
    ap_uint<33> s1o0_1_7 = (ap_uint<33>)s1o0_0_14 + (ap_uint<33>)s1o0_0_15;
    ap_uint<33> s1o0_1_8 = (ap_uint<33>)s1o0_0_16 + (ap_uint<33>)s1o0_0_17;
    ap_uint<33> s1o0_1_9 = (ap_uint<33>)s1o0_0_18 + (ap_uint<33>)s1o0_0_19;
    ap_uint<33> s1o0_1_10 = (ap_uint<33>)s1o0_0_20 + (ap_uint<33>)s1o0_0_21;
    ap_uint<33> s1o0_1_11 = (ap_uint<33>)s1o0_0_22 + (ap_uint<33>)s1o0_0_23;
    ap_uint<33> s1o0_1_12 = (ap_uint<33>)s1o0_0_24 + (ap_uint<33>)s1o0_0_25;
    ap_uint<33> s1o0_1_13 = (ap_uint<33>)s1o0_0_26 + (ap_uint<33>)s1o0_0_27;
    ap_uint<33> s1o0_1_14 = (ap_uint<33>)s1o0_0_28 + (ap_uint<33>)s1o0_0_29;
    ap_uint<33> s1o0_1_15 = (ap_uint<33>)s1o0_0_30 + (ap_uint<33>)s1o0_0_31;
    ap_uint<33> s1o0_1_16 = (ap_uint<33>)s1o0_0_32 + (ap_uint<33>)s1o0_0_33;
    ap_uint<33> s1o0_1_17 = (ap_uint<33>)s1o0_0_34 + (ap_uint<33>)s1o0_0_35;
    ap_uint<33> s1o0_1_18 = (ap_uint<33>)s1o0_0_36 + (ap_uint<33>)s1o0_0_37;
    ap_uint<33> s1o0_1_19 = (ap_uint<33>)s1o0_0_38 + (ap_uint<33>)s1o0_0_39;
    ap_uint<33> s1o0_1_20 = (ap_uint<33>)s1o0_0_40 + (ap_uint<33>)s1o0_0_41;
    ap_uint<33> s1o0_1_21 = (ap_uint<33>)s1o0_0_42 + (ap_uint<33>)s1o0_0_43;
    ap_uint<33> s1o0_1_22 = s1o0_0_44;
    M[16].range(32, 0) = s1o0_1_0.range(32, 0);
    M[16].range(63, 33) = s1o0_1_1.range(30, 0);
    M[17].range(1, 0) = s1o0_1_1.range(32, 31);
    M[17].range(34, 2) = s1o0_1_2.range(32, 0);
    M[17].range(63, 35) = s1o0_1_3.range(28, 0);
    M[18].range(3, 0) = s1o0_1_3.range(32, 29);
    M[18].range(36, 4) = s1o0_1_4.range(32, 0);
    M[18].range(63, 37) = s1o0_1_5.range(26, 0);
    M[19].range(5, 0) = s1o0_1_5.range(32, 27);
    M[19].range(38, 6) = s1o0_1_6.range(32, 0);
    M[19].range(63, 39) = s1o0_1_7.range(24, 0);
    M[20].range(7, 0) = s1o0_1_7.range(32, 25);
    M[20].range(40, 8) = s1o0_1_8.range(32, 0);
    M[20].range(63, 41) = s1o0_1_9.range(22, 0);
    M[21].range(9, 0) = s1o0_1_9.range(32, 23);
    M[21].range(42, 10) = s1o0_1_10.range(32, 0);
    M[21].range(63, 43) = s1o0_1_11.range(20, 0);
    M[22].range(11, 0) = s1o0_1_11.range(32, 21);
    M[22].range(44, 12) = s1o0_1_12.range(32, 0);
    M[22].range(63, 45) = s1o0_1_13.range(18, 0);
    M[23].range(13, 0) = s1o0_1_13.range(32, 19);
    M[23].range(46, 14) = s1o0_1_14.range(32, 0);
    M[23].range(63, 47) = s1o0_1_15.range(16, 0);
    M[24].range(15, 0) = s1o0_1_15.range(32, 17);
    M[24].range(48, 16) = s1o0_1_16.range(32, 0);
    M[24].range(63, 49) = s1o0_1_17.range(14, 0);
    M[25].range(17, 0) = s1o0_1_17.range(32, 15);
    M[25].range(50, 18) = s1o0_1_18.range(32, 0);
    M[25].range(63, 51) = s1o0_1_19.range(12, 0);
    M[26].range(19, 0) = s1o0_1_19.range(32, 13);
    M[26].range(52, 20) = s1o0_1_20.range(32, 0);
    M[26].range(63, 53) = s1o0_1_21.range(10, 0);
    M[27].range(21, 0) = s1o0_1_21.range(32, 11);
    M[27].range(54, 22) = s1o0_1_22.range(32, 0);
}
static inline void mono_s2(const lane_t A[MONO_NA], ap_uint<8> dec, lane_t M[MONO_NB], bool ext, const word32_t EA[], const word32_t EB[], word32_t EY[]) {
#pragma HLS INLINE
    for (int l = 0; l < MONO_NB; l++) {
#pragma HLS UNROLL
        M[l] = (l < 16) ? A[l] : (lane_t)0; }
    ap_uint<33> p0_0;
    p0_0.range(32, 0) = A[16].range(32, 0);
    ap_uint<33> p0_1;
    p0_1.range(30, 0) = A[16].range(63, 33);
    p0_1.range(32, 31) = A[17].range(1, 0);
    ap_uint<33> p0_2;
    p0_2.range(32, 0) = A[17].range(34, 2);
    ap_uint<33> p0_3;
    p0_3.range(28, 0) = A[17].range(63, 35);
    p0_3.range(32, 29) = A[18].range(3, 0);
    ap_uint<33> p0_4;
    p0_4.range(32, 0) = A[18].range(36, 4);
    ap_uint<33> p0_5;
    p0_5.range(26, 0) = A[18].range(63, 37);
    p0_5.range(32, 27) = A[19].range(5, 0);
    ap_uint<33> p0_6;
    p0_6.range(32, 0) = A[19].range(38, 6);
    ap_uint<33> p0_7;
    p0_7.range(24, 0) = A[19].range(63, 39);
    p0_7.range(32, 25) = A[20].range(7, 0);
    ap_uint<33> p0_8;
    p0_8.range(32, 0) = A[20].range(40, 8);
    ap_uint<33> p0_9;
    p0_9.range(22, 0) = A[20].range(63, 41);
    p0_9.range(32, 23) = A[21].range(9, 0);
    ap_uint<33> p0_10;
    p0_10.range(32, 0) = A[21].range(42, 10);
    ap_uint<33> p0_11;
    p0_11.range(20, 0) = A[21].range(63, 43);
    p0_11.range(32, 21) = A[22].range(11, 0);
    ap_uint<33> p0_12;
    p0_12.range(32, 0) = A[22].range(44, 12);
    ap_uint<33> p0_13;
    p0_13.range(18, 0) = A[22].range(63, 45);
    p0_13.range(32, 19) = A[23].range(13, 0);
    ap_uint<33> p0_14;
    p0_14.range(32, 0) = A[23].range(46, 14);
    ap_uint<33> p0_15;
    p0_15.range(16, 0) = A[23].range(63, 47);
    p0_15.range(32, 17) = A[24].range(15, 0);
    ap_uint<33> p0_16;
    p0_16.range(32, 0) = A[24].range(48, 16);
    ap_uint<33> p0_17;
    p0_17.range(14, 0) = A[24].range(63, 49);
    p0_17.range(32, 15) = A[25].range(17, 0);
    ap_uint<33> p0_18;
    p0_18.range(32, 0) = A[25].range(50, 18);
    ap_uint<33> p0_19;
    p0_19.range(12, 0) = A[25].range(63, 51);
    p0_19.range(32, 13) = A[26].range(19, 0);
    ap_uint<33> p0_20;
    p0_20.range(32, 0) = A[26].range(52, 20);
    ap_uint<33> p0_21;
    p0_21.range(10, 0) = A[26].range(63, 53);
    p0_21.range(32, 11) = A[27].range(21, 0);
    ap_uint<33> p0_22;
    p0_22.range(32, 0) = A[27].range(54, 22);
    ap_uint<34> s2o0_0_0a = ext ? (ap_uint<34>)EA[0] : (ap_uint<34>)p0_0;
    ap_uint<34> s2o0_0_0b = ext ? (ap_uint<34>)EB[0] : (ap_uint<34>)p0_1;
    ap_uint<34> s2o0_0_0 = s2o0_0_0a + s2o0_0_0b;
    EY[0] = s2o0_0_0.range(31, 0);
    ap_uint<34> s2o0_0_1a = ext ? (ap_uint<34>)EA[1] : (ap_uint<34>)p0_2;
    ap_uint<34> s2o0_0_1b = ext ? (ap_uint<34>)EB[1] : (ap_uint<34>)p0_3;
    ap_uint<34> s2o0_0_1 = s2o0_0_1a + s2o0_0_1b;
    EY[1] = s2o0_0_1.range(31, 0);
    ap_uint<34> s2o0_0_2a = ext ? (ap_uint<34>)EA[2] : (ap_uint<34>)p0_4;
    ap_uint<34> s2o0_0_2b = ext ? (ap_uint<34>)EB[2] : (ap_uint<34>)p0_5;
    ap_uint<34> s2o0_0_2 = s2o0_0_2a + s2o0_0_2b;
    EY[2] = s2o0_0_2.range(31, 0);
    ap_uint<34> s2o0_0_3a = ext ? (ap_uint<34>)EA[3] : (ap_uint<34>)p0_6;
    ap_uint<34> s2o0_0_3b = ext ? (ap_uint<34>)EB[3] : (ap_uint<34>)p0_7;
    ap_uint<34> s2o0_0_3 = s2o0_0_3a + s2o0_0_3b;
    EY[3] = s2o0_0_3.range(31, 0);
    ap_uint<34> s2o0_0_4a = ext ? (ap_uint<34>)EA[4] : (ap_uint<34>)p0_8;
    ap_uint<34> s2o0_0_4b = ext ? (ap_uint<34>)EB[4] : (ap_uint<34>)p0_9;
    ap_uint<34> s2o0_0_4 = s2o0_0_4a + s2o0_0_4b;
    EY[4] = s2o0_0_4.range(31, 0);
    ap_uint<34> s2o0_0_5 = (ap_uint<34>)p0_10 + (ap_uint<34>)p0_11;
    ap_uint<34> s2o0_0_6 = (ap_uint<34>)p0_12 + (ap_uint<34>)p0_13;
    ap_uint<34> s2o0_0_7 = (ap_uint<34>)p0_14 + (ap_uint<34>)p0_15;
    ap_uint<34> s2o0_0_8 = (ap_uint<34>)p0_16 + (ap_uint<34>)p0_17;
    ap_uint<34> s2o0_0_9 = (ap_uint<34>)p0_18 + (ap_uint<34>)p0_19;
    ap_uint<34> s2o0_0_10 = (ap_uint<34>)p0_20 + (ap_uint<34>)p0_21;
    ap_uint<34> s2o0_0_11 = p0_22;
    ap_uint<35> s2o0_1_0 = (ap_uint<35>)s2o0_0_0 + (ap_uint<35>)s2o0_0_1;
    ap_uint<35> s2o0_1_1 = (ap_uint<35>)s2o0_0_2 + (ap_uint<35>)s2o0_0_3;
    ap_uint<35> s2o0_1_2 = (ap_uint<35>)s2o0_0_4 + (ap_uint<35>)s2o0_0_5;
    ap_uint<35> s2o0_1_3 = (ap_uint<35>)s2o0_0_6 + (ap_uint<35>)s2o0_0_7;
    ap_uint<35> s2o0_1_4 = (ap_uint<35>)s2o0_0_8 + (ap_uint<35>)s2o0_0_9;
    ap_uint<35> s2o0_1_5 = (ap_uint<35>)s2o0_0_10 + (ap_uint<35>)s2o0_0_11;
    M[16].range(34, 0) = s2o0_1_0.range(34, 0);
    M[16].range(63, 35) = s2o0_1_1.range(28, 0);
    M[17].range(5, 0) = s2o0_1_1.range(34, 29);
    M[17].range(40, 6) = s2o0_1_2.range(34, 0);
    M[17].range(63, 41) = s2o0_1_3.range(22, 0);
    M[18].range(11, 0) = s2o0_1_3.range(34, 23);
    M[18].range(46, 12) = s2o0_1_4.range(34, 0);
    M[18].range(63, 47) = s2o0_1_5.range(16, 0);
    M[19].range(17, 0) = s2o0_1_5.range(34, 17);
}
static inline void mono_s3(const lane_t B[MONO_NB], ap_uint<8> dec, lane_t M[MONO_NC], bool ext, const word32_t EA[], const word32_t EB[], word32_t EY[]) {
#pragma HLS INLINE
    for (int l = 0; l < MONO_NC; l++) {
#pragma HLS UNROLL
        M[l] = (l < 16) ? B[l] : (lane_t)0; }
    ap_uint<35> p0_0;
    p0_0.range(34, 0) = B[16].range(34, 0);
    ap_uint<35> p0_1;
    p0_1.range(28, 0) = B[16].range(63, 35);
    p0_1.range(34, 29) = B[17].range(5, 0);
    ap_uint<35> p0_2;
    p0_2.range(34, 0) = B[17].range(40, 6);
    ap_uint<35> p0_3;
    p0_3.range(22, 0) = B[17].range(63, 41);
    p0_3.range(34, 23) = B[18].range(11, 0);
    ap_uint<35> p0_4;
    p0_4.range(34, 0) = B[18].range(46, 12);
    ap_uint<35> p0_5;
    p0_5.range(16, 0) = B[18].range(63, 47);
    p0_5.range(34, 17) = B[19].range(17, 0);
    ap_uint<36> s3o0_0_0a = ext ? (ap_uint<36>)EA[0] : (ap_uint<36>)p0_0;
    ap_uint<36> s3o0_0_0b = ext ? (ap_uint<36>)EB[0] : (ap_uint<36>)p0_1;
    ap_uint<36> s3o0_0_0 = s3o0_0_0a + s3o0_0_0b;
    EY[0] = s3o0_0_0.range(31, 0);
    ap_uint<36> s3o0_0_1a = ext ? (ap_uint<36>)EA[1] : (ap_uint<36>)p0_2;
    ap_uint<36> s3o0_0_1b = ext ? (ap_uint<36>)EB[1] : (ap_uint<36>)p0_3;
    ap_uint<36> s3o0_0_1 = s3o0_0_1a + s3o0_0_1b;
    EY[1] = s3o0_0_1.range(31, 0);
    ap_uint<36> s3o0_0_2a = ext ? (ap_uint<36>)EA[2] : (ap_uint<36>)p0_4;
    ap_uint<36> s3o0_0_2b = ext ? (ap_uint<36>)EB[2] : (ap_uint<36>)p0_5;
    ap_uint<36> s3o0_0_2 = s3o0_0_2a + s3o0_0_2b;
    EY[2] = s3o0_0_2.range(31, 0);
    ap_uint<37> s3o0_1_0 = (ap_uint<37>)s3o0_0_0 + (ap_uint<37>)s3o0_0_1;
    ap_uint<37> s3o0_1_1 = s3o0_0_2;
    M[16].range(36, 0) = s3o0_1_0.range(36, 0);
    M[16].range(63, 37) = s3o0_1_1.range(26, 0);
    M[17].range(9, 0) = s3o0_1_1.range(36, 27);
}
static inline void mono_s4(const lane_t C[MONO_NC], ap_uint<8> dec, lane_t M[MONO_ND], bool ext, const word32_t EA[], const word32_t EB[], word32_t EY[], const lane_t BR[]) {
#pragma HLS INLINE
#pragma HLS BIND_STORAGE variable=MONO_RC type=rom_1p impl=lutram
    bool bars = dec[7], sq = dec[6], br = dec[5], last = dec[4]; ap_uint<3> mk = dec.range(2, 0); bool addrc = (mk < 5);
    bool rot = !bars && !br;
    word32_t x[16], ob[16], xr[16], obn[16], v[16];
    for (int i = 0; i < 8; i++) {
#pragma HLS UNROLL
        x[2*i] = C[i].range(31, 0); x[2*i+1] = C[i].range(63, 32);
        ob[2*i] = C[8+i].range(31, 0); ob[2*i+1] = C[8+i].range(63, 32); }
    ap_uint<37> p0_0;
    p0_0.range(36, 0) = C[16].range(36, 0);
    ap_uint<37> p0_1;
    p0_1.range(26, 0) = C[16].range(63, 37);
    p0_1.range(36, 27) = C[17].range(9, 0);
    ap_uint<38> f0a = ext ? (ap_uint<38>)EA[0] : (ap_uint<38>)p0_0;
    ap_uint<38> f0b = ext ? (ap_uint<38>)EB[0] : (ap_uint<38>)p0_1;
    ap_uint<38> f0 = f0a + f0b;
    EY[0] = f0.range(31, 0);
    word32_t g0a = ext ? EA[1] : (word32_t)f0.range(30, 0);
    word32_t g0b = ext ? EB[1] : (word32_t)f0.range(37, 31);
    word32_t g0 = g0a + g0b;
    EY[1] = g0;
    v[0] = m31_fold32(g0);
    for (int i = 0; i < 16; i++) {
#pragma HLS UNROLL
        xr[i] = x[(i + 1) & 15];
        obn[i] = (i < 15) ? ob[(i + 1) & 15] : v[(i - 15) & 15];
    }
    lane_t rc[8];
    for (int i = 0; i < 8; i++) {
#pragma HLS UNROLL
        rc[i] = MONO_RC[addrc ? mk : (ap_uint<3>)0][i];
    }
    for (int i = 0; i < 8; i++) {
#pragma HLS UNROLL
        lane_t o, ob2;
        if (br) {
            word32_t a0 = (i == 0) ? x[0] : m31_fold32(x[2*i] + ob[(2*i + 15) & 15]);
            word32_t a1 = m31_fold32(x[2*i+1] + ob[2*i]);
            o = pk(a0, a1);
            ob2 = C[8 + i];
        } else if (bars) {
            o = (i < 4) ? BR[i < 4 ? i : 0] : C[i];
            ob2 = C[8 + i];
        } else if (last) {
            word32_t a0 = obn[2*i], a1 = obn[2*i+1];
            if (addrc) { a0 = m31_fold32(a0 + (word32_t)rc[i].range(31, 0)); a1 = m31_fold32(a1 + (word32_t)rc[i].range(63, 32)); }
            o = pk(a0, a1);
            ob2 = pk(obn[2*i], obn[2*i+1]);
        } else {
            o = pk(xr[2*i], xr[2*i+1]);
            ob2 = pk(obn[2*i], obn[2*i+1]);
        }
        M[i] = o;
        M[8 + i] = ob2;
    }
}

static inline void mono_s4(const lane_t C[MONO_NC], ap_uint<8> dec, lane_t M[MONO_ND], bool ext, const word32_t EA[], const word32_t EB[], word32_t EY[]) {
#pragma HLS INLINE
    lane_t BR[4];
    for (int i = 0; i < 4; i++) {
#pragma HLS UNROLL
        BR[i] = pk(bar31(C[i].range(31, 0)), bar31(C[i].range(63, 32)));
    }
    mono_s4(C, dec, M, ext, EA, EB, EY, BR);
}
