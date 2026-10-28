#!/bin/sh
# syn_keep.sh - Yosys + ABC, Nangate45 area of the hand-written tops with every ALU instance kept as written: the alu_*
# modules carry keep_hierarchy, so the flattening of the rest never merges two adders that compute the same sum (each
# ALU instance is real hardware, in the separate units and in the shared unit alike); the netlist is flattened only for
# the count. Results: work_keep/<top>_flat.txt (same format as syn.sh, report.py reads them with WORK=work_keep).
#   sh syn_keep.sh [top ...]    (shared mono chacha blake3)
cd "$(dirname "$0")"
LIB=/home/dana336/eda/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
SRC="../../alu_add.sv ../../alu_addp.sv ../../alu_lend.sv ../../alu_fold.sv ../../alu_fold31.sv ../../alu_canon.sv ../../alu_bar_chunk.sv ../../alu_bar31.sv ../../alu_mul31_en_p2.sv ../../alu_xor.sv ../kara_pkg.sv ../mono_dp18.sv ../arx_group.sv ../../pe/axn_step.sv"
mkdir -p work_keep
for t in ${*:-shared mono chacha blake3}; do
  cat > work_keep/$t.ys <<EOF
read_verilog -sv -I../../pe $SRC ../unit18_$t.sv
hierarchy -top unit18_$t
setattr -mod -set keep_hierarchy 1 *alu_*
synth -top unit18_$t -flatten
dfflibmap -liberty $LIB
abc -liberty $LIB
opt_clean -purge
flatten
opt_clean -purge
tee -o work_keep/${t}_flat.txt stat -liberty $LIB
EOF
  /usr/bin/time -f "$t keep: %e s, %M KB" yosys -q -l work_keep/$t.log work_keep/$t.ys > /dev/null 2>> work_keep/time.txt
  tail -n 1 work_keep/time.txt
done
