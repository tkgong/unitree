#!/bin/sh
# run_tb.sh - check every module of RTL/ against the HLS C++ ALUs (dse/TOP/alu_core.h), bit for bit.
#   1. ref_alu.cpp (the C++ ALUs exported one by one) -> ref_alu.dll, with dse/verify/build_dll.sh (clang++, Vitis ap_int)
#   2. gen_vectors.py drives the DLL: 115 vector files (one per module instance: every W / H / R the unit uses), 4096
#      vectors each (edge cases, the 7 / 8-bit Bars chunks exhaustively, the rest random), inputs + expected output
#   3. tb_alu.sv instantiates every module with every parameter value, applies the vectors, compares (Icarus Verilog:
#      MSYS2 ucrt64 iverilog / vvp; Vivado's xsim compiles but its snapshot cannot run on this machine).
#   sh run_tb.sh [PYTHON]
set -e
PY=${1:-/c/Users/gong.ten/AppData/Local/Programs/Python/Python314/python.exe}
IV=/c/msys64/ucrt64/bin
cd "$(dirname "$0")"
sh ../../dse/verify/build_dll.sh ref_alu.dll ref_alu.cpp -I"$(cd ../../dse/TOP && pwd)"
$PY -X utf8 gen_vectors.py
$IV/iverilog.exe -g2012 -o tb_alu.vvp tb_alu.sv ../alu_*.sv ../rot31.sv 2>&1 | grep -vE "timescale|inherited|time unit|time precision|^$" || true
$IV/vvp.exe -n tb_alu.vvp | tee sim.log | grep -E "FAIL|SUMMARY"
