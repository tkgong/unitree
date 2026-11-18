module alu_addf #(
    parameter int H = 31
) (
    input  logic [31:0] a,
    input  logic [31:0] b,
    output logic [30:0] t
);
    logic [31:0] r0, r1;
    assign r0 = a + b;
    assign r1 = a + b + 32'd1;
    generate
        if (H >= 31) begin : g31
            assign t = r0[31] ? r1[30:0] : r0[30:0];
        end else begin : gh
            assign t[30:H]  = r0[30:H];
            assign t[H-1:0] = r0[31] ? r1[H-1:0] : r0[H-1:0];
        end
    endgenerate
endmodule
