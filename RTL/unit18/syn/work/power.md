# unit18 power (vectorless, pre-placement) and energy per tree vs the GPU (dana336, 2026-10-29)

Method: `syn/power.sh` = OpenSTA `report_power` on the timing-closed, repaired netlists of work_t10 (`<top>_rep.v`),
Nangate45 typical (1.1 V), 1 GHz clock, no placement: cell internal power + switching of the pin capacitances + leakage; no
wire capacitance, no clock tree, no SRAM. Three activity models: every net toggling 0.25 / 0.5 times per cycle (`-global`),
and 0.5 transitions per cycle on every data input propagated by OpenSTA through the logic (`-input`; over 1 on xor / multiplier
trees, an overestimate). Outputs `work_t10/<top>_power_<model>.out`.

| top (one core) | global 0.25 W | **global 0.5 W** | input 0.5 propagated W | leakage mW | flip-flops |
|---|---:|---:|---:|---:|---:|
| unit18_chacha | 1.06 | **1.67** | 3.64 | 17 | 121,770 |
| unit18_blake3 | 1.23 | **1.91** | 3.14 | 19 | 149,418 |
| unit18_mono | 1.13 | **2.03** | 6.94 | 22 | 55,446 |
| unit18_shared | 2.23 | **3.68** | 10.6 | 39 | 205,622 |

The shared unit's figure assumes every net active; with one primitive running per program the other primitive's logic is
idle (the Monolith multipliers under an ARX program, the ARX xors under Monolith), so its per-program power lies between the
natural unit's and this number. A vector-based figure (RTL VCD of a program replay annotated onto the netlist) was not done.

SRAM (one FakeRAM 4 KB macro `fakeram45_1024x32` in OpenSTA: clock energy 7.1 pJ per cycle independent of the access,
leakage 0.8 mW; the FakeRAM model has no access-dependent energy): 32 KB per core as 8 macros = 57 mW + 6 mW leakage =
**63 mW per core (estimate)**.

DRAM (not measured; literature: GDDR6 about 7.5 pJ/bit at the device, Micron / NVIDIA figures): the unit moves 8.4 MB per
2^18 tree (store=out) = 0.50 mJ; the GPU 25 MB = 1.5 mJ.

GPU energy measured (`merkle_baseline/run_energy.py`, RTX 3070 board power from nvidia-smi every 20 ms, 8 trees x 500
repetitions per call, kernels only, `RESULTS_ENERGY_linux.md`):

| program 2^18 | GPU us / tree | board W | idle W | mJ / tree | above idle mJ / tree |
|---|---:|---:|---:|---:|---:|
| BLAKE3 Merkle | 72.2 | 234.5 | 48.4 | 16.9 | 13.4 |
| BLAKE3-XOF GGM | 149.8 | 211.4 | 48.4 | 31.7 | 24.4 |
| ChaCha20 GGM | 147.0 | 225.3 | 48.4 | 33.1 | 26.0 |
| Monolith-31 Merkle | 451.3 | 227.2 | 48.4 | 102.6 | 80.7 |

CPU energy: RAPL is root-only on dana336 (perf_event_paranoid 3, no sudo); not measured.

Energy per 2^18 tree of one unit core (natural unit at global 0.5, cycles of the GDDR6 2-channel runs, + SRAM; DRAM
separately), against the GPU above idle:

| program | core W | cycles | core + SRAM uJ | + DRAM 7.5 pJ/bit uJ | GPU above idle uJ | ratio w/o DRAM | ratio with DRAM |
|---|---:|---:|---:|---:|---:|---:|---:|
| ChaCha20 GGM | 1.67 | 205,707 | 343 + 13 = 356 | 856 | 26,006 | 73x | 30x |
| BLAKE3 GGM | 1.91 | 205,684 | 393 + 13 = 406 | 906 | 24,421 | 60x | 27x |
| BLAKE3 Merkle | 1.91 | 205,692 | 393 + 13 = 406 | 906 | 13,440 | 33x | 15x |
| Monolith-31 Merkle | 2.03 | 919,735 | 1,867 + 58 = 1,925 | 2,425 | 80,714 | 42x | 33x |

With the board power instead of above-idle the GPU side is 1.26x higher. The 8-core system runs 8 trees at once; the
energy per tree is the same as one core's.
