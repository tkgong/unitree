#!/bin/sh
# regress.sh - every check and flow of RTL/ from a clean checkout (dana336), each log in $OUT (default RTL/test/regress/):
#   1. ks_equiv.sh: the Kogge-Stone adder proofs        2. run_dp.sh: one datapath vs the Python model (NL = 0, 216; KS45)
#   3. run_tb.sh: the four tops on every trace (behavioural adders and KS45)
#   4. the timing flow (syn.sh + repair.sh, WORK=work_reg) and the netlists compared with syn/work_t10 (what was measured)
#   5. the area-mapped flow (syn.sh + area/report.py, WORK=work_area)
#   sh RTL/test/regress.sh
R=$(cd "$(dirname "$0")/.." && pwd); . "$R/env.sh"
OUT=${OUT:-$R/test/regress}; mkdir -p $OUT
sh $R/test/ks_equiv.sh > $OUT/ks_equiv.log 2>&1
for nl in 0 216; do sh $R/test/run_dp.sh $nl > $OUT/dp_$nl.log 2>&1; KS45=1 sh $R/test/run_dp.sh $nl > $OUT/dp_${nl}_ks45.log 2>&1; done
for t in $TOPS; do (sh $R/test/run_tb.sh $t > $OUT/tb_$t.log 2>&1; KS45=1 sh $R/test/run_tb.sh $t > $OUT/tb_${t}_ks45.log 2>&1) & done; wait
for t in $TOPS; do
  (WORK=work_reg MODES=flat KEEPALU=1 KS45=1 NET=1 ABC_SPEED=1 ADDER=kogge-stone ABC_D=600 sh $R/syn/syn.sh $t > $OUT/syn_$t.log 2>&1
   WORK=work_reg sh $R/syn/repair.sh $t > $OUT/repair_$t.log 2>&1
   WORK=work_reg NL=rep sh $R/benchmark/timing/sta.sh $t > $OUT/sta_$t.log 2>&1
   a=$(md5sum < $R/syn/work_reg/${t}_rep.v); b=$(md5sum < $R/syn/work_t10/${t}_rep.v 2>/dev/null)
   [ "$a" = "$b" ] && echo "$t: netlist identical to work_t10" > $OUT/netlist_$t.log || echo "$t: netlist DIFFERS from work_t10" > $OUT/netlist_$t.log) &
done; wait
for t in $TOPS; do WORK=work_area sh $R/syn/syn.sh $t > $OUT/area_syn_$t.log 2>&1 & done; wait
WORK=work_area python3 $R/benchmark/area/report.py --md $OUT/area.md > $OUT/area.log 2>&1
echo "== summary"
grep -h "SUCCESS\|FAIL" $OUT/ks_equiv.log | sort | uniq -c
grep -H "SUMMARY" $OUT/dp_*.log | sed "s|.*/||"
grep -H "SUMMARY" $OUT/tb_*.log | sed "s|.*/||"
cat $OUT/sta_*.log $OUT/netlist_*.log
grep -A6 "^| sharing" $OUT/area.md
