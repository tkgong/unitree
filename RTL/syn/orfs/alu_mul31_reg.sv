// ORFS top: alu_mul31 between pipeline registers. The ALU's own area = total standard-cell area minus the flip-flops.
module alu_mul31_reg (
    input  logic        clk,
    input  logic [30:0] a, b,
    output logic [61:0] y
);
    logic [30:0] a_q, b_q;
    logic [61:0] y_d;
    always_ff @(posedge clk) begin
        a_q <= a; b_q <= b;
        y <= y_d;
    end
    alu_mul31 u (.a(a_q), .b(b_q), .y(y_d));
endmodule
