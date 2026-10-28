// mono_dp18.sv - one Monolith-31 datapath (width 16): one traversal of the permutation as an 18-level pipeline, II = 1,
// the same interface and latency as the HLS unit's datapath (dse/TOP/bz3s): a state (8 lanes = 16 elements, lane k holds
// elements 2k (low word) and 2k+1) enters with mono = 1 and the traversal index r, and leaves on y 18 cycles later.
// The program (compile_tree.py) re-issues a state 7 times (r = 0..6): r = 0 is the Concrete-only pass the permutation
// starts with, r = 1..6 the rounds (Bars, Bricks, Concrete, round constant RC[r-1] for r <= 5).
//   L1 canon + Bars (r >= 1)        L2-L3 squares x_{i-1}^2 (two-stage multipliers, en = 0 on r = 0)
//   L4 square mod p                 L5 Bricks b_i = x_i + x_{i-1}^2
//   L6-L9 the Concrete terms summed per CSD shift (the narrow trees)     L10-L14 the 17 shifted sums combined
//   L15 fold (lo31 + hi24)          L16 + RC, fold                       L17-L18 registers
// NL > 0: the first NL adders of level 6 (the narrow trees' first level, order output / shift / position) are alu_lend:
// while no Monolith state is at level 6 they add ea + eb for the ARX blocks (ey, the same cycle). NL = 0: all adders
// private (the natural Monolith unit).
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
    localparam int D = 18;
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
    logic [16*31-1:0] xb1, xb2, xb3, xb4;
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
    always_ff @(posedge clk) begin xb2 <= xb1; xb3 <= xb2; xb4 <= xb3; end
    // ---- L2-L3: squares (en = 0 on r = 0: 0)    L4: square mod p    L5: Bricks ----
    logic [16*31-1:0] br;
    logic             en2;
    assign en2 = (rr[1] != 9'd0);
    always_ff @(posedge clk) br[0 +: 31] <= xb4[0 +: 31];
    generate
        for (genvar i = 1; i < 16; i++) begin : g_brick
            logic [61:0] sq;
            logic [31:0] r1, r2;
            logic [30:0] t1c, t1, t2;
            alu_mul31_en_p2 u_sq (.clk(clk), .en(en2), .a(xb1[(i-1)*31 +: 31]), .b(xb1[(i-1)*31 +: 31]), .y(sq));
            alu_addp #(.W(32)) u_a1 (.a({1'b0, sq[30:0]}), .b({1'b0, sq[61:31]}), .y(r1));
            alu_fold31 u_f1 (.r(r1), .t(t1c));
            always_ff @(posedge clk) t1 <= t1c;
            alu_addp #(.W(32)) u_a2 (.a({1'b0, xb4[i*31 +: 31]}), .b({1'b0, t1}), .y(r2));
            alu_fold31 u_f2 (.r(r2), .t(t2));
            always_ff @(posedge clk) br[i*31 +: 31] <= t2;
        end
    endgenerate
    // ---- L6-L14: Concrete ----
    logic ext6;
    assign ext6 = !mp[5];                                    // no Monolith state at level 6: the lent adders serve the ARX blocks
    logic [16*31-1:0] tn;
    assign tn = ~br;                                         // p - b (b <= p)
    logic [16*31-1:0] yo;
    generate
        if (NL == 0) begin : g_noey
            assign ey = '0;
        end
        for (genvar i = 0; i < 16; i++) begin : g_out
            logic [csd_pkg::NSH*52-1:0] wt;
            for (genvar s = 0; s < csd_pkg::NSH; s++) begin : g_sh
                localparam int NT = csd_pkg::nterm(s);
                localparam int WN = 31 + csd_pkg::clog2i(NT);
                localparam int NLD = csd_pkg::nlend(NL, i, s);
                localparam int LO = csd_pkg::lend_off(i, s);
                logic [NT*31-1:0] tv;
                logic [WN-1:0]    ns;
                for (genvar k = 0; k < 16; k++) begin : g_term
                    if (csd_pkg::dig(k, s) == 2'd1) begin : g_pos
                        assign tv[csd_pkg::tidx(s, k)*31 +: 31] = br[((i + k) % 16)*31 +: 31];
                    end else if (csd_pkg::dig(k, s) == 2'd2) begin : g_neg
                        assign tv[csd_pkg::tidx(s, k)*31 +: 31] = tn[((i + k) % 16)*31 +: 31];
                    end
                end
                if (NLD > 0) begin : g_lend
                    add_tree #(.N(NT), .W0(31), .WMAX(64), .LAT(4), .NLD(NLD)) u_tree (.clk(clk), .x(tv), .y(ns), .ext(ext6),
                        .ea(ea[LO*32 +: NLD*32]), .eb(eb[LO*32 +: NLD*32]), .ey(ey[LO*32 +: NLD*32]));
                end else begin : g_priv
                    logic [31:0] ey_nc;
                    add_tree #(.N(NT), .W0(31), .WMAX(64), .LAT(4), .NLD(0)) u_tree (.clk(clk), .x(tv), .y(ns), .ext(1'b0),
                        .ea(32'd0), .eb(32'd0), .ey(ey_nc));
                end
                logic [51:0] nz;
                assign nz = ns;
                assign wt[s*52 +: 52] = nz << s;
            end
            logic [csd_pkg::WSUM-1:0] ysum;
            logic [31:0] ey_nc;
            add_tree #(.N(csd_pkg::NSH), .W0(52), .WMAX(csd_pkg::WSUM), .LAT(5), .NLD(0)) u_wide (.clk(clk), .x(wt), .y(ysum),
                .ext(1'b0), .ea(32'd0), .eb(32'd0), .ey(ey_nc));
            // ---- L15: fold      L16: + RC[r-1] (r = 1..5), fold ----
            logic [31:0] r1, r2;
            logic [30:0] t1c, t1, t2, rc;
            alu_addp #(.W(32)) u_a1 (.a({1'b0, ysum[30:0]}), .b({8'd0, ysum[csd_pkg::WSUM-1:31]}), .y(r1));
            alu_fold #(.H(csd_pkg::WSUM - 31)) u_f1 (.r(r1), .t(t1c));
            always_ff @(posedge clk) t1 <= t1c;
            always_comb begin
                case (rr[15])
                    9'd1: rc = csd_pkg::RC(0, i);
                    9'd2: rc = csd_pkg::RC(1, i);
                    9'd3: rc = csd_pkg::RC(2, i);
                    9'd4: rc = csd_pkg::RC(3, i);
                    9'd5: rc = csd_pkg::RC(4, i);
                    default: rc = 31'd0;
                endcase
            end
            alu_addp #(.W(32)) u_a2 (.a({1'b0, t1}), .b({1'b0, rc}), .y(r2));
            alu_fold31 u_f2 (.r(r2), .t(t2));
            always_ff @(posedge clk) yo[i*31 +: 31] <= t2;
        end
    endgenerate
    // ---- L17-L18 ----
    logic [16*31-1:0] y17, y18;
    always_ff @(posedge clk) begin y17 <= yo; y18 <= y17; end
    generate
        for (genvar k = 0; k < 8; k++) begin : g_pack
            assign y[k*64 +: 64] = {1'b0, y18[(2*k + 1)*31 +: 31], 1'b0, y18[(2*k)*31 +: 31]};
        end
    endgenerate
endmodule
