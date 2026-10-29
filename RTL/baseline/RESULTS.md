known-answer tests
  SHA3-256('abc'): OK
  ChaCha20 block RFC 8439 2.3.2: OK
  AES-128 FIPS-197 C.1 (portable): OK
  AES-128 FIPS-197 C.1 (AES-NI): OK
  Monolith-31 permutation vs Python model: OK
node functions vs Python (20 random pairs each)
  SHA3-256: OK
  SHA-256: OK
  ChaCha20 (2 blocks): OK
  AES-128 DM: OK
  Monolith-31: OK
  SHA3-256 (unrolled): OK
  SHA-256 (SHA-NI): OK
  ChaCha20 (2 blocks): OK
  AES-128 DM (AES-NI): OK
  Monolith-31 (folds): OK
merklecpp roots vs a Python binary tree (8 leaves)
  SHA3-256: OK
  SHA-256: OK
  ChaCha20 (2 blocks): OK
  AES-128 DM: OK
  Monolith-31: OK
  SHA3-256 (unrolled): OK
  SHA-256 (SHA-NI): OK
  ChaCha20 (2 blocks): OK
  AES-128 DM (AES-NI): OK
  Monolith-31 (folds): OK

CPU: 20 hardware threads. HLS unit: II = 1, one issue per cycle, utilisation 98% (dse/SCHED).

| primitive | CPU portable ns/node | CPU optimised ns/node | in merklecpp (2^20 leaves) ns/node | all 20 threads ns/node | unit issues/node (best variant) | unit FPGA 300 MHz Mnodes/s | unit ASIC 1 GHz Mnodes/s | unit @1 GHz vs 1 core | unit @1 GHz vs 20 threads |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| SHA3-256 | 591 | 207 | 320 | 20.6 | 24 (12) | 24.5 | 81.7 | 16.9x | 1.69x |
| SHA-256 | 420 | 69 | 182 | 5.2 | 130 (130) | 2.3 | 7.5 | 0.5x | 0.04x |
| ChaCha20 | 158 | 154 | 284 | 12.2 | 42 (42) | 7.0 | 23.3 | 3.6x | 0.28x |
| AES-128 DM | 196 | 31 | 136 | 2.7 | 11 (11) | 26.7 | 89.1 | 2.8x | 0.24x |
| Monolith-31 | 690 | 339 | 448 | 36.1 | 220 (25) | 11.8 | 39.2 | 13.3x | 1.41x |

ALL OK
