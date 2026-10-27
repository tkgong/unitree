#!/bin/sh
# build.sh - compile the merklecpp baseline with the five primitives into baseline.dll (run_baseline.py drives it)
CL="/c/Program Files/Microsoft Visual Studio/2022/Community/VC/Tools/Llvm/bin/clang++.exe"
HERE=$(cd "$(dirname "$0")" && pwd)
"$CL" --target=x86_64-pc-windows-msvc -std=c++20 -O3 -DNDEBUG -march=native -I/d/merklecpp -I"$HERE" -shared "$HERE/baseline.cpp" -o "$HERE/baseline.dll" 2>&1 | grep -E "error|warning" | head -20
echo "built $HERE/baseline.dll"
