// ALU-ADD: the W-bit lendable adder (alu_add<W> in dse/TOP/alu_core.h). A plain integer adder, no modulus: W is the
// generator's bound on the sum, so y is the exact sum (every emitted W holds the worst case, checked statically); the
// ARX side reads y[31:0] = (a + b) mod 2^32, the M31 side reduces once at the end of its adder tree (alu_fold).
// 912 instances in the bz unit, W = 32..41 (444 / 176 / 104 / 66 / 40 / 34 / 26 / 16 / 4 / 2).
module alu_add #(
    parameter int W = 32
) (
    input  logic [W-1:0] a,
    input  logic [W-1:0] b,
    output logic [W-1:0] y
);
    assign y = a + b;
endmodule
