#!/bin/sh
# power_vcd.sh - power of a timing-closed netlist with the switching activity MEASURED on a real program, not assumed:
#   1. the repaired netlist $WORK/<top>_rep.v with every internal net renamed to a short name n<k> (Yosys rename -hide /
#      -enumerate; the ports keep theirs), so that the simulation's VCD and OpenSTA see the same net names (no leading
#      underscore: Verilator does not trace those);
#   2. Verilator gate-level (zero-delay) simulation of that netlist with the Nangate45 cell models Yosys writes from the
#      liberty (read_liberty: the cells' functions and flip-flops), driven by tb_unit18.cpp with a compiled program's trace
#      (compile_tree.py trace=): closed loop, every node finish checked against the HLS unit, so the netlist is verified too;
#   3. VCD of every net over the program cycles [FROM, TO) (steady state), OpenSTA read_vcd on the same netlist, 1 GHz,
#      report_power (internal + pin-capacitance switching + leakage; no wires, no clock tree: pre-placement).
#   WORK=work_t10 FROM=1000 TO=2000 sh power_vcd.sh <top> <trace> [<trace> ...]     -> $WORK/pw_<top>_<trace>.out
cd "$(dirname "$0")"
ulimit -s unlimited                                          # the gate-level model's eval needs a large stack
WK=${WORK:-work_t10}; T=$1; shift; FROM=${FROM:-1000}; TO=${TO:-2000}
LIBDIR=/home/dana336/eda/OpenROAD-flow-scripts/flow/platforms/nangate45/lib
LIB=$LIBDIR/NangateOpenCellLibrary_typical.lib
TR=${TRDIR:-../verify/trp}
[ -f $WK/ng45_cells.v ] || yosys -q -p "read_liberty -ignore_miss_func $LIB; write_verilog -noattr $WK/ng45_cells.v"
if [ ! -f $WK/${T}_gl.v ]; then
  TIE=""; grep -q "(zero_)" $WK/${T}_rep.v && TIE="connect -set zero_ 1'b0;"     # OpenROAD's tie-low net (written undeclared)
  grep -q "(one_)" $WK/${T}_rep.v && TIE="$TIE connect -set one_ 1'b1;"
  yosys -q -l $WK/${T}_gl.log -p "read_liberty -lib $LIB; read_verilog $WK/${T}_rep.v; hierarchy -top unit18_$T; $TIE rename -hide w:* c:*; rename -enumerate -pattern n%; write_verilog -noattr -noexpr $WK/${T}_gl.v"
fi
OBJ=$WK/obj_gl_$T
if [ ! -x $OBJ/Vunit18_$T ]; then
  rm -rf $OBJ
  /usr/bin/time -a -o $WK/time_gl.txt -f "verilator $T: %e s, %M KB" \
  verilator --cc --exe --build -j 16 --trace -Wno-fatal -Wno-lint -Wno-style -O1 --x-assign 0 --x-initial 0 \
      --output-split 20000 --output-split-cfuncs 2000 --top-module unit18_$T -Mdir $OBJ \
      -CFLAGS "-O1 -DVTOP=Vunit18_$T -DVTOP_H=\\\"Vunit18_$T.h\\\" -DTOPNAME=\\\"unit18_${T}_gl\\\"" \
      $WK/ng45_cells.v $WK/${T}_gl.v $(pwd)/../verify/tb_unit18.cpp >$WK/verilator_gl_$T.log 2>&1 \
      || { echo "== $T: verilator failed"; grep -E "%Error" $WK/verilator_gl_$T.log | head -n 5; exit 1; }
fi
for p in "$@"; do
  V=$WK/pw_${T}_$p.vcd; O=$WK/pw_${T}_$p.out
  VCD=$V VCD_FROM=$FROM VCD_TO=$TO $OBJ/Vunit18_$T $TR/$p.tr | tail -n 1 > $O
  cat > $WK/pw_${T}_$p.tcl <<TCL
read_liberty /lib/NangateOpenCellLibrary_typical.lib
read_verilog /w/${T}_gl.v
link_design unit18_$T
create_clock -name clk -period 1.0 [get_ports clk]
set_input_delay 0 -clock clk [delete_from_list [all_inputs] [get_ports clk]]
set_output_delay 0 -clock clk [all_outputs]
read_vcd -scope TOP/unit18_$T /w/pw_${T}_$p.vcd
report_power
TCL
  docker run --rm -v $(pwd)/$WK:/w -v $LIBDIR:/lib ghcr.io/efabless/openlane2:2.3.10 sh -c "sta -no_splash -exit /w/pw_${T}_$p.tcl" >> $O 2>&1
  echo "== $T $p: $(head -n 1 $O | sed 's/.*: //')"; grep -E "^(Sequential|Combinational|Total)|nnotat|rror" $O | head -n 6
  rm -f $V
done
