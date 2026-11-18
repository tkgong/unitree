#!/bin/sh
R=$(cd "$(dirname "$0")/.." && pwd); . "$R/env.sh"
cd "$R/syn"
WK=${WORK:-work}; T=$1; PER=${PERIOD:-1.0}; FO=${MAXFO:-16}
cat > $WK/${T}_repair.tcl <<TCL
read_lef /plat/lef/NangateOpenCellLibrary.tech.lef
read_lef /plat/lef/NangateOpenCellLibrary.macro.mod.lef
read_liberty /plat/lib/NangateOpenCellLibrary_typical.lib
read_verilog /w/${T}_flat.v
link_design unit18_$T
initialize_floorplan -utilization 50 -aspect_ratio 1 -core_space 2 -site FreePDK45_38x28_10R_NP_162NW_34O
create_clock -name clk -period $PER [get_ports clk]
set_input_delay 0 -clock clk [delete_from_list [all_inputs] [get_ports clk]]
set_output_delay 0 -clock clk [all_outputs]
set_max_fanout $FO [current_design]
puts "BEFORE"; report_wns; report_tns; report_design_area
repair_design
puts "AFTER repair_design"; report_wns; report_tns; report_design_area
repair_timing -setup
puts "AFTER repair_timing"; report_wns; report_tns; report_design_area
report_checks -path_delay max -format full -digits 3 -group_count 1 -fields {fanout cap slew}
write_verilog /w/${T}_rep.v
TCL
docker run --rm -v $(pwd)/$WK:/w -v $PLAT:/plat $OPENLANE sh -c "openroad -no_splash -exit /w/${T}_repair.tcl" > $WK/${T}_repair.out 2>&1
grep -E "^(BEFORE|AFTER)|^wns|^tns|^Design area|Inserted|Resized|Repair" $WK/${T}_repair.out
