#!/bin/sh
# ks_equiv.sh - formal equivalence (Yosys miter + SAT) of the structural Nangate45 Kogge-Stone adder alu_add_ks45 #(W)
# against y = a + b, W = 32 and 33, with the cell functions taken from the liberty itself (read_liberty without -lib).
#   sh ks_equiv.sh            (dana336)
R=$(cd "$(dirname "$0")/.." && pwd); . "$R/env.sh"
cd "$R/test"
cat > ks_equiv.ys <<EOF
read_liberty -ignore_miss_func $LIB
read_verilog -sv $A/alu_add_ks45.sv
read_verilog -sv -DKS45 $A/alu_add.sv $A/alu_addp.sv $A/alu_lend.sv
rename alu_add alu_add_k
rename alu_addp alu_addp_k
rename alu_lend alu_lend_k
read_verilog -sv $A/alu_add.sv $A/alu_addp.sv $A/alu_lend.sv
read_verilog -sv <<V
module gatep (input [31:0] a, input [31:0] b, output [31:0] y); alu_addp_k #(.W(32)) u (.a(a), .b(b), .y(y)); endmodule
module goldp (input [31:0] a, input [31:0] b, output [31:0] y); alu_addp #(.W(32)) u (.a(a), .b(b), .y(y)); endmodule
module gatel (input e, input [32:0] ea, input [32:0] eb, input [32:0] a, input [32:0] b, output [32:0] y); alu_lend_k #(.W(33)) u (.ext(e), .ea(ea), .eb(eb), .a(a), .b(b), .y(y)); endmodule
module goldl (input e, input [32:0] ea, input [32:0] eb, input [32:0] a, input [32:0] b, output [32:0] y); alu_lend #(.W(33)) u (.ext(e), .ea(ea), .eb(eb), .a(a), .b(b), .y(y)); endmodule
module gold #(parameter int W = 32) (input [W-1:0] a, input [W-1:0] b, output [W-1:0] y); assign y = a + b; endmodule
module gate32 (input [31:0] a, input [31:0] b, output [31:0] y); alu_add_ks45 #(.W(32)) u (.a(a), .b(b), .y(y)); endmodule
module gold32 (input [31:0] a, input [31:0] b, output [31:0] y); gold #(.W(32)) u (.a(a), .b(b), .y(y)); endmodule
module gate33 (input [32:0] a, input [32:0] b, output [32:0] y); alu_add_ks45 #(.W(33)) u (.a(a), .b(b), .y(y)); endmodule
module gold33 (input [32:0] a, input [32:0] b, output [32:0] y); gold #(.W(33)) u (.a(a), .b(b), .y(y)); endmodule
V
hierarchy -check
proc
flatten
miter -equiv -flatten -make_outputs gold32 gate32 m32
miter -equiv -flatten -make_outputs gold33 gate33 m33
sat -verify -prove trigger 0 -show-ports m32
sat -verify -prove trigger 0 -show-ports m33
miter -equiv -flatten -make_outputs goldp gatep mp
miter -equiv -flatten -make_outputs goldl gatel ml
sat -verify -prove trigger 0 mp
sat -verify -prove trigger 0 ml
EOF
yosys -q -l ks_equiv.log ks_equiv.ys > /dev/null 2>&1
grep -E "SUCCESS|FAIL|ERROR|proof" ks_equiv.log | head
