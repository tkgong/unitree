#!/bin/sh
# build_bz3s.sh - the 18-block unit (bz3s): ChaCha20 + BLAKE3 + Monolith, two datapaths, 9 blocks per copy (two rings:
# 5 blocks on levels 7..12, 4 on levels 5..10), 216 lent adders per datapath. The block count follows the HBM bandwidth
# share of the 22-PE design point (RTL/fsm/README.md), not the lendable adders.      sh build_bz3s.sh [PYTHON]
set -e
PY=${1:-/c/Users/gong.ten/AppData/Local/Programs/Python/Python314/python.exe}
cd "$(dirname "$0")"
LEND='5:16,6:16,7:36,8:36,9:36,10:36,11:20,12:20'
G='7,8,9,10,11,12:5;5,6,7,8,9,10:4'
LOG=$(mktemp)
env MONO_BASE=396 MONO_SQMUL=1 MONO_LEND=$LEND MONO_LEND_ANY=1 MONO_LEND_RED=1 MONO_LEND_MOD=1 MONO_OUT=bz3s/lane_mono_kl.inc $PY gen_lane_mono6.py > $LOG
B1=$(grep -oE "written: .*lanes \[[0-9, ]+\]" $LOG | grep -oE "\[[0-9, ]+\]" | tr -d '[] ' | tr ',' '\n' | sort -n | tail -n 1)
env MONO_BASE=$B1 MONO_PREFIX=monk2 MONO_DEF=MONO2 MONO_SQMUL=1 MONO_LEND=$LEND MONO_LEND_ANY=1 MONO_LEND_RED=1 MONO_LEND_MOD=1 MONO_OUT=bz3s/lane_mono2_kl.inc $PY gen_lane_mono6.py > $LOG
echo "bz3s: datapaths at lanes 396, $B1"
cp bz3s/lane_mono_kl.inc lane_mono_kl.inc; cp bz3s/lane_mono2_kl.inc lane_mono2_kl.inc
$PY gen_pipe_axn.py 10 3 0 "--groups=$G;$G" --mono2=lane_mono2_kl.inc | tail -n 1 | cut -c1-120
mv pipe_axn.h bz3s/pipe_axn.h; rm -f lane_mono_kl.inc lane_mono2_kl.inc
sh ../verify/build_dll.sh verify/lz3s_16.dll verify/shim_axn.cpp -DMODES_MASK=0x16 -I"$(pwd)/bz3s" -I"$(pwd)" | tail -n 1
rm -f verify/lz3s_16.exp verify/lz3s_16.lib
$PY verify/check_axn.py verify/lz3s_16.dll 0x16 | tail -n 1
rm -f $LOG
