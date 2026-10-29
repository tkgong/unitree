#!/bin/sh
# syn_blk.sh - flat Nangate45 area of the sub-blocks alone, to split the flat sharing result (syn.sh) by block:
#   dp_lent  mono_dp18 NL=216 (the 216 narrowest adders lendable: alu_lend)      dp_nat   mono_dp18 NL=0 (alu_addp only)
#   arx_lend arx_group NBK=9 BL=22 CP=0 PRIV=0 (adds go out on ea/eb)    arx_priv arx_group NBK=9 BL=22 CP=0 PRIV=1
# Results: syn/$WORK/blk_<name>.txt.        sh syn_blk.sh [name ...]
R=$(cd "$(dirname "$0")/../.." && pwd); . "$R/env.sh"
H=$R/benchmark/area                                           # wrap_shared_b.sv
cd "$R/syn"
SRC="$SRC_ALU $SRC_BLK"
WK=${WORK:-work}
mkdir -p $WK
for n in ${*:-dp_lent dp_nat arx_lend arx_priv sh_b0 sh_b1}; do
  X=""
  case $n in
    dp_lent)  TOP=mono_dp18; P="-set NL 216";;
    dp_nat)   TOP=mono_dp18; P="-set NL 0";;
    arx_lend) TOP=arx_group; P="-set NBK 9 -set BL 22 -set CP 0 -set PRIV 0";;
    arx_priv) TOP=arx_group; P="-set NBK 9 -set BL 22 -set CP 0 -set PRIV 1";;
    sh_b0)    TOP=wrap_shared_b; P="-set BLK 0"; X="$(top_sv shared) $H/wrap_shared_b.sv";;   # shared, blake tied 0
    sh_b1)    TOP=wrap_shared_b; P="-set BLK 1"; X="$(top_sv shared) $H/wrap_shared_b.sv";;   # shared, blake tied 1
  esac
  cat > $WK/blk_$n.ys <<EOF
read_verilog -sv $INC $SRC $X
chparam $P $TOP
hierarchy -top $TOP
synth -flatten
dfflibmap -liberty $LIB
abc -liberty $LIB
opt_clean -purge
tee -o $WK/blk_$n.txt stat -liberty $LIB
EOF
  /usr/bin/time -a -o $WK/time.txt -f "blk_$n: %e s, %M KB" yosys -q -l $WK/blk_$n.log $WK/blk_$n.ys > /dev/null 2>&1
  tail -n 1 $WK/time.txt
done
