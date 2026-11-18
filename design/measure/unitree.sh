#!/bin/sh
D=$(cd "$(dirname "$0")/.." && pwd); O=${1:-$D/measure/out}; SZ=${2:-"21"}; BT=${3:-"10:64 16:4"}
mkdir -p $O; cd $D/model
F=$D/compiler/compile_forest.py; C=$D/compiler/compile_tree.py; A="sram=32 gddr=2 audit"
W="merkle:blake3 ggm:chacha ggm:blake3 merkle:mono"
for bt in $BT; do L=${bt%%:*}; T=${bt#*:}
  for w in $W; do r=${w%%:*}; p=${w#*:}
    python3 $C verify/lz3s_16.so $r $p $L x$T $A > $O/batch_${r}_${p}_$L.log 2>&1 &
  done
done
wait
for L in $SZ; do
  for w in $W; do r=${w%%:*}; p=${w#*:}
    python3 $F verify/lz3s_16.so $r $p $L pes=8 work=$O/forest_${r}_${p}_$L $A > $O/forest_${r}_${p}_$L.md 2>&1
  done
done
python3 $D/measure/energy.py $O > $O/unitree.csv
cat $O/unitree.csv
