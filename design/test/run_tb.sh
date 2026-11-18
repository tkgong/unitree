#!/bin/sh
R=$(cd "$(dirname "$0")/.." && pwd); . "$R/env.sh"
cd "$R/test"
ulimit -s unlimited 2>/dev/null || true
ALU="${KS45:+-DKS45 $SRC_KS45 $SRC_CELLS} $SRC_ALU"
for t in ${*:-$TOPS}; do
  O=obj_$t${KS45:+_ks45}
  if [ ! -x $O/Vunit18_$t ]; then
    rm -rf $O
    verilator --cc --exe --build -j 12 -Wno-fatal -Wno-lint -O1 --top-module unit18_$t -Mdir $O $INC \
        -CFLAGS "-DVTOP=Vunit18_$t -DVTOP_H=\\\"Vunit18_$t.h\\\" -DTOPNAME=\\\"unit18_$t\\\"" \
        $ALU $SRC_BLK $(top_sv $t) tb_unit18.cpp > verilator_$t${KS45:+_ks45}.log 2>&1 || { echo "== unit18_$t: build failed"; grep -E "%Error|error:" verilator_$t${KS45:+_ks45}.log | head -n 8; continue; }
  fi
  for tr in tr/${t}_*.tr; do ./$O/Vunit18_$t $tr | tail -n 7; done
done
