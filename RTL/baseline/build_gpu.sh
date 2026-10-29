#!/bin/sh
# build_gpu.sh - compile gpu_prims.cu into gpu_prims.dll (CUDA 12.6, sm_86 = RTX 3070); run from Git Bash, nvcc goes through PowerShell
# so that MSYS does not rewrite the /MD /O2 flags as paths.
powershell.exe -NoProfile -Command '& "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6\bin\nvcc.exe" -O3 -arch=sm_86 -std=c++17 -shared -ccbin "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.29.30133\bin\HostX64\x64" -Xcompiler "/MD /O2 /wd4244" -o D:\unitree\unitree\RTL\baseline\gpu_prims.dll D:\unitree\unitree\RTL\baseline\gpu_prims.cu'
ls -la gpu_prims.dll | awk '{print "built gpu_prims.dll", $5, "bytes"}'
