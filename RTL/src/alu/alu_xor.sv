// ALU-XOR: 64-bit xor (alu_xor), the ARX blocks' only own logic (22 in level_ops_axn.h).
module alu_xor (
    input  logic [63:0] a,
    input  logic [63:0] b,
    output logic [63:0] y
);
    assign y = a ^ b;
endmodule
