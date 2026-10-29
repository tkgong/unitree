Area-mapped sharing of the current RTL (dana336, 2026-10-28, `syn.sh` default flow: flat + hier, Yosys + ABC area
mapping, Nangate45; `report.py`). The timing-closed netlists and their sharing are in `timing.md`.

| unit | cells | total um^2 | flip-flops um^2 (count) | logic um^2 | ALU instances um^2 |
|---|---:|---:|---:|---:|---:|
| unit18_shared | 673,359 | 1,447,576 | 872,972 (193,050) | 574,604 | 546,216 |
| unit18_mono | 362,398 | 597,244 | 248,773 (55,014) | 348,471 | 455,566 |
| unit18_chacha | 217,162 | 653,847 | 524,231 (115,929) | 129,616 | 118,589 |
| unit18_blake3 | 258,627 | 820,079 | 670,459 (148,266) | 149,620 | 118,589 |

| sharing: unit18_shared vs unit18_mono + unit18_chacha + unit18_blake3 | separate um^2 | shared um^2 | saved |
|---|---:|---:|---:|
| logic only (all non-flip-flop cells) | 627,707 | 574,604 | +8.5% |
| ALU instances only | 692,744 | 546,216 | +21.2% |
| registers | 1,443,463 | 872,972 | +39.5% |
| total | 2,071,170 | 1,447,576 | +30.1% |

| ALU (instances x um^2 each) | unit18_shared | unit18_mono | unit18_chacha | unit18_blake3 | separate sum | shared |
|---|---:|---:|---:|---:|---:|---:|
| alu_add W=32 | 282 x 185 |  |  |  | 0 | 282 |
| alu_add W=33 | 150 x 199 |  |  |  | 0 | 150 |
| alu_addf H=31 | 112 x 280 | 112 x 280 |  |  | 112 | 112 |
| alu_addf H=8 | 22 x 215 | 22 x 215 |  |  | 22 | 22 |
| alu_addf H=9 | 10 x 215 | 10 x 215 |  |  | 10 | 10 |
| alu_addp W=32 |  | 282 x 185 | 432 x 185 | 432 x 185 | 1,146 | 0 |
| alu_addp W=33 | 64 x 199 | 214 x 199 |  |  | 214 | 64 |
| alu_addp W=34 | 126 x 201 | 126 x 201 |  |  | 126 | 126 |
| alu_addp W=35 | 86 x 206 | 86 x 206 |  |  | 86 | 86 |
| alu_addp W=36 | 60 x 217 | 60 x 217 |  |  | 60 | 60 |
| alu_addp W=37 | 48 x 219 | 48 x 219 |  |  | 48 | 48 |
| alu_addp W=38 | 44 x 235 | 44 x 235 |  |  | 44 | 44 |
| alu_addp W=39 | 50 x 230 | 50 x 230 |  |  | 50 | 50 |
| alu_addp W=40 | 16 x 237 | 16 x 237 |  |  | 16 | 16 |
| alu_bar31 | 16 x 0 | 16 x 0 |  |  | 16 | 16 |
| alu_bar_chunk W=7 | 16 x 19 | 16 x 19 |  |  | 16 | 16 |
| alu_bar_chunk W=8 | 48 x 25 | 48 x 25 |  |  | 48 | 48 |
| alu_canon W=32 | 16 x 63 | 16 x 63 |  |  | 16 | 16 |
| alu_csa31 | 30 x 181 | 30 x 181 |  |  | 30 | 30 |
| alu_lend W=32 | 282 x 119 |  |  |  | 0 | 282 |
| alu_lend W=33 | 150 x 123 |  |  |  | 0 | 150 |
| alu_mul31_en_p2 | 30 x 7,416 | 30 x 7,416 |  |  | 30 | 30 |
| alu_xor | 378 x 102 |  | 378 x 102 | 378 x 102 | 756 | 378 |
