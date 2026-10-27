// ORFS top: alu_lend<32> between pipeline registers (as it sits in the unit), so the flow has a real clock and a
// register-to-register path. The ALU's own area = total standard-cell area minus the flip-flops.
module alu_lend_32_reg (
    input  logic        clk,
    input  logic        ext,
    input  logic [31:0] ea, eb, a, b,
    output logic [31:0] y
);
    logic        ext_q;
    logic [31:0] ea_q, eb_q, a_q, b_q, y_d;
    always_ff @(posedge clk) begin
        ext_q <= ext; ea_q <= ea; eb_q <= eb; a_q <= a; b_q <= b;
        y <= y_d;
    end
    alu_lend #(.W(32)) u (.ext(ext_q), .ea(ea_q), .eb(eb_q), .a(a_q), .b(b_q), .y(y_d));
endmodule
