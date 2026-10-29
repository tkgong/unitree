#!/bin/sh
# run_tb.sh - Verilator (dana336): build each hand-written top and replay its programs' traces closed loop.
#   sh run_tb.sh [top ...]         tops: shared mono chacha blake3 (default: all); traces in tr/<top>_*.tr
cd "$(dirname "$0")"
ALU="${KS45:+-DKS45 ../../alu_add_ks45.sv ../../nangate45_cells.sv} ../../alu_add.sv ../../alu_addp.sv ../../alu_lend.sv ../../alu_fold.sv ../../alu_fold31.sv ../../alu_addf.sv ../../alu_csa31.sv ../../alu_canon.sv ../../alu_bar_chunk.sv ../../alu_bar31.sv ../../alu_mul31_en_p2.sv ../../alu_xor.sv"
SRC="../kara_pkg.sv ../mono_dp18.sv ../arx_group.sv ../axn_step.sv"
for t in ${*:-shared mono chacha blake3}; do
  if [ ! -x obj_$t/Vunit18_$t ]; then
    rm -rf obj_$t
    verilator --cc --exe --build -j 12 -Wno-fatal -Wno-lint -O1 --top-module unit18_$t -Mdir obj_$t -I.. \
        -CFLAGS "-DVTOP=Vunit18_$t -DVTOP_H=\\\"Vunit18_$t.h\\\" -DTOPNAME=\\\"unit18_$t\\\"" \
        $ALU $SRC ../unit18_$t.sv tb_unit18.cpp > verilator_$t.log 2>&1 || { echo "== unit18_$t: build failed"; grep -E "%Error|error:" verilator_$t.log | head -n 8; continue; }
  fi
  for tr in tr/${t}_*.tr; do ./obj_$t/Vunit18_$t $tr | tail -n 7; done
done
