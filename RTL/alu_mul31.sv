// ALU-MUL: 31 x 31 -> 62 multiplier (alu_mul31): Bricks squares x^2 x^4 x^5 and the Poseidon2 engines' products.
// The full product; the M31 reduction is a separate lo31 + hi31 adder (alu_addp<32>) and an alu_fold31.
module alu_mul31 (
    input  logic [30:0] a,
    input  logic [30:0] b,
    output logic [61:0] y
);
    assign y = a * b;
endmodule
