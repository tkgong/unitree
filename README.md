# unitree

A unified II=1 hash unit for Merkle and GGM trees (ChaCha20, BLAKE3, Monolith-31, Poseidon2-M31 on one shared
adder / multiplier array), its software tree compiler and cycle-accurate simulator, the ALUs in SystemVerilog, and the
CPU / GPU baselines.

| directory | contents | start at |
|---|---|---|
| `dse/TOP` | the HLS unit (generators, headers, synthesis configs), `verify/compile_tree.py` (tree compiler + simulator + memory model + audits), the measured results | `dse/TOP/README.md` |
| `dse/common`, `dse/verify` | shared headers (`lanes.h`, `field31.h`), `build_dll.sh` (HLS C++ -> DLL driven from Python) | |
| `RTL` | the hand-written SystemVerilog unit (`RTL/unit18`: shared unit + natural ChaCha20 / BLAKE3 / Monolith units, the ALUs of `dse/TOP/alu_core.h`), Verilator closed-loop check against the HLS unit, Yosys / Nangate45 sharing report | `RTL/README.md` |
| `merkle_baseline` | CPU (BLAKE3 C, Plonky3 Monolith / Poseidon2 via `p3mono`) and GPU (CUDA) baselines | `merkle_baseline/README.md` |

Build products (DLLs, simulation vectors, Rust `target/`, object files) are not committed; each directory's README
names the script that rebuilds them. The HLS component project (`hls_component`) and the archive of earlier variants
(`_archive_2026-10-23`) stay outside the repository.
