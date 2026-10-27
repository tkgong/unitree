// add_tree.sv - pairwise adder tree of N unsigned terms (W0 bits each) -> their sum (W0 + clog2(N) bits, capped at WMAX).
// Level L holds ceil(N / 2^L) partial sums of width wl(L) = min(W0 + L, WMAX); element j of level L is the sum of elements
// 2j and 2j+1 of level L-1 (an adder) or element 2j alone (pass-through, when the level has an odd count). N - 1 adders,
// every one at least W0 + 1 >= 32 bits, indexed in level order: aoff(L) + j.
// LEND = 1: every adder is an alu_lend (its operands come from the ea / eb ports while ext = 1, its low 32 bits go to ey);
// LEND = 0: alu_addp (private).
module add_tree #(
    parameter int N    = 2,
    parameter int W0   = 31,
    parameter int WMAX = 64,
    parameter int LEND = 1,
    parameter int NA   = (N > 1) ? N - 1 : 1,                  // lend port width (at least one slot)
    parameter int WO   = ((W0 + $clog2(N)) < WMAX) ? (W0 + $clog2(N)) : WMAX
) (
    input  logic [N*W0-1:0]  x,
    output logic [WO-1:0]    y,
    input  logic             ext,
    input  logic [NA*32-1:0] ea,
    input  logic [NA*32-1:0] eb,
    output logic [NA*32-1:0] ey
);
    localparam int LV = $clog2(N);
    function automatic int wl(input int L);
        wl = ((W0 + L) < WMAX) ? (W0 + L) : WMAX;
    endfunction
    function automatic int nl(input int L);                      // elements at level L
        nl = (N + (1 << L) - 1) >> L;
    endfunction
    function automatic int off(input int L);                     // bit offset of level L in the flat vector e
        int l;
        off = 0;
        for (l = 0; l < L; l++) off = off + nl(l) * wl(l);
    endfunction
    function automatic int aoff(input int L);                    // adders of the levels before L
        int l;
        aoff = 0;
        for (l = 1; l < L; l++) aoff = aoff + (nl(l - 1) >> 1);
    endfunction
    localparam int EBITS = off(LV) + wl(LV);
    logic [EBITS-1:0] e;
    assign e[N*W0-1:0] = x;
    generate
        if (N == 1) begin : g_one
            assign ey = '0;
        end
        for (genvar L = 1; L <= LV; L++) begin : g_lvl
            for (genvar j = 0; j < nl(L); j++) begin : g_el
                if (2 * j + 1 < nl(L - 1)) begin : g_add
                    logic [wl(L)-1:0] a, b, s;
                    assign a = e[off(L - 1) + (2 * j) * wl(L - 1) +: wl(L - 1)];
                    assign b = e[off(L - 1) + (2 * j + 1) * wl(L - 1) +: wl(L - 1)];
                    if (LEND) begin : g_lend
                        logic [wl(L)-1:0] la, lb;
                        assign la = ea[(aoff(L) + j) * 32 +: 32];
                        assign lb = eb[(aoff(L) + j) * 32 +: 32];
                        alu_lend #(.W(wl(L))) u_add (.ext(ext), .ea(la), .eb(lb), .a(a), .b(b), .y(s));
                        assign ey[(aoff(L) + j) * 32 +: 32] = s[31:0];
                    end else begin : g_priv
                        alu_addp #(.W(wl(L))) u_add (.a(a), .b(b), .y(s));
                        assign ey[(aoff(L) + j) * 32 +: 32] = '0;
                    end
                    assign e[off(L) + j * wl(L) +: wl(L)] = s;
                end else begin : g_pass
                    logic [wl(L)-1:0] a;
                    assign a = e[off(L - 1) + (2 * j) * wl(L - 1) +: wl(L - 1)];
                    assign e[off(L) + j * wl(L) +: wl(L)] = a;
                end
            end
        end
    endgenerate
    assign y = e[off(LV) +: wl(LV)];
endmodule
