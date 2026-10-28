#!/bin/sh
# sta.sh - OpenSTA (OpenLane2 container) on a flat gate netlist from syn.sh NET=1: clock period PERIOD ns (default 1.0) on
# clk, inputs / outputs at 0, no wires (pre-placement). Prints WNS / TNS, the worst path with fanout / cap / slew and the
# 30 worst endpoints.        WORK=<dir> PERIOD=1.0 sh sta.sh <top>        -> $WORK/<top>_sta.out
cd "$(dirname "$0")"
WK=${WORK:-work}; T=$1; PER=${PERIOD:-1.0}
LIBDIR=/home/dana336/eda/OpenROAD-flow-scripts/flow/platforms/nangate45/lib
cat > $WK/${T}_sta.tcl <<TCL
read_liberty /lib/NangateOpenCellLibrary_typical.lib
read_verilog /w/${T}_flat.v
link_design unit18_$T
create_clock -name clk -period $PER [get_ports clk]
set_input_delay 0 -clock clk [delete_from_list [all_inputs] [get_ports clk]]
set_output_delay 0 -clock clk [all_outputs]
report_wns
report_tns
report_checks -path_delay max -format full -digits 3 -group_count 1 -fields {fanout cap slew}
report_checks -path_delay max -format end -group_count 30 -digits 3
TCL
docker run --rm -v $(pwd)/$WK:/w -v $LIBDIR:/lib ghcr.io/efabless/openlane2:2.3.10 sh -c "sta -no_splash -exit /w/${T}_sta.tcl" > $WK/${T}_sta.out 2>&1
head -n 2 $WK/${T}_sta.out
