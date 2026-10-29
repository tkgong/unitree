#!/bin/sh
# run_gddr.sh - the GDDR6 runs of memsim/README.md (the benchmark GPU's memory, RTX 3070): the unit RTL/src implements
# (dse/TOP/verify/lz3s_16.so, memsim/build_linux.sh), 32 KB SRAM, every run audited and bit-exact against the Python
# references. gddr=<ch>: the channels one core owns (16 = all 448 GB/s; 2 = one core's share when 8 cores split them).
#   sh memsim/run_gddr.sh            -> memsim/results/logs18/<request>_<prim>_<size>_store_<s>_gddr_<ch>.log (in parallel)
H=$(cd "$(dirname "$0")" && pwd); CT=$H/../RTL/compiler/compile_tree.py; L=$H/results/logs18; mkdir -p $L
cd "$H/../dse/TOP"
for a in "merkle blake3 18 out 2" "merkle blake3 18 out 1" "merkle blake3 18 out 16" "ggm chacha 18 out 2" "ggm chacha 18 out 1" \
         "ggm chacha 18 k2 2" "ggm chacha 18 k2 4" "ggm blake3 18 out 2" "ggm blake3 18 k2 2" "ggm blake3 18 k2 4" \
         "ggm blake3 18 k2 16" "merkle mono 16 all 2" "merkle mono 18 out 2"; do
  set -- $a
  python3 $CT verify/lz3s_16.so $1 $2 $3 sram=32 gddr=$5 store=$4 audit > $L/$1_$2_$3_store_$4_gddr_$5.log 2>&1 &
done
wait
grep -H "^  cycles\|check:\|audit" $L/*gddr*.log
