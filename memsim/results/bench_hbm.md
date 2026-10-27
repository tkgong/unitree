Ramulator2 HBM2 (UniZK RamSim): 1 channel(s) x 128 bit at 2 Gb/s, tCK 1 ns, 32 B per access, nBL 2, 1 KB rows, FR-FCFS, all-bank refresh, RoBaRaCoCh; peak 32 B/cycle

| pattern | nBL | mapping | channels | peak B/cycle | cycles | achieved B/cycle | of peak | row hit | B per ACT | read latency avg / max (cycles) |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| sequential read | 2 | RoBaRaCoCh | 1 | 32 | 40,871 | 25.7 | 80% | 96.9% | 1,024 | 50.3 / 66 |
| sequential read | 2 | RoBaRaCoCh | 2 | 64 | 20,391 | 51.4 | 80% | 96.9% | 1,024 | 50.1 / 66 |
| sequential read | 2 | RoBaRaCoCh | 4 | 128 | 10,151 | 103.3 | 81% | 96.9% | 1,024 | 49.8 / 66 |
| sequential read | 2 | RoBaRaCoCh | 8 | 256 | 5,031 | 208.4 | 81% | 96.9% | 1,024 | 49.1 / 66 |
| sequential read | 2 | MOP4CLXOR | 1 | 32 | 35,020 | 29.9 | 94% | 96.8% | 1,009 | 44.4 / 76 |
| sequential read | 2 | MOP4CLXOR | 2 | 64 | 17,468 | 60.0 | 94% | 96.9% | 1,024 | 44.2 / 74 |
| sequential read | 2 | MOP4CLXOR | 4 | 128 | 8,773 | 119.5 | 93% | 96.9% | 1,024 | 44.3 / 75 |
| sequential read | 2 | MOP4CLXOR | 8 | 256 | 4,373 | 239.8 | 94% | 96.9% | 1,024 | 41.6 / 74 |
| sequential read | 4 | RoBaRaCoCh | 1 | 32 | 65,583 | 16.0 | 50% | 96.9% | 1,024 | 77.2 / 128 |
| sequential read | 4 | RoBaRaCoCh | 2 | 64 | 32,815 | 32.0 | 50% | 96.9% | 1,024 | 77.2 / 128 |
| sequential read | 4 | RoBaRaCoCh | 4 | 128 | 16,431 | 63.8 | 50% | 96.9% | 1,024 | 77.1 / 128 |
| sequential read | 4 | RoBaRaCoCh | 8 | 256 | 8,239 | 127.3 | 50% | 96.9% | 1,024 | 77.0 / 128 |
| sequential read | 4 | MOP4CLXOR | 1 | 32 | 65,987 | 15.9 | 50% | 95.8% | 768 | 77.7 / 133 |
| sequential read | 4 | MOP4CLXOR | 2 | 64 | 32,785 | 32.0 | 50% | 96.9% | 1,024 | 77.2 / 103 |
| sequential read | 4 | MOP4CLXOR | 4 | 128 | 16,403 | 63.9 | 50% | 96.9% | 1,024 | 77.1 / 107 |
| sequential read | 4 | MOP4CLXOR | 8 | 256 | 8,213 | 127.7 | 50% | 96.9% | 1,024 | 75.0 / 106 |
| sequential write | 2 | RoBaRaCoCh | 1 | 32 | 40,815 | 25.7 | 80% | 96.9% | 1,023 | - (writes complete at acceptance) |
| sequential write | 2 | RoBaRaCoCh | 2 | 64 | 20,335 | 51.6 | 81% | 96.9% | 1,022 | - (writes complete at acceptance) |
| sequential write | 2 | RoBaRaCoCh | 4 | 128 | 10,095 | 103.9 | 81% | 96.9% | 1,020 | - (writes complete at acceptance) |
| sequential write | 2 | RoBaRaCoCh | 8 | 256 | 4,975 | 210.8 | 82% | 96.9% | 1,016 | - (writes complete at acceptance) |
| sequential write | 2 | MOP4CLXOR | 1 | 32 | 34,854 | 30.1 | 94% | 96.9% | 1,023 | - (writes complete at acceptance) |
| sequential write | 2 | MOP4CLXOR | 2 | 64 | 17,427 | 60.2 | 94% | 96.9% | 1,022 | - (writes complete at acceptance) |
| sequential write | 2 | MOP4CLXOR | 4 | 128 | 8,732 | 120.1 | 94% | 96.9% | 1,020 | - (writes complete at acceptance) |
| sequential write | 2 | MOP4CLXOR | 8 | 256 | 4,330 | 242.2 | 95% | 96.9% | 1,017 | - (writes complete at acceptance) |
| sequential write | 4 | RoBaRaCoCh | 1 | 32 | 65,493 | 16.0 | 50% | 96.9% | 1,023 | - (writes complete at acceptance) |
| sequential write | 4 | RoBaRaCoCh | 2 | 64 | 32,725 | 32.0 | 50% | 96.9% | 1,022 | - (writes complete at acceptance) |
| sequential write | 4 | RoBaRaCoCh | 4 | 128 | 16,341 | 64.2 | 50% | 96.9% | 1,020 | - (writes complete at acceptance) |
| sequential write | 4 | RoBaRaCoCh | 8 | 256 | 8,149 | 128.7 | 50% | 96.9% | 1,016 | - (writes complete at acceptance) |
| sequential write | 4 | MOP4CLXOR | 1 | 32 | 65,756 | 15.9 | 50% | 95.9% | 785 | - (writes complete at acceptance) |
| sequential write | 4 | MOP4CLXOR | 2 | 64 | 32,709 | 32.1 | 50% | 96.9% | 1,022 | - (writes complete at acceptance) |
| sequential write | 4 | MOP4CLXOR | 4 | 128 | 16,326 | 64.2 | 50% | 96.9% | 1,020 | - (writes complete at acceptance) |
| sequential write | 4 | MOP4CLXOR | 8 | 256 | 8,138 | 128.8 | 50% | 96.9% | 1,016 | - (writes complete at acceptance) |
| random 32 B read (256 MB) | 2 | RoBaRaCoCh | 1 | 32 | 119,245 | 8.8 | 27% | 0.0% | 32 | 136.0 / 241 |
| random 32 B read (256 MB) | 2 | RoBaRaCoCh | 2 | 64 | 60,487 | 17.3 | 27% | 0.0% | 32 | 109.5 / 203 |
| random 32 B read (256 MB) | 2 | RoBaRaCoCh | 4 | 128 | 30,628 | 34.2 | 27% | 0.1% | 32 | 91.5 / 198 |
| random 32 B read (256 MB) | 2 | RoBaRaCoCh | 8 | 256 | 15,612 | 67.2 | 26% | 0.1% | 32 | 75.4 / 188 |
| random 32 B read (256 MB) | 2 | MOP4CLXOR | 1 | 32 | 119,289 | 8.8 | 27% | 0.0% | 32 | 136.0 / 231 |
| random 32 B read (256 MB) | 2 | MOP4CLXOR | 2 | 64 | 60,404 | 17.4 | 27% | 0.0% | 32 | 110.6 / 203 |
| random 32 B read (256 MB) | 2 | MOP4CLXOR | 4 | 128 | 30,693 | 34.2 | 27% | 0.1% | 32 | 89.9 / 210 |
| random 32 B read (256 MB) | 2 | MOP4CLXOR | 8 | 256 | 15,802 | 66.4 | 26% | 0.1% | 32 | 75.2 / 210 |
| random 32 B read (256 MB) | 4 | RoBaRaCoCh | 1 | 32 | 121,127 | 8.7 | 27% | 0.0% | 32 | 140.7 / 245 |
| random 32 B read (256 MB) | 4 | RoBaRaCoCh | 2 | 64 | 61,361 | 17.1 | 27% | 0.0% | 32 | 112.7 / 211 |
| random 32 B read (256 MB) | 4 | RoBaRaCoCh | 4 | 128 | 31,180 | 33.6 | 26% | 0.1% | 32 | 95.1 / 215 |
| random 32 B read (256 MB) | 4 | RoBaRaCoCh | 8 | 256 | 15,761 | 66.5 | 26% | 0.1% | 32 | 79.9 / 220 |
| random 32 B read (256 MB) | 4 | MOP4CLXOR | 1 | 32 | 121,159 | 8.7 | 27% | 0.0% | 32 | 140.7 / 223 |
| random 32 B read (256 MB) | 4 | MOP4CLXOR | 2 | 64 | 61,843 | 17.0 | 26% | 0.1% | 32 | 110.0 / 216 |
| random 32 B read (256 MB) | 4 | MOP4CLXOR | 4 | 128 | 31,193 | 33.6 | 26% | 0.1% | 32 | 96.0 / 219 |
| random 32 B read (256 MB) | 4 | MOP4CLXOR | 8 | 256 | 15,996 | 65.6 | 26% | 0.1% | 32 | 79.4 / 206 |
| random 1 KB-row read, whole row | 2 | RoBaRaCoCh | 1 | 32 | 49,513 | 21.2 | 66% | 96.9% | 1,016 | 59.0 / 105 |
| random 1 KB-row read, whole row | 2 | RoBaRaCoCh | 2 | 64 | 23,161 | 45.3 | 71% | 93.6% | 500 | 55.9 / 110 |
| random 1 KB-row read, whole row | 2 | RoBaRaCoCh | 4 | 128 | 11,351 | 92.4 | 72% | 86.6% | 238 | 55.4 / 127 |
| random 1 KB-row read, whole row | 2 | RoBaRaCoCh | 8 | 256 | 6,420 | 163.3 | 64% | 74.0% | 123 | 62.0 / 119 |
| random 1 KB-row read, whole row | 2 | MOP4CLXOR | 1 | 32 | 51,894 | 20.2 | 63% | 74.7% | 127 | 63.0 / 103 |
| random 1 KB-row read, whole row | 2 | MOP4CLXOR | 2 | 64 | 25,311 | 41.4 | 65% | 74.9% | 128 | 61.6 / 105 |
| random 1 KB-row read, whole row | 2 | MOP4CLXOR | 4 | 128 | 12,992 | 80.7 | 63% | 74.9% | 127 | 62.8 / 104 |
| random 1 KB-row read, whole row | 2 | MOP4CLXOR | 8 | 256 | 6,466 | 162.2 | 63% | 73.8% | 122 | 59.4 / 138 |
| random 1 KB-row read, whole row | 4 | RoBaRaCoCh | 1 | 32 | 95,307 | 11.0 | 34% | 96.1% | 811 | 107.2 / 302 |
| random 1 KB-row read, whole row | 4 | RoBaRaCoCh | 2 | 64 | 41,674 | 25.2 | 39% | 91.5% | 377 | 95.4 / 344 |
| random 1 KB-row read, whole row | 4 | RoBaRaCoCh | 4 | 128 | 18,872 | 55.6 | 43% | 82.4% | 182 | 88.1 / 353 |
| random 1 KB-row read, whole row | 4 | RoBaRaCoCh | 8 | 256 | 9,268 | 113.1 | 44% | 61.5% | 83 | 88.2 / 228 |
| random 1 KB-row read, whole row | 4 | MOP4CLXOR | 1 | 32 | 67,067 | 15.6 | 49% | 65.9% | 94 | 81.3 / 147 |
| random 1 KB-row read, whole row | 4 | MOP4CLXOR | 2 | 64 | 33,527 | 31.3 | 49% | 65.3% | 92 | 81.3 / 179 |
| random 1 KB-row read, whole row | 4 | MOP4CLXOR | 4 | 128 | 16,697 | 62.8 | 49% | 65.3% | 92 | 80.9 / 184 |
| random 1 KB-row read, whole row | 4 | MOP4CLXOR | 8 | 256 | 8,800 | 119.2 | 47% | 63.7% | 88 | 81.7 / 241 |
