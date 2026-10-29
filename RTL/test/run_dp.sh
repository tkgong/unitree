#!/bin/sh
# run_dp.sh - Verilator (dana336): mono_dp18 alone against dp_vec.txt (dp_vec.py).   sh run_dp.sh [NL]
R=$(cd "$(dirname "$0")/.." && pwd); . "$R/env.sh"
cd "$R/test"
NL=${1:-0}
rm -rf obj_dp
verilator --cc --exe --build -j 12 -Wno-fatal -Wno-lint -O1 --top-module mono_dp18 -GNL=$NL -Mdir obj_dp $INC \
    ${KS45:+-DKS45 $SRC_KS45 $SRC_CELLS} $SRC_ALU $SRC_BLK tb_dp.cpp > verilator_dp.log 2>&1 \
    || { echo "build failed"; grep -E "%Error" verilator_dp.log | head -n 8; exit 1; }
./obj_dp/Vmono_dp18 dp_vec.txt
