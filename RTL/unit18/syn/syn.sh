#!/bin/sh
# syn.sh - Yosys + ABC, Nangate45 area-only mapping of the hand-written tops (dana336). Two runs per top:
#   flat: synth -flatten  -> total, flip-flops, combinational
#   hier: the alu_* modules kept as hierarchy -> the ALU area (instances x area each) and the operator counts
# Results: $WORK/<top>_{flat,hier}.txt (default work); NET=1 also writes the flat gate netlist $WORK/<top>_flat.v (power / STA);
# ABC_D=<ps> maps for delay (abc -D: delay target, buffering and sizing) instead of area; ADDER=kogge-stone|sklansky|han-carlson
# maps the adders' carry chains ($lcu) as that parallel-prefix network (Yosys techmap +/choices) instead of the default;
# ABC_SPEED=1 maps with the ORFS abc_speed script (repeated SOP balancing for delay, buffer / upsize / dnsize against the
# library timing: the driving cell BUF_X1 and load 3.898 fF of the ORFS nangate45 config) instead of Yosys's default abc script.
# HFLAT=1 (hier mode): every module (each ALU, the ARX step operand / result logic) is mapped by ABC on its own, then the
# netlist is flattened and written as $WORK/<top>_flat.v (+ <top>_flat.txt): the ALUs keep the depth they get standalone
# (ABC on the flat design maps a 32-bit add at 2x the standalone depth).
#   sh syn.sh [top ...]    (shared mono chacha blake3)
cd "$(dirname "$0")"
LIB=/home/dana336/eda/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
SRC="../../alu_add.sv ../../alu_addp.sv ../../alu_lend.sv ../../alu_fold.sv ../../alu_fold31.sv ../../alu_addf.sv ../../alu_csa31.sv ../../alu_canon.sv ../../alu_bar_chunk.sv ../../alu_bar31.sv ../../alu_mul31_en_p2.sv ../../alu_xor.sv ../kara_pkg.sv ../mono_dp18.sv ../arx_group.sv ../axn_step.sv"
WK=${WORK:-work}
mkdir -p $WK
ORFS=/home/dana336/eda/OpenROAD-flow-scripts/flow
if [ -n "$ABC_SPEED" ]; then printf 'set_driving_cell BUF_X1
set_load 3.898
' > $WK/abc.constr; ABCS="-script $ORFS/scripts/abc_speed.script -constr $WK/abc.constr"; fi
for t in ${*:-shared mono chacha blake3}; do
  for mode in ${MODES:-flat hier}; do
    if [ $mode = flat ]; then FL="-flatten"; else FL=""; fi
    cat > $WK/$t.$mode.ys <<EOF
read_verilog -sv -I.. $SRC ../unit18_$t.sv
hierarchy -top unit18_$t
synth -top unit18_$t $FL ${ADDER:+-run :fine}
${ADDER:+techmap -map +/techmap.v -map +/choices/$ADDER.v}
${ADDER:+synth -top unit18_$t $FL -run fine:}
dfflibmap -liberty $LIB
abc ${ABC_D:+-D $ABC_D} $ABCS -liberty $LIB
opt_clean -purge
tee -o $WK/${t}_$mode.txt stat -liberty $LIB
EOF
    if [ -n "$NET" ] && [ $mode = flat ]; then echo "write_verilog -noattr $WK/${t}_flat.v" >> $WK/$t.$mode.ys; fi
    if [ -n "$HFLAT" ] && [ $mode = hier ]; then printf 'flatten\nopt_clean -purge\ntee -o %s stat -liberty %s\nwrite_verilog -noattr %s\n' $WK/${t}_flat.txt $LIB $WK/${t}_flat.v >> $WK/$t.$mode.ys; fi
    /usr/bin/time -a -o $WK/time.txt -f "$t $mode: %e s, %M KB" yosys -q -l $WK/$t.$mode.log $WK/$t.$mode.ys > /dev/null 2>&1
    tail -n 1 $WK/time.txt
  done
done
