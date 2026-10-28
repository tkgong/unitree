// alu_csa31.sv - carry-save step of three 31-bit M31 residues with the end-around carry: x + y + z = s + 2c, and the
// carry out of bit 30 (weight 2^31 = 1 mod p) wraps to bit 0, so s + cr = x + y + z (mod p) with s, cr < 2^31; one
// alu_addf #(31) then gives the residue <= p. One full-adder level instead of two serial adders (Bricks: b_i = x_i + lo31
// + hi31 of the square x_{i-1}^2).
module alu_csa31 (
    input  logic [30:0] x,
    input  logic [30:0] y,
    input  logic [30:0] z,
    output logic [30:0] s,
    output logic [30:0] cr
);
    logic [30:0] c;
    assign s  = x ^ y ^ z;
    assign c  = (x & y) | (x & z) | (y & z);
    assign cr = {c[29:0], c[30]};
endmodule
