# RTL/syn - standard-cell area of the ALUs vs the README's gate model (2026-10-27)

The area numbers in `dse/TOP/README.md` come from a NAND2-equivalent gate model applied to the csynth operator tables
(`dse/DSE2/asic_price.py` in the archive: add 7.5 / bit, xor 2.3 / bit, and/or 1.3 / bit, 2:1 select 2.3 / bit,
multiplier 6.0 per partial-product bit, compare 1.5 / bit, register 6 / FF). This directory checks those prices
against real standard-cell synthesis of the ALU modules in `RTL/`, on the Dana 336 PC (`ssh dana336`).

## Tools and library (dana336)

| | |
|---|---|
| synthesis | Yosys 0.61+112 native (`synth -flatten`, `abc -liberty`, `stat -liberty`) |
| library | NangateOpenCellLibrary_typical.lib, 45 nm, the ORFS `nangate45` platform (`~/eda/OpenROAD-flow-scripts/flow/platforms`); NAND2_X1 = 0.798 um^2, used to convert area to NAND2 equivalents |
| place & route | OpenROAD from the `openroad/orfs:latest` docker image (ORFS flow, Yosys 0.68 inside). Synthesis, floorplan and timing-driven placement run; CTS dies with `illegal instruction` on this CPU (i7-10700K, no AVX-512), so the flow stops after placement |
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

## OpenROAD, timing-driven, nangate45, 1 ns clock: every ALU (`orfs/orfs_all.py`, table in `orfs_results.md`)

Each ALU between input and output registers (generated wrappers under `orfs/gen/`), ORFS synth + floorplan +
timing-driven placement with repair (CTS and routing not run, see above), `openroad` reports on `3_place.odb`. The
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
The 1 GHz of `dse/TOP/README.md` is now backed for every ALU by this flow (placement-level STA, ideal clock, nangate45);
routing and CTS could not be run on this machine.

## Reproduce

```
ssh dana336
cd ~/unitree/RTL/syn && python3 area_nangate45.py --jobs 12 --out area_nangate45_area.md     # ~3 s
python3 array_totals.py
python3 orfs/orfs_all.py --jobs 4 --out orfs_results.md   # docker, ~3 min for all 20; stops at placement (CTS crashes on this CPU)
```
