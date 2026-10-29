# unit18 power with the switching activity measured on real programs (dana336, 2026-10-29)

Method (`power_vcd.sh`, all eight runs by `run_all.sh`): the timing-closed, repaired netlists of `syn/work_t10`
(`<top>_rep.v`, 1 GHz), Nangate45 typical (1.1 V), 1 GHz clock, pre-placement.

1. The RTL (Verilator) replays a compiled program closed loop: a 2^12-leaf ARX tree or a 2^10-leaf Monolith tree
   (`test/make_traces.sh trp`), every node finish checked against the HLS unit, and writes every input and its `lout` per
   clock phase.
2. Icarus Verilog replays the same inputs on the gate netlist (zero delay, cell functions from the liberty), compares
   `lout` with the RTL's at every phase after the warm-up, and dumps every net over the program cycles 1000-1400 (steady
   state: the pipelines full; mono over 2600-3000 gives the same power within 0.1%).
3. Per net bit: transitions per 1 ns cycle and the fraction of time at 1, set on the driving cell's output pin; OpenSTA
   `report_power`: cell internal power + switching of the pin capacitances + leakage, with the liberty's flip-flop power
   conditions written without QN (OpenSTA treats Q and QN as independent; with QN the clock-pin power of a flip-flop whose Q
   is at 1 half the time comes out at half). The clock net has no driver pre-placement, so its pin load is added:
   flip-flops x 0.9497 fF x 1.1 V^2 x 1 GHz. No wires, no clock tree.

Every run: 2,844 clock phases replayed, **0 phases with `lout` different from the RTL**, 100% of the driven pins annotated.
The constant-0 output lanes of mono / shared are left undriven by OpenROAD (no tie cells pre-placement); they are tied to 0
for the replay and checked like every other bit.

| top | program | flip-flops | FF transitions / cycle | comb. transitions / cycle | sequential W | combinational W | leakage mW | clock pins W | **total W** |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| unit18_chacha | ChaCha20 GGM | 121,770 | 0.383 | 0.402 | 1.413 | 0.444 | 17 | 0.140 | **2.00** |
| unit18_blake3 | BLAKE3 Merkle | 149,418 | 0.399 | 0.416 | 1.757 | 0.460 | 19 | 0.172 | **2.39** |
| unit18_blake3 | BLAKE3 GGM | 149,418 | 0.311 | 0.336 | 1.607 | 0.382 | 19 | 0.172 | **2.16** |
| unit18_mono | Monolith-31 Merkle | 55,446 | 0.473 | 0.378 | 0.745 | 1.208 | 22 | 0.064 | **2.02** |
| unit18_shared | ChaCha20 GGM | 205,622 | 0.327 | 0.271 | 2.254 | 1.001 | 38 | 0.236 | **3.49** |
| unit18_shared | BLAKE3 Merkle | 205,622 | 0.390 | 0.276 | 2.404 | 1.017 | 38 | 0.236 | **3.66** |
| unit18_shared | BLAKE3 GGM | 205,622 | 0.326 | 0.246 | 2.253 | 0.928 | 38 | 0.236 | **3.42** |
| unit18_shared | Monolith-31 Merkle | 205,622 | 0.273 | 0.376 | 2.135 | 1.397 | 38 | 0.236 | **3.77** |

(The transition counts are per output bit of the flip-flops / combinational cells. "Sequential" includes the clock-pin
internal power of every flip-flop, about 7 uW each: the flip-flops are clocked every cycle whether or not the program uses
them; the design has no clock gating.)

Not in these numbers: glitches (the replay is zero-delay; a unit-delay replay of mono over 100 cycles, 1 ps per cell, raised
the combinational transitions from 0.378 to 0.567 per cycle and the total from 1.95 to 2.52 W without the clock pins: an
estimate of the size, real cell delays differ), wires and the clock tree (pre-placement), the SRAM, the DRAM.

## Energy per 2^18 tree against the RTX 3070

Energy per tree = power per core x cycles per tree of one core at 1 GHz (the GDDR6 2-channel runs with refresh,
`memsim/README.md`; 8 cores run 8 trees at once, the energy per tree is one core's). GPU: RTX 3070 board power from
nvidia-smi every 20 ms, 8 trees x 500 repetitions per call, kernels only (`RTL/baseline/run_energy.py`,
`RTL/baseline/RESULTS_ENERGY_linux.md`; the idle figure is taken with a CUDA context open, 48 W).

| program 2^18 | cycles | shared core W | shared uJ / tree | natural unit W | natural uJ / tree | GPU above idle uJ | GPU board uJ | shared vs GPU above idle | natural vs GPU above idle |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ChaCha20 GGM | 205,834 | 3.49 | 718 | 2.00 | 411 | 26,006 | 33,122 | 36.2x | 63.3x |
| BLAKE3 GGM | 205,993 | 3.42 | 704 | 2.16 | 445 | 24,421 | 31,672 | 34.7x | 54.9x |
| BLAKE3 Merkle | 206,390 | 3.66 | 755 | 2.39 | 493 | 13,440 | 16,936 | 17.8x | 27.3x |
| Monolith-31 Merkle | 919,735 | 3.77 | 3,465 | 2.02 | 1,855 | 80,714 | 102,557 | 23.3x | 43.5x |

The SRAM (32 KB per core; FakeRAM2.0 has no access energy, its clock energy is about 63 mW per core: an estimate, not
measured) and the DRAM are not in the unit's numbers; the GPU's board power includes its GDDR6. The natural units' cycles
are the shared unit's (the same programs; at 2^12 the natural BLAKE3 GGM schedule takes 3,947 cycles against the shared
unit's 3,862, the other three are cycle-identical). CPU energy is not measured: RAPL is root-only on dana336.

Raw outputs: `syn/work_t10/pw_<top>_<program>.out` (replay summary, annotation, report_power, clock pins), `sta_*.log`,
`time_gl.txt` (Icarus compile 3-78 min per top, replay 14 min - 4.4 h per program). `PW_ONLY=1 power_vcd.sh` reruns the
power step on the activity files.
