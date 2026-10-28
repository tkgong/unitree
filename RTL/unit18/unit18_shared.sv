// unit18_shared.sv - the 18-block shared unit (ChaCha20 + BLAKE3 + Monolith-31), hand-written; the program interface of
// the HLS unit dse/TOP/bz3s (verify/lz3s_16.dll): 456 lanes in / out per cycle, mono / mono2 / r / r2 for the two
// Monolith datapaths, blake and the round index rg[g] of each block group.
//   PE 0: datapath 0 (lanes 396..403) + group 0 (blocks 0..4, lanes 0..109, copy 0) + group 1 (blocks 5..8, lanes 110..197)
//   PE 1: datapath 1 (lanes 448..455) + group 2 (blocks 9..13, lanes 198..307, copy 1) + group 3 (blocks 14..17, 308..395)
// The 9 blocks of a PE do their 216 adds per cycle on the first 216 adders of the datapath's level 6 (alu_lend). A program
// holds either Monolith states or ARX blocks, never both (the compiler); the datapath lends while it holds no state.
module unit18_shared (
    input  logic            clk,
    input  logic            rst,
    input  logic [456*64-1:0] lin,
    output logic [456*64-1:0] lout,
    input  logic            mono, mono2, htap, blake,
    input  logic [8:0]      r, r2,
    input  logic [4*9-1:0]  rg
);
    localparam int BL = 22;
    logic [216*32-1:0] ea0, eb0, ey0, ea1, eb1, ey1;
    mono_dp18 #(.NL(216)) u_dp0 (.clk(clk), .rst(rst), .x(lin[396*64 +: 8*64]), .mono(mono), .r(r), .y(lout[396*64 +: 8*64]),
        .ea(ea0), .eb(eb0), .ey(ey0));
    mono_dp18 #(.NL(216)) u_dp1 (.clk(clk), .rst(rst), .x(lin[448*64 +: 8*64]), .mono(mono2), .r(r2), .y(lout[448*64 +: 8*64]),
        .ea(ea1), .eb(eb1), .ey(ey1));
    // PE 0: group 0 (5 blocks) on adders 0..119, group 1 (4 blocks) on 120..215
    arx_group #(.NBK(5), .BL(BL), .CP(0), .PRIV(0)) u_g0 (.clk(clk), .x(lin[0 +: 5*BL*64]), .r(rg[0 +: 9]), .blake(blake),
        .y(lout[0 +: 5*BL*64]), .ea(ea0[0 +: 120*32]), .eb(eb0[0 +: 120*32]), .ey(ey0[0 +: 120*32]));
    arx_group #(.NBK(4), .BL(BL), .CP(0), .PRIV(0)) u_g1 (.clk(clk), .x(lin[110*64 +: 4*BL*64]), .r(rg[9 +: 9]), .blake(blake),
        .y(lout[110*64 +: 4*BL*64]), .ea(ea0[120*32 +: 96*32]), .eb(eb0[120*32 +: 96*32]), .ey(ey0[120*32 +: 96*32]));
    // PE 1
    arx_group #(.NBK(5), .BL(BL), .CP(1), .PRIV(0)) u_g2 (.clk(clk), .x(lin[198*64 +: 5*BL*64]), .r(rg[18 +: 9]), .blake(blake),
        .y(lout[198*64 +: 5*BL*64]), .ea(ea1[0 +: 120*32]), .eb(eb1[0 +: 120*32]), .ey(ey1[0 +: 120*32]));
    arx_group #(.NBK(4), .BL(BL), .CP(1), .PRIV(0)) u_g3 (.clk(clk), .x(lin[308*64 +: 4*BL*64]), .r(rg[27 +: 9]), .blake(blake),
        .y(lout[308*64 +: 4*BL*64]), .ea(ea1[120*32 +: 96*32]), .eb(eb1[120*32 +: 96*32]), .ey(ey1[120*32 +: 96*32]));
    assign lout[404*64 +: 44*64] = '0;                        // lanes 404..447: no state (the HLS datapath's internal lanes)
endmodule
