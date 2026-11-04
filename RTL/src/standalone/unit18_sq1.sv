// unit18_sq1.sv - timing probe of the single-stage squarer (alu_mul31_en_p2 EXT = 2) as the shared unit uses it: x from a
// register, the square into a register through the PE vector's select (ms ? square : the ARX value). Not a unit.
module unit18_sq1 (
    input  logic        clk,
    input  logic        en,
    input  logic [30:0] x,
    input  logic        ms,
    input  logic [61:0] an,
    output logic [61:0] y
);
    logic [30:0] xq;
    logic [61:0] yd, yq;
    always_ff @(posedge clk) xq <= x;
    alu_mul31_en_p2 #(.EXT(2)) u_sq (.clk(clk), .en(en), .a(xq), .b(xq), .y(), .yd(yd), .yq(yq), .s1d(), .s1q('0));
    always_ff @(posedge clk) yq <= ms ? yd : an;
    assign y = yq;
endmodule
