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

| program (cycles) | K = 0 (all) | k1 | k2 | k3 | k4 | k5 | out | model: traffic / 44 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| ChaCha20 GGM | 386,185 | 283,508 | 238,616 | 216,468 | **205,671** | 205,858 | 205,834 | 381k / 286k / 238k / 214k / fits / fits |
| BLAKE3 GGM | 388,093 | 283,486 | 238,773 | 216,621 | **205,966** | 205,851 | 205,993 | same |
| BLAKE3 Merkle | 408,012 | 321,089 | 238,616 (tile run) | 244,465 | 214,987 | **209,696** | 206,390 | same; reads + writes mixed |
| Monolith Merkle | **919,736** | | 919,736 | | 919,736 | | 919,735 | compute-bound at every K |

GGM: K = 4 is compute-bound as computed (the write stream alone). Merkle ARX: the same traffic costs +4.2% at K = 4 and +1.6%
at K = 5: its stream is reads (93% of the usable rate) plus writes, and the read / write turnarounds cost what the
bytes-only model does not see; the Merkle policy takes K = 5 (the margin), the GGM policy K = 4. Monolith: every K gives
the compute bound, K = 0 (store everything) is free.

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

Adaptive = the policy of sections 2.1-2.3 per primitive and direction: ARX Merkle TK 8 / K 5, ARX GGM TK 3 / K 4, Monolith
Merkle TK 6..8 / K 0. Rigid policies fix one setting for every program. Per-engine utilization in brackets (`ablation18/`,
`tile18/`, `store18/`; every run audited and bit-exact).

| policy | BLAKE3 Merkle | ChaCha20 GGM | BLAKE3 GGM | Monolith Merkle |
|---|---:|---:|---:|---:|
| **adaptive** | 209,696 (97.2%) | 205,491 (99.2%) | 205,508 (99.2%) | 919,736 (99.8%) |
| one subtree size for both directions: TK 8 (the Merkle one) | = | 247,827 (82%) **-17%** | 247,369 (82%) **-17%** | = |
| one subtree size for both directions: TK 3 (the GGM one) | 432,133 (47%) **-52%** | = | = | 977,309 (94%) -6% |
| one store policy: keep everything | 408,012 (50%) **-49%** | 386,185 (53%) **-47%** | 388,093 (53%) **-47%** | = |
| Monolith's settings for all (TK 6, keep everything) | 461,320 (44%) **-55%** | 448,875 (45%) **-54%** | 450,591 (45%) **-54%** | = |
| ARX's settings for all (K 4 / 5, TK 8 Merkle, TK 3 GGM) | = | = | = | 919,736 (99.8%): commit unchanged; **the open pays** (section 5) |

No rigid setting is good for both primitive classes. The settings that suit Monolith (store everything, mid-size tiles)
halve the ARX utilization; the settings that suit ARX cost Monolith nothing at commit time but make its opens recompute
what it could have stored for free, and with Monolith's 4.5x lower hash throughput that recompute is 7-10x the K = 0 open
(section 5: measured against the CPU and the GPU, `open18.md`).

## 5. The open: CPU / GPU / unit

`memsim/open18.py`, results in `open18.md` (adaptive K) and `open18_rigid.md` (the rigid store policies). The open of q
random leaves of a committed 2^18 tree = the proof (the opened leaves and the merged authentication-path siblings, 32 B
each, written out) plus, for Merkle, the paths hashed up to the root (log2 n = 18 compressions per opened leaf, shared
where paths merge); GGM = the co-path seeds (no compression chain). The same opened sets on the three platforms; the GPU's
proof and roots checked against the CPU's stored tree, the unit's against the Python reference and the committed root.
Unit: one core per tree, 2 GDDR6 channels; Merkle as one compiled program (`compile_tree.py open`: stored siblings read,
the K unstored levels recomputed from their leaves, every path hashed to the root, the proof written; closed loop on the
GDDR6 model, cycle by cycle, bit-exact); GGM = the co-path stream through the GDDR6 model + the recompute program. GPU:
RTX 3070, 8 trees per call, a gather kernel (the proof) + one kernel per level over the distinct path nodes; board power
minus idle. CPU: i7-10700K, 16 threads, level-synchronous over the distinct path nodes, 8 trees in sequence. 8 cores open
8 trees at once, so the unit's time for 8 trees = one core's cycles at 1 GHz. Energy: unit = idle 1.70 W (vectorless, no
data toggling) + (program power - idle) x engine utilization, over the program's cycles, DRAM not included; GPU board
minus idle, includes its GDDR6.

| program (adaptive K) | q | compressions / tree | unit us (engine util.) | GPU us (gather + paths) | CPU us | vs GPU | vs CPU | unit uJ / tree | GPU uJ / tree | energy vs GPU |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BLAKE3 Merkle, K 5 | 64 | 765 + 3,648 recomputed | 6.6 (52%) | 2.1 + 65.0 | 561 | 10.1x | 85x | 18 | 223 | 12x |
| | 1,024 | 8,325 + 55,924 | 60.7 (73%) | 14.9 + 75.0 | 856 | 1.48x | 14x | 194 | 750 | 3.9x |
| | 4,096 | 25,158 + ~140k | 165.0 | 40.8 + 136.2 | 2,366 | 1.07x | 14x | 534 | 2,224 | 4.2x |
| | 16,384 | 69,657 + ~215k | 285.2 | 102.3 + 280.3 | 6,229 | 1.34x | 22x | 880 | 6,067 | 6.9x |
| Monolith Merkle, K 0 | 64 | 765 | 4.9 (54%) | 2.1 + 405.4 | 2,175 | 83x | 442x | 14 | 914 | 66x |
| | 1,024 | 8,325 | 31.3 (93%) | 15.1 + 417.4 | 7,059 | 13.8x | 225x | 114 | 3,044 | 27x |
| | 4,096 | 25,158 | 93.4 | 41.0 + 672.5 | 18,299 | 7.6x | 196x | 341 | 8,122 | 24x |
| | 16,384 | 69,657 | 257.9 | 101.0 + 1,243.5 | 50,123 | 5.2x | 194x | 943 | 21,069 | 22x |
| ChaCha20 GGM, K 4 (= BLAKE3 GGM) | 64 | 0 (+ 256 expansions) | 2.0 | 1.8 | 18.6 | 0.94x | 9.5x | 4.4 | 8.9 | 2.0x |
| | 1,024 | 0 (+ 3,442) | 16.1 | 14.4 | 313 | 0.90x | 19x | 33 | 163 | 4.9x |
| | 16,384 | 0 (+ 35,095) | 102.5 | 81.7 | 474 | 0.80x | 4.6x | 237 | 1,081 | 4.6x |

- Merkle: the open is hash-bound at the unit (73-93% engine utilization from q = 1,024) and the unit wins by the same
  kind of margin as the commit does, reduced by its memory side (random 32 B reads on 2 channels run at ~22 B / cycle,
  half the sequential rate; writes are staged and burst). The GPU's path hashing is 18 dependent kernels: launch and
  latency bound below q ~ 1,000 (a Monolith permutation on one thread takes ~20 us; 55 us for BLAKE3's 18 levels), near its
  commit throughput at q = 16,384 (2.2 ns per Monolith compression, 0.5 ns per BLAKE3 one).
- GGM: no compressions; a random gather through a 2-channel core against the GPU's 16 channels: 0.8-0.9x, 4-5x less
  energy.
- End to end (commit + open, 8 trees, q = 1,024 / 16,384): BLAKE3 Merkle GPU 656 / 949 us vs unit 270 / 495 us (2.4x /
  1.9x); ChaCha20 GGM 1,176 / 1,244 vs 222 / 308 (5.3x / 4.0x); Monolith Merkle 4,013 / 4,925 vs 951 / 1,178 (4.2x / 4.2x).

The rigid store policies at the open (`open18_rigid.md`; the commit side is in section 4):

| | q = 64 | 256 | 1,024 | 4,096 | 16,384 |
|---|---:|---:|---:|---:|---:|
| Monolith open, K 4 (ARX's policy) vs K 0: unit us | 10.6 vs 4.9 | 34.1 vs 11.7 | 119.0 vs 31.3 | 373.2 vs 93.4 | 804.2 vs 257.9 |
| slower / more energy | 2.1x / 2.6x | 2.9x / 3.2x | **3.8x / 3.9x** | **4.0x / 4.1x** | **3.1x / 3.2x** |
| commit + open vs adaptive (commit 919.7 us either way) | +0.6% | +2.4% | **+8.7%** | **+28%** | **+46%** |
| BLAKE3 Merkle open, K 0 (keep everything) vs K 5: unit us | 4.4 vs 6.6 | 11.1 vs 19.9 | 30.2 vs 60.7 | 75.4 vs 165.0 | 159.5 vs 285.2 |
| commit + open vs adaptive (commit 408.0 vs 209.7 us) | 1.91x slower | 1.83x | 1.62x | 1.29x | **1.26x slower** |
| ChaCha20 GGM open, K 0 vs K 4: unit us | 2.2 vs 2.0 | 6.6 vs 5.7 | 20.0 vs 16.1 | 50.8 vs 44.0 | 105.6 vs 102.5 |

Both directions are significant: Monolith with ARX's K pays 3-4x at the open and up to +46% end to end at FRI-scale
query counts; ARX with Monolith's keep-everything is 1.3-1.9x slower end to end at every q (its open is faster, its commit
twice as slow); GGM with keep-everything loses on both.
