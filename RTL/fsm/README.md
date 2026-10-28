# RTL/fsm - hand-written FSM cores: the three kernels and the shared PE, from the SV ALUs

Hand-written SystemVerilog (no generator): iterative cores with FSM controllers, every arithmetic operator an instance of
`RTL/alu_*.sv`. One module, `pe_core`, with parameters selects the hardware:

| configuration | what | adders |
|---|---|---|
| `pe_core #(1,0,0)` | the natural Monolith-31 kernel | `alu_addp` (private) |
| `pe_core #(0,1,0,NB)` | the natural ChaCha20 kernel, NB blocks in lockstep | 4 NB `alu_addp` |
| `pe_core #(0,0,1,NB)` | the natural BLAKE3 kernel | 4 NB `alu_addp` |
| `pe_core #(1,1,1,NB)` | **the shared PE**: Monolith-31 + NB ChaCha20 / BLAKE3 blocks | the blocks' 4 NB adds run on the Concrete tree's `alu_lend` adders (`ext` = 1 while the run is not Monolith); NB <= 356 |

A run executes one primitive on the whole core (`prim`), as the unit's programs do. Every run is 84 cycles: ChaCha20 80
ARX steps + 4 feed-forward steps, BLAKE3 14 half-rounds x 6 steps, Monolith 7 passes x MC = 12 cycles.

| file | module | what |
|---|---|---|
| `mono_pkg.sv` | package | the MDS row, the round constants, the CSD digit tables of the row (computed once at elaboration) |
| `add_tree.sv` | `add_tree #(N, W0, WMAX, LEND)` | pairwise adder tree of N terms, N - 1 adders of growing width, every adder an `alu_lend` (lend ports: `ext`, `ea`, `eb`, `ey`) or `alu_addp` |
| `mono_round.sv` | `mono_round` | one round as a combinational function: `alu_canon` + `alu_bar31` on x[0..7]; Bricks x_i + x_{i-1}^2 with `alu_mul31` and two add + fold reductions; Concrete y_i = sum_k ROW[k] x_{i+k} as the CSD terms (+x << s or (~x) << s = (p - x) << s) summed per shift by an `add_tree` (narrow, 32..35 bits) and the 17 shifted group sums by an `add_tree` (53..55 bits); fold + round constant + fold |
| `mono_core.sv` | `mono_core #(MC, LEND)` | 16 x 31-bit state, the round, the FSM: 7 passes (pass 0 Concrete only), each held MC cycles (multicycle path), the round constant by pass; canonical output |
| `arx_block.sv` | `arx_block #(MODE)` | one block: v[16], m[16] (ChaCha input copy / BLAKE3 message), h[8] (BLAKE3). One ARX step per cycle in place on the four hardware columns: 4 adds on the external adders (ea / eb -> ey), 4 `alu_xor` + rotate, write-back; the diagonal half-rounds by the P involution (word (r, j) <- (r, (r - j) mod 4)) at every half-round end; SIGMA on m at every BLAKE3 round end; finalisation xors. MODE 0 ChaCha20 only, 1 BLAKE3 only, 2 both (`blake` selects the rotations / message adds) |
| `arx_ctrl.sv` | `arx_ctrl` | the FSM: step / half-round / feed-forward counters, the step kinds (a+b, a+m, c+d, ff), xor target, rotation select, P, SIGMA, done |
| `pe_core.sv` | `pe_core #(HAS_MONO, HAS_CC, HAS_B3, NB, MC)` | the top: `mono_core` + `arx_ctrl` + NB `arx_block`; the blocks' adders = the first 4 NB tree adders (shared) or 4 NB `alu_addp` (natural) |
| `verify/` | | `run_tb.sh [NB] [NT] [HAS_MONO HAS_CC HAS_B3]`: `gen_vectors.py` (random inputs, expected outputs from `dse/TOP/verify/models.py`), `tb_pe.sv` (Icarus) |
| `syn/` | | `syn_all.sh` (Yosys + ABC, Nangate45, flat and hierarchical runs), `report_fsm.py` (area / sharing tables), `elab_check.sh` |

The Concrete tree: the 16 constants have 90 CSD digits over the shifts 0..16, so every output sums 90 terms: 73 adders in the
17 per-shift groups + 16 adders combining the shifted group sums = 89 per output, 1,424 for the 16 outputs (`mono_pkg::NTREE`),
all >= 32 bits and lendable: 356 ARX blocks use every one of them. (The HLS unit's generator found a Karatsuba
structure with ~437 adders per datapath for the same matrix; the hand-written tree is the direct CSD sum, about 3x the
adders, 1,424 x 33..55 bits.) The round is a multicycle combinational path: canon, Bars, multiplier, 4 add / fold
levels, 4 narrow tree levels, 5 wide levels, 4 fold / constant levels; MC = 12 cycles at 1 GHz is an estimate from the
ALUs' post-route delays (`RTL/syn/orfs_results_route.md`), not a measured path.

## Verification (Icarus Verilog, `verify/run_tb.sh`)

Random vectors from the Python models (`cc_block`, `compress16`, `mono`), every output word compared:

| configuration | runs | result |
|---|---|---|
| Monolith only | 1 x 16 elements | 0 mismatches, 84 cycles |
| ChaCha20 only, NB 3 | 2 x 3 blocks | 0 mismatches, 84 cycles |
| BLAKE3 only, NB 3 | 2 x 3 blocks | 0 mismatches, 84 cycles |
| shared, NB 3 | 2 x (ChaCha20, BLAKE3, Monolith) | 0 mismatches |
| **shared, NB 356** (all 1,424 tree adders lent) | ChaCha20, BLAKE3, Monolith | 0 mismatches |

Mutants caught: a ChaCha rotation 8 -> 9 (every word wrong), the MDS constant ROW[3] - 1 (every Monolith word wrong).
