# RTL/baseline - CPU Merkle-tree baseline (microsoft/merklecpp) with the five unitree primitives

`D:\merklecpp` (header-only, C++20) supplies the tree: `merkle::TreeT<HASH_SIZE, HASH_FUNCTION>` with
`void HASH_FUNCTION(const HashT<N>& l, const HashT<N>& r, HashT<N>& out)`. This directory adds the five
node functions as plain C++ (`prims.h`), builds everything into `baseline.dll` (`build.sh`; the machine
blocks freshly built executables, so the Python driver loads the DLL as for the HLS verification), and
`run_baseline.py` checks and times it.

| prim | node function (same function as the unified HLS unit, dse/TOP) | digest | issues/node on the unit |
|---|---|---:|---:|
| 0 SHA3-256 | SHA3-256(l ‖ r), one Keccak-f[1600] | 32 B | 24 (12 with two rounds per issue) |
| 1 SHA-256 | merklecpp's built-in `merkle::sha256`: SHA-256(l ‖ r) with padding, two compressions | 32 B | 130 |
| 2 ChaCha20 | h1 = Block(key=l, ctr‖nonce=r[0:16])[0:32]; out = Block(key=h1, ctr‖nonce=r[16:32])[0:32] | 32 B | 42 |
| 3 AES-128 | AES-128_{key=l}(r) ⊕ r (Davies-Meyer, the unit's fixed-key mode) | 16 B | 11 |
| 4 Monolith-31 | Monolith-31 t=16 permutation of (l ‖ r) as 16 Mersenne31 elements (u32 LE), first 8 | 32 B | 220 (25 Karatsuba) |

Checks in `run_baseline.py`: NIST/RFC known answers (SHA3-256, ChaCha20 RFC 8439, AES FIPS-197), Monolith
vs the Python model used for the HLS verification, every node function vs an independent Python
implementation, and merklecpp roots of 8-leaf trees vs a Python binary tree. Leaves are deterministic
(xorshift64*, each 32-bit word masked to 31 bits so Monolith inputs are field elements).

    sh build.sh
    python run_baseline.py baseline.dll 20     # 2^20 leaves -> RESULTS.md

`prims_fast.h` adds the optimised CPU versions (prims 5..9: AES-NI, SHA-NI, unrolled Keccak, Mersenne folds;
built with -march=native, i7-12700K); `bench_hash_mt` runs the node function on every hardware thread.
merklecpp itself adds ~100-130 ns per node (insert + root bookkeeping) on top of the hash function.
Results (2^20 leaves, i7-12700K, 20 threads): `RESULTS.md`.

## Tree baselines for the unified unit (2026-10-22)

The unit's four tree workloads (BLAKE3 Merkle, BLAKE3-XOF GGM, ChaCha20 GGM, Monolith-31 Merkle) with the node framings of
`RTL/compiler/compile_tree.py`, every implementation checked against the Python models (`dse/TOP/verify/models.py`).

- **CPU** (`cpu/`, i7-12700K): `cpu_trees.cpp` + the official BLAKE3 C library 1.8.2 (`cpu/blake3_c/`, from the `blake3`
  crate: `blake3_hash_many` for Merkle parents, `blake3_compress_xof` for GGM nodes), our 8-way SoA / AVX2 kernels, scalar
  versions; persistent thread pool with dynamic chunks. `sh cpu/build_cpu.sh`, `python cpu/run_cpu_trees.py 22` ->
  `RESULTS_CPU_TREES.md`, `cpu/cpu_trees.json`.
- **Plonky3 Monolith** (`p3mono/`, Rust cdylib on `p3-monolith 0.8.0`, rayon). This machine refuses to execute freshly built
  .exe files, so cargo cannot run build scripts: the dependencies are vendored and `p3mono/patch_vendor.py` removes the
  build scripts and supplies their outputs (two cfgs, three generated `private.rs` modules; rayon-core via a `links`
  override in `.cargo/config.toml`). Build: `CARGO_TARGET_DIR=<local dir> cargo +1.95.0 build --release --offline`, copy
  `p3mono.dll` next to `Cargo.toml`.
- **GPU** (`gpu_trees2.cu`, RTX 3070): batches of T trees, fused small levels (one launch, shared memory), 32-bit Monolith
  MDS; `sh build_gpu_trees2.sh`, `python run_gpu_trees2.py 22` -> `RESULTS_GPU_TREES2.md`, `gpu_trees2.json`.
- **Comparison**: `python build_baselines.py <unit_trees.log>` -> `RESULTS_BASELINES.md` (unit cycles x 1 ns; the 1 GHz
  clock is an assumption).
- Monolith-31 Bars: the 7-bit chunk has two rotations (`y ^ (~rotl1(y) & rotl2(y))`), checked against the reference test
  vector (Plonky3 KAT); fixed in every copy on 2026-10-22.
