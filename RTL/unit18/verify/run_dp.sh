#!/bin/sh
# run_dp.sh - Verilator (dana336): mono_dp18 alone against dp_vec.txt (dp_vec.py).   sh run_dp.sh [NL]
cd "$(dirname "$0")"
NL=${1:-0}
rm -rf obj_dp
verilator --cc --exe --build -j 12 -Wno-fatal -Wno-lint -O1 --top-module mono_dp18 -GNL=$NL -Mdir obj_dp \
    ${KS45:+-DKS45 ../../alu_add_ks45.sv ../../nangate45_cells.sv} ../../alu_add.sv ../../alu_addp.sv ../../alu_lend.sv ../../alu_fold.sv ../../alu_fold31.sv ../../alu_addf.sv ../../alu_csa31.sv ../../alu_canon.sv ../../alu_bar_chunk.sv ../../alu_bar31.sv ../../alu_mul31_en_p2.sv \
    ../kara_pkg.sv ../mono_dp18.sv tb_dp.cpp > verilator_dp.log 2>&1 || { echo "build failed"; grep -E "%Error" verilator_dp.log | head -n 8; exit 1; }
./obj_dp/Vmono_dp18 dp_vec.txt
