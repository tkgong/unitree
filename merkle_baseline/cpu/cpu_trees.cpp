// cpu_trees.cpp - CPU baselines for the four tree workloads of the unified unit, with the node framings of
// dse/TOP/verify/compile_tree.py (merkle_fn / ggm_fn), built level by level on a persistent thread pool.
//   kind 1  BLAKE3 Merkle    parent = compress(IV, l || r, PARENT [| ROOT])[0:8]
//   kind 2  BLAKE3-XOF GGM   node   = compress(seed, [idx_lo, idx_hi, level, 0..], 64, KEYED|START|END|ROOT) -> 2 children
//   kind 3  ChaCha20 GGM     node   = ChaCha20 block(key = seed, counter = idx_lo, nonce = (idx_hi, level, 0)) -> 2 children
//   kind 4  Monolith-31 Merkle      parent = Monolith-31 permutation(l || r)[0:8]
// impl 0: library / scalar  (BLAKE3: the official C library, blake3_hash_many for parents (AVX2 x8 here) and
//                            blake3_compress_xof per GGM node; ChaCha20 / Monolith: scalar C++)
// impl 1: our 8-way structure-of-arrays kernels (AVX2 via clang -O3 -march=native), every kind but BLAKE3 Merkle
// impl 2: ChaCha20 hand-written with AVX2 intrinsics (8 nodes per register set)
// Built by build_cpu.sh into cpu_trees.dll; driven by run_cpu_trees.py (checks against the Python models, timing).
#include <cstdint>
#include <cstring>
#include <vector>
#include <thread>
#include <atomic>
#include <chrono>
#include <functional>
#include <algorithm>
#include <immintrin.h>
extern "C" {
#include "blake3_c/blake3_impl.h"
}
#define API extern "C" __declspec(dllexport)

// ---------------- persistent thread pool (spin barrier; the caller is worker 0) ----------------
struct Pool {
  int T = 1;
  std::vector<std::thread> th;
  std::atomic<uint64_t> gen{0};
  std::atomic<int> left{0};
  std::atomic<bool> quit{false};
  std::function<void(int, int)> job;
  void start(int t) {
    stop(); T = std::max(1, t); quit = false;
    const uint64_t g0 = gen.load();                    // captured here: a worker that starts late must still see the next job
    for (int i = 1; i < T; i++)
      th.emplace_back([this, i, g0] {
        uint64_t seen = g0;
        for (;;) {
          uint64_t g; int spins = 0;
          while ((g = gen.load(std::memory_order_acquire)) == seen) {   // spin briefly (back-to-back levels), then sleep
            if (quit.load(std::memory_order_relaxed)) return;
            if (++spins < 400000) _mm_pause(); else gen.wait(seen, std::memory_order_acquire);   // sleeps only after ~10 ms idle
          }
          if (quit.load(std::memory_order_relaxed)) return;
          seen = g; job(i, T); left.fetch_sub(1, std::memory_order_acq_rel);
        }
      });
  }
  void stop() { quit = true; gen.fetch_add(1); gen.notify_all(); for (auto& x : th) x.join(); th.clear(); quit = false; }
  // f(i0, i1) over [0, n): dynamic chunks (multiples of 8) taken from an atomic counter, so P-cores, their
  // hyper-threads and E-cores each take as much as they finish (a static split waits for the slowest thread)
  std::atomic<size_t> next{0};
  void par(size_t n, const std::function<void(size_t, size_t)>& f) {
    if (T == 1 || n < 16) { f(0, n); return; }
    size_t chunk = std::max<size_t>(8, ((n / ((size_t)T * 16)) + 7) & ~(size_t)7);
    next.store(0, std::memory_order_relaxed);
    job = [&](int, int) { for (;;) { size_t a = next.fetch_add(chunk, std::memory_order_relaxed); if (a >= n) break; f(a, std::min(n, a + chunk)); } };
    left.store(T - 1, std::memory_order_release);
    gen.fetch_add(1, std::memory_order_acq_rel);
    gen.notify_all();
    job(0, T);
    while (left.load(std::memory_order_acquire)) _mm_pause();
  }
};
static Pool POOL;

// ---------------- constants ----------------
static const uint32_t B3IV[8] = {0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A, 0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19};
enum { F_START = 1, F_END = 2, F_PARENT = 4, F_ROOT = 8, F_KEYED = 16 };
static const uint8_t B3PERM[16] = {2, 6, 3, 10, 7, 0, 4, 13, 1, 11, 12, 5, 9, 14, 15, 8};
static uint8_t B3SCHED[7][16];
static const uint32_t M31P = 0x7FFFFFFFu;
static const uint32_t MROW[16] = {61402, 17845, 26798, 59689, 12021, 40901, 41351, 27521, 56951, 12034, 53865, 43244, 7454, 33823, 28750, 1108};
static const uint32_t MRC[5][16] = {
#include "../mono_rc.inc"
};
static inline uint32_t rotl32(uint32_t v, int n) { return (v << n) | (v >> (32 - n)); }
static inline uint32_t rotr32(uint32_t v, int n) { return (v >> n) | (v << (32 - n)); }

// ---------------- BLAKE3 ----------------
static void b3_parents_official(const uint32_t* src, uint32_t* dst, size_t i0, size_t i1, uint8_t flags) {
  const uint8_t* ptr[64];
  for (size_t i = i0; i < i1; i += 64) {
    size_t k = std::min<size_t>(64, i1 - i);
    for (size_t j = 0; j < k; j++) ptr[j] = (const uint8_t*)(src + 16 * (i + j));
    blake3_hash_many(ptr, k, 1, B3IV, 0, false, flags, 0, 0, (uint8_t*)(dst + 8 * i));
  }
}
static void b3_ggm_official(const uint32_t* src, uint32_t* dst, size_t i0, size_t i1, uint32_t level) {
  alignas(64) uint32_t blk[16];
  for (size_t i = i0; i < i1; i++) {
    memset(blk, 0, sizeof blk); blk[0] = (uint32_t)i; blk[1] = (uint32_t)((uint64_t)i >> 32); blk[2] = level;
    blake3_compress_xof(src + 8 * i, (const uint8_t*)blk, 64, 0, F_KEYED | F_START | F_END | F_ROOT, (uint8_t*)(dst + 16 * i));
  }
}
// 8 independent compressions, structure of arrays: v[word][lane]
static inline void g8(uint32_t (&v)[16][8], int a, int b, int c, int d, const uint32_t* __restrict mx, const uint32_t* __restrict my) {
  for (int j = 0; j < 8; j++) {
    uint32_t A = v[a][j], B = v[b][j], C = v[c][j], D = v[d][j];
    A = A + B + mx[j]; D = rotr32(D ^ A, 16); C = C + D; B = rotr32(B ^ C, 12);
    A = A + B + my[j]; D = rotr32(D ^ A, 8);  C = C + D; B = rotr32(B ^ C, 7);
    v[a][j] = A; v[b][j] = B; v[c][j] = C; v[d][j] = D;
  }
}
static inline void b3_compress8_xof(const uint32_t (&cv)[8][8], const uint32_t (&m)[16][8], uint32_t flags, uint32_t (&out)[16][8]) {
  uint32_t v[16][8];
  for (int w = 0; w < 8; w++) for (int j = 0; j < 8; j++) v[w][j] = cv[w][j];
  for (int w = 0; w < 4; w++) for (int j = 0; j < 8; j++) v[8 + w][j] = B3IV[w];
  for (int j = 0; j < 8; j++) { v[12][j] = 0; v[13][j] = 0; v[14][j] = 64; v[15][j] = flags; }
  for (int r = 0; r < 7; r++) {
    const uint8_t* s = B3SCHED[r];
    g8(v, 0, 4, 8, 12, m[s[0]], m[s[1]]);   g8(v, 1, 5, 9, 13, m[s[2]], m[s[3]]);
    g8(v, 2, 6, 10, 14, m[s[4]], m[s[5]]);  g8(v, 3, 7, 11, 15, m[s[6]], m[s[7]]);
    g8(v, 0, 5, 10, 15, m[s[8]], m[s[9]]);  g8(v, 1, 6, 11, 12, m[s[10]], m[s[11]]);
    g8(v, 2, 7, 8, 13, m[s[12]], m[s[13]]); g8(v, 3, 4, 9, 14, m[s[14]], m[s[15]]);
  }
  for (int w = 0; w < 8; w++) for (int j = 0; j < 8; j++) { out[w][j] = v[w][j] ^ v[w + 8][j]; out[w + 8][j] = v[w + 8][j] ^ cv[w][j]; }
}
static void b3_ggm_simd(const uint32_t* src, uint32_t* dst, size_t i0, size_t i1, uint32_t level) {
  alignas(64) uint32_t cv[8][8], m[16][8], o[16][8];
  memset(m, 0, sizeof m);
  for (size_t i = i0; i < i1; i += 8) {
    size_t k = std::min<size_t>(8, i1 - i);
    for (size_t j = 0; j < 8; j++) {
      size_t n = i + (j < k ? j : 0);
      for (int w = 0; w < 8; w++) cv[w][j] = src[8 * n + w];
      m[0][j] = (uint32_t)(i + j); m[1][j] = (uint32_t)((uint64_t)(i + j) >> 32); m[2][j] = level;
    }
    b3_compress8_xof(cv, m, F_KEYED | F_START | F_END | F_ROOT, o);
    for (size_t j = 0; j < k; j++) for (int w = 0; w < 16; w++) dst[16 * (i + j) + w] = o[w][j];
  }
}

// ---------------- ChaCha20 ----------------
#define QR1(a, b, c, d) a += b; d = rotl32(d ^ a, 16); c += d; b = rotl32(b ^ c, 12); a += b; d = rotl32(d ^ a, 8); c += d; b = rotl32(b ^ c, 7);
static inline void chacha_block1(const uint32_t* key, uint32_t ctr, uint32_t n0, uint32_t n1, uint32_t n2, uint32_t* out) {
  uint32_t s[16] = {0x61707865, 0x3320646e, 0x79622d32, 0x6b206574, key[0], key[1], key[2], key[3], key[4], key[5], key[6], key[7], ctr, n0, n1, n2};
  uint32_t x[16]; memcpy(x, s, sizeof s);
  for (int r = 0; r < 10; r++) {
    QR1(x[0], x[4], x[8], x[12]) QR1(x[1], x[5], x[9], x[13]) QR1(x[2], x[6], x[10], x[14]) QR1(x[3], x[7], x[11], x[15])
    QR1(x[0], x[5], x[10], x[15]) QR1(x[1], x[6], x[11], x[12]) QR1(x[2], x[7], x[8], x[13]) QR1(x[3], x[4], x[9], x[14])
  }
  for (int i = 0; i < 16; i++) out[i] = x[i] + s[i];
}
static void cc_ggm_scalar(const uint32_t* src, uint32_t* dst, size_t i0, size_t i1, uint32_t level) {
  for (size_t i = i0; i < i1; i++) chacha_block1(src + 8 * i, (uint32_t)i, (uint32_t)((uint64_t)i >> 32), level, 0, dst + 16 * i);
}
static inline void qr8(uint32_t* __restrict a, uint32_t* __restrict b, uint32_t* __restrict c, uint32_t* __restrict d) {
  for (int j = 0; j < 8; j++) {
    uint32_t A = a[j], B = b[j], C = c[j], D = d[j];
    A += B; D = rotl32(D ^ A, 16); C += D; B = rotl32(B ^ C, 12);
    A += B; D = rotl32(D ^ A, 8);  C += D; B = rotl32(B ^ C, 7);
    a[j] = A; b[j] = B; c[j] = C; d[j] = D;
  }
}
static void cc_ggm_simd(const uint32_t* src, uint32_t* dst, size_t i0, size_t i1, uint32_t level) {
  alignas(64) uint32_t s[16][8], x[16][8];
  static const uint32_t C4[4] = {0x61707865, 0x3320646e, 0x79622d32, 0x6b206574};
  for (size_t i = i0; i < i1; i += 8) {
    size_t k = std::min<size_t>(8, i1 - i);
    for (size_t j = 0; j < 8; j++) {
      size_t n = i + (j < k ? j : 0);
      for (int w = 0; w < 4; w++) s[w][j] = C4[w];
      for (int w = 0; w < 8; w++) s[4 + w][j] = src[8 * n + w];
      s[12][j] = (uint32_t)(i + j); s[13][j] = (uint32_t)((uint64_t)(i + j) >> 32); s[14][j] = level; s[15][j] = 0;
    }
    memcpy(x, s, sizeof s);
    for (int r = 0; r < 10; r++) {
      qr8(x[0], x[4], x[8], x[12]); qr8(x[1], x[5], x[9], x[13]); qr8(x[2], x[6], x[10], x[14]); qr8(x[3], x[7], x[11], x[15]);
      qr8(x[0], x[5], x[10], x[15]); qr8(x[1], x[6], x[11], x[12]); qr8(x[2], x[7], x[8], x[13]); qr8(x[3], x[4], x[9], x[14]);
    }
    for (size_t j = 0; j < k; j++) for (int w = 0; w < 16; w++) dst[16 * (i + j) + w] = x[w][j] + s[w][j];
  }
}

// impl 2: hand-written AVX2, 8 nodes in the 8 lanes; rotations by 16 / 8 as byte shuffles, 12 / 7 as shift + or
static inline __m256i rotv(__m256i v, int n) { return _mm256_or_si256(_mm256_slli_epi32(v, n), _mm256_srli_epi32(v, 32 - n)); }
static inline __m256i rot16v(__m256i v) {
  const __m256i m = _mm256_setr_epi8(2, 3, 0, 1, 6, 7, 4, 5, 10, 11, 8, 9, 14, 15, 12, 13, 2, 3, 0, 1, 6, 7, 4, 5, 10, 11, 8, 9, 14, 15, 12, 13);
  return _mm256_shuffle_epi8(v, m);
}
static inline __m256i rot8v(__m256i v) {
  const __m256i m = _mm256_setr_epi8(3, 0, 1, 2, 7, 4, 5, 6, 11, 8, 9, 10, 15, 12, 13, 14, 3, 0, 1, 2, 7, 4, 5, 6, 11, 8, 9, 10, 15, 12, 13, 14);
  return _mm256_shuffle_epi8(v, m);
}
#define QRV(a, b, c, d) a = _mm256_add_epi32(a, b); d = rot16v(_mm256_xor_si256(d, a)); c = _mm256_add_epi32(c, d); b = rotv(_mm256_xor_si256(b, c), 12); \
                        a = _mm256_add_epi32(a, b); d = rot8v(_mm256_xor_si256(d, a));  c = _mm256_add_epi32(c, d); b = rotv(_mm256_xor_si256(b, c), 7);
static inline void transpose8(__m256i r[8]) {          // 8x8 32-bit transpose
  __m256i t0 = _mm256_unpacklo_epi32(r[0], r[1]), t1 = _mm256_unpackhi_epi32(r[0], r[1]), t2 = _mm256_unpacklo_epi32(r[2], r[3]), t3 = _mm256_unpackhi_epi32(r[2], r[3]);
  __m256i t4 = _mm256_unpacklo_epi32(r[4], r[5]), t5 = _mm256_unpackhi_epi32(r[4], r[5]), t6 = _mm256_unpacklo_epi32(r[6], r[7]), t7 = _mm256_unpackhi_epi32(r[6], r[7]);
  __m256i u0 = _mm256_unpacklo_epi64(t0, t2), u1 = _mm256_unpackhi_epi64(t0, t2), u2 = _mm256_unpacklo_epi64(t1, t3), u3 = _mm256_unpackhi_epi64(t1, t3);
  __m256i u4 = _mm256_unpacklo_epi64(t4, t6), u5 = _mm256_unpackhi_epi64(t4, t6), u6 = _mm256_unpacklo_epi64(t5, t7), u7 = _mm256_unpackhi_epi64(t5, t7);
  r[0] = _mm256_permute2x128_si256(u0, u4, 0x20); r[1] = _mm256_permute2x128_si256(u1, u5, 0x20);
  r[2] = _mm256_permute2x128_si256(u2, u6, 0x20); r[3] = _mm256_permute2x128_si256(u3, u7, 0x20);
  r[4] = _mm256_permute2x128_si256(u0, u4, 0x31); r[5] = _mm256_permute2x128_si256(u1, u5, 0x31);
  r[6] = _mm256_permute2x128_si256(u2, u6, 0x31); r[7] = _mm256_permute2x128_si256(u3, u7, 0x31);
}
static void cc_ggm_avx2(const uint32_t* src, uint32_t* dst, size_t i0, size_t i1, uint32_t level) {
  alignas(32) uint32_t tail[16 * 8];
  for (size_t i = i0; i < i1; i += 8) {
    size_t k = std::min<size_t>(8, i1 - i);
    __m256i key[8];
    if (k == 8) { for (int j = 0; j < 8; j++) key[j] = _mm256_loadu_si256((const __m256i*)(src + 8 * (i + j))); }
    else { for (size_t j = 0; j < 8; j++) key[j] = _mm256_loadu_si256((const __m256i*)(src + 8 * (i + (j < k ? j : 0)))); }
    transpose8(key);                                    // key[w] = word w of the 8 seeds
    __m256i idx = _mm256_add_epi32(_mm256_set1_epi32((int)(uint32_t)i), _mm256_setr_epi32(0, 1, 2, 3, 4, 5, 6, 7));
    __m256i s[16] = {_mm256_set1_epi32(0x61707865), _mm256_set1_epi32(0x3320646e), _mm256_set1_epi32(0x79622d32), _mm256_set1_epi32(0x6b206574),
                     key[0], key[1], key[2], key[3], key[4], key[5], key[6], key[7],
                     idx, _mm256_set1_epi32((int)(uint32_t)((uint64_t)i >> 32)), _mm256_set1_epi32((int)level), _mm256_setzero_si256()};
    __m256i x[16];
    for (int w = 0; w < 16; w++) x[w] = s[w];
    for (int r = 0; r < 10; r++) {
      QRV(x[0], x[4], x[8], x[12]) QRV(x[1], x[5], x[9], x[13]) QRV(x[2], x[6], x[10], x[14]) QRV(x[3], x[7], x[11], x[15])
      QRV(x[0], x[5], x[10], x[15]) QRV(x[1], x[6], x[11], x[12]) QRV(x[2], x[7], x[8], x[13]) QRV(x[3], x[4], x[9], x[14])
    }
    for (int w = 0; w < 16; w++) x[w] = _mm256_add_epi32(x[w], s[w]);
    transpose8(x); transpose8(x + 8);                    // x[j] = words 0..7 of node j, x[8 + j] = words 8..15
    uint32_t* o = (k == 8) ? dst + 16 * i : tail;
    for (int j = 0; j < 8; j++) { _mm256_storeu_si256((__m256i*)(o + 16 * j), x[j]); _mm256_storeu_si256((__m256i*)(o + 16 * j + 8), x[8 + j]); }
    if (k < 8) memcpy(dst + 16 * i, tail, k * 64);
  }
}

// ---------------- Monolith-31 ----------------
static inline uint32_t fold62(uint64_t v) {
  uint64_t r = (v & M31P) + (v >> 31);
  r = (r & M31P) + (r >> 31);
  return r == M31P ? 0 : (uint32_t)r;
}
static inline uint32_t bar31(uint32_t x) {          // chunks 8 | 8 | 8 | 7 bits; the 7-bit chunk has two rotations
  uint32_t lo = x & 0x00FFFFFFu, top = (x >> 24) & 0x7F;
  // byte-wise rotations of the three low chunks (SWAR)
  auto rb = [](uint32_t v, int k) { return ((v << k) & (0x00FFFFFFu & (0x010101u * ((0xFFu << k) & 0xFFu)))) | ((v >> (8 - k)) & (0x010101u * (0xFFu >> (8 - k)))); };
  uint32_t nlo = ~lo & 0x00FFFFFFu;
  uint32_t t = lo ^ (rb(nlo, 1) & rb(lo, 2) & rb(lo, 3));
  t = rb(t, 1);
  uint32_t r1 = ((~top << 1) | ((~top & 0x7F) >> 6)) & 0x7F, r2 = ((top << 2) | (top >> 5)) & 0x7F;
  uint32_t u = (top ^ (r1 & r2)) & 0x7F;
  u = ((u << 1) | (u >> 6)) & 0x7F;
  return t | (u << 24);
}
static inline void mono_perm1(uint32_t x[16]) {
  auto concrete = [](uint32_t* x) {
    uint32_t y[16];
    for (int i = 0; i < 16; i++) { uint64_t acc = 0; for (int k = 0; k < 16; k++) acc += (uint64_t)MROW[k] * x[(i + k) & 15]; y[i] = fold62(acc); }
    memcpy(x, y, sizeof y);
  };
  concrete(x);
  for (int r = 0; r < 6; r++) {
    for (int i = 0; i < 8; i++) x[i] = bar31(x[i]);
    for (int i = 15; i >= 1; i--) x[i] = fold62(x[i] + (uint64_t)x[i - 1] * x[i - 1]);
    concrete(x);
    if (r < 5) for (int i = 0; i < 16; i++) { uint32_t v = x[i] + MRC[r][i]; x[i] = v >= M31P ? v - M31P : v; }
  }
}
static void mono_parents_scalar(const uint32_t* src, uint32_t* dst, size_t i0, size_t i1) {
  uint32_t x[16];
  for (size_t i = i0; i < i1; i++) { memcpy(x, src + 16 * i, 64); mono_perm1(x); memcpy(dst + 8 * i, x, 32); }
}
static inline void mono_perm8(uint32_t (&x)[16][8]) {
  uint32_t y[16][8];
  auto concrete = [&]() {
    for (int i = 0; i < 16; i++) {
      uint64_t acc[8] = {0, 0, 0, 0, 0, 0, 0, 0};
      for (int k = 0; k < 16; k++) { const uint32_t* xr = x[(i + k) & 15]; uint64_t c = MROW[k]; for (int j = 0; j < 8; j++) acc[j] += c * xr[j]; }
      for (int j = 0; j < 8; j++) y[i][j] = fold62(acc[j]);
    }
    memcpy(x, y, sizeof y);
  };
  concrete();
  for (int r = 0; r < 6; r++) {
    for (int i = 0; i < 8; i++) for (int j = 0; j < 8; j++) x[i][j] = bar31(x[i][j]);
    for (int i = 15; i >= 1; i--) for (int j = 0; j < 8; j++) x[i][j] = fold62(x[i][j] + (uint64_t)x[i - 1][j] * x[i - 1][j]);
    concrete();
    if (r < 5) for (int i = 0; i < 16; i++) for (int j = 0; j < 8; j++) { uint32_t v = x[i][j] + MRC[r][i]; x[i][j] = v >= M31P ? v - M31P : v; }
  }
}
static void mono_parents_simd(const uint32_t* src, uint32_t* dst, size_t i0, size_t i1) {
  alignas(64) uint32_t x[16][8];
  for (size_t i = i0; i < i1; i += 8) {
    size_t k = std::min<size_t>(8, i1 - i);
    for (size_t j = 0; j < 8; j++) { size_t n = i + (j < k ? j : 0); for (int w = 0; w < 16; w++) x[w][j] = src[16 * n + w]; }
    mono_perm8(x);
    for (size_t j = 0; j < k; j++) for (int w = 0; w < 8; w++) dst[8 * (i + j) + w] = x[w][j];
  }
}

// ---------------- trees ----------------
static void merkle_level(int kind, int impl, const uint32_t* src, uint32_t* dst, size_t m) {
  bool root = (m == 1);
  POOL.par(m, [&](size_t a, size_t b) {
    if (kind == 1) b3_parents_official(src, dst, a, b, (uint8_t)(F_PARENT | (root ? F_ROOT : 0)));
    else if (impl == 1) mono_parents_simd(src, dst, a, b);
    else mono_parents_scalar(src, dst, a, b);
  });
}
static void ggm_level(int kind, int impl, const uint32_t* src, uint32_t* dst, size_t m, uint32_t level) {
  POOL.par(m, [&](size_t a, size_t b) {
    if (kind == 2) { if (impl == 1) b3_ggm_simd(src, dst, a, b, level); else b3_ggm_official(src, dst, a, b, level); }
    else { if (impl == 2) cc_ggm_avx2(src, dst, a, b, level); else if (impl == 1) cc_ggm_simd(src, dst, a, b, level); else cc_ggm_scalar(src, dst, a, b, level); }
  });
}
static uint64_t xs_state;
static inline uint32_t xs31() { xs_state ^= xs_state >> 12; xs_state ^= xs_state << 25; xs_state ^= xs_state >> 27; return (uint32_t)((xs_state * 0x2545F4914F6CDD1DULL) >> 33) & 0x7FFFFFFFu; }

API void cpu_init(int threads) {
  for (int k = 0; k < 16; k++) B3SCHED[0][k] = (uint8_t)k;
  for (int r = 1; r < 7; r++) for (int k = 0; k < 16; k++) B3SCHED[r][k] = B3SCHED[r - 1][B3PERM[k]];
  POOL.start(threads);
}
API void cpu_stop() { POOL.stop(); }
API int cpu_b3_simd_degree() { return (int)blake3_simd_degree(); }   // parallel inputs per blake3_hash_many call (AVX2: 8)

// Build one tree. Merkle: in = 2^log2 leaves (8 words each, or NULL for generated leaves), out = root (8 words).
// GGM: in = root seed (8 words, or NULL), out = 2^log2 leaves (8 words each, or NULL). Returns ns per node, averaged
// over reps (buffers allocated and inputs generated before the clock starts).
API double cpu_tree(int kind, int impl, int log2, int reps, const uint32_t* in, uint32_t* out) {
  size_t n = (size_t)1 << log2;
  std::vector<uint32_t> a(n * 8, 0), b(n * 8, 0);              // both buffers touched before the clock
  xs_state = 0x9E3779B97F4A7C15ULL ^ (uint64_t)log2;
  bool merkle = (kind == 1 || kind == 4);
  std::vector<uint32_t> start(merkle ? n * 8 : 8);
  if (in) memcpy(start.data(), in, start.size() * 4); else for (auto& v : start) v = xs31();
  double ns = 0;
  for (int rep = 0; rep < reps; rep++) {
    memcpy(a.data(), start.data(), start.size() * 4);            // inputs restored outside the clock
    uint32_t* src = a.data(); uint32_t* dst = b.data();
    auto t0 = std::chrono::steady_clock::now();
    if (merkle) for (size_t m = n / 2; m >= 1; m /= 2) { merkle_level(kind, impl, src, dst, m); std::swap(src, dst); }
    else for (int lv = 0; lv < log2; lv++) { ggm_level(kind, impl, src, dst, (size_t)1 << lv, (uint32_t)lv); std::swap(src, dst); }
    auto t1 = std::chrono::steady_clock::now();
    ns += std::chrono::duration<double, std::nano>(t1 - t0).count();
    if (out && rep == reps - 1) memcpy(out, src, merkle ? 32 : n * 32);
  }
  return ns / ((double)(n - 1) * reps);
}
API void cpu_mono_perm(const uint32_t* in, uint32_t* out) { uint32_t x[16]; memcpy(x, in, 64); mono_perm1(x); memcpy(out, x, 64); }
