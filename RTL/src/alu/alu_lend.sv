// ALU-ADD operand select (alu_lend<W>): the ARX operands (ea, eb) when ext (no datapath issue at this level), else the
// datapath's own (a, b); the sum feeds both (the ARX block takes y[31:0] as EY).
module alu_lend #(
    parameter int W = 32
) (
    input  logic         ext,
    input  logic [W-1:0] ea,
    input  logic [W-1:0] eb,
    input  logic [W-1:0] a,
    input  logic [W-1:0] b,
    output logic [W-1:0] y
);
    logic [W-1:0] la, lb;
    assign la = ext ? ea : a;
    assign lb = ext ? eb : b;
    alu_add #(.W(W)) u_add (.a(la), .b(lb), .y(y));
endmodule
