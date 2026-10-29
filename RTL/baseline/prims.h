// prims.h - the five tree primitives as plain C++ (uint32/uint64) node functions for the merklecpp baseline.
// Every node function has merklecpp's signature  void f(const HashT<N>& l, const HashT<N>& r, HashT<N>& out)
// and computes the SAME function as the unified HLS unit (dse/TOP, verified by verify/check_pipe.py):
//   sha256   : merkle::sha256          SHA-256(l || r) with padding, two compressions          (32 B)
//   sha3     : SHA3-256(l || r)        one Keccak-f[1600] (64 B < rate 136 B)                   (32 B)
//   chacha   : h1 = Block(key = l, ctr||nonce = r[0:16])[0:32], out = Block(key = h1, ctr||nonce = r[16:32])[0:32]
//              two ChaCha20 block functions, every input byte reaches the output                (32 B)
//   aes      : AES-128_{key = l}(r) ^ r  (Davies-Meyer, the unit's fixed-key mode)               (16 B)
//   monolith : Monolith-31 t=16 permutation of (l || r) as 16 Mersenne31 elements, first 8 out (32 B, 8 x u32 LE)
#pragma once
#include <cstdint>
#include <cstring>
#include <merklecpp.h>

namespace prims {

// ---------------- Keccak-f[1600] / SHA3-256 ----------------
static const uint64_t KRC[24] = {
  0x0000000000000001ULL, 0x0000000000008082ULL, 0x800000000000808AULL, 0x8000000080008000ULL,
  0x000000000000808BULL, 0x0000000080000001ULL, 0x8000000080008081ULL, 0x8000000000008009ULL,
  0x000000000000008AULL, 0x0000000000000088ULL, 0x0000000080008009ULL, 0x000000008000000AULL,
  0x000000008000808BULL, 0x800000000000008BULL, 0x8000000000008089ULL, 0x8000000000008003ULL,
  0x8000000000008002ULL, 0x8000000000000080ULL, 0x000000000000800AULL, 0x800000008000000AULL,
  0x8000000080008081ULL, 0x8000000000008080ULL, 0x0000000080000001ULL, 0x8000000080008008ULL};
static const int KROT[25] = {0, 1, 62, 28, 27, 36, 44, 6, 55, 20, 3, 10, 43, 25, 39, 41, 45, 15, 21, 8, 18, 2, 61, 56, 14};
inline uint64_t rotl64(uint64_t v, int n) { return n ? (v << n) | (v >> (64 - n)) : v; }

inline void keccak_f1600(uint64_t s[25])
{
  for (int r = 0; r < 24; r++)
  {
    uint64_t C[5], D[5], B[25];
    for (int x = 0; x < 5; x++) C[x] = s[x] ^ s[x + 5] ^ s[x + 10] ^ s[x + 15] ^ s[x + 20];
    for (int x = 0; x < 5; x++) D[x] = C[(x + 4) % 5] ^ rotl64(C[(x + 1) % 5], 1);
    for (int i = 0; i < 25; i++) s[i] ^= D[i % 5];
    for (int x = 0; x < 5; x++)
      for (int y = 0; y < 5; y++) B[y + 5 * ((2 * x + 3 * y) % 5)] = rotl64(s[x + 5 * y], KROT[x + 5 * y]);
    for (int i = 0; i < 25; i++)
    {
      int x = i % 5, y5 = i - x;
      s[i] = B[i] ^ (~B[(x + 1) % 5 + y5] & B[(x + 2) % 5 + y5]);
    }
    s[0] ^= KRC[r];
  }
}

inline void sha3_256(const uint8_t* msg, size_t len, uint8_t out[32])   // len <= 135 (one block)
{
  uint64_t s[25] = {0};
  uint8_t blk[136] = {0};
  memcpy(blk, msg, len);
  blk[len] ^= 0x06; blk[135] ^= 0x80;
  for (int i = 0; i < 17; i++)
  {
    uint64_t w = 0;
    for (int b = 0; b < 8; b++) w |= (uint64_t)blk[8 * i + b] << (8 * b);
    s[i] ^= w;
  }
  keccak_f1600(s);
  for (int i = 0; i < 4; i++)
    for (int b = 0; b < 8; b++) out[8 * i + b] = (uint8_t)(s[i] >> (8 * b));
}

inline void sha3_node(const merkle::HashT<32>& l, const merkle::HashT<32>& r, merkle::HashT<32>& out)
{
  uint8_t m[64];
  memcpy(m, l.bytes, 32); memcpy(m + 32, r.bytes, 32);
  sha3_256(m, 64, out.bytes);
}

// ---------------- ChaCha20 block function (RFC 8439) ----------------
inline uint32_t rotl32(uint32_t v, int n) { return (v << n) | (v >> (32 - n)); }
inline uint32_t ld32(const uint8_t* p) { return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24); }
inline void st32(uint8_t* p, uint32_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); p[2] = (uint8_t)(v >> 16); p[3] = (uint8_t)(v >> 24); }
#define CC_QR(a, b, c, d) \
  a += b; d ^= a; d = rotl32(d, 16); c += d; b ^= c; b = rotl32(b, 12); \
  a += b; d ^= a; d = rotl32(d, 8);  c += d; b ^= c; b = rotl32(b, 7);

inline void chacha_block(const uint8_t key[32], uint32_t counter, const uint8_t nonce[12], uint8_t out[64])
{
  uint32_t s[16] = {0x61707865u, 0x3320646eu, 0x79622d32u, 0x6b206574u};
  for (int i = 0; i < 8; i++) s[4 + i] = ld32(key + 4 * i);
  s[12] = counter;
  for (int i = 0; i < 3; i++) s[13 + i] = ld32(nonce + 4 * i);
  uint32_t x[16];
  memcpy(x, s, sizeof x);
  for (int i = 0; i < 10; i++)
  {
    CC_QR(x[0], x[4], x[8], x[12]) CC_QR(x[1], x[5], x[9], x[13]) CC_QR(x[2], x[6], x[10], x[14]) CC_QR(x[3], x[7], x[11], x[15])
    CC_QR(x[0], x[5], x[10], x[15]) CC_QR(x[1], x[6], x[11], x[12]) CC_QR(x[2], x[7], x[8], x[13]) CC_QR(x[3], x[4], x[9], x[14])
  }
  for (int i = 0; i < 16; i++) st32(out + 4 * i, x[i] + s[i]);
}
#undef CC_QR

inline void chacha_node(const merkle::HashT<32>& l, const merkle::HashT<32>& r, merkle::HashT<32>& out)
{
  uint8_t ks[64];
  chacha_block(l.bytes, ld32(r.bytes), r.bytes + 4, ks);
  uint8_t h1[32];
  memcpy(h1, ks, 32);
  chacha_block(h1, ld32(r.bytes + 16), r.bytes + 20, ks);
  memcpy(out.bytes, ks, 32);
}

// ---------------- AES-128 (S-box generated from the field, FIPS-197) ----------------
struct AesTables
{
  uint8_t sbox[256];
  AesTables()
  {
    uint8_t inv[256] = {0};
    for (int a = 1; a < 256; a++)
      for (int b = 1; b < 256; b++)
      {
        uint8_t p = 0, x = (uint8_t)a, y = (uint8_t)b;
        for (int i = 0; i < 8; i++) { if (y & 1) p ^= x; uint8_t hi = x & 0x80; x <<= 1; if (hi) x ^= 0x1b; y >>= 1; }
        if (p == 1) { inv[a] = (uint8_t)b; break; }
      }
    for (int a = 0; a < 256; a++)
    {
      uint8_t v = inv[a], s = v;
      for (int i = 1; i <= 4; i++) { v = (uint8_t)((v << 1) | (v >> 7)); s ^= v; }
      sbox[a] = s ^ 0x63;
    }
  }
};
inline const AesTables& aes_tables() { static AesTables t; return t; }
inline uint8_t xtime(uint8_t x) { return (uint8_t)((x << 1) ^ ((x & 0x80) ? 0x1b : 0)); }

inline void aes128_encrypt(const uint8_t key[16], const uint8_t in[16], uint8_t out[16])
{
  const uint8_t* S = aes_tables().sbox;
  uint8_t rk[11][16];
  memcpy(rk[0], key, 16);
  uint8_t rcon = 1;
  for (int r = 1; r <= 10; r++)
  {
    uint8_t t[4] = {S[rk[r - 1][13]], S[rk[r - 1][14]], S[rk[r - 1][15]], S[rk[r - 1][12]]};
    t[0] ^= rcon; rcon = xtime(rcon);
    for (int i = 0; i < 4; i++) rk[r][i] = rk[r - 1][i] ^ t[i];
    for (int i = 4; i < 16; i++) rk[r][i] = rk[r - 1][i] ^ rk[r][i - 4];
  }
  uint8_t s[16];
  for (int i = 0; i < 16; i++) s[i] = in[i] ^ rk[0][i];
  for (int r = 1; r <= 10; r++)
  {
    uint8_t t[16];
    for (int i = 0; i < 16; i++) t[i] = S[s[i]];                                   // SubBytes
    for (int c = 0; c < 4; c++)                                                     // ShiftRows (column-major state)
      for (int row = 0; row < 4; row++) s[4 * c + row] = t[4 * ((c + row) & 3) + row];
    if (r < 10)
      for (int c = 0; c < 4; c++)                                                   // MixColumns
      {
        uint8_t a0 = s[4 * c], a1 = s[4 * c + 1], a2 = s[4 * c + 2], a3 = s[4 * c + 3];
        s[4 * c]     = xtime(a0) ^ (xtime(a1) ^ a1) ^ a2 ^ a3;
        s[4 * c + 1] = a0 ^ xtime(a1) ^ (xtime(a2) ^ a2) ^ a3;
        s[4 * c + 2] = a0 ^ a1 ^ xtime(a2) ^ (xtime(a3) ^ a3);
        s[4 * c + 3] = (xtime(a0) ^ a0) ^ a1 ^ a2 ^ xtime(a3);
      }
    for (int i = 0; i < 16; i++) s[i] ^= rk[r][i];
  }
  memcpy(out, s, 16);
}

inline void aes_node(const merkle::HashT<16>& l, const merkle::HashT<16>& r, merkle::HashT<16>& out)
{
  uint8_t c[16];
  aes128_encrypt(l.bytes, r.bytes, c);
  for (int i = 0; i < 16; i++) out.bytes[i] = c[i] ^ r.bytes[i];
}

// ---------------- Monolith-31 (t = 16, Plonky3 structure, Mersenne31) ----------------
static const uint32_t M31P = 0x7FFFFFFFu;
static const uint64_t MROW[16] = {61402, 17845, 26798, 59689, 12021, 40901, 41351, 27521, 56951, 12034, 53865, 43244, 7454, 33823, 28750, 1108};
static const uint32_t MRC[5][16] = {
#include "mono_rc.inc"
};
inline uint32_t bar_chunk8(uint32_t x)
{
  uint32_t nx = (~x) & 0xFF;
  uint32_t r1 = ((nx << 1) | (nx >> 7)) & 0xFF, r2 = ((x << 2) | (x >> 6)) & 0xFF, r3 = ((x << 3) | (x >> 5)) & 0xFF;
  uint32_t t = x ^ (r1 & r2 & r3);
  return ((t << 1) | (t >> 7)) & 0xFF;
}
inline uint32_t bar_chunk7(uint32_t x)
{
  uint32_t nx = (~x) & 0x7F;
  uint32_t r1 = ((nx << 1) | (nx >> 6)) & 0x7F, r2 = ((x << 2) | (x >> 5)) & 0x7F;   // 7-bit chunk: two rotations
  uint32_t t = x ^ (r1 & r2);
  return ((t << 1) | (t >> 6)) & 0x7F;
}
inline uint32_t bar31(uint32_t x)
{
  return bar_chunk8(x & 0xFF) | (bar_chunk8((x >> 8) & 0xFF) << 8) | (bar_chunk8((x >> 16) & 0xFF) << 16) | (bar_chunk7(x >> 24) << 24);
}
inline void concrete(uint32_t x[16])
{
  uint32_t y[16];
  for (int i = 0; i < 16; i++)
  {
    uint64_t acc = 0;
    for (int k = 0; k < 16; k++) acc += MROW[k] * (uint64_t)x[(i + k) & 15];   // < 2^51
    y[i] = (uint32_t)(acc % M31P);
  }
  memcpy(x, y, sizeof y);
}
inline void monolith_perm(uint32_t x[16])
{
  concrete(x);
  for (int k = 0; k < 6; k++)
  {
    for (int i = 0; i < 8; i++) x[i] = bar31(x[i]);
    for (int i = 15; i >= 1; i--) x[i] = (uint32_t)((x[i] + (uint64_t)x[i - 1] * x[i - 1]) % M31P);
    concrete(x);
    if (k < 5)
      for (int i = 0; i < 16; i++) { uint32_t v = x[i] + MRC[k][i]; x[i] = v >= M31P ? v - M31P : v; }
  }
}
inline void mono_node(const merkle::HashT<32>& l, const merkle::HashT<32>& r, merkle::HashT<32>& out)
{
  uint32_t x[16];
  for (int i = 0; i < 8; i++) { x[i] = ld32(l.bytes + 4 * i); x[8 + i] = ld32(r.bytes + 4 * i); }
  monolith_perm(x);
  for (int i = 0; i < 8; i++) st32(out.bytes + 4 * i, x[i]);
}

}  // namespace prims
