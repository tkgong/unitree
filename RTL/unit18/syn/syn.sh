#!/bin/sh
# syn.sh - Yosys + ABC, Nangate45 area-only mapping of the hand-written tops (dana336). Two runs per top:
#   flat: synth -flatten  -> total, flip-flops, combinational
#   hier: the alu_* modules kept as hierarchy -> the ALU area (instances x area each) and the operator counts
# Results: $WORK/<top>_{flat,hier}.txt (default work); NET=1 also writes the flat gate netlist $WORK/<top>_flat.v (power / STA);
# ABC_D=<ps> maps for delay (abc -D: delay target, buffering and sizing) instead of area.
#   sh syn.sh [top ...]    (shared mono chacha blake3)
cd "$(dirname "$0")"
LIB=/home/dana336/eda/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
SRC="../../alu_add.sv ../../alu_addp.sv ../../alu_lend.sv ../../alu_fold.sv ../../alu_fold31.sv ../../alu_canon.sv ../../alu_bar_chunk.sv ../../alu_bar31.sv ../../alu_mul31_en_p2.sv ../../alu_xor.sv ../kara_pkg.sv ../mono_dp18.sv ../arx_group.sv ../axn_step.sv"
WK=${WORK:-work}
mkdir -p $WK
for t in ${*:-shared mono chacha blake3}; do
  for mode in ${MODES:-flat hier}; do
    if [ $mode = flat ]; then FL="-flatten"; else FL=""; fi
    cat > $WK/$t.$mode.ys <<EOF
read_verilog -sv -I.. $SRC ../unit18_$t.sv
hierarchy -top unit18_$t
synth -top unit18_$t $FL
dfflibmap -liberty $LIB
abc ${ABC_D:+-D $ABC_D} -liberty $LIB
opt_clean -purge
tee -o $WK/${t}_$mode.txt stat -liberty $LIB
EOF
    if [ -n "$NET" ] && [ $mode = flat ]; then echo "write_verilog -noattr $WK/${t}_flat.v" >> $WK/$t.$mode.ys; fi
    /usr/bin/time -a -o $WK/time.txt -f "$t $mode: %e s, %M KB" yosys -q -l $WK/$t.$mode.log $WK/$t.$mode.ys > /dev/null 2>&1
    tail -n 1 $WK/time.txt
  done
done
