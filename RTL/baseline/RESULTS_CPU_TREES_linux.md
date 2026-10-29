# CPU tree baselines (Intel(R) Core(TM) i7-10700K CPU @ 3.80GHz, 16 threads)

Same node framings as RTL/compiler/compile_tree.py and the GPU trees (gpu_trees.cu); leaves / seeds are 31-bit words.
Official BLAKE3 C library 1.8.2: blake3_hash_many processes 8 inputs per call on this CPU.
Built with gcc / g++-13 -O3 -march=native and cargo 1.93 -C target-cpu=native (Plonky3); timing excludes buffer allocation and input generation.

## Correctness
- Monolith-31 permutation of [0..15] = reference test vector (Plonky3 KAT): Plonky3 OK, our C++ OK, Python model OK
- every implementation, Merkle roots of 2^1 / 2^6 / 2^9 leaves and all GGM leaves of depth 1 / 6 / 9, on 1 and 16 threads, vs the Python models: OK

## ns per node (lower is better) and Mnodes/s

| tree | size | implementation | 1 thread ns/node | 16 threads ns/node | 16 threads ns/node | best Mnodes/s (threads) |
|---|---:|---|---:|---:|---:|---:|
| BLAKE3 Merkle | 2^10 | official BLAKE3 C, hash_many | 16.20 | 7.837 | 7.433 | 135 (16) |
| BLAKE3 Merkle | 2^14 | official BLAKE3 C, hash_many | 15.54 | 2.751 | 2.759 | 364 (16) |
| BLAKE3 Merkle | 2^18 | official BLAKE3 C, hash_many | 15.40 | 2.474 | 2.426 | 412 (16) |
| BLAKE3 Merkle | 2^22 | official BLAKE3 C, hash_many | 17.06 | 3.909 | 4.103 | 256 (16) |
| BLAKE3-XOF GGM | 2^10 | official BLAKE3 C, compress_xof | 48.48 | 10.982 | 11.024 | 91 (16) |
| BLAKE3-XOF GGM | 2^10 | ours, 8-way SoA | 104.16 | 25.126 | 25.263 | 40 (16) |
| BLAKE3-XOF GGM | 2^14 | official BLAKE3 C, compress_xof | 48.31 | 5.921 | 5.928 | 169 (16) |
| BLAKE3-XOF GGM | 2^14 | ours, 8-way SoA | 102.14 | 15.066 | 15.040 | 66 (16) |
| BLAKE3-XOF GGM | 2^18 | official BLAKE3 C, compress_xof | 48.46 | 4.999 | 5.001 | 200 (16) |
| BLAKE3-XOF GGM | 2^18 | ours, 8-way SoA | 103.46 | 13.925 | 13.944 | 72 (16) |
| BLAKE3-XOF GGM | 2^22 | official BLAKE3 C, compress_xof | 49.24 | 5.523 | 5.513 | 181 (16) |
| BLAKE3-XOF GGM | 2^22 | ours, 8-way SoA | 103.21 | 14.519 | 14.202 | 70 (16) |
| ChaCha20 GGM | 2^10 | ours, scalar | 77.48 | 15.646 | 15.715 | 64 (16) |
| ChaCha20 GGM | 2^10 | ours, 8-way SoA | 114.25 | 27.501 | 27.575 | 36 (16) |
| ChaCha20 GGM | 2^10 | ours, AVX2 intrinsics | 17.56 | 8.002 | 7.932 | 126 (16) |
| ChaCha20 GGM | 2^14 | ours, scalar | 77.42 | 9.296 | 9.254 | 108 (16) |
| ChaCha20 GGM | 2^14 | ours, 8-way SoA | 112.90 | 16.608 | 16.570 | 60 (16) |
| ChaCha20 GGM | 2^14 | ours, AVX2 intrinsics | 17.11 | 3.006 | 3.001 | 333 (16) |
| ChaCha20 GGM | 2^18 | ours, scalar | 76.92 | 8.448 | 8.443 | 118 (16) |
| ChaCha20 GGM | 2^18 | ours, 8-way SoA | 113.01 | 15.467 | 15.445 | 65 (16) |
| ChaCha20 GGM | 2^18 | ours, AVX2 intrinsics | 17.47 | 2.174 | 2.166 | 462 (16) |
| ChaCha20 GGM | 2^22 | ours, scalar | 78.05 | 8.457 | 8.466 | 118 (16) |
| ChaCha20 GGM | 2^22 | ours, 8-way SoA | 114.45 | 15.816 | 15.920 | 63 (16) |
| ChaCha20 GGM | 2^22 | ours, AVX2 intrinsics | 18.28 | 4.843 | 4.846 | 206 (16) |
| Monolith-31 Merkle | 2^10 | Plonky3 p3-monolith 0.8.0 | 472.69 | 427.042 | 425.516 | 2 (16) |
| Monolith-31 Merkle | 2^10 | ours, scalar | 1475.39 | 205.268 | 205.587 | 5 (16) |
| Monolith-31 Merkle | 2^10 | ours, 8-way SoA | 604.84 | 124.998 | 123.974 | 8 (16) |
| Monolith-31 Merkle | 2^14 | Plonky3 p3-monolith 0.8.0 | 467.20 | 95.874 | 94.624 | 11 (16) |
| Monolith-31 Merkle | 2^14 | ours, scalar | 1477.58 | 148.375 | 141.446 | 7 (16) |
| Monolith-31 Merkle | 2^14 | ours, 8-way SoA | 595.01 | 79.842 | 79.910 | 13 (16) |
| Monolith-31 Merkle | 2^18 | Plonky3 p3-monolith 0.8.0 | 432.79 | 54.593 | 54.301 | 18 (16) |
| Monolith-31 Merkle | 2^18 | ours, scalar | 1474.93 | 134.646 | 135.991 | 7 (16) |
| Monolith-31 Merkle | 2^18 | ours, 8-way SoA | 594.56 | 75.732 | 75.623 | 13 (16) |
| Monolith-31 Merkle | 2^22 | Plonky3 p3-monolith 0.8.0 | 444.96 | 52.907 | 52.855 | 19 (16) |
| Monolith-31 Merkle | 2^22 | ours, scalar | 1484.56 | 138.246 | 138.218 | 7 (16) |
| Monolith-31 Merkle | 2^22 | ours, 8-way SoA | 601.52 | 74.887 | 75.378 | 13 (16) |
| Poseidon2-M31 Merkle | 2^10 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 711.87 | 592.649 | 583.890 | 2 (16) |
| Poseidon2-M31 Merkle | 2^14 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 707.67 | 137.133 | 138.254 | 7 (16) |
| Poseidon2-M31 Merkle | 2^18 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 668.15 | 79.632 | 79.581 | 13 (16) |
| Poseidon2-M31 Merkle | 2^22 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 668.55 | 77.723 | 77.701 | 13 (16) |

## Best CPU implementation per tree (best of 1 / 16 / 16 threads)

| tree | size | best implementation | ns/node | Mnodes/s | tree time us |
|---|---:|---|---:|---:|---:|
| BLAKE3 Merkle | 2^10 | official BLAKE3 C, hash_many | 7.433 | 135 | 7.6 |
| BLAKE3 Merkle | 2^14 | official BLAKE3 C, hash_many | 2.751 | 364 | 45.1 |
| BLAKE3 Merkle | 2^18 | official BLAKE3 C, hash_many | 2.426 | 412 | 636.1 |
| BLAKE3 Merkle | 2^22 | official BLAKE3 C, hash_many | 3.909 | 256 | 16,394.7 |
| BLAKE3-XOF GGM | 2^10 | official BLAKE3 C, compress_xof | 10.982 | 91 | 11.2 |
| BLAKE3-XOF GGM | 2^14 | official BLAKE3 C, compress_xof | 5.921 | 169 | 97.0 |
| BLAKE3-XOF GGM | 2^18 | official BLAKE3 C, compress_xof | 4.999 | 200 | 1,310.5 |
| BLAKE3-XOF GGM | 2^22 | official BLAKE3 C, compress_xof | 5.513 | 181 | 23,123.2 |
| ChaCha20 GGM | 2^10 | ours, AVX2 intrinsics | 7.932 | 126 | 8.1 |
| ChaCha20 GGM | 2^14 | ours, AVX2 intrinsics | 3.001 | 333 | 49.2 |
| ChaCha20 GGM | 2^18 | ours, AVX2 intrinsics | 2.166 | 462 | 567.8 |
| ChaCha20 GGM | 2^22 | ours, AVX2 intrinsics | 4.843 | 206 | 20,314.0 |
| Monolith-31 Merkle | 2^10 | ours, 8-way SoA | 123.974 | 8 | 126.8 |
| Monolith-31 Merkle | 2^14 | ours, 8-way SoA | 79.842 | 13 | 1,308.1 |
| Monolith-31 Merkle | 2^18 | Plonky3 p3-monolith 0.8.0 | 54.301 | 18 | 14,234.6 |
| Monolith-31 Merkle | 2^22 | Plonky3 p3-monolith 0.8.0 | 52.855 | 19 | 221,688.1 |
| Poseidon2-M31 Merkle | 2^10 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 583.890 | 2 | 597.3 |
| Poseidon2-M31 Merkle | 2^14 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 137.133 | 7 | 2,246.6 |
| Poseidon2-M31 Merkle | 2^18 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 79.581 | 13 | 20,861.5 |
| Poseidon2-M31 Merkle | 2^22 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 77.701 | 13 | 325,901.7 |
