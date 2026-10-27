#!/bin/sh
# build_bz.sh - regenerate the unit (bz: ChaCha20 / BLAKE3 ARX blocks on Monolith's adders + two Monolith-31 / Poseidon2-M31
# datapaths, three multiplier ranks, Poseidon2 linear layers hosted on the Concrete adders, state lanes only), build the
# simulator DLL and run the bit-exact check.      sh build_bz.sh [PYTHON]
set -e
PY=${1:-/c/Users/gong.ten/AppData/Local/Programs/Python/Python314/python.exe}
cd "$(dirname "$0")"
LEND='2:12,3:12,4:12,5:16,6:28,7:56,8:72,9:72,10:64,11:40,12:28,13:12,14:4,15:4,16:8,17:8,18:8'
G='7,8,9,10,11,12:7;5,6,7,8,9,10:4;6,7,8,9,10,11:3;13,14,15,16,17,18:1;2,3,4+8,9,10:2;2,3,4+8,9+13:1;8+9+13+16+17,18:1'
OPT="MONO_SQMUL=1 MONO_P2=1 MONO_P2_MUL3=1 MONO_P2_A1=1 MONO_LEND=$LEND MONO_LEND_ANY=1 MONO_LEND_RED=1 MONO_LEND_MOD=1"
mkdir -p bz
# datapath 0 at lane 1188, datapath 1 right after datapath 0's widest level
env MONO_BASE=1188 $OPT MONO_OUT=bz/lane_mono_kl.inc $PY gen_lane_mono6.py > bz/gen0.log
tail -n 4 bz/gen0.log
B1=$(grep -oE "written: .*lanes \[[0-9, ]+\]" bz/gen0.log | grep -oE "\[[0-9, ]+\]" | tr -d '[] ' | tr ',' '
' | sort -n | tail -n 1)
rm -f bz/gen0.log
echo "datapath 1 at lane $B1"
env MONO_BASE=$B1 MONO_PREFIX=monk2 MONO_DEF=MONO2 $OPT MONO_OUT=bz/lane_mono2_kl.inc $PY gen_lane_mono6.py | tail -n 1
# the ARX block groups and the top-level pipe (gen_pipe_axn.py reads ./lane_mono_kl.inc and writes ./pipe_axn.h)
cp bz/lane_mono_kl.inc lane_mono_kl.inc; cp bz/lane_mono2_kl.inc lane_mono2_kl.inc
$PY gen_pipe_axn.py 10 3 0 "--groups=$G;$G" --mono2=lane_mono2_kl.inc --p2eng=4 | tail -n 1
mv pipe_axn.h bz/pipe_axn.h; rm -f lane_mono_kl.inc lane_mono2_kl.inc
# simulator: the HLS C++ compiled into a DLL, driven cycle by cycle from Python
sh ../verify/build_dll.sh verify/lz_16.dll verify/shim_axn.cpp -DMODES_MASK=0x16 -I"$(pwd)/bz" -I"$(pwd)"
rm -f verify/lz_16.exp verify/lz_16.lib
$PY verify/check_axn.py verify/lz_16.dll 0x16 | tail -n 7
