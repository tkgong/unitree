# RTL/benchmark - the measurements

| directory | what | result |
|---|---|---|
| `timing/` | `sta.sh` (OpenSTA, 1 ns clock, pre-placement); the closure history and worst paths | `timing/timing.md` |
| `area/` | `report.py` (area and sharing from the Yosys stat files), `syn_blk.sh` + `wrap_shared_b.sv` (per-block area) | `area/area.md`, `timing/timing.md` (timing-closed netlists) |
| `power/` | `power_vcd.sh` (activity measured by a gate-level replay of real programs), `run_all.sh`, `vcd_act.cpp`, `act_tcl.py` | `power/power.md` |
| `sram/` | FakeRAM2.0 config and macro areas, OpenRAM config of the slot SRAM | `sram/fakeram45_areas.md` |

## Summary (dana336, 2026-10-29)

System: 8 cores of `unit18_shared` at 1 GHz (timing-closed on Nangate45, pre-placement), 32 KB SRAM per core, the RTX 3070's
GDDR6 (16 channels, 448 GB/s; 2 channels per core). Cycles per tree of one core from the Ramulator2 GDDR6 co-simulation
(`memsim/README.md`, with DRAM refresh; every run audited and bit-exact against the reference models); 8 cores run 8 trees
at once: ns per node = cycles / 8 / 262,143. CPU: i7-10700K, best of 1 / 8 / 16 threads, the fastest implementation per tree
(`RTL/baseline/RESULTS_CPU_TREES_linux.md`, re-measured 2026-10-29 on an idle machine, with the AVX2 BLAKE3-XOF GGM). GPU:
RTX 3070, fused + optimized kernels, 8 trees per program, device-resident, no PCIe
(`RTL/baseline/RESULTS_GPU_TREES2_linux.md`, as originally measured). Trees of 2^18 leaves (262,143 nodes).

| workload | cycles / tree (1 core) | 8-core ns/node | CPU ns/node (implementation) | GPU ns/node | vs CPU | vs GPU | W / core | 8-core W | uJ / tree | GPU uJ / tree (above idle) | energy vs GPU |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BLAKE3 Merkle | 206,390 | 0.0984 | 2.514 (BLAKE3 C hash_many) | 0.270 | 25.5x | 2.74x | 3.66 | 29.3 | 755 | 13,440 | 17.8x |
| ChaCha20 GGM | 205,834 | 0.0981 | 2.236 (AVX2) | 0.554 | 22.8x | 5.64x | 3.49 | 27.9 | 718 | 26,006 | 36.2x |
| BLAKE3 GGM | 205,993 | 0.0982 | 1.784 (AVX2) | 0.563 | 18.2x | 5.73x | 3.42 | 27.4 | 704 | 24,421 | 34.7x |
| Monolith-31 Merkle | 919,735 | 0.4386 | 56.17 (Plonky3) | 1.707 | 128.1x | 3.89x | 3.77 | 30.2 | 3,465 | 80,714 | 23.3x |

Power: `unit18_shared`, switching activity measured by a gate-level replay of each program (`power/power.md`), flip-flop
clock pins included; per core, no wires / clock tree / glitches / SRAM / DRAM. uJ / tree = W / core x cycles / tree.
The CPU Monolith baseline is Plonky3's p3-monolith (the fastest of the three measured); gcc does not vectorize our SoA
version, so a hand-vectorized CPU Monolith could be faster.

| area (Nangate45, timing-closed netlists) | per core mm^2 | 8 cores mm^2 |
|---|---:|---:|
| unit18_shared standard cells | 1.898 | 15.18 |
| SRAM 32 KB (FakeRAM2.0 model, 2.017 um^2 per bit; an estimate) | 0.529 | 4.23 |
| total | 2.427 | 19.42 |

Not included in the area: placement utilization, routing, clock tree, the GDDR6 PHY / memory controller, IO. The baselines
are on newer processes: RTX 3070 = GA104, Samsung 8 nm, 392.5 mm^2; i7-10700K = Intel 14 nm (die size not published; the
10-core Comet Lake die measures about 206 mm^2).

Sharing (`unit18_shared` against `unit18_mono + unit18_chacha + unit18_blake3`, the same throughput):

| | area-mapped (`area/area.md`) | timing-closed at 1 GHz (`timing/timing.md`) |
|---|---:|---:|
| logic (non-flip-flop cells) | 8.9% | 31.8% |
| registers | 39.7% | 37.0% |
| total | 30.4% | 34.5% |

Timing: WNS 0.00 at 1 ns on all four tops with every input driven by a flip-flop (`timing/timing.md`); `test/regress.sh`
rebuilds the four netlists byte-identical from the checkout.
