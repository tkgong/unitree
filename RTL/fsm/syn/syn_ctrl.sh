#!/bin/sh
# syn_ctrl.sh - Yosys + ABC, Nangate45 area-only mapping of the accelerator's controller (dana336): accel_top with the
# unit (unit_bz3, measured in RTL/pe), the slot SRAM, the program memories and the write FIFO as black boxes (memory
# macros; their sizes are reported in bits by report_ctrl.py). Result: work/ctrl_hier.txt (hierarchical stat).
cd "$(dirname "$0")"
LIB=/home/dana336/eda/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
mkdir -p work
cat > work/ctrl.ys <<EOF
read_verilog -sv ../../alu_add.sv ../../alu_addp.sv ../../alu_fold31.sv ../../alu_canon.sv ../unit_cfg.sv ../lane_fmt.sv ../lane_cap.sv ../mems.sv ../seq.sv ../accel_top.sv
read_verilog -sv ../../pe/unit_bz3.sv
blackbox unit_bz3 slot_sram prog_mem ev_fifo
hierarchy -top accel_top
synth -top accel_top
dfflibmap -liberty $LIB
abc -liberty $LIB
opt_clean -purge
tee -o work/ctrl_hier.txt stat -liberty $LIB
EOF
/usr/bin/time -f "ctrl: %e s, %M KB" yosys -q -l work/ctrl.log work/ctrl.ys > /dev/null 2>> work/time_ctrl.txt
tail -n 1 work/time_ctrl.txt
grep -E "Chip area for top|cells$" work/ctrl_hier.txt | tail -n 3
