// add_tree.sv - pipelined pairwise adder tree of N unsigned terms (W0 bits each) -> their sum, II = 1. Level L holds
// ceil(N / 2^L) partial sums of width min(W0 + L, WMAX); element j of level L = elements 2j + 2j+1 of level L-1 (an
// adder) or element 2j alone (odd count: a pass-through). Every level ends in a register; the output is delayed to
// exactly LAT register stages (LAT >= clog2 N) so trees of different depth stay aligned.
// The first NLD adders of level 1 are alu_lend (NLD <= N / 2): while ext = 1 they add ea + eb for the ARX blocks
// instead (the sum on ey, the same cycle); all other adders are alu_addp.
module add_tree #(
    parameter int N    = 2,
    parameter int W0   = 31,
    parameter int WMAX = 64,
    parameter int LAT  = 4,
    parameter int NLD  = 0,
    parameter int NLP  = (NLD > 0) ? NLD : 1,
    parameter int WO   = ((W0 + $clog2(N)) < WMAX) ? (W0 + $clog2(N)) : WMAX
) (
    input  logic             clk,
    input  logic [N*W0-1:0]  x,
    output logic [WO-1:0]    y,
    input  logic             ext,
    input  logic [NLP*32-1:0] ea,
    input  logic [NLP*32-1:0] eb,
    output logic [NLP*32-1:0] ey
);
    localparam int LV = $clog2(N);
    function automatic int wl(input int L);
        wl = ((W0 + L) < WMAX) ? (W0 + L) : WMAX;
    endfunction
    function automatic int nl(input int L);
        nl = (N + (1 << L) - 1) >> L;
    endfunction
    function automatic int off(input int L);
        int l;
        off = 0;
        for (l = 0; l < L; l++) off = off + nl(l) * wl(l);
    endfunction
    localparam int EBITS = off(LV) + wl(LV);
    wire  [EBITS-1:0] e;                                      // level 0 = x; level L = the registered sums
    assign e[N*W0-1:0] = x;
    generate
        if (NLD == 0) begin : g_noey
            assign ey = '0;
        end
        for (genvar L = 1; L <= LV; L++) begin : g_lvl
            logic [nl(L)*wl(L)-1:0] nxt;
            for (genvar j = 0; j < nl(L); j++) begin : g_el
                if (2 * j + 1 < nl(L - 1)) begin : g_add
                    logic [wl(L)-1:0] a, b, s;
                    assign a = e[off(L - 1) + (2 * j) * wl(L - 1) +: wl(L - 1)];
                    assign b = e[off(L - 1) + (2 * j + 1) * wl(L - 1) +: wl(L - 1)];
                    if (L == 1 && j < NLD) begin : g_lend
                        logic [wl(L)-1:0] la, lb;
                        assign la = ea[j*32 +: 32];
                        assign lb = eb[j*32 +: 32];
                        alu_lend #(.W(wl(L))) u_add (.ext(ext), .ea(la), .eb(lb), .a(a), .b(b), .y(s));
                        assign ey[j*32 +: 32] = s[31:0];
                    end else begin : g_priv
                        alu_addp #(.W(wl(L))) u_add (.a(a), .b(b), .y(s));
                    end
                    assign nxt[j * wl(L) +: wl(L)] = s;
                end else begin : g_pass
                    assign nxt[j * wl(L) +: wl(L)] = e[off(L - 1) + (2 * j) * wl(L - 1) +: wl(L - 1)];
                end
            end
            logic [nl(L)*wl(L)-1:0] q;
            always_ff @(posedge clk) q <= nxt;
            assign e[off(L) +: nl(L) * wl(L)] = q;
        end
        if (LAT > LV) begin : g_dly                          // align to LAT stages
            logic [wl(LV)-1:0] d [0:LAT-LV-1];
            always_ff @(posedge clk) d[0] <= e[off(LV) +: wl(LV)];
            for (genvar i = 1; i < LAT - LV; i++) begin : g_d
                always_ff @(posedge clk) d[i] <= d[i - 1];
            end
            assign y = d[LAT - LV - 1];
        end else begin : g_nodly
            assign y = e[off(LV) +: wl(LV)];
        end
    endgenerate
endmodule
