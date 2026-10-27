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

## OpenROAD, timing-driven, nangate45, 1 ns clock (`orfs/`, run with `orfs/run_orfs.sh`)

Each ALU between input and output registers (`orfs/*_reg.sv`), ORFS synth + floorplan + placement with timing repair
(CTS and routing not run, see above); `openroad` reports on `3_place.odb`:

| design | std-cell area um^2 | of which flip-flops | of which repair buffers | ALU logic um^2 | worst slack at 1 ns |
|---|---:|---:|---:|---:|---:|
| alu_lend W=32 | 1,418 | 728 (161 DFF) | 131 | 540 | +0.306 ns (met) |
| alu_mul31 | 7,125 | 561 (124 DFF) | 613 | 5,908 | -0.493 ns (violated) |

Timing-driven synthesis makes the 32-bit lend adder 1.7x the area-only mapping (X2 / X4 drive cells, MUX2 and HA
cells), still well inside 1 ns. The 31 x 31 multiplier does not close 1 GHz as a single stage in this 45 nm library
(1.45 ns through the FA array); the unit's multiplier ranks would need two pipeline stages at 1 GHz, or a faster
library (the 1 GHz in `dse/TOP/README.md` is an assumption, not a result of this flow). ORFS's multiplier is Booth
mapped and smaller than the area-only Yosys array (5,908 vs 6,442 um^2).

## Reproduce

```
ssh dana336
cd ~/unitree/RTL/syn && python3 area_nangate45.py --jobs 12 --out area_nangate45_area.md     # ~3 s
python3 array_totals.py
sh orfs/run_orfs.sh alu_lend_32    # docker; stops at CTS on this CPU, results under orfs/work/
```
