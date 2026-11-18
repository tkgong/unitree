#!/bin/sh
R=$(cd "$(dirname "$0")/.." && pwd)
D=${1:-tr}; OUT=$R/test/$D; mkdir -p $OUT
if [ $D = trp ]; then A=12; G=12; M=10; else A=8; G=7; M=5; fi
cd "$R/model"
for a in "lz3s_16 merkle blake3 $A shared_mb3" "lz3s_16 ggm chacha $A shared_gcc" "lz3s_16 ggm blake3 $G shared_gb3" \
         "lz3s_16 merkle mono $M shared_mmo" "lnc18_04 ggm chacha $A chacha_gcc" "lnb18_02 merkle blake3 $A blake3_mb3" \
         "lnb18_02 ggm blake3 $G blake3_gb3" "lm3s_10 merkle mono $M mono_mmo"; do
  set -- $a
  (python3 $R/compiler/compile_tree.py verify/$1.so $2 $3 $4 trace=$OUT/$5.tr 2>&1 | grep -E "^\s+cycles|check|trace " \
      | sed "s/(Monolith.*//" | tr "\n" " " | sed "s/^/$5: /"; echo) &
done
wait
