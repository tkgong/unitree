module alu_canon #(
    parameter int W = 32
) (
    input  logic [30:0]  t,
    output logic [W-1:0] y
);
    localparam logic [30:0] P31 = 31'h7FFF_FFFF;
    assign y = (t == P31) ? {W{1'b0}} : {{(W-31){1'b0}}, t};
endmodule
