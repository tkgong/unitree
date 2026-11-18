module mono_dp18 #(
    parameter int NL  = 216,
    parameter int NLP = (NL > 0) ? NL : 1,
    parameter int PB  = 0,
    parameter int PBP = (PB > 0) ? PB : 1,
    parameter int CP  = 0,
    parameter int NUP = 1
) (
    input  logic              clk,
    input  logic              rst,
    input  logic [8*64-1:0]   x,
    input  logic              mono,
    input  logic [8:0]        r,
    output logic [8*64-1:0]   y,
    input  logic [NLP*32-1:0] ea,
    input  logic [NLP*32-1:0] eb,
    output logic [NLP*32-1:0] ey,
    output logic [NUP-1:0]    mn,
    output logic [NUP-1:0]    ms,
    input  logic [PBP-1:0]    mq
);
    localparam int D   = 18;
    localparam int NN  = kara_pkg::NN;
    localparam int VW  = 41;
    localparam int MPR = 4;
    localparam int NMC = (NLP + MPR - 1) / MPR;
`include "pe_map.svh"
`define MSEL(S, POS, W, LV, C, DIN, QOUT) \
    if (PB > 0) begin \
        assign mn[(S)*64 +: (W)] = (DIN); \
        assign ms[(S)*64 +: (W)] = {(W){lsel[(C) % NMC][(LV)]}}; \
        if ((W) < 64) begin \
            assign mn[(S)*64 + (W) +: 64 - (W)] = '0; \
            assign ms[(S)*64 + (W) +: 64 - (W)] = '0; \
        end \
        assign QOUT = mq[(POS) +: (W)]; \
    end else begin \
        always_ff @(posedge clk) QOUT <= (DIN); \
    end
`define MREG(V, W, LV, C, DIN, QOUT) `MSEL(V, gpos(V), W, LV, C, DIN, QOUT)
`define MHEAD(CI, W, LV, C, DIN, QOUT) `MSEL(NV + (CI), cpos(CI, 0), W, LV, C, DIN, QOUT)
`define MPK(LB, OFF, W, LV, C, DIN, QOUT) \
    if (PB > 0) begin : LB \
        for (genvar pj = 0; pj < (W); pj++) begin : g_b \
            assign mn[(V_PK + ((OFF) + pj) / 64) * 64 + ((OFF) + pj) % 64] = DIN[pj]; \
            assign ms[(V_PK + ((OFF) + pj) / 64) * 64 + ((OFF) + pj) % 64] = lsel[(C) % NMC][(LV)]; \
            assign QOUT[pj] = mq[gpos(V_PK + ((OFF) + pj) / 64) + ((OFF) + pj) % 64]; \
        end \
    end else begin : LB \
        always_ff @(posedge clk) QOUT <= DIN; \
    end
`define MCLN(K, W, DIN, QOUT) \
    assign mn[(CL0 + (K))*64 +: (W)] = (DIN); \
    assign ms[(CL0 + (K))*64 +: 64] = '0; \
    if ((W) < 64) begin \
        assign mn[(CL0 + (K))*64 + (W) +: 64 - (W)] = '0; \
    end \
    assign QOUT = mq[clpos(K, CP) +: (W)];
`define MFOL(CI, K, W, DIN, QOUT) \
    if (PB > 0) begin \
        assign QOUT = mq[cpos(CI, K) +: (W)]; \
    end else begin \
        always_ff @(posedge clk) QOUT <= (DIN); \
    end
    logic [D:1] mpc [0:NMC-1];
    logic [D*9-1:0] rr;
    logic [NMC-1:0] monoc;
`ifdef KS45
    generate for (genvar c = 0; c < NMC; c++) begin : g_mc
        BUF_X1 u_m (.A(mono), .Z(monoc[c]));
    end endgenerate
`else
    assign monoc = {NMC{mono}};
`endif
    always_ff @(posedge clk) begin
        for (int c = 0; c < NMC; c++) mpc[c] <= rst ? '0 : {mpc[c][D-1:1], monoc[c]};
    end
    logic [D:1] lsel [0:NMC-1];
    generate
        for (genvar c = 0; c < NMC; c++) begin : g_lsel
            assign lsel[c] = {mpc[c][D-1:1], monoc[c]};
        end
        if (PB == 0) begin : g_nopb
            assign mn = '0;
            assign ms = '0;
        end else begin : g_pk0
            for (genvar u = NHB + 9 * RRN; u < NPK * 64; u++) begin : g_u
                assign mn[V_PK * 64 + u] = 1'b0;
                assign ms[V_PK * 64 + u] = 1'b0;
            end
        end
        for (genvar k = 1; k <= D; k++) begin : g_rr
            logic [8:0] rd, rq;
            if (k == 1) begin : g_in
                assign rd = r;
            end else begin : g_dl
                assign rd = rr[(k-2)*9 +: 9];
            end
            if (k <= RRN) begin : g_p
                `MPK(g_f, NHB + 9 * (k - 1), 9, k, k, rd, rq)
            end else begin : g_r
                always_ff @(posedge clk) rq <= rd;
            end
            assign rr[(k-1)*9 +: 9] = rq;
        end
    endgenerate
    logic [16*31-1:0] xe;
    generate
        for (genvar k = 0; k < 8; k++) begin : g_unpack
            assign xe[(2*k)*31 +: 31]     = x[k*64 +: 31];
            assign xe[(2*k + 1)*31 +: 31] = x[k*64 + 32 +: 31];
        end
    endgenerate
    logic [16*31-1:0] xb1, xb2, xb3;
    logic             byp;
    assign byp = (r == 9'd0);
    generate
        for (genvar i = 0; i < 8; i++) begin : g_bar
            logic [31:0] c, b;
            alu_canon #(.W(32)) u_canon (.t(xe[i*31 +: 31]), .y(c));
            alu_bar31 u_bar (.x(c), .y(b));
            `MHEAD(C_XB + i, 31, 1, i, byp ? xe[i*31 +: 31] : b[30:0], xb1[i*31 +: 31])
        end
        for (genvar i = 8; i < 16; i++) begin : g_nobar
            `MHEAD(C_XB + i, 31, 1, i, xe[i*31 +: 31], xb1[i*31 +: 31])
        end
        for (genvar i = 0; i < 16; i++) begin : g_xb23
            `MFOL(C_XB + i, 1, 31, xb1[i*31 +: 31], xb2[i*31 +: 31])
            `MFOL(C_XB + i, 2, 31, xb2[i*31 +: 31], xb3[i*31 +: 31])
        end
    endgenerate
    logic [16*31-1:0] br;
    logic             en2;
    assign en2 = (rr[0 +: 9] != 9'd0);
    generate
        if (1) begin : g_br0
            `MREG(V_BR, 31, 4, 0, xb3[0 +: 31], br[0 +: 31])
        end
        for (genvar i = 1; i < 16; i++) begin : g_brick
            logic [61:0] sq;
            logic [30:0] cs, cc, t;
            if (PB > 0) begin : g_sqx
                logic [61:0]  sqd, sqq;
                logic [232:0] s1d, s1q;
                logic [223:0] s1c, s1cq;
                logic         env;
                logic [30:0]  xg;
                assign env = en2 && lsel[i % NMC][2];
                assign xg  = xb1[(i-1)*31 +: 31] & {31{env}};
                alu_mul31_en_p2 #(.EXT(1)) u_sq (.clk(clk), .en(env), .a(xg), .b(xg), .y(sq), .yd(sqd), .yq(sqq),
                    .s1d(s1d), .s1q(s1q));
                assign s1c = {s1d[232:231], s1d[229:228], s1d[226:225], s1d[222:212], s1d[210:200], s1d[198:11], s1d[10:8],
                              s1d[6:5], s1d[3:2], s1d[0]};
                assign s1q = {s1cq[223:222], s1cq[222:221], s1cq[220], s1cq[221], s1cq[219:218], s1cq[218], s1cq[219],
                              s1cq[217:207], 1'b0, s1cq[206:196], 1'b0, s1cq[195:5], s1cq[7], s1cq[4:3], s1cq[4], s1cq[2:1],
                              s1cq[1:0]};
                `MCLN(sq_clean(i, -1), 62, sqd, sqq)
                for (genvar j = 0; j < 4; j++) begin : g_s1
                    localparam int SW = (j < 3) ? 64 : 224 - 3 * 64;
                    if (sq_clean(i, j) >= 0) begin : g_c
                        `MCLN(sq_clean(i, j), SW, s1c[j*64 +: SW], s1cq[j*64 +: SW])
                    end else begin : g_g
                        `MREG(V_S4 + i - 13, SW, 2, i, s1c[j*64 +: SW], s1cq[j*64 +: SW])
                    end
                end
            end else begin : g_sq
                alu_mul31_en_p2 u_sq (.clk(clk), .en(en2), .a(xb1[(i-1)*31 +: 31]), .b(xb1[(i-1)*31 +: 31]), .y(sq));
            end
            alu_csa31 u_c (.x(xb3[i*31 +: 31]), .y(sq[30:0]), .z(sq[61:31]), .s(cs), .cr(cc));
            alu_addf #(.H(31)) u_f (.a({1'b0, cs}), .b({1'b0, cc}), .t(t));
            `MREG(V_BR + i, 31, 4, i, t, br[i*31 +: 31])
        end
    endgenerate
    logic [16*31-1:0] bn;
    assign bn = ~br;
    wire [NN*VW-1:0] v, vd1, vd2, vd3;
    wire [41*31-1:0] redv;
    generate
        if (NL == 0) begin : g_noey
            assign ey = '0;
        end
        for (genvar m = 0; m < 41; m++) begin : g_mul
            localparam logic [25:0] MT = kara_pkg::MUL_TAB[m*26 +: 26];
            localparam int IN = MT[25:16];
            localparam int WI = MT[10:5];
            localparam int LVIN = int'(kara_pkg::NODE_TAB[IN*50 + 42 +: 5]);
            logic [30:0] t2, rq;
            logic [VW-1:0] w;
            assign w  = v[IN*VW +: VW];
            alu_addf #(.H(31)) u_r (.a({1'b0, w[30:0]}), .b({{(63 - WI){1'b0}}, w[WI-1:31]}), .t(t2));
            if (PB > 0 && rq_word(m) >= 0) begin : g_ow
                localparam int OW  = rq_word(m);
                localparam int ROT = int'(kara_pkg::OPW_TAB[OW*12 +: 5]);
                logic [30:0] wd, wq;
                if (ROT == 0) begin : g_r0
                    assign wd = t2;
                    assign rq = wq;
                end else begin : g_rk
                    assign wd = {t2[30-ROT:0], t2[30:31-ROT]};
                    assign rq = {wq[ROT-1:0], wq[30:ROT]};
                end
                assign mn[(OP0 + OW / 2)*64 + (OW % 2)*32 +: 32] = {1'b0, wd};
                assign ms[(OP0 + OW / 2)*64 + (OW % 2)*32 +: 32] = {32{lsel[m % NMC][LVIN + 1]}};
                assign wq = mq[opos(OW) +: 31];
                assign mn[(V_RQ + m)*64 +: 64] = '0;
                assign ms[(V_RQ + m)*64 +: 64] = '0;
            end else begin : g_gs
                `MREG(V_RQ + m, 31, LVIN + 1, m, t2, rq)
            end
            assign redv[m*31 +: 31] = rq;
        end
        if (PB > 0) begin : g_owz
            for (genvar ow = 0; ow < 72; ow++) begin : g_w
                if (!kara_pkg::OPW_TAB[ow*12 + 11]) begin : g_z
                    assign mn[(OP0 + ow / 2)*64 + (ow % 2)*32 +: 32] = '0;
                    assign ms[(OP0 + ow / 2)*64 + (ow % 2)*32 +: 32] = '0;
                end
            end
        end
        for (genvar id = 0; id < NN; id++) begin : g_node
            localparam logic [49:0] T  = kara_pkg::NODE_TAB[id*50 +: 50];
            localparam int KD = T[49:47];
            localparam int LV = T[46:42];
            localparam int W  = T[41:36];
            localparam int A  = T[35:26];
            localparam bit NA = T[25];
            localparam int B  = T[24:15];
            localparam bit NB = T[14];
            localparam logic [10:0] LT = kara_pkg::LEND_TAB[id*11 +: 11];
            localparam int LD = LT[8:0];
            localparam bit MTA = LT[9];
            localparam bit MTB = LT[10];
            localparam int LIFE = T[4:0];
            if (LV == 0) begin : g_absent
                assign v[id*VW +: VW] = '0;
            end else if (KD == 5) begin : g_k
                assign v[id*VW +: VW] = '0;
            end else if (KD == 2) begin : g_leaf
                logic [30:0] rv, lf;
                assign rv = redv[A*31 +: 31];
                if (B == 0) begin : g_r0
                    assign lf = rv;
                end else begin : g_rk
                    assign lf = {rv[30-B:0], rv[30:31-B]};
                end
                assign v[id*VW +: VW] = {10'd0, NA ? ~lf : lf};
                if (LIFE >= 1) begin : g_d1
                    localparam int CI = C_LF + R_LF[id*10 +: 10];
                    logic [30:0] q1, q2, q3;
                    `MHEAD(CI, 31, LV + 1, id, NA ? ~lf : lf, q1)
                    `MFOL(CI, 1, 31, q1, q2)
                    `MFOL(CI, 2, 31, q2, q3)
                    assign vd1[id*VW +: VW] = {10'd0, q1};
                    assign vd2[id*VW +: VW] = {10'd0, q2};
                    assign vd3[id*VW +: VW] = {10'd0, q3};
                end
            end else begin : g_add
                localparam logic [49:0] TA = kara_pkg::NODE_TAB[A*50 +: 50];
                localparam logic [49:0] TB = kara_pkg::NODE_TAB[B*50 +: 50];
                localparam int DA = (KD == 0) ? 0 : LV - int'(TA[46:42]) - 1;
                localparam int DB = (KD == 0) ? 0 : LV - int'(TB[46:42]) - 1;
                localparam int WA = (KD == 0) ? 31 : int'(TA[41:36]);
                localparam int WB = (KD == 0) ? 31 : int'(TB[41:36]);
                localparam int KA = (KD == 0) ? 0 : int'(TA[49:47]);
                logic [W-1:0]  a, b, s, q;
                logic [VW-1:0] ra, rb;
                logic [30:0]   kc, kcq;
                if (KD == 0) begin : g_bank
                    localparam int BK = A / 8;
                    localparam int BJ = A % 8;
                    assign a = {1'b0, (BK == 0 || BK == 1) ? br[BJ*31 +: 31] : bn[BJ*31 +: 31]};
                    assign b = {1'b0, (BK == 0 || BK == 2) ? br[(BJ + 8)*31 +: 31] : bn[(BJ + 8)*31 +: 31]};
                end else begin : g_ops
                    if (DA == 0) begin : g_ra0      assign ra = v[A*VW +: VW];
                    end else if (DA == 1) begin : g_ra1 assign ra = vd1[A*VW +: VW];
                    end else if (DA == 2) begin : g_ra2 assign ra = vd2[A*VW +: VW];
                    end else begin : g_ra3          assign ra = vd3[A*VW +: VW]; end
                    if (DB == 0) begin : g_rb0      assign rb = v[B*VW +: VW];
                    end else if (DB == 1) begin : g_rb1 assign rb = vd1[B*VW +: VW];
                    end else if (DB == 2) begin : g_rb2 assign rb = vd2[B*VW +: VW];
                    end else begin : g_rb3          assign rb = vd3[B*VW +: VW]; end
                    if (KA == 5) begin : g_ka
                        localparam int KI = int'(TA[35:26]);
                        always_comb begin
                            case (rr[(LV-3)*9 +: 9])
                                9'd1: kc = kara_pkg::KC_TAB[(1*16 + KI)*31 +: 31];
                                9'd2: kc = kara_pkg::KC_TAB[(2*16 + KI)*31 +: 31];
                                9'd3: kc = kara_pkg::KC_TAB[(3*16 + KI)*31 +: 31];
                                9'd4: kc = kara_pkg::KC_TAB[(4*16 + KI)*31 +: 31];
                                9'd5: kc = kara_pkg::KC_TAB[(5*16 + KI)*31 +: 31];
                                default: kc = kara_pkg::KC_TAB[KI*31 +: 31];
                            endcase
                        end
                        `MREG(V_KC + KI, 31, LV - 1, id, kc, kcq)
                        assign a = {{(W - 31){1'b0}}, kcq};
                    end else if (NA) begin : g_na
                        assign a = {{(W - WA){1'b0}}, ~ra[WA-1:0]};
                    end else begin : g_pa
                        assign a = {{(W - WA){1'b0}}, ra[WA-1:0]};
                    end
                    if (NB) begin : g_nb
                        assign b = {{(W - WB){1'b0}}, ~rb[WB-1:0]};
                    end else begin : g_pb
                        assign b = {{(W - WB){1'b0}}, rb[WB-1:0]};
                    end
                end
                if (LD < NL) begin : g_lend
                    localparam int KB  = (KD == 0) ? 0 : int'(TB[49:47]);
                    localparam bit AEB = (KA != 2) && (DA == 0);
                    localparam bit BEA = (KB == 2) || (DB == 2);
                    localparam bit SWP = (MTA && AEB) || (MTB && BEA);
                    localparam bit MXA = (PB > 0) && (SWP ? MTB : MTA);
                    localparam bit MXB = (PB > 0) && (SWP ? MTA : MTB);
                    logic [W-1:0] la, lb;
                    assign la = {{(W - 32){1'b0}}, ea[LD*32 +: 32]};
                    assign lb = {{(W - 32){1'b0}}, eb[LD*32 +: 32]};
                    alu_lend #(.W(W), .MA(MXA), .MB(MXB)) u_add (.ext(!mpc[LD / MPR][LV - 1]), .ea(la), .eb(lb),
                        .a(SWP ? b : a), .b(SWP ? a : b), .y(s));
                    assign ey[LD*32 +: 32] = s[31:0];
                end else begin : g_priv
                    alu_addp #(.W(W)) u_add (.a(a), .b(b), .y(s));
                end
                if (PB > 0 && LD < NL) begin : g_twin
                    assign q[31:0] = mq[twin_pos(LD, CP) +: 32];
                    if (W > 32) begin : g_hi
                        logic [W-33:0] sh, qh;
                        assign sh = s[W-1:32];
                        `MPK(g_p, R_HI[id*12 +: 12], W - 32, LV, id, sh, qh)
                        assign q[W-1:32] = qh;
                    end
                end else if (LIFE >= 1) begin : g_qc
                    `MHEAD(R_PA[id*10 +: 10], W, LV, id, s, q)
                end else begin : g_q
                    `MREG(R_PN[id*10 +: 10], W, LV, id, s, q)
                end
                assign v[id*VW +: VW] = {{(VW - W){1'b0}}, q};
                if (LIFE >= 1) begin : g_d1
                    logic [W-1:0] q1, q2, q3;
                    if (LD < NL) begin : g_ld
                        if (PB > 0 && lfree(LD, 1)) begin : g_f1
                            assign q1[31:0] = mq[ldpos(LD, CP, 1) +: 32];
                            if (W > 32) begin : g_hi
                                logic [W-33:0] dh1, qh1;
                                assign dh1 = q[W-1:32];
                                `MPK(g_p, R_HI[id*12 +: 12] + (W - 32), W - 32, LV + 1, id, dh1, qh1)
                                assign q1[W-1:32] = qh1;
                            end
                        end else begin : g_s1
                            `MREG(V_LD1 + R_LD1[id*10 +: 10], W, LV + 1, id, q, q1)
                        end
                        if (LIFE >= 2) begin : g_2
                            if (PB > 0 && lfree(LD, 2)) begin : g_f2
                                assign q2[31:0] = mq[ldpos(LD, CP, 2) +: 32];
                                if (W > 32) begin : g_hi
                                    logic [W-33:0] dh2, qh2;
                                    assign dh2 = q1[W-1:32];
                                    `MPK(g_p, R_HI[id*12 +: 12] + 2 * (W - 32), W - 32, LV + 2, id, dh2, qh2)
                                    assign q2[W-1:32] = qh2;
                                end
                            end else begin : g_s2
                                `MREG(V_LD2 + R_LD2[id*10 +: 10], W, LV + 2, id, q1, q2)
                            end
                        end
                        if (LIFE >= 3) begin : g_3
                            `MREG(V_LD3 + R_LD3[id*10 +: 10], W, LV + 3, id, q2, q3)
                        end
                    end else begin : g_pd
                        `MFOL(R_PA[id*10 +: 10], 1, W, q, q1)
                        if (LIFE >= 2) begin : g_2
                            `MFOL(R_PA[id*10 +: 10], 2, W, q1, q2)
                        end
                        if (LIFE >= 3) begin : g_3
                            `MFOL(R_PA[id*10 +: 10], 3, W, q2, q3)
                        end
                    end
                    assign vd1[id*VW +: VW] = {{(VW - W){1'b0}}, q1};
                    if (LIFE >= 2) begin : g_v2
                        assign vd2[id*VW +: VW] = {{(VW - W){1'b0}}, q2};
                    end
                    if (LIFE >= 3) begin : g_v3
                        assign vd3[id*VW +: VW] = {{(VW - W){1'b0}}, q3};
                    end
                end
            end
        end
        for (genvar i = 0; i < 16; i++) begin : g_out
            localparam logic [20:0] OT = kara_pkg::OUT_TAB[i*21 +: 21];
            localparam int OID = OT[20:11];
            localparam int OL  = OT[10:6];
            localparam int OW  = OT[5:0];
            localparam int ND  = D - (OL + 1);
            logic [VW-1:0] ov;
            logic [30:0]   t;
            logic [30:0]   oq [0:ND];
            assign ov = v[OID*VW +: VW];
            alu_addf #(.H(OW - 31)) u_f (.a({1'b0, ov[30:0]}), .b({{(63 - OW){1'b0}}, ov[OW-1:31]}), .t(t));
            `MREG(V_OUT + i, 31, OL + 1, i, t, oq[0])
            for (genvar d = 1; d <= ND; d++) begin : g_dly
                always_ff @(posedge clk) oq[d] <= oq[d - 1];
            end
            assign y[(i / 2)*64 + (i % 2)*32 +: 32] = {1'b0, oq[ND]};
        end
    endgenerate
`undef MSEL
`undef MREG
`undef MHEAD
`undef MFOL
`undef MPK
`undef MCLN
endmodule
