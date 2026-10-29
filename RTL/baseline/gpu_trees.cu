// gpu_trees.cu - the three-primitive tree workloads on the GPU, level by level with device-resident data:
//   GGM trees   : BLAKE3 keyed-XOF (one node = compress(h = seed, m = [index, level], KEYED|START|END|ROOT) -> 64 B = 2 children)
//                 ChaCha20          (one node = ChaCha20 block(key = seed, counter = index_lo, nonce = (index_hi, level, 0)) -> 64 B)
//   Merkle trees: BLAKE3 parent     (compress(IV, left || right, PARENT [| ROOT]) -> 32 B)
//                 Monolith-31       (permutation(left || right) -> first 8 field elements)
// Same node framings as dse/TOP/verify/compile_tree.py, so the GPU trees and the HLS unit's compiled programs compute
// identical trees. Built as a DLL (build_gpu_trees.sh) and driven by run_gpu_trees.py.
#include "gpu_prims.cu"

template <int P>                                   // 1 = BLAKE3 keyed-XOF, 2 = ChaCha20
__global__ void ggm_kernel(const uint32_t* __restrict__ in, uint32_t* __restrict__ out, size_t n, uint32_t level)
{
  size_t i = (size_t)blockIdx.x * blockDim.x + threadIdx.x;
  if (i >= n) return;
  uint32_t seed[8], o[16];
#pragma unroll
  for (int k = 0; k < 8; k++) seed[k] = in[8 * i + k];
  if (P == 1)
  {
    uint32_t blk[16] = {(uint32_t)i, (uint32_t)(i >> 32), level, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
    b3_compress(seed, blk, 64, 16 | 1 | 2 | 8, o);
  }
  else
  {
    uint32_t nonce[3] = {(uint32_t)(i >> 32), level, 0};
    chacha_block(seed, (uint32_t)i, nonce, o);
  }
#pragma unroll
  for (int k = 0; k < 16; k++) out[16 * i + k] = o[k];          // children 2i (o[0..7]) and 2i+1 (o[8..15])
}

template <int P>                                   // 1 = BLAKE3 parent, 4 = Monolith-31
__global__ void merkle_kernel(const uint32_t* __restrict__ in, uint32_t* __restrict__ out, size_t n, uint32_t flags)
{
  size_t i = (size_t)blockIdx.x * blockDim.x + threadIdx.x;
  if (i >= n) return;
  if (P == 1)
  {
    uint32_t blk[16], o[16];
#pragma unroll
    for (int k = 0; k < 16; k++) blk[k] = in[16 * i + k];
    b3_compress(B3IV, blk, 64, flags, o);
#pragma unroll
    for (int k = 0; k < 8; k++) out[8 * i + k] = o[k];
  }
  else
  {
    uint8_t l[32], r[32], o[32];
#pragma unroll
    for (int k = 0; k < 32; k++) { l[k] = ((const uint8_t*)(in + 16 * i))[k]; r[k] = ((const uint8_t*)(in + 16 * i + 8))[k]; }
    mono_node(l, r, o);
#pragma unroll
    for (int k = 0; k < 32; k++) ((uint8_t*)(out + 8 * i))[k] = o[k];
  }
}

static void ggm_level(int p, const uint32_t* in, uint32_t* out, size_t n, uint32_t level)
{
  int tpb = 256; unsigned blocks = (unsigned)((n + tpb - 1) / tpb);
  if (p == 1) ggm_kernel<1><<<blocks, tpb>>>(in, out, n, level); else ggm_kernel<2><<<blocks, tpb>>>(in, out, n, level);
}
static void merkle_level(int p, const uint32_t* in, uint32_t* out, size_t n, uint32_t flags)
{
  int tpb = 256; unsigned blocks = (unsigned)((n + tpb - 1) / tpb);
  if (p == 1) merkle_kernel<1><<<blocks, tpb>>>(in, out, n, flags); else merkle_kernel<4><<<blocks, tpb>>>(in, out, n, flags);
}

// GGM tree of 'depth' levels from one root seed: 2^depth - 1 nodes expanded, 2^depth leaves. Returns ns per node.
API double bench_ggm(int p, int depth, int reps)
{
  size_t leaves = (size_t)1 << depth;
  uint32_t *a, *b;
  cudaMalloc(&a, leaves * 8 * sizeof(uint32_t)); cudaMalloc(&b, leaves * 8 * sizeof(uint32_t));
  fill_kernel<<<1, 8>>>((uint8_t*)a, 8, 3);
  cudaDeviceSynchronize();
  cudaEvent_t t0, t1; cudaEventCreate(&t0); cudaEventCreate(&t1);
  cudaEventRecord(t0);
  for (int rep = 0; rep < reps; rep++)
  {
    uint32_t* src = a; uint32_t* dst = b;
    for (int lv = 0; lv < depth; lv++)
    {
      ggm_level(p, src, dst, (size_t)1 << lv, (uint32_t)lv);
      uint32_t* t = src; src = dst; dst = t;
    }
  }
  cudaEventRecord(t1); cudaEventSynchronize(t1);
  float ms = 0; cudaEventElapsedTime(&ms, t0, t1);
  cudaFree(a); cudaFree(b);
  return ms * 1e6 / ((double)(leaves - 1) * reps);
}

// Merkle tree over 2^log2n leaves (32 B each): 2^log2n - 1 parents, bottom up. Returns ns per node.
API double bench_merkle(int p, int log2n, int reps)
{
  size_t n = (size_t)1 << log2n;
  uint32_t *a, *b;
  cudaMalloc(&a, n * 8 * sizeof(uint32_t)); cudaMalloc(&b, n / 2 * 8 * sizeof(uint32_t));
  fill_kernel<<<(unsigned)((n * 8 + 255) / 256), 256>>>((uint8_t*)a, n * 8, 2);
  cudaDeviceSynchronize();
  cudaEvent_t t0, t1; cudaEventCreate(&t0); cudaEventCreate(&t1);
  cudaEventRecord(t0);
  for (int rep = 0; rep < reps; rep++)
  {
    uint32_t* src = a; uint32_t* dst = b;
    for (size_t m = n / 2; m >= 1; m /= 2)
    {
      merkle_level(p, src, dst, m, m == 1 ? (4 | 8) : 4);
      uint32_t* t = src; src = dst; dst = t;
    }
  }
  cudaEventRecord(t1); cudaEventSynchronize(t1);
  float ms = 0; cudaEventElapsedTime(&ms, t0, t1);
  cudaFree(a); cudaFree(b);
  return ms * 1e6 / ((double)(n - 1) * reps);
}

// correctness helpers: all leaves of a GGM tree / the root of a Merkle tree, from host data
API int ggm_run(int p, int depth, const uint32_t* root_seed, uint32_t* leaves_out)
{
  size_t leaves = (size_t)1 << depth;
  uint32_t *a, *b;
  cudaMalloc(&a, leaves * 8 * sizeof(uint32_t)); cudaMalloc(&b, leaves * 8 * sizeof(uint32_t));
  cudaMemcpy(a, root_seed, 32, cudaMemcpyHostToDevice);
  uint32_t* src = a; uint32_t* dst = b;
  for (int lv = 0; lv < depth; lv++) { ggm_level(p, src, dst, (size_t)1 << lv, (uint32_t)lv); uint32_t* t = src; src = dst; dst = t; }
  cudaError_t e = cudaDeviceSynchronize();
  cudaMemcpy(leaves_out, src, leaves * 32, cudaMemcpyDeviceToHost);
  cudaFree(a); cudaFree(b);
  return e == cudaSuccess ? 0 : (int)e;
}
API int merkle_run(int p, int log2n, const uint32_t* leaves, uint32_t* root_out)
{
  size_t n = (size_t)1 << log2n;
  uint32_t *a, *b;
  cudaMalloc(&a, n * 8 * sizeof(uint32_t)); cudaMalloc(&b, n / 2 * 8 * sizeof(uint32_t));
  cudaMemcpy(a, leaves, n * 32, cudaMemcpyHostToDevice);
  uint32_t* src = a; uint32_t* dst = b;
  for (size_t m = n / 2; m >= 1; m /= 2) { merkle_level(p, src, dst, m, m == 1 ? (4 | 8) : 4); uint32_t* t = src; src = dst; dst = t; }
  cudaError_t e = cudaDeviceSynchronize();
  cudaMemcpy(root_out, src, 32, cudaMemcpyDeviceToHost);
  cudaFree(a); cudaFree(b);
  return e == cudaSuccess ? 0 : (int)e;
}
