#!/bin/sh
# run_tb.sh - the FSM tops (RTL/fsm) against the Python models with Icarus Verilog.
#   sh run_tb.sh <top> [NB] [NT]        top: mono | chacha | blake3 | shared       default NB 4, 3 runs
set -e
TOP=${1:-shared}; NB=${2:-4}; NT=${3:-3}
PY=${PY:-/c/Users/gong.ten/AppData/Local/Programs/Python/Python314/python.exe}
IV=${IV:-/c/msys64/ucrt64/bin}
cd "$(dirname "$0")"
case $TOP in mono) D=-DTOP_MONO ;; chacha) D=-DTOP_CHACHA ;; blake3) D=-DTOP_BLAKE3 ;; shared) D= ;; *) echo "top?"; exit 1 ;; esac
$PY -X utf8 gen_vectors.py $NB $NT
rm -f tb_$TOP.vvp
$IV/iverilog.exe -g2012 -DNB=$NB -DNT=$NT -DTOP=$TOP $D -o tb_$TOP.vvp \
    tb_pe.sv ../mono_pkg.sv ../add_tree.sv ../mono_round.sv ../mono_core.sv ../cc_block.sv ../b3_block.sv ../arx_block.sv ../arx_ctrl.sv \
    ../top_mono.sv ../top_chacha.sv ../top_blake3.sv ../top_shared.sv ../../alu_*.sv ../../rot31.sv 2>&1 \
    | grep -vE "timescale|inherited|time unit|time precision|sorry: constant selects|^\s*$" || true
$IV/vvp.exe -n tb_$TOP.vvp | tee sim_${TOP}_${NB}.log | grep -E "run |SUMMARY|got"
