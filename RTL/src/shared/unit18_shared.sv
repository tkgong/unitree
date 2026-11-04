// unit18_shared.sv - the 18-block shared unit (ChaCha20 + BLAKE3 + Monolith-31), hand-written; the program interface of
// the HLS unit dse/TOP/bz3s (verify/lz3s_16.dll): 456 lanes in / out per cycle, mono / mono2 / r / r2 for the two
// Monolith datapaths, blake and the round index rg[g] of each block group.
//   PE 0: datapath 0 (lanes 396..403) + group 0 (blocks 0..4, lanes 0..109, copy 0) + group 1 (blocks 5..8, lanes 110..197)
//   PE 1: datapath 1 (lanes 448..455) + group 2 (blocks 9..13, lanes 198..307, copy 1) + group 3 (blocks 14..17, 308..395)
// The 9 blocks of a PE do their 216 adds per cycle on the datapath's lent adders (mono_dp18, alu_lend: the first 216 by width). A program
// holds either Monolith states or ARX blocks, never both (the compiler); the datapath lends while it holds no state.
// One register vector per PE (pr0 / pr1, 76,032 bits): the ARX groups' six level registers, and the Monolith datapath's value
// registers at fixed slots in it (mono_dp18 PB): a register takes the Monolith value when a Monolith state enters its level.
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
    localparam int G0 = 6 * 5 * BL * 64;                     // the level registers of group 0 / 2 (5 blocks) ...
    localparam int G1 = 6 * 4 * BL * 64;                     // ... and of group 1 / 3 (4 blocks)
    localparam int PB = G0 + G1;                             // one register vector per PE: 76,032 bits
    logic [216*32-1:0] ea0, eb0, ey0, ea1, eb1, ey1;
    logic [PB-1:0] pr0, mn0, ms0, an0, pr1, mn1, ms1, an1;
    // the PE registers: the Monolith value where a Monolith state enters that register's level, else the ARX value
    always_ff @(posedge clk) begin
        pr0 <= (ms0 & mn0) | (~ms0 & an0);
        pr1 <= (ms1 & mn1) | (~ms1 & an1);
    end
    mono_dp18 #(.NL(216), .PB(PB)) u_dp0 (.clk(clk), .rst(rst), .x(lin[396*64 +: 8*64]), .mono(mono), .r(r), .y(lout[396*64 +: 8*64]),
        .ea(ea0), .eb(eb0), .ey(ey0), .mn(mn0), .ms(ms0), .mq(pr0));
    mono_dp18 #(.NL(216), .PB(PB)) u_dp1 (.clk(clk), .rst(rst), .x(lin[448*64 +: 8*64]), .mono(mono2), .r(r2), .y(lout[448*64 +: 8*64]),
        .ea(ea1), .eb(eb1), .ey(ey1), .mn(mn1), .ms(ms1), .mq(pr1));
    // PE 0: group 0 (5 blocks) on adders 0..119, group 1 (4 blocks) on 120..215
    arx_group #(.NBK(5), .BL(BL), .CP(0), .PRIV(0), .EXT(1)) u_g0 (.clk(clk), .x(lin[0 +: 5*BL*64]), .r(rg[0 +: 9]), .blake(blake),
        .y(lout[0 +: 5*BL*64]), .ea(ea0[0 +: 120*32]), .eb(eb0[0 +: 120*32]), .ey(ey0[0 +: 120*32]), .an(an0[0 +: G0]), .aq(pr0[0 +: G0]));
    arx_group #(.NBK(4), .BL(BL), .CP(0), .PRIV(0), .EXT(1)) u_g1 (.clk(clk), .x(lin[110*64 +: 4*BL*64]), .r(rg[9 +: 9]), .blake(blake),
        .y(lout[110*64 +: 4*BL*64]), .ea(ea0[120*32 +: 96*32]), .eb(eb0[120*32 +: 96*32]), .ey(ey0[120*32 +: 96*32]), .an(an0[G0 +: G1]), .aq(pr0[G0 +: G1]));
    // PE 1
    arx_group #(.NBK(5), .BL(BL), .CP(1), .PRIV(0), .EXT(1)) u_g2 (.clk(clk), .x(lin[198*64 +: 5*BL*64]), .r(rg[18 +: 9]), .blake(blake),
        .y(lout[198*64 +: 5*BL*64]), .ea(ea1[0 +: 120*32]), .eb(eb1[0 +: 120*32]), .ey(ey1[0 +: 120*32]), .an(an1[0 +: G0]), .aq(pr1[0 +: G0]));
    arx_group #(.NBK(4), .BL(BL), .CP(1), .PRIV(0), .EXT(1)) u_g3 (.clk(clk), .x(lin[308*64 +: 4*BL*64]), .r(rg[27 +: 9]), .blake(blake),
        .y(lout[308*64 +: 4*BL*64]), .ea(ea1[120*32 +: 96*32]), .eb(eb1[120*32 +: 96*32]), .ey(ey1[120*32 +: 96*32]), .an(an1[G0 +: G1]), .aq(pr1[G0 +: G1]));
    assign lout[404*64 +: 44*64] = '0;                        // lanes 404..447: no state (the HLS datapath's internal lanes)
endmodule
