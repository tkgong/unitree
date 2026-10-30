# Memory policy per primitive: analysis, verification, ablation (2^18 trees, 32 KB SRAM, GDDR6 2 channels; dana336, 2026-10-30)

Every number below is a `compile_tree.py` run on the unit RTL/src implements (`verify/lz3s_16.so`), `sram=32 gddr=2 audit`,
every node bit-exact against the Python references (`run_tile.sh`, `run_store.sh`, `run_ablation.sh`; logs in `tile18/`,
`store18/`, `ablation18/`). Per-engine utilization = node traversals issued on an ARX ring / (its blocks x cycles), Monolith
issues / (2 datapaths x cycles); the compiler balances the rings within 0.2%, so one number per run is given (= compute bound /
cycles).

## 1. Parameters (from the hardware model and the DRAM model, nothing fitted)

| | ARX (ChaCha20 / BLAKE3) | Monolith-31 |
|---|---:|---:|
| throughput theta, nodes / cycle | 18 blocks / 14 traversals = 1.286 | 2 datapaths / 7 traversals = 0.286 |
| node latency L, cycles | 14 x 7 = 98 | 7 x 19 = 133 |
| nodes the pipeline holds, W | 126 | 38 |
| compute bound, cycles (262,143 nodes) | 203,889 | 917,501 |
| bytes per node (leaf read or result written) | 32 | 32 |
| DRAM rate the compute bound needs, 32 theta | 41 B / cycle | 9.1 B / cycle |
| DRAM usable, 2 GDDR6 channels | 44 B / cycle (78.6% of the 56 peak: the bandwidth-bound k2 run, 10.49 MB / 238,616 cycles) | |
| DRAM row-hit round trip (nRCDRD 26 + nCL 24 CK at 1.75 GHz) | 29 cycles before queueing | |
| SRAM | CAP = 1,024 slots of 32 B | |

## 2. Analysis

### 2.1 Which levels to store (K = levels above the leaves not written; the open recomputes them)

Cycles = max(compute bound, traffic(K) / 44) to within the memory model's few percent. Traffic: GGM writes the leaves (8.39 MB)
plus 32 x (2^(18-K) - 2) of seeds; Merkle reads the leaves (8.39 MB) plus writes 32 x (2^(18-K) - 1) of internal nodes.
Choose the smallest K whose traffic fits 44 x compute bound:

| K | traffic MB (GGM = Merkle) | ARX (fits 8.97 MB?) | Monolith (fits 40.4 MB?) |
|---|---:|---|---|
| 0 (all) | 16.78 | no: 381k cycles, utilization 53% | **yes: K = 0, store everything** |
| 1 | 12.58 | no: 286k | yes |
| 2 | 10.49 | no: 238k | yes |
| 3 | 9.44 | no: 214k (+5%) | yes |
| **4** | **8.91** | **yes: K = 4** | yes (unnecessary) |

Open cost of K = 4 per path: Merkle 2^5 - 6 = 26 hashes (the siblings of the bottom 4 levels from their 16 leaves) instead of
reading 4 nodes; GGM 2^4 - 1 = 15 expansions from the stored level-4 seed instead of reading 4 seeds. Monolith pays nothing:
its pipeline is 4.5x slower, so even all its levels fit the bandwidth (at 1 channel too: 22 x 917,501 = 20 MB > 16.8). The
policy is a function of theta and the channel count: at 4 channels (88 B / cycle, 17.9 MB) the ARX trees also keep everything.

### 2.2 Merkle subtree (bottom-up): the read window and the pipeline width

The tile pointer advances when the current tile's leaves are consumed and reads go one tile ahead, so the outstanding read
window is two tiles, 2^(TK+1) x 32 B. Three conditions:

1. Read stream (Little): window >= 32 theta x round trip. ARX runs the read stream at 41 / 44 = 93% of the usable rate, where
   queueing multiplies the 29-cycle row-hit latency; the sweep gives the effective round trip (window / achieved rate) 37, 62,
   110, 209 cycles at TK = 4..7, i.e. the window has to reach ~8 KB -> TK >= 7, with margin 8. Monolith's stream is at 21%
   of the rate, no queueing: 9.1 x ~40 = 364 B -> TK >= 3, not binding.
2. Pipeline width: the bottom levels of the two open tiles must offer W ready nodes: 2 x 2^(TK-1) >= W -> ARX TK >= 7,
   Monolith TK >= 6.
3. SRAM: 2^(TK+1) + W <= CAP -> TK <= 8 (TK = 9 nominally fills the SRAM with leaves; it runs because leaves stream in as
   slots free, 0.3% faster than 8).

Prediction: ARX TK = 8 (the compiler's log2(CAP / 4) rule); Monolith flat over TK = 6..8, degrading below 6.

### 2.3 GGM subtree (top-down): open subtrees x occupancy + the reserve

A subtree of 2^TK leaves has a critical path of TK x L cycles for 2^TK - 1 nodes, so N = theta TK L / (2^TK - 1) subtrees
must be open at once to sustain theta (ARX: 84, 54, 34, 20, 12, 7 at TK = 2..7). Each open subtree occupies at most one row
cut plus its seed, 2^TK + 1 slots (measured maximum: 5, 9, 17, 33, 65, 129 at TK = 2..7 - the bound 2^(TK+1) - 1 is never
reached), and the deadlock reserve kept free for the oldest subtree is RES = 2^(TK+1) + 64 + (18 - TK) + 8. Working set
N x (2^TK + 1) + RES against CAP = 1,024, plus up to 256 slots of rows staged for the write:

| TK | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---:|---:|---:|---:|---:|---:|
| N x (2^TK + 1) | 420 | 486 | 578 | 660 | 780 | 903 |
| RES | 98 | 102 | 118 | 149 | 212 | 339 |
| sum | 518 | 588 | 696 | 809 | 992 | 1,242 |

Prediction: flat at TK = 2..4, the reserve starts to throttle at 5, 6 is marginal, 7 does not fit. Below TK = 2 the stack
nodes above the subtrees (2^(18-TK) of them) and per-subtree bookkeeping grow; the write rows (1 KB = 32 leaves) are completed
across consecutive subtrees by the DFS order, so TK < 5 costs no row efficiency.

## 3. Verification (measured)

### 3.1 Store policy

| program | K = 0 (all) | k2 | k4 | out | model |
|---|---:|---:|---:|---:|---|
| ChaCha20 GGM | 386,185 | 238,616 | PENDING | 205,834 | 381k / 238k / compute-bound |
| BLAKE3 GGM | 388,093 | 238,773 | PENDING | 205,993 | |
| BLAKE3 Merkle | 406,546 (TK 9) | PENDING | PENDING | 206,390 | 381k / 238k / compute-bound |
| Monolith Merkle | PENDING | PENDING | PENDING | 919,735 | compute-bound at every K |

### 3.2 Merkle tile (store=out; compute bound 203,889)

| BLAKE3 Merkle | TK = 4 | 5 | 6 | 7 | **8** | 9 |
|---|---:|---:|---:|---:|---:|---:|
| cycles | 304,442 | 254,632 | 224,221 | 213,889 | **206,390** | 205,692 |
| engine utilization | 67.0% | 80.1% | 90.9% | 95.3% | **98.8%** | 99.1% |
| read rate achieved, B / cycle | 27.6 | 33.0 | 37.4 | 39.2 | 40.7 | 40.8 |

| Monolith Merkle (bound 917,501) | TK = 2 | 3 | 4 | 5 | **6** | 7 | 8 | 9 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| cycles, store=out | 966,418 | 939,473 | 928,036 | 919,962 | **919,735** | 919,735 | 919,735 | 919,735 |
| utilization | 94.9% | 97.7% | 98.9% | 99.7% | **99.8%** | 99.8% | 99.8% | 99.8% |
| cycles, store=all | 1,132,056 | 977,309 | 946,575 | 923,921 | 920,046 | 919,736 | 919,736 | 919,736 |
| SRAM high-water, out / all, KB | 1.9 / 7.2 | 2.2 / 8.1 | 2.6 / 8.4 | 3.6 / 9.3 | 5.6 / 10.9 | 9.5 / 14.6 | 16.4 / 21.9 | 31.2 / 32.0 |

As predicted: flat from TK = 6 (the pipeline-width condition 2^TK >= W = 38), the read window is never binding (the stream is
at 21% of the bandwidth), and the SRAM upper bound does not bite before TK = 9. Below 6 the pipeline starves (TK = 2: -5%
out, -19% all). The two primitives' Merkle tiles are limited by different things: ARX by the read stream's queueing (needs
8 KB in flight), Monolith by its pipeline width only.

### 3.3 GGM tile (compute bound 203,889)

| store=out | TK = 2 | **3** | 4 (old default) | 5 | 6 | 7 |
|---|---:|---:|---:|---:|---:|---:|
| ChaCha20 GGM cycles | 205,833 | **205,469** | 205,834 | 207,380 | 210,272 | 213,280 |
| utilization | 99.1% | **99.2%** | 99.1% | 98.3% | 97.0% | 95.6% |
| BLAKE3 GGM cycles | 205,680 | **205,467** | 205,993 | 207,499 | 209,885 | 214,326 |
| k2 (bandwidth bound 238k): ChaCha20 / BLAKE3 | 238,688 / 238,812 | **238,616 / 238,773** | 242,346 / 243,069 | 243,971 / 243,449 | 244,298 / 244,338 | 245,219 / 246,374 |
| all (bandwidth bound 381k): ChaCha20 / BLAKE3 | **386,185 / 388,093** | 435,381 / 438,408 | 445,383 / 444,809 | 452,978 / 447,964 | 448,875 / 450,591 | 439,489 / 446,239 |

The model's onset (TK = 5) and order hold. Not in the model: with store=all, TK >= 3 loses 12-17% - the rows staged for the
write exceed the CAP / 4 budget and are written partial (more activations); TK = 2 keeps them within it.

## 4. Ablation: adaptive policy vs one rigid policy for all

Adaptive = the policy of sections 2.1-2.3 per primitive and direction: ARX Merkle TK 8, ARX GGM TK 3, Monolith Merkle TK 6,
K = 4 for ARX, K = 0 for Monolith. Rigid policies fix one setting for every program.

PENDING (ablation18/)
