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
(`memsim/README.md`, every run audited and bit-exact against the reference models); 8 cores run 8 trees at once:
ns per node = cycles / 8 / 262,143. CPU: i7-10700K, 16 threads, the fastest implementation per tree
(`RTL/baseline/RESULTS_CPU_TREES_linux.md`). GPU: RTX 3070, fused + optimized kernels, 8 trees per program, device-resident,
no PCIe (`RTL/baseline/RESULTS_GPU_TREES2_linux.md`). Trees of 2^18 leaves (262,143 nodes).

| workload | cycles / tree (1 core) | 8-core ns/node | CPU ns/node | GPU ns/node | vs CPU | vs GPU | W / core | 8-core W | uJ / tree | GPU uJ / tree (above idle) | energy vs GPU |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BLAKE3 Merkle | 205,692 | 0.0981 | 2.426 | 0.270 | 24.7x | 2.75x | 2.76 | 22.1 | 568 | 13,440 | 23.7x |
| ChaCha20 GGM | 205,707 | 0.0981 | 2.166 | 0.554 | 22.1x | 5.65x | 2.71 | 21.7 | 557 | 26,006 | 46.7x |
| BLAKE3 GGM | 205,684 | 0.0981 | 4.999 | 0.563 | 51.0x | 5.74x | 2.63 | 21.0 | 541 | 24,421 | 45.1x |
| Monolith-31 Merkle | 919,735 | 0.4386 | 54.30 | 1.707 | 123.8x | 3.89x | 3.07 | 24.6 | 2,824 | 80,714 | 28.6x |

Power: measured activity (`power/power.md`), per core, no wires / clock tree / SRAM / DRAM.

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
| logic (non-flip-flop cells) | 8.5% | 31.8% |
| registers | 39.5% | 37.0% |
| total | 30.1% | 34.5% |
