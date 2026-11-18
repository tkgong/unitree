module unit18_regr (
    input  logic              clk,
    input  logic              rst,
    input  logic [324*64-1:0] lin_c,
    output logic [324*64-1:0] lout_c,
    input  logic [396*64-1:0] lin_b,
    output logic [396*64-1:0] lout_b,
    input  logic [16*64-1:0]  lin_m,
    output logic [16*64-1:0]  lout_m,
    input  logic              mono, mono2, blake,
    input  logic [8:0]        r, r2,
    input  logic [2*9-1:0]    rg_c,
    input  logic [2*9-1:0]    rg_b
);
    unit18_reg #(.ROT(1)) u (.clk(clk), .rst(rst), .lin_c(lin_c), .lout_c(lout_c), .lin_b(lin_b), .lout_b(lout_b),
        .lin_m(lin_m), .lout_m(lout_m), .mono(mono), .mono2(mono2), .blake(blake), .r(r), .r2(r2), .rg_c(rg_c), .rg_b(rg_b));
endmodule
