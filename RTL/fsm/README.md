# RTL/fsm - the accelerator: the bz3 unit + sequencer + SRAM + FSM, memory and compute in parallel

The unit (`RTL/pe/unit_bz3.sv`, generated from the HLS C++ and verified clock by clock) executes the program that the
software compiler produces: `dse/TOP/verify/compile_tree.py` turns a Merkle or GGM tree into atomic per-cycle operations
(which ring issues, which block positions, round indices), so the unit has no run-time scheduling and no mode muxes. The
hardware around it is hand-written SystemVerilog: a sequencer that runs the compiled stream on the unit, the on-chip SRAM,
the program memories, and the FSM that moves data between the HBM and the SRAM while the unit computes.

| file | module | what |
|---|---|---|
| `unit_cfg.sv` | package | the unit's lane map: 54 blocks of 22 lanes, the 14 ARX rings (first-span blocks, last-span blocks, span chains), the two Monolith datapaths (lanes 1188, 1240) |
| `lane_fmt.sv` | `arx_fmt`, `mono_fmt` | the input lanes of one issue from the SRAM values and the descriptor: BLAKE3 parent `compress(IV, l ‖ r, PARENT [‖ ROOT])`, BLAKE3-XOF / ChaCha20 GGM node from the seed, idx, level; Monolith state `l ‖ r` |
| `lane_cap.sv` | `arx_cap`, `mono_cap` | the result of a finished node from the output lanes (chaining value; the two GGM children; the 8 Monolith elements, canonical) |
| `seq.sv` | `seq` | the sequencer: one control word per cycle (mono, blake, r, rg, issue / finish bit per ring); on an issue it pops the ring's next descriptor group, reads the SRAM, formats the lanes; every cycle it recirculates each ring's last-span lanes into its first span and passes each span to the next of its chain (ChaCha20 across the two copies); on a finish it captures the result from the previous output vector (a register: the HLS call computes out from the registers before the update) and writes the SRAM; program slots are relative, translated by three regions + the root slot |
| `mems.sv` | `slot_sram`, `prog_mem`, `ev_fifo` | the 32 B slot SRAM (NRP read / NWP + 1 write ports), the two program banks (control words, per-ring descriptor groups), the result FIFO to the HBM; behavioural, memory macros in synthesis |
| `accel_top.sv` | `accel_top` | the FSM: Merkle in tiles of 2^TK leaves (the tile program on buffer A / B, the next tile's leaves prefetched into the other buffer while the current tile computes, the tile roots on chip, the top program last); GGM: the top program expands the seed to the subtree seeds, each subtree program expands one to 2^TK leaves, double-buffered and streamed to the HBM; every finished node goes to the write FIFO as it finishes |
| `verify/build_prog.py` | | compiles the tile / subtree and top programs (`compile_tree.py ... hw=<dir>`, `noroot` for a tile) and the CPU-baseline expectation (BLAKE3 C library, Plonky3 Monolith, cpu_trees GGM) |
| `verify/tb_accel.cpp`, `verify/run_accel.sh` | | Verilator: the HBM model (latency, accesses per cycle), the programs loaded into the program banks, the tree run from the HBM and back, the root / leaves compared |
| `syn/syn_ctrl.sh` | | Yosys, Nangate45: the controller with the unit and the memories as black boxes |
| `mem/` | | the memory macros: FakeRAM2.0 (`fakeram45.cfg`, FreePDK45 bitcell 0.895 x 1.565 um measured from OpenRAM's cell) and OpenRAM (`*.py`) |

The program format (`compile_tree.py hw=`): a control word per cycle (306 bits: mono / mono2, htap, blake, r, r2, the 28
round indices, 16 issue bits, 16 finish bits) and, per ring, the descriptor groups in issue order (nb descriptors of 104
bits per issue, padded with invalid ones: kind, the two input slots, idx, level, root, the two result slots, valid).

## Results

(filled in from the Verilator runs, the controller synthesis and the memory compilers)
