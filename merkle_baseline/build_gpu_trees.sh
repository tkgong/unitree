#!/bin/sh
# build_gpu_trees.sh - compile gpu_trees.cu (which includes gpu_prims.cu) into gpu_trees.dll (CUDA 12.6, sm_86 = RTX 3070);
# nvcc goes through PowerShell so that MSYS does not rewrite the /MD /O2 flags as paths.
powershell.exe -NoProfile -Command '& "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6\bin\nvcc.exe" -O3 -arch=sm_86 -std=c++17 -shared -ccbin "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.29.30133\bin\HostX64\x64" -Xcompiler "/MD /O2 /wd4244" -o D:\unitree\merkle_baseline\gpu_trees.dll D:\unitree\merkle_baseline\gpu_trees.cu'
ls -la gpu_trees.dll | awk '{print "built gpu_trees.dll", $5, "bytes"}'
