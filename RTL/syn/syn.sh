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
# (ABC on the flat design maps a 32-bit add at 2x the standalone depth). KEEPALU=1 (flat mode): only the alu_* modules stay
# hierarchical through ABC (mapped standalone), everything else is flattened into the top before mapping; flattened after.
# KS45=1: the ARX / lent adders are the structural Nangate45 Kogge-Stone (alu_add_ks45.sv, `define KS45; the liberty cells
# are read as blackboxes and kept). KEEPCTL=1: the replicated control registers (arx_group r0_q / r8_q / bk_q, mono_dp18
# mpc) get the keep attribute on the $dff cells themselves, which is what stops opt_merge from merging the copies.
#   sh syn.sh [top ...]    (shared mono chacha blake3)
R=$(cd "$(dirname "$0")/.." && pwd); . "$R/env.sh"
cd "$R/syn"
SRC="$SRC_KS45 $SRC_ALU $SRC_BLK"
WK=${WORK:-work}
mkdir -p $WK
if [ -n "$ABC_SPEED" ]; then printf 'set_driving_cell BUF_X1
set_load 3.898
' > $WK/abc.constr; ABCS="-script $ORFS/scripts/abc_speed.script -constr $WK/abc.constr"; fi
for t in ${*:-$TOPS}; do
  for mode in ${MODES:-flat hier}; do
    if [ $mode = flat ] && [ -z "$KEEPALU" ]; then FL="-flatten"; else FL=""; fi
    if [ $mode = flat ] && [ -n "$KEEPALU" ]; then KA1="setattr -mod -set keep_hierarchy 1 *alu_*
flatten
opt_clean"; KA2="setattr -mod -unset keep_hierarchy *alu_*
flatten"; else KA1=""; KA2=""; fi
    cat > $WK/$t.$mode.ys <<EOF
${KS45:+read_liberty -lib $LIB}
read_verilog -sv ${KS45:+-DKS45} $INC $SRC $(top_sv $t)
hierarchy -top unit18_$t
${KEEPCTL:+proc}
${KEEPCTL:+select -set ctl w:*r0_q* w:*r8_q* %u w:*bk_q* %u w:*mpc* %u %ci1 t:\$dff %i}
${KEEPCTL:+setattr -set keep 1 @ctl}
synth -top unit18_$t $FL ${ADDER:+-run :fine}
${ADDER:+techmap -map +/techmap.v -map +/choices/$ADDER.v}
${ADDER:+synth -top unit18_$t $FL -run fine:}
$KA1
dfflibmap -liberty $LIB
abc ${ABC_D:+-D $ABC_D} $ABCS -liberty $LIB
opt_clean -purge
$KA2
opt_clean -purge
tee -o $WK/${t}_$mode.txt stat -liberty $LIB
EOF
    if [ -n "$NET" ] && [ $mode = flat ]; then echo "write_verilog -noattr $WK/${t}_flat.v" >> $WK/$t.$mode.ys; fi
    if [ -n "$HFLAT" ] && [ $mode = hier ]; then printf 'flatten\nopt_clean -purge\ntee -o %s stat -liberty %s\nwrite_verilog -noattr %s\n' $WK/${t}_flat.txt $LIB $WK/${t}_flat.v >> $WK/$t.$mode.ys; fi
    /usr/bin/time -a -o $WK/time.txt -f "$t $mode: %e s, %M KB" yosys -q -l $WK/$t.$mode.log $WK/$t.$mode.ys > /dev/null 2>&1
    tail -n 1 $WK/time.txt
  done
done
