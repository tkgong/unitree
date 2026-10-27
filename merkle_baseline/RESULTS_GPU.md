GPU: NVIDIA GeForce RTX 3070, 46 SMs, 1.81 GHz
GPU node functions vs CPU (20 random pairs each)
  SHA3-256: OK
  SHA-256: OK
  ChaCha20 (2 blocks): OK
  AES-128 DM: OK
  Monolith-31: OK

| primitive | GPU ns/node (independent, 2^22) | GPU Mnodes/s | GPU Merkle level-by-level ns/node | CPU 1 core ns | CPU 20 thr ns | unit issues/node | unit @300 MHz Mnodes/s | unit @1 GHz Mnodes/s | GPU / unit@1GHz | units for 10x GPU |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| SHA3-256 | 1.70 | 588 | 1.82 | 201 | 20.6 | 24 (12) | 24.5 | 81.7 | 7x | 72 |
| SHA-256 | 0.95 | 1,053 | 1.02 | 66 | 6.0 | 130 (130) | 2.3 | 7.5 | 140x | 1,397 |
| ChaCha20 | 0.93 | 1,079 | 1.00 | 152 | 12.0 | 42 (42) | 7.0 | 23.3 | 46x | 462 |
| AES-128 DM | 0.34 | 2,962 | 0.37 | 31 | 3.2 | 11 (11) | 26.7 | 89.1 | 33x | 332 |
| Monolith-31 | 1.94 | 514 | 2.09 | 333 | 35.1 | 220 (25) | 11.8 | 39.2 | 13x | 131 |

ALL OK
