#!/bin/sh
# power_vcd.sh - power of a timing-closed netlist with the switching activity MEASURED on a real program, not assumed:
#   1. RTL Verilator replay of the program (tb_unit18.cpp, compile_tree.py trace=, closed loop, every node finish checked
#      against the HLS unit), writing every input and the RTL's lout per clock phase from the reset on (STIM=);
#   2. the repaired netlist $WORK/<top>_rep.v with every internal net renamed n<k> (Yosys rename -hide / -enumerate; the
#      ports keep theirs; OpenROAD's undeclared tie nets zero_ / one_ tied), simulated gate by gate (zero delay) by Icarus
#      Verilog with the Nangate45 cells' functions Yosys writes from the liberty (tb_gl.v): the same inputs phase by phase,
#      lout compared with the RTL's at every phase (the netlist is verified on the program too), every net dumped over the
#      program cycles [FROM, TO) (steady state);
#   3. per net bit the transitions and the time at 1 (vcd_act), set on the driving cell's output pin (act_tcl.py,
#      set_power_activity -pins / -input_ports), OpenSTA report_power at 1 GHz (internal + pin-capacitance switching +
#      leakage; no wires, no clock tree: pre-placement).
#   WORK=work_t10 FROM=1500 TO=2500 sh power_vcd.sh <top> <trace> [<trace> ...]     -> $WORK/pw_<top>_<trace>.out
# (Verilator on the gate netlist with every net traced needs 29-42 GB per natural unit, Yosys sim 48 GB for chacha: neither
# fits the shared unit; OpenSTA read_vcd only matches cell pins, not nets.)
cd "$(dirname "$0")"
WK=${WORK:-work_t10}; T=$1; shift; FROM=${FROM:-1500}; TO=${TO:-2500}
LIBDIR=/home/dana336/eda/OpenROAD-flow-scripts/flow/platforms/nangate45/lib
LIB=$LIBDIR/NangateOpenCellLibrary_typical.lib
OSS=/home/dana336/eda/oss-cad-suite/bin                      # iverilog / vvp
TR=${TRDIR:-../verify/trp}
RTLSRC="../../alu_add.sv ../../alu_addp.sv ../../alu_lend.sv ../../alu_fold.sv ../../alu_fold31.sv ../../alu_addf.sv ../../alu_csa31.sv ../../alu_canon.sv ../../alu_bar_chunk.sv ../../alu_bar31.sv ../../alu_mul31_en_p2.sv ../../alu_xor.sv ../kara_pkg.sv ../mono_dp18.sv ../arx_group.sv ../axn_step.sv ../unit18_$T.sv"
[ -f $WK/ng45_cells.v ] || yosys -q -p "read_liberty -ignore_miss_func $LIB; write_verilog -noattr $WK/ng45_cells.v"
[ -x vcd_act ] || g++ -O2 -o vcd_act vcd_act.cpp
if [ ! -f $WK/${T}_gl.v ]; then
  TIE=""; grep -q "(zero_)" $WK/${T}_rep.v && TIE="connect -set zero_ 1'b0;"     # OpenROAD's tie-low net (written undeclared)
  grep -q "(one_)" $WK/${T}_rep.v && TIE="$TIE connect -set one_ 1'b1;"
  yosys -q -l $WK/${T}_gl.log -p "read_liberty -lib $LIB; read_verilog $WK/${T}_rep.v; hierarchy -top unit18_$T; $TIE rename -hide w:* c:*; rename -enumerate -pattern n%; write_verilog -noattr -noexpr $WK/${T}_gl.v"
fi
OBJ=$WK/obj_rtl_$T
if [ ! -x $OBJ/Vunit18_$T ]; then
  rm -rf $OBJ
  verilator --cc --exe --build -j 16 -Wno-fatal -Wno-lint -O1 --top-module unit18_$T -Mdir $OBJ -I.. \
      -CFLAGS "-DVTOP=Vunit18_$T -DVTOP_H=\\\"Vunit18_$T.h\\\" -DTOPNAME=\\\"unit18_$T\\\"" \
      $RTLSRC $(pwd)/../verify/tb_unit18.cpp > $WK/verilator_rtl_$T.log 2>&1 \
      || { echo "== $T: verilator failed"; grep -E "%Error|error:" $WK/verilator_rtl_$T.log | head -n 5; exit 1; }
fi
W=$(grep -m1 -oE "input \[[0-9]+:0\] lin" $WK/${T}_gl.v | grep -oE "[0-9]+" | head -n 1); W=$((W + 1))
RG=$(grep -m1 -oE "input \[[0-9]+:0\] rg" $WK/${T}_gl.v | grep -oE "[0-9]+" | head -n 1); RG=$((RG + 1))
PF=$(( 43 + 2 * FROM )); PT=$(( 43 + 2 * TO ))              # stimulus phases: 43 reset / warm-up, then 2 per program cycle
SIM=$WK/gl_$T.vvp
for p in "$@"; do
  O=$WK/pw_${T}_$p.out; V=$WK/pw_${T}_$p.vcd
  STIM=$WK/stim_${T}_$p.txt $OBJ/Vunit18_$T $TR/$p.tr | tail -n 1 > $O
  /usr/bin/time -a -o $WK/time_gl.txt -f "iverilog $T $p: %e s, %M KB" \
  $OSS/iverilog -g2012 -o $SIM.$p -DTOP=unit18_$T "-DSTIM=\"$WK/stim_${T}_$p.txt\"" "-DVCDF=\"$V\"" \
      -Ptb.W=$W -Ptb.RG=$RG -Ptb.FROM=$PF -Ptb.TO=$PT $WK/ng45_cells.v $WK/${T}_gl.v tb_gl.v > $WK/iverilog_$T.log 2>&1 \
      || { echo "== $T: iverilog failed"; head -n 5 $WK/iverilog_$T.log; exit 1; }
  /usr/bin/time -a -o $WK/time_gl.txt -f "vvp $T $p: %e s, %M KB" $OSS/vvp -n $SIM.$p | grep -E "GATE|differs|STIM" >> $O
  ./vcd_act $V > $WK/act_${T}_$p.txt && rm -f $V $SIM.$p $WK/stim_${T}_$p.txt
  python3 act_tcl.py $WK/ng45_cells.v $WK/${T}_gl.v $WK/act_${T}_$p.txt $WK/act_${T}_$p.tcl >> $O
  cat > $WK/pw_${T}_$p.tcl <<TCL
read_liberty /lib/NangateOpenCellLibrary_typical.lib
read_verilog /w/${T}_gl.v
link_design unit18_$T
create_clock -name clk -period 1.0 [get_ports clk]
set_input_delay 0 -clock clk [delete_from_list [all_inputs] [get_ports clk]]
set_output_delay 0 -clock clk [all_outputs]
source /w/act_${T}_$p.tcl
report_power
TCL
  docker run --rm -v $(pwd)/$WK:/w -v $LIBDIR:/lib ghcr.io/efabless/openlane2:2.3.10 sh -c "sta -no_splash -exit /w/pw_${T}_$p.tcl" > $WK/sta_${T}_$p.log 2>&1
  grep -E "^(Group|Sequential|Combinational|Clock|Macro|Pad|Total)" $WK/sta_${T}_$p.log >> $O
  echo "== $T $p"; cat $O
done
