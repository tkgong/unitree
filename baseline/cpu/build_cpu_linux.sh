#!/bin/sh
CC=${1:-gcc}; CXX=${2:-g++-13}
HERE=$(cd "$(dirname "$0")" && pwd); O=$HERE/obj_linux; mkdir -p $O
for f in blake3 blake3_dispatch blake3_portable; do $CC -O3 -fPIC -c $HERE/blake3_c/$f.c -o $O/$f.o || exit 1; done
$CC -O3 -fPIC -msse2 -c $HERE/blake3_c/blake3_sse2.c -o $O/blake3_sse2.o || exit 1
$CC -O3 -fPIC -msse4.1 -c $HERE/blake3_c/blake3_sse41.c -o $O/blake3_sse41.o || exit 1
$CC -O3 -fPIC -mavx2 -c $HERE/blake3_c/blake3_avx2.c -o $O/blake3_avx2.o || exit 1
$CC -O3 -fPIC -mavx512f -mavx512vl -c $HERE/blake3_c/blake3_avx512.c -o $O/blake3_avx512.o || exit 1
$CXX -std=c++20 -O3 -DNDEBUG -march=native -fPIC -shared -pthread $HERE/cpu_trees.cpp $O/*.o -o $HERE/cpu_trees.so || exit 1
ls -la $HERE/cpu_trees.so | awk '{print "built cpu_trees.so", $5, "bytes"}'
cd $HERE/p3mono && ${CARGO:-$HOME/.cargo/bin/cargo} build --release --offline 2>&1 | tail -n 2 && ls -la target/release/libp3mono.so | awk '{print "built libp3mono.so", $5, "bytes"}'
