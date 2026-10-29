#!/bin/sh
# make_traces.sh - the closed-loop traces of the RTL testbench (tb_unit18.cpp), written by the software compiler
# dse/TOP/verify/compile_tree.py trace=<file> from the HLS unit models (dse/TOP/verify/<model>.so, memsim/build_linux.sh):
#   lz3s_16  the shared unit (bz3s, ChaCha20 + BLAKE3 + Monolith)   lnc18_04 / lnb18_02  natural ChaCha20 / BLAKE3 (nat18c)
#   lm3s_10  natural Monolith (bz3s, Monolith only)
# One primitive and one tree kind per program. tr  (default): short traces, checked in (2^8 ARX, 2^7 BLAKE3 GGM, 2^5 Monolith);
# trp: the power traces of benchmark/power/power_vcd.sh (2^12 ARX, 2^10 Monolith).          sh make_traces.sh [tr|trp]
R=$(cd "$(dirname "$0")/.." && pwd)
D=${1:-tr}; OUT=$R/test/$D; mkdir -p $OUT
if [ $D = trp ]; then A=12; G=12; M=10; else A=8; G=7; M=5; fi
cd "$R/../dse/TOP"
for a in "lz3s_16 merkle blake3 $A shared_mb3" "lz3s_16 ggm chacha $A shared_gcc" "lz3s_16 ggm blake3 $G shared_gb3" \
         "lz3s_16 merkle mono $M shared_mmo" "lnc18_04 ggm chacha $A chacha_gcc" "lnb18_02 merkle blake3 $A blake3_mb3" \
         "lnb18_02 ggm blake3 $G blake3_gb3" "lm3s_10 merkle mono $M mono_mmo"; do
  set -- $a
  (python3 verify/compile_tree.py verify/$1.so $2 $3 $4 trace=$OUT/$5.tr 2>&1 | grep -E "^\s+cycles|check|trace " \
      | sed "s/(Monolith.*//" | tr "\n" " " | sed "s/^/$5: /"; echo) &
done
wait
