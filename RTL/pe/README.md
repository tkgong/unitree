# RTL/pe - the bz3 unit's processing element in SystemVerilog, assembled from the ALUs

bz3 = ChaCha20 + BLAKE3 + Monolith-31 (`dse/TOP/bz3`, the baseline without Poseidon2). The unit is two identical
**processing elements** side by side. A PE is:

- one Monolith-31 datapath, 18 pipeline levels (`dp_l1` .. `dp_l18`): Bars, Bricks squares on the multipliers, the
  Karatsuba Concrete adder tree, the M31 folds;
- the 27 ChaCha20 / BLAKE3 blocks (22 lanes each) whose 4-wide adds run on **that** datapath's lendable adders
  (`alu_lend`): every ARX step issues its four operands (`axn_ops`) into the datapath level it sits on, and takes the sums
  back (`axn_fin`: xors, rotations, the row permutation).

PE 0 holds datapath 0 and the block groups of ChaCha copy 0; PE 1 holds datapath 1 and copy 1 (`CP` parameter, the only
difference). The two PEs share nothing but the `blake` control: each has its own lanes, registers, round indices and
Monolith issue bit. Lanes inside a PE: 0..593 the blocks (block j at 22 j), 594..645 the datapath.

| file | module | what |
|---|---|---|
| `pe.sv` | `pe #(CP)` | one PE: 18 levels, 18 datapath-level instances, 114 `axn_ops` + 114 `axn_fin` (19 block-steps per step), 3,052 pipeline registers (190,001 bits), the decode of the Monolith round control |
| `dp_l1.sv` .. `dp_l18.sv` | `dp_l<k>` | level k of the Monolith datapath; every operator an instance of `RTL/alu_*.sv` |
| `axn_step.sv`, `axn_func.svh` | `axn_ops #(STEP, CP)`, `axn_fin #(STEP, CP)` | the six ARX steps of one block (operand select; xors as `alu_xor`, rotations and P as wiring) |
| `unit_bz3.sv` | `unit_bz3` | the unit: two PEs + the lane map of the HLS top's ports (1,248 lanes in / out, one issue per clock) |
| `gen_pe.py`, `cparse.py` | | the generator (below) |
| `verify/` | | `run_unit_tb.sh`, `gen_unit_vectors.py`, `tb_unit.sv`: the unit against the HLS C++ |

ALU instances in one PE (one datapath + its blocks), counted in the generated netlist:

| ALU | per PE | unit |
|---|---:|---:|
| `alu_lend` (lendable adders, W = 32..41) | 456 | 912 |
| `alu_addp` (private adders) | 53 | 106 |
| `alu_mul31_en` (Bricks squares) | 15 | 30 |
| `alu_fold` (H = 2, 4, 8, 9, 10) | 72 | 144 |
| `alu_canon` | 31 | 62 |
| `alu_bar31` | 8 | 16 |
| `alu_xor` (in `axn_fin`) | 380 (CP 0) / 418 (CP 1) | 798 |
| `rot31` (wiring) | 258 | 516 |

All 456 lendable adders of a datapath are used by the blocks: 114 block-steps x 4 adds = 456.

## How it is generated (nothing re-designed)

`python gen_pe.py` reads the C++ the HLS unit is built from:

- **datapath levels**: `monk_lx<k>` of `dse/TOP/bz3/lane_mono_kl.inc` is parsed (`cparse.py`, the C++ subset the generators
  emit) and translated statement by statement: every `alu_*` call becomes an instance of the RTL module of the same name,
  casts / ranges / `pk` / shifts / `^ p` become assigns, `if (bars)` becomes a mux. Datapath 1 (`lane_mono2_kl.inc`) is
  translated too; the generator checks that it gives the identical module (lanes relative to the datapath base).
- **the PE**: `lane_pipe` of `dse/TOP/bz3/pipe_axn.h` is executed symbolically with `MODES_MASK = 0x16`: every lane of every
  level and every register update is traced to its source (an input lane, a register, an `axn_fin` / datapath output), every
  `axn_ops` / `axn_fin` / `monk_lx` call becomes an instance. Registers that can only ever hold 0 are removed. The result is
  split by copy; the generator checks that copy 0 and copy 1 give the identical PE text up to `CP`.
- **ARX steps**: `axn_step.sv` is a hand transcription of `dse/TOP/level_ops_axn.h` (the only hand-written part).

## Verification (2026-10-27)

- **Against the HLS C++, clock by clock** (`verify/run_unit_tb.sh`): `gen_unit_vectors.py` drives
  `dse/TOP/verify/lz3_16.dll` (the HLS C++ of `lane_pipe`, compiled; one call = one clock) with random issue controls
  (mono, mono2, htap, blake; r, r2 and the 28 group round indices over 0..511, a quarter of the cycles with the indices a
  real program issues) and random input lanes, from the zero reset state; `tb_unit.sv` runs `unit_bz3` on the same inputs
  (Icarus Verilog 13.0) and compares **all 1,248 output lanes every cycle**. Result: **300 cycles x 1,248 lanes, 354,778 of
  them nonzero, 0 mismatches.**
- **The testbench catches errors**: two mutated copies (one rotation in an ARX step, 20 -> 19; one `rot31` amount in
  datapath level 9) both fail (first mismatches at cycles 2 and 16).
- **Structural checks in the generator**: datapath 0 == datapath 1 at all 18 levels; PE copy 0 == copy 1 up to `CP`;
  every ARX step writes exactly the lanes the HLS merges take (`WMASK`).
- **Tools**: Vivado 2025.2 `xvlog -sv` analyzes all 38 modules without errors or warnings and `xelab` elaborates
  `unit_bz3`; Yosys 0.61 parses and elaborates `pe` (synthesis below).

## Area (Yosys + ABC, nangate45, area-only mapping, one PE)

`pe` (CP = 0) flattened and mapped on dana336 (`synth -flatten`, `dfflibmap`, `abc -liberty`; 4 min 32 s, 2.8 GB;
report `pe_stat_nangate45.txt`):

| | cells | area um^2 | share |
|---|---:|---:|---:|
| flip-flops (DFF_X1) | 166,081 | 751,000 | 59% |
| combinational | 456,389 | 512,851 | 41% |
| **one PE** | 622,470 | **1,263,851** | |

The unit is two PEs, about 2.53 mm^2 in this 45 nm library before place-and-route (PE 1 has 38 more `alu_xor`).
Yosys keeps 166,081 of the 190,001 register bits the generator declares (the rest are lane bits that are constant or
never read). For comparison, the PE's ALU instances priced by the per-module area-only runs of `RTL/syn` come to about
290,000 um^2 (estimate: half of the unit inventory in `RTL/syn/bz3_alus.md`, with the one-stage multiplier); the other
~220,000 um^2 of combinational area is the lane and operand selection around them (block step muxes, the lane merges of
every level, the lend selects' fan-in). The pipeline registers, not the ALUs, are the largest part of the PE.

## Not done

- The multipliers are the one-stage `alu_mul31_en`, as in the HLS pipeline the PE is generated from (one level per
  multiplier rank). That multiplier does not meet 1 ns in nangate45 (-0.54 ns post-route, `RTL/syn/orfs_results_route.md`);
  the two-stage `alu_mul31_en_p2` does, but using it adds a level to each multiplier rank, which has to be done in the HLS
  generator (`dse/TOP/gen_lane_mono6.py`) and re-verified; not done here. Every other ALU of the PE meets 1 ns post-route.
- No place-and-route of the whole PE (the ALUs were placed and routed one by one, `RTL/syn`).
- The Poseidon2 build (bz) is not generated; `gen_pe.py` reads bz3 only.
