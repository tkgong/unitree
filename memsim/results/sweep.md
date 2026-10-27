| workload | memory | peak B/cycle | cycles | vs ideal at the same peak | achieved B/cycle | row hit | B per ACT | read latency avg / max | SRAM high-water KB | audit, check |
|---|---|---:|---:|---:|---:|---:|---:|---|---:|---|
| BLAKE3 Merkle 2^18, store=all | ideal 172 B/cycle (README) | 172 | 99,250 |  | 169.0 |  |  |  | 56.1 | audit OK, check OK |
| BLAKE3 Merkle 2^18, store=all | ideal 128 B/cycle | 128 | 132,671 |  | 126.5 |  |  |  | 43.3 | audit OK, check OK |
| BLAKE3 Merkle 2^18, store=all | HBM2 4 ch, RoBaRaCoCh | 128 | 174,118 | +31.2% | 96.4 | 96.6% | 938 | 78.1 / 382 | 43.6 | audit OK, check OK |
| BLAKE3 Merkle 2^18, store=all | HBM2 4 ch, MOP4CLXOR | 128 | 196,153 | +47.8% | 85.5 | 80.9% | 168 | 82.0 / 618 | 47.7 | audit OK, check OK |
| BLAKE3 Merkle 2^18, store=all | ideal 256 B/cycle | 256 | 98,348 |  | 170.6 |  |  |  | 58.6 | audit OK, check OK |
| BLAKE3 Merkle 2^18, store=all | HBM2 8 ch, RoBaRaCoCh | 256 | 98,434 | +0.1% | 170.4 | 96.5% | 907 | 65.9 / 245 | 58.5 | audit OK, check OK |
| BLAKE3 Merkle 2^18, store=all | HBM2 8 ch, MOP4CLXOR | 256 | 115,583 | +17.5% | 145.2 | 72.2% | 115 | 83.3 / 296 | 57.1 | audit OK, check OK |
| BLAKE3 Merkle 2^18, store=all | HBM2 8 ch, RoBaRaCoCh, Ramulator preset nBL 4 (UniZK) | 256 | 154,175 | +56.8% | 108.8 | 96.4% | 893 | 117.9 / 428 | 43.2 | audit OK, check OK |
| ChaCha20 GGM 2^18, store=all | ideal 172 B/cycle (README) | 172 | 98,960 |  | 169.5 |  |  |  | 60.3 | audit OK, check OK |
| ChaCha20 GGM 2^18, store=all | ideal 128 B/cycle | 128 | 132,452 |  | 126.7 |  |  |  | 60.5 | audit OK, check OK |
| ChaCha20 GGM 2^18, store=all | HBM2 4 ch, RoBaRaCoCh | 128 | 163,144 | +23.2% | 102.8 | 95.8% | 769 | 17.0 / 17 | 60.7 | audit OK, check OK |
| ChaCha20 GGM 2^18, store=all | HBM2 4 ch, MOP4CLXOR | 128 | 215,304 | +62.6% | 77.9 | 74.2% | 124 | 17.0 / 17 | 60.6 | audit OK, check OK |
| ChaCha20 GGM 2^18, store=all | ideal 256 B/cycle | 256 | 98,042 |  | 171.1 |  |  |  | 57.8 | audit OK, check OK |
| ChaCha20 GGM 2^18, store=all | HBM2 8 ch, RoBaRaCoCh | 256 | 98,058 | +0.0% | 171.1 | 95.1% | 654 | 17.0 / 17 | 57.8 | audit OK, check OK |
| ChaCha20 GGM 2^18, store=all | HBM2 8 ch, MOP4CLXOR | 256 | 119,456 | +21.8% | 140.4 | 74.5% | 125 | 17.0 / 17 | 60.6 | audit OK, check OK |
| ChaCha20 GGM 2^18, store=all | HBM2 8 ch, RoBaRaCoCh, Ramulator preset nBL 4 (UniZK) | 256 | 148,185 | +51.1% | 113.2 | 94.8% | 613 | 19.0 / 19 | 60.6 | audit OK, check OK |
| BLAKE3 GGM 2^18, store=all | ideal 172 B/cycle (README) | 172 | 98,958 |  | 169.5 |  |  |  | 60.4 | audit OK, check OK |
| BLAKE3 GGM 2^18, store=all | ideal 128 B/cycle | 128 | 132,452 |  | 126.7 |  |  |  | 60.4 | audit OK, check OK |
| BLAKE3 GGM 2^18, store=all | HBM2 4 ch, RoBaRaCoCh | 128 | 162,963 | +23.0% | 103.0 | 95.8% | 768 | 17.0 / 17 | 60.8 | audit OK, check OK |
| BLAKE3 GGM 2^18, store=all | HBM2 4 ch, MOP4CLXOR | 128 | 215,654 | +62.8% | 77.8 | 74.2% | 124 | 17.0 / 17 | 60.8 | audit OK, check OK |
| BLAKE3 GGM 2^18, store=all | ideal 256 B/cycle | 256 | 98,069 |  | 171.1 |  |  |  | 58.7 | audit OK, check OK |
| BLAKE3 GGM 2^18, store=all | HBM2 8 ch, RoBaRaCoCh | 256 | 98,085 | +0.0% | 171.0 | 95.2% | 664 | 17.0 / 17 | 58.7 | audit OK, check OK |
| BLAKE3 GGM 2^18, store=all | HBM2 8 ch, MOP4CLXOR | 256 | 119,499 | +21.9% | 140.4 | 74.5% | 125 | 17.0 / 17 | 60.5 | audit OK, check OK |
| BLAKE3 GGM 2^18, store=all | HBM2 8 ch, RoBaRaCoCh, Ramulator preset nBL 4 (UniZK) | 256 | 148,144 | +51.1% | 113.2 | 94.7% | 605 | 19.0 / 19 | 60.6 | audit OK, check OK |
| BLAKE3 Merkle 2^18, store=out | ideal 86 B/cycle (README) | 86 | 99,422 |  | 84.4 |  |  |  | 12.1 | audit OK, check OK |
| BLAKE3 Merkle 2^18, store=out | ideal 64 B/cycle | 64 | 132,974 |  | 63.1 |  |  |  | 8.6 | audit OK, check OK |
| BLAKE3 Merkle 2^18, store=out | HBM2 2 ch, RoBaRaCoCh | 64 | 165,615 | +24.5% | 50.7 | 96.9% | 1024 | 50.4 / 66 | 9.6 | audit OK, check OK |
| BLAKE3 Merkle 2^18, store=out | HBM2 2 ch, MOP4CLXOR | 64 | 141,791 | +6.6% | 59.2 | 96.9% | 1024 | 44.4 / 74 | 10.9 | audit OK, check OK |
| BLAKE3 Merkle 2^18, store=out | ideal 128 B/cycle | 128 | 98,414 |  | 85.2 |  |  |  | 33.7 | audit OK, check OK |
| BLAKE3 Merkle 2^18, store=out | HBM2 4 ch, RoBaRaCoCh | 128 | 98,451 | +0.0% | 85.2 | 96.9% | 1024 | 45.5 / 66 | 31.3 | audit OK, check OK |
| BLAKE3 Merkle 2^18, store=out | HBM2 4 ch, MOP4CLXOR | 128 | 98,423 | +0.0% | 85.2 | 96.9% | 1024 | 20.3 / 73 | 32.7 | audit OK, check OK |
| BLAKE3 Merkle 2^18, store=out | HBM2 4 ch, RoBaRaCoCh, Ramulator preset nBL 4 (UniZK) | 128 | 132,966 | +35.1% | 63.1 | 96.9% | 1024 | 77.3 / 128 | 13.1 | audit OK, check OK |
| Monolith Merkle 2^16, store=all | ideal 32 B/cycle (README) | 32 | 231,326 |  | 18.1 |  |  |  | 38.0 | audit OK, check OK |
| Monolith Merkle 2^16, store=all | ideal 32 B/cycle | 32 | 231,326 |  | 18.1 |  |  |  | 38.0 | audit OK, check OK |
| Monolith Merkle 2^16, store=all | HBM2 1 ch, RoBaRaCoCh | 32 | 231,358 | +0.0% | 18.1 | 96.7% | 980 | 74.2 / 399 | 31.3 | audit OK, check OK |
| Monolith Merkle 2^16, store=all | HBM2 1 ch, MOP4CLXOR | 32 | 231,351 | +0.0% | 18.1 | 78.7% | 150 | 95.2 / 395 | 31.2 | audit OK, check OK |
| Monolith Merkle 2^16, store=all | ideal 64 B/cycle | 64 | 231,307 |  | 18.1 |  |  |  | 38.0 | audit OK, check OK |
| Monolith Merkle 2^16, store=all | HBM2 2 ch, RoBaRaCoCh | 64 | 231,334 | +0.0% | 18.1 | 96.7% | 974 | 57.0 / 156 | 35.9 | audit OK, check OK |
| Monolith Merkle 2^16, store=all | HBM2 2 ch, MOP4CLXOR | 64 | 231,327 | +0.0% | 18.1 | 82.1% | 179 | 58.4 / 164 | 36.6 | audit OK, check OK |
| Monolith Merkle 2^16, store=all | HBM2 2 ch, RoBaRaCoCh, Ramulator preset nBL 4 (UniZK) | 64 | 231,351 | +0.0% | 18.1 | 96.7% | 974 | 105.0 / 269 | 32.8 | audit OK, check OK |
| Poseidon2 Merkle 2^16, store=all | ideal 16 B/cycle (README) | 16 | 299,475 |  | 14.0 |  |  |  | 42.4 | audit OK, check OK |
| Poseidon2 Merkle 2^16, store=all | ideal 32 B/cycle | 32 | 299,376 |  | 14.0 |  |  |  | 42.2 | audit OK, check OK |
| Poseidon2 Merkle 2^16, store=all | HBM2 1 ch, RoBaRaCoCh | 32 | 299,411 | +0.0% | 14.0 | 96.3% | 855 | 75.6 / 315 | 35.7 | audit OK, check OK |
| Poseidon2 Merkle 2^16, store=all | HBM2 1 ch, MOP4CLXOR | 32 | 299,396 | +0.0% | 14.0 | 87.0% | 245 | 65.9 / 412 | 40.9 | audit OK, check OK |
| Poseidon2 Merkle 2^16, store=all | HBM2 1 ch, RoBaRaCoCh, Ramulator preset nBL 4 (UniZK) | 32 | 327,934 | +9.5% | 12.8 | 96.8% | 986 | 173.8 / 911 | 21.4 | audit OK, check OK |

Open batches (openonly, 2^22, q = 1 / 64 / 1024), each layout's reads in address order on the HBM2 model:

BLAKE3 Merkle 2^22 open, HBM2 8 ch, RoBaRaCoCh:
    1         23     23.0      0.7        3       0       0 |                      19      17       7 |                  19.0   17.0    7.0
    HBM2 8 ch: level 27 cycles (27.3 B/cycle, ACT 20, row hit 13%, latency avg 19); tile 49 cycles (15.0 B/cycle, ACT 17, row hit 26%, latency avg 22); block 41 cycles (18.0 B/cycle, ACT 21, row hit 9%, latency avg 20)
    64      1,024     16.0     32.0      128       0       0 |                     768     614     280 |                  12.0    9.6    4.4
    HBM2 8 ch: level 408 cycles (80.3 B/cycle, ACT 838, row hit 18%, latency avg 82); tile 403 cycles (81.3 B/cycle, ACT 762, row hit 26%, latency avg 60); block 525 cycles (62.4 B/cycle, ACT 769, row hit 25%, latency avg 54)
    1024     12,430     12.1    388.4    1,554       0       0 |                   8,300   7,421   3,483 |                   8.1    7.2    3.4
    HBM2 8 ch: level 4,773 cycles (83.3 B/cycle, ACT 9,266, row hit 25%, latency avg 69); tile 4,863 cycles (81.8 B/cycle, ACT 9,666, row hit 22%, latency avg 71); block 5,971 cycles (66.6 B/cycle, ACT 8,774, row hit 29%, latency avg 55)
BLAKE3 Merkle 2^22 open, HBM2 8 ch, MOP4CLXOR:
    1         23     23.0      0.7        3       0       0 |                      19      17       7 |                  19.0   17.0    7.0
    HBM2 8 ch: level 23 cycles (32.0 B/cycle, ACT 22, row hit 4%, latency avg 18); tile 27 cycles (27.3 B/cycle, ACT 22, row hit 4%, latency avg 19); block 41 cycles (18.0 B/cycle, ACT 18, row hit 22%, latency avg 20)
    64      1,024     16.0     32.0      128       0       0 |                     768     614     280 |                  12.0    9.6    4.4
    HBM2 8 ch: level 434 cycles (75.5 B/cycle, ACT 870, row hit 15%, latency avg 57); tile 408 cycles (80.3 B/cycle, ACT 858, row hit 16%, latency avg 71); block 449 cycles (73.0 B/cycle, ACT 824, row hit 20%, latency avg 61)
    1024     12,430     12.1    388.4    1,554       0       0 |                   8,300   7,421   3,483 |                   8.1    7.2    3.4
    HBM2 8 ch: level 4,673 cycles (85.1 B/cycle, ACT 9,263, row hit 25%, latency avg 65); tile 5,042 cycles (78.9 B/cycle, ACT 10,398, row hit 16%, latency avg 73); block 5,083 cycles (78.3 B/cycle, ACT 8,670, row hit 30%, latency avg 53)
ChaCha20 GGM 2^22 open, HBM2 8 ch, RoBaRaCoCh:
    1         22     22.0      0.7        3       0       0 |                      19      17       7 |                  19.0   17.0    7.0
    HBM2 8 ch: level 27 cycles (26.1 B/cycle, ACT 19, row hit 14%, latency avg 19); tile 25 cycles (28.2 B/cycle, ACT 18, row hit 18%, latency avg 19); block 25 cycles (28.2 B/cycle, ACT 20, row hit 9%, latency avg 19)
    64        960     15.0     30.0      120       0       0 |                     768     608     280 |                  12.0    9.5    4.4
    HBM2 8 ch: level 364 cycles (84.4 B/cycle, ACT 774, row hit 19%, latency avg 81); tile 367 cycles (83.7 B/cycle, ACT 745, row hit 22%, latency avg 74); block 488 cycles (63.0 B/cycle, ACT 705, row hit 27%, latency avg 54)
    1024     11,406     11.1    356.4    1,426       0       0 |                   8,300   5,951   3,483 |                   8.1    5.8    3.4
    HBM2 8 ch: level 4,289 cycles (85.1 B/cycle, ACT 8,248, row hit 28%, latency avg 65); tile 4,131 cycles (88.4 B/cycle, ACT 7,719, row hit 32%, latency avg 61); block 5,490 cycles (66.5 B/cycle, ACT 7,756, row hit 32%, latency avg 50)
ChaCha20 GGM 2^22 open, HBM2 8 ch, MOP4CLXOR:
    1         22     22.0      0.7        3       0       0 |                      19      17       7 |                  19.0   17.0    7.0
    HBM2 8 ch: level 23 cycles (30.6 B/cycle, ACT 21, row hit 5%, latency avg 18); tile 23 cycles (30.6 B/cycle, ACT 20, row hit 9%, latency avg 18); block 27 cycles (26.1 B/cycle, ACT 17, row hit 23%, latency avg 19)
    64        960     15.0     30.0      120       0       0 |                     768     608     280 |                  12.0    9.5    4.4
    HBM2 8 ch: level 376 cycles (81.7 B/cycle, ACT 806, row hit 16%, latency avg 72); tile 362 cycles (84.9 B/cycle, ACT 771, row hit 20%, latency avg 71); block 438 cycles (70.1 B/cycle, ACT 760, row hit 21%, latency avg 56)
    1024     11,406     11.1    356.4    1,426       0       0 |                   8,300   5,951   3,483 |                   8.1    5.8    3.4
    HBM2 8 ch: level 4,209 cycles (86.7 B/cycle, ACT 8,251, row hit 28%, latency avg 62); tile 3,988 cycles (91.5 B/cycle, ACT 7,806, row hit 32%, latency avg 62); block 4,592 cycles (79.5 B/cycle, ACT 7,658, row hit 33%, latency avg 48)
