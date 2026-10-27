# RTL/syn - standard-cell area of the ALUs vs the README's gate model (2026-10-27)

The area numbers in `dse/TOP/README.md` come from a NAND2-equivalent gate model applied to the csynth operator tables
(`dse/DSE2/asic_price.py` in the archive: add 7.5 / bit, xor 2.3 / bit, and/or 1.3 / bit, 2:1 select 2.3 / bit,
multiplier 6.0 per partial-product bit, compare 1.5 / bit, register 6 / FF). This directory checks those prices
against real standard-cell synthesis of the ALU modules in `RTL/`, on the Dana 336 PC (`ssh dana336`).

## Where everything is, per unit

| | ChaCha20 + BLAKE3 + Monolith (bz3, the baseline) | four primitives (bz) |
|---|---|---|
| ALU designs | `RTL/alu_*.sv` (the same modules; bz3 uses alu_lend / alu_add W = 32..41, alu_mul31_en_p2, alu_fold H = 2, 4, 8, 9, 10, alu_canon W = 32, alu_bar31, alu_xor; no engines, no alu_mul31 chain ranks, no alu_fold31 / alu_negm31) | all of `RTL/alu_*.sv` |
| instance counts | `RTL/syn/bz3_alus.md` (from `dse/TOP/bz3/lane_mono_kl.inc` x 2 datapaths, `level_ops_axn.h`) | `RTL/syn/bz_alus.md`, `RTL/README.md` |
| synthesis, area-only (Yosys + ABC, nangate45) | `RTL/syn/area_nangate45_area.md` (every module at every parameter value) | same file |
| timing-driven placement, 1 ns (OpenROAD) | `RTL/syn/orfs_results.md` (37 designs, every one bz3 uses meets 1 ns: adders +0.26..+0.46 ns, two-stage multiplier +0.15 ns, folds / canon / Bars / xor >= +0.67 ns) | same file |
| the inventory priced three ways | `RTL/syn/bz3_alus.md` (`python3 unit_alus.py bz3`) | `RTL/syn/bz_alus.md` |
| bit-exact check of the RTL | `RTL/verify/run_tb.sh` (117 instances, 479,232 vectors, 0 mismatches) | same |

bz3 ALU totals (2,258 instances): gate model 775,482 NAND2; area-only synthesis 652,019 um^2 (817,067 NAND2 eq);
timing-driven at 1 ns 798,920 um^2 of ALU logic (1,001,153 NAND2 eq) plus the 30 two-stage multipliers' 233 stage
flip-flops each (30 x 1,054 um^2 = 31,620 um^2 of sequential cells). bz: 3,049 instances, 1,477,139 NAND2 model,
1,314,672 um^2 area-only, 1,377,332 um^2 timing-driven (+ 108 x 1,054 um^2 of multiplier stage flip-flops).

## Tools and library (dana336)

| | |
|---|---|
| synthesis | Yosys 0.61+112 native (`synth -flatten`, `abc -liberty`, `stat -liberty`) |
| library | NangateOpenCellLibrary_typical.lib, 45 nm, the ORFS `nangate45` platform (`~/eda/OpenROAD-flow-scripts/flow/platforms`); NAND2_X1 = 0.798 um^2, used to convert area to NAND2 equivalents |
| place & route | OpenROAD from the `openroad/orfs:latest` docker image (ORFS flow, Yosys 0.68 inside), the full flow to `finish` (CTS, global + detailed route) with `LEC_CHECK=0`: the image's equivalence checker kepler-formal (run inside the CTS step) is built with AVX-512 and dies with `illegal instruction` on this CPU (i7-10700K, AVX2 only); OpenROAD itself is fine |
| also present | asap7 (NLDM), sky130hd/hs, gf180, ihp-sg13g2 platforms; Verilator 5.004; no native OpenROAD / OpenSTA |

## Per module, area-only mapping (`area_nangate45.py`, results in `area_nangate45_area.md`)

Every module at every parameter value the unit uses. NAND2 eq = cell area / 0.798 um^2; "gate model" = the README
prices applied to what the model would count for that module.

| module | cells | area um^2 | NAND2 eq | gate model | synth / model |
|---|---:|---:|---:|---:|---:|
| alu_add W=32 | 161 | 185.1 | 232 | 240 | 0.97 |
| alu_add W=41 | 196 | 240.5 | 301 | 308 | 0.98 |
| alu_lend W=32 (add + 2 selects) | 230 | 312.3 | 391 | 387 | 1.01 |
| alu_lend W=41 | 317 | 410.2 | 514 | 496 | 1.04 |
| alu_mul31 | 5,848 | 6,442.5 | 8,073 | 5,766 | 1.40 |
| alu_mul31_en | 5,912 | 6,489.6 | 8,132 | 5,909 | 1.38 |
| alu_fold H=4 | 7 | 9.6 | 12 | 30 | 0.40 |
| alu_fold H=10 | 19 | 26.1 | 33 | 75 | 0.44 |
| alu_fold31 | 73 | 84.1 | 105 | 232 | 0.45 |
| alu_canon W=32 | 72 | 62.5 | 78 | 118 | 0.66 |
| alu_negm31 W=33 | 31 | 16.5 | 21 | 232 | 0.09 |
| alu_bar31 | 87 | 93.9 | 118 | 143 | 0.82 |
| alu_xor (64 b) | 64 | 102.1 | 128 | 147 | 0.87 |
| rot31 | 0 | 0 | 0 | 0 | wiring |

All W = 32..41 adders are within 0.97..1.01 of the model, all lend variants within 1.01..1.04 (the full table is in
`area_nangate45_area.md`). An ABC delay target of 1000 or 500 ps changes none of these numbers (`_1000ps.md`,
`_500ps.md`); at 300 ps the 41-bit adder grows to 245.8 um^2 (+2%).

What the model gets wrong:
- **multiplier 1.40x too small**: 6.0 NAND2 per partial-product bit vs 8.4 synthesised (the FA / HA cells of the
  array plus the final adder).
- **folds 0.45x**: the model prices `r[H-1:0] + r[31]` as a full H-bit adder (7.5 / bit); an increment is a half-adder
  chain (3.4 / bit).
- **negm31 0.09x**: p - t with p = 2^31 - 1 is a bitwise inversion; the model priced a 31-bit subtract.
- canon 0.66x (compare + select share logic), Bars 0.82x, 64-bit xor 0.87x (XOR2_X1 = 1.33 um^2 = 1.67 NAND2, not 2.3).

## The whole ALU inventory (`array_totals.py`)

The instance counts of `RTL/README.md` priced both ways (the 64-bit xors from the csynth xor bit count of bz_16f):

| ALU class | instances | gate model NAND2 | Nangate45 synth NAND2 eq | synth / model |
|---|---:|---:|---:|---:|
| lent adders (ALU-ADD + lend select) | 912 | 367,892 | 374,826 | 1.02 |
| private adders, datapaths | 176 | 44,830 | 43,704 | 0.97 |
| private adders, Poseidon2 engines | 268 | 67,028 | 65,644 | 0.98 |
| multipliers | 108 | 627,304 | 873,772 | 1.39 |
| folds | 382 | 47,304 | 21,106 | 0.45 |
| canon | 192 | 22,656 | 14,976 | 0.66 |
| negm31 | 4 | 928 | 84 | 0.09 |
| Bars | 2 | 286 | 236 | 0.83 |
| 64-bit xors | 1,005 | 147,735 | 128,640 | 0.87 |
| total | 3,049 | 1,325,963 | 1,522,988 | 1.15 |

The adders, 86% of the unit's shared logic, are priced right; the total is 15% low because of the multipliers.

Effect on the README's sharing claim (the four separate units carry the same 108 multipliers and their own xors, so
the correction applies to both sides; `dse/TOP/verify/verify_area.py` parts, mult x 1.39, xor x 0.87, adders x 1.0):

| | ALU gates unified vs separate | ALU sharing | total sharing |
|---|---|---:|---:|
| README gate model | 1,179,261 vs 1,939,715 | +39.2% | +32.5% |
| corrected | 1,402,894 vs 2,225,713 | +37.0% | +32.0% |

The fold / canon / negm31 corrections are not applied there: csynth lists an increment as a `+` of H bits like any
adder, so they cannot be separated in the reports; they are 5% of the inventory's model gates and would move the
sharing by less than that.

## The larger multiplier and the sharing claims, with and without Poseidon2

The unit's multipliers are shared between Monolith (its 30 Bricks squares) and Poseidon2 (108 products): the unified
unit has 108, the separate units 30 + 108 = 138. Without Poseidon2 (bz3, bt_12) the unit has Monolith's 30 and nothing
shares them. Re-pricing the multiplier (gate model 5,766 NAND2; one-stage synthesis 8,073 = x1.40; two-stage Dadda with
its 233 stage flip-flops 9,219 = x1.60; xor x0.87 in both corrected columns) in the csynth gate-model parts of every
unit (`dse/TOP/verify/verify_area.py`):

| configuration | multipliers unified / separate | ALU sharing: model | 1-stage mult | 2-stage mult | total sharing: model | 1-stage | 2-stage | multiplier share of the unified ALU (2-stage) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 4 primitives (with Poseidon2) | 108 / 138 | +39.2% | +36.9% | +35.9% | +32.5% | +32.0% | +31.7% | 65% |
| BLAKE3 + Monolith + Poseidon2 | 108 / 138 | +30.4% | +29.2% | +28.7% | +10.2% | +11.0% | +11.4% | 66% |
| Monolith + Poseidon2 (ZK pair) | 108 / 138 | +21.1% | +21.3% | +21.3% | +17.6% | +18.2% | +18.4% | 70% |
| ChaCha20 + BLAKE3 + Monolith (no Poseidon2) | 30 / 30 | +44.9% | +42.6% | +41.3% | +33.6% | +33.2% | +33.0% | 41% |
| BLAKE3 + Monolith (no Poseidon2) | 30 / 30 | +28.2% | +26.4% | +25.3% | +2.2% | +2.1% | +2.1% | 43% |

With Poseidon2 the multiplier itself is shared (138 -> 108), so a larger multiplier barely moves the figures: the ZK
pair even gains (+21.1 -> +21.3% ALU, +17.6 -> +18.4% total), the 4-primitive unit loses 3.3 points of ALU sharing and
0.8 of total. Without Poseidon2 the multipliers are unshared Monolith-only logic on both sides, so every gate they grow
dilutes the (adder / xor) sharing: the 3-primitive unit drops from +44.9% to +41.3% ALU, the total only 0.6 points,
because the registers and selects dominate the total. The multiplier is 65-70% of the unified ALU logic with Poseidon2
and 41-43% without it.

## OpenROAD, nangate45, 1 ns clock, after routing: every ALU (`orfs/orfs_all.py`, `orfs_results_route.md`)

Each ALU between input and output registers, the full ORFS flow: synthesis, floorplan, timing-driven placement, CTS,
global and detailed routing, finish; `openroad` reports on `6_final.odb` with the extracted parasitics (`6_final.spef`)
and the propagated clock tree, plus the detailed-route DRC count. 37 designs (every module at every parameter value the
units use):

| design (between registers) | ALU logic um^2 | worst slack at 1 ns, routed | route DRC |
|---|---:|---:|---:|
| alu_lend W=32 .. 41 (10 runs) | 468 .. 630 | +0.209 .. +0.263, all met | 0 |
| alu_add W=32 .. 41 (10 runs) | 339 .. 492 | +0.358 .. +0.444, all met | 0 |
| alu_mul31, one stage (reference) | 5,992 | **-0.540, violated** | 0 |
| alu_mul31_p2, two-stage Dadda | 5,390 | **+0.067, met** | 0 |
| alu_mul31_en_p2 | 5,491 | **+0.116, met** | 0 |
| alu_fold H = 1, 2, 4, 5, 6, 8, 9, 10 / alu_fold31 | 2 .. 35 / 131 | +0.669 .. +0.705 / +0.488 | 0 |
| alu_canon W = 31 / 32 | 64 | +0.623 / +0.625 | 0 |
| alu_negm31 W=33 | 1 | +0.704 | 0 |
| alu_bar31 | 81 | +0.701 | 0 |
| alu_xor | 102 | +0.685 | 0 |

**Every ALU meets 1 ns after routing** (with the two-stage multiplier), no DRC. Routing costs the adders 0.02-0.05 ns
against placement and the two-stage multiplier 0.065 ns (it keeps +0.067 ns). The tables below are the earlier
placement-level runs (ideal clock), kept for the cell breakdown.

## OpenROAD, timing-driven placement, nangate45, 1 ns clock (`orfs_all.py --target place`, `orfs_results.md`)

Each ALU between input and output registers (generated wrappers under `orfs/gen/`), ORFS synth + floorplan +
timing-driven placement with repair, `openroad` reports on `3_place.odb` (ideal clock). The
small modules get an explicit 90 x 90 um die (the power grid needs it); everything else 50% utilization.

| design (between registers) | std-cell area um^2 | flip-flops | ALU logic um^2 | worst slack at 1 ns |
|---|---:|---:|---:|---:|
| alu_lend W=32 .. 41 (10 runs) | 1,373 .. 1,719 | 161 .. 206 | 468 .. 630 | +0.257 .. +0.306, all met |
| alu_add W=41 | 1,162 | 123 | 491 | +0.389 |
| alu_mul31, one stage (reference) | 7,125 | 124 | 5,908 | **-0.493, violated** |
| alu_mul31_p2, Dadda tree in two stages | 7,547 | 419 | 5,390 | **+0.132, met** |
| alu_mul31_en_p2 | 7,648 | 421 | 5,491 | **+0.147, met** |
| alu_fold H=10 / alu_fold31 | 393 / 492 | 63 | 32 / 131 | +0.683 / +0.529 |
| alu_canon W=32 | 420 | 62 | 64 | +0.670 |
| alu_negm31 W=33 | 357 | 62 | 1 (absorbed into the flip-flops' inverted outputs) | +0.800 |
| alu_bar31 | 437 | 62 | 81 | +0.800 |
| alu_xor | 1,140 | 192 | 102 | +0.800 |

**Every ALU meets 1 ns**, with the multiplier in two pipeline stages. The one-stage 31 x 31 array needs 1.45 ns in this
library; a first attempt that registered two 31 x 16 products (each with its own carry-propagate adder) still failed
(-0.28 ns, the 47-bit adder of each half sits in stage 1). What closes is the carry-save cut: `gen_mul31_p2.py` emits
the 961 partial-product bits and a Dadda tree (870 full / half adders, 8 levels: heights 28, 19, 13, 9, 6, 4, 3, 2),
registers the tree at height 4 (233 flip-flops), and does the last two levels plus the 62-bit carry-propagate add in
stage 2 (critical path 0.83 ns: 2 FA + HA + the adder). Cost vs the one-stage multiplier: +295 flip-flops (+1,334 um^2
of sequential cells), 9% less combinational area (the repair buffers drop from 613 to 204 um^2 because no path is
stretched any more); 108 multipliers in the unit would add 108 x 233 = 25,164 stage flip-flops (about 6% of the unit's
401,347 FFs). In the HLS unit each multiplier rank would then be two pipeline levels instead of one: the ring periods
and W grow by 3 (the x^5 chain has three ranks), the issue rate (II = 1) does not; the HLS sources are not changed here.

Timing-driven synthesis makes the adders 1.5-1.8x their area-only mapping (X2 / X4 drive cells, MUX2 and HA cells).
The 1 GHz of `dse/TOP/README.md` is backed for every ALU by this flow, after routing (see above).

## Reproduce

```
ssh dana336
cd ~/unitree/RTL/syn && python3 area_nangate45.py --jobs 12 --out area_nangate45_area.md     # ~3 s
python3 array_totals.py
python3 orfs/orfs_all.py --jobs 4 --out orfs_results_route.md   # docker, full flow with LEC_CHECK=0, ~15 min for all 37
```
