#!/bin/sh
# run_store.sh - store-mode sweep (k<K>: the K levels above the leaves are not written, the open recomputes them) per
# primitive: 2^18 trees on the unit RTL/src implements (dse/TOP/verify/lz3s_16.so), 32 KB SRAM, GDDR6 2 channels (one core's
# share of the RTX 3070's memory), audit on. The analytical choice (memsim/README.md): the smallest K whose DRAM traffic fits
# the compute bound, traffic(K) / 44 B per cycle <= nodes / theta.
#   sh memsim/run_store.sh           -> memsim/results/store18/<req>_<prim>_store_<s>.log
H=$(cd "$(dirname "$0")" && pwd); CT=$H/../RTL/compiler/compile_tree.py; L=$H/results/store18; mkdir -p $L
cd "$H/../dse/TOP"
{
  for s in all k1 k3 k4 k5; do echo "merkle blake3 $s"; done
  for p in chacha blake3; do for s in k1 k3 k4 k5; do echo "ggm $p $s"; done; done
  for s in all k2 k4; do echo "merkle mono $s"; done
} | CT=$CT L=$L xargs -P ${JOBS:-16} -L 1 sh -c 'python3 $CT verify/lz3s_16.so $0 $1 18 sram=32 gddr=2 store=$2 audit > $L/$0_$1_store_$2.log 2>&1'
for f in $L/*.log; do
  printf "%s " $(basename $f .log); grep -h "^  cycles" $f | awk '{printf "%s ", $2}'; grep -h "values written" $f | grep -oE "\([0-9.]+ MB\)" | tr -d '\n'
  grep -qh "check: .*OK" $f && echo " OK" || { echo " FAIL"; tail -n 2 $f; }
done
