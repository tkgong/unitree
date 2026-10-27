// alu_mul31_en: the 31 x 31 -> 62 multiplier, 0 when the issue has no Bricks (en = 0).
module alu_mul31_en (
    input  logic        en,
    input  logic [30:0] a,
    input  logic [30:0] b,
    output logic [61:0] y
);
    logic [61:0] p;
    assign p = a * b;
    assign y = en ? p : 62'd0;
endmodule
