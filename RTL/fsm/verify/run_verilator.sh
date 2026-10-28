#!/bin/sh
# run_verilator.sh - Verilator (Linux, dana336): the depth-2 trees of tb_tree.cpp on every top, against the CPU baselines.
#   sh run_verilator.sh [top ...]        default: mono chacha blake3 shared      (vec_tree/tree.hex from gen_tree_vectors.py)
cd "$(dirname "$0")"
SRC="../../alu_add.sv ../../alu_addp.sv ../../alu_lend.sv ../../alu_fold.sv ../../alu_fold31.sv ../../alu_canon.sv ../../alu_bar_chunk.sv ../../alu_bar31.sv ../../alu_mul31.sv ../../alu_xor.sv ../mono_pkg.sv ../add_tree.sv ../mono_round.sv ../mono_core.sv ../cc_block.sv ../b3_block.sv ../arx_block.sv ../arx_ctrl.sv"
TOPS=${*:-"mono chacha blake3 shared"}
for t in $TOPS; do
  case $t in
    mono)   D="-DTOP_MONO -DTOP_NAT";   G="" ;;
    chacha) D="-DTOP_CHACHA -DTOP_NAT"; G="-GNB=2" ;;
    blake3) D="-DTOP_BLAKE3 -DTOP_NAT"; G="-GNB=2" ;;
    shared) D="-DTOP_SHARED";           G="-GNB=2" ;;
  esac
  rm -rf obj_$t
  verilator --cc --exe --build -j 8 -Wno-fatal -Wno-lint -O2 --top-module top_$t $G -Mdir obj_$t \
      -CFLAGS "$D -DTOPNAME=\\\"top_$t\\\"" $SRC ../top_$t.sv tb_tree.cpp > verilator_$t.log 2>&1 || { echo "== top_$t: build failed"; grep -E "%Error" verilator_$t.log | head -n 5; continue; }
  echo "== top_$t"; ./obj_$t/Vtop_$t | tee -a verilator_$t.log
done
