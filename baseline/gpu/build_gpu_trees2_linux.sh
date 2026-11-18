#!/bin/sh
NVCC=${1:-nvcc}
HERE=$(cd "$(dirname "$0")" && pwd)
$NVCC -O3 -arch=sm_86 -std=c++17 -shared -Xcompiler -fPIC -o $HERE/gpu_trees2.so $HERE/gpu_trees2.cu || exit 1
ls -la $HERE/gpu_trees2.so | awk '{print "built gpu_trees2.so", $5, "bytes"}'
