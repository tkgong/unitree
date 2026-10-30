#!/bin/sh
# run_ablation.sh - adaptive (per primitive and tree direction) vs rigid memory policies, 2^18 trees on the unit RTL/src
# implements (dse/TOP/verify/lz3s_16.so), 32 KB SRAM, GDDR6 2 channels, audit on. Points not in run_tile.sh / run_store.sh:
# the Merkle tile applied to GGM (tk8), the GGM tile applied to Merkle (tk3), the ARX store policy (k4) at the adaptive tiles,
# Monolith at the ARX tiles. Each log prints the per-engine utilization.
#   sh memsim/run_ablation.sh        -> memsim/results/ablation18/<req>_<prim>_store_<s>_tk<TK>.log
H=$(cd "$(dirname "$0")" && pwd); CT=$H/../RTL/compiler/compile_tree.py; L=$H/results/ablation18; mkdir -p $L
cd "$H/../dse/TOP"
{
  for p in chacha blake3; do for s in out k4; do echo "ggm $p $s 8"; echo "ggm $p $s 3"; done; done
  for s in out k4; do echo "merkle blake3 $s 3"; echo "merkle blake3 $s 8"; done
  for s in all k4; do echo "merkle mono $s 3"; echo "merkle mono $s 6"; echo "merkle mono $s 8"; done
} | CT=$CT L=$L xargs -P ${JOBS:-16} -L 1 sh -c 'python3 $CT verify/lz3s_16.so $0 $1 18 sram=32 gddr=2 store=$2 tile=$3 audit > $L/$0_$1_store_$2_tk$3.log 2>&1'
for f in $L/*.log; do
  printf "%s " $(basename $f .log); grep -h "^  cycles" $f | awk '{printf "%s ", $2}'; grep -h "engine utilization" $f | sed 's/(node.*//; s/  engine utilization  //' | tr -d '\n'
  grep -qh "check: .*OK" $f && echo " OK" || { echo " FAIL"; tail -n 2 $f; }
done
