# unitree

A unified II=1 hash unit for Merkle and GGM trees (ChaCha20, BLAKE3, Monolith-31 on one shared adder array), its
software tree compiler and cycle-accurate simulator, the hand-written SystemVerilog unit with its synthesis, timing and
power flows, the DRAM co-simulation, and the CPU / GPU baselines.

| directory | contents | start at |
|---|---|---|
| `RTL/src` | the hand-written SystemVerilog: `alu/` (the ALUs), `shared/` (the shared unit and its blocks), `standalone/` (the natural ChaCha20 / BLAKE3 / Monolith units it is compared with) | `RTL/README.md` |
| `RTL/compiler` | `compile_tree.py`: the software compiler. A Merkle / GGM tree request becomes the unit's per-cycle atomic operation stream (one primitive per program, every round and dependency scheduled at compile time, so the hardware has no mode or scheduler muxes); it executes the stream on the unit model, checks it bit-exact, models the SRAM and the DRAM (Ramulator2), and writes the RTL testbench traces | `RTL/README.md` |
| `RTL/syn` | Yosys / ABC synthesis and OpenROAD timing repair (Nangate45), the synthesized netlists | `RTL/README.md` |
| `RTL/test` | testbenches: Verilator closed-loop replay against the HLS unit, the datapath vectors, the adder equivalence proofs, the gate-level replay | `RTL/README.md` |
| `RTL/benchmark` | the measurements: timing, area / sharing, power (activity from real program traces), SRAM macros, and the summary of speedup / power / energy / area | `RTL/benchmark/README.md` |
| `RTL/baseline` | CPU (BLAKE3 C, our ChaCha20 AVX2, Plonky3 Monolith via `p3mono`) and GPU (CUDA) measurements | `RTL/baseline/README.md` |
| `memsim` | Ramulator2 co-simulation (HBM2, GDDR6 of the RTX 3070) driven by the tree compiler: the system cycles per tree | `memsim/README.md` |
| `dse/TOP` | the HLS unit (generators, headers, synthesis configs) and its C++ models (`verify/*.so`), the Python references `verify/models.py` | `dse/TOP/README.md` |
| `dse/common`, `dse/verify` | shared headers (`lanes.h`, `field31.h`), `build_dll.sh` (HLS C++ -> DLL driven from Python) | |

Every flow runs on the Linux machine dana336 (`RTL/env.sh` has its tool paths). Build products (shared libraries, Verilator
objects, synthesis work directories, Rust `target/`) are not committed; each README names the script that rebuilds them.
The HLS component project (`hls_component`) and the archive of earlier variants stay outside the repository.
