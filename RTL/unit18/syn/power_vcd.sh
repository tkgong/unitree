#!/bin/sh
# power_vcd.sh - power of a timing-closed netlist with the switching activity MEASURED on a real program, not assumed:
#   1. RTL Verilator replay of the program (tb_unit18.cpp, compile_tree.py trace=, closed loop, every node finish checked
#      against the HLS unit) recording the top-level ports from the reset on (VCD_ALL, --trace-depth 1): the stimulus;
#   2. the repaired netlist $WORK/<top>_rep.v with every internal net renamed n<k> (Yosys rename -hide / -enumerate; the
#      ports keep theirs; OpenROAD's undeclared tie nets zero_ / one_ tied), simulated gate by gate (zero delay) by Yosys
#      `sim` with the Nangate45 cells' functions from the liberty, driven by that stimulus; -sim-cmp checks every output of
#      the netlist against the RTL's at every step (the netlist is verified on the program too);
#   3. the gate-level waveform of every net over the program cycles [FROM, TO) (steady state) -> VCD -> OpenSTA read_vcd on
#      the same netlist, 1 GHz, report_power (internal + pin-capacitance switching + leakage; no wires, no clock tree).
#   WORK=work_t10 FROM=1500 TO=2500 sh power_vcd.sh <top> <trace> [<trace> ...]     -> $WORK/pw_<top>_<trace>.out
# (Verilator on the gate netlist with every net traced needs 29-42 GB per natural unit and does not fit the shared one.)
cd "$(dirname "$0")"
WK=${WORK:-work_t10}; T=$1; shift; FROM=${FROM:-1500}; TO=${TO:-2500}
LIBDIR=/home/dana336/eda/OpenROAD-flow-scripts/flow/platforms/nangate45/lib
LIB=$LIBDIR/NangateOpenCellLibrary_typical.lib
OSS=/home/dana336/eda/oss-cad-suite/bin                      # vcd2fst / fst2vcd
TR=${TRDIR:-../verify/trp}
RTLSRC="../../alu_add.sv ../../alu_addp.sv ../../alu_lend.sv ../../alu_fold.sv ../../alu_fold31.sv ../../alu_addf.sv ../../alu_csa31.sv ../../alu_canon.sv ../../alu_bar_chunk.sv ../../alu_bar31.sv ../../alu_mul31_en_p2.sv ../../alu_xor.sv ../kara_pkg.sv ../mono_dp18.sv ../arx_group.sv ../axn_step.sv ../unit18_$T.sv"
if [ ! -f $WK/${T}_gl.v ]; then
  TIE=""; grep -q "(zero_)" $WK/${T}_rep.v && TIE="connect -set zero_ 1'b0;"     # OpenROAD's tie-low net (written undeclared)
  grep -q "(one_)" $WK/${T}_rep.v && TIE="$TIE connect -set one_ 1'b1;"
  yosys -q -l $WK/${T}_gl.log -p "read_liberty -lib $LIB; read_verilog $WK/${T}_rep.v; hierarchy -top unit18_$T; $TIE rename -hide w:* c:*; rename -enumerate -pattern n%; write_verilog -noattr -noexpr $WK/${T}_gl.v"
fi
OBJ=$WK/obj_ports_$T
if [ ! -x $OBJ/Vunit18_$T ]; then
  rm -rf $OBJ
  verilator --cc --exe --build -j 16 --trace --trace-depth 1 -Wno-fatal -Wno-lint -O1 --top-module unit18_$T -Mdir $OBJ -I.. \
      -CFLAGS "-DVTOP=Vunit18_$T -DVTOP_H=\\\"Vunit18_$T.h\\\" -DTOPNAME=\\\"unit18_$T\\\"" \
      $RTLSRC $(pwd)/../verify/tb_unit18.cpp > $WK/verilator_ports_$T.log 2>&1 \
      || { echo "== $T: verilator failed"; grep -E "%Error|error:" $WK/verilator_ports_$T.log | head -n 5; exit 1; }
fi
for p in "$@"; do
  O=$WK/pw_${T}_$p.out
  # 1. stimulus (ports, RTL, from the reset)
  VCD=$WK/ports_${T}_$p.vcd VCD_ALL=1 $OBJ/Vunit18_$T $TR/$p.tr | tail -n 1 > $O
  $OSS/vcd2fst $WK/ports_${T}_$p.vcd $WK/ports_${T}_$p.fst > /dev/null 2>&1 && rm -f $WK/ports_${T}_$p.vcd
  # time of program cycle c: the tb's 43 reset / warm-up phases, then 1000 ps per cycle (the rising edge at +500)
  T0=$(( 43 * 500 + FROM * 1000 )); T1=$(( 43 * 500 + TO * 1000 ))
  # 2. gate-level simulation of the whole run, checked against the RTL's outputs
  /usr/bin/time -a -o $WK/time_gl.txt -f "yosys sim $T $p: %e s, %M KB" \
  yosys -q -l $WK/sim_${T}_$p.log -p "read_liberty -ignore_miss_func $LIB; read_verilog $WK/${T}_gl.v; hierarchy -top unit18_$T; flatten; opt_clean; sim -r $WK/ports_${T}_$p.fst -scope TOP -sim-cmp -fst $WK/gl_${T}_$p.fst -q" \
      > /dev/null 2>&1; echo "yosys sim exit $? ($(grep -ciE 'mismatch|error' $WK/sim_${T}_$p.log) mismatch / error lines)" >> $O
  # 3. the window as VCD, OpenSTA
  $OSS/fst2vcd $WK/gl_${T}_$p.fst 2> /dev/null | awk -v T0=$T0 -v T1=$T1 -f vcd_window.awk > $WK/pw_${T}_$p.vcd
  cat > $WK/pw_${T}_$p.tcl <<TCL
read_liberty /lib/NangateOpenCellLibrary_typical.lib
read_verilog /w/${T}_gl.v
link_design unit18_$T
create_clock -name clk -period 1.0 [get_ports clk]
set_input_delay 0 -clock clk [delete_from_list [all_inputs] [get_ports clk]]
set_output_delay 0 -clock clk [all_outputs]
read_vcd -scope unit18_$T /w/pw_${T}_$p.vcd
report_power
TCL
  docker run --rm -v $(pwd)/$WK:/w -v $LIBDIR:/lib ghcr.io/efabless/openlane2:2.3.10 sh -c "sta -no_splash -exit /w/pw_${T}_$p.tcl" >> $O 2>&1
  echo "== $T $p"; grep -vE "^\[|^ *$" $O | grep -E "SUMMARY|yosys sim|^(Sequential|Combinational|Total)|nnotat|period|rror" | head -n 8
  rm -f $WK/pw_${T}_$p.vcd
done
