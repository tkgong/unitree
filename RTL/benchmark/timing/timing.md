# unit18 timing closure at 1 GHz (Nangate45, pre-placement; dana336, 2026-10-28/29)

Flow: `WORK=work_t10 MODES=flat KEEPALU=1 KS45=1 NET=1 ABC_SPEED=1 ADDER=kogge-stone ABC_D=600 sh syn.sh <top>` then
`WORK=work_t10 sh repair.sh <top>` (OpenROAD `repair_design` + `repair_timing -setup`, 1 ns clock, no wires). WNS in ns after
`repair_timing`; the arrival of the worst path and its cells from `<top>_repair.out`, the nets from `<top>_rep.v`.

| run | RTL / flow | shared | mono | chacha | blake3 |
|---|---|---:|---:|---:|---:|
| t3 | RTL before the restructuring, Kogge-Stone techmap, default ABC | -0.84 | -0.83 | -0.42 | -0.20 |
| t4 | one carry chain per level (alu_addf / alu_csa31), K constants registered, default ABC | -0.72 | -0.62 | -0.44 | -0.33 |
| t6 | + abc_speed, ABC_D=600 | -0.84 | -0.53 | -0.21 | -0.13 |
| t7 | + every module mapped standalone (HFLAT; logic area x2.4) | -0.16 | 0.00 | -0.11 | -0.11 |
| t8 | + control copies per lane pair (merged back by opt_merge), KEEPALU | -0.25 | 0.00 | -0.15 | -0.16 |
| t9 | + structural Nangate45 Kogge-Stone adders (alu_add_ks45) | -0.08 | 0.00 | 0.00 | 0.00 |
| **t10** | + a BUF_X1 per control copy (the copies survive) | **0.00** | **0.00** | **0.00** | **0.00** |

Worst paths of t10 (arrival ns; the clock is 1.000, setup absorbs the rest):

- shared 0.952: `r8_q` copy -> INV, NOR2 (ff decode) -> 2 BUF_X1 -> ops mux -> lend mux -> structural adder (XOR2, 5 x
  AOI21/OAI21, INV, XOR2: 0.42 -> 0.67) -> step-6 result: xor, 2 selects, xor, select -> level register.
- chacha / blake3 0.842: the same without the lend mux.
- mono 0.858: reduction register -> alu_addf (fused add + fold) -> register; the Bricks (alu_csa31 + alu_addf) and the
  multiplier's second stage are under it.

What moved the numbers (all measured):

- ABC maps a 32-bit add from behavioural RTL at 13 gates / 0.49 ns inside the design (0.50 ns standalone with abc_speed,
  1.08 with the default script, whose -D does nothing). The ARX step = clk-q + control fanout + operand select + add + xor
  / rotate selects + setup; with that adder it is 1.02 ns at best. `alu_add_ks45.sv` builds the adder from Nangate45 cells
  (pg, 5 prefix levels of AOI21 / OAI21 + NAND2 / NOR2, XNOR2): 7 gates / 0.27 ns; the liberty cells are read as blackboxes
  so ABC leaves them. Equivalence to a + b (W = 32, 33) and of the `alu_addp` / `alu_lend` KS45 paths: Yosys miter + SAT with
  the liberty's own cell functions (`test/ks_equiv.sh`, 4 proofs).
- Yosys opt_merge folds identical flip-flops: the per-lane-pair control copies (arx_group r0_q / r8_q / bk_q, mono_dp18 mpc)
  came out as 1.8 per block instead of 11. `(* keep *)` on the always block and `setattr keep` on the $dff cells did not
  stop it (lost at techmap). A BUF_X1 liberty cell per copy on the input makes the copies structurally distinct (t10:
  1,179 r8_q flops in chacha).
- ABC on the flat design degrades the ALU mapping; KEEPALU keeps only the alu_* modules hierarchical through ABC.

Area of the timing-closed netlists (t10, flat, Nangate45 um^2; the sharing in `report.md` is from the area-mapped flow):

| unit | total | flip-flops (count) | cells |
|---|---:|---:|---:|
| unit18_shared | 1,898,076 | 205,622 | 981,490 |
| unit18_mono | 990,478 | 55,446 | 694,768 |
| unit18_chacha | 890,724 | 121,770 | 377,388 |
| unit18_blake3 | 1,015,758 | 149,418 | 405,036 |

| sharing on the timing-closed netlists | separate | shared | saved |
|---|---:|---:|---:|
| logic (non-flip-flop cells) | 1,419,921 | 968,253 | 31.8% |
| registers | 1,477,039 | 929,823 | 37.0% |
| total | 2,896,960 | 1,898,076 | 34.5% |

The logic sharing is higher than in the area-mapped flow (8.5%) because the timing-closed ARX adders are the structural
Kogge-Stone (about twice the cells of an area-mapped adder) and the shared unit has 432 of them where the separate units
have 864 (the natural ChaCha20 and BLAKE3 units each carry their own).
