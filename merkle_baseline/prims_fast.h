// prims_fast.h - optimised CPU versions of the node functions (same results as prims.h, checked by run_baseline.py):
//   AES-128 with AES-NI, SHA-256 with SHA-NI (Intel SHA extensions), Keccak-f[1600] fully unrolled with
//   constant rotations and a ping-pong state, Monolith-31 with Mersenne folds instead of '%'.
// Built with -march=native (i7-12700K: AES-NI, SHA-NI, AVX2).
#pragma once
#include <immintrin.h>
#include "prims.h"

namespace fast {

// ---------------- Keccak-f[1600], unrolled ----------------
static constexpr int ROT[25] = {0, 1, 62, 28, 27, 36, 44, 6, 55, 20, 3, 10, 43, 25, 39, 41, 45, 15, 21, 8, 18, 2, 61, 56, 14};
template <int N> static inline uint64_t rol(uint64_t v) { return N ? (v << N) | (v >> (64 - N)) : v; }

static inline void kround(const uint64_t A[25], uint64_t E[25], uint64_t rc)
{
  uint64_t C[5], D[5];
#pragma unroll
  for (int x = 0; x < 5; x++) C[x] = A[x] ^ A[x + 5] ^ A[x + 10] ^ A[x + 15] ^ A[x + 20];
#pragma unroll
  for (int x = 0; x < 5; x++) D[x] = C[(x + 4) % 5] ^ ((C[(x + 1) % 5] << 1) | (C[(x + 1) % 5] >> 63));
#pragma unroll
  for (int Y = 0; Y < 5; Y++)
  {
    uint64_t B[5];
#pragma unroll
    for (int X = 0; X < 5; X++)
    {
      const int x = (X + 3 * Y) % 5, y = X, i = x + 5 * y, n = ROT[i];
      const uint64_t v = A[i] ^ D[x];
      B[X] = n ? (v << n) | (v >> (64 - n)) : v;
    }
#pragma unroll
    for (int X = 0; X < 5; X++) E[X + 5 * Y] = B[X] ^ (~B[(X + 1) % 5] & B[(X + 2) % 5]);
  }
  E[0] ^= rc;
}

inline void keccak_f1600(uint64_t A[25])
{
  uint64_t E[25];
#pragma unroll
  for (int r = 0; r < 24; r += 2) { kround(A, E, prims::KRC[r]); kround(E, A, prims::KRC[r + 1]); }
}

inline void sha3_node(const merkle::HashT<32>& l, const merkle::HashT<32>& r, merkle::HashT<32>& out)
{
  uint64_t s[25] = {0};
  memcpy(s, l.bytes, 32); memcpy(s + 4, r.bytes, 32);     // little-endian lanes = byte order of the message
  s[8] ^= 0x06; s[16] ^= 0x8000000000000000ULL;
  keccak_f1600(s);
  memcpy(out.bytes, s, 32);
}

// ---------------- SHA-256 with SHA-NI ----------------
static const uint32_t K256[64] = {
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};

// one 64-byte block; state packed as STATE0 = ABEF, STATE1 = CDGH (Intel's layout)
static inline void sha256_block_ni(__m128i& S0, __m128i& S1, const uint8_t* data)
{
  const __m128i MASK = _mm_set_epi64x(0x0c0d0e0f08090a0bULL, 0x0405060700010203ULL);
  const __m128i A0 = S0, C0 = S1;
  __m128i W[4];
#pragma unroll
  for (int g = 0; g < 16; g++)
  {
    if (g < 4) W[g] = _mm_shuffle_epi8(_mm_loadu_si128((const __m128i*)(data + 16 * g)), MASK);
    else
    {
      __m128i t = _mm_sha256msg1_epu32(W[(g - 4) & 3], W[(g - 3) & 3]);
      t = _mm_add_epi32(t, _mm_alignr_epi8(W[(g - 1) & 3], W[(g - 2) & 3], 4));
      W[g & 3] = _mm_sha256msg2_epu32(t, W[(g - 1) & 3]);
    }
    __m128i m = _mm_add_epi32(W[g & 3], _mm_setr_epi32((int)K256[4 * g], (int)K256[4 * g + 1], (int)K256[4 * g + 2], (int)K256[4 * g + 3]));
    S1 = _mm_sha256rnds2_epu32(S1, S0, m);
    m = _mm_shuffle_epi32(m, 0x0E);
    S0 = _mm_sha256rnds2_epu32(S0, S1, m);
  }
  S0 = _mm_add_epi32(S0, A0); S1 = _mm_add_epi32(S1, C0);
}

inline void sha256_node(const merkle::HashT<32>& l, const merkle::HashT<32>& r, merkle::HashT<32>& out)
{
  // initial state a..h -> ABEF / CDGH
  __m128i T = _mm_setr_epi32((int)0x6a09e667, (int)0xbb67ae85, (int)0x3c6ef372, (int)0xa54ff53a);   // ABCD
  __m128i S1 = _mm_setr_epi32((int)0x510e527f, (int)0x9b05688c, (int)0x1f83d9ab, (int)0x5be0cd19);  // EFGH
  T = _mm_shuffle_epi32(T, 0xB1);            // CDAB
  S1 = _mm_shuffle_epi32(S1, 0x1B);          // HGFE
  __m128i S0 = _mm_alignr_epi8(T, S1, 8);    // ABEF
  S1 = _mm_blend_epi16(S1, T, 0xF0);         // CDGH
  uint8_t block[64];
  memcpy(block, l.bytes, 32); memcpy(block + 32, r.bytes, 32);
  sha256_block_ni(S0, S1, block);
  uint8_t pad[64] = {0x80}; pad[62] = 0x02;
  sha256_block_ni(S0, S1, pad);
  T = _mm_shuffle_epi32(S0, 0x1B);           // FEBA
  S1 = _mm_shuffle_epi32(S1, 0xB1);          // DCHG
  S0 = _mm_blend_epi16(T, S1, 0xF0);         // DCBA
  S1 = _mm_alignr_epi8(S1, T, 8);            // HGFE
  uint32_t st[8];
  _mm_storeu_si128((__m128i*)st, S0); _mm_storeu_si128((__m128i*)(st + 4), S1);
  for (int i = 0; i < 8; i++)
  {
    out.bytes[4 * i] = (uint8_t)(st[i] >> 24); out.bytes[4 * i + 1] = (uint8_t)(st[i] >> 16);
    out.bytes[4 * i + 2] = (uint8_t)(st[i] >> 8); out.bytes[4 * i + 3] = (uint8_t)st[i];
  }
}

// ---------------- AES-128 with AES-NI ----------------
static inline __m128i key_step(__m128i k, __m128i g)
{
  g = _mm_shuffle_epi32(g, 0xff);
  k = _mm_xor_si128(k, _mm_slli_si128(k, 4));
  k = _mm_xor_si128(k, _mm_slli_si128(k, 4));
  k = _mm_xor_si128(k, _mm_slli_si128(k, 4));
  return _mm_xor_si128(k, g);
}
#define KS(i, rc) k[i] = key_step(k[i - 1], _mm_aeskeygenassist_si128(k[i - 1], rc))
inline void aes128_encrypt(const uint8_t key[16], const uint8_t in[16], uint8_t out[16])
{
  __m128i k[11];
  k[0] = _mm_loadu_si128((const __m128i*)key);
  KS(1, 0x01); KS(2, 0x02); KS(3, 0x04); KS(4, 0x08); KS(5, 0x10); KS(6, 0x20); KS(7, 0x40); KS(8, 0x80); KS(9, 0x1b); KS(10, 0x36);
  __m128i s = _mm_xor_si128(_mm_loadu_si128((const __m128i*)in), k[0]);
#pragma unroll
  for (int r = 1; r < 10; r++) s = _mm_aesenc_si128(s, k[r]);
  s = _mm_aesenclast_si128(s, k[10]);
  _mm_storeu_si128((__m128i*)out, s);
}
#undef KS
inline void aes_node(const merkle::HashT<16>& l, const merkle::HashT<16>& r, merkle::HashT<16>& out)
{
  uint8_t c[16];
  aes128_encrypt(l.bytes, r.bytes, c);
  for (int i = 0; i < 16; i++) out.bytes[i] = c[i] ^ r.bytes[i];
}

// ---------------- Monolith-31 with Mersenne folds ----------------
static inline uint32_t fold62(uint64_t v)       // v < 2^62 -> canonical [0, P)
{
  uint64_t r = (v & prims::M31P) + (v >> 31);   // < 2^31 + 2^31
  r = (r & prims::M31P) + (r >> 31);            // <= P
  return r == prims::M31P ? 0 : (uint32_t)r;
}
inline void concrete(uint32_t x[16])
{
  uint32_t y[16];
#pragma unroll
  for (int i = 0; i < 16; i++)
  {
    uint64_t acc = 0;
#pragma unroll
    for (int k = 0; k < 16; k++) acc += prims::MROW[k] * (uint64_t)x[(i + k) & 15];
    y[i] = fold62(acc);
  }
  memcpy(x, y, sizeof y);
}
inline void monolith_perm(uint32_t x[16])
{
  concrete(x);
  for (int k = 0; k < 6; k++)
  {
    for (int i = 0; i < 8; i++) x[i] = prims::bar31(x[i]);
    for (int i = 15; i >= 1; i--) x[i] = fold62(x[i] + (uint64_t)x[i - 1] * x[i - 1]);
    concrete(x);
    if (k < 5)
      for (int i = 0; i < 16; i++) { uint32_t v = x[i] + prims::MRC[k][i]; x[i] = v >= prims::M31P ? v - prims::M31P : v; }
  }
}
inline void mono_node(const merkle::HashT<32>& l, const merkle::HashT<32>& r, merkle::HashT<32>& out)
{
  uint32_t x[16];
  memcpy(x, l.bytes, 32); memcpy(x + 8, r.bytes, 32);
  monolith_perm(x);
  memcpy(out.bytes, x, 32);
}

// ChaCha20: the portable code is already word-parallel; reuse it
inline void chacha_node(const merkle::HashT<32>& l, const merkle::HashT<32>& r, merkle::HashT<32>& out) { prims::chacha_node(l, r, out); }

}  // namespace fast
