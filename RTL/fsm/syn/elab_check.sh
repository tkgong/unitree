#!/bin/sh
# elab_check.sh - Yosys elaboration of pe_core (NB 4, all primitives): cell summary
cd "$(dirname "$0")/.."
yosys -q -p "read_verilog -sv ../alu_add.sv ../alu_addp.sv ../alu_lend.sv ../alu_fold.sv ../alu_fold31.sv ../alu_canon.sv ../alu_bar_chunk.sv ../alu_bar31.sv ../alu_mul31.sv ../alu_xor.sv mono_pkg.sv add_tree.sv mono_round.sv mono_core.sv arx_block.sv arx_ctrl.sv pe_core.sv; chparam -set NB 4 pe_core; hierarchy -top pe_core; proc; flatten; opt_clean; stat" 2>&1 | grep -E "Number of cells|ERROR|error|alu_|_add_|_mul_|_mux_|_xor_|_dff" | head -40
