// unit18_mono.sv - the natural Monolith-31 unit, hand-written: the two datapaths of the shared unit with every adder
// private (no lending), no ARX blocks. Program interface of dse/TOP/bz3s built with MODES_MASK 0x10 (verify/lm3s_10):
// 456 lanes, the datapaths at lanes 396 and 448.
module unit18_mono (
    input  logic            clk,
    input  logic            rst,
    input  logic [456*64-1:0] lin,
    output logic [456*64-1:0] lout,
    input  logic            mono, mono2, htap, blake,
    input  logic [8:0]      r, r2,
    input  logic [4*9-1:0]  rg
);
    logic [31:0] nc0, nc1;
    mono_dp18 #(.NL(0)) u_dp0 (.clk(clk), .rst(rst), .x(lin[396*64 +: 8*64]), .mono(mono), .r(r), .y(lout[396*64 +: 8*64]),
        .ea(32'd0), .eb(32'd0), .ey(nc0));
    mono_dp18 #(.NL(0)) u_dp1 (.clk(clk), .rst(rst), .x(lin[448*64 +: 8*64]), .mono(mono2), .r(r2), .y(lout[448*64 +: 8*64]),
        .ea(32'd0), .eb(32'd0), .ey(nc1));
    assign lout[0 +: 396*64]     = '0;
    assign lout[404*64 +: 44*64] = '0;
endmodule
