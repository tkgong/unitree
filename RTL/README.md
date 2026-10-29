# RTL/ - the unified hash unit (ChaCha20, BLAKE3, Monolith-31) in hand-written SystemVerilog

One shared unit and the three separate (natural) units it is compared with, at the same throughput (the same pipelines
and ring periods; every program runs cycle-identical on both). It is the hand-written RTL of the HLS DSE configuration
bz3s (`dse/TOP/build_bz3s.sh`): 18 ARX blocks (ChaCha20 / BLAKE3) and two Monolith-31 datapaths, fully pipelined (II = 1).
The programs come from the software compiler `dse/TOP/verify/compile_tree.py` (atomic per-cycle operations, one primitive
and one tree kind per program). Results: `benchmark/README.md`.

| directory | what |
|---|---|
| `src/alu/` | the ALUs, one module per function of `dse/TOP/alu_core.h`; `alu_add_ks45.sv` the structural Kogge-Stone adder of the timing flow, `nangate45_cells.sv` its cell models for simulation |
| `src/shared/` | the shared unit `unit18_shared.sv` and its blocks (`mono_dp18`, `arx_group`, `axn_step`, `kara_pkg`), which the standalone units instantiate with private adders |
| `src/standalone/` | the natural units `unit18_chacha.sv`, `unit18_blake3.sv`, `unit18_mono.sv` |
| `syn/` | `syn.sh` (Yosys + ABC, Nangate45), `repair.sh` (OpenROAD repair_design / repair_timing at 1 GHz), `netlist/` the timing-closed netlists (gzip), `syn_time.txt` run times; work directories `syn/work*/` are not committed |
| `test/` | `run_tb.sh` (Verilator closed-loop replay of compiled programs against the HLS unit), `make_traces.sh` (the traces), `run_dp.sh` + `dp_vec.py` (one datapath vs the Python model), `ks_equiv.sh` (Yosys miter + SAT proofs of the Kogge-Stone adder), `tb_gl.v` (gate-level replay of a netlist against the RTL, used by the power flow) |
| `benchmark/` | `timing/` (`sta.sh`, `timing.md`), `area/` (`report.py` sharing, `syn_blk.sh` per block, `area.md`), `power/` (`power_vcd.sh`, `run_all.sh`, `power.md`), `sram/` (FakeRAM2.0 / OpenRAM macro configs and areas), `README.md` the summary |
| `baseline/` | CPU and GPU measurements of the same trees (`baseline/README.md`) |
| `env.sh` | source lists and the tool / library paths of dana336, sourced by every script |

## The design

| file | module | what |
|---|---|---|
| `src/shared/unit18_shared.sv` | `unit18_shared` | the shared unit: 2 x `mono_dp18 #(NL = 216)` + 4 `arx_group` (5 / 4 / 5 / 4 blocks) whose 864 adds per cycle run on the datapaths' lent adders |
| `src/standalone/unit18_mono.sv` | `unit18_mono` | natural Monolith-31 unit: 2 x `mono_dp18 #(NL = 0)` (private adders only) |
| `src/standalone/unit18_chacha.sv` | `unit18_chacha` | natural ChaCha20 unit: 2 x `arx_group` (9 blocks of 18 lanes, private adders) |
| `src/standalone/unit18_blake3.sv` | `unit18_blake3` | natural BLAKE3 unit: 2 x `arx_group` (9 blocks of 22 lanes, private adders) |
| `src/shared/mono_dp18.sv` | `mono_dp18` | one Monolith-31 datapath, 18 levels: L1 Bars, L2-3 square (`alu_mul31_en_p2`), L4 Bricks, L5-18 Concrete as the Plonky3 Karatsuba conv16 (`dse/TOP/kara_dag.py`); NL > 0 makes its NL narrowest adders `alu_lend` |
| `src/shared/kara_pkg.sv` | `kara_pkg` | the Karatsuba network as packed constant tables (`NODE_TAB`, `MUL_TAB`, `OUT_TAB`, `KC_TAB`) and the round constants |
| `src/shared/arx_group.sv` | `arx_group` | one ARX block group: NBK blocks through six pipeline levels, one ARX step per level; PRIV = 1 own adders, PRIV = 0 the adds go out to lent adders |
| `src/shared/axn_step.sv`, `axn_func.svh` | `axn_ops`, `axn_fin` | the ARX step operands and results (`dse/TOP/level_ops_axn.h` transcribed by hand): xors, constant rotations, row permutation |

| ALU (`src/alu/`) | role |
|---|---|
| `alu_add #(W)` | plain W-bit adder (the lendable adders: ARX takes y[31:0], M31 folds once at the end of its tree) |
| `alu_lend #(W)` | the operand select in front of a lent adder: ARX operands (ea, eb) when `ext`, else the datapath's (a, b) |
| `alu_addp #(W)` | private adder |
| `alu_fold #(H)`, `alu_fold31` | M31 end-around carry |
| `alu_addf #(H)` | fused add + fold: compound adder (sum and sum + 1 in parallel, the end-around carry selects), one carry chain |
| `alu_csa31` | three 31-bit residues to carry-save form with the end-around carry (the Bricks sum) |
| `alu_canon #(W)` | p -> 0 |
| `alu_bar_chunk #(W)`, `alu_bar31` | Monolith Bars S-box (8 / 8 / 8 / 7-bit chunks) |
| `alu_mul31_en_p2` | 31 x 31 -> 62 multiplier, two pipeline stages, 0 when `en` = 0 |
| `alu_xor` | 64-bit xor |
| `alu_add_ks45 #(W)` | the adder as a structural Kogge-Stone of Nangate45 cells; `alu_add` and `alu_addp #(32)` instantiate it under `` `define KS45 `` (the timing flow) |

## Flows (dana336)

```sh
sh RTL/test/make_traces.sh                 # tr/: short traces of every top's programs (trp: the power traces)
sh RTL/test/run_tb.sh                      # all four tops, every trace: 0 mismatching words
sh RTL/test/run_dp.sh 0                    # one datapath vs the Python model (140 states, r = 0..6)
sh RTL/test/ks_equiv.sh                    # Kogge-Stone adder == a + b (W = 32, 33, the alu_addp / alu_lend paths)
WORK=work_t10 MODES=flat KEEPALU=1 KS45=1 NET=1 ABC_SPEED=1 ADDER=kogge-stone ABC_D=600 sh RTL/syn/syn.sh   # timing flow
WORK=work_t10 sh RTL/syn/repair.sh shared  # OpenROAD repair at 1 GHz -> syn/work_t10/shared_rep.v
WORK=work_t10 NL=rep sh RTL/benchmark/timing/sta.sh shared
WORK=work_t10 sh RTL/benchmark/power/run_all.sh                # measured-activity power, all eight (top, program) pairs
sh RTL/syn/syn.sh && python3 RTL/benchmark/area/report.py      # area-mapped sharing (syn/work)
```

The previous designs (the HLS-generated bz3 unit in `RTL/pe`, its accelerator shell `RTL/fsm`, the per-ALU ORFS runs
`RTL/syn`, the standalone ALU testbench `RTL/verify`) were removed on 2026-10-28; they are in the git history (last at
commit fb6a8ab). The RTL lived in `RTL/unit18` until 2026-10-29.
