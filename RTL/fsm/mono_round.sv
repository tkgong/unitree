// mono_round.sv - one Monolith-31 round (width 16) as a combinational function of the state: Bars on x[0..7], Bricks,
// Concrete (the CSD adder tree, mono_pkg), round constant. Inputs x_i <= p (31 bits), outputs <= p. bypass = 1 skips Bars
// and Bricks (the Concrete-only pass the permutation starts with). The function is deep (multiplier + ~14 adders); the FSM
// in mono_core holds x for MC cycles per round (multicycle path), so the round needs no pipeline registers.
// Every adder of the Concrete tree is an alu_lend (LEND = 1): while ext = 1 the NTREE adders compute ea + eb for the ARX
// blocks of the shared PE (ey = the low 32 bits) instead of the tree.
module mono_round
#(
    parameter int LEND = 1
) (
    input  logic [16*31-1:0]    x,
    input  logic                bypass,
    input  logic [16*31-1:0]    rc,
    output logic [16*31-1:0]    y,
    input  logic                ext,
    input  logic [mono_pkg::NTREE*32-1:0] ea,
    input  logic [mono_pkg::NTREE*32-1:0] eb,
    output logic [mono_pkg::NTREE*32-1:0] ey
);
    // ---- Bars on elements 0..7 (canonical input: p -> 0), the rest unchanged ----
    logic [16*31-1:0] xb;
    generate
        for (genvar i = 0; i < 8; i++) begin : g_bar
            logic [31:0] c, b;
            alu_canon #(.W(32)) u_canon (.t(x[i*31 +: 31]), .y(c));
            alu_bar31 u_bar (.x(c), .y(b));
            assign xb[i*31 +: 31] = b[30:0];
        end
        for (genvar i = 8; i < 16; i++) begin : g_nobar
            assign xb[i*31 +: 31] = x[i*31 +: 31];
        end
    endgenerate
    // ---- Bricks: b_i = xb_i + xb_{i-1}^2 (mod p), i = 1..15 ----
    logic [16*31-1:0] br;
    assign br[0 +: 31] = xb[0 +: 31];
    generate
        for (genvar i = 1; i < 16; i++) begin : g_brick
            logic [61:0] sq;
            logic [31:0] lo, hi, r1, r2;
            logic [30:0] t1, t2;
            alu_mul31 u_sq (.a(xb[(i-1)*31 +: 31]), .b(xb[(i-1)*31 +: 31]), .y(sq));
            assign lo = {1'b0, sq[30:0]};
            assign hi = {1'b0, sq[61:31]};
            alu_addp #(.W(32)) u_a1 (.a(lo), .b(hi), .y(r1));          // sq mod p: lo31 + hi31 (<= 2^32 - 2)
            alu_fold31 u_f1 (.r(r1), .t(t1));                           // <= p
            alu_addp #(.W(32)) u_a2 (.a({1'b0, xb[i*31 +: 31]}), .b({1'b0, t1}), .y(r2));
            alu_fold31 u_f2 (.r(r2), .t(t2));                           // <= p
            assign br[i*31 +: 31] = t2;
        end
    endgenerate
    // ---- Concrete input: the Bricks output, or x itself on the bypass pass ----
    logic [16*31-1:0] t, tn;
    assign t  = bypass ? x : br;
    assign tn = ~t;                                                     // p - t_i (t_i <= p)
    // ---- Concrete: y_i = sum_k mono_pkg::ROW[k] t_{i+k}; per shift s the group sum N_{i,s} of the terms with a CSD digit at s ----
    logic [16*31-1:0] yc;
    generate
        for (genvar i = 0; i < 16; i++) begin : g_out
            logic [mono_pkg::NSH*52-1:0] wt;                                      // the 17 shifted group sums, 52 bits each
            for (genvar s = 0; s < mono_pkg::NSH; s++) begin : g_sh
                localparam int NT = mono_pkg::nterm(s);
                localparam int WN = 31 + mono_pkg::clog2i(NT);
                logic [NT*31-1:0] tv;
                logic [WN-1:0]    ns;
                for (genvar k = 0; k < 16; k++) begin : g_term
                    if (mono_pkg::dig(k, s) == 2'd1) begin : g_pos
                        assign tv[mono_pkg::tidx(s, k)*31 +: 31] = t[((i + k) % 16)*31 +: 31];
                    end else if (mono_pkg::dig(k, s) == 2'd2) begin : g_neg
                        assign tv[mono_pkg::tidx(s, k)*31 +: 31] = tn[((i + k) % 16)*31 +: 31];
                    end
                end
                if (NT > 1) begin : g_tree
                    localparam int OFF = mono_pkg::grp_off(s) + i * mono_pkg::grp_adders(s);
                    add_tree #(.N(NT), .W0(31), .WMAX(64), .LEND(LEND)) u_tree (
                        .x(tv), .y(ns), .ext(ext),
                        .ea(ea[OFF*32 +: mono_pkg::grp_adders(s)*32]), .eb(eb[OFF*32 +: mono_pkg::grp_adders(s)*32]), .ey(ey[OFF*32 +: mono_pkg::grp_adders(s)*32]));
                end else begin : g_single
                    assign ns = tv;
                end
                logic [51:0] nz;
                assign nz = ns;                                         // zero-extend, then shift (31 + 4 + 16 <= 52 bits)
                assign wt[s*52 +: 52] = nz << s;
            end
            // combine the 17 shifted sums: 16 adders of 53..55 bits, lend index mono_pkg::NARROW + 16 i + local
            logic [mono_pkg::WSUM-1:0] ysum;
            localparam int WOFF = mono_pkg::NARROW + 16 * i;
            add_tree #(.N(mono_pkg::NSH), .W0(52), .WMAX(mono_pkg::WSUM), .LEND(LEND)) u_wide (
                .x(wt), .y(ysum), .ext(ext),
                .ea(ea[WOFF*32 +: 16*32]), .eb(eb[WOFF*32 +: 16*32]), .ey(ey[WOFF*32 +: 16*32]));
            // reduce mod p: lo31 + hi24 (one carry fold), then + round constant, fold again
            logic [31:0] r1, r2;
            logic [30:0] t1, t2;
            alu_addp #(.W(32)) u_a1 (.a({1'b0, ysum[30:0]}), .b({8'd0, ysum[mono_pkg::WSUM-1:31]}), .y(r1));
            alu_fold #(.H(mono_pkg::WSUM - 31)) u_f1 (.r(r1), .t(t1));
            alu_addp #(.W(32)) u_a2 (.a({1'b0, t1}), .b({1'b0, rc[i*31 +: 31]}), .y(r2));
            alu_fold31 u_f2 (.r(r2), .t(t2));
            assign yc[i*31 +: 31] = t2;
        end
    endgenerate
    assign y = yc;
endmodule
