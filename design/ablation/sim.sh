#!/bin/sh
R=$(cd "$(dirname "$0")/.." && pwd); H=$R/ablation; . "$R/env.sh"
W=${OUT:-$R/test/obj_ablation}; mkdir -p $W; cd $W
ulimit -s unlimited 2>/dev/null || true
ALU_R=$(echo "$SRC_ALU" | sed "s#$A/alu_lend.sv#$H/slots/alu_lend.sv#; s#$A/alu_mul31_en_p2.sv#$H/slots/alu_mul31_en_p2.sv#")
BLK_R="$H/slots/kara_pkg.sv $H/slots/mono_dp18.sv $S/arx_group.sv $S/axn_step.sv"
sed -e 's/unit18_reg u /unit18_regr u /; s/unit18_regc/unit18_regrc/g; s/unit18_regb/unit18_regrb/g; s/unit18_regm/unit18_regrm/g' $H/unit18_reg_tb.sv > unit18_regr_tb.sv
build() {
  t=$1; shift
  rm -rf obj_$t
  verilator --cc --exe --build -j 6 -Wno-fatal -Wno-lint -O1 --top-module unit18_$t -Mdir obj_$t $INC \
    -CFLAGS "-DVTOP=Vunit18_$t -DVTOP_H=\\\"Vunit18_$t.h\\\" -DTOPNAME=\\\"unit18_$t\\\"" \
    "$@" $R/test/tb_unit18.cpp > verilator_$t.log 2>&1 || { echo "unit18_$t: build failed"; grep -E "%Error|error:" verilator_$t.log | head -n 8; }
}
for t in aluc alub alum; do build $t $SRC_ALU $SRC_BLK $H/unit18_alu.sv $H/unit18_alu_tb.sv & done; wait
for t in regc regb regm; do build $t $ALU_R $BLK_R $H/unit18_reg.sv $H/unit18_reg_tb.sv & done; wait
for t in regrc regrb regrm; do build $t $ALU_R $BLK_R $H/unit18_reg.sv $H/unit18_regr.sv unit18_regr_tb.sv & done; wait
for p in "aluc chacha_gcc" "alub blake3_gb3" "alub blake3_mb3" "alum mono_mmo" "regc chacha_gcc" "regb blake3_gb3" "regb blake3_mb3" "regm mono_mmo" \
         "regrc chacha_gcc" "regrb blake3_gb3" "regrb blake3_mb3" "regrm mono_mmo"; do set -- $p
  [ -x obj_$1/Vunit18_$1 ] && echo "unit18_$1 $2: $(./obj_$1/Vunit18_$1 $R/test/tr/$2.tr | tail -n 1)"
done
