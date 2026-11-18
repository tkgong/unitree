#!/bin/sh
R=$(cd "$(dirname "$0")/../.." && pwd); . "$R/env.sh"
cd "$R/syn"
WK=${WORK:-work}; T=$1; PER=${PERIOD:-1.0}; N=${NL:-flat}
cat > $WK/${T}_${N}_sta.tcl <<TCL
read_liberty /lib/NangateOpenCellLibrary_typical.lib
read_verilog /w/${T}_$N.v
link_design unit18_$T
create_clock -name clk -period $PER [get_ports clk]
set_input_delay 0 -clock clk [delete_from_list [all_inputs] [get_ports clk]]
set_output_delay 0 -clock clk [all_outputs]
set_driving_cell -lib_cell DFF_X1 -pin Q [delete_from_list [all_inputs] [get_ports clk]]
set_multicycle_path 2 -setup -from [get_ports blake]
set_multicycle_path 1 -hold -from [get_ports blake]
report_wns
report_tns
report_checks -path_delay max -format full -digits 3 -group_count 1 -fields {fanout cap slew}
report_checks -path_delay max -format end -group_count 30 -digits 3
TCL
docker run --rm -v $(pwd)/$WK:/w -v $LIBDIR:/lib $OPENLANE sh -c "sta -no_splash -exit /w/${T}_${N}_sta.tcl" > $WK/${T}_${N}_sta.out 2>&1
head -n 2 $WK/${T}_${N}_sta.out
