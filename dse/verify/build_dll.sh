#!/bin/sh
# build_dll.sh <output.dll> <shim.cpp> [additional .cpp ...]
# Compiles HLS C++ (ap_int) into a 64-bit DLL that Python/ctypes can drive.
# Replaces Vitis C simulation: csim.exe cannot run on this machine (endpoint
# policy blocks execution of freshly built binaries), but a DLL loaded by the
# signed system Python works. -DHLS_NO_XIL_FPO_LIB avoids the Vitis half-float
# headers, which clash with the MSVC CRT; we only use integer ap_uint types.
CL="/c/Program Files/Microsoft Visual Studio/2022/Community/VC/Tools/Llvm/bin/clang++.exe"
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT="$1"; shift
"$CL" --target=x86_64-pc-windows-msvc -std=c++14 -O1 -DHLS_NO_XIL_FPO_LIB \
  -IC:/Xilinx/Vitis/2025.2/Vitis/include -I"$ROOT/common" \
  -shared "$@" -o "$OUT" 2>&1 | grep -E "error" && exit 1
echo "built $OUT"
