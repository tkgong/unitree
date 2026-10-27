#!/bin/sh
# run_unit_tb.sh - unit_bz3.sv (two generated PEs) against the HLS C++ (dse/TOP/verify/lz3_16.dll), clock by clock.
#   1. gen_pe.py regenerates RTL/pe/*.sv from dse/TOP/bz3 (and checks: datapath 0 == datapath 1, PE copy 0 == copy 1)
#   2. gen_unit_vectors.py drives the DLL with random issue controls and lanes for N cycles
#   3. Icarus Verilog runs tb_unit.sv and compares all 1248 output lanes every cycle
#   sh run_unit_tb.sh [cycles] [PYTHON]                    (300 cycles: about 5 minutes)
set -e
N=${1:-300}
PY=${2:-/c/Users/gong.ten/AppData/Local/Programs/Python/Python314/python.exe}
IV=/c/msys64/ucrt64/bin
cd "$(dirname "$0")"
(cd .. && $PY -X utf8 gen_pe.py)
$PY -X utf8 gen_unit_vectors.py $N
$IV/iverilog.exe -g2012 -I.. -DNCYC=$N -o tb_unit.vvp tb_unit.sv ../unit_bz3.sv ../pe.sv ../dp_l*.sv ../axn_step.sv ../../alu_*.sv ../../rot31.sv 2>&1 \
  | grep -vE "timescale|inherited|time unit|time precision|sorry: constant selects|^\s*$" || true
$IV/vvp.exe -n tb_unit.vvp | tee sim.log | grep -E "^cycle|SUMMARY"
