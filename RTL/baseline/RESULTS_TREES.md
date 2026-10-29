# GPU tree benchmarks (2026-10-17): GGM (BLAKE3 keyed-XOF, ChaCha20) and Merkle (BLAKE3, Monolith-31) trees on the RTX 3070

gpu_trees.cu (includes gpu_prims.cu; build_gpu_trees.sh -> gpu_trees.dll), run_gpu_trees.py [--unit] [max log2]. Trees are built level by level with device-resident data (one kernel launch per level; the GGM top levels and the Merkle top levels are launch-latency bound). Node framings are identical to dse/TOP/verify/compile_tree.py, and every GPU tree is checked against the Python models (models.py). The unit rows are the compiled schedules of the final unit (dse/TOP pipe_axn.h, be: ChaCha/BLAKE3 x8 on Monolith adders, h lanes co-located) executed on verify/ld_16.dll; 2^18 and 2^22 are scaled linearly from the largest simulated size (97-99% utilisation there).

GPU: NVIDIA GeForce RTX 3070, 46 SMs, 1.81 GHz
  BLAKE3 keyed-XOF GGM depth 6 (64 leaves) vs Python model: OK
  ChaCha20 GGM depth 6 (64 leaves) vs Python model: OK
  BLAKE3 Merkle 2^6 leaves, root vs Python model: OK
  Monolith-31 Merkle 2^6 leaves, root vs Python model: OK

| tree | size | nodes | GPU us / tree | GPU ns / node | GPU Mnodes/s |
|---|---:|---:|---:|---:|---:|
| BLAKE3-XOF GGM | 2^10 | 1,023 | 66.5 | 65.003 | 15 |
| BLAKE3-XOF GGM | 2^14 | 16,383 | 98.2 | 5.997 | 167 |
| BLAKE3-XOF GGM | 2^18 | 262,143 | 268.4 | 1.024 | 977 |
| BLAKE3-XOF GGM | 2^22 | 4,194,303 | 2,578.7 | 0.615 | 1,626 |
| ChaCha20 GGM | 2^10 | 1,023 | 66.0 | 64.563 | 15 |
| ChaCha20 GGM | 2^14 | 16,383 | 97.8 | 5.967 | 168 |
| ChaCha20 GGM | 2^18 | 262,143 | 266.1 | 1.015 | 985 |
| ChaCha20 GGM | 2^22 | 4,194,303 | 2,529.6 | 0.603 | 1,658 |
| BLAKE3 Merkle | 2^10 | 1,023 | 58.2 | 56.936 | 18 |
| BLAKE3 Merkle | 2^14 | 16,383 | 90.4 | 5.520 | 181 |
| BLAKE3 Merkle | 2^18 | 262,143 | 166.0 | 0.633 | 1,579 |
| BLAKE3 Merkle | 2^22 | 4,194,303 | 1,144.4 | 0.273 | 3,665 |
| Monolith-31 Merkle | 2^10 | 1,023 | 246.5 | 240.995 | 4 |
| Monolith-31 Merkle | 2^14 | 16,383 | 406.1 | 24.787 | 40 |
| Monolith-31 Merkle | 2^18 | 262,143 | 1,015.2 | 3.873 | 258 |
| Monolith-31 Merkle | 2^22 | 4,194,303 | 8,958.9 | 2.136 | 468 |

| tree | size | unit cycles (compiled schedule) | unit us @ 1 GHz | GPU us | one unit vs GPU (GPU time / unit time) | units for 10x GPU |
|---|---:|---:|---:|---:|---:|---:|
| BLAKE3-XOF GGM | 2^10 | 2,367 OK | 2.4 | 66.5 | 28.09x | 1 |
| BLAKE3-XOF GGM | 2^14 | 29,222 OK | 29.2 | 98.2 | 3.36x | 3 |
| BLAKE3-XOF GGM | 2^18 | 467,578 (scaled from 2^14) OK | 467.6 | 268.4 | 0.57x | 18 |
| BLAKE3-XOF GGM | 2^22 | 7,481,286 (scaled from 2^14) OK | 7,481.3 | 2,578.7 | 0.34x | 30 |
| ChaCha20 GGM | 2^10 | 3,543 OK | 3.5 | 66.0 | 18.64x | 1 |
| ChaCha20 GGM | 2^14 | 43,824 OK | 43.8 | 97.8 | 2.23x | 5 |
| ChaCha20 GGM | 2^18 | 701,224 (scaled from 2^14) OK | 701.2 | 266.1 | 0.38x | 27 |
| ChaCha20 GGM | 2^22 | 11,219,626 (scaled from 2^14) OK | 11,219.6 | 2,529.6 | 0.23x | 45 |
| BLAKE3 Merkle | 2^10 | 2,575 OK | 2.6 | 58.2 | 22.62x | 1 |
| BLAKE3 Merkle | 2^14 | 29,920 OK | 29.9 | 90.4 | 3.02x | 4 |
| BLAKE3 Merkle | 2^18 | 478,747 (scaled from 2^14) OK | 478.7 | 166.0 | 0.35x | 29 |
| BLAKE3 Merkle | 2^22 | 7,659,985 (scaled from 2^14) OK | 7,660.0 | 1,144.4 | 0.15x | 67 |
| Monolith-31 Merkle | 2^10 | 28,530 OK | 28.5 | 246.5 | 8.64x | 2 |
| Monolith-31 Merkle | 2^14 | 424,689 (scaled from 2^12) OK | 424.7 | 406.1 | 0.96x | 11 |
| Monolith-31 Merkle | 2^18 | 6,795,425 (scaled from 2^12) OK | 6,795.4 | 1,015.2 | 0.15x | 67 |
| Monolith-31 Merkle | 2^22 | 108,727,190 (scaled from 2^12) OK | 108,727.2 | 8,958.9 | 0.08x | 122 |

ALL OK

## reading

- Small trees are latency bound on the GPU (10-14 launches of 5-25 us): at 2^10 one unit is 9-28x faster than the GPU, at 2^14 about 3x (Monolith: parity).
- Large trees reach the GPU throughput: 2^22 GGM 0.61 ns/node (1.6 G nodes/s, both primitives), BLAKE3 Merkle 0.27 ns/node (3.6 G/s), Monolith Merkle 2.2 ns/node (0.45 G/s). The unit is fixed at 0.55 (BLAKE3) / 0.37 (ChaCha) / 0.04 (Monolith) nodes per cycle, so at 1 GHz one unit is 0.15-0.34x of the GPU on the ARX trees and 0.08x on Monolith.
- 10x the GPU in the throughput regime: BLAKE3-XOF GGM 30 units, ChaCha GGM 45, BLAKE3 Merkle 67, Monolith Merkle 122 (x 806K gates each). Below ~2^16 nodes per tree a single unit already beats the GPU because the GPU cannot pipeline a dependent tree.

## br unit (2026-10-21, 37 blocks in chains, Monolith one round per traversal): compiled schedules measured cycle by cycle on verify/ll_16.dll
GPU times from the table above (RTX 3070, run_gpu_trees.py). Merkle BFS (fifo), GGM DFS (deep), one tree per program, every run bit-exact.

| tree | size | nodes | unit cycles | unit us @ 1 GHz | GPU us | one unit vs GPU | units for 10x GPU |
|---|---:|---:|---:|---:|---:|---:|---:|
| BLAKE3 Merkle | 2^14 | 16,383 | 6,985 | 7.0 | 90.4 | 12.94x | 1 |
| BLAKE3 Merkle | 2^18 | 262,143 | 99,984 | 100.0 | 166.0 | 1.66x | 7 |
| BLAKE3 Merkle | 2^22 | 4,194,303 | 1,587,852 | 1,587.9 | 1,144.4 | 0.72x | 14 |
| BLAKE3-XOF GGM | 2^18 | 262,143 | 100,136 | 100.1 | 268.4 | 2.68x | 4 |
| BLAKE3-XOF GGM | 2^22 | 4,194,303 | 1,587,993 | 1,588.0 | 2,578.7 | 1.62x | 7 |
| ChaCha20 GGM | 2^18 | 262,143 | 150,160 | 150.2 | 266.1 | 1.77x | 6 |
| ChaCha20 GGM | 2^22 | 4,194,303 | 2,382,190 | 2,382.2 | 2,529.6 | 1.06x | 10 |
| Monolith-31 Merkle | 2^14 | 16,383 | 115,412 | 115.4 | 406.1 | 3.52x | 3 |
| Monolith-31 Merkle | 2^18 | 262,143 | 1,835,840 | 1,835.8 | 1,015.2 | 0.55x | 19 |

Per-node rates at 2^22: unit BLAKE3 Merkle 2.641 nodes/cycle = 2,641 Mnodes/s at 1 GHz vs GPU 3,665; BLAKE3 GGM 2,641 vs 1,626; ChaCha GGM
1,761 vs 1,658; Monolith 143 (99.9% of 1/7, measured at 2^18) vs 468.
The 1 GHz figure is an ASIC assumption (csynth on the FPGA target estimates 4.64 ns per level); the cycle counts are measured.

