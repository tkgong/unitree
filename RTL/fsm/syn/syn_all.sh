#!/bin/sh
# syn_all.sh - Yosys + ABC, Nangate45 area-only mapping of the FSM cores (dana336):
#   mono        pe_core #(1,0,0)        the natural Monolith-31 kernel
#   cc_<NB>     pe_core #(0,1,0,NB)     the natural ChaCha20 kernel, NB blocks, 4 NB private adders
#   b3_<NB>     pe_core #(0,0,1,NB)     the natural BLAKE3 kernel
#   shared_<NB> pe_core #(1,1,1,NB)     the shared PE: the blocks' adds on 4 NB adders of the Concrete tree
# Two runs per design: flat (synth -flatten: total / DFF / combinational) and hier (the alu_* modules kept as hierarchy:
# the ALU area = sum of the ALU instances). Results in work/<name>_{flat,hier}.txt.
#   sh syn_all.sh <name> [<name> ...]      names: mono cc_64 b3_64 shared_64 cc_356 ...
cd "$(dirname "$0")"
LIB=/home/dana336/eda/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
SRC="../../alu_add.sv ../../alu_addp.sv ../../alu_lend.sv ../../alu_fold.sv ../../alu_fold31.sv ../../alu_canon.sv ../../alu_bar_chunk.sv ../../alu_bar31.sv ../../alu_mul31.sv ../../alu_xor.sv ../mono_pkg.sv ../add_tree.sv ../mono_round.sv ../mono_core.sv ../arx_block.sv ../arx_ctrl.sv ../pe_core.sv"
mkdir -p work
for name in "$@"; do
  case $name in
    mono)      P="-set HAS_MONO 1 -set HAS_CC 0 -set HAS_B3 0 -set NB 1" ;;
    cc_*)      P="-set HAS_MONO 0 -set HAS_CC 1 -set HAS_B3 0 -set NB ${name#cc_}" ;;
    b3_*)      P="-set HAS_MONO 0 -set HAS_CC 0 -set HAS_B3 1 -set NB ${name#b3_}" ;;
    shared_*)  P="-set HAS_MONO 1 -set HAS_CC 1 -set HAS_B3 1 -set NB ${name#shared_}" ;;
    *) echo "unknown $name"; continue ;;
  esac
  for mode in flat hier; do
    if [ $mode = flat ]; then FL="-flatten"; else FL=""; fi
    cat > work/$name.$mode.ys <<EOF
read_verilog -sv $SRC
chparam $P pe_core
hierarchy -top pe_core
synth -top pe_core $FL
dfflibmap -liberty $LIB
abc -liberty $LIB
opt_clean -purge
tee -o work/${name}_$mode.txt stat -liberty $LIB
EOF
    /usr/bin/time -f "$name $mode: %e s, %M KB" yosys -q -l work/$name.$mode.log work/$name.$mode.ys > /dev/null 2>> work/time.txt
    tail -n 1 work/time.txt
  done
done
