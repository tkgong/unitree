| module | cells | area um^2 | NAND2 eq | gate model | synth / model | model counts |
|---|---:|---:|---:|---:|---:|---|
| alu_add_W32 | 161 | 185.1 | 232 | 240 | 0.97 | add 32 b |
| alu_lend_W32 | 236 | 312.3 | 391 | 387 | 1.01 | add 32 b + 2 selects 32 b |
| alu_add_W33 | 168 | 199.0 | 249 | 248 | 1.01 | add 33 b |
| alu_lend_W33 | 250 | 326.6 | 409 | 399 | 1.03 | add 33 b + 2 selects 33 b |
| alu_add_W34 | 169 | 200.6 | 251 | 255 | 0.99 | add 34 b |
| alu_lend_W34 | 256 | 335.4 | 420 | 411 | 1.02 | add 34 b + 2 selects 34 b |
| alu_add_W35 | 170 | 205.6 | 258 | 262 | 0.98 | add 35 b |
| alu_lend_W35 | 268 | 350.9 | 440 | 424 | 1.04 | add 35 b + 2 selects 35 b |
| alu_add_W36 | 182 | 216.5 | 271 | 270 | 1.00 | add 36 b |
| alu_lend_W36 | 272 | 354.0 | 444 | 436 | 1.02 | add 36 b + 2 selects 36 b |
| alu_add_W37 | 183 | 219.2 | 275 | 278 | 0.99 | add 37 b |
| alu_lend_W37 | 269 | 363.6 | 456 | 448 | 1.02 | add 37 b + 2 selects 37 b |
| alu_add_W38 | 198 | 234.9 | 294 | 285 | 1.03 | add 38 b |
| alu_lend_W38 | 294 | 379.1 | 475 | 460 | 1.03 | add 38 b + 2 selects 38 b |
| alu_add_W39 | 192 | 230.1 | 288 | 292 | 0.99 | add 39 b |
| alu_lend_W39 | 290 | 384.4 | 482 | 472 | 1.02 | add 39 b + 2 selects 39 b |
| alu_add_W40 | 199 | 237.3 | 297 | 300 | 0.99 | add 40 b |
| alu_lend_W40 | 303 | 394.7 | 495 | 484 | 1.02 | add 40 b + 2 selects 40 b |
| alu_add_W41 | 204 | 243.7 | 305 | 308 | 0.99 | add 41 b |
| alu_lend_W41 | 313 | 409.4 | 513 | 496 | 1.03 | add 41 b + 2 selects 41 b |
| alu_addp_W32 | 161 | 185.1 | 232 | 240 | 0.97 | add 32 b |
| alu_mul31 | 5832 | 6,429.2 | 8,057 | 5,766 | 1.40 | 31 x 31 partial products |
| alu_mul31_en | None | 6,489.6 | 8,132 | 5,909 | 1.38 | 31 x 31 + select 62 b |
| alu_mul31_p2 | None | 7,357.0 | 9,219 | 7,164 | 1.29 | 31 x 31 + 233 stage flip-flops x 6 |
| alu_mul31_en_p2 | None | 7,415.8 | 9,293 | 7,313 | 1.27 | 31 x 31 + select 62 b + 234 flip-flops x 6 |
| alu_fold_H1 | 1 | 1.6 | 2 | 8 | 0.27 | add 1 b (increment) |
| alu_fold_H4 | 7 | 9.6 | 12 | 30 | 0.40 | add 4 b (increment) |
| alu_fold_H5 | 10 | 12.5 | 16 | 38 | 0.42 | add 5 b (increment) |
| alu_fold_H6 | 11 | 14.9 | 19 | 45 | 0.41 | add 6 b (increment) |
| alu_fold_H8 | 16 | 20.7 | 26 | 60 | 0.43 | add 8 b (increment) |
| alu_fold_H9 | 17 | 23.1 | 29 | 68 | 0.43 | add 9 b (increment) |
| alu_fold_H10 | 19 | 26.1 | 33 | 75 | 0.44 | add 10 b (increment) |
| alu_fold_H31 | 73 | 84.1 | 105 | 232 | 0.45 | add 31 b (increment) |
| alu_fold31 | 73 | 84.1 | 105 | 232 | 0.45 | add 31 b (increment) |
| alu_canon_W32 | 72 | 62.5 | 78 | 118 | 0.66 | compare 31 b + select 31 b |
| alu_canon_W31 | 72 | 62.5 | 78 | 118 | 0.66 | compare 31 b + select 31 b |
| alu_negm31_W33 | 31 | 16.5 | 21 | 232 | 0.09 | subtract 31 b |
| alu_bar_chunk_W8 | 23 | 25.0 | 31 | 39 | 0.80 | per bit: 2 and + 1 xor (3-input and) |
| alu_bar_chunk_W7 | 18 | 18.9 | 24 | 25 | 0.94 | per bit: 1 and + 1 xor |
| alu_bar31 | 87 | 93.9 | 118 | 143 | 0.82 | 3 x 8-bit + 7-bit chunks |
| alu_xor | 64 | 102.1 | 128 | 147 | 0.87 | xor 64 b |
| rot31_R7 | 0 | 0.0 | 0 | 0 | - | wiring |
