OpenROAD (ORFS docker, nangate45, 1 ns clock), every ALU between input / output registers, timing-driven placement
(`orfs/orfs_all.py`; openroad reports on 3_place.odb). ALU logic = multi-input combinational + inverter cells.

| design (between registers) | std-cell area um^2 | flip-flops (area) | repair buffers um^2 | ALU logic um^2 | worst slack at 1 ns | met |
|---|---:|---:|---:|---:|---:|---|
| alu_lend W=32 | 1,418 | 161 (728) | 131 | 540 | +0.306 | yes |
| alu_lend W=33 | 1,373 | 166 (751) | 135 | 468 | +0.274 | yes |
| alu_lend W=34 | 1,446 | 171 (773) | 140 | 513 | +0.296 | yes |
| alu_lend W=35 | 1,544 | 176 (796) | 146 | 583 | +0.292 | yes |
| alu_lend W=36 | 1,537 | 181 (818) | 148 | 551 | +0.294 | yes |
| alu_lend W=37 | 1,595 | 186 (841) | 153 | 580 | +0.265 | yes |
| alu_lend W=38 | 1,591 | 191 (864) | 156 | 551 | +0.273 | yes |
| alu_lend W=39 | 1,696 | 196 (886) | 159 | 630 | +0.273 | yes |
| alu_lend W=40 | 1,713 | 201 (909) | 163 | 620 | +0.274 | yes |
| alu_lend W=41 | 1,719 | 206 (932) | 168 | 598 | +0.257 | yes |
| alu_add W=32 | 864 | 96 (434) | 77 | 339 | +0.420 | yes |
| alu_add W=33 | 930 | 99 (448) | 79 | 388 | +0.463 | yes |
| alu_add W=34 | 947 | 102 (461) | 81 | 389 | +0.459 | yes |
| alu_add W=35 | 989 | 105 (475) | 84 | 414 | +0.418 | yes |
| alu_add W=36 | 1,051 | 108 (488) | 86 | 460 | +0.446 | yes |
| alu_add W=37 | 1,050 | 111 (502) | 89 | 443 | +0.407 | yes |
| alu_add W=38 | 1,091 | 114 (516) | 91 | 468 | +0.461 | yes |
| alu_add W=39 | 1,131 | 117 (529) | 93 | 492 | +0.423 | yes |
| alu_add W=40 | 1,141 | 120 (543) | 96 | 485 | +0.437 | yes |
| alu_add W=41 | 1,162 | 123 (556) | 98 | 491 | +0.389 | yes |
| alu_mul31 (one stage, reference) | 7,125 | 124 (561) | 613 | 5,908 | -0.493 | NO |
| alu_mul31_p2 (Dadda, two stages) | 7,547 | 419 (1,895) | 204 | 5,390 | +0.132 | yes |
| alu_mul31_en_p2 (two stages) | 7,648 | 421 (1,904) | 195 | 5,491 | +0.147 | yes |
| alu_fold H=1 | 363 | 63 (285) | 50 | 2 | +0.800 | yes |
| alu_fold H=2 | 365 | 63 (285) | 50 | 4 | +0.793 | yes |
| alu_fold H=4 | 373 | 63 (285) | 50 | 11 | +0.753 | yes |
| alu_fold H=5 | 373 | 63 (285) | 50 | 12 | +0.729 | yes |
| alu_fold H=6 | 380 | 63 (285) | 50 | 19 | +0.724 | yes |
| alu_fold H=8 | 390 | 63 (285) | 50 | 29 | +0.686 | yes |
| alu_fold H=9 | 397 | 63 (285) | 50 | 35 | +0.681 | yes |
| alu_fold H=10 | 393 | 63 (285) | 50 | 32 | +0.683 | yes |
| alu_fold31 | 492 | 63 (285) | 50 | 131 | +0.529 | yes |
| alu_canon W=32 | 420 | 62 (280) | 49 | 64 | +0.670 | yes |
| alu_canon W=31 | 419 | 62 (280) | 49 | 64 | +0.670 | yes |
| alu_negm31 W=33 | 357 | 62 (280) | 49 | 1 | +0.800 | yes |
| alu_bar31 | 437 | 62 (280) | 49 | 81 | +0.800 | yes |
| alu_xor | 1,140 | 192 (868) | 153 | 102 | +0.800 | yes |
