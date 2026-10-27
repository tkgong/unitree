// alu_lendp<W>: the lend select in front of a private adder (builds without MONO_LEND_MOD; not used by bz).
module alu_lendp #(
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
    alu_addp #(.W(W)) u_add (.a(la), .b(lb), .y(y));
endmodule
