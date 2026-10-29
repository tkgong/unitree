#!/bin/sh
# power.sh - OpenSTA (OpenLane2 container) vectorless power of a repaired netlist from repair.sh (<top>_rep.v): 1 GHz clock,
# no wires (pre-placement: cell internal + pin-capacitance switching + leakage, no interconnect, no clock tree), activity
# either propagated from the inputs (MODE=input: ACT transitions per cycle on every data input, duty 0.5; the registers and
# the logic behind them get OpenSTA's propagated probabilities) or set on every net (MODE=global: ACT on all nets).
#   WORK=work_t10 MODE=input ACT=0.5 sh power.sh <top>      -> $WORK/<top>_power_<mode><act>.out
cd "$(dirname "$0")"
WK=${WORK:-work}; T=$1; MODE=${MODE:-input}; ACT=${ACT:-0.5}
LIBDIR=/home/dana336/eda/OpenROAD-flow-scripts/flow/platforms/nangate45/lib
OUT=$WK/${T}_power_${MODE}${ACT}.out
cat > $WK/${T}_power.tcl <<TCL
read_liberty /lib/NangateOpenCellLibrary_typical.lib
read_verilog /w/${T}_rep.v
link_design unit18_$T
create_clock -name clk -period 1.0 [get_ports clk]
set_input_delay 0 -clock clk [delete_from_list [all_inputs] [get_ports clk]]
set_output_delay 0 -clock clk [all_outputs]
$( [ $MODE = global ] && echo "set_power_activity -global -activity $ACT -duty 0.5" || echo "set_power_activity -input -activity $ACT -duty 0.5" )
set_power_activity -input_port rst -activity 0 -duty 0
report_power

TCL
docker run --rm -v $(pwd)/$WK:/w -v $LIBDIR:/lib ghcr.io/efabless/openlane2:2.3.10 sh -c "sta -no_splash -exit /w/${T}_power.tcl" > $OUT 2>&1
sed -n '/Group/,/^Total/p' $OUT | head -12
