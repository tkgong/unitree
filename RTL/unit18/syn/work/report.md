| unit | cells | total um^2 | flip-flops um^2 (count) | logic um^2 | ALU instances um^2 |
|---|---:|---:|---:|---:|---:|
| unit18_shared | 991,541 | 2,081,552 | 1,237,016 (273,555) | 844,536 | 963,993 |
| unit18_mono | 616,045 | 1,143,369 | 573,534 (126,832) | 569,835 | 873,902 |
| unit18_chacha | 215,624 | 650,406 | 520,971 (115,208) | 129,435 | 118,589 |
| unit18_blake3 | 258,917 | 816,191 | 666,886 (147,476) | 149,304 | 118,589 |

| sharing: unit18_shared vs unit18_mono + unit18_chacha + unit18_blake3 | separate um^2 | shared um^2 | saved |
|---|---:|---:|---:|
| logic only (all non-flip-flop cells) | 848,575 | 844,536 | +0.5% |
| ALU instances only | 1,111,080 | 963,993 | +13.2% |
| registers | 1,761,391 | 1,237,016 | +29.8% |
| total | 2,609,966 | 2,081,552 | +20.2% |

| ALU (instances x um^2 each) | unit18_shared | unit18_mono | unit18_chacha | unit18_blake3 | separate sum | shared |
|---|---:|---:|---:|---:|---:|---:|
| alu_add W=32 | 432 x 185 |  |  |  | 0 | 432 |
| alu_addp W=32 | 1,004 x 185 | 1,436 x 185 | 432 x 185 | 432 x 185 | 2,300 | 1,004 |
| alu_addp W=33 | 640 x 199 | 640 x 199 |  |  | 640 | 640 |
| alu_addp W=34 | 352 x 201 | 352 x 201 |  |  | 352 | 352 |
| alu_addp W=35 | 32 x 206 | 32 x 206 |  |  | 32 | 32 |
| alu_addp W=53 | 256 x 324 | 256 x 324 |  |  | 256 | 256 |
| alu_addp W=54 | 128 x 330 | 128 x 330 |  |  | 128 | 128 |
| alu_addp W=55 | 128 x 340 | 128 x 340 |  |  | 128 | 128 |
| alu_bar31 | 16 x 0 | 16 x 0 |  |  | 16 | 16 |
| alu_bar_chunk W=7 | 16 x 19 | 16 x 19 |  |  | 16 | 16 |
| alu_bar_chunk W=8 | 48 x 25 | 48 x 25 |  |  | 48 | 48 |
| alu_canon W=32 | 16 x 63 | 16 x 63 |  |  | 16 | 16 |
| alu_fold H=24 | 32 x 65 | 32 x 65 |  |  | 32 | 32 |
| alu_fold31 | 92 x 84 | 92 x 84 |  |  | 92 | 92 |
| alu_lend W=32 | 432 x 119 |  |  |  | 0 | 432 |
| alu_mul31_en_p2 | 30 x 7,416 | 30 x 7,416 |  |  | 30 | 30 |
| alu_xor | 378 x 102 |  | 378 x 102 | 378 x 102 | 756 | 378 |
