module alu_csa31 (
    input  logic [30:0] x,
    input  logic [30:0] y,
    input  logic [30:0] z,
    output logic [30:0] s,
    output logic [30:0] cr
);
    logic [30:0] c;
    assign s  = x ^ y ^ z;
    assign c  = (x & y) | (x & z) | (y & z);
    assign cr = {c[29:0], c[30]};
endmodule
