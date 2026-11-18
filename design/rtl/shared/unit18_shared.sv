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
    localparam int G0 = 6 * 5 * BL * 64;
    localparam int G1 = 6 * 4 * BL * 64;
    localparam int PB = G0 + G1;
    logic [216*32-1:0] ea0, eb0, ey0, ea1, eb1, ey1;
`include "pe_map.svh"
    logic [PB-1:0]    pr0, an0, d0, pr1, an1, d1;
    logic [NS*64-1:0] mn0, ms0, mn1, ms1;
    generate
        for (genvar g = 0; g < 2; g++) begin : g_grp
            for (genvar lv = 1; lv <= 6; lv++) begin : g_lv
                for (genvar b = 0; b < (g == 0 ? 5 : 4); b++) begin : g_blk
                    for (genvar l = 0; l < BL; l++) begin : g_lane
                        localparam int P = (g == 0 ? 0 : G0) + (lv - 1) * (g == 0 ? 5 : 4) * BL * 64 + (b * BL + l) * 64;
                        localparam int U  = lane_slot(g, lv, b, l);
                        localparam int K0 = lane_clean(g, lv, b, l, 0);
                        localparam int K1 = lane_clean(g, lv, b, l, 1);
                        localparam bit XB = (U >= NV + C_XB) && (U < NV + NC);
                        if (K0 >= 0) begin : g_c0
                            assign d0[P +: 64] = mn0[(CL0 + K0)*64 +: 64] | an0[P +: 64];
                        end else if (U >= 0 && XB) begin : g_x0
                            assign d0[P +: 64] = mn0[U*64 +: 64] | an0[P +: 64];
                        end else if (U >= 0) begin : g_m0
                            assign d0[P +: 64] = (ms0[U*64 +: 64] & mn0[U*64 +: 64]) | (~ms0[U*64 +: 64] & an0[P +: 64]);
                        end else begin : g_a0
                            assign d0[P +: 64] = an0[P +: 64];
                        end
                        if (K1 >= 0) begin : g_c1
                            assign d1[P +: 64] = mn1[(CL0 + K1)*64 +: 64] | an1[P +: 64];
                        end else if (U >= 0 && XB) begin : g_x1
                            assign d1[P +: 64] = mn1[U*64 +: 64] | an1[P +: 64];
                        end else if (U >= 0) begin : g_m1
                            assign d1[P +: 64] = (ms1[U*64 +: 64] & mn1[U*64 +: 64]) | (~ms1[U*64 +: 64] & an1[P +: 64]);
                        end else begin : g_a1
                            assign d1[P +: 64] = an1[P +: 64];
                        end
                    end
                end
            end
        end
    endgenerate
    always_ff @(posedge clk) begin
        pr0 <= d0;
        pr1 <= d1;
    end
    mono_dp18 #(.NL(216), .PB(PB), .CP(0), .NUP(NS * 64)) u_dp0 (.clk(clk), .rst(rst), .x(lin[396*64 +: 8*64]), .mono(mono), .r(r), .y(lout[396*64 +: 8*64]),
        .ea(ea0), .eb(eb0), .ey(ey0), .mn(mn0), .ms(ms0), .mq(pr0));
    mono_dp18 #(.NL(216), .PB(PB), .CP(1), .NUP(NS * 64)) u_dp1 (.clk(clk), .rst(rst), .x(lin[448*64 +: 8*64]), .mono(mono2), .r(r2), .y(lout[448*64 +: 8*64]),
        .ea(ea1), .eb(eb1), .ey(ey1), .mn(mn1), .ms(ms1), .mq(pr1));
    arx_group #(.NBK(5), .BL(BL), .CP(0), .PRIV(0), .EXT(1), .LAY(1)) u_g0 (.clk(clk), .x(lin[0 +: 5*BL*64]), .r(rg[0 +: 9]), .blake(blake),
        .y(lout[0 +: 5*BL*64]), .ea(ea0[0 +: 120*32]), .eb(eb0[0 +: 120*32]), .ey(ey0[0 +: 120*32]), .an(an0[0 +: G0]), .aq(pr0[0 +: G0]));
    arx_group #(.NBK(4), .BL(BL), .CP(0), .PRIV(0), .EXT(1), .LAY(1)) u_g1 (.clk(clk), .x(lin[110*64 +: 4*BL*64]), .r(rg[9 +: 9]), .blake(blake),
        .y(lout[110*64 +: 4*BL*64]), .ea(ea0[120*32 +: 96*32]), .eb(eb0[120*32 +: 96*32]), .ey(ey0[120*32 +: 96*32]), .an(an0[G0 +: G1]), .aq(pr0[G0 +: G1]));
    arx_group #(.NBK(5), .BL(BL), .CP(1), .PRIV(0), .EXT(1), .LAY(1)) u_g2 (.clk(clk), .x(lin[198*64 +: 5*BL*64]), .r(rg[18 +: 9]), .blake(blake),
        .y(lout[198*64 +: 5*BL*64]), .ea(ea1[0 +: 120*32]), .eb(eb1[0 +: 120*32]), .ey(ey1[0 +: 120*32]), .an(an1[0 +: G0]), .aq(pr1[0 +: G0]));
    arx_group #(.NBK(4), .BL(BL), .CP(1), .PRIV(0), .EXT(1), .LAY(1)) u_g3 (.clk(clk), .x(lin[308*64 +: 4*BL*64]), .r(rg[27 +: 9]), .blake(blake),
        .y(lout[308*64 +: 4*BL*64]), .ea(ea1[120*32 +: 96*32]), .eb(eb1[120*32 +: 96*32]), .ey(ey1[120*32 +: 96*32]), .an(an1[G0 +: G1]), .aq(pr1[G0 +: G1]));
    assign lout[404*64 +: 44*64] = '0;
endmodule
