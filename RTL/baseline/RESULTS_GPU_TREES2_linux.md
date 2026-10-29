# GPU tree baselines, tuned (RTX 3070, nvcc 11.8, driver 570, sm_86)

GPU: NVIDIA GeForce RTX 3070, 46 SMs, 1.77 GHz. Variants: **per-level** = one launch per tree level, the original gpu_trees.cu kernels (Monolith with 64-bit constants); **fused+opt** = the top (Merkle) / head (GGM) levels with <= 256 nodes per tree in one launch in shared memory, Monolith MDS on 32-bit operands; **x8** = 8 independent trees per program. Kernel time with device-resident data (cudaEvent over the whole program); PCIe = copy of the program's leaves from pinned memory, one direction.

## Correctness
- every variant (per-level / fused, 1 / 3 / 8 trees, Monolith with both MDS forms), trees of 2^1, 2^6, 2^9, 2^10 vs the Python models: OK

## ns per node and Mnodes/s

| tree | size | per-level, 1 tree ns/node | fused+opt, 1 tree ns/node | fused+opt, x8 ns/node | x8 Mnodes/s | PCIe of x8 leaves ms |
|---|---:|---:|---:|---:|---:|---:|
| BLAKE3 Merkle | 2^10 | 30.212 | 15.918 | 2.019 | 495 | 0.10 |
| BLAKE3 Merkle | 2^14 | 3.046 | 2.135 | 0.475 | 2,107 | 1.43 |
| BLAKE3 Merkle | 2^18 | 0.502 | 0.408 | 0.270 | 3,703 | 22.71 |
| BLAKE3 Merkle | 2^22 | 0.259 | 0.255 | 0.239 | 4,177 | 364.04 |
| BLAKE3-XOF GGM | 2^10 | 30.112 | 13.358 | 1.687 | 593 | 0.09 |
| BLAKE3-XOF GGM | 2^14 | 3.427 | 2.381 | 0.753 | 1,329 | 1.29 |
| BLAKE3-XOF GGM | 2^18 | 0.798 | 0.733 | 0.563 | 1,778 | 25.66 |
| BLAKE3-XOF GGM | 2^22 | 0.556 | 0.551 | 0.532 | 1,881 | 337.85 |
| ChaCha20 GGM | 2^10 | 30.818 | 14.940 | 1.914 | 522 | 0.09 |
| ChaCha20 GGM | 2^14 | 3.530 | 2.533 | 0.766 | 1,305 | 1.31 |
| ChaCha20 GGM | 2^18 | 0.800 | 0.736 | 0.554 | 1,804 | 20.50 |
| ChaCha20 GGM | 2^22 | 0.548 | 0.544 | 0.527 | 1,898 | 337.42 |
| Monolith-31 Merkle | 2^10 | 189.470 | 152.324 | 19.101 | 52 | 0.10 |
| Monolith-31 Merkle | 2^14 | 18.677 | 15.835 | 3.173 | 315 | 1.44 |
| Monolith-31 Merkle | 2^18 | 3.136 | 2.755 | 1.707 | 586 | 22.67 |
| Monolith-31 Merkle | 2^22 | 1.868 | 1.656 | 1.572 | 636 | 364.82 |
| Poseidon2-M31 Merkle | 2^10 | 225.588 | 199.059 | 24.922 | 40 | 0.10 |
| Poseidon2-M31 Merkle | 2^14 | 22.524 | 20.887 | 4.605 | 217 | 2.07 |
| Poseidon2-M31 Merkle | 2^18 | 4.210 | 4.112 | 2.790 | 358 | 22.63 |
| Poseidon2-M31 Merkle | 2^22 | 2.740 | 2.732 | 2.627 | 381 | 364.82 |
