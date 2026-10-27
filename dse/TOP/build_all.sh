#!/bin/sh
# build_all.sh - regenerate every unit from the generators (all operators are ALU calls, alu_core.h), the flattened tops,
# the simulator DLLs, and run the bit-exact checks.      sh build_all.sh [PYTHON]
#   bz      four primitives (build_bz.sh)                          verify/lz_16.dll
#   bz3     ChaCha20 + BLAKE3 + Monolith, no Poseidon2              verify/lz3_16.dll
#   pwe     natural Poseidon2 + 4 engines                           verify/lpwe_10.dll
#   nat38c  natural ChaCha20, 1.5 rounds per traversal              verify/lnc_04.dll
set -e
PY=${1:-/c/Users/gong.ten/AppData/Local/Programs/Python/Python314/python.exe}
cd "$(dirname "$0")"
LEND='2:12,3:12,4:12,5:16,6:28,7:56,8:72,9:72,10:64,11:40,12:28,13:12,14:4,15:4,16:8,17:8,18:8'
G='7,8,9,10,11,12:7;5,6,7,8,9,10:4;6,7,8,9,10,11:3;13,14,15,16,17,18:1;2,3,4+8,9,10:2;2,3,4+8,9+13:1;8+9+13+16+17,18:1'
LOG=$(mktemp)
# two datapaths: datapath 1 starts right after datapath 0's widest level
datapaths() {   # dir, options
  env MONO_BASE=$3 $2 MONO_OUT=$1/lane_mono_kl.inc $PY gen_lane_mono6.py > $LOG
  B1=$(grep -oE "written: .*lanes \[[0-9, ]+\]" $LOG | grep -oE "\[[0-9, ]+\]" | tr -d '[] ' | tr ',' '\n' | sort -n | tail -n 1)
  env MONO_BASE=$B1 MONO_PREFIX=monk2 MONO_DEF=MONO2 $2 MONO_OUT=$1/lane_mono2_kl.inc $PY gen_lane_mono6.py > $LOG
  echo "$1: datapaths at lanes $3, $B1"
}
top() {         # dir, gen_pipe_axn.py arguments...
  d=$1; shift
  cp $d/lane_mono_kl.inc lane_mono_kl.inc; [ -f $d/lane_mono2_kl.inc ] && cp $d/lane_mono2_kl.inc lane_mono2_kl.inc
  $PY gen_pipe_axn.py "$@" | tail -n 1 | cut -c1-110
  mv pipe_axn.h $d/pipe_axn.h; rm -f lane_mono_kl.inc lane_mono2_kl.inc
}
dll() {         # dir, dll, mask
  sh ../verify/build_dll.sh verify/$2.dll verify/shim_axn.cpp -DMODES_MASK=$3 -I"$(pwd)/$1" -I"$(pwd)" | tail -n 1
  rm -f verify/$2.exp verify/$2.lib
  $PY verify/check_axn.py verify/$2.dll $3 | tail -n 1
}
sh build_bz.sh $PY
datapaths bz3 "MONO_SQMUL=1 MONO_LEND=$LEND MONO_LEND_ANY=1 MONO_LEND_RED=1 MONO_LEND_MOD=1" 1188
top bz3 10 3 0 "--groups=$G;$G" --mono2=lane_mono2_kl.inc
dll bz3 lz3_16 0x16
datapaths pwe "MONO_SQMUL=1 MONO_P2=1 MONO_P2_MUL3=1 MONO_P2_A1=1 MONO_ONLY_P2=1 MONO_LEND=2:4,3:4,4:4,6:4,7:4,8:4 MONO_LEND_ANY=1 MONO_LEND_RED=1 MONO_LEND_MOD=1" 44
top pwe 1 2 0 "--groups=2,3,4+6,7,8:1" --mono2=lane_mono2_kl.inc --p2eng=4
dll pwe lpwe_10 0x10
# nat38c keeps its hand-set datapath copy (lane_mono_kl.inc: MONO_LEND 152 at levels 1..6; no Monolith code is compiled)
top nat38c 19 2 0 "--groups=1,2,3,4,5,6:19;1,2,3,4,5,6:19"
dll nat38c lnc_04 0x04
# flattened tops for reading
$PY flatten_ops.py
$PY flatten_pipe.py bz/pipe_axn.h bz/pipe_axn_flat.h 0x16
$PY flatten_pipe.py bz3/pipe_axn.h bz3/pipe_axn_flat.h 0x16
# self-contained flat tops: datapath levels, ARX steps and engines inlined, lane_pipe reads as alu_core.h calls
$PY inline_flat.py bz/pipe_axn_flat.h
$PY inline_flat.py bz3/pipe_axn_flat.h
rm -f $LOG
