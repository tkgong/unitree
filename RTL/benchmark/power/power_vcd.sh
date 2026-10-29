#!/bin/sh
# power_vcd.sh - power of a timing-closed netlist with the switching activity MEASURED on a real program, not assumed:
#   1. RTL Verilator replay of the program (test/tb_unit18.cpp on a trace of test/make_traces.sh, closed loop, every node
#      finish checked against the HLS unit), writing every input and the RTL's lout per clock phase from the reset on (STIM=);
#   2. the repaired netlist syn/$WORK/<top>_rep.v with every internal net renamed n<k> (Yosys rename -hide / -enumerate; the
#      ports keep theirs; OpenROAD's undeclared tie nets zero_ / one_ tied, and the output bits it leaves undriven - the
#      constant-0 lanes of mono / shared, no tie cells pre-placement - tied to 0), simulated gate by gate (zero delay) by
#      Icarus Verilog with the Nangate45 cells' functions Yosys writes from the liberty (test/tb_gl.v): the same inputs phase
#      by phase, lout compared with the RTL's at every phase (the netlist is verified on the program too), every net dumped
#      over the program cycles [FROM, TO) (steady state);
#   3. per net bit the transitions and the time at 1 (vcd_act), set on the driving cell's output pin (act_tcl.py,
#      set_power_activity -pins / -input_ports), OpenSTA report_power at 1 GHz (internal + pin-capacitance switching +
#      leakage; no wires, no clock tree: pre-placement).
#   WORK=work_t10 FROM=1000 TO=1400 sh power_vcd.sh <top> [<trace> ...]   -> syn/$WORK/pw_<top>_<trace>.out
#   (no trace: only builds the gate netlist, the RTL model and the Icarus compile of <top>, once per top)
# (Verilator on the gate netlist with every net traced needs 29-42 GB per natural unit, Yosys sim 48 GB for chacha: neither
# fits the shared unit; OpenSTA read_vcd only matches cell pins, not nets.)
R=$(cd "$(dirname "$0")/../.." && pwd); . "$R/env.sh"
H=$R/benchmark/power
cd "$R/syn"
WK=${WORK:-work_t10}; T=$1; shift; FROM=${FROM:-1000}; TO=${TO:-1400}
TR=${TRDIR:-$R/test/trp}
[ -f $WK/ng45_cells.v ] || yosys -q -p "read_liberty -ignore_miss_func $LIB; write_verilog -noattr $WK/ng45_cells.v"
# the power liberty: the flip-flops' internal-power conditions name both Q and QN ("!CK & !D & !Q & QN"); OpenSTA takes the
# two as independent, so the states sum to (1-d)^2 + d^2 < 1 (d = Q's duty) and up to half the clock-pin power was lost.
# The QN terms are dropped (QN = !Q).
[ -f $WK/ng45_power.lib ] || sed -E "/when/ s/ & !?QN//g" $LIB > $WK/ng45_power.lib
CKCAP=$(awk '/^\s*cell \(DFF_X1\)/ {c = 1} c && /pin \(CK\)/ {p = 1} c && p && /^\s*capacitance/ {gsub(/[;\t ]/, ""); split($0, a, ":"); print a[2]; exit}' $LIB)
[ -x $H/vcd_act ] || g++ -O2 -o $H/vcd_act $H/vcd_act.cpp
if [ ! -f $WK/${T}_gl.v ]; then
  TIE=""; grep -q "(zero_)" $WK/${T}_rep.v && TIE="connect -set zero_ 1'b0;"     # OpenROAD's tie-low net (written undeclared)
  grep -q "(one_)" $WK/${T}_rep.v && TIE="$TIE connect -set one_ 1'b1;"
  echo "$T: $(grep -oE '\(lout\[[0-9]+\]\)' $WK/${T}_rep.v | sort -u | wc -l) lout bits driven by cells in ${T}_rep.v, the rest tied to 0" > $WK/${T}_gl.txt
  yosys -q -l $WK/${T}_gl.log -p "read_liberty -lib $LIB; read_verilog $WK/${T}_rep.v; hierarchy -top unit18_$T; $TIE setundef -undriven -zero; rename -hide w:* c:*; rename -enumerate -pattern n%; write_verilog -noattr -noexpr $WK/${T}_gl.v"
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
PF=$(( 43 + 2 * FROM )); PT=$(( 43 + 2 * TO ))              # stimulus phases: 43 reset / warm-up, then 2 per program cycle
SIM=$WK/gl_$T.vvp
if [ ! -f $SIM ]; then
  /usr/bin/time -a -o $WK/time_gl.txt -f "iverilog $T: %e s, %M KB" \
  $OSS/iverilog -g2012 -o $SIM -DTOP=unit18_$T -Ptb.W=$W -Ptb.RG=$RG $WK/ng45_cells.v $WK/${T}_gl.v $R/test/tb_gl.v > $WK/iverilog_$T.log 2>&1 \
      || { echo "== $T: iverilog failed"; head -n 5 $WK/iverilog_$T.log; rm -f $SIM; exit 1; }
fi
for p in "$@"; do
  O=$WK/pw_${T}_$p.out; V=$WK/pw_${T}_$p.vcd
  if [ -z "$PW_ONLY" ]; then                                 # PW_ONLY=1: only the power step, on the activity files already there
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
  # the clock net: OpenSTA charges a net's switching to its driver and clk has none (no clock tree pre-placement), so the
  # clock pins' capacitance is added here: (flip-flops x CK pin capacitance) x VDD^2 x f (two transitions per cycle)
  NFF=$(grep -cE "^\s*DFF\w*_X[0-9]+ " $WK/${T}_gl.v)
  awk -v n=$NFF -v tot="$(awk '/^Total/ {print $5}' $WK/sta_${T}_$p.log)" -v c=$CKCAP \
      'BEGIN { p = n * c * 1e-15 * 1.1 * 1.1 * 1e9; printf "clock pins           %d flip-flops x %.4f fF x 1.1 V^2 x 1 GHz = %.4f W; total with the clock pins %.4f W\n", n, c, p, tot + p }' >> $O
  echo "== $T $p"; cat $O
done
