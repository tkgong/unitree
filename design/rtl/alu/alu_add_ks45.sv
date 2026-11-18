module alu_add_ks45 #(
    parameter int W = 32
) (
    input  logic [W-1:0] a,
    input  logic [W-1:0] b,
    output logic [W-1:0] y
);
    localparam int L = $clog2(W);
    logic [W-1:0] gl [0:L];
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
                    if (l % 2 == 1) begin : g_odd
                        AOI21_X1 u_g (.A(gl[l-1][i]), .B1(pl[l-1][i]), .B2(gl[l-1][i-K]), .ZN(gl[l][i]));
                        NAND2_X1 u_p (.A1(pl[l-1][i]), .A2(pl[l-1][i-K]), .ZN(pl[l][i]));
                    end else begin : g_even
                        OAI21_X1 u_g (.A(gl[l-1][i]), .B1(pl[l-1][i]), .B2(gl[l-1][i-K]), .ZN(gl[l][i]));
                        NOR2_X1  u_p (.A1(pl[l-1][i]), .A2(pl[l-1][i-K]), .ZN(pl[l][i]));
                    end
                end else begin : g_t
                    INV_X1 u_g (.A(gl[l-1][i]), .ZN(gl[l][i]));
                    INV_X1 u_p (.A(pl[l-1][i]), .ZN(pl[l][i]));
                end
            end
        end
        assign y[0] = pl[0][0];
        for (genvar i = 1; i < W; i++) begin : g_s
            if (L % 2 == 1) begin : g_xn
                XNOR2_X1 u_s (.A(pl[0][i]), .B(gl[L][i-1]), .ZN(y[i]));
            end else begin : g_x
                XOR2_X1 u_s (.A(pl[0][i]), .B(gl[L][i-1]), .Z(y[i]));
            end
        end
    endgenerate
endmodule
