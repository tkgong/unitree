// ALU-BAR: Monolith Bars S-box on one 31-bit element in a 32-bit word (alu_bar31): 8 / 8 / 8 / 7-bit chunks, bit 31 = 0.
module alu_bar31 (
    input  logic [31:0] x,
    output logic [31:0] y
);
    alu_bar_chunk #(.W(8)) u_c0 (.x(x[7:0]),   .y(y[7:0]));
    alu_bar_chunk #(.W(8)) u_c1 (.x(x[15:8]),  .y(y[15:8]));
    alu_bar_chunk #(.W(8)) u_c2 (.x(x[23:16]), .y(y[23:16]));
    alu_bar_chunk #(.W(7)) u_c3 (.x(x[30:24]), .y(y[30:24]));
    assign y[31] = 1'b0;
endmodule
