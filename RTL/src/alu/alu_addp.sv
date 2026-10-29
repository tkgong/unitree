// ALU-ADP: the W-bit private adder (alu_addp<W>): engine part sums and constants, reduction first adders that are not
// lent, the datapath adders that are not lent. Same arithmetic as alu_add; kept apart so the instance roles stay
// distinct (176 in the datapaths, W = 32..41; 268 in the four Poseidon2 engines, W = 32..35).
module alu_addp #(
    parameter int W = 32
) (
    input  logic [W-1:0] a,
    input  logic [W-1:0] b,
    output logic [W-1:0] y
);
`ifdef KS45                                                   // timing flow: the structural Nangate45 Kogge-Stone adder
    if (1 && W == 32) begin : g_ks
        alu_add_ks45 #(.W(W)) u_ks (.a(a), .b(b), .y(y));
    end else begin : g_beh
        assign y = a + b;
    end
`else
    assign y = a + b;
`endif
endmodule
