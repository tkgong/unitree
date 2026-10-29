# GPU tree baselines, tuned (RTX 3070, CUDA 12.6, sm_86)

GPU: NVIDIA GeForce RTX 3070, 46 SMs, 1.81 GHz. Variants: **per-level** = one launch per tree level, the original gpu_trees.cu kernels (Monolith with 64-bit constants); **fused+opt** = the top (Merkle) / head (GGM) levels with <= 256 nodes per tree in one launch in shared memory, Monolith MDS on 32-bit operands; **x8** = 8 independent trees per program. Kernel time with device-resident data (cudaEvent over the whole program); PCIe = copy of the program's leaves from pinned memory, one direction.

## Correctness
- every variant (per-level / fused, 1 / 3 / 8 trees, Monolith with both MDS forms), trees of 2^1, 2^6, 2^9, 2^10 vs the Python models: OK

## ns per node and Mnodes/s

| tree | size | per-level, 1 tree ns/node | fused+opt, 1 tree ns/node | fused+opt, x8 ns/node | x8 Mnodes/s | PCIe of x8 leaves ms |
|---|---:|---:|---:|---:|---:|---:|
| BLAKE3 Merkle | 2^10 | 61.857 | 16.811 | 2.154 | 464 | 0.05 |
| BLAKE3 Merkle | 2^14 | 5.725 | 3.016 | 0.504 | 1,984 | 0.22 |
| BLAKE3 Merkle | 2^18 | 0.650 | 0.461 | 0.271 | 3,688 | 2.65 |
| BLAKE3 Merkle | 2^22 | 0.271 | 0.259 | 0.237 | 4,215 | 42.93 |
| BLAKE3-XOF GGM | 2^10 | 54.573 | 15.370 | 1.959 | 510 | 0.05 |
| BLAKE3-XOF GGM | 2^14 | 5.723 | 2.873 | 0.808 | 1,238 | 0.21 |
| BLAKE3-XOF GGM | 2^18 | 0.968 | 0.782 | 0.579 | 1,728 | 2.70 |
| BLAKE3-XOF GGM | 2^22 | 0.578 | 0.567 | 0.544 | 1,837 | 42.29 |
| ChaCha20 GGM | 2^10 | 57.531 | 17.282 | 2.214 | 452 | 0.05 |
| ChaCha20 GGM | 2^14 | 5.636 | 3.273 | 0.814 | 1,229 | 0.20 |
| ChaCha20 GGM | 2^18 | 0.971 | 0.783 | 0.570 | 1,754 | 2.68 |
| ChaCha20 GGM | 2^22 | 0.571 | 0.559 | 0.539 | 1,855 | 42.41 |
| Monolith-31 Merkle | 2^10 | 201.421 | 155.574 | 19.528 | 51 | 0.05 |
| Monolith-31 Merkle | 2^14 | 19.702 | 16.227 | 3.220 | 311 | 0.20 |
| Monolith-31 Merkle | 2^18 | 3.223 | 2.809 | 1.732 | 577 | 2.66 |
| Monolith-31 Merkle | 2^22 | 1.890 | 1.682 | 1.594 | 627 | 42.79 |
