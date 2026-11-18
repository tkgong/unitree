module alu_add #(
    parameter int W = 32
) (
    input  logic [W-1:0] a,
    input  logic [W-1:0] b,
    output logic [W-1:0] y
);
`ifdef KS45
    if (1) begin : g_ks
        alu_add_ks45 #(.W(W)) u_ks (.a(a), .b(b), .y(y));
    end else begin : g_beh
        assign y = a + b;
    end
`else
    assign y = a + b;
`endif
endmodule
