// gpu_prims.cu - the five tree node functions as CUDA kernels (same definitions as prims.h), built as a DLL
// (fresh executables are blocked on this machine) and driven by run_gpu.py.
//   prim: 0 sha3  1 sha256  2 chacha (2 blocks)  3 aes DM (16-byte digests)  4 monolith
#include <cuda_runtime.h>
#include <cstdint>
#include <cstdio>
#include <cstring>
#ifdef _WIN32
#define API extern "C" __declspec(dllexport)
#else
#define API extern "C" __attribute__((visibility("default")))
#endif

__constant__ uint64_t KRC[24] = {
  0x0000000000000001ULL, 0x0000000000008082ULL, 0x800000000000808AULL, 0x8000000080008000ULL,
  0x000000000000808BULL, 0x0000000080000001ULL, 0x8000000080008081ULL, 0x8000000000008009ULL,
  0x000000000000008AULL, 0x0000000000000088ULL, 0x0000000080008009ULL, 0x000000008000000AULL,
  0x000000008000808BULL, 0x800000000000008BULL, 0x8000000000008089ULL, 0x8000000000008003ULL,
  0x8000000000008002ULL, 0x8000000000000080ULL, 0x000000000000800AULL, 0x800000008000000AULL,
  0x8000000080008081ULL, 0x8000000000008080ULL, 0x0000000080000001ULL, 0x8000000080008008ULL};
__constant__ uint32_t K256[64] = {
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};
__constant__ uint8_t SBOX_C[256];
__constant__ uint32_t MRC_C[5][16];
__constant__ uint64_t MROW[16] = {61402, 17845, 26798, 59689, 12021, 40901, 41351, 27521, 56951, 12034, 53865, 43244, 7454, 33823, 28750, 1108};
#define M31P 0x7FFFFFFFu

// ---------------- Keccak ----------------
__device__ __forceinline__ uint64_t rotl64(uint64_t v, int n) { return (v << n) | (v >> (64 - n)); }
__constant__ int KROT[25] = {0, 1, 62, 28, 27, 36, 44, 6, 55, 20, 3, 10, 43, 25, 39, 41, 45, 15, 21, 8, 18, 2, 61, 56, 14};
__device__ void keccak_f1600(uint64_t s[25])
{
#pragma unroll 1
  for (int r = 0; r < 24; r++)
  {
    uint64_t C[5], D[5], B[25];
#pragma unroll
    for (int x = 0; x < 5; x++) C[x] = s[x] ^ s[x + 5] ^ s[x + 10] ^ s[x + 15] ^ s[x + 20];
#pragma unroll
    for (int x = 0; x < 5; x++) D[x] = C[(x + 4) % 5] ^ rotl64(C[(x + 1) % 5], 1);
#pragma unroll
    for (int i = 0; i < 25; i++) s[i] ^= D[i % 5];
#pragma unroll
    for (int x = 0; x < 5; x++)
#pragma unroll
      for (int y = 0; y < 5; y++)
      {
        const int n = KROT[x + 5 * y];
        B[y + 5 * ((2 * x + 3 * y) % 5)] = n ? rotl64(s[x + 5 * y], n) : s[x + 5 * y];
      }
#pragma unroll
    for (int i = 0; i < 25; i++)
    {
      const int x = i % 5, y5 = i - x;
      s[i] = B[i] ^ (~B[(x + 1) % 5 + y5] & B[(x + 2) % 5 + y5]);
    }
    s[0] ^= KRC[r];
  }
}
__device__ void sha3_node(const uint8_t* l, const uint8_t* r, uint8_t* out)
{
  uint64_t s[25];
#pragma unroll
  for (int i = 0; i < 25; i++) s[i] = 0;
  const uint64_t* L = (const uint64_t*)l; const uint64_t* R = (const uint64_t*)r;
#pragma unroll
  for (int i = 0; i < 4; i++) { s[i] = L[i]; s[4 + i] = R[i]; }
  s[8] ^= 0x06ULL; s[16] ^= 0x8000000000000000ULL;
  keccak_f1600(s);
  uint64_t* O = (uint64_t*)out;
#pragma unroll
  for (int i = 0; i < 4; i++) O[i] = s[i];
}

// ---------------- SHA-256 ----------------
__device__ __forceinline__ uint32_t rotr32(uint32_t v, int n) { return (v >> n) | (v << (32 - n)); }
__device__ void sha256_transform(uint32_t st[8], const uint8_t blk[64])
{
  uint32_t w[64];
#pragma unroll
  for (int i = 0; i < 16; i++) w[i] = ((uint32_t)blk[4 * i] << 24) | ((uint32_t)blk[4 * i + 1] << 16) | ((uint32_t)blk[4 * i + 2] << 8) | blk[4 * i + 3];
#pragma unroll
  for (int i = 16; i < 64; i++)
  {
    uint32_t s0 = rotr32(w[i - 15], 7) ^ rotr32(w[i - 15], 18) ^ (w[i - 15] >> 3);
    uint32_t s1 = rotr32(w[i - 2], 17) ^ rotr32(w[i - 2], 19) ^ (w[i - 2] >> 10);
    w[i] = w[i - 16] + s0 + w[i - 7] + s1;
  }
  uint32_t a = st[0], b = st[1], c = st[2], d = st[3], e = st[4], f = st[5], g = st[6], h = st[7];
#pragma unroll
  for (int i = 0; i < 64; i++)
  {
    uint32_t S1 = rotr32(e, 6) ^ rotr32(e, 11) ^ rotr32(e, 25);
    uint32_t ch = (e & f) ^ (~e & g);
    uint32_t t1 = h + S1 + ch + K256[i] + w[i];
    uint32_t S0 = rotr32(a, 2) ^ rotr32(a, 13) ^ rotr32(a, 22);
    uint32_t mj = (a & b) ^ (a & c) ^ (b & c);
    uint32_t t2 = S0 + mj;
    h = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
  }
  st[0] += a; st[1] += b; st[2] += c; st[3] += d; st[4] += e; st[5] += f; st[6] += g; st[7] += h;
}
__device__ void sha256_node(const uint8_t* l, const uint8_t* r, uint8_t* out)
{
  uint32_t st[8] = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};
  uint8_t blk[64];
#pragma unroll
  for (int i = 0; i < 32; i++) { blk[i] = l[i]; blk[32 + i] = r[i]; }
  sha256_transform(st, blk);
#pragma unroll
  for (int i = 0; i < 64; i++) blk[i] = 0;
  blk[0] = 0x80; blk[62] = 0x02;
  sha256_transform(st, blk);
#pragma unroll
  for (int i = 0; i < 8; i++) { out[4 * i] = st[i] >> 24; out[4 * i + 1] = st[i] >> 16; out[4 * i + 2] = st[i] >> 8; out[4 * i + 3] = st[i]; }
}

// ---------------- ChaCha20 ----------------
__device__ __forceinline__ uint32_t rotl32(uint32_t v, int n) { return (v << n) | (v >> (32 - n)); }
#define QR(a, b, c, d) a += b; d ^= a; d = rotl32(d, 16); c += d; b ^= c; b = rotl32(b, 12); a += b; d ^= a; d = rotl32(d, 8); c += d; b ^= c; b = rotl32(b, 7);
__device__ void chacha_block(const uint32_t key[8], uint32_t ctr, const uint32_t nonce[3], uint32_t out[16])
{
  uint32_t s[16] = {0x61707865u, 0x3320646eu, 0x79622d32u, 0x6b206574u, key[0], key[1], key[2], key[3], key[4], key[5], key[6], key[7], ctr, nonce[0], nonce[1], nonce[2]};
  uint32_t x[16];
#pragma unroll
  for (int i = 0; i < 16; i++) x[i] = s[i];
#pragma unroll
  for (int i = 0; i < 10; i++)
  {
    QR(x[0], x[4], x[8], x[12]) QR(x[1], x[5], x[9], x[13]) QR(x[2], x[6], x[10], x[14]) QR(x[3], x[7], x[11], x[15])
    QR(x[0], x[5], x[10], x[15]) QR(x[1], x[6], x[11], x[12]) QR(x[2], x[7], x[8], x[13]) QR(x[3], x[4], x[9], x[14])
  }
#pragma unroll
  for (int i = 0; i < 16; i++) out[i] = x[i] + s[i];
}
__device__ void chacha_node(const uint8_t* l, const uint8_t* r, uint8_t* out)
{
  const uint32_t* L = (const uint32_t*)l; const uint32_t* R = (const uint32_t*)r;
  uint32_t ks[16];
  chacha_block(L, R[0], R + 1, ks);
  uint32_t h1[8];
#pragma unroll
  for (int i = 0; i < 8; i++) h1[i] = ks[i];
  chacha_block(h1, R[4], R + 5, ks);
  uint32_t* O = (uint32_t*)out;
#pragma unroll
  for (int i = 0; i < 8; i++) O[i] = ks[i];
}

// ---------------- AES-128 (S-box in shared memory) ----------------
__device__ __forceinline__ uint8_t xtime(uint8_t x) { return (uint8_t)((x << 1) ^ ((x & 0x80) ? 0x1b : 0)); }
__device__ void aes128_encrypt(const uint8_t* S, const uint8_t key[16], const uint8_t in[16], uint8_t out[16])
{
  uint8_t rk[11][16];
#pragma unroll
  for (int i = 0; i < 16; i++) rk[0][i] = key[i];
  uint8_t rcon = 1;
#pragma unroll
  for (int r = 1; r <= 10; r++)
  {
    uint8_t t[4] = {S[rk[r - 1][13]], S[rk[r - 1][14]], S[rk[r - 1][15]], S[rk[r - 1][12]]};
    t[0] ^= rcon; rcon = xtime(rcon);
#pragma unroll
    for (int i = 0; i < 4; i++) rk[r][i] = rk[r - 1][i] ^ t[i];
#pragma unroll
    for (int i = 4; i < 16; i++) rk[r][i] = rk[r - 1][i] ^ rk[r][i - 4];
  }
  uint8_t s[16];
#pragma unroll
  for (int i = 0; i < 16; i++) s[i] = in[i] ^ rk[0][i];
#pragma unroll
  for (int r = 1; r <= 10; r++)
  {
    uint8_t t[16];
#pragma unroll
    for (int i = 0; i < 16; i++) t[i] = S[s[i]];
#pragma unroll
    for (int c = 0; c < 4; c++)
#pragma unroll
      for (int row = 0; row < 4; row++) s[4 * c + row] = t[4 * ((c + row) & 3) + row];
    if (r < 10)
#pragma unroll
      for (int c = 0; c < 4; c++)
      {
        uint8_t a0 = s[4 * c], a1 = s[4 * c + 1], a2 = s[4 * c + 2], a3 = s[4 * c + 3];
        s[4 * c]     = xtime(a0) ^ (xtime(a1) ^ a1) ^ a2 ^ a3;
        s[4 * c + 1] = a0 ^ xtime(a1) ^ (xtime(a2) ^ a2) ^ a3;
        s[4 * c + 2] = a0 ^ a1 ^ xtime(a2) ^ (xtime(a3) ^ a3);
        s[4 * c + 3] = (xtime(a0) ^ a0) ^ a1 ^ a2 ^ xtime(a3);
      }
#pragma unroll
    for (int i = 0; i < 16; i++) s[i] ^= rk[r][i];
  }
#pragma unroll
  for (int i = 0; i < 16; i++) out[i] = s[i];
}
__device__ void aes_node(const uint8_t* S, const uint8_t* l, const uint8_t* r, uint8_t* out)
{
  uint8_t c[16];
  aes128_encrypt(S, l, r, c);
#pragma unroll
  for (int i = 0; i < 16; i++) out[i] = c[i] ^ r[i];
}

// ---------------- Monolith-31 ----------------
__device__ __forceinline__ uint32_t fold62(uint64_t v)
{
  uint64_t r = (v & M31P) + (v >> 31);
  r = (r & M31P) + (r >> 31);
  return r == M31P ? 0 : (uint32_t)r;
}
__device__ __forceinline__ uint32_t bar_chunk8(uint32_t x)
{
  uint32_t nx = (~x) & 0xFF;
  uint32_t r1 = ((nx << 1) | (nx >> 7)) & 0xFF, r2 = ((x << 2) | (x >> 6)) & 0xFF, r3 = ((x << 3) | (x >> 5)) & 0xFF;
  uint32_t t = x ^ (r1 & r2 & r3);
  return ((t << 1) | (t >> 7)) & 0xFF;
}
__device__ __forceinline__ uint32_t bar_chunk7(uint32_t x)
{
  uint32_t nx = (~x) & 0x7F;
  uint32_t r1 = ((nx << 1) | (nx >> 6)) & 0x7F, r2 = ((x << 2) | (x >> 5)) & 0x7F;   // 7-bit chunk: two rotations
  uint32_t t = x ^ (r1 & r2);
  return ((t << 1) | (t >> 6)) & 0x7F;
}
__device__ __forceinline__ uint32_t bar31(uint32_t x)
{
  return bar_chunk8(x & 0xFF) | (bar_chunk8((x >> 8) & 0xFF) << 8) | (bar_chunk8((x >> 16) & 0xFF) << 16) | (bar_chunk7(x >> 24) << 24);
}
__device__ void concrete(uint32_t x[16])
{
  uint32_t y[16];
#pragma unroll
  for (int i = 0; i < 16; i++)
  {
    uint64_t acc = 0;
#pragma unroll
    for (int k = 0; k < 16; k++) acc += MROW[k] * (uint64_t)x[(i + k) & 15];
    y[i] = fold62(acc);
  }
#pragma unroll
  for (int i = 0; i < 16; i++) x[i] = y[i];
}
__device__ void monolith_perm(uint32_t x[16])
{
  concrete(x);
#pragma unroll 1
  for (int k = 0; k < 6; k++)
  {
#pragma unroll
    for (int i = 0; i < 8; i++) x[i] = bar31(x[i]);
#pragma unroll
    for (int i = 15; i >= 1; i--) x[i] = fold62(x[i] + (uint64_t)x[i - 1] * x[i - 1]);
    concrete(x);
    if (k < 5)
#pragma unroll
      for (int i = 0; i < 16; i++) { uint32_t v = x[i] + MRC_C[k][i]; x[i] = v >= M31P ? v - M31P : v; }
  }
}
__device__ void mono_node(const uint8_t* l, const uint8_t* r, uint8_t* out)
{
  uint32_t x[16];
  const uint32_t* L = (const uint32_t*)l; const uint32_t* R = (const uint32_t*)r;
#pragma unroll
  for (int i = 0; i < 8; i++) { x[i] = L[i]; x[8 + i] = R[i]; }
  monolith_perm(x);
  uint32_t* O = (uint32_t*)out;
#pragma unroll
  for (int i = 0; i < 8; i++) O[i] = x[i];
}

// ---------------- BLAKE3 (prim 5: Merkle parent node, prim 6: keyed-XOF GGM node, 64-byte output) ----------------
__constant__ uint32_t B3IV[8] = {0x6A09E667u, 0xBB67AE85u, 0x3C6EF372u, 0xA54FF53Au, 0x510E527Fu, 0x9B05688Cu, 0x1F83D9ABu, 0x5BE0CD19u};
#define B3G(a, b, c, d, x, y) v[a] += v[b] + x; v[d] = rotr32(v[d] ^ v[a], 16); v[c] += v[d]; v[b] = rotr32(v[b] ^ v[c], 12); v[a] += v[b] + y; v[d] = rotr32(v[d] ^ v[a], 8); v[c] += v[d]; v[b] = rotr32(v[b] ^ v[c], 7);
__device__ void b3_compress(const uint32_t h[8], const uint32_t blk[16], uint32_t blen, uint32_t flags, uint32_t out[16])
{
  const int SIG[16] = {2, 6, 3, 10, 7, 0, 4, 13, 1, 11, 12, 5, 9, 14, 15, 8};
  uint32_t v[16] = {h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7], B3IV[0], B3IV[1], B3IV[2], B3IV[3], 0, 0, blen, flags};
  uint32_t m[16];
#pragma unroll
  for (int i = 0; i < 16; i++) m[i] = blk[i];
#pragma unroll
  for (int r = 0; r < 7; r++)
  {
    B3G(0, 4, 8, 12, m[0], m[1]) B3G(1, 5, 9, 13, m[2], m[3]) B3G(2, 6, 10, 14, m[4], m[5]) B3G(3, 7, 11, 15, m[6], m[7])
    B3G(0, 5, 10, 15, m[8], m[9]) B3G(1, 6, 11, 12, m[10], m[11]) B3G(2, 7, 8, 13, m[12], m[13]) B3G(3, 4, 9, 14, m[14], m[15])
    uint32_t t[16];
#pragma unroll
    for (int i = 0; i < 16; i++) t[i] = m[SIG[i]];
#pragma unroll
    for (int i = 0; i < 16; i++) m[i] = t[i];
  }
#pragma unroll
  for (int i = 0; i < 8; i++) { out[i] = v[i] ^ v[i + 8]; out[i + 8] = v[i + 8] ^ h[i]; }
}
__device__ void b3_parent_node(const uint8_t* l, const uint8_t* r, uint8_t* out)      // h = IV, block = l || r, PARENT
{
  uint32_t blk[16], o[16];
  const uint32_t* L = (const uint32_t*)l; const uint32_t* R = (const uint32_t*)r;
#pragma unroll
  for (int i = 0; i < 8; i++) { blk[i] = L[i]; blk[8 + i] = R[i]; }
  b3_compress(B3IV, blk, 64, 4, o);
  uint32_t* O = (uint32_t*)out;
#pragma unroll
  for (int i = 0; i < 8; i++) O[i] = o[i];
}
__device__ void b3_xof_node(const uint8_t* l, const uint8_t* r, uint8_t* out)        // h = seed (l), block = index words (r), KEYED|START|END|ROOT, 64 bytes out
{
  uint32_t blk[16], o[16];
  const uint32_t* L = (const uint32_t*)l; const uint32_t* R = (const uint32_t*)r;
#pragma unroll
  for (int i = 0; i < 8; i++) { blk[i] = R[i]; blk[8 + i] = 0; }
  b3_compress(L, blk, 64, 16 | 1 | 2 | 8, o);
  uint32_t* O = (uint32_t*)out;
#pragma unroll
  for (int i = 0; i < 16; i++) O[i] = o[i];
}

// ---------------- kernels ----------------
template <int P>
__global__ void node_kernel(const uint8_t* __restrict__ in, uint8_t* __restrict__ out, size_t n)
{
  __shared__ uint8_t S[256];
  if (P == 3) { for (int i = threadIdx.x; i < 256; i += blockDim.x) S[i] = SBOX_C[i]; __syncthreads(); }
  size_t i = (size_t)blockIdx.x * blockDim.x + threadIdx.x;
  if (i >= n) return;
  constexpr int D = (P == 3) ? 16 : 32;
  constexpr int DO = (P == 6) ? 64 : D;
  const uint8_t* l = in + i * 2 * D; const uint8_t* r = l + D;
  uint8_t lb[32], rb[32], o[64];
#pragma unroll
  for (int k = 0; k < D; k++) { lb[k] = l[k]; rb[k] = r[k]; }
  if (P == 0) sha3_node(lb, rb, o);
  else if (P == 1) sha256_node(lb, rb, o);
  else if (P == 2) chacha_node(lb, rb, o);
  else if (P == 3) aes_node(S, lb, rb, o);
  else if (P == 5) b3_parent_node(lb, rb, o);
  else if (P == 6) b3_xof_node(lb, rb, o);
  else mono_node(lb, rb, o);
#pragma unroll
  for (int k = 0; k < DO; k++) out[i * DO + k] = o[k];
}
__global__ void fill_kernel(uint8_t* buf, size_t words, uint64_t seed)
{
  size_t i = (size_t)blockIdx.x * blockDim.x + threadIdx.x;
  if (i >= words) return;
  uint64_t s = seed ^ (i * 0x9E3779B97F4A7C15ULL);
  s ^= s >> 12; s ^= s << 25; s ^= s >> 27; s *= 0x2545F4914F6CDD1DULL;
  uint32_t v = (uint32_t)s & 0x7FFFFFFFu;
  if (v == 0x7FFFFFFFu) v = 0;
  ((uint32_t*)buf)[i] = v;
}

static void launch(int p, const uint8_t* in, uint8_t* out, size_t n)
{
  int tpb = 256; size_t blocks = (n + tpb - 1) / tpb;
  switch (p)
  {
    case 0: node_kernel<0><<<(unsigned)blocks, tpb>>>(in, out, n); break;
    case 1: node_kernel<1><<<(unsigned)blocks, tpb>>>(in, out, n); break;
    case 2: node_kernel<2><<<(unsigned)blocks, tpb>>>(in, out, n); break;
    case 3: node_kernel<3><<<(unsigned)blocks, tpb>>>(in, out, n); break;
    case 5: node_kernel<5><<<(unsigned)blocks, tpb>>>(in, out, n); break;
    case 6: node_kernel<6><<<(unsigned)blocks, tpb>>>(in, out, n); break;
    default: node_kernel<4><<<(unsigned)blocks, tpb>>>(in, out, n); break;
  }
}
static int dsize(int p) { return p == 3 ? 16 : 32; }
static int osize(int p) { return p == 6 ? 64 : dsize(p); }

API int gpu_init(const uint8_t* sbox, const uint32_t* mrc)
{
  if (cudaMemcpyToSymbol(SBOX_C, sbox, 256) != cudaSuccess) return -1;
  if (cudaMemcpyToSymbol(MRC_C, mrc, 5 * 16 * 4) != cudaSuccess) return -2;
  return 0;
}
API const char* gpu_name()
{
  static char name[256];
  cudaDeviceProp prop; cudaGetDeviceProperties(&prop, 0);
  snprintf(name, sizeof name, "%s, %d SMs, %.2f GHz", prop.name, prop.multiProcessorCount, prop.clockRate / 1e6);
  return name;
}
API int gpu_node(int p, const uint8_t* l, const uint8_t* r, uint8_t* out)   // one node (cross-check)
{
  int D = dsize(p), DO = osize(p);
  uint8_t *din, *dout;
  cudaMalloc(&din, 2 * D); cudaMalloc(&dout, DO);
  cudaMemcpy(din, l, D, cudaMemcpyHostToDevice); cudaMemcpy(din + D, r, D, cudaMemcpyHostToDevice);
  launch(p, din, dout, 1);
  cudaError_t e = cudaDeviceSynchronize();
  cudaMemcpy(out, dout, DO, cudaMemcpyDeviceToHost);
  cudaFree(din); cudaFree(dout);
  return e == cudaSuccess ? 0 : (int)e;
}
API double bench_gpu_nodes(int p, int log2n, int reps)   // ns per node, independent nodes (pure throughput)
{
  int D = dsize(p); size_t n = (size_t)1 << log2n;
  uint8_t *din, *dout;
  cudaMalloc(&din, n * 2 * D); cudaMalloc(&dout, n * osize(p));
  fill_kernel<<<(unsigned)((n * 2 * D / 4 + 255) / 256), 256>>>(din, n * 2 * D / 4, 1);
  launch(p, din, dout, n); cudaDeviceSynchronize();          // warm-up
  cudaEvent_t t0, t1; cudaEventCreate(&t0); cudaEventCreate(&t1);
  cudaEventRecord(t0);
  for (int i = 0; i < reps; i++) launch(p, din, dout, n);
  cudaEventRecord(t1); cudaEventSynchronize(t1);
  float ms = 0; cudaEventElapsedTime(&ms, t0, t1);
  cudaFree(din); cudaFree(dout);
  return ms * 1e6 / ((double)n * reps);
}
API double bench_gpu_tree(int p, int log2n, int reps)    // level-by-level Merkle build over 2^log2n leaves, ns per node
{
  int D = dsize(p); size_t n = (size_t)1 << log2n;
  uint8_t *a, *b;
  cudaMalloc(&a, n * D); cudaMalloc(&b, n / 2 * D);
  fill_kernel<<<(unsigned)((n * D / 4 + 255) / 256), 256>>>(a, n * D / 4, 2);
  cudaDeviceSynchronize();
  cudaEvent_t t0, t1; cudaEventCreate(&t0); cudaEventCreate(&t1);
  cudaEventRecord(t0);
  for (int rep = 0; rep < reps; rep++)
  {
    uint8_t* src = a; uint8_t* dst = b;
    for (size_t m = n / 2; m >= 1; m /= 2)          // m parents from 2m children
    {
      launch(p, src, dst, m);
      uint8_t* t = src; src = dst; dst = t;
    }
  }
  cudaEventRecord(t1); cudaEventSynchronize(t1);
  float ms = 0; cudaEventElapsedTime(&ms, t0, t1);
  cudaFree(a); cudaFree(b);
  return ms * 1e6 / ((double)(n - 1) * reps);
}
