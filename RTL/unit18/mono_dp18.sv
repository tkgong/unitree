// mono_dp18.sv - one Monolith-31 datapath (width 16): one traversal of the permutation as an 18-level pipeline, II = 1,
// the same interface and latency as the HLS unit's datapath (dse/TOP/bz3s): a state (8 lanes = 16 elements, lane k holds
// elements 2k (low word) and 2k+1) enters with mono = 1 and the traversal index r, and leaves on y 18 cycles later.
// The program (compile_tree.py) re-issues a state 7 times (r = 0..6): r = 0 is the Concrete-only pass the permutation
// starts with, r = 1..6 the rounds (Bars, Bricks, Concrete, round constant RC[r-1] for r <= 5).
//   L1 canon + Bars (r >= 1)        L2-L3 squares x_{i-1}^2 (two-stage multipliers, en = 0 on r = 0)
//   L4 Bricks b_i = x_i + lo31 + hi31 of the square, folded to <= p
//   L5-L18 the Concrete as the Plonky3 Karatsuba conv16 (kara_pkg: bank at L5, pre-adds, 41 reductions + CSD trees,
//          post-adds), output folds; one adder per level, every value registered at its level.
// NL > 0: the adders with lend index < NL (kara_pkg NODE_TAB, 32-bit adders first) are alu_lend: while no Monolith
// state is at their level they add ea + eb for the ARX blocks (ey, the same cycle). NL = 0: all adders private (the
// natural Monolith unit).
module mono_dp18 #(
    parameter int NL  = 216,
    parameter int NLP = (NL > 0) ? NL : 1
) (
    input  logic              clk,
    input  logic              rst,
    input  logic [8*64-1:0]   x,
    input  logic              mono,
    input  logic [8:0]        r,
    output logic [8*64-1:0]   y,
    input  logic [NLP*32-1:0] ea,
    input  logic [NLP*32-1:0] eb,
    output logic [NLP*32-1:0] ey
);
    localparam int D  = 18;
    localparam int NN = kara_pkg::NN;
    localparam int VW = 41;                                  // node value slot (max node width 40)
    // ---- mono / r travel with the state ----
    logic [D:1] mp;
    logic [8:0] rr [1:D];
    always_ff @(posedge clk) begin
        if (rst) mp <= '0;
        else mp <= {mp[D-1:1], mono};
        rr[1] <= r;
        for (int k = 2; k <= D; k++) rr[k] <= rr[k - 1];
    end
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
            always_ff @(posedge clk) xb1[i*31 +: 31] <= byp ? xe[i*31 +: 31] : b[30:0];
        end
        for (genvar i = 8; i < 16; i++) begin : g_nobar
            always_ff @(posedge clk) xb1[i*31 +: 31] <= xe[i*31 +: 31];
        end
    endgenerate
    always_ff @(posedge clk) begin xb2 <= xb1; xb3 <= xb2; end
    // ---- L2-L3: squares (en = 0 on r = 0: 0)    L4: Bricks b_i = x_i + x_{i-1}^2 folded to <= p ----
    logic [16*31-1:0] br;
    logic             en2;
    assign en2 = (rr[1] != 9'd0);
    always_ff @(posedge clk) br[0 +: 31] <= xb3[0 +: 31];
    generate
        for (genvar i = 1; i < 16; i++) begin : g_brick
            logic [61:0] sq;
            logic [32:0] s;
            logic [31:0] f1;
            logic [30:0] t;
            alu_mul31_en_p2 u_sq (.clk(clk), .en(en2), .a(xb1[(i-1)*31 +: 31]), .b(xb1[(i-1)*31 +: 31]), .y(sq));
            assign s  = {2'b00, xb3[i*31 +: 31]} + {2'b00, sq[30:0]} + {2'b00, sq[61:31]};   // <= 3p
            assign f1 = {1'b0, s[30:0]} + {30'd0, s[32:31]};                                   // <= p + 3
            alu_fold31 u_f (.r(f1), .t(t));
            always_ff @(posedge clk) br[i*31 +: 31] <= t;
        end
    endgenerate
    logic [16*31-1:0] bn;
    assign bn = ~br;                                         // p - b (b <= p)
    // ---- L5-L18: the Karatsuba network ----
    // v: every node's value at its own level; vd[d]: the value d further stages later (d <= life)
    wire [NN*VW-1:0] v, vd1, vd2, vd3;
    wire [41*31-1:0] redv;                                   // the 41 reduced mult inputs (at the mult's red level)
    function automatic logic [VW-1:0] rd(input logic [NN*VW-1:0] v0, input logic [NN*VW-1:0] d1,
                                        input logic [NN*VW-1:0] d2, input logic [NN*VW-1:0] d3, input int id, input int d);
        case (d)
            0: rd = v0[id*VW +: VW];
            1: rd = d1[id*VW +: VW];
            2: rd = d2[id*VW +: VW];
            default: rd = d3[id*VW +: VW];
        endcase
    endfunction
    generate
        if (NL == 0) begin : g_noey
            assign ey = '0;
        end
        // ---- the 41 reductions ----
        for (genvar m = 0; m < 41; m++) begin : g_mul
            localparam logic [25:0] MT = kara_pkg::MUL_TAB[m*26 +: 26];
            localparam int IN = MT[25:16];
            localparam int WI = MT[10:5];
            logic [31:0] t1;
            logic [30:0] t2, rq;
            logic [VW-1:0] w;
            assign w  = v[IN*VW +: VW];                      // the input node is registered at the level before
            alu_addp #(.W(32)) u_r1 (.a({1'b0, w[30:0]}), .b({{(63 - WI){1'b0}}, w[WI-1:31]}), .y(t1));
            alu_fold31 u_r2 (.r(t1), .t(t2));
            always_ff @(posedge clk) rq <= t2;
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
                    logic [30:0] q1, q2, q3;
                    always_ff @(posedge clk) begin q1 <= NA ? ~lf : lf; q2 <= q1; q3 <= q2; end
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
                logic [30:0]   kc;
                if (KD == 0) begin : g_bank                  // bank entry A: kind A / 8, j = A % 8
                    localparam int BK = A / 8;
                    localparam int BJ = A % 8;
                    assign a = {1'b0, (BK == 0 || BK == 1) ? br[BJ*31 +: 31] : bn[BJ*31 +: 31]};
                    assign b = {1'b0, (BK == 0 || BK == 2) ? br[(BJ + 8)*31 +: 31] : bn[(BJ + 8)*31 +: 31]};
                end else begin : g_ops
                    assign ra = rd(v, vd1, vd2, vd3, A, DA);
                    assign rb = rd(v, vd1, vd2, vd3, B, DB);
                    if (KA == 5) begin : g_ka                // operand A is the output constant K_i (i = its A field)
                        localparam int KI = int'(TA[35:26]);
                        always_comb begin
                            case (rr[LV - 1])
                                9'd1: kc = kara_pkg::KC_TAB[(1*16 + KI)*31 +: 31];
                                9'd2: kc = kara_pkg::KC_TAB[(2*16 + KI)*31 +: 31];
                                9'd3: kc = kara_pkg::KC_TAB[(3*16 + KI)*31 +: 31];
                                9'd4: kc = kara_pkg::KC_TAB[(4*16 + KI)*31 +: 31];
                                9'd5: kc = kara_pkg::KC_TAB[(5*16 + KI)*31 +: 31];
                                default: kc = kara_pkg::KC_TAB[KI*31 +: 31];
                            endcase
                        end
                        assign a = {{(W - 31){1'b0}}, kc};
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
                    alu_lend #(.W(W)) u_add (.ext(!mp[LV - 1]), .ea(la), .eb(lb), .a(a), .b(b), .y(s));
                    assign ey[LD*32 +: 32] = s[31:0];
                end else begin : g_priv
                    alu_addp #(.W(W)) u_add (.a(a), .b(b), .y(s));
                end
                always_ff @(posedge clk) q <= s;
                assign v[id*VW +: VW] = {{(VW - W){1'b0}}, q};
                if (LIFE >= 1) begin : g_d1
                    logic [W-1:0] q1;
                    always_ff @(posedge clk) q1 <= q;
                    assign vd1[id*VW +: VW] = {{(VW - W){1'b0}}, q1};
                    if (LIFE >= 2) begin : g_d2
                        logic [W-1:0] q2;
                        always_ff @(posedge clk) q2 <= q1;
                        assign vd2[id*VW +: VW] = {{(VW - W){1'b0}}, q2};
                        if (LIFE >= 3) begin : g_d3
                            logic [W-1:0] q3;
                            always_ff @(posedge clk) q3 <= q2;
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
            logic [31:0]   f;
            logic [30:0]   t;
            logic [30:0]   oq [0:ND];
            assign ov = v[OID*VW +: VW];
            alu_addp #(.W(32)) u_f1 (.a({1'b0, ov[30:0]}), .b({{(63 - OW){1'b0}}, ov[OW-1:31]}), .y(f));
            alu_fold #(.H(OW - 31)) u_f2 (.r(f), .t(t));
            always_ff @(posedge clk) oq[0] <= t;
            for (genvar d = 1; d <= ND; d++) begin : g_dly
                always_ff @(posedge clk) oq[d] <= oq[d - 1];
            end
            assign y[(i / 2)*64 + (i % 2)*32 +: 32] = {1'b0, oq[ND]};
        end
    endgenerate
endmodule
