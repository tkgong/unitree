// mono_dp18.sv - one Monolith-31 datapath (width 16): one traversal of the permutation as an 18-level pipeline, II = 1,
// the same interface and latency as the HLS unit's datapath (dse/TOP/bz3s): a state (8 lanes = 16 elements, lane k holds
// elements 2k (low word) and 2k+1) enters with mono = 1 and the traversal index r, and leaves on y 18 cycles later.
// The program (compile_tree.py) re-issues a state 7 times (r = 0..6): r = 0 is the Concrete-only pass the permutation
// starts with, r = 1..6 the rounds (Bars, Bricks, Concrete, round constant RC[r-1] for r <= 5).
//   L1 canon + Bars (r >= 1)        L2-L3 squares x_{i-1}^2 (two-stage multipliers, en = 0 on r = 0)
//   L4 Bricks b_i = x_i + lo31 + hi31 of the square (alu_csa31 + alu_addf: one carry chain), folded to <= p
//   L5-L18 the Concrete as the Plonky3 Karatsuba conv16 (kara_pkg: bank at L5, pre-adds, 41 reductions + CSD trees,
//          post-adds), output folds; one adder per level, every value registered at its level.
// NL > 0: the adders with lend index < NL (kara_pkg NODE_TAB, 32-bit adders first) are alu_lend: while no Monolith
// state is at their level they add ea + eb for the ARX blocks (ey, the same cycle). NL = 0: all adders private (the
// natural Monolith unit). Timing: every level is one carry chain (the reductions and output folds are alu_addf, the
// fused add + fold), the K constants are selected a level early and registered, the issue bit is replicated per MPR
// lent adders (the fanout of the lend select).
// PB > 0: the datapath has no registers of its own (the shared unit): every value register lives in the PE's register
// vector (PB bits, the ARX block groups' level registers) at a fixed slot. The datapath drives mn (the value to register)
// and ms (1 where a Monolith state enters that register's level this cycle: the state bit travelling with it) and reads
// the registers on mq; the PE registers ms ? mn : the ARX value. Slots (VW = 41-bit node slots, ranks in node order):
//   node registers id*VW | first delays NN*VW + id*VW | reductions RQ0 + m*31 | xb1, xb2, xb3, br XB0 + (4 x 16 x 31)
//   K constants KC0 + i*31 | outputs OUT0 + i*31 | second delays D2_0 + rank*VW | third delays D3_0 + rank*VW
// The issue bit / r copies (mpc, rr) and the squarers' internal stage stay private.
module mono_dp18 #(
    parameter int NL  = 216,
    parameter int NLP = (NL > 0) ? NL : 1,
    parameter int PB  = 0,
    parameter int PBP = (PB > 0) ? PB : 1
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
    output logic [PBP-1:0]    mn,
    output logic [PBP-1:0]    ms,
    input  logic [PBP-1:0]    mq
);
    localparam int D   = 18;
    localparam int NN  = kara_pkg::NN;
    localparam int VW  = 41;                                 // node value slot (max node width 40)
    localparam int MPR = 4;                                  // lent adders per copy of the issue bit
    localparam int NMC = (NLP + MPR - 1) / MPR;
    // ---- the register slots (PB > 0) ----
    // node id has a k-th delay stage register (a leaf with a life has all three); Verilog-2005 style for Yosys
    function automatic integer has_dly(input integer id, input integer k);
        reg [49:0] t;
        begin
            t = kara_pkg::NODE_TAB[id*50 +: 50];
            if (t[46:42] == 0 || t[49:47] == 5) has_dly = 0;
            else if (t[49:47] == 2) has_dly = (t[4:0] >= 1);
            else has_dly = (t[4:0] >= k);
        end
    endfunction
    function automatic integer rank_dly(input integer id, input integer k);  // delay-k registers of the nodes before id
        integer j;
        reg [49:0] t;
        begin
            rank_dly = 0;
            for (j = 0; j < id; j = j + 1) begin
                t = kara_pkg::NODE_TAB[j*50 +: 50];
                if (t[46:42] != 0 && t[49:47] != 5 && (t[49:47] == 2 ? t[4:0] >= 1 : t[4:0] >= k)) rank_dly = rank_dly + 1;
            end
        end
    endfunction
    localparam int D1_0 = NN * VW;
    localparam int RQ0  = 2 * NN * VW;
    localparam int XB0  = RQ0 + 41 * 31;
    localparam int KC0  = XB0 + 4 * 16 * 31;
    localparam int OUT0 = KC0 + 16 * 31;
    localparam int D2_0 = OUT0 + 16 * 31;
    localparam int D3_0 = D2_0 + rank_dly(NN, 2) * VW;
    localparam int SEND = D3_0 + rank_dly(NN, 3) * VW;     // first slot not used
    // a register of W bits at level LV (written when a state enters LV), slot SL, issue-bit copy C
`define MREG(SL, W, LV, C, DIN, QOUT) \
    if (PB > 0) begin \
        assign mn[(SL) +: (W)] = (DIN); \
        assign ms[(SL) +: (W)] = {(W){lsel[(C) % NMC][(LV)]}}; \
        assign QOUT = mq[(SL) +: (W)]; \
    end else begin \
        always_ff @(posedge clk) QOUT <= (DIN); \
    end
    // the unused bits of a slot (zero: never selected)
`define MFILL(SL, W) \
    if (PB > 0 && (W) > 0) begin \
        assign mn[(SL) +: (W)] = '0; \
        assign ms[(SL) +: (W)] = '0; \
    end
    // ---- mono / r travel with the state (mpc: NMC copies of the issue bit, copy c serves lent adders c*MPR..) ----
    logic [D:1] mpc [0:NMC-1];
    logic [8:0] rr [1:D];
    logic [NMC-1:0] monoc;                                   // the issue bit per copy
`ifdef KS45                                               // timing flow: a buffer cell per copy keeps the copies structurally
    generate for (genvar c = 0; c < NMC; c++) begin : g_mc    // distinct, so that opt_merge cannot fold them back into one
        BUF_X1 u_m (.A(mono), .Z(monoc[c]));
    end endgenerate
`else
    assign monoc = {NMC{mono}};
`endif
    always_ff @(posedge clk) begin
        for (int c = 0; c < NMC; c++) mpc[c] <= rst ? '0 : {mpc[c][D-1:1], monoc[c]};
        rr[1] <= r;
        for (int k = 2; k <= D; k++) rr[k] <= rr[k - 1];
    end
    logic [D:1] lsel [0:NMC-1];                              // lsel[c][L]: a state enters level L this cycle
    generate
        for (genvar c = 0; c < NMC; c++) begin : g_lsel
            assign lsel[c] = {mpc[c][D-1:1], monoc[c]};
        end
        if (PB == 0) begin : g_nopb
            assign mn = '0;
            assign ms = '0;
        end else if (SEND < PB) begin : g_tail
            assign mn[PB-1:SEND] = '0;
            assign ms[PB-1:SEND] = '0;
        end
    endgenerate
    // ---- the 16 elements ----
    logic [16*31-1:0] xe;
    generate
        for (genvar k = 0; k < 8; k++) begin : g_unpack
            assign xe[(2*k)*31 +: 31]     = x[k*64 +: 31];
            assign xe[(2*k + 1)*31 +: 31] = x[k*64 + 32 +: 31];
        end
    endgenerate
    // ---- L1: canon + Bars on elements 0..7 (r = 0: unchanged) ----
    logic [16*31-1:0] xb1, xb2, xb3;
    logic             byp;
    assign byp = (r == 9'd0);
    generate
        for (genvar i = 0; i < 8; i++) begin : g_bar
            logic [31:0] c, b;
            alu_canon #(.W(32)) u_canon (.t(xe[i*31 +: 31]), .y(c));
            alu_bar31 u_bar (.x(c), .y(b));
            `MREG(XB0 + i*31, 31, 1, i, byp ? xe[i*31 +: 31] : b[30:0], xb1[i*31 +: 31])
        end
        for (genvar i = 8; i < 16; i++) begin : g_nobar
            `MREG(XB0 + i*31, 31, 1, i, xe[i*31 +: 31], xb1[i*31 +: 31])
        end
        for (genvar i = 0; i < 16; i++) begin : g_xb23
            `MREG(XB0 + 496 + i*31, 31, 2, i, xb1[i*31 +: 31], xb2[i*31 +: 31])
            `MREG(XB0 + 992 + i*31, 31, 3, i, xb2[i*31 +: 31], xb3[i*31 +: 31])
        end
    endgenerate
    // ---- L2-L3: squares (en = 0 on r = 0: 0)    L4: Bricks b_i = x_i + x_{i-1}^2 folded to <= p ----
    logic [16*31-1:0] br;
    logic             en2;
    assign en2 = (rr[1] != 9'd0);
    generate
        if (1) begin : g_br0
            `MREG(XB0 + 1488, 31, 4, 0, xb3[0 +: 31], br[0 +: 31])
        end
        for (genvar i = 1; i < 16; i++) begin : g_brick
            logic [61:0] sq;
            logic [30:0] cs, cc, t;
            alu_mul31_en_p2 u_sq (.clk(clk), .en(en2), .a(xb1[(i-1)*31 +: 31]), .b(xb1[(i-1)*31 +: 31]), .y(sq));
            alu_csa31 u_c (.x(xb3[i*31 +: 31]), .y(sq[30:0]), .z(sq[61:31]), .s(cs), .cr(cc));   // cs + cc = b_i (mod p)
            alu_addf #(.H(31)) u_f (.a({1'b0, cs}), .b({1'b0, cc}), .t(t));                      // <= p
            `MREG(XB0 + 1488 + i*31, 31, 4, i, t, br[i*31 +: 31])
        end
    endgenerate
    logic [16*31-1:0] bn;
    assign bn = ~br;                                         // p - b (b <= p)
    // ---- L5-L18: the Karatsuba network ----
    // v: every node's value at its own level; vd[d]: the value d further stages later (d <= life)
    wire [NN*VW-1:0] v, vd1, vd2, vd3;
    wire [41*31-1:0] redv;                                   // the 41 reduced mult inputs (at the mult's red level)
    generate
        if (NL == 0) begin : g_noey
            assign ey = '0;
        end
        // ---- the 41 reductions ----
        for (genvar m = 0; m < 41; m++) begin : g_mul
            localparam logic [25:0] MT = kara_pkg::MUL_TAB[m*26 +: 26];
            localparam int IN = MT[25:16];
            localparam int WI = MT[10:5];
            localparam int LVIN = int'(kara_pkg::NODE_TAB[IN*50 + 42 +: 5]);
            logic [30:0] t2, rq;
            logic [VW-1:0] w;
            assign w  = v[IN*VW +: VW];                      // the input node is registered at the level before
            alu_addf #(.H(31)) u_r (.a({1'b0, w[30:0]}), .b({{(63 - WI){1'b0}}, w[WI-1:31]}), .t(t2));
            `MREG(RQ0 + m*31, 31, LVIN + 1, m, t2, rq)
            assign redv[m*31 +: 31] = rq;
        end
        // ---- the nodes ----
        for (genvar id = 0; id < NN; id++) begin : g_node
            localparam logic [49:0] T  = kara_pkg::NODE_TAB[id*50 +: 50];
            localparam int KD = T[49:47];
            localparam int LV = T[46:42];
            localparam int W  = T[41:36];
            localparam int A  = T[35:26];
            localparam bit NA = T[25];
            localparam int B  = T[24:15];
            localparam bit NB = T[14];
            localparam int LD = T[13:5];
            localparam int LIFE = T[4:0];
            if (LV == 0 || KD == 5 || KD == 2) begin : g_noq  // no node register: its slot is unused
                `MFILL(id*VW, VW)
            end
            if (!has_dly(id, 1)) begin : g_nod1
                `MFILL(D1_0 + id*VW, VW)
            end
            if (LV == 0) begin : g_absent
                assign v[id*VW +: VW] = '0;
            end else if (KD == 5) begin : g_k                 // constant: the consumer selects it by its own r
                assign v[id*VW +: VW] = '0;
            end else if (KD == 2) begin : g_leaf              // CSD leaf: rotation (complemented) of mult A's reduced input
                logic [30:0] rv, lf;
                assign rv = redv[A*31 +: 31];
                if (B == 0) begin : g_r0
                    assign lf = rv;
                end else begin : g_rk
                    assign lf = {rv[30-B:0], rv[30:31-B]};
                end
                assign v[id*VW +: VW] = {10'd0, NA ? ~lf : lf};
                if (LIFE >= 1) begin : g_d1                  // an odd leaf of a tree is summed a level later
                    localparam int R2 = rank_dly(id, 2);
                    localparam int R3 = rank_dly(id, 3);
                    logic [30:0] q1, q2, q3;
                    `MREG(D1_0 + id*VW, 31, LV + 1, id, NA ? ~lf : lf, q1)
                    `MFILL(D1_0 + id*VW + 31, VW - 31)
                    `MREG(D2_0 + R2*VW, 31, LV + 2, id, q1, q2)
                    `MFILL(D2_0 + R2*VW + 31, VW - 31)
                    `MREG(D3_0 + R3*VW, 31, LV + 3, id, q2, q3)
                    `MFILL(D3_0 + R3*VW + 31, VW - 31)
                    assign vd1[id*VW +: VW] = {10'd0, q1};
                    assign vd2[id*VW +: VW] = {10'd0, q2};
                    assign vd3[id*VW +: VW] = {10'd0, q3};
                end
            end else begin : g_add                           // bank / pre / tree / post adder, registered at level LV
                localparam logic [49:0] TA = kara_pkg::NODE_TAB[A*50 +: 50];   // operand node entries
                localparam logic [49:0] TB = kara_pkg::NODE_TAB[B*50 +: 50];
                localparam int DA = (KD == 0) ? 0 : LV - int'(TA[46:42]) - 1;
                localparam int DB = (KD == 0) ? 0 : LV - int'(TB[46:42]) - 1;
                localparam int WA = (KD == 0) ? 31 : int'(TA[41:36]);
                localparam int WB = (KD == 0) ? 31 : int'(TB[41:36]);
                localparam int KA = (KD == 0) ? 0 : int'(TA[49:47]);
                logic [W-1:0]  a, b, s, q;
                logic [VW-1:0] ra, rb;
                logic [30:0]   kc, kcq;
                if (KD == 0) begin : g_bank                  // bank entry A: kind A / 8, j = A % 8
                    localparam int BK = A / 8;
                    localparam int BJ = A % 8;
                    assign a = {1'b0, (BK == 0 || BK == 1) ? br[BJ*31 +: 31] : bn[BJ*31 +: 31]};
                    assign b = {1'b0, (BK == 0 || BK == 2) ? br[(BJ + 8)*31 +: 31] : bn[(BJ + 8)*31 +: 31]};
                end else begin : g_ops
                    // operand read: the node register itself (DA = 0) or its delay stage DA (bus vd1..vd3); a select at
                    // generate time (a function taking the 30 kbit buses as arguments made Yosys copy them per call)
                    if (DA == 0) begin : g_ra0      assign ra = v[A*VW +: VW];
                    end else if (DA == 1) begin : g_ra1 assign ra = vd1[A*VW +: VW];
                    end else if (DA == 2) begin : g_ra2 assign ra = vd2[A*VW +: VW];
                    end else begin : g_ra3          assign ra = vd3[A*VW +: VW]; end
                    if (DB == 0) begin : g_rb0      assign rb = v[B*VW +: VW];
                    end else if (DB == 1) begin : g_rb1 assign rb = vd1[B*VW +: VW];
                    end else if (DB == 2) begin : g_rb2 assign rb = vd2[B*VW +: VW];
                    end else begin : g_rb3          assign rb = vd3[B*VW +: VW]; end
                    if (KA == 5) begin : g_ka                // operand A is the output constant K_i (i = its A field):
                        localparam int KI = int'(TA[35:26]);  // selected by the state's r one level early, registered
                        always_comb begin
                            case (rr[LV - 2])
                                9'd1: kc = kara_pkg::KC_TAB[(1*16 + KI)*31 +: 31];
                                9'd2: kc = kara_pkg::KC_TAB[(2*16 + KI)*31 +: 31];
                                9'd3: kc = kara_pkg::KC_TAB[(3*16 + KI)*31 +: 31];
                                9'd4: kc = kara_pkg::KC_TAB[(4*16 + KI)*31 +: 31];
                                9'd5: kc = kara_pkg::KC_TAB[(5*16 + KI)*31 +: 31];
                                default: kc = kara_pkg::KC_TAB[KI*31 +: 31];
                            endcase
                        end
                        `MREG(KC0 + KI*31, 31, LV - 1, id, kc, kcq)
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
                    logic [W-1:0] la, lb;
                    assign la = {{(W - 32){1'b0}}, ea[LD*32 +: 32]};
                    assign lb = {{(W - 32){1'b0}}, eb[LD*32 +: 32]};
                    alu_lend #(.W(W)) u_add (.ext(!mpc[LD / MPR][LV - 1]), .ea(la), .eb(lb), .a(a), .b(b), .y(s));
                    assign ey[LD*32 +: 32] = s[31:0];
                end else begin : g_priv
                    alu_addp #(.W(W)) u_add (.a(a), .b(b), .y(s));
                end
                `MREG(id*VW, W, LV, id, s, q)
                `MFILL(id*VW + W, VW - W)
                assign v[id*VW +: VW] = {{(VW - W){1'b0}}, q};
                if (LIFE >= 1) begin : g_d1
                    logic [W-1:0] q1;
                    `MREG(D1_0 + id*VW, W, LV + 1, id, q, q1)
                    `MFILL(D1_0 + id*VW + W, VW - W)
                    assign vd1[id*VW +: VW] = {{(VW - W){1'b0}}, q1};
                    if (LIFE >= 2) begin : g_d2
                        localparam int R2 = rank_dly(id, 2);
                        logic [W-1:0] q2;
                        `MREG(D2_0 + R2*VW, W, LV + 2, id, q1, q2)
                        `MFILL(D2_0 + R2*VW + W, VW - W)
                        assign vd2[id*VW +: VW] = {{(VW - W){1'b0}}, q2};
                        if (LIFE >= 3) begin : g_d3
                            localparam int R3 = rank_dly(id, 3);
                            logic [W-1:0] q3;
                            `MREG(D3_0 + R3*VW, W, LV + 3, id, q2, q3)
                            `MFILL(D3_0 + R3*VW + W, VW - W)
                            assign vd3[id*VW +: VW] = {{(VW - W){1'b0}}, q3};
                        end
                    end
                end
            end
        end
        // ---- the 16 outputs: fold at the level after the root, delayed to L18 ----
        for (genvar i = 0; i < 16; i++) begin : g_out
            localparam logic [20:0] OT = kara_pkg::OUT_TAB[i*21 +: 21];
            localparam int OID = OT[20:11];
            localparam int OL  = OT[10:6];
            localparam int OW  = OT[5:0];
            localparam int ND  = D - (OL + 1);                 // delay stages after the fold register
            logic [VW-1:0] ov;
            logic [30:0]   t;
            logic [30:0]   oq [0:ND];
            assign ov = v[OID*VW +: VW];
            alu_addf #(.H(OW - 31)) u_f (.a({1'b0, ov[30:0]}), .b({{(63 - OW){1'b0}}, ov[OW-1:31]}), .t(t));
            `MREG(OUT0 + i*31, 31, OL + 1, i, t, oq[0])
            for (genvar d = 1; d <= ND; d++) begin : g_dly
                always_ff @(posedge clk) oq[d] <= oq[d - 1];
            end
            assign y[(i / 2)*64 + (i % 2)*32 +: 32] = {1'b0, oq[ND]};
        end
    endgenerate
`undef MREG
`undef MFILL
endmodule
