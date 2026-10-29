// alu_addf.sv - ALU-ADD and ALU-FLD fused: t = fold_H(a + b), the M31 reduction of a 32-bit sum, in ONE carry-chain
// depth. r = a + b (< 2^32) and r + 1 are formed by two adders in parallel (a compound adder) and the end-around carry
// r[31] selects: t[H-1:0] = (r[31] ? r + 1 : r)[H-1:0], t[30:H] = r[30:H] (the increment cannot carry out of the low
// H bits, see alu_fold; H = 31 is alu_fold31). The same function as alu_addp #(32) followed by alu_fold #(H): that
// serial adder + incrementer was the critical path of the datapath levels (Bricks, reductions, output folds).
module alu_addf #(
    parameter int H = 31
) (
    input  logic [31:0] a,
    input  logic [31:0] b,
    output logic [30:0] t
);
    logic [31:0] r0, r1;
    assign r0 = a + b;
    assign r1 = a + b + 32'd1;
    generate
        if (H >= 31) begin : g31
            assign t = r0[31] ? r1[30:0] : r0[30:0];
        end else begin : gh
            assign t[30:H]  = r0[30:H];
            assign t[H-1:0] = r0[31] ? r1[H-1:0] : r0[H-1:0];
        end
    endgenerate
endmodule
