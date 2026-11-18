module alu_fold #(
    parameter int H = 31
) (
    input  logic [31:0] r,
    output logic [30:0] t
);
    generate
        if (H >= 31) begin : g31
            assign t = r[30:0] + r[31];
        end else begin : gh
            assign t[30:H]  = r[30:H];
            assign t[H-1:0] = r[H-1:0] + r[31];
        end
    endgenerate
endmodule
