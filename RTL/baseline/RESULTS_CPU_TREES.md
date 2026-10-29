# CPU tree baselines (i7-12700K, 12 cores / 20 threads)

Same node framings as RTL/compiler/compile_tree.py and the GPU trees (gpu_trees.cu); leaves / seeds are 31-bit words.
Official BLAKE3 C library 1.8.2: blake3_hash_many processes 8 inputs per call on this CPU (AVX2; AVX-512 is off on Alder Lake).
Built with clang 19 -O3 -march=native (C/C++) and rustc 1.95 -C target-cpu=native (Plonky3); timing excludes buffer allocation and input generation.

## Correctness
- Monolith-31 permutation of [0..15] = reference test vector (Plonky3 KAT): Plonky3 OK, our C++ OK, Python model OK
- every implementation, Merkle roots of 2^1 / 2^6 / 2^9 leaves and all GGM leaves of depth 1 / 6 / 9, on 1 and 20 threads, vs the Python models: OK

## ns per node (lower is better) and Mnodes/s

| tree | size | implementation | 1 thread ns/node | 16 threads ns/node | 20 threads ns/node | best Mnodes/s (threads) |
|---|---:|---|---:|---:|---:|---:|
| BLAKE3 Merkle | 2^10 | official BLAKE3 C, hash_many | 13.12 | 14.643 | 16.998 | 76 (1) |
| BLAKE3 Merkle | 2^14 | official BLAKE3 C, hash_many | 13.37 | 3.750 | 3.891 | 267 (16) |
| BLAKE3 Merkle | 2^18 | official BLAKE3 C, hash_many | 13.37 | 1.783 | 1.699 | 588 (20) |
| BLAKE3 Merkle | 2^22 | official BLAKE3 C, hash_many | 14.39 | 2.295 | 2.928 | 436 (16) |
| BLAKE3-XOF GGM | 2^10 | official BLAKE3 C, compress_xof | 61.08 | 16.940 | 19.298 | 59 (16) |
| BLAKE3-XOF GGM | 2^10 | ours, 8-way SoA | 15.14 | 14.341 | 19.421 | 70 (16) |
| BLAKE3-XOF GGM | 2^14 | official BLAKE3 C, compress_xof | 62.18 | 6.639 | 5.929 | 169 (20) |
| BLAKE3-XOF GGM | 2^14 | ours, 8-way SoA | 15.18 | 3.557 | 3.927 | 281 (16) |
| BLAKE3-XOF GGM | 2^18 | official BLAKE3 C, compress_xof | 59.83 | 4.985 | 4.915 | 203 (20) |
| BLAKE3-XOF GGM | 2^18 | ours, 8-way SoA | 15.36 | 1.834 | 1.652 | 605 (20) |
| BLAKE3-XOF GGM | 2^22 | official BLAKE3 C, compress_xof | 62.34 | 4.828 | 3.942 | 254 (20) |
| BLAKE3-XOF GGM | 2^22 | ours, 8-way SoA | 14.96 | 2.163 | 2.141 | 467 (20) |
| ChaCha20 GGM | 2^10 | ours, scalar | 69.52 | 16.342 | 18.695 | 61 (16) |
| ChaCha20 GGM | 2^10 | ours, 8-way SoA | 49.04 | 21.284 | 19.528 | 51 (20) |
| ChaCha20 GGM | 2^10 | ours, AVX2 intrinsics | 16.84 | 16.322 | 20.424 | 61 (16) |
| ChaCha20 GGM | 2^14 | ours, scalar | 68.53 | 7.174 | 6.433 | 155 (20) |
| ChaCha20 GGM | 2^14 | ours, 8-way SoA | 48.43 | 6.165 | 6.043 | 165 (20) |
| ChaCha20 GGM | 2^14 | ours, AVX2 intrinsics | 17.28 | 3.760 | 4.057 | 266 (16) |
| ChaCha20 GGM | 2^18 | ours, scalar | 68.11 | 5.675 | 4.945 | 202 (20) |
| ChaCha20 GGM | 2^18 | ours, 8-way SoA | 46.95 | 4.901 | 4.367 | 229 (20) |
| ChaCha20 GGM | 2^18 | ours, AVX2 intrinsics | 17.18 | 1.977 | 1.796 | 557 (20) |
| ChaCha20 GGM | 2^22 | ours, scalar | 68.58 | 5.865 | 4.787 | 209 (20) |
| ChaCha20 GGM | 2^22 | ours, 8-way SoA | 47.89 | 4.946 | 4.462 | 224 (20) |
| ChaCha20 GGM | 2^22 | ours, AVX2 intrinsics | 17.32 | 2.185 | 2.136 | 468 (20) |
| Monolith-31 Merkle | 2^10 | Plonky3 p3-monolith 0.8.0 | 384.37 | 291.438 | 297.868 | 3 (16) |
| Monolith-31 Merkle | 2^10 | ours, scalar | 592.65 | 149.858 | 181.481 | 7 (16) |
| Monolith-31 Merkle | 2^10 | ours, 8-way SoA | 302.91 | 71.258 | 70.226 | 14 (20) |
| Monolith-31 Merkle | 2^14 | Plonky3 p3-monolith 0.8.0 | 352.36 | 62.694 | 60.913 | 16 (20) |
| Monolith-31 Merkle | 2^14 | ours, scalar | 595.42 | 83.361 | 77.991 | 13 (20) |
| Monolith-31 Merkle | 2^14 | ours, 8-way SoA | 296.98 | 40.257 | 38.279 | 26 (20) |
| Monolith-31 Merkle | 2^18 | Plonky3 p3-monolith 0.8.0 | 353.58 | 43.908 | 38.837 | 26 (20) |
| Monolith-31 Merkle | 2^18 | ours, scalar | 594.90 | 71.811 | 69.277 | 14 (20) |
| Monolith-31 Merkle | 2^18 | ours, 8-way SoA | 299.35 | 37.011 | 33.041 | 30 (20) |
| Monolith-31 Merkle | 2^22 | Plonky3 p3-monolith 0.8.0 | 357.48 | 40.160 | 37.734 | 27 (20) |
| Monolith-31 Merkle | 2^22 | ours, scalar | 599.47 | 76.262 | 68.731 | 15 (20) |
| Monolith-31 Merkle | 2^22 | ours, 8-way SoA | 301.62 | 36.681 | 33.100 | 30 (20) |

## Best CPU implementation per tree (best of 1 / 16 / 20 threads)

| tree | size | best implementation | threads | ns/node | Mnodes/s | tree time us |
|---|---:|---|---:|---:|---:|---:|
| BLAKE3 Merkle | 2^10 | official BLAKE3 C, hash_many | 1 | 13.120 | 76 | 13.4 |
| BLAKE3 Merkle | 2^14 | official BLAKE3 C, hash_many | 16 | 3.750 | 267 | 61.4 |
| BLAKE3 Merkle | 2^18 | official BLAKE3 C, hash_many | 20 | 1.699 | 588 | 445.4 |
| BLAKE3 Merkle | 2^22 | official BLAKE3 C, hash_many | 16 | 2.295 | 436 | 9,627.4 |
| BLAKE3-XOF GGM | 2^10 | ours, 8-way SoA | 16 | 14.341 | 70 | 14.7 |
| BLAKE3-XOF GGM | 2^14 | ours, 8-way SoA | 16 | 3.557 | 281 | 58.3 |
| BLAKE3-XOF GGM | 2^18 | ours, 8-way SoA | 20 | 1.652 | 605 | 433.0 |
| BLAKE3-XOF GGM | 2^22 | ours, 8-way SoA | 20 | 2.141 | 467 | 8,978.2 |
| ChaCha20 GGM | 2^10 | ours, AVX2 intrinsics | 16 | 16.322 | 61 | 16.7 |
| ChaCha20 GGM | 2^14 | ours, AVX2 intrinsics | 16 | 3.760 | 266 | 61.6 |
| ChaCha20 GGM | 2^18 | ours, AVX2 intrinsics | 20 | 1.796 | 557 | 470.9 |
| ChaCha20 GGM | 2^22 | ours, AVX2 intrinsics | 20 | 2.136 | 468 | 8,959.6 |
| Monolith-31 Merkle | 2^10 | ours, 8-way SoA | 20 | 70.226 | 14 | 71.8 |
| Monolith-31 Merkle | 2^14 | ours, 8-way SoA | 20 | 38.279 | 26 | 627.1 |
| Monolith-31 Merkle | 2^18 | ours, 8-way SoA | 20 | 33.041 | 30 | 8,661.6 |
| Monolith-31 Merkle | 2^22 | ours, 8-way SoA | 20 | 33.100 | 30 | 138,830.4 |

## Poseidon2-M31 Merkle (added 2026-10-23, run with every other process suspended)

Plonky3 p3-mersenne-31 Poseidon2 0.8.0 (width 16, x^5, 4 + 14 + 4 rounds), one permutation per parent, via the same Rust DLL (p3mono) as Monolith; bit-exact against verify/models.py pos2.

| tree | size | implementation | 1 thread ns/node | 16 threads ns/node | 20 threads ns/node | best Mnodes/s (threads) |
|---|---:|---|---:|---:|---:|---:|
| Poseidon2-M31 Merkle | 2^10 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 529.81 | 334.326 | 342.453 | 3 (16) |
| Poseidon2-M31 Merkle | 2^14 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 489.68 | 83.180 | 83.446 | 12 (16) |
| Poseidon2-M31 Merkle | 2^18 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 490.60 | 58.647 | 57.994 | 17 (20) |
| Poseidon2-M31 Merkle | 2^22 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 494.98 | 57.221 | 54.744 | 18 (20) |

| tree | size | best implementation | ns/node | Mnodes/s | tree time us |
|---|---:|---|---:|---:|---:|
| Poseidon2-M31 Merkle | 2^10 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 334.326 | 3 | 342.0 |
| Poseidon2-M31 Merkle | 2^14 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 83.180 | 12 | 1,362.7 |
| Poseidon2-M31 Merkle | 2^18 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 57.994 | 17 | 15,202.7 |
| Poseidon2-M31 Merkle | 2^22 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 54.744 | 18 | 229,614.9 |
