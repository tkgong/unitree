# CPU tree baselines (Intel(R) Core(TM) i7-10700K CPU @ 3.80GHz, 16 threads)

Same node framings as RTL/compiler/compile_tree.py and the GPU trees (gpu_trees.cu); leaves / seeds are 31-bit words.
Official BLAKE3 C library 1.8.2: blake3_hash_many processes 8 inputs per call on this CPU.
Built with gcc / g++-13 -O3 -march=native and cargo 1.93 -C target-cpu=native (Plonky3); timing excludes buffer allocation and input generation.

## Correctness
- Monolith-31 permutation of [0..15] = reference test vector (Plonky3 KAT): Plonky3 OK, our C++ OK, Python model OK
- every implementation, Merkle roots of 2^1 / 2^6 / 2^9 leaves and all GGM leaves of depth 1 / 6 / 9, on 1 and 16 threads, vs the Python models: OK

## ns per node (lower is better) and Mnodes/s

| tree | size | implementation | 1 thread ns/node | 8 threads ns/node | 16 threads ns/node | best Mnodes/s (threads) |
|---|---:|---|---:|---:|---:|---:|
| BLAKE3 Merkle | 2^10 | official BLAKE3 C, hash_many | 15.33 | 8.589 | 8.121 | 123 (16) |
| BLAKE3 Merkle | 2^14 | official BLAKE3 C, hash_many | 14.97 | 3.118 | 2.762 | 362 (16) |
| BLAKE3 Merkle | 2^18 | official BLAKE3 C, hash_many | 16.09 | 2.715 | 2.514 | 398 (16) |
| BLAKE3 Merkle | 2^22 | official BLAKE3 C, hash_many | 16.55 | 3.802 | 3.846 | 263 (8) |
| BLAKE3-XOF GGM | 2^10 | official BLAKE3 C, compress_xof | 48.06 | 12.777 | 11.041 | 91 (16) |
| BLAKE3-XOF GGM | 2^10 | ours, 8-way SoA | 102.76 | 23.828 | 24.700 | 42 (8) |
| BLAKE3-XOF GGM | 2^10 | ours, AVX2 intrinsics | 13.22 | 7.633 | 7.664 | 131 (8) |
| BLAKE3-XOF GGM | 2^14 | official BLAKE3 C, compress_xof | 48.27 | 7.573 | 5.890 | 170 (16) |
| BLAKE3-XOF GGM | 2^14 | ours, 8-way SoA | 102.33 | 15.217 | 15.006 | 67 (16) |
| BLAKE3-XOF GGM | 2^14 | ours, AVX2 intrinsics | 12.78 | 2.832 | 2.527 | 396 (16) |
| BLAKE3-XOF GGM | 2^18 | official BLAKE3 C, compress_xof | 48.07 | 6.657 | 4.982 | 201 (16) |
| BLAKE3-XOF GGM | 2^18 | ours, 8-way SoA | 101.75 | 13.996 | 13.929 | 72 (16) |
| BLAKE3-XOF GGM | 2^18 | ours, AVX2 intrinsics | 13.05 | 1.974 | 1.784 | 561 (16) |
| BLAKE3-XOF GGM | 2^22 | official BLAKE3 C, compress_xof | 49.02 | 6.680 | 5.516 | 181 (16) |
| BLAKE3-XOF GGM | 2^22 | ours, 8-way SoA | 103.28 | 13.968 | 15.539 | 72 (8) |
| BLAKE3-XOF GGM | 2^22 | ours, AVX2 intrinsics | 13.88 | 4.575 | 4.790 | 219 (8) |
| ChaCha20 GGM | 2^10 | ours, scalar | 77.63 | 17.011 | 15.659 | 64 (16) |
| ChaCha20 GGM | 2^10 | ours, 8-way SoA | 113.76 | 25.706 | 27.131 | 39 (8) |
| ChaCha20 GGM | 2^10 | ours, AVX2 intrinsics | 17.51 | 8.606 | 8.144 | 123 (16) |
| ChaCha20 GGM | 2^14 | ours, scalar | 77.43 | 11.396 | 9.318 | 107 (16) |
| ChaCha20 GGM | 2^14 | ours, 8-way SoA | 113.29 | 16.644 | 16.605 | 60 (16) |
| ChaCha20 GGM | 2^14 | ours, AVX2 intrinsics | 17.05 | 3.498 | 3.040 | 329 (16) |
| ChaCha20 GGM | 2^18 | ours, scalar | 77.03 | 10.580 | 8.501 | 118 (16) |
| ChaCha20 GGM | 2^18 | ours, 8-way SoA | 112.89 | 15.476 | 15.463 | 65 (16) |
| ChaCha20 GGM | 2^18 | ours, AVX2 intrinsics | 17.43 | 2.533 | 2.236 | 447 (16) |
| ChaCha20 GGM | 2^22 | ours, scalar | 78.36 | 10.570 | 8.460 | 118 (16) |
| ChaCha20 GGM | 2^22 | ours, 8-way SoA | 114.71 | 15.765 | 15.562 | 64 (16) |
| ChaCha20 GGM | 2^22 | ours, AVX2 intrinsics | 18.16 | 4.639 | 4.840 | 216 (8) |
| Monolith-31 Merkle | 2^10 | Plonky3 p3-monolith 0.8.0 | 464.20 | 294.400 | 421.980 | 3 (8) |
| Monolith-31 Merkle | 2^10 | ours, scalar | 1447.74 | 235.090 | 199.873 | 5 (16) |
| Monolith-31 Merkle | 2^10 | ours, 8-way SoA | 604.98 | 109.981 | 122.087 | 9 (8) |
| Monolith-31 Merkle | 2^14 | Plonky3 p3-monolith 0.8.0 | 488.00 | 95.666 | 97.346 | 10 (8) |
| Monolith-31 Merkle | 2^14 | ours, scalar | 1442.89 | 197.932 | 138.341 | 7 (16) |
| Monolith-31 Merkle | 2^14 | ours, 8-way SoA | 589.97 | 82.563 | 79.887 | 13 (16) |
| Monolith-31 Merkle | 2^18 | Plonky3 p3-monolith 0.8.0 | 440.44 | 63.592 | 56.167 | 18 (16) |
| Monolith-31 Merkle | 2^18 | ours, scalar | 1456.00 | 196.949 | 136.041 | 7 (16) |
| Monolith-31 Merkle | 2^18 | ours, 8-way SoA | 598.66 | 80.620 | 74.670 | 13 (16) |
| Monolith-31 Merkle | 2^22 | Plonky3 p3-monolith 0.8.0 | 436.25 | 60.359 | 53.269 | 19 (16) |
| Monolith-31 Merkle | 2^22 | ours, scalar | 1458.87 | 198.051 | 138.082 | 7 (16) |
| Monolith-31 Merkle | 2^22 | ours, 8-way SoA | 603.31 | 81.155 | 74.097 | 13 (16) |
| Poseidon2-M31 Merkle | 2^10 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 702.40 | 517.879 | 605.932 | 2 (8) |
| Poseidon2-M31 Merkle | 2^14 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 704.92 | 140.037 | 137.119 | 7 (16) |
| Poseidon2-M31 Merkle | 2^18 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 665.82 | 99.190 | 78.830 | 13 (16) |
| Poseidon2-M31 Merkle | 2^22 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 668.81 | 91.186 | 77.534 | 13 (16) |

## Best CPU implementation per tree (best of 1 / 8 / 16 threads)

| tree | size | best implementation | ns/node | Mnodes/s | tree time us |
|---|---:|---|---:|---:|---:|
| BLAKE3 Merkle | 2^10 | official BLAKE3 C, hash_many | 8.121 | 123 | 8.3 |
| BLAKE3 Merkle | 2^14 | official BLAKE3 C, hash_many | 2.762 | 362 | 45.3 |
| BLAKE3 Merkle | 2^18 | official BLAKE3 C, hash_many | 2.514 | 398 | 659.1 |
| BLAKE3 Merkle | 2^22 | official BLAKE3 C, hash_many | 3.802 | 263 | 15,945.7 |
| BLAKE3-XOF GGM | 2^10 | ours, AVX2 intrinsics | 7.633 | 131 | 7.8 |
| BLAKE3-XOF GGM | 2^14 | ours, AVX2 intrinsics | 2.527 | 396 | 41.4 |
| BLAKE3-XOF GGM | 2^18 | ours, AVX2 intrinsics | 1.784 | 561 | 467.6 |
| BLAKE3-XOF GGM | 2^22 | ours, AVX2 intrinsics | 4.575 | 219 | 19,190.6 |
| ChaCha20 GGM | 2^10 | ours, AVX2 intrinsics | 8.144 | 123 | 8.3 |
| ChaCha20 GGM | 2^14 | ours, AVX2 intrinsics | 3.040 | 329 | 49.8 |
| ChaCha20 GGM | 2^18 | ours, AVX2 intrinsics | 2.236 | 447 | 586.1 |
| ChaCha20 GGM | 2^22 | ours, AVX2 intrinsics | 4.639 | 216 | 19,456.0 |
| Monolith-31 Merkle | 2^10 | ours, 8-way SoA | 109.981 | 9 | 112.5 |
| Monolith-31 Merkle | 2^14 | ours, 8-way SoA | 79.887 | 13 | 1,308.8 |
| Monolith-31 Merkle | 2^18 | Plonky3 p3-monolith 0.8.0 | 56.167 | 18 | 14,723.8 |
| Monolith-31 Merkle | 2^22 | Plonky3 p3-monolith 0.8.0 | 53.269 | 19 | 223,428.4 |
| Poseidon2-M31 Merkle | 2^10 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 517.879 | 2 | 529.8 |
| Poseidon2-M31 Merkle | 2^14 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 137.119 | 7 | 2,246.4 |
| Poseidon2-M31 Merkle | 2^18 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 78.830 | 13 | 20,664.7 |
| Poseidon2-M31 Merkle | 2^22 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 77.534 | 13 | 325,199.7 |
