module alu_bar_chunk #(
    parameter int W = 8
) (
    input  logic [W-1:0] x,
    output logic [W-1:0] y
);
    logic [W-1:0] nx, r1, r2, r3, t;
    assign nx = ~x;
    assign r1 = {nx[W-2:0], nx[W-1]};
    assign r2 = {x[W-3:0], x[W-1:W-2]};
    assign r3 = {x[W-4:0], x[W-1:W-3]};
    generate
        if (W == 7) begin : g7
            assign t = x ^ (r1 & r2);
        end else begin : g8
            assign t = x ^ (r1 & r2 & r3);
        end
    endgenerate
    assign y = {t[W-2:0], t[W-1]};
endmodule
