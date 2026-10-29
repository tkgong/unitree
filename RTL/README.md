# RTL/ - the unified hash unit (ChaCha20, BLAKE3, Monolith-31) in hand-written SystemVerilog

The design is `unit18/`: one shared unit and the three separate (natural) units it is compared with, at the same
throughput (the same pipelines and ring periods; every program runs cycle-identical on both). It is the hand-written
RTL of the HLS DSE configuration bz3s (`dse/TOP/build_bz3s.sh`): 18 ARX blocks (ChaCha20 / BLAKE3) and two Monolith-31
datapaths, fully pipelined (II = 1). The programs come from the software compiler `dse/TOP/verify/compile_tree.py`
(atomic per-cycle operations, one primitive and one tree kind per program).

## Files

| file | module | what |
|---|---|---|
| `unit18/unit18_shared.sv` | `unit18_shared` | the shared unit: 2 x `mono_dp18 #(NL = 216)` + 4 `arx_group` (5 / 4 / 5 / 4 blocks) whose 864 adds per cycle run on the datapaths' lent adders |
| `unit18/unit18_mono.sv` | `unit18_mono` | natural Monolith-31 unit: 2 x `mono_dp18 #(NL = 0)` (private adders only) |
| `unit18/unit18_chacha.sv` | `unit18_chacha` | natural ChaCha20 unit: 2 x `arx_group` (9 blocks of 18 lanes, private adders) |
| `unit18/unit18_blake3.sv` | `unit18_blake3` | natural BLAKE3 unit: 2 x `arx_group` (9 blocks of 22 lanes, private adders) |
| `unit18/mono_dp18.sv` | `mono_dp18` | one Monolith-31 datapath, 18 levels: L1 Bars, L2-3 square (`alu_mul31_en_p2`), L4 Bricks, L5-18 Concrete as the Plonky3 Karatsuba conv16 (the DSE method, `dse/TOP/kara_dag.py`); NL > 0 makes its NL narrowest adders `alu_lend` |
| `unit18/kara_pkg.sv` | `kara_pkg` | the Karatsuba network as packed constant tables (`NODE_TAB`, `MUL_TAB`, `OUT_TAB`, `KC_TAB`) and the round constants |
| `unit18/arx_group.sv` | `arx_group` | one ARX block group: NBK blocks through six pipeline levels, one ARX step per level; PRIV = 1 own adders, PRIV = 0 the adds go out to lent adders |
| `unit18/axn_step.sv`, `unit18/axn_func.svh` | `axn_ops`, `axn_fin` | the ARX step operands and results (`dse/TOP/level_ops_axn.h` transcribed by hand): xors, constant rotations, row permutation |
| `alu_*.sv` | | the ALUs, one module per function of `dse/TOP/alu_core.h` (below) |
| `mem/` | | on-chip SRAM macros: FakeRAM2.0 config (`fakeram45.cfg`, FreePDK45 bitcell) and the areas (`fakeram45_areas.md`), OpenRAM config of the slot SRAM |

| ALU | role |
|---|---|
| `alu_add #(W)` | plain W-bit adder (the lendable adders: ARX takes y[31:0], M31 folds once at the end of its tree) |
| `alu_lend #(W)` | the operand select in front of a lent adder: ARX operands (ea, eb) when `ext`, else the datapath's (a, b); the `ext ? ea : a` of `alu_core.h` |
| `alu_addp #(W)` | private adder |
| `alu_fold #(H)`, `alu_fold31` | M31 end-around carry |
| `alu_addf #(H)` | fused `alu_addp #(32)` + `alu_fold #(H)`: compound adder (sum and sum + 1 in parallel, the end-around carry selects), one carry chain |
| `alu_csa31` | three 31-bit residues to carry-save form with the end-around carry (the Bricks sum) |
| `alu_canon #(W)` | p -> 0 |
| `alu_bar_chunk #(W)`, `alu_bar31` | Monolith Bars S-box (8 / 8 / 8 / 7-bit chunks) |
| `alu_mul31_en_p2` | 31 x 31 -> 62 multiplier, two pipeline stages, 0 when `en` = 0 |
| `alu_xor` | 64-bit xor |
| `alu_add_ks45 #(W)` | the adder as a structural Kogge-Stone of Nangate45 cells (7 gates for 32 bits); `alu_add` and `alu_addp #(32)` instantiate it under `` `define KS45 `` (the timing flow); `nangate45_cells.sv` models the cells for Verilator |

## Verification (dana336, Verilator)

- `unit18/verify/run_tb.sh [top ...]`: every top replays compiled programs closed loop, cycle by cycle, against the HLS
  unit (the DLL, `compile_tree.py trace=`): `tr/*.tr` = BLAKE3 GGM, ChaCha20 GGM, BLAKE3 Merkle, Monolith Merkle. All 8
  traces: 0 mismatching words.
- `unit18/verify/run_dp.sh [NL]`: `mono_dp18` alone against the Python model (`dp_vec.py`: 140 states, every round
  index r = 0..6). 0 bad.

## Synthesis (dana336, Yosys + ABC, Nangate45)

`unit18/syn/syn.sh [top ...]` (flat and hier runs; `WORK=<dir>`, `NET=1` writes the flat netlist), `report.py` (the
sharing table), `syn_blk.sh` (sub-blocks alone: datapath lent / natural, ARX group lent / private; `wrap_shared_b.sv`
ties `blake` for the attribution runs). Current result (`unit18/syn/work/report.md`):

| sharing: unit18_shared vs unit18_mono + unit18_chacha + unit18_blake3 | separate um^2 | shared um^2 | saved |
|---|---:|---:|---:|
| logic only (all non-flip-flop cells, flat) | 627,707 | 574,604 | 8.5% |
| ALU instances only (hier) | 692,744 | 546,216 | 21.2% |
| registers | 1,443,463 | 872,972 | 39.5% |
| total | 2,071,170 | 1,447,576 | 30.1% |

Sub-blocks (flat, before the timing restructuring): one datapath natural 297,177 um^2 / lent 324,137 (the 216 lend
selects); one 9-block ARX group private 451,533 / lent 410,654.

## Timing (dana336, Yosys + ABC + OpenROAD repair, Nangate45, 1 ns clock, pre-placement)

All four tops close at 1 GHz (WNS 0.00 after `repair_timing`): `unit18/syn/work/timing.md` has the runs, the worst paths and
the flow (`syn.sh` KEEPALU=1 KS45=1 ABC_SPEED=1 ADDER=kogge-stone ABC_D=600, then `repair.sh`). Every level is one carry chain
(`alu_addf`, `alu_csa31`), the ARX / lent adders are the structural `alu_add_ks45` (proven equal to a + b by
`unit18/verify/ks_equiv.sh`, Yosys miter + SAT), the step controls travel as 11 registered copies per block. Area of the
timing-closed netlists: shared 1,898,076 um^2, mono 990,478, chacha 890,724, blake3 1,015,758 (sharing on them: logic
31.8%, registers 37.0%, total 34.5%).

Power (vectorless OpenSTA on the same netlists, 1 GHz, every net toggling 0.5 per cycle, no wires / clock tree):
chacha 1.67 W, blake3 1.91, mono 2.03, shared 3.68 per core; SRAM about 63 mW per core (FakeRAM); energy per 2^18 tree vs the
RTX 3070 in `unit18/syn/work/power.md` (15-73x below the GPU's above-idle energy, 27-33x with the DRAM traffic at 7.5 pJ/bit).

The previous designs (the HLS-generated bz3 unit in `RTL/pe`, its accelerator shell `RTL/fsm`, the per-ALU ORFS runs
`RTL/syn`, the standalone ALU testbench `RTL/verify` and the ALUs only those used) were removed on 2026-10-28; they are in
the git history (last at commit fb6a8ab).
