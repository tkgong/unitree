# RTL/fsm - hand-written FSM cores: the three kernels and the shared PE, from the SV ALUs

Hand-written SystemVerilog (no generator): iterative cores with FSM controllers, every arithmetic operator an instance of
`RTL/alu_*.sv`. Four tops, one per design:

| top | what | adders |
|---|---|---|
| `top_mono` | the natural Monolith-31 kernel (`mono_core`) | `alu_addp` (private) |
| `top_chacha #(NB)` | the natural ChaCha20 kernel: NB `cc_block` in lockstep | 4 NB `alu_addp` |
| `top_blake3 #(NB)` | the natural BLAKE3 kernel: NB `b3_block` | 4 NB `alu_addp` |
| `top_shared #(NB)` | **the shared PE**: `mono_core` + NB `arx_block` (ChaCha20 / BLAKE3) | the blocks' 4 NB adds run on the Concrete tree's `alu_lend` adders (`ext` = 1 while the run is not Monolith); NB <= 356 |

A run executes one primitive on the whole core (`prim` of the shared PE), as the unit's programs do. Every run is 84
cycles: ChaCha20 80 ARX steps + 4 feed-forward steps, BLAKE3 14 half-rounds x 6 steps, Monolith 7 passes x MC = 12 cycles.

| file | module | what |
|---|---|---|
| `mono_pkg.sv` | package | the MDS row, the round constants, the CSD digit tables of the row (computed once at elaboration) |
| `add_tree.sv` | `add_tree #(N, W0, WMAX, LEND)` | pairwise adder tree of N terms, N - 1 adders of growing width, every adder an `alu_lend` (LEND = 1, lend ports `ext`, `ea`, `eb`, `ey`) or an `alu_addp` |
| `mono_round.sv` | `mono_round #(LEND)` | one round as a combinational function: `alu_canon` + `alu_bar31` on x[0..7]; Bricks x_i + x_{i-1}^2 with `alu_mul31` and two add + fold reductions; Concrete y_i = sum_k ROW[k] x_{i+k} as the CSD terms (+x << s or (~x) << s = (p - x) << s) summed per shift by an `add_tree` (narrow, 32..35 bits) and the 17 shifted group sums by an `add_tree` (53..55 bits); fold + round constant + fold |
| `mono_core.sv` | `mono_core #(MC, LEND)` | 16 x 31-bit state, the round, the FSM: 7 passes (pass 0 Concrete only), each held MC cycles (multicycle path), the round constant by pass; canonical output |
| `cc_block.sv` | `cc_block` | one ChaCha20 block of the natural kernel: v[16], the input copy m[16]; one ARX step per cycle in place on the four hardware columns: 4 adds on the external adders (ea / eb -> ey), 4 `alu_xor` + rotate 16 / 12 / 8 / 7, write-back; the diagonal half-rounds by the P involution (word (r, j) <- (r, (r - j) mod 4)) at every half-round end; feed-forward |
| `b3_block.sv` | `b3_block` | one BLAKE3 block of the natural kernel: v[16], m[16], h[8]; the same step engine with the message adds, rotate right 16 / 12 / 8 / 7, SIGMA on m at every round end, the finalisation xors |
| `arx_block.sv` | `arx_block` | the block of the shared PE: both primitives (`blake` selects the rotations, the message adds, the finalisation) |
| `arx_ctrl.sv` | `arx_ctrl` | the FSM: step / half-round / feed-forward counters, the step kinds (a+b, a+m, c+d, ff), xor target, rotation select, P, SIGMA, done |
| `top_mono.sv`, `top_chacha.sv`, `top_blake3.sv`, `top_shared.sv` | the four tops | see above |
| `verify/` | | `run_tb.sh <top> [NB] [NT]`: `gen_vectors.py` (random inputs, expected outputs from `dse/TOP/verify/models.py`), `tb_pe.sv` (Icarus) |
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

| top | runs | result |
|---|---|---|
| `top_mono` | 2 x 16 elements | 0 mismatches, 84 cycles |
| `top_chacha`, NB 3 | 2 x 3 blocks | 0 mismatches, 84 cycles |
| `top_blake3`, NB 3 | 2 x 3 blocks | 0 mismatches, 84 cycles |
| `top_shared`, NB 3 | 2 x (ChaCha20, BLAKE3, Monolith) | 0 mismatches |
| **`top_shared`, NB 356** (all 1,424 tree adders lent) | ChaCha20, BLAKE3, Monolith | 0 mismatches |

Mutants caught: a ChaCha rotation 8 -> 9 (every word wrong), the MDS constant ROW[3] - 1 (every Monolith word wrong).
