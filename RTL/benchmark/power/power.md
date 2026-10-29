# unit18 power with the switching activity measured on real programs (dana336, 2026-10-29)

Method (`power_vcd.sh`, all eight runs by `run_all.sh`): the timing-closed, repaired netlists of `syn/work_t10`
(`<top>_rep.v`, WNS 0.00 at 1 GHz), Nangate45 typical (1.1 V), 1 GHz clock, pre-placement.

1. The RTL (Verilator) replays a compiled program closed loop: a 2^12-leaf ARX tree or a 2^10-leaf Monolith tree
   (`test/make_traces.sh trp`), every node finish checked against the HLS unit, and writes every input and its `lout` per
   clock phase.
2. Icarus Verilog replays the same inputs on the gate netlist (zero delay, cell functions from the liberty), compares
   `lout` with the RTL's at every phase after the warm-up, and dumps every net over the program cycles 1000-1400 (steady
   state: the pipelines full).
3. Per net bit: transitions per 1 ns cycle and the fraction of time at 1, set on the driving cell's output pin; OpenSTA
   `report_power`: cell internal power + switching of the pin capacitances + leakage. No wires and no clock tree
   (pre-placement); the clock pins of the flip-flops toggle every cycle (the clock definition).

Every run: 2,844 clock phases replayed, **0 phases with `lout` different from the RTL**, 100% of the driven pins annotated.
The constant-0 output lanes of mono / shared (no datapath drives them) are left undriven by OpenROAD (no tie cells
pre-placement); they are tied to 0 for the replay and checked like every other bit.

| top | program | flip-flops | FF transitions / cycle | comb. transitions / cycle | sequential W | combinational W | leakage mW | **total W** |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| unit18_chacha | ChaCha20 GGM | 121,770 | 0.383 | 0.402 | 1.03 | 0.444 | 17 | **1.47** |
| unit18_blake3 | BLAKE3 Merkle | 149,418 | 0.399 | 0.416 | 1.26 | 0.460 | 19 | **1.72** |
| unit18_blake3 | BLAKE3 GGM | 149,418 | 0.311 | 0.336 | 1.22 | 0.382 | 19 | **1.60** |
| unit18_mono | Monolith-31 Merkle | 55,446 | 0.473 | 0.378 | 0.530 | 1.21 | 22 | **1.74** |
| unit18_shared | ChaCha20 GGM | 205,622 | 0.327 | 0.271 | 1.71 | 1.00 | 38 | **2.71** |
| unit18_shared | BLAKE3 Merkle | 205,622 | 0.390 | 0.276 | 1.75 | 1.02 | 39 | **2.76** |
| unit18_shared | BLAKE3 GGM | 205,622 | 0.326 | 0.246 | 1.70 | 0.928 | 38 | **2.63** |
| unit18_shared | Monolith-31 Merkle | 205,622 | 0.273 | 0.376 | 1.68 | 1.40 | 38 | **3.07** |

(The transition counts are per output bit of the flip-flops / combinational cells. "Sequential" includes the clock-pin
internal power of every flip-flop: 55-63% of the shared core's power, 70-76% of the ARX units', 30% of the Monolith unit's.
The flip-flops are clocked every cycle whether or not the program uses them; the design has no clock gating.)

## Energy per 2^18 tree against the RTX 3070

Energy per tree = power per core x cycles per tree of one core at 1 GHz (the GDDR6 2-channel runs of `memsim/README.md`;
8 cores run 8 trees at once, the energy per tree is one core's). GPU: RTX 3070 board power from nvidia-smi every 20 ms,
8 trees x 500 repetitions per call, kernels only (`RTL/baseline/run_energy.py`, `RTL/baseline/RESULTS_ENERGY_linux.md`).

| program 2^18 | cycles | shared core W | shared uJ / tree | natural unit W | natural uJ / tree | GPU above idle uJ | GPU board uJ | shared vs GPU above idle | natural vs GPU above idle |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ChaCha20 GGM | 205,707 | 2.71 | 557 | 1.47 | 302 | 26,006 | 33,122 | 46.7x | 86.0x |
| BLAKE3 GGM | 205,684 | 2.63 | 541 | 1.60 | 329 | 24,421 | 31,672 | 45.1x | 74.2x |
| BLAKE3 Merkle | 205,692 | 2.76 | 568 | 1.72 | 354 | 13,440 | 16,936 | 23.7x | 38.0x |
| Monolith-31 Merkle | 919,735 | 3.07 | 2,824 | 1.74 | 1,600 | 80,714 | 102,557 | 28.6x | 50.4x |

Not in the unit's numbers: wires and the clock tree (pre-placement), the SRAM (32 KB per core; FakeRAM2.0 has no access
energy, its clock energy is about 63 mW per core: an estimate, not measured), the DRAM (the GPU's board power includes its
GDDR6). The natural units' cycles are the shared unit's (the same programs; at 2^12 the natural BLAKE3 GGM schedule takes
3,947 cycles against the shared unit's 3,862, the other three are cycle-identical). CPU energy is not measured: RAPL is
root-only on dana336.

Raw outputs: `syn/work_t10/pw_<top>_<program>.out` (replay summary, annotation, report_power), `sta_*.log`, `time_gl.txt`
(Icarus compile 3-78 min per top, replay 14 min - 4.4 h per program).
