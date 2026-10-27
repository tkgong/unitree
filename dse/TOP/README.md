# unitree TOP unit (bz) - HLS sources, software compiler / scheduler, simulator

One II=1 unit that runs ChaCha20 (GGM), BLAKE3 (Merkle, keyed-XOF GGM), Monolith-31 (Merkle) and Poseidon2-M31 (Merkle) on a
shared adder / multiplier array. No mode register and no hardware scheduler: software pre-compiles every request into a
per-cycle operation stream (per-issue bits). Older variants and results are in `D:\unitree\_archive_2026-10-23\` (same relative
paths, outside the repository); the CPU / GPU baselines are in `../../merkle_baseline/`, the ALUs in SystemVerilog in `../../RTL/`.

## Design

| part | what it does |
|---|---|
| 38 ARX blocks, 6 steps per traversal, two identical copies of the block groups | every add on the 912 lendable Concrete adders of the two datapaths. BLAKE3: one half-round per traversal (14 per node). ChaCha20: 1.5 rounds per traversal (14 per block: 80 round steps + 4 feed-forward steps), alternating the two copies; column <-> diagonal by the involution P |
| 2 Monolith-31 / Poseidon2-M31 datapaths, 18 levels | 3 ranks of 31x31 multipliers (Bricks squares; x^2 x^4 x^5), Karatsuba Concrete adder trees (lent to ARX, M_E hosted on them). Monolith: 7 issues per permutation. Poseidon2: initial M_E + 8 external rounds, 9 issues |
| 4 Poseidon2 internal-round engines (`p2_engine.h`) | one internal round per engine per cycle, latency 10 (x0^5 on 3 multipliers, part sum, M_I with 2^s as 31-bit rotations) |

## Files

| what | files |
|---|---|
| HLS top `lane_pipe` | `bz/pipe_axn.h`, `bz/lane_mono_kl.inc`, `bz/lane_mono2_kl.inc` (generated), `level_ops_axn.h` (ARX steps), `p2_engine.h`, `alu_core.h`, `level_ops.h`, `round_unit.h`, `lane_mono_rp1.inc`, constant tables `*.inc`, `../common/{lanes,field31}.h` |
| ALUs (`alu_core.h`) | every operator of the unit is a call: `alu_lend<W>` / `alu_add<W>` (the 912 lendable Concrete adders; `alu_add` is a non-inlined module, one instance per call), `alu_addp<W>` (private adders), `alu_mul31` / `alu_mul31_en` (31x31 multipliers), `alu_fold<H>` / `alu_fold31` / `alu_canon` / `alu_negm31` (M31 reduction), `alu_bar31` (Bars), `alu_xor` (ARX). Rotations, packing, P / sigma stay wiring. (`alu.h` is the older tree-datapath ALU set, only included through `round_unit.h`, never called by these units) |
| generators | `gen_lane_mono6.py` (datapath; uses `kara_dag.py`, `mono_constants.json`), `gen_pipe_axn.py` (ARX groups, copies, `--p2eng=4`) |
| software compiler + scheduler | `verify/compile_tree.py` (Merkle / GGM tree -> per-cycle instruction stream: ARX rings, ChaCha copy alternation, Poseidon2 programs, engine assignment; runs it on the simulator and checks every node), `verify/pos2_prog.py` (Poseidon2 program, `P2ProgEng`) |
| simulator | `verify/shim_axn.cpp` built by `../verify/build_dll.sh` into `verify/lz_16.dll` (one call = one clock, entry `lp_step_e`); `verify/check_axn.py` checks it issue by issue against `verify/models.py` (RFC 8439, official BLAKE3, Plonky3 KATs) |
| review checks | `verify/compile_tree.py ... audit` (memory-model invariants, open reconstruction), `verify/verify_layout.py` (HBM layouts / row staging), `verify/diff_dll.py old.dll new.dll` (random-cycle differential test of two builds), `verify/verify_area.py` (area / sharing from the csynth reports) |
| flattened tops (no #if / HAS(), for reading) | `bz/pipe_axn_flat.h` (four primitives), `bz3/pipe_axn_flat.h` (ChaCha20 + BLAKE3 + Monolith, no Poseidon2: Monolith-only datapaths, no engines; DLL `verify/lz3_16.dll`); made by `flatten_pipe.py <pipe_axn.h> <out> 0x16`, then `inline_flat.py <out>`: every datapath level (`monk_lx<k>`), ARX step (`axn_ops<j>` / `axn_fin<j>`) and engine (`p2eng<E>`) call is replaced by its body, so `lane_pipe` itself is written as `alu_core.h` calls (912 `alu_lend`, ...) plus wiring; synthesis configs `syn/bz_16f_flat`, `syn/bz3_flat` compile these files. The included files only supply constants and wiring helpers; `level_ops_axn_flat.h` comes from `flatten_ops.py` |
| natural comparison units | `pwe/` (Poseidon2 only + 4 engines, `verify/lpwe_10.dll`), `nat38c/` (ChaCha20 only, 1.5 rounds per traversal, `verify/lnc_04.dll`) |
| synthesis configs | `syn/bz_16f` (four primitives), `syn/bz_12e` (BLAKE3 + Monolith + Poseidon2), `syn/bz_10e` (Monolith + Poseidon2), `syn/pwe_10`, `syn/n38c_04`; run with `sh ../run_dse.sh /d/unitree/dse/TOP/syn/bz_16f` |

```
sh build_all.sh                                                 # regenerate bz/ bz3/ pwe/ nat38c/ and the flattened tops, build all DLLs, bit-exact checks
sh build_bz.sh                                                  # regenerate bz/, build verify/lz_16.dll, bit-exact check (ALL OK)
python verify/compile_tree.py verify/lz_16.dll merkle pos2 14 fifo
python verify/compile_tree.py verify/lz_16.dll ggm chacha 14 deep
```

Run one Vitis csynth at a time: the array-partition step of a full unit commits 60-70 GB. Write ARX selects between scalar
copies of the lanes (as `level_ops_axn.h` does): `c ? S[i] : S[j]` on array elements becomes wide index-keyed muxes in Vitis.

## Measured (2026-10-24)

Throughput, compiled trees executed cycle by cycle, every node bit-exact (2^22 leaves / seeds; 1 GHz is an assumption). All five rows were re-run on the current verify/lz_16.dll on 2026-10-26/27 (identical cycles, every node checked; scratchpad `t22`):

| workload | cycles | nodes per cycle | bound |
|---|---:|---:|---:|
| BLAKE3 Merkle | 1,546,104 | 2.71 | 912 / 336 |
| BLAKE3-XOF GGM | 1,546,311 | 2.71 | 912 / 336 |
| ChaCha20 GGM | 1,546,338 | 2.71 | 912 / 336 |
| Monolith-31 Merkle | 14,680,687 | 0.286 | 2 / 7 |
| Poseidon2-M31 Merkle | 18,876,157 | 0.222 | 2 / 9 |

Area (csynth gate model of the archived report_axn.py, recomputed 2026-10-26 by `verify/verify_area.py` from the reports
in the work dirs) and sharing against natural units of the same throughput (n38c_04 ChaCha20 1,847,391, n38_02 BLAKE3
2,310,700, btf_10 Monolith 738,834, pwe_10 Poseidon2 1,253,786). The reports synthesized before the ALU refactor (`*_prealu`)
give 792 more gates for bz_16f and pwe_10 (a renamed 132-bit register that the gate model's name rule counts differently; the
utilization tables are identical) and the same percentages:

| unit | gates | logic | ALU | registers | total |
|---|---:|---:|---:|---:|---:|
| bz_16f, four primitives | 4,152,774 | +19.0% | +39.2% | +39.9% | **+32.5%** |
| bz_12e, BLAKE3 + Monolith + Poseidon2 | 3,864,326 | +18.9% | +30.4% | +3.8% | +10.2% |
| bz_10e, Monolith + Poseidon2 | 1,642,653 | +17.4% | +21.1% | +18.0% | +17.6% |

bz_16f operators: 890 adders / 23,904 bits (separate 3,156 / 95,448), 1,355 xor, 108 multipliers (76 alu_mul31 + 32
alu_mul31_en). csynth utilization total: LUT 502,362, FF 567,466 (register rows 562,790).

## Memory model (2026-10-26, reviewed)

`compile_tree.py ... sram=<KB> bw=<B/cycle> store=all|out|k<K> [top<n>] [audit]`: one fixed on-chip SRAM of 32-byte slots,
never exceeded. Every value on chip takes a slot (a leaf read from HBM, a GGM seed, a result slot reserved when its node
issues, a result staged for its HBM row); a slot frees when its value has been consumed and, if it is stored, written. ARX
issues are planned LEAD = 2 cycles ahead: a Merkle parent takes over the slot of one freeable child for its result at plan
time, the other child frees at the issue cycle. `top<n>` keeps the top n levels resident on chip for the open (paid in SRAM;
default 0: the open reads them from HBM). `audit` checks while it runs: the SRAM count after every change (never above the
capacity) and recounted from the node states every 997 cycles; every issue has its inputs on chip and its outputs reserved;
every value written exactly once iff its level is stored; the HBM byte totals; at the end only the resident slots remain;
with open=, the openings are rebuilt from the nodes read (Merkle: all authentication paths to the root, together; GGM: the
co-path seeds cover every unpunctured leaf exactly once and no punctured one, each obtained from the reads by the counted
expansions, values equal to the tree's).

| | rule (CAP = SRAM / 32 B slots) |
|---|---|
| Merkle | subtree = 2^TK leaves, TK = log2(CAP / 4): the leaves of two subtrees in half the SRAM, the next prefetched while the current reduces (64 KB: 2^9 leaves) |
| GGM | subtree = 2^4 leaves (fixed; the SRAM sets how many are open), subtrees in DFS order; a node of any subtree but the oldest unfinished one issues only while the SRAM keeps a reserve (2 x 2^4 + 2 rows + depth + 8 slots) for the oldest; nothing is reserved up front. The nodes above the subtree roots (the DFS stack) run ahead by r x (age + (SZ - TK) x L_max) subtrees, all from the simulated pipeline, no fitted constant: L_max = slowest ring period x traversals (ARX 11 x 14 = 154 cycles), age = the oldest open subtree's lifetime (at least TK x L_max), r = subtrees finished per cycle measured over the last SZ x L_max cycles (at most theta / (2^TK - 1), theta = blocks / traversals = 2.714). `ahead=N` fixes the window (the old fitted window was 353); the older options `gsched=adm` and `gate=wt` deadlock at small SRAM (2 KB at 2^10) |
| both | results staged per 1 KB HBM row of the block layout and written when the row is complete; staging is bounded to CAP / 4 slots, beyond it the fullest row is written partial |

Pipeline depth does not change the Merkle subtree: it sets W, the nodes the pipeline holds (its ring slots: ARX 282,
Monolith 38, Poseidon2 128; measured in flight ARX ~278, Monolith ~35, Poseidon2 ~60), which drives the GGM lookahead and
the SRAM floor. The slowdown is not exactly independent of the tree size (fill and drain are fixed costs): 64 KB, store=all,
172 B/cycle: BLAKE3 Merkle 2^12 / 14 / 16 / 18 +4.0% / +1.5% / +0.8% / +1.0%; ChaCha GGM +0.3% / +0.9% / +1.6% / +1.3%.

All numbers below: final code, every run `audit` OK and bit-exact against the reference (Merkle: scratchpad `claims2`; GGM: `claims4`, with 45 more GGM runs at 1-16 KB, 2^8-2^12, store all / out / k2).

Every workload on the same 64 KB SRAM (unconstrained: BLAKE3 Merkle 2^18 98,275, ChaCha GGM 97,676, BLAKE3 GGM 97,556,
Monolith 2^16 231,293, Poseidon2 2^16 299,315):

| workload | HBM B/cycle | store | cycles | vs unconstrained | SRAM high-water | B per write activation (block) |
|---|---:|---|---:|---:|---:|---:|
| BLAKE3 Merkle 2^18 | 172 | all | 99,250 | +1.0% | 56.1 KB | 959 |
| BLAKE3 Merkle 2^18 | 86 | out | 99,422 | +1.2% | 12.1 KB | (root only) |
| ChaCha20 GGM 2^18 | 172 | all | 98,960 | +1.3% | 60.3 KB | 648 |
| ChaCha20 GGM 2^18 | 86 | out | 99,377 | +1.7% | 60.4 KB | 1,024 (leaves) |
| BLAKE3 GGM 2^18 | 172 | all | 98,958 | +1.4% | 60.4 KB | 646 |
| Monolith Merkle 2^16 | 32 | all | 231,326 | +0.0% | 38.0 KB | 959 |
| Poseidon2 Merkle 2^16 | 16 | all | 299,475 | +0.1% | 42.4 KB | 959 |

Smallest SRAM (2^16 ARX, 2^14 ZK; unconstrained 25,616 / 25,215 / 58,936 / 77,537):

| workload | store, HBM B/cycle | SRAM: cycles (slowdown) |
|---|---|---|
| BLAKE3 Merkle | out, 86 | 8 KB 33,470 (+30.7%); 12 KB 26,088 (+1.8%) |
| BLAKE3 Merkle | all, 172 | 16 KB 26,042 (+1.7%, 468 B per write activation); 32 KB 25,984 (+1.4%, 893 B) |
| ChaCha20 GGM | out, 86 | 32 KB 38,461 (+52.5%); 40 KB 28,451 (+12.8%); 48 KB 26,168 (+3.8%) |
| ChaCha20 GGM | all, 172 | 40 KB 27,494 (+9.0%); 48 KB 25,970 (+3.0%) |
| Monolith Merkle | all, 32 | 2 KB 59,018 (+0.1%); 4 KB 58,992 (+0.1%) |
| Poseidon2 Merkle | all, 16 | 2 KB 111,610 (+43.9%); 4 KB 77,666 (+0.2%) |

Deadlock: the unit has no run-time arbitration, it executes the compiled stream, so a program the simulator ran to the end
(every node checked) cannot deadlock on the unit: per program this is exact. For the GGM scheduler in general (gate=res): (1)
the values one subtree holds are a cut of it (unconsumed seeds, reserved children, unwritten leaves: at most its 2^TK leaves)
plus seeds consumed but not yet written (at most 2^TK - 1), so at most 2^(TK+1) - 1 = 31 slots; `audit` counts every subtree's
slots at every change and checks the bound (it is reached: 31); (2) everything except the oldest subtree and the path to its
root allocates only while the SRAM keeps the reserve (114-118 slots at 2^14-2^18) free; (3) so the oldest subtree always has
room for its next issue, finishes, and the next one becomes the oldest. Writes always drain (bandwidth > 0; staged rows
complete as later subtrees finish, or are flushed beyond CAP / 4). The remaining assumption, that leftovers of finished
subtrees (staged rows waiting for the next subtree) fit the reserve's margin of 2^TK + 2 rows, is argued, not machine-checked;
no run stopped (no-progress guard) in the sweeps, including 1-4 KB SRAM where the reserve is most of the SRAM.

Why GGM needs the reserve rule and Merkle does not: a Merkle issue frees two slots and takes one (its wide level comes from
HBM just in time); a GGM issue frees one and takes two, and its wide level is produced on chip from earlier results, so a
subtree starting from one seed needs ~8 issue latencies before it is ~278 nodes wide: several subtrees must be open at once,
and an SRAM full of seeds that cannot issue would deadlock. The run prints the SRAM split at the high-water (in flight /
waiting for the write / inputs waiting).

### Partial storage (`store=k<K>`)

Levels 1..K above the leaves are not written (Merkle: internal nodes; GGM: seeds; leaves are always in HBM: Merkle input, GGM
output). The open recomputes them from what is stored: a Merkle sibling at level l <= K from its 2^l leaves (2^l - 1 hashes);
a GGM co-path seed at level l <= K from the path node at level K + 1 (one expansion per path node between them, counted
once). Merkle writes drop to 2^-K of the internal nodes; GGM writes drop from leaves + seeds to leaves + 2^-K of the seeds.
64 KB SRAM, HBM bandwidth set to what the write stream needs (2^16 ARX, 2^14 ZK):

| workload | HBM B/cycle | store=all | store=k |
|---|---:|---:|---:|
| BLAKE3 Merkle | 129 | 33,910 (+32.4%) | k1 25,835 (+0.9%) |
| BLAKE3 Merkle | 108 | 40,180 (+56.9%) | k2 25,734 (+0.5%) |
| ChaCha20 GGM | 129 | 33,712 (+33.7%) | k1 25,629 (+1.6%) |
| ChaCha20 GGM | 108 | 40,014 (+58.7%) | k2 25,556 (+1.4%) |
| Monolith Merkle | 16 / 12 | 66,453 (+12.8%) | k1 59,061 (+0.2%) / k2 59,093 (+0.3%) |
| Poseidon2 Merkle | 8 / 6 | 133,403 (+72.0%) | k1 101,012 (+30.3%) / k2 111,660 (+44.0%) (reading the leaves alone needs ~7 B/cycle) |

Open of a 2^22 tree, q = 1,024 (`openonly`): nodes read / hashes recomputed (recompute cycles = hashes / measured throughput,
an estimate): BLAKE3 Merkle all 12,430 / 0, k1 13,432 / 1,024 (~378 cycles), k2 16,504 / 4,096 (~1,511); ChaCha GGM all
11,406 / 0, k1 11,384 / 1,024, k2 10,360 / 2,048; Monolith k1 13,432 / 1,024 (~3,580), k2 16,504 / 4,096 (~14,322); Poseidon2
k1 13,432 / 1,024 (~4,613).

### Open and HBM layout (`open=<q,..>`, `openonly`)

Open runs after the commit (the indices come from the root): Merkle authentication paths (leaf + sibling per level), GGM
punctures (co-path seeds), merged across the opened leaves. Layouts (leaves in their own array in all three; internal nodes
from the next 1 KB boundary): `level` (BFS), `tile` (Merkle subtree order), `block` (bands of 4 levels; a block = the 4
levels under one anchor node, 30 nodes = 960 B in one 1 KB row, level by level, sibling pairs in one 64 B burst). Checked by
`verify/verify_layout.py` (70 configurations, 2^2..2^13, every store mode): addresses distinct in all layouts, rows <=
1 KB, pairs in one burst, the staged row size equals the stored nodes that map to the row. Row activations per opened leaf,
1 KB rows, the batch read in address order (distinct rows):

| 2^22, q = 1 / 64 / 1024 | level | tile | block |
|---|---:|---:|---:|
| Merkle, store=all, top levels from HBM | 19.0 / 12.0 / 8.1 | 17.0 / 9.6 / 7.2 | **7.0 / 4.4 / 3.4** |
| Merkle, store=all, top8 resident | 15.0 / 11.9 / 8.1 | 13.0 / 9.5 / 7.2 | **5.0 / 4.3 / 3.4** |
| GGM, store=all, top levels from HBM | 19.0 / 12.0 / 8.1 | 17.0 / 9.5 / 5.8 | **7.0 / 4.4 / 3.4** |
| GGM, store=all, top8 resident | 15.0 / 11.9 / 8.1 | 13.0 / 9.4 / 5.8 | **5.0 / 4.3 / 3.4** |

Open traffic is small: 1,024 Merkle openings of a 2^22 tree read 12,430 nodes = 388 KB = 2,313 cycles at 172 B/cycle; the
cost is random rows, which the block layout cuts by 2.4-2.7x against level order. The commit's write stream is staged per
block row (bytes per activation in the 64 KB table above); the level and tile write counts the run also prints are measured
on that same block-ordered stream, so they are not a fair comparison of those layouts' own write cost.
