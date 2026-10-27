// alu_negm31<W>: p - t (t <= p), zero-extended to the W-bit operand of an add (the engines' y0 = part + (p - t)).
module alu_negm31 #(
    parameter int W = 33
) (
    input  logic [30:0]  t,
    output logic [W-1:0] y
);
    localparam logic [30:0] P31 = 31'h7FFF_FFFF;
    logic [30:0] d;
    assign d = P31 - t;
    assign y = {{(W-31){1'b0}}, d};
endmodule
