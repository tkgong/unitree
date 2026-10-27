# CPU tree baselines (i7-12700K, 12 cores / 20 threads)

Same node framings as dse/TOP/verify/compile_tree.py and the GPU trees (gpu_trees.cu); leaves / seeds are 31-bit words.
Official BLAKE3 C library 1.8.2: blake3_hash_many processes 8 inputs per call on this CPU (AVX2; AVX-512 is off on Alder Lake).
Built with clang 19 -O3 -march=native (C/C++) and rustc 1.95 -C target-cpu=native (Plonky3); timing excludes buffer allocation and input generation.

## Correctness
- Monolith-31 permutation of [0..15] = reference test vector (Plonky3 KAT): Plonky3 OK, our C++ OK, Python model OK
- every implementation, Merkle roots of 2^1 / 2^6 / 2^9 leaves and all GGM leaves of depth 1 / 6 / 9, on 1 and 20 threads, vs the Python models: OK

## ns per node (lower is better) and Mnodes/s

| tree | size | implementation | 1 thread ns/node | 16 threads ns/node | 20 threads ns/node | best Mnodes/s (threads) |
|---|---:|---|---:|---:|---:|---:|
| Poseidon2-M31 Merkle | 2^10 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 529.81 | 334.326 | 342.453 | 3 (16) |
| Poseidon2-M31 Merkle | 2^14 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 489.68 | 83.180 | 83.446 | 12 (16) |
| Poseidon2-M31 Merkle | 2^18 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 490.60 | 58.647 | 57.994 | 17 (20) |
| Poseidon2-M31 Merkle | 2^22 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 494.98 | 57.221 | 54.744 | 18 (20) |

## Best CPU implementation per tree (best of 1 / 16 / 20 threads)

| tree | size | best implementation | ns/node | Mnodes/s | tree time us |
|---|---:|---|---:|---:|---:|
| Poseidon2-M31 Merkle | 2^10 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 334.326 | 3 | 342.0 |
| Poseidon2-M31 Merkle | 2^14 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 83.180 | 12 | 1,362.7 |
| Poseidon2-M31 Merkle | 2^18 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 57.994 | 17 | 15,202.7 |
| Poseidon2-M31 Merkle | 2^22 | Plonky3 p3-mersenne-31 Poseidon2 0.8.0 | 54.744 | 18 | 229,614.9 |
