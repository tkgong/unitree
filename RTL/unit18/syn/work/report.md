| unit | cells | total um^2 | flip-flops um^2 (count) | logic um^2 | ALU instances um^2 |
|---|---:|---:|---:|---:|---:|
| unit18_shared | 678,094 | 1,435,817 | 864,520 (191,181) | 571,297 | 533,724 |
| unit18_mono | 360,441 | 595,975 | 247,525 (54,738) | 348,450 | 442,978 |
| unit18_chacha | 215,624 | 650,406 | 520,971 (115,208) | 129,435 | 118,589 |
| unit18_blake3 | 258,917 | 816,191 | 666,886 (147,476) | 149,304 | 118,589 |

| sharing: unit18_shared vs unit18_mono + unit18_chacha + unit18_blake3 | separate um^2 | shared um^2 | saved |
|---|---:|---:|---:|
| logic only (all non-flip-flop cells) | 627,189 | 571,297 | +8.9% |
| ALU instances only | 680,157 | 533,724 | +21.5% |
| registers | 1,435,382 | 864,520 | +39.8% |
| total | 2,062,572 | 1,435,817 | +30.4% |

| ALU (instances x um^2 each) | unit18_shared | unit18_mono | unit18_chacha | unit18_blake3 | separate sum | shared |
|---|---:|---:|---:|---:|---:|---:|
| alu_add W=32 | 282 x 185 |  |  |  | 0 | 282 |
| alu_add W=33 | 150 x 199 |  |  |  | 0 | 150 |
| alu_addp W=32 | 114 x 185 | 396 x 185 | 432 x 185 | 432 x 185 | 1,260 | 114 |
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
| alu_fold H=8 | 22 x 21 | 22 x 21 |  |  | 22 | 22 |
| alu_fold H=9 | 10 x 23 | 10 x 23 |  |  | 10 | 10 |
| alu_fold31 | 112 x 84 | 112 x 84 |  |  | 112 | 112 |
| alu_lend W=32 | 282 x 119 |  |  |  | 0 | 282 |
| alu_lend W=33 | 150 x 123 |  |  |  | 0 | 150 |
| alu_mul31_en_p2 | 30 x 7,416 | 30 x 7,413 |  |  | 30 | 30 |
| alu_xor | 378 x 102 |  | 378 x 102 | 378 x 102 | 756 | 378 |
