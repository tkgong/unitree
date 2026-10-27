#!/bin/sh
# run_tb.sh - pe_core (RTL/fsm) against the Python models with Icarus Verilog.
#   sh run_tb.sh [NB] [NT] [HAS_MONO HAS_CC HAS_B3]       default: NB 4, 3 runs, all three primitives (the shared PE)
set -e
NB=${1:-4}; NT=${2:-3}; HM=${3:-1}; HC=${4:-1}; HB=${5:-1}
PY=${PY:-/c/Users/gong.ten/AppData/Local/Programs/Python/Python314/python.exe}
IV=${IV:-/c/msys64/ucrt64/bin}
cd "$(dirname "$0")"
$PY -X utf8 gen_vectors.py $NB $NT
rm -f tb_pe.vvp
$IV/iverilog.exe -g2012 -DNB=$NB -DNT=$NT -DHAS_MONO=$HM -DHAS_CC=$HC -DHAS_B3=$HB -o tb_pe.vvp \
    tb_pe.sv ../mono_pkg.sv ../add_tree.sv ../mono_round.sv ../mono_core.sv ../arx_block.sv ../arx_ctrl.sv ../pe_core.sv \
    ../../alu_*.sv ../../rot31.sv 2>&1 | grep -vE "timescale|inherited|time unit|time precision|^\s*$" || true
$IV/vvp.exe -n tb_pe.vvp | tee sim_${HM}${HC}${HB}_${NB}.log | grep -E "run |SUMMARY|got"
