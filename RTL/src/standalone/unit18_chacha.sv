// unit18_chacha.sv - the natural ChaCha20 unit, hand-written: 18 blocks of 18 lanes in two groups of 9 (copy 0: blocks
// 0..8, lanes 0..161; copy 1: blocks 9..17, lanes 162..323), entry level 1, latency 6, private adders (4 per block step,
// 216 per group). Program interface of dse/TOP/nat18c built with MODES_MASK 0x04 (verify/lnc18_04): 324 lanes.
module unit18_chacha (
    input  logic            clk,
    input  logic            rst,
    input  logic [324*64-1:0] lin,
    output logic [324*64-1:0] lout,
    input  logic            mono, mono2, htap, blake,
    input  logic [8:0]      r, r2,
    input  logic [2*9-1:0]  rg
);
    localparam int BL = 18;
    logic [216*32-1:0] nc_a0, nc_b0, nc_a1, nc_b1;
    arx_group #(.NBK(9), .BL(BL), .CP(0), .PRIV(1)) u_g0 (.clk(clk), .x(lin[0 +: 9*BL*64]), .r(rg[0 +: 9]), .blake(1'b0),
        .y(lout[0 +: 9*BL*64]), .ea(nc_a0), .eb(nc_b0), .ey('0));
    arx_group #(.NBK(9), .BL(BL), .CP(1), .PRIV(1)) u_g1 (.clk(clk), .x(lin[162*64 +: 9*BL*64]), .r(rg[9 +: 9]), .blake(1'b0),
        .y(lout[162*64 +: 9*BL*64]), .ea(nc_a1), .eb(nc_b1), .ey('0));
endmodule
