# GPU tree baselines, tuned (RTX 3070, CUDA 12.6, sm_86)

GPU: NVIDIA GeForce RTX 3070, 46 SMs, 1.81 GHz. Variants: **per-level** = one launch per tree level, the original gpu_trees.cu kernels (Monolith with 64-bit constants); **fused+opt** = the top (Merkle) / head (GGM) levels with <= 256 nodes per tree in one launch in shared memory, Monolith MDS on 32-bit operands; **x8** = 8 independent trees per program. Kernel time with device-resident data (cudaEvent over the whole program); PCIe = copy of the program's leaves from pinned memory, one direction.

## Correctness
- every variant (per-level / fused, 1 / 3 / 8 trees, Monolith with both MDS forms), trees of 2^1, 2^6, 2^9, 2^10 vs the Python models: OK

## ns per node and Mnodes/s

| tree | size | per-level, 1 tree ns/node | fused+opt, 1 tree ns/node | fused+opt, x8 ns/node | x8 Mnodes/s | PCIe of x8 leaves ms |
|---|---:|---:|---:|---:|---:|---:|
| Poseidon2-M31 Merkle | 2^10 | 240.059 | 203.274 | 25.485 | 39 | 0.04 |
| Poseidon2-M31 Merkle | 2^14 | 23.623 | 21.428 | 4.657 | 215 | 0.20 |
| Poseidon2-M31 Merkle | 2^18 | 4.352 | 4.209 | 2.864 | 349 | 2.61 |
| Poseidon2-M31 Merkle | 2^22 | 2.813 | 2.892 | 2.716 | 368 | 43.91 |
