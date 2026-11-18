module unit18_regc (
    input  logic            clk,
    input  logic            rst,
    input  logic [324*64-1:0] lin,
    output logic [324*64-1:0] lout,
    input  logic            mono, mono2, htap, blake,
    input  logic [8:0]      r, r2,
    input  logic [2*9-1:0]  rg
);
    logic [396*64-1:0] nb;
    logic [16*64-1:0]  nm;
    unit18_reg u (.clk(clk), .rst(rst), .lin_c(lin), .lout_c(lout), .lin_b('0), .lout_b(nb), .lin_m('0), .lout_m(nm),
        .mono(1'b0), .mono2(1'b0), .blake(1'b0), .r(9'd0), .r2(9'd0), .rg_c(rg), .rg_b(18'd0));
endmodule

module unit18_regb (
    input  logic            clk,
    input  logic            rst,
    input  logic [396*64-1:0] lin,
    output logic [396*64-1:0] lout,
    input  logic            mono, mono2, htap, blake,
    input  logic [8:0]      r, r2,
    input  logic [2*9-1:0]  rg
);
    logic [324*64-1:0] nc;
    logic [16*64-1:0]  nm;
    unit18_reg u (.clk(clk), .rst(rst), .lin_c('0), .lout_c(nc), .lin_b(lin), .lout_b(lout), .lin_m('0), .lout_m(nm),
        .mono(1'b0), .mono2(1'b0), .blake(1'b1), .r(9'd0), .r2(9'd0), .rg_c(18'd0), .rg_b(rg));
endmodule

module unit18_regm (
    input  logic            clk,
    input  logic            rst,
    input  logic [456*64-1:0] lin,
    output logic [456*64-1:0] lout,
    input  logic            mono, mono2, htap, blake,
    input  logic [8:0]      r, r2,
    input  logic [4*9-1:0]  rg
);
    logic [324*64-1:0] nc;
    logic [396*64-1:0] nb;
    logic [16*64-1:0]  ym;
    unit18_reg u (.clk(clk), .rst(rst), .lin_c('0), .lout_c(nc), .lin_b('0), .lout_b(nb),
        .lin_m({lin[448*64 +: 8*64], lin[396*64 +: 8*64]}), .lout_m(ym),
        .mono(mono), .mono2(mono2), .blake(blake), .r(r), .r2(r2), .rg_c(18'd0), .rg_b(18'd0));
    assign lout[0 +: 396*64]       = '0;
    assign lout[396*64 +: 8*64]    = ym[0 +: 8*64];
    assign lout[404*64 +: 44*64]   = '0;
    assign lout[448*64 +: 8*64]    = ym[8*64 +: 8*64];
endmodule
