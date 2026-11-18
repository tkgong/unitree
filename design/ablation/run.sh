#!/bin/sh
D=$(cd "$(dirname "$0")/.." && pwd); H=$D/ablation; O=${OUT:-$D/syn/work_ablation}
mkdir -p $O; : > $O/stage.txt
rm -rf $O/a $O/r $O/n; mkdir -p $O/stub
for t in a r; do
  mkdir -p $O/$t/syn $O/$t/flow/timing
  cp $D/env.sh $O/$t/; cp -r $D/rtl $O/$t/rtl
  cp $D/syn/syn.sh $D/syn/repair.sh $O/$t/syn/; cp $D/flow/timing/sta.sh $O/$t/flow/timing/
done
cp $H/unit18_alu.sv $O/a/rtl/standalone/
cp $H/slots/alu_lend.sv $H/slots/alu_mul31_en_p2.sv $O/r/rtl/alu/
cp $H/slots/kara_pkg.sv $H/slots/mono_dp18.sv $O/r/rtl/shared/
cp $H/unit18_reg.sv $H/unit18_regr.sv $O/r/rtl/standalone/
cp -r $O/r $O/n
echo 'SRC_BLK="$SRC_BLK $R/rtl/standalone/unit18_reg.sv"' >> $O/r/env.sh
R=$O/a; . $R/env.sh
echo $LIB > $O/lib.txt
printf '#!/bin/sh\nexit 0\n' > $O/stub/yosys; chmod +x $O/stub/yosys
one() {
  cd $O/$1/syn || return
  PATH=$O/stub:$PATH WORK=work MODES=flat KEEPALU=1 KS45=1 NET=1 ABC_SPEED=1 ADDER=kogge-stone ABC_D=600 sh syn.sh $2 > /dev/null 2>&1
  awk -v s=work/${2}_ka.txt -v lib=$LIB '/^setattr -mod -unset keep_hierarchy/ {print "tee -o " s " stat -liberty " lib} {print}' work/$2.flat.ys > work/$2.ka.ys
  yosys -q -l work/$2.ka.log work/$2.ka.ys > /dev/null 2>&1; echo "$3 synthesis exit $? $(date)" >> $O/stage.txt
  WORK=work PERIOD=${4:-1.0} sh repair.sh $2 > $O/${3}_repair.txt 2>&1; echo "$3 repair exit $? $(date)" >> $O/stage.txt
  ( cd .. && WORK=work NL=rep sh flow/timing/sta.sh $2 ) > $O/${3}_sta.txt 2>&1; echo "$3 sign-off exit $? $(date)" >> $O/stage.txt
  cp work/${2}_rep.v $O/${3}_rep.v; cp work/${2}_ka.txt $O/${3}_ka.txt
}
one a alu alu_only & one r regr reg_strict & one a shared bind & wait
one n reg reg_lane & one a mono mono & wait
one a chacha chacha & one a blake3 blake3 & wait
python3 $H/summary.py $O > $O/sharing.csv 2>&1
echo "ALL DONE $(date)" >> $O/stage.txt
cat $O/stage.txt $O/sharing.csv
