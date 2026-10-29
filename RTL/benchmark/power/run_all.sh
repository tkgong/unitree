#!/bin/sh
# run_all.sh - the eight measured-activity power runs (power_vcd.sh) of benchmark/power/power.md: each top compiled once,
# its programs replayed in parallel; logs syn/$WORK/pwi_<top>_<trace>.log, results syn/$WORK/pw_<top>_<trace>.out.
#   (needs syn/$WORK/<top>_rep.v from syn/syn.sh + syn/repair.sh and the traces of test/make_traces.sh trp)
#   WORK=work_t10 FROM=1000 TO=1400 sh run_all.sh
H=$(cd "$(dirname "$0")" && pwd); W=$H/../../syn/${WORK:-work_t10}
run() {   # top, traces
  T=$1; shift; sh $H/power_vcd.sh $T > /dev/null 2>&1
  for p in "$@"; do sh $H/power_vcd.sh $T $p > $W/pwi_${T}_$p.log 2>&1 & done; wait
}
run chacha chacha_gcc &
run mono mono_mmo &
run blake3 blake3_mb3 blake3_gb3 &
run shared shared_gcc shared_mb3 shared_gb3 shared_mmo &
wait
