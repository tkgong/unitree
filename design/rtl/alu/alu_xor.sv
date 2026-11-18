module alu_xor (
    input  logic [63:0] a,
    input  logic [63:0] b,
    output logic [63:0] y
);
    assign y = a ^ b;
endmodule
