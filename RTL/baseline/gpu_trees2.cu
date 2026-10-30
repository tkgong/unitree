// gpu_trees2.cu - the four tree workloads on the GPU with the optimisations a tuned baseline should have:
//   * T independent trees per program (batch), one launch per level covering all trees;
//   * fused small levels: the top of a Merkle tree (<= 256 parents per tree) and the head of a GGM tree (<= 256 nodes
//     per level) run in ONE launch, one CTA per tree, in shared memory (cuts 8-9 launches per tree);
//   * Monolith-31 with 32-bit operands for the MDS products (IMAD.WIDE) and word loads instead of byte copies.
// Same node framings as gpu_trees.cu / dse/TOP/verify/compile_tree.py. Built by build_gpu_trees2.sh, driven by run_gpu_trees2.py.
//   kind 1 BLAKE3 Merkle   kind 2 BLAKE3-XOF GGM   kind 3 ChaCha20 GGM   kind 4 Monolith-31 Merkle
#include "gpu_prims.cu"

#define FUSE 256                                    // threads (= nodes per level per tree) of a fused CTA
__constant__ uint32_t MROW32[16] = {61402, 17845, 26798, 59689, 12021, 40901, 41351, 27521, 56951, 12034, 53865, 43244, 7454, 33823, 28750, 1108};

__device__ __forceinline__ void concrete_opt(uint32_t x[16])
{
  uint32_t y[16];
#pragma unroll
  for (int i = 0; i < 16; i++)
  {
    uint64_t acc = 0;
#pragma unroll
    for (int k = 0; k < 16; k++) acc += (uint64_t)MROW32[k] * x[(i + k) & 15];      // 32 x 32 -> 64: one IMAD.WIDE
    y[i] = fold62(acc);
  }
#pragma unroll
  for (int i = 0; i < 16; i++) x[i] = y[i];
}
__device__ __forceinline__ void monolith_perm_opt(uint32_t x[16])
{
  concrete_opt(x);
#pragma unroll 1
  for (int k = 0; k < 6; k++)
  {
#pragma unroll
    for (int i = 0; i < 8; i++) x[i] = bar31(x[i]);
#pragma unroll
    for (int i = 15; i >= 1; i--) x[i] = fold62(x[i] + (uint64_t)x[i - 1] * x[i - 1]);
    concrete_opt(x);
    if (k < 5)
#pragma unroll
      for (int i = 0; i < 16; i++) { uint32_t v = x[i] + MRC_C[k][i]; x[i] = v >= M31P ? v - M31P : v; }
  }
}

// ---------------- Poseidon2-M31 (Plonky3 width 16: x^5, 4 + 14 + 4 rounds; constants from pos2_rc.inc) ----------------
#include "pos2_rc.inc"
__constant__ uint32_t P2E_C[8][16] = P2_RC_EXT_INIT;
__constant__ uint32_t P2I_C[14] = P2_RC_INT_INIT;
__constant__ int P2S_C[15] = P2_SHIFTS_INIT;
__device__ __forceinline__ uint32_t p2_sbox(uint32_t x)
{
  uint32_t x2 = fold62((uint64_t)x * x), x4 = fold62((uint64_t)x2 * x2);
  return fold62((uint64_t)x4 * x);
}
__device__ __forceinline__ void p2_ext(uint32_t x[16])
{
  uint32_t m[16];
#pragma unroll
  for (int c = 0; c < 4; c++)
  {
    uint64_t a = x[4 * c], b = x[4 * c + 1], cc = x[4 * c + 2], d = x[4 * c + 3];
    uint64_t t01 = a + b, t23 = cc + d, t0123 = t01 + t23, t01123 = t0123 + b, t01233 = t0123 + d;
    m[4 * c] = fold62(t01123 + t01); m[4 * c + 1] = fold62(t01123 + 2 * cc); m[4 * c + 2] = fold62(t01233 + t23); m[4 * c + 3] = fold62(t01233 + 2 * a);
  }
  uint64_t s[4];
#pragma unroll
  for (int j = 0; j < 4; j++) s[j] = (uint64_t)m[j] + m[4 + j] + m[8 + j] + m[12 + j];
#pragma unroll
  for (int i = 0; i < 16; i++) x[i] = fold62((uint64_t)m[i] + s[i & 3]);
}
__device__ __forceinline__ void p2_int(uint32_t x[16])
{
  uint64_t part = 0;
#pragma unroll
  for (int i = 1; i < 16; i++) part += x[i];
  uint64_t full = part + x[0];
  uint32_t y0 = fold62(part + (M31P - x[0]));
#pragma unroll
  for (int i = 1; i < 16; i++) x[i] = fold62(full + ((uint64_t)x[i] << P2S_C[i - 1]));
  x[0] = y0;
}
__device__ void pos2_perm(uint32_t x[16])
{
  p2_ext(x);
#pragma unroll 1
  for (int r = 0; r < 4; r++) {
#pragma unroll
    for (int i = 0; i < 16; i++) x[i] = p2_sbox(fold62((uint64_t)x[i] + P2E_C[r][i]));
    p2_ext(x); }
#pragma unroll 1
  for (int r = 0; r < 14; r++) { x[0] = p2_sbox(fold62((uint64_t)x[0] + P2I_C[r])); p2_int(x); }
#pragma unroll 1
  for (int r = 4; r < 8; r++) {
#pragma unroll
    for (int i = 0; i < 16; i++) x[i] = p2_sbox(fold62((uint64_t)x[i] + P2E_C[r][i]));
    p2_ext(x); }
}

// one Merkle parent: 16 words (left || right) -> 8 words
template <int K, bool OPT>
__device__ __forceinline__ void merkle_node(const uint32_t* in, uint32_t* out, uint32_t flags)
{
  uint32_t x[16];
#pragma unroll
  for (int k = 0; k < 16; k++) x[k] = in[k];
  if (K == 1) { uint32_t o[16]; b3_compress(B3IV, x, 64, flags, o);
#pragma unroll
    for (int k = 0; k < 8; k++) out[k] = o[k]; }
  else if (K == 5) { pos2_perm(x);
#pragma unroll
    for (int k = 0; k < 8; k++) out[k] = x[k]; }
  else { if (OPT) monolith_perm_opt(x); else monolith_perm(x);
#pragma unroll
    for (int k = 0; k < 8; k++) out[k] = x[k]; }
}
// one GGM node: seed (8 words), index within its level, level -> 16 words (children 2i, 2i+1)
template <int K>
__device__ __forceinline__ void ggm_node(const uint32_t* seed_in, uint64_t idx, uint32_t level, uint32_t* out)
{
  uint32_t seed[8], o[16];
#pragma unroll
  for (int k = 0; k < 8; k++) seed[k] = seed_in[k];
  if (K == 2) { uint32_t blk[16] = {(uint32_t)idx, (uint32_t)(idx >> 32), level, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
                b3_compress(seed, blk, 64, 16 | 1 | 2 | 8, o); }
  else { uint32_t nonce[3] = {(uint32_t)(idx >> 32), level, 0}; chacha_block(seed, (uint32_t)idx, nonce, o); }
#pragma unroll
  for (int k = 0; k < 16; k++) out[k] = o[k];
}

// ---------------- per-level kernels over all T trees (concatenated layout) ----------------
// Merkle level: T*m parents; parent i reads children 2i, 2i+1 (tree t's children are [2tm, 2tm+2m)).
template <int K, bool OPT>
__global__ void merkle_level_k(const uint32_t* __restrict__ in, uint32_t* __restrict__ out, size_t n, uint32_t flags)
{
  size_t i = (size_t)blockIdx.x * blockDim.x + threadIdx.x;
  if (i < n) merkle_node<K, OPT>(in + 16 * i, out + 8 * i, flags);
}
// GGM level: T * 2^lv nodes; node i of tree t = i >> lv has index j = i & mask; children at 2i, 2i+1.
template <int K>
__global__ void ggm_level_k(const uint32_t* __restrict__ in, uint32_t* __restrict__ out, size_t n, uint32_t level, uint64_t mask)
{
  size_t i = (size_t)blockIdx.x * blockDim.x + threadIdx.x;
  if (i < n) ggm_node<K>(in + 8 * i, i & mask, level, out + 16 * i);
}
// ---------------- fused kernels: one CTA per tree, shared memory ----------------
// Merkle top: tree t has 2m children (m <= FUSE parents) at in + 16tm; computes every level down to the root.
template <int K, bool OPT>
__global__ void __launch_bounds__(FUSE) merkle_top_k(const uint32_t* __restrict__ in, uint32_t* __restrict__ roots, uint32_t m)
{
  __shared__ uint32_t s[2][2 * FUSE * 8];
  const uint32_t t = blockIdx.x, tid = threadIdx.x;
  for (uint32_t w = tid; w < 16 * m; w += blockDim.x) s[0][w] = in[(size_t)16 * m * t + w];
  __syncthreads();
  int cur = 0;
  for (uint32_t mm = m; mm >= 1; mm >>= 1)
  {
    if (tid < mm) merkle_node<K, OPT>(&s[cur][16 * tid], &s[cur ^ 1][8 * tid], mm == 1 ? (4 | 8) : 4);
    __syncthreads();
    cur ^= 1;
  }
  if (tid < 8) roots[8 * t + tid] = s[cur][tid];
}
// GGM head: tree t from its seed through levels 0 .. H-1 (2^(H-1) <= FUSE); writes the 2^H nodes of level H at out + 8 * 2^H * t.
template <int K>
__global__ void __launch_bounds__(FUSE) ggm_head_k(const uint32_t* __restrict__ seeds, uint32_t* __restrict__ out, int H)
{
  __shared__ uint32_t s[2][2 * FUSE * 8];
  const uint32_t t = blockIdx.x, tid = threadIdx.x;
  if (tid < 8) s[0][tid] = seeds[8 * t + tid];
  __syncthreads();
  int cur = 0;
  for (int lv = 0; lv < H; lv++)
  {
    if (tid < (1u << lv)) ggm_node<K>(&s[cur][8 * tid], tid, (uint32_t)lv, &s[cur ^ 1][16 * tid]);
    __syncthreads();
    cur ^= 1;
  }
  for (uint32_t w = tid; w < 8u << H; w += blockDim.x) out[((size_t)8 << H) * t + w] = s[cur][w];
}

static inline unsigned nblk(size_t n) { return (unsigned)((n + 255) / 256); }
static inline bool is_merkle(int kind) { return kind == 1 || kind == 4 || kind == 5; }
static void merkle_launch(int kind, bool opt, const uint32_t* in, uint32_t* out, size_t n, uint32_t flags)
{
  if (kind == 1) merkle_level_k<1, false><<<nblk(n), 256>>>(in, out, n, flags);
  else if (kind == 5) merkle_level_k<5, false><<<nblk(n), 256>>>(in, out, n, flags);
  else if (opt) merkle_level_k<4, true><<<nblk(n), 256>>>(in, out, n, flags);
  else merkle_level_k<4, false><<<nblk(n), 256>>>(in, out, n, flags);
}
static void merkle_top_launch(int kind, bool opt, const uint32_t* in, uint32_t* roots, int T, uint32_t m)
{
  unsigned th = m < 32 ? 32 : m;
  if (kind == 1) merkle_top_k<1, false><<<T, th>>>(in, roots, m);
  else if (kind == 5) merkle_top_k<5, false><<<T, th>>>(in, roots, m);
  else if (opt) merkle_top_k<4, true><<<T, th>>>(in, roots, m);
  else merkle_top_k<4, false><<<T, th>>>(in, roots, m);
}

// One program: T trees of 2^L leaves. Merkle: a = leaves (T * 2^L * 8 words) -> roots[T * 8]. GGM: a[0 .. 8T) = seeds ->
// leaves in the returned buffer. fuse: run the top (Merkle) / head (GGM) in one launch per program.
static uint32_t* run_tree(int kind, bool opt, bool fuse, int L, int T, uint32_t* a, uint32_t* b, uint32_t* roots)
{
  size_t n = (size_t)1 << L;
  uint32_t* src = a; uint32_t* dst = b;
  if (is_merkle(kind))
  {
    size_t m = n / 2;
    for (; m >= 1; m /= 2)
    {
      if (fuse && m <= FUSE) { merkle_top_launch(kind, opt, src, roots, T, (uint32_t)m); return roots; }
      merkle_launch(kind, opt, src, dst, m * T, m == 1 ? (4 | 8) : 4);
      uint32_t* x = src; src = dst; dst = x;
    }
    cudaMemcpyAsync(roots, src, (size_t)T * 32, cudaMemcpyDeviceToDevice);
    return roots;
  }
  int lv = 0;
  if (fuse)
  {
    int H = 1; while (H < L && (1 << H) <= FUSE) H++;   // levels 0 .. H-1 have <= FUSE nodes
    if (H > L) H = L;
    if (kind == 2) ggm_head_k<2><<<T, FUSE>>>(src, dst, H); else ggm_head_k<3><<<T, FUSE>>>(src, dst, H);
    lv = H; uint32_t* x = src; src = dst; dst = x;
  }
  for (; lv < L; lv++)
  {
    size_t nn = ((size_t)T) << lv; uint64_t mask = (1ull << lv) - 1;
    if (kind == 2) ggm_level_k<2><<<nblk(nn), 256>>>(src, dst, nn, (uint32_t)lv, mask);
    else ggm_level_k<3><<<nblk(nn), 256>>>(src, dst, nn, (uint32_t)lv, mask);
    uint32_t* x = src; src = dst; dst = x;
  }
  return src;
}

// correctness: in = T*2^L leaves (Merkle) or T seeds (GGM); out = T roots (Merkle) or T*2^L leaves (GGM)
API int tree2_run(int kind, int opt, int fuse, int L, int T, const uint32_t* in, uint32_t* out)
{
  size_t n = (size_t)1 << L, words = (size_t)T * n * 8;
  uint32_t *a, *b, *r;
  cudaMalloc(&a, words * 4); cudaMalloc(&b, words * 4); cudaMalloc(&r, (size_t)T * 32);
  bool merkle = is_merkle(kind);
  cudaMemcpy(a, in, merkle ? words * 4 : (size_t)T * 32, cudaMemcpyHostToDevice);
  uint32_t* res = run_tree(kind, opt != 0, fuse != 0, L, T, a, b, r);
  cudaError_t e = cudaDeviceSynchronize();
  cudaMemcpy(out, res, merkle ? (size_t)T * 32 : words * 4, cudaMemcpyDeviceToHost);
  cudaFree(a); cudaFree(b); cudaFree(r);
  return e == cudaSuccess ? 0 : (int)e;
}

// timing: ns per node (kernel time of the whole program / (T * (2^L - 1)) / reps); *pcie_ms = host<->device copy of the
// leaves of the program over PCIe from pinned memory (Merkle: host -> device; GGM: device -> host), one direction.
API double tree2_bench(int kind, int opt, int fuse, int L, int T, int reps, double* pcie_ms)
{
  size_t n = (size_t)1 << L, words = (size_t)T * n * 8;
  uint32_t *a, *b, *r, *h;
  if (cudaMalloc(&a, words * 4) != cudaSuccess || cudaMalloc(&b, words * 4) != cudaSuccess) return -1.0;
  cudaMalloc(&r, (size_t)T * 32);
  bool merkle = is_merkle(kind);
  fill_kernel<<<(unsigned)((words + 255) / 256), 256>>>((uint8_t*)a, words, 2);
  cudaDeviceSynchronize();
  run_tree(kind, opt != 0, fuse != 0, L, T, a, b, r);                       // warm-up
  if (!merkle) fill_kernel<<<1, 256>>>((uint8_t*)a, (size_t)T * 8, 3);
  cudaDeviceSynchronize();
  cudaEvent_t t0, t1; cudaEventCreate(&t0); cudaEventCreate(&t1);
  cudaEventRecord(t0);
  for (int rep = 0; rep < reps; rep++) run_tree(kind, opt != 0, fuse != 0, L, T, a, b, r);
  cudaEventRecord(t1); cudaEventSynchronize(t1);
  float ms = 0; cudaEventElapsedTime(&ms, t0, t1);
  cudaError_t e = cudaGetLastError();
  if (pcie_ms)
  {
    cudaMallocHost(&h, words * 4);
    float c = 0; cudaEventRecord(t0);
    if (merkle) cudaMemcpy(a, h, words * 4, cudaMemcpyHostToDevice); else cudaMemcpy(h, b, words * 4, cudaMemcpyDeviceToHost);
    cudaEventRecord(t1); cudaEventSynchronize(t1); cudaEventElapsedTime(&c, t0, t1);
    *pcie_ms = c; cudaFreeHost(h);
  }
  cudaFree(a); cudaFree(b); cudaFree(r);
  if (e != cudaSuccess) return -2.0;
  return ms * 1e6 / ((double)(n - 1) * T * reps);
}

// ---------------- opening: T trees stored with every level (device resident), gather of the opened nodes ----------------
// open_build: T trees from in (Merkle: T * 2^L leaves; GGM: T root seeds), every level kept: level l (Merkle: above the
// leaves; GGM: lam, 0 = leaves) at word offset g_off[l], the T trees' 2^(L-l) nodes each concatenated (tree-major). Not timed.
// open_bench: gather n nodes given as word offsets / 8 (the caller computes them: memsim/open18.py), one thread per 16 B,
// the output in list order; kernel time over reps -> ns per call; out_host gets the last gather.
static uint32_t* g_store = nullptr; static std::vector<size_t> g_off;
API int open_build(int kind, int L, int T, const uint32_t* in)
{
  size_t n = (size_t)1 << L; g_off.assign(L + 1, 0); size_t tot = 0;
  for (int l = 0; l <= L; l++) { g_off[l] = tot; tot += (size_t)T * (n >> l) * 8; }
  if (g_store) cudaFree(g_store);
  if (cudaMalloc(&g_store, tot * 4) != cudaSuccess) return -1;
  if (is_merkle(kind))
  {
    cudaMemcpy(g_store + g_off[0], in, (size_t)T * n * 32, cudaMemcpyHostToDevice);
    for (int l = 1; l <= L; l++) merkle_launch(kind, true, g_store + g_off[l - 1], g_store + g_off[l], (size_t)T * (n >> l), l == L ? (4 | 8) : 4);
  }
  else
  {
    cudaMemcpy(g_store + g_off[L], in, (size_t)T * 32, cudaMemcpyHostToDevice);
    for (int lv = 0; lv < L; lv++)
    {
      size_t nn = ((size_t)T) << lv; uint64_t mask = (1ull << lv) - 1;
      if (kind == 2) ggm_level_k<2><<<nblk(nn), 256>>>(g_store + g_off[L - lv], g_store + g_off[L - lv - 1], nn, (uint32_t)lv, mask);
      else ggm_level_k<3><<<nblk(nn), 256>>>(g_store + g_off[L - lv], g_store + g_off[L - lv - 1], nn, (uint32_t)lv, mask);
    }
  }
  return cudaDeviceSynchronize() == cudaSuccess ? 0 : -2;
}
API uint64_t open_off(int lvl) { return g_off[lvl] / 8; }                            // node offset (32 B units) of level lvl, tree 0, index 0
__global__ void gather_k(const uint32_t* __restrict__ store, const uint64_t* __restrict__ off, uint32_t* __restrict__ out, size_t n2)
{
  size_t k = blockIdx.x * (size_t)blockDim.x + threadIdx.x;                          // one thread per 16 B half of a node
  if (k >= n2) return;
  ((uint4*)(out + (k >> 1) * 8))[k & 1] = ((const uint4*)(store + off[k >> 1] * 8))[k & 1];
}
API double open_bench(size_t n, const uint64_t* off_host, int reps, uint32_t* out_host)
{
  uint64_t* d_off; uint32_t* d_out;
  if (cudaMalloc(&d_off, n * 8) != cudaSuccess || cudaMalloc(&d_out, n * 32) != cudaSuccess) return -1.0;
  cudaMemcpy(d_off, off_host, n * 8, cudaMemcpyHostToDevice);
  gather_k<<<nblk(2 * n), 256>>>(g_store, d_off, d_out, 2 * n); cudaDeviceSynchronize();   // warm-up
  cudaEvent_t t0, t1; cudaEventCreate(&t0); cudaEventCreate(&t1);
  cudaEventRecord(t0);
  for (int rep = 0; rep < reps; rep++) gather_k<<<nblk(2 * n), 256>>>(g_store, d_off, d_out, 2 * n);
  cudaEventRecord(t1); cudaEventSynchronize(t1);
  float ms = 0; cudaEventElapsedTime(&ms, t0, t1);
  cudaError_t e = cudaGetLastError();
  if (out_host) cudaMemcpy(out_host, d_out, n * 32, cudaMemcpyDeviceToHost);
  cudaFree(d_off); cudaFree(d_out);
  return e == cudaSuccess ? ms * 1e6 / reps : -2.0;
}
