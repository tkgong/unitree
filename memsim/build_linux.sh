#!/bin/sh
# build_linux.sh - Linux build of the HBM co-simulation (run on dana336):
#   1. memsim/ramsim/libramulator.so: UniZK's RamSim (Ramulator2) + hbm_capi.cpp. CMake fetches yaml-cpp 0.7.0, spdlog 1.11.0
#      and argparse 2.9 from GitHub into memsim/ramsim/ext (as upstream Ramulator2 does).
#   2. memsim/ext/ap_types: Xilinx's open-source ap_int headers (HLS_arbitrary_Precision_Types, Apache-2.0), standing in for
#      the Vitis headers the Windows DLLs use.
#   3. dse/TOP/verify/lz_16.so (bz: four primitives) and lz3_16.so (bz3: ChaCha20 + BLAKE3 + Monolith): the same sources and
#      defines as build_all.sh / build_bz.sh, compiled by g++ instead of clang-cl.
#   sh memsim/build_linux.sh [CXX]          (default g++-13)
set -e
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$HERE/.." && pwd)
CXX=${1:-g++-13}
cmake -S "$HERE/ramsim" -B "$HERE/ramsim/build" -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=$CXX \
      -DCMAKE_POLICY_VERSION_MINIMUM=3.5 > "$HERE/ramsim/build.log" 2>&1 || { tail -n 30 "$HERE/ramsim/build.log"; exit 1; }
cmake --build "$HERE/ramsim/build" -j"$(nproc)" --target ramulator >> "$HERE/ramsim/build.log" 2>&1 || { grep -E "error" "$HERE/ramsim/build.log" | head -n 30; exit 1; }
echo "built $HERE/ramsim/libramulator.so"
AP="$HERE/ext/ap_types"
[ -f "$AP/include/ap_int.h" ] || git clone -q --depth 1 https://github.com/Xilinx/HLS_arbitrary_Precision_Types.git "$AP"
cd "$ROOT/dse/TOP"
unit() {   # dir, name, MODES_MASK
  $CXX -std=c++14 -O1 -fPIC -shared -w '-D__declspec(x)=' -DMODES_MASK=$3 -I"$AP/include" -I"$ROOT/dse/common" -I"$(pwd)/$1" -I"$(pwd)" \
       verify/shim_axn.cpp -o verify/$2.so
  echo "built dse/TOP/verify/$2.so"
}
unit bz lz_16 0x16
unit bz3 lz3_16 0x16
PY=${PY:-python3}
$PY verify/check_axn.py verify/lz_16.so 0x16 | tail -n 1
$PY verify/check_axn.py verify/lz3_16.so 0x16 | tail -n 1
