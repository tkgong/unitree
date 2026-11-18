#!/bin/sh
R=$(cd "$(dirname "$0")/../.." && pwd); . "$R/env.sh"
H=$R/flow/power; SB=${SIMBUF:-$R/test/simbuf.v}
cd "$R/syn"
WK=${WORK:-work_t10}; T=$1; shift; FROM=${FROM:-1000}; TO=${TO:-1400}
TR=${TRDIR:-$R/test/trp}
[ -f $WK/ng45_cells.v ] || yosys -q -p "read_liberty -ignore_miss_func $LIB; write_verilog -noattr $WK/ng45_cells.v"
[ -f $WK/ng45_power.lib ] || sed -E "/when/ s/ & !?QN//g" $LIB > $WK/ng45_power.lib
CKCAP=$(awk '/^\s*cell \(DFF_X1\)/ {c = 1} c && /pin \(CK\)/ {p = 1} c && p && /^\s*capacitance/ {gsub(/[;\t ]/, ""); split($0, a, ":"); print a[2]; exit}' $LIB)
[ -x $H/vcd_act ] || g++ -O2 -o $H/vcd_act $H/vcd_act.cpp
if [ ! -f $WK/${T}_gl.v ]; then
  TIE=""; grep -q "(zero_)" $WK/${T}_rep.v && TIE="connect -set zero_ 1'b0;"
  grep -q "(one_)" $WK/${T}_rep.v && TIE="$TIE connect -set one_ 1'b1;"
  echo "$T: $(grep -oE '\(lout\[[0-9]+\]\)' $WK/${T}_rep.v | sort -u | wc -l) lout bits driven by cells in ${T}_rep.v, the rest tied to 0" > $WK/${T}_gl.txt
  yosys -q -l $WK/${T}_gl.log -p "read_liberty -lib $LIB; read_verilog $WK/${T}_rep.v; hierarchy -top unit18_$T; $TIE setundef -undriven -zero; splitnets; rename -hide w:* c:*; rename -enumerate -pattern n%; write_verilog -noattr -noexpr $WK/${T}_gl.v; read_verilog -lib $SB; iopadmap -bits -outpad simbuf A:Z; splitnets; rename -enumerate -pattern s%; write_verilog -noattr -noexpr $WK/${T}_glsim.v"
fi
OBJ=$WK/obj_rtl_$T
if [ ! -x $OBJ/Vunit18_$T ]; then
  rm -rf $OBJ
  verilator --cc --exe --build -j 16 -Wno-fatal -Wno-lint -O1 --top-module unit18_$T -Mdir $OBJ $INC \
      -CFLAGS "-DVTOP=Vunit18_$T -DVTOP_H=\\\"Vunit18_$T.h\\\" -DTOPNAME=\\\"unit18_$T\\\"" \
      $SRC_ALU $SRC_BLK $(top_sv $T) $R/test/tb_unit18.cpp > $WK/verilator_rtl_$T.log 2>&1 \
      || { echo "== $T: verilator failed"; grep -E "%Error|error:" $WK/verilator_rtl_$T.log | head -n 5; exit 1; }
fi
W=$(grep -m1 -oE "input \[[0-9]+:0\] lin" $WK/${T}_gl.v | grep -oE "[0-9]+" | head -n 1); W=$((W + 1))
RG=$(grep -m1 -oE "input \[[0-9]+:0\] rg" $WK/${T}_gl.v | grep -oE "[0-9]+" | head -n 1); RG=$((RG + 1))
PF=$(( 43 + 2 * FROM )); PT=$(( 43 + 2 * TO ))
SIM=$WK/gl_$T.vvp
if [ ! -f $SIM ]; then
  /usr/bin/time -a -o $WK/time_gl.txt -f "iverilog $T: %e s, %M KB" \
  $OSS/iverilog -g2012 -o $SIM -DTOP=unit18_$T -Ptb.W=$W -Ptb.RG=$RG $WK/ng45_cells.v $SB $WK/${T}_glsim.v $R/test/tb_gl.v > $WK/iverilog_$T.log 2>&1 \
      || { echo "== $T: iverilog failed"; head -n 5 $WK/iverilog_$T.log; rm -f $SIM; exit 1; }
fi
for p in "$@"; do
  O=$WK/pw_${T}_$p.out; V=$WK/pw_${T}_$p.vcd
  if [ -z "$PW_ONLY" ]; then
    STIM=$WK/stim_${T}_$p.txt $OBJ/Vunit18_$T $TR/$p.tr | tail -n 1 > $O
    cat $WK/${T}_gl.txt >> $O
    /usr/bin/time -a -o $WK/time_gl.txt -f "vvp $T $p: %e s, %M KB" \
    $OSS/vvp -n $SIM +STIM=$WK/stim_${T}_$p.txt +VCD=$V +FROM=$PF +TO=$PT | grep -E "GATE|differs|STIM" >> $O
    $H/vcd_act $V > $WK/act_${T}_$p.txt && rm -f $V $WK/stim_${T}_$p.txt
    python3 $H/act_tcl.py $WK/ng45_cells.v $WK/${T}_gl.v $WK/act_${T}_$p.txt $WK/act_${T}_$p.tcl >> $O
  else
    grep -vE "^(Group|Sequential|Combinational|Clock|Macro|Pad|Total|clock pins)" $O > $O.tmp; mv $O.tmp $O
  fi
  cat > $WK/pw_${T}_$p.tcl <<TCL
read_liberty /w/ng45_power.lib
read_verilog /w/${T}_gl.v
link_design unit18_$T
create_clock -name clk -period 1.0 [get_ports clk]
set_input_delay 0 -clock clk [delete_from_list [all_inputs] [get_ports clk]]
set_output_delay 0 -clock clk [all_outputs]
source /w/act_${T}_$p.tcl
report_power -digits 4
TCL
  docker run --rm -v $(pwd)/$WK:/w $OPENLANE sh -c "sta -no_splash -exit /w/pw_${T}_$p.tcl" > $WK/sta_${T}_$p.log 2>&1
  grep -E "^(Group|Sequential|Combinational|Clock|Macro|Pad|Total)" $WK/sta_${T}_$p.log >> $O
  NFF=$(grep -cE "^\s*DFF\w*_X[0-9]+ " $WK/${T}_gl.v)
  awk -v n=$NFF -v tot="$(awk '/^Total/ {print $5}' $WK/sta_${T}_$p.log)" -v c=$CKCAP \
      'BEGIN { p = n * c * 1e-15 * 1.1 * 1.1 * 1e9; printf "clock pins           %d flip-flops x %.4f fF x 1.1 V^2 x 1 GHz = %.4f W; total with the clock pins %.4f W\n", n, c, p, tot + p }' >> $O
  echo "== $T $p"; cat $O
done
