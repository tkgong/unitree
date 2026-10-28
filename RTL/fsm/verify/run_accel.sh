#!/bin/sh
# run_accel.sh - Verilator (Linux, dana336): build accel_top (the bz3 unit + sequencer + SRAM + FSM) once, then run the
# programs of build_prog.py against the CPU baselines.      sh run_accel.sh [prog dir ...] [-- lat bw]
cd "$(dirname "$0")"
LAT=60; BW=4
PROGS=""
while [ $# -gt 0 ]; do case $1 in --) LAT=$2; BW=$3; shift 3 ;; *) PROGS="$PROGS $1"; shift ;; esac; done
[ -z "$PROGS" ] && PROGS=$(ls -d prog_* 2>/dev/null)
SRC="../../alu_add.sv ../../alu_addp.sv ../../alu_lend.sv ../../alu_lendp.sv ../../alu_fold.sv ../../alu_fold31.sv ../../alu_canon.sv ../../alu_bar_chunk.sv ../../alu_bar31.sv ../../alu_mul31.sv ../../alu_mul31_en.sv ../../alu_negm31.sv ../../alu_xor.sv ../../rot31.sv ../../pe/dp_l1.sv ../../pe/dp_l2.sv ../../pe/dp_l3.sv ../../pe/dp_l4.sv ../../pe/dp_l5.sv ../../pe/dp_l6.sv ../../pe/dp_l7.sv ../../pe/dp_l8.sv ../../pe/dp_l9.sv ../../pe/dp_l10.sv ../../pe/dp_l11.sv ../../pe/dp_l12.sv ../../pe/dp_l13.sv ../../pe/dp_l14.sv ../../pe/dp_l15.sv ../../pe/dp_l16.sv ../../pe/dp_l17.sv ../../pe/dp_l18.sv ../../pe/axn_step.sv ../../pe/pe.sv ../../pe/unit_bz3.sv ../unit_cfg.sv ../lane_fmt.sv ../lane_cap.sv ../mems.sv ../seq.sv ../accel_top.sv"
if [ ! -x obj_accel/Vaccel_top ]; then
  rm -rf obj_accel
  verilator --cc --exe --build -j 12 -Wno-fatal -Wno-lint -O2 --top-module accel_top --public-flat-rw -Mdir obj_accel \
      -I../../pe $SRC tb_accel.cpp > verilator_accel.log 2>&1 || { echo "build failed"; grep -E "%Error" verilator_accel.log | head -n 10; exit 1; }
  echo "built obj_accel/Vaccel_top"
fi
for p in $PROGS; do
  echo "== $p (HBM latency $LAT, $BW accesses/cycle)"; ./obj_accel/Vaccel_top $p $LAT $BW | tee $p/run.log
done
