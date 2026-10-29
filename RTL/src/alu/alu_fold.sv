// ALU-FLD: alu_fold<H>, the M31 end-around carry of a 32-bit sum r = lo31 + hi (hi < 2^H): the low H bits of r plus
// r[31], the bits above H unchanged. Exact because r[31] = 1 implies r - 2^31 <= 2^H - 2, so the increment cannot
// carry out of the low H bits. H = 1, 4, 5, 6, 8, 9, 10 in the bz datapaths; H = 31 is alu_fold31.
module alu_fold #(
    parameter int H = 31
) (
    input  logic [31:0] r,
    output logic [30:0] t
);
    generate
        if (H >= 31) begin : g31
            assign t = r[30:0] + r[31];
        end else begin : gh
            assign t[30:H]  = r[30:H];
            assign t[H-1:0] = r[H-1:0] + r[31];
        end
    endgenerate
endmodule
