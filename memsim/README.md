# memsim - UniZK's HBM model (Ramulator2 / RamSim) as the HBM of our tree simulator

`RTL/compiler/compile_tree.py` models the on-chip SRAM exactly (32 B slots, never exceeded, audited) but the HBM as an
ideal pipe: `bw=<B/cycle>`, reads and writes share it, no latency, no banks, no row buffer, no refresh. This folder replaces
that pipe with the cycle-level DRAM model UniZK uses: their RamSim, a fork of Ramulator2 (`ramsim/`, MIT, from
`D:\UniZK\thirdparty\ramsim`, commit 9c94b55 of the UniZK repo).

## What is ported, what differs

| | UniZK | here |
|---|---|---|
| DRAM, controller, scheduler, refresh, address mapping | Ramulator2 HBM2_4Gb, HBM2_2Gbps, Generic controller, FR-FCFS, all-bank refresh, RoBaRaCoCh | the same code; RoBaRaCoCh by default, MOP4CLXOR compared |
| frontend | open loop: the Rust model writes a trace (address, size, dependencies, a fixed compute delay per buffer block), `TraceGen` replays it | closed loop: `compile_tree.py` is the frontend. Every cycle it sends the reads / writes its SRAM model allows, ticks the HBM once, takes back the reads that completed |
| access size | 64 B per request (a request of n bytes = n / 64 requests) | 32 B per access = one SRAM slot (`channel_width: 128`: 2 x 128 bit), 1 KB rows |
| burst | preset nBL 4 | nBL 2 (JEDEC HBM2: a 64-bit pseudochannel moves 32 B with BL4 in 2 tCK). With 32 B accesses the preset gives half the JEDEC rate; `hnbl=4` runs the preset |
| channels | 128 | 1-8 per run (8 = one HBM2 stack, 256 GB/s) |
| clock | accelerator and DRAM 1:1 | the same: tCK 1 ns = the unit's 1 GHz |
| SRAM | read / write buffers per kernel, double buffering by block | ours, unchanged: a read reserves its slot when it is sent and is on chip when the HBM returns it; a write frees its slot when the controller accepts it (as RamSim) |

Files:

| file | what |
|---|---|
| `ramsim/` | UniZK's RamSim (Ramulator2). Changes: `src/base/utils.h` includes `<cstdint>` (g++ 13); `CMakeLists.txt` adds `../hbm_capi.cpp` to `libramulator.so` |
| `hbm_capi.cpp` | C interface (`hbm_new / hbm_send / hbm_tick / hbm_cmd`) and a controller plugin counting the issued commands (ACT, PRE, RD, WR, REF) |
| `hbm2.yaml` | our HBM: UniZK's config with the GEM5 (external) frontend, 128-bit channels, nBL 2, the channel count set per run |
| `hbm.py` | ctypes wrapper (`HBM`, `batch`) |
| `bench_hbm.py` | calibration: achieved B/cycle against the peak for sequential / random / row-sized patterns |
| `sweep.py` | the README memory-model workloads on the ideal pipe and on HBM2 at the same peak |
| `build_linux.sh` | builds `libramulator.so`, fetches Xilinx's open-source `ap_int` headers, builds the unit as `dse/TOP/verify/lz_16.so` / `lz3_16.so` and runs `check_axn.py` on them |
| `results/` | `bench_hbm.md`, `sweep.md`, `logs/` (every run's full output) |

`compile_tree.py` options: `hbm=<channels>` (on instead of `bw=`), `hmap=RoBaRaCoCh|MOP4CLXOR|ChRaBaRoCo`, `hnbl=2|4`,
`hport=<n>` (accesses sent per cycle, default = channels), `hlay=block|level|tile` (where stored nodes go). With `open=`, every
layout's open batch is also timed on the HBM2 model. The run prints the HBM2 commands, row-hit rate, bytes per activation,
read latency (send to data on chip) and how long the write buffers took to drain after the last cycle.

## The benchmark GPU's memory: GDDR6 (`gddr6.yaml`, `hbm.py` GDDR6, `compile_tree.py gddr=<channels>`)

The CPU / GPU baselines run on dana336's RTX 3070: 8 GB GDDR6, 8 x 8 Gb x32 chips = 16 channels x 16 bit at 14 Gb/s =
448 GB/s. The unit is compared at that memory, not an HBM stack: `gddr=<channels>` runs the Ramulator2 GDDR6 device model
with the RTX 3070's organization and clock (CK 1.75 GHz, ticked 7 times per 4 unit cycles; 32 B per access = BL16 x 16
bit, 2 CK per access per channel = 28 B/cycle per channel; 2 KB rows; 4 bank groups x 4 banks; JEDEC GDDR6 timings, tRFC
120 ns, tREFI 1.9 us; FR-FCFS, all-bank refresh, RoBaRaCoCh), `gddr=16` = the whole 448 GB/s for one core, `gddr=2` = one
core's share when 8 cores split the 16 channels (a static partition: every core owns 2 channels, no sharing between cores).
Calibration (`bench_hbm.py 2 16 --gddr`): sequential read 79-82% of the peak, sequential write 83-88%, row hit 98%, read
latency 60 cycles average (the HBM2 model: 80%, 50 cycles); calibrated before the refresh fix (with refresh: 44.2 instead of 44.4 B/cycle sequential at 2 channels).

Results (dana336, 2026-10-29; bz3s unit, 32 KB SRAM per core, DRAM refresh on, every run `audit` OK and bit-exact;
`sh memsim/run_gddr.sh` -> `results/logs18/*_gddr_*.log`):

| program | gddr=1 (16 cores, 28 GB/s each) | gddr=2 (8 cores, 56 GB/s each) | gddr=4 (4 cores) | gddr=16 (1 core, all 448 GB/s) | HBM2 2 ch (64 GB/s, no refresh) |
|---|---:|---:|---:|---:|---:|
| BLAKE3 Merkle 2^18 store=out | 381,123 (22.0 B/cycle) | 206,390 (40.6) | | 205,582 | 205,674 |
| ChaCha20 GGM 2^18 store=out | 366,433 (22.9) | 205,834 (40.8) | | | 205,662 |
| ChaCha20 GGM 2^18 store=k2 | | 242,346 (43.3) | 205,652 (51.0) | | 209,252 |
| BLAKE3 GGM 2^18 store=out | | 205,993 (40.7) | | | 205,637 |
| BLAKE3 GGM 2^18 store=k2 | | 243,069 (43.1) | 205,546 (51.0) | 205,569 | 209,280 |
| Monolith Merkle 2^16 store=all | | 231,345 (18.1) | | | 231,358 |
| Monolith Merkle 2^18 store=out | | 919,735 (9.1) | | | 919,735 |

- Refresh: Ramulator2's all-bank refresh took the rank count from a level GDDR6 / HBM2 do not have and never refreshed
  (REFab 0 in every earlier log; fixed 2026-10-29 with the GDDR6 PREA scope and refresh-first in the controller). With it the
  2-channel store=out runs take 0.06-0.34% more cycles (216 REFab each); the store=k2 runs at 2 channels +4% (233,2xx before).
  The HBM2 column and the older HBM2 tables below were run without refresh.
- Two GDDR6 channels per core (8 cores on the RTX 3070's 16 channels) run every store=out program and Monolith at the compute
  bound (40.6-40.8 B/cycle of the 56 peak, 73%); the store=k2 GGM variants (51 B/cycle needed) are memory-bound at 2 channels
  (+18%) and compute-bound at 4 (4 cores).
- One channel per core (16 cores): memory-bound at 22-23 B/cycle of 28 (79-82% of the peak), 1.8x the cycles.
- Latency: 63 cycles average read latency on the Merkle leaf stream (265 max with refresh), row hit 98%; the SRAM high-water
  stays at 4.6-28.8 KB, 32 KB per core holds.
- Not modeled: where the per-cycle instruction stream comes from (one word per cycle; no DRAM or SRAM traffic is charged
  for it), and the SRAM's access ports (only its capacity: the compute side needs 3.5 accesses of 32 B per cycle on
  average plus 1.3 DRAM fills, 12-15 in the cycles where a ring group starts and finishes).

## Run (Linux; dana336)

```bash
sh memsim/build_linux.sh                 # ~4 min: libramulator.so, ap_types, the unit models (lz_16, lz3_16, lz3s_16, natural units), check_axn ALL OK
sh memsim/run_gddr.sh                    # the GDDR6 runs above (13 in parallel, ~15 min)
python3 memsim/bench_hbm.py 1 2 4 8 --nbl 2 --nbl 4 --map RoBaRaCoCh --map MOP4CLXOR --md memsim/results/bench_hbm.md
python3 memsim/sweep.py 14                # every run with audit and the bit-exact check
cd dse/TOP && python3 ../../RTL/compiler/compile_tree.py verify/lz_16.so merkle blake3 16 sram=64 hbm=8 store=all audit open=1,64
```

## Results (dana336, 2026-10-27; every run `audit` OK and bit-exact; full tables `results/bench_hbm.md`, `results/sweep.md`, logs in `results/logs/`)

**Calibration** (`bench_hbm.py`, 32,768 accesses of 32 B per pattern, achieved B/cycle of the peak 32 B per channel per cycle):

| pattern | 1 channel | 8 channels | row hit | read latency avg / max |
|---|---:|---:|---:|---|
| sequential read, nBL 2 (JEDEC burst) | 25.7 (80%) | 208 (81%) | 97% | 50 / 66 |
| sequential read, MOP4CLXOR mapping | 29.9 (94%) | 240 (94%) | 97% | 44 / 76 |
| sequential read, Ramulator preset nBL 4 (UniZK as is) | 16.0 (50%) | 127 (50%) | 97% | 77 / 128 |
| random 32 B read | 8.8 (27%) | 67 (26%) | 0% | 136 / 241 |
| random 1 KB row, read whole | 21.2 (66%) | 163 (64%) | 74-97% | 59 / 105 |

With UniZK's preset (nBL 4) a 32 B access occupies a pseudochannel for 4 tCK, so a channel gives 16 B/cycle = half the
JEDEC rate; UniZK's traces count 64 B per request, which hides the factor. `hbm2.yaml` sets nBL 2. The remaining 20% under
the peak on sequential reads is the controller (one command per cycle per channel, read/write turnarounds, refresh).

**The tree programs** (64 KB SRAM, 2^18 ARX / 2^16 ZK, same peak bandwidth for the ideal pipe and the HBM2 model):

| workload | memory | peak B/cycle | cycles | vs ideal pipe at that peak |
|---|---|---:|---:|---:|
| BLAKE3 Merkle 2^18, store=all | ideal 172 (README) | 172 | 99,250 | |
| | HBM2 8 ch | 256 | 98,434 | +0.1% |
| | HBM2 4 ch | 128 | 174,118 | +31.2% (ideal 128: 132,671) |
| | HBM2 8 ch, nBL 4 (UniZK preset) | 256 | 154,175 | +56.8% |
| ChaCha20 GGM 2^18, store=all | HBM2 8 ch | 256 | 98,058 | +0.0% |
| | HBM2 4 ch | 128 | 163,144 | +23.2% |
| BLAKE3 GGM 2^18, store=all | HBM2 8 ch | 256 | 98,085 | +0.0% |
| BLAKE3 Merkle 2^18, store=out | HBM2 4 ch | 128 | 98,451 | +0.0% |
| | HBM2 2 ch | 64 | 165,615 | +24.5% (MOP4CLXOR +6.6%) |
| Monolith Merkle 2^16, store=all | HBM2 1 ch | 32 | 231,358 | +0.0% |
| Poseidon2 Merkle 2^16, store=all | HBM2 1 ch | 32 | 299,411 | +0.0% |
| | HBM2 1 ch, nBL 4 | 32 | 327,934 | +9.5% |

- One HBM2 stack (8 channels, 256 B/cycle peak) runs every ARX workload at the compute bound (+0.0-0.1% over the ideal
  pipe); the write stream is sequential (block rows staged in SRAM, ~650-940 B per activation, 95-97% row hits).
- Half a stack (4 channels, 128 B/cycle) is not enough for store=all at 2^18: the programs need ~170 B/cycle, and the
  HBM2 delivers 96-103 of the 128 (the ideal pipe at 128 is already +34%); store=out fits in 4 channels.
- The ZK hashes need one channel. UniZK's burst preset (nBL 4) costs +51-57% on the ARX workloads and +9.5% on Poseidon2.
- RoBaRaCoCh (UniZK's mapping) beats MOP4CLXOR on the write stream (+17-22% vs +0.0% at 8 channels): the staged rows are
  written whole, and interleaving them over bank groups breaks the row hits.
- Reads (Merkle leaves) see 66-78 cycles of latency on average under load; the SRAM double buffer hides it (the GGM
  programs read one seed only).
- Open batches (2^22, q = 1,024, 12,430 node reads on 8 channels): level 4,773 cycles, tile 4,863, block 5,971. The block
  layout has the fewest activations (8,774 vs 9,266) but the batch is a single address-ordered stream, so the fewer, longer
  rows serialize on fewer channels; per 1,024 openings the open costs ~5,000 cycles against a 1.55 M-cycle commit.

### Per-unit bandwidth share at the 10x design point (2026-10-28)

22 PEs on one GPU-class HBM budget (448 GB/s) give each unit about 100 B/cycle = 4 HBM2 channels of the model. 2^18 trees,
64 KB SRAM, Ramulator HBM2 (4 channels, 128 B/cycle peak), every run `audit` OK and bit-exact (`results/logs10x/`):

| workload | store | cycles | vs unconstrained | HBM B/cycle | transferring |
|---|---|---:|---:|---:|---:|
| BLAKE3 Merkle 2^18 | out | 98,451 | +0.2% | 85.2 (reads) | 98% |
| BLAKE3 Merkle 2^18 | k2 | 113,316 | +15.3% | 92.5 | 98% |
| BLAKE3 Merkle 2^18 | all | 174,118 | +77% | 96.4 | 99% |
| ChaCha20 GGM 2^18 | out | 98,062 | +0.4% | 85.5 (writes) | 67% |
| ChaCha20 GGM 2^18 | k2 | 103,360 | +5.8% | 101.4 | 84% |

At 100 B/cycle per unit, store=out runs at the compute bound (32 B per node), store=k2 costs 6-15%, store=all is
bandwidth-bound (64 B per node against the ~96 B/cycle the 4 channels deliver).
