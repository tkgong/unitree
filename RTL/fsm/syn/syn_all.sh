#!/bin/sh
# syn_all.sh - Yosys + ABC, Nangate45 area-only mapping of the four tops (dana336):
#   mono          top_mono           the natural Monolith-31 kernel
#   chacha_<NB>   top_chacha #(NB)   the natural ChaCha20 kernel, NB blocks, 4 NB private adders
#   blake3_<NB>   top_blake3 #(NB)   the natural BLAKE3 kernel
#   shared_<NB>   top_shared #(NB)   the shared PE: the blocks' adds on 4 NB adders of the Concrete tree
# Two runs per design: flat (synth -flatten: total / DFF / combinational) and hier (the alu_* modules kept as hierarchy:
# the ALU area = sum of the ALU instances). Results in work/<name>_{flat,hier}.txt.
#   sh syn_all.sh <name> [<name> ...]      names: mono chacha_64 blake3_64 shared_64 chacha_356 ...
cd "$(dirname "$0")"
LIB=/home/dana336/eda/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
SRC="../../alu_add.sv ../../alu_addp.sv ../../alu_lend.sv ../../alu_fold.sv ../../alu_fold31.sv ../../alu_canon.sv ../../alu_bar_chunk.sv ../../alu_bar31.sv ../../alu_mul31.sv ../../alu_xor.sv ../mono_pkg.sv ../add_tree.sv ../mono_round.sv ../mono_core.sv ../cc_block.sv ../b3_block.sv ../arx_block.sv ../arx_ctrl.sv ../top_mono.sv ../top_chacha.sv ../top_blake3.sv ../top_shared.sv"
mkdir -p work
for name in "$@"; do
  case $name in
    mono)      TOP=top_mono;   P="" ;;
    chacha_*)  TOP=top_chacha; P="chparam -set NB ${name#chacha_} top_chacha" ;;
    blake3_*)  TOP=top_blake3; P="chparam -set NB ${name#blake3_} top_blake3" ;;
    shared_*)  TOP=top_shared; P="chparam -set NB ${name#shared_} top_shared" ;;
    *) echo "unknown $name"; continue ;;
  esac
  for mode in flat hier; do
    if [ $mode = flat ]; then FL="-flatten"; else FL=""; fi
    cat > work/$name.$mode.ys <<EOF
read_verilog -sv $SRC
$P
hierarchy -top $TOP
synth -top $TOP $FL
dfflibmap -liberty $LIB
abc -liberty $LIB
opt_clean -purge
tee -o work/${name}_$mode.txt stat -liberty $LIB
EOF
    /usr/bin/time -f "$name $mode: %e s, %M KB" yosys -q -l work/$name.$mode.log work/$name.$mode.ys > /dev/null 2>> work/time.txt
    tail -n 1 work/time.txt
  done
done
