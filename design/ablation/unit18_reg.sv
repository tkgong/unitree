module unit18_reg #(
    parameter int ROT = 0
) (
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
    localparam int NA  = 216;
    localparam int MPR = 4;
    localparam int NBC = NA / MPR;
    localparam int NBK = 9;
    localparam int LB  = 22;
    localparam int LC  = 18;
    localparam int PB  = 6 * NBK * LB * 64;
    localparam int PC  = 6 * NBK * LC * 64;
    localparam int RPR = 4;
    localparam int NRC = (6 * NBK * LB + RPR - 1) / RPR;
    generate
        for (genvar p = 0; p < 2; p++) begin : g_pe
            logic [NA*32-1:0] ca, cb, ba, bb, ea, eb, ey;
            logic [PB-1:0]    pr, mn, ms, anb, ax;
            logic [PC-1:0]    anc, aqc;
            logic [NBC-1:0]   bi, bq;
            logic [NRC-1:0]   ri, rq;
`ifdef KS45
            for (genvar c = 0; c < NBC; c++) begin : g_bc
                BUF_X1 u_b (.A(blake), .Z(bi[c]));
            end
            for (genvar c = 0; c < NRC; c++) begin : g_rc
                BUF_X1 u_r (.A(blake), .Z(ri[c]));
            end
`else
            assign bi = {NBC{blake}};
            assign ri = {NRC{blake}};
`endif
            (* keep *) always_ff @(posedge clk) begin bq <= bi; rq <= ri; end
            for (genvar q = 0; q < NA; q++) begin : g_op
                assign ea[q*32 +: 32] = bq[q / MPR] ? ba[q*32 +: 32] : ca[q*32 +: 32];
                assign eb[q*32 +: 32] = bq[q / MPR] ? bb[q*32 +: 32] : cb[q*32 +: 32];
            end
            for (genvar s = 0; s < 6; s++) begin : g_lv
                for (genvar b = 0; b < NBK; b++) begin : g_blk
                    for (genvar l = 0; l < LB; l++) begin : g_lane
                        localparam int PW = s * NBK * LB + b * LB + l;
                        if (l < LC) begin : g_cb
                            localparam int CL = (l + LC - (ROT * (s + 1)) % LC) % LC;
                            localparam int CW = s * NBK * LC + b * LC + CL;
                            assign aqc[CW*64 +: 64] = pr[PW*64 +: 64];
                            assign ax[PW*64 +: 64]  = rq[PW / RPR] ? anb[PW*64 +: 64] : anc[CW*64 +: 64];
                        end else begin : g_b
                            assign ax[PW*64 +: 64]  = anb[PW*64 +: 64];
                        end
                    end
                end
            end
            always_ff @(posedge clk) pr <= (ms & mn) | (~ms & ax);
            mono_dp18 #(.NL(NA), .PB(PB)) u_dp (.clk(clk), .rst(rst), .x(lin_m[p*8*64 +: 8*64]), .mono(p == 0 ? mono : mono2),
                .r(p == 0 ? r : r2), .y(lout_m[p*8*64 +: 8*64]), .ea(ea), .eb(eb), .ey(ey), .mn(mn), .ms(ms), .mq(pr));
            arx_group #(.NBK(NBK), .BL(LC), .CP(p), .PRIV(0), .EXT(1), .BKC(0)) u_c (.clk(clk), .x(lin_c[p*NBK*LC*64 +: NBK*LC*64]),
                .r(rg_c[p*9 +: 9]), .blake(1'b0), .y(lout_c[p*NBK*LC*64 +: NBK*LC*64]), .ea(ca), .eb(cb), .ey(ey), .an(anc), .aq(aqc));
            arx_group #(.NBK(NBK), .BL(LB), .CP(p), .PRIV(0), .EXT(1), .BKC(1)) u_b (.clk(clk), .x(lin_b[p*NBK*LB*64 +: NBK*LB*64]),
                .r(rg_b[p*9 +: 9]), .blake(1'b1), .y(lout_b[p*NBK*LB*64 +: NBK*LB*64]), .ea(ba), .eb(bb), .ey(ey), .an(anb), .aq(pr));
        end
    endgenerate
endmodule
