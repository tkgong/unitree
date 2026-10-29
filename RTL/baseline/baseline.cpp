// baseline.cpp - CPU Merkle-tree baseline on microsoft/merklecpp with the five unitree primitives.
// Built as a DLL (the machine blocks freshly built executables) and driven by run_baseline.py.
//   prim 0..4  portable C++ : sha3  sha256  chacha  aes (16-byte digests)  monolith
//   prim 5..9  optimised    : same order, prims_fast.h (AES-NI, SHA-NI, unrolled Keccak, Mersenne folds)
#include <chrono>
#include <cstdint>
#include <cstring>
#include <thread>
#include <vector>
#include "prims.h"
#include "prims_fast.h"

#define API extern "C" __declspec(dllexport)

static const char* NAMES[10] = {"SHA3-256", "SHA-256", "ChaCha20 (2 blocks)", "AES-128 DM", "Monolith-31",
                                "SHA3-256 (unrolled)", "SHA-256 (SHA-NI)", "ChaCha20 (2 blocks)", "AES-128 DM (AES-NI)", "Monolith-31 (folds)"};
static const int DSIZE[10] = {32, 32, 32, 16, 32, 32, 32, 32, 16, 32};

API const char* prim_name(int p) { return NAMES[p]; }
API int digest_size(int p) { return DSIZE[p]; }

// deterministic leaves shared with run_baseline.py: xorshift64*, every 32-bit word masked to 31 bits (P -> 0)
struct Rng
{
  uint64_t s;
  uint64_t next() { s ^= s >> 12; s ^= s << 25; s ^= s >> 27; return s * 0x2545F4914F6CDD1DULL; }
  void fill(uint8_t* p, int n)
  {
    for (int i = 0; i < n; i += 4)
    {
      uint32_t v = (uint32_t)next() & 0x7FFFFFFFu;
      if (v == 0x7FFFFFFFu) v = 0;
      p[i] = (uint8_t)v; p[i + 1] = (uint8_t)(v >> 8); p[i + 2] = (uint8_t)(v >> 16); p[i + 3] = (uint8_t)(v >> 24);
    }
  }
};

template <size_t N, void (*F)(const merkle::HashT<N>&, const merkle::HashT<N>&, merkle::HashT<N>&)>
static double tree_bench(int log2n, int root_interval, uint8_t* root_out, uint64_t seed)
{
  const size_t n = (size_t)1 << log2n;
  Rng rng{seed ? seed : 0x9E3779B97F4A7C15ULL};
  std::vector<merkle::HashT<N>> leaves(n);
  for (auto& h : leaves) rng.fill(h.bytes, (int)N);
  merkle::TreeT<N, F> t;
  auto t0 = std::chrono::high_resolution_clock::now();
  size_t j = 0;
  for (const auto& h : leaves)
  {
    t.insert(h);
    if (root_interval && (j++ % root_interval) == 0) t.root();
  }
  auto r = t.root();
  auto t1 = std::chrono::high_resolution_clock::now();
  memcpy(root_out, r.bytes, N);
  return std::chrono::duration<double>(t1 - t0).count();
}

template <size_t N, void (*F)(const merkle::HashT<N>&, const merkle::HashT<N>&, merkle::HashT<N>&)>
static double hash_bench(long long iters, uint8_t* out, uint64_t seed)
{
  merkle::HashT<N> a, b, c;
  Rng rng{seed};
  rng.fill(a.bytes, (int)N); rng.fill(b.bytes, (int)N);
  auto t0 = std::chrono::high_resolution_clock::now();
  for (long long i = 0; i < iters; i++) { F(a, b, c); b = a; a = c; }
  auto t1 = std::chrono::high_resolution_clock::now();
  if (out) memcpy(out, a.bytes, N);
  return std::chrono::duration<double>(t1 - t0).count() * 1e9 / (double)iters;   // ns per node
}

template <size_t N, void (*F)(const merkle::HashT<N>&, const merkle::HashT<N>&, merkle::HashT<N>&)>
static void one_node(const uint8_t* l, const uint8_t* r, uint8_t* out)
{
  merkle::HashT<N> a(l), b(r), c; F(a, b, c); memcpy(out, c.bytes, N);
}

template <size_t N, auto F> struct Prim { static constexpr size_t n = N; static constexpr auto f = F; };
template <class Op> static auto dispatch(int p, Op op)
{
  switch (p)
  {
    case 0: return op(Prim<32, prims::sha3_node>{});
    case 1: return op(Prim<32, merkle::sha256>{});
    case 2: return op(Prim<32, prims::chacha_node>{});
    case 3: return op(Prim<16, prims::aes_node>{});
    case 4: return op(Prim<32, prims::mono_node>{});
    case 5: return op(Prim<32, fast::sha3_node>{});
    case 6: return op(Prim<32, fast::sha256_node>{});
    case 7: return op(Prim<32, fast::chacha_node>{});
    case 8: return op(Prim<16, fast::aes_node>{});
    default: return op(Prim<32, fast::mono_node>{});
  }
}

API double bench_tree(int p, int log2n, int root_interval, uint8_t* root_out, uint64_t seed)
{
  return dispatch(p, [&](auto pr) { using Pr = decltype(pr); return tree_bench<Pr::n, Pr::f>(log2n, root_interval, root_out, seed); });
}

API double bench_hash(int p, long long iters, uint8_t* out)
{
  return dispatch(p, [&](auto pr) { using Pr = decltype(pr); return hash_bench<Pr::n, Pr::f>(iters, out, 1234567); });
}

API double bench_hash_mt(int p, long long iters, int threads)   // aggregate ns per node over all threads
{
  std::vector<std::thread> th;
  std::vector<double> ns(threads);
  auto t0 = std::chrono::high_resolution_clock::now();
  for (int t = 0; t < threads; t++)
    th.emplace_back([&, t]() {
      ns[t] = dispatch(p, [&](auto pr) { using Pr = decltype(pr); return hash_bench<Pr::n, Pr::f>(iters, nullptr, 7 + t); });
    });
  for (auto& x : th) x.join();
  auto t1 = std::chrono::high_resolution_clock::now();
  return std::chrono::duration<double>(t1 - t0).count() * 1e9 / ((double)iters * threads);
}

API void node(int p, const uint8_t* l, const uint8_t* r, uint8_t* out)   // one node function call (cross-check)
{
  dispatch(p, [&](auto pr) { using Pr = decltype(pr); one_node<Pr::n, Pr::f>(l, r, out); return 0; });
}

API void leaves(int p, int n, uint64_t seed, uint8_t* out)   // the leaves bench_tree uses, for the Python check
{
  Rng rng{seed ? seed : 0x9E3779B97F4A7C15ULL};
  for (int i = 0; i < n; i++) rng.fill(out + (size_t)i * DSIZE[p], DSIZE[p]);
}

// raw primitives for the known-answer tests
API void raw_sha3(const uint8_t* msg, int len, uint8_t* out) { prims::sha3_256(msg, len, out); }
API void raw_chacha(const uint8_t* key, uint32_t ctr, const uint8_t* nonce, uint8_t* out) { prims::chacha_block(key, ctr, nonce, out); }
API void raw_aes(const uint8_t* key, const uint8_t* in, uint8_t* out) { prims::aes128_encrypt(key, in, out); }
API void raw_aes_ni(const uint8_t* key, const uint8_t* in, uint8_t* out) { fast::aes128_encrypt(key, in, out); }
API void raw_mono(uint32_t* x) { prims::monolith_perm(x); }
API int cpu_threads() { return (int)std::thread::hardware_concurrency(); }
