// alu_add_ks45.sv - the W-bit adder as a structural Kogge-Stone network of Nangate45 cells (timing flow only: `define KS45
// makes alu_add / alu_addp #(32) instantiate it). Yosys keeps the liberty cells as they are and ABC does not remap them, so
// the adder stays at its 7-gate depth (32 bits: pg, 5 prefix levels, sum); ABC maps the same adder from behavioural RTL
// at 13 gates / 0.49 ns, which does not fit the 1 ns ARX step with its operand selects and result logic (0.26 + 0.32 ns).
// Prefix levels alternate polarity so that every node is one AOI21 / OAI21 (G) and one NAND2 / NOR2 (P): odd levels take
// true (G, P) and give inverted, even levels the reverse; bits below the level's span pass through an inverter. Sum bit i is
// p_i xor the final carry G_{i-1} (XNOR when the last level is odd). Verilator simulates it with nangate45_cells.sv.
module alu_add_ks45 #(
    parameter int W = 32
) (
    input  logic [W-1:0] a,
    input  logic [W-1:0] b,
    output logic [W-1:0] y
);
    localparam int L = $clog2(W);                            // prefix levels: 5 for W = 32, 6 for W = 33..64
    logic [W-1:0] gl [0:L];                                  // level-l generate / propagate (true polarity on even l)
    logic [W-1:0] pl [0:L];
    generate
        for (genvar i = 0; i < W; i++) begin : g_pg
            XOR2_X1 u_p (.A(a[i]), .B(b[i]), .Z(pl[0][i]));
            AND2_X1 u_g (.A1(a[i]), .A2(b[i]), .ZN(gl[0][i]));
        end
        for (genvar l = 1; l <= L; l++) begin : g_lv
            localparam int K = 1 << (l - 1);
            for (genvar i = 0; i < W; i++) begin : g_n
                if (i >= K) begin : g_c
                    if (l % 2 == 1) begin : g_odd            // true in, inverted out: Gn = ~(G_i | P_i & G_{i-K}), Pn = ~(P_i & P_{i-K})
                        AOI21_X1 u_g (.A(gl[l-1][i]), .B1(pl[l-1][i]), .B2(gl[l-1][i-K]), .ZN(gl[l][i]));
                        NAND2_X1 u_p (.A1(pl[l-1][i]), .A2(pl[l-1][i-K]), .ZN(pl[l][i]));
                    end else begin : g_even                  // inverted in, true out: G = ~(Gn_i & (Pn_i | Gn_{i-K})), P = ~(Pn_i | Pn_{i-K})
                        OAI21_X1 u_g (.A(gl[l-1][i]), .B1(pl[l-1][i]), .B2(gl[l-1][i-K]), .ZN(gl[l][i]));
                        NOR2_X1  u_p (.A1(pl[l-1][i]), .A2(pl[l-1][i-K]), .ZN(pl[l][i]));
                    end
                end else begin : g_t                         // below the span: pass through, polarity flipped
                    INV_X1 u_g (.A(gl[l-1][i]), .ZN(gl[l][i]));
                    INV_X1 u_p (.A(pl[l-1][i]), .ZN(pl[l][i]));
                end
            end
        end
        assign y[0] = pl[0][0];
        for (genvar i = 1; i < W; i++) begin : g_s
            if (L % 2 == 1) begin : g_xn                     // carry G_{i-1} arrives inverted
                XNOR2_X1 u_s (.A(pl[0][i]), .B(gl[L][i-1]), .ZN(y[i]));
            end else begin : g_x
                XOR2_X1 u_s (.A(pl[0][i]), .B(gl[L][i-1]), .Z(y[i]));
            end
        end
    endgenerate
endmodule
