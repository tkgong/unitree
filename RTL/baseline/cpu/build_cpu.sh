#!/bin/sh
# build_cpu.sh - the official BLAKE3 C library (each SIMD file with its own ISA flags, runtime dispatch) + cpu_trees.cpp -> cpu_trees.dll
CC="/c/Program Files/Microsoft Visual Studio/2022/Community/VC/Tools/Llvm/bin/clang.exe"
CXX="/c/Program Files/Microsoft Visual Studio/2022/Community/VC/Tools/Llvm/bin/clang++.exe"
HERE=$(cd "$(dirname "$0")" && pwd); O=$HERE/obj; mkdir -p $O
T=--target=x86_64-pc-windows-msvc
for f in blake3 blake3_dispatch blake3_portable; do "$CC" $T -O3 -c $HERE/blake3_c/$f.c -o $O/$f.o || exit 1; done
"$CC" $T -O3 -msse2 -c $HERE/blake3_c/blake3_sse2.c -o $O/blake3_sse2.o || exit 1
"$CC" $T -O3 -msse4.1 -c $HERE/blake3_c/blake3_sse41.c -o $O/blake3_sse41.o || exit 1
"$CC" $T -O3 -mavx2 -c $HERE/blake3_c/blake3_avx2.c -o $O/blake3_avx2.o || exit 1
"$CC" $T -O3 -mavx512f -mavx512vl -c $HERE/blake3_c/blake3_avx512.c -o $O/blake3_avx512.o || exit 1
"$CXX" $T -std=c++20 -O3 -DNDEBUG -march=native -shared $HERE/cpu_trees.cpp $O/*.o -o $HERE/cpu_trees.dll 2>&1 | grep -E "error|warning: .*vector" | head -n 20
ls -la $HERE/cpu_trees.dll | awk '{print "built cpu_trees.dll", $5, "bytes"}'
