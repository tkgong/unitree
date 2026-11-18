#!/bin/sh
set -e
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$HERE/.." && pwd)
CXX=${1:-g++-13}
cmake -S "$HERE/ramsim" -B "$HERE/ramsim/build" -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=$CXX \
      -DCMAKE_POLICY_VERSION_MINIMUM=3.5 > "$HERE/ramsim/build.log" 2>&1 || { tail -n 30 "$HERE/ramsim/build.log"; exit 1; }
cmake --build "$HERE/ramsim/build" -j"$(nproc)" --target ramulator >> "$HERE/ramsim/build.log" 2>&1 || { grep -E "error" "$HERE/ramsim/build.log" | head -n 30; exit 1; }
echo "built $HERE/ramsim/libramulator.so"
AP="$HERE/ext/ap_types"
[ -f "$AP/include/ap_int.h" ] || git clone -q --depth 1 https://github.com/Xilinx/HLS_arbitrary_Precision_Types.git "$AP"
cd "$ROOT/model"
unit() {
  $CXX -std=c++14 -O1 -fPIC -shared -w '-D__declspec(x)=' -DMODES_MASK=$3 -I"$AP/include" -I"$ROOT/model/common" -I"$(pwd)/$1" -I"$(pwd)" \
       verify/shim_axn.cpp -o verify/$2.so
  echo "built model/verify/$2.so"
}
unit bz3s lz3s_16 0x16
unit bz3s lm3s_10 0x10
unit nat18c lnc18_04 0x04
unit nat18c lnb18_02 0x02
PY=${PY:-python3}
for m in "lz3s_16 0x16" "lm3s_10 0x10" "lnc18_04 0x04" "lnb18_02 0x02"; do
  set -- $m; $PY verify/check_axn.py verify/$1.so $2 | tail -n 1
done
