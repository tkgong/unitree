#!/bin/sh
# run_tile.sh - subtree (tile) size sweep per primitive and store mode: 2^18 trees on the unit RTL/src implements
# (dse/TOP/verify/lz3s_16.so), 32 KB SRAM, GDDR6 2 channels (one core's share of the RTX 3070's memory), audit on.
# tile=<TK>: subtrees of 2^TK leaves (Merkle: two leaf tiles double-buffered; GGM: DFS tiles under the reserve rule).
#   sh memsim/run_tile.sh            -> memsim/results/tile18/<req>_<prim>_store_<s>_tk<TK>.log (16 at a time)
H=$(cd "$(dirname "$0")" && pwd); CT=$H/../RTL/compiler/compile_tree.py; L=$H/results/tile18; mkdir -p $L
cd "$H/../dse/TOP"
J=${JOBS:-16}
{
  for s in out all; do for tk in 4 5 6 7 8 9; do echo "merkle blake3 $s $tk"; done; done
  for p in chacha blake3; do for s in out k2 all; do for tk in 2 3 4 5 6 7; do echo "ggm $p $s $tk"; done; done; done
  for s in out all; do for tk in 2 3 4 5 6 7 8 9; do echo "merkle mono $s $tk"; done; done
} | CT=$CT L=$L xargs -P $J -L 1 sh -c 'python3 $CT verify/lz3s_16.so $0 $1 18 sram=32 gddr=2 store=$2 tile=$3 audit > $L/$0_$1_store_$2_tk$3.log 2>&1'
for f in $L/*.log; do
  printf "%s " $(basename $f .log); grep -h "^  cycles" $f | awk '{printf "%s ", $2}'; grep -h "SRAM high-water" $f | awk '{printf "%s KB ", $8}'
  grep -qh "check: .*OK" $f && echo OK || { echo FAIL; tail -n 2 $f; }
done
