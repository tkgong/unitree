#!/bin/sh
H=$(cd "$(dirname "$0")" && pwd); W=$H/../../syn/${WORK:-work_t10}
run() {
  T=$1; shift; sh $H/power_vcd.sh $T > /dev/null 2>&1
  for p in "$@"; do sh $H/power_vcd.sh $T $p > $W/pwi_${T}_$p.log 2>&1 & done; wait
}
run chacha chacha_gcc &
run mono mono_mmo &
run blake3 blake3_mb3 blake3_gb3 &
run shared shared_gcc shared_mb3 shared_gb3 shared_mmo &
wait
