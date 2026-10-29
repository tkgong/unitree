# Unit vs CPU vs GPU on the tree workloads (2026-10-23)

- **Unit**: compiled schedules executed cycle by cycle on the corrected DLLs (Monolith Bars fixed), one tree per program, Merkle BFS / GGM DFS; every run bit-exact against the Python models. br = 37 ARX blocks + 1 Monolith datapath (adder chains); bt = 38 blocks + 2 Monolith datapaths with multipliers; bu = bt with Poseidon2 on both datapaths, one multiplier rank (67 issues per permutation); bw = three multiplier ranks, Poseidon2's linear layers on the Concrete adders (23 issues); their ARX / Monolith cycles equal bt's. The final unit bz (bw fed from the state lanes only, 3,847,813 gates, 36.0% sharing) has the identical schedule: same cycle counts (verified at 2^10 for every workload), so the bw column is bz's. **Time = cycles x 1 ns: the 1 GHz clock is an assumption, not a measurement.**
- **CPU**: i7-12700K, best of 1 / 16 / 20 threads and of the implementations in RESULTS_CPU_TREES.md (official BLAKE3 C 1.8.2, Plonky3 p3-monolith / Poseidon2 0.8.0, our AVX2 / 8-way kernels).
- **GPU**: RTX 3070, gpu_trees2.cu (fused small levels, 32-bit Monolith MDS), device-resident data, kernel time only; x8 = 8 trees per program (throughput regime). PCIe transfers are listed in RESULTS_GPU_TREES2.md and are not included.

| tree | size | unit br us | unit bt us | unit bu us | unit bw us | CPU best us (impl, threads) | GPU 1 tree us | GPU x8 ns/node | best unit: CPU / unit | best unit: GPU / unit |
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|
| BLAKE3 Merkle | 2^10 | 1.2 | 1.2 | 1.2 | 1.2 | 13.4 (official BLAKE3 C, hash_many, 1) | 17.2 | 2.154 | 11.33x | 14.51x |
| BLAKE3 Merkle | 2^14 | 7.0 | 6.9 | 6.9 | 6.9 | 61.4 (official BLAKE3 C, hash_many, 16) | 49.4 | 0.504 | 8.94x | 7.19x |
| BLAKE3 Merkle | 2^18 | 100.0 | 97.5 | - | 97.5 | 445.4 (official BLAKE3 C, hash_many, 20) | 120.7 | 0.271 | 4.57x | 1.24x |
| BLAKE3 Merkle | 2^22 | 1,587.9 | 1,546.1 | - | 1,546.1 | 9,627.4 (official BLAKE3 C, hash_many, 16) | 1,085.4 | 0.237 | 6.23x | 0.70x |
| BLAKE3-XOF GGM | 2^10 | 1.2 | 1.3 | 1.3 | 1.3 | 14.7 (ours, 8-way SoA, 16) | 15.7 | 1.959 | 12.13x | 13.01x |
| BLAKE3-XOF GGM | 2^14 | 7.1 | 7.0 | 7.0 | 7.0 | 58.3 (ours, 8-way SoA, 16) | 47.1 | 0.808 | 8.35x | 6.75x |
| BLAKE3-XOF GGM | 2^18 | 100.1 | 97.6 | - | 97.6 | 433.0 (ours, 8-way SoA, 20) | 205.0 | 0.579 | 4.44x | 2.10x |
| BLAKE3-XOF GGM | 2^22 | 1,588.0 | 1,546.3 | - | 1,546.3 | 8,978.2 (ours, 8-way SoA, 20) | 2,378.5 | 0.544 | 5.81x | 1.54x |
| ChaCha20 GGM | 2^10 | 1.8 | 2.0 | 2.0 | 2.0 | 16.7 (ours, AVX2 intrinsics, 16) | 17.7 | 2.214 | 9.14x | 9.68x |
| ChaCha20 GGM | 2^14 | 10.6 | 10.5 | 10.5 | 10.5 | 61.6 (ours, AVX2 intrinsics, 16) | 53.6 | 0.814 | 5.87x | 5.11x |
| ChaCha20 GGM | 2^18 | 150.2 | 146.2 | - | 146.2 | 470.9 (ours, AVX2 intrinsics, 20) | 205.4 | 0.570 | 3.22x | 1.40x |
| ChaCha20 GGM | 2^22 | 2,382.2 | 2,319.3 | - | 2,319.3 | 8,959.6 (ours, AVX2 intrinsics, 20) | 2,343.7 | 0.539 | 3.86x | 1.01x |
| Monolith-31 Merkle | 2^10 | 8.0 | 4.3 | 4.3 | 4.3 | 71.8 (ours, 8-way SoA, 20) | 159.2 | 19.528 | 16.86x | 37.35x |
| Monolith-31 Merkle | 2^14 | 115.4 | 58.0 | 58.0 | 58.0 | 627.1 (ours, 8-way SoA, 20) | 265.8 | 3.220 | 10.81x | 4.58x |
| Monolith-31 Merkle | 2^18 | 1,835.8 | 918.1 | - | 918.1 | 8,661.6 (ours, 8-way SoA, 20) | 736.4 | 1.732 | 9.43x | 0.80x |
| Monolith-31 Merkle | 2^22 | - | - | - | 14,680.7 | 138,830.4 (ours, 8-way SoA, 20) | 7,053.3 | 1.594 | 9.46x | 0.48x |
| Poseidon2-M31 Merkle | 2^10 | - | - | 36.1 | 13.4 | 342.0 (Plonky3 p3-mersenne-31 Poseidon2 0.8.0, 16) | 207.9 | 25.485 | 25.61x | 15.57x |
| Poseidon2-M31 Merkle | 2^14 | - | - | 550.6 | 190.0 | 1,362.7 (Plonky3 p3-mersenne-31 Poseidon2 0.8.0, 16) | 351.0 | 4.657 | 7.17x | 1.85x |
| Poseidon2-M31 Merkle | 2^18 | - | - | 8,783.6 | 3,016.2 | 15,202.7 (Plonky3 p3-mersenne-31 Poseidon2 0.8.0, 20) | 1,103.5 | 2.864 | 5.04x | 0.37x |
| Poseidon2-M31 Merkle | 2^22 | - | - | - | 48,236.1 | 229,614.9 (Plonky3 p3-mersenne-31 Poseidon2 0.8.0, 20) | 12,131.2 | 2.716 | 4.76x | 0.25x |

Ratios > 1: the fastest unit (at the assumed 1 GHz) finishes the tree faster. Missing unit entries (-) were not run (Monolith 2^22 and Poseidon2 2^22: 7-280 M cycles of cycle-by-cycle simulation).
