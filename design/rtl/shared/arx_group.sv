module arx_group #(
    parameter int NBK  = 5,
    parameter int BL   = 22,
    parameter int CP   = 0,
    parameter int PRIV = 0,
    parameter int NA   = 4 * NBK * 6,
    parameter int EXT  = 0,
    parameter int LAY  = 0,
    parameter int BKC  = -1
) (
    input  logic                 clk,
    input  logic [NBK*BL*64-1:0] x,
    input  logic [8:0]           r,
    input  logic                 blake,
    output logic [NBK*BL*64-1:0] y,
    output logic [NA*32-1:0]     ea,
    output logic [NA*32-1:0]     eb,
    input  logic [NA*32-1:0]     ey,
    output logic [6*NBK*BL*64-1:0] an,
    input  logic [6*NBK*BL*64-1:0] aq
);
    function automatic bit wmask(input int s, input int l);
        case (s)
            1, 4: wmask = (l < 8) || (l == 16) || (l == 17);
            2:    wmask = (l < 8);
            3:    wmask = (l == 1) || (l == 2) || (l == 5) || (l == 6);
            5:    wmask = (l == 0) || (l == 3) || (l == 4) || (l == 7);
            default: wmask = (l < 16);
        endcase
    endfunction
    wire  [NBK*BL*64-1:0] R [0:6];
    localparam int NC = 11;
    wire  [NC-1:0]        r0 [0:5][0:NBK-1];
    wire  [NC-1:0]        r8 [0:5][0:NBK-1];
    wire  [NC-1:0]        bk [0:5][0:NBK-1];
    assign R[0] = x;
    generate
        for (genvar b = 0; b < ((BKC < 0) ? 0 : NBK); b++) begin : g_ctl0c
`ifdef KS45
            for (genvar c = 0; c < NC; c++) begin : g_c
                BUF_X1 u_0 (.A(r[0]),  .Z(r0[0][b][c]));
                BUF_X1 u_8 (.A(r[8]),  .Z(r8[0][b][c]));
            end
`else
            assign r0[0][b] = {NC{r[0]}};
            assign r8[0][b] = {NC{r[8]}};
`endif
            assign bk[0][b] = {NC{BKC != 0}};
        end
        for (genvar s = 1; s <= ((BKC < 0) ? 0 : 5); s++) begin : g_ctlc
            for (genvar b = 0; b < NBK; b++) begin : g_blk
                logic [NC-1:0] r0_q, r8_q;
                (* keep *) always_ff @(posedge clk) begin r0_q <= r0[s - 1][b]; r8_q <= r8[s - 1][b]; end
                assign r0[s][b] = r0_q;
                assign r8[s][b] = r8_q;
                assign bk[s][b] = {NC{BKC != 0}};
            end
        end
    endgenerate
    generate
        for (genvar b = 0; b < ((BKC < 0) ? NBK : 0); b++) begin : g_ctl0
`ifdef KS45
            for (genvar c = 0; c < NC; c++) begin : g_c
                BUF_X1 u_0 (.A(r[0]),  .Z(r0[0][b][c]));
                BUF_X1 u_8 (.A(r[8]),  .Z(r8[0][b][c]));
                BUF_X1 u_b (.A(blake), .Z(bk[0][b][c]));
            end
`else
            assign r0[0][b] = {NC{r[0]}};
            assign r8[0][b] = {NC{r[8]}};
            assign bk[0][b] = {NC{blake}};
`endif
        end
        for (genvar s = 1; s <= ((BKC < 0) ? 5 : 0); s++) begin : g_ctl
            for (genvar b = 0; b < NBK; b++) begin : g_blk
                logic [NC-1:0] r0_q, r8_q, bk_q;
                (* keep *) always_ff @(posedge clk) begin r0_q <= r0[s - 1][b]; r8_q <= r8[s - 1][b]; bk_q <= bk[s - 1][b]; end
                assign r0[s][b] = r0_q;
                assign r8[s][b] = r8_q;
                assign bk[s][b] = bk_q;
            end
        end
    endgenerate
    generate
        for (genvar s = 1; s <= 6; s++) begin : g_step
            logic [NBK*BL*64-1:0] nxt;
            for (genvar b = 0; b < NBK; b++) begin : g_blk
                localparam int Q = ((s - 1) * NBK + b) * 4;
                logic [22*64-1:0] sv, m;
                logic [4*32-1:0]  a, bb, sum;
                if (BL == 22) begin : g_22
                    assign sv = R[s - 1][b*BL*64 +: BL*64];
                end else begin : g_18
                    assign sv = {{((22 - BL)*64){1'b0}}, R[s - 1][b*BL*64 +: BL*64]};
                end
                axn_ops #(.STEP(s), .CP(CP), .LAY(LAY)) u_ops (.S(sv), .r0(r0[s - 1][b]), .r8(r8[s - 1][b]), .bk(bk[s - 1][b]), .EA(a), .EB(bb));
                if (PRIV) begin : g_priv
                    for (genvar q = 0; q < 4; q++) begin : g_add
                        alu_addp #(.W(32)) u_add (.a(a[q*32 +: 32]), .b(bb[q*32 +: 32]), .y(sum[q*32 +: 32]));
                    end
                    assign ea[Q*32 +: 128] = '0;
                    assign eb[Q*32 +: 128] = '0;
                end else begin : g_lend
                    assign ea[Q*32 +: 128] = a;
                    assign eb[Q*32 +: 128] = bb;
                    assign sum = ey[Q*32 +: 128];
                end
                axn_fin #(.STEP(s), .CP(CP), .LAY(LAY)) u_fin (.S(sv), .r0(r0[s - 1][b]), .r8(r8[s - 1][b]), .bk(bk[s - 1][b]), .EY(sum), .M(m));
                for (genvar l = 0; l < BL; l++) begin : g_lane
                    if (wmask(s, l)) begin : g_w
                        assign nxt[(b*BL + l)*64 +: 64] = m[l*64 +: 64];
                    end else begin : g_p
                        assign nxt[(b*BL + l)*64 +: 64] = sv[l*64 +: 64];
                    end
                end
            end
            if (EXT) begin : g_ext
                assign an[(s - 1)*NBK*BL*64 +: NBK*BL*64] = nxt;
                assign R[s] = aq[(s - 1)*NBK*BL*64 +: NBK*BL*64];
            end else begin : g_reg
                logic [NBK*BL*64-1:0] q;
                always_ff @(posedge clk) q <= nxt;
                assign R[s] = q;
                assign an[(s - 1)*NBK*BL*64 +: NBK*BL*64] = '0;
            end
        end
    endgenerate
    assign y = R[6];
endmodule
