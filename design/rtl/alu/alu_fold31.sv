module alu_fold31 (
    input  logic [31:0] r,
    output logic [30:0] t
);
    assign t = r[30:0] + r[31];
endmodule
