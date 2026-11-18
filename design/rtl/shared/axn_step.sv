module axn_ops #(
    parameter int STEP = 1,
    parameter int CP   = 0,
    parameter int LAY  = 0
) (
    input  logic [22*64-1:0] S,
    input  logic [10:0]      r0,
    input  logic [10:0]      r8,
    input  logic [10:0]      bk,
    output logic [4*32-1:0]  EA,
    output logic [4*32-1:0]  EB
);
    localparam int NC = 11;
    logic [21:0][63:0] sv;
    assign sv = S;
    logic [NC-1:0] ff, diag, msg;
    always_comb for (int c = 0; c < NC; c++) begin
        ff[c]   = (CP == 1) && !bk[c] && r8[c];
        diag[c] = r0[c];
        msg[c]  = bk[c] || ff[c];
    end
    logic [63:0] a0, a1, b0, b1;
    always_comb begin : ops_c
        case (STEP)
            1: if (CP == 1 && LAY == 1) begin a0 = sv[1]; a1 = sv[5];
                     b0 = bk[6] ? (diag[6] ? sv[12] : sv[8]) : sv[3]; b1 = bk[7] ? (diag[7] ? sv[14] : sv[10]) : sv[7]; end
               else begin a0 = sv[1]; a1 = sv[5];
                     b0 = bk[6] ? (diag[6] ? sv[12] : sv[8]) : sv[0]; b1 = bk[7] ? (diag[7] ? sv[14] : sv[10]) : sv[4]; end
            2: if (CP == 0) begin a0 = sv[0]; a1 = sv[4]; b0 = bk[6] ? sv[16] : sv[1]; b1 = bk[7] ? sv[17] : sv[5]; end
               else if (LAY == 1) begin a0 = sv[0]; a1 = sv[4]; b0 = sv[16]; b1 = sv[17]; end
               else begin a0 = bk[4] ? sv[0] : sv[2]; a1 = bk[5] ? sv[4] : sv[6]; b0 = bk[6] ? sv[16] : sv[3]; b1 = bk[7] ? sv[17] : sv[7]; end
            3: begin a0 = sv[2]; a1 = sv[6]; b0 = ff[6] ? sv[8] : sv[3]; b1 = ff[7] ? sv[10] : sv[7]; end
            4: begin a0 = sv[1]; a1 = sv[5];
                     b0 = msg[6] ? (diag[6] ? sv[13] : sv[9]) : sv[0]; b1 = msg[7] ? (diag[7] ? sv[15] : sv[11]) : sv[4]; end
            5: begin a0 = sv[0]; a1 = sv[4];
                     b0 = bk[6] ? sv[16] : (ff[6] ? sv[12] : sv[1]); b1 = bk[7] ? sv[17] : (ff[7] ? sv[14] : sv[5]); end
            default: begin a0 = ff[4] ? sv[9] : sv[2]; a1 = ff[5] ? sv[11] : sv[6]; b0 = sv[3]; b1 = sv[7]; end
        endcase
    end
    assign EA = {a1, a0};
    assign EB = {b1, b0};
endmodule

module axn_fin #(
    parameter int STEP = 1,
    parameter int CP   = 0,
    parameter int LAY  = 0
) (
    input  logic [22*64-1:0] S,
    input  logic [10:0]      r0,
    input  logic [10:0]      r8,
    input  logic [10:0]      bk,
    input  logic [4*32-1:0]  EY,
    output logic [22*64-1:0] M
);
    `include "axn_func.svh"
    localparam int NC = 11;
    logic [21:0][63:0] sv, m;
    assign sv = S;
    assign M  = m;
    logic [NC-1:0] ff, diag, last, cc, g, perm;
    always_comb for (int c = 0; c < NC; c++) begin
        ff[c]   = (CP == 1) && !bk[c] && r8[c];
        diag[c] = r0[c];
        last[c] = bk[c] && r8[c];
        cc[c]   = !bk[c] && !ff[c];
        g[c]    = (CP == 1) || bk[c];
        perm[c] = bk[c] && diag[c];
    end
    logic [63:0] s1, s2;
    assign s1 = EY[63:0];
    assign s2 = EY[127:64];
    logic [63:0] xa, xb, x1, x2;
    localparam bit L1 = (CP == 1) && (LAY == 1);
    assign xa = (STEP == 3 || STEP == 6) ? sv[1] : (STEP == 1 && L1) ? sv[2] : sv[3];
    assign xb = (STEP == 3 || STEP == 6) ? sv[5] : (STEP == 1 && L1) ? sv[6] : sv[7];
    alu_xor u_x1 (.a(xa), .b(s1), .y(x1));
    alu_xor u_x2 (.a(xb), .b(s2), .y(x2));
    logic [63:0] y1, y2;
    logic [7:0][63:0] o, z;
    if (STEP == 2 && CP == 1 && !L1) begin : g_y
        alu_xor u_y1 (.a(sv[1]), .b(s1), .y(y1));
        alu_xor u_y2 (.a(sv[5]), .b(s2), .y(y2));
    end else begin : g_noy
        assign y1 = '0;
        assign y2 = '0;
    end
    if (STEP == 6) begin : g_z
        alu_xor u_z0 (.a(o[0]), .b(o[2]),   .y(z[0]));
        alu_xor u_z1 (.a(o[4]), .b(o[6]),   .y(z[1]));
        alu_xor u_z2 (.a(o[1]), .b(o[3]),   .y(z[2]));
        alu_xor u_z3 (.a(o[5]), .b(o[7]),   .y(z[3]));
        alu_xor u_z4 (.a(o[2]), .b(sv[18]), .y(z[4]));
        alu_xor u_z5 (.a(o[6]), .b(sv[19]), .y(z[5]));
        alu_xor u_z6 (.a(o[3]), .b(sv[20]), .y(z[6]));
        alu_xor u_z7 (.a(o[7]), .b(sv[21]), .y(z[7]));
    end else begin : g_noz
        assign z = '0;
    end
    logic [63:0] b61, b62, c61, c62;
    logic [127:0] p6a, p6b, p6c, p6d;
    assign b61 = bk[8] ? rotl2x32(x1, 25) : (ff[8] ? s1 : ((CP == 0) ? rotl2x32(x1, 12) : rotl2x32(x1, 7)));
    assign b62 = bk[9] ? rotl2x32(x2, 25) : (ff[9] ? s2 : ((CP == 0) ? rotl2x32(x2, 12) : rotl2x32(x2, 7)));
    assign c61 = ff[10] ? sv[2] : s1;
    assign c62 = ff[10] ? sv[6] : s2;
    assign p6a = prow(0, sv[0], sv[4]);
    assign p6b = prow(1, b61, b62);
    assign p6c = prow(2, c61, c62);
    assign p6d = prow(3, sv[3], sv[7]);
    if (CP == 0 && LAY == 1) begin : g_o1
        assign o[0] = g[0] ? p6a[63:0] : c61;    assign o[4] = g[2] ? p6a[127:64] : c62;
        assign o[1] = g[0] ? p6b[63:0] : sv[0];  assign o[5] = g[2] ? p6b[127:64] : sv[4];
        assign o[2] = g[1] ? p6c[63:0] : sv[3];  assign o[6] = g[3] ? p6c[127:64] : sv[7];
        assign o[3] = g[1] ? p6d[63:0] : b61;    assign o[7] = g[3] ? p6d[127:64] : b62;
    end else begin : g_o0
        assign o[0] = g[0] ? p6a[63:0] : sv[0];  assign o[4] = g[2] ? p6a[127:64] : sv[4];
        assign o[1] = g[0] ? p6b[63:0] : b61;    assign o[5] = g[2] ? p6b[127:64] : b62;
        assign o[2] = g[1] ? p6c[63:0] : c61;    assign o[6] = g[3] ? p6c[127:64] : c62;
        assign o[3] = g[1] ? p6d[63:0] : sv[3];  assign o[7] = g[3] ? p6d[127:64] : sv[7];
    end
    logic [7:0][63:0] p;
    assign p[0] = pk(sv[8][63:32],  sv[9][63:32]);
    assign p[1] = pk(sv[10][63:32], sv[14][63:32]);
    assign p[2] = pk(sv[11][63:32], sv[10][31:0]);
    assign p[3] = pk(sv[8][31:0],   sv[15][31:0]);
    assign p[4] = pk(sv[9][31:0],   sv[13][63:32]);
    assign p[5] = pk(sv[15][63:32], sv[12][31:0]);
    assign p[6] = pk(sv[13][31:0],  sv[14][31:0]);
    assign p[7] = pk(sv[12][63:32], sv[11][31:0]);
    logic [127:0] pa, pb, pc, pd;
    logic [63:0] b1, b2, c1, c2;
    always_comb begin : fin_c
        m = '0; pa = '0; pb = '0; pc = '0; pd = '0; b1 = '0; b2 = '0; c1 = '0; c2 = '0;
        case (STEP)
        1: begin
            m[16] = s1; m[17] = s2;
            if (L1) begin
                m[16] = bk[8] ? s1 : rotl2x32(x1, 8);        m[17] = bk[8] ? s2 : rotl2x32(x2, 8);
                m[0] = sv[0];                                m[4] = sv[4];
                m[1] = bk[0] ? sv[1] : s1;                   m[5] = bk[2] ? sv[5] : s2;
                m[2] = sv[2];                                m[6] = sv[6];
                m[3] = sv[3];                                m[7] = sv[7];
            end else if (CP == 0) begin
                m[0] = bk[0] ? sv[0] : sv[2];                m[4] = bk[2] ? sv[4] : sv[6];
                m[1] = bk[0] ? sv[1] : rotl2x32(x1, 16);     m[5] = bk[2] ? sv[5] : rotl2x32(x2, 16);
                m[2] = bk[1] ? sv[2] : s1;                   m[6] = bk[3] ? sv[6] : s2;
                m[3] = bk[1] ? sv[3] : sv[1];                m[7] = bk[3] ? sv[7] : sv[5];
            end else begin
                m[0] = bk[0] ? sv[0] : s1;                   m[4] = bk[2] ? sv[4] : s2;
                m[1] = sv[1];                                m[5] = sv[5];
                m[2] = sv[2];                                m[6] = sv[6];
                m[3] = bk[1] ? sv[3] : rotl2x32(x1, 8);      m[7] = bk[3] ? sv[7] : rotl2x32(x2, 8);
            end
        end
        2: begin
            if (CP == 0) begin
                m[0] = s1; m[4] = s2;
                m[3] = bk[1] ? rotl2x32(x1, 16) : rotl2x32(x1, 12); m[7] = bk[3] ? rotl2x32(x2, 16) : rotl2x32(x2, 12);
                m[1] = sv[1]; m[5] = sv[5]; m[2] = sv[2]; m[6] = sv[6];
            end else begin
                if (L1) begin
                    b1 = rotl2x32(x1, 7); b2 = rotl2x32(x2, 7);
                    pd = prow(3, sv[16], sv[17]);
                    pa = prow(0, sv[1], sv[5]);
                end else begin
                    b1 = rotl2x32(y1, 7); b2 = rotl2x32(y2, 7);
                    pd = prow(3, sv[3], sv[7]);
                    pa = prow(0, sv[0], sv[4]);
                end
                pc = prow(2, s1, s2);
                pb = prow(1, b1, b2);
                m[0] = bk[0] ? s1 : pc[63:0];                m[4] = bk[2] ? s2 : pc[127:64];
                m[1] = bk[0] ? sv[1] : pd[63:0];             m[5] = bk[2] ? sv[5] : pd[127:64];
                m[2] = bk[1] ? sv[2] : pa[63:0];             m[6] = bk[3] ? sv[6] : pa[127:64];
                m[3] = bk[1] ? rotl2x32(x1, 16) : pb[63:0];  m[7] = bk[3] ? rotl2x32(x2, 16) : pb[127:64];
            end
        end
        3: begin
            m[2] = s1; m[6] = s2;
            c1 = (CP == 0) ? rotl2x32(x1, 8) : rotl2x32(x1, 16); c2 = (CP == 0) ? rotl2x32(x2, 8) : rotl2x32(x2, 16);
            m[1] = bk[0] ? rotl2x32(x1, 20) : (ff[0] ? sv[1] : c1);
            m[5] = bk[2] ? rotl2x32(x2, 20) : (ff[2] ? sv[5] : c2);
        end
        4: begin
            m[16] = s1; m[17] = s2;
            if (CP == 0) begin
                b1 = rotl2x32(x1, 7); b2 = rotl2x32(x2, 7);
                pa = prow(0, sv[2], sv[6]);
                pb = prow(1, b1, b2);
                pc = prow(2, s1, s2);
                pd = prow(3, sv[1], sv[5]);
                m[0] = cc[0] ? pa[63:0] : sv[0]; m[4] = cc[2] ? pa[127:64] : sv[4];
                m[1] = cc[0] ? pb[63:0] : sv[1]; m[5] = cc[2] ? pb[127:64] : sv[5];
                m[2] = cc[1] ? pc[63:0] : sv[2]; m[6] = cc[3] ? pc[127:64] : sv[6];
                m[3] = cc[1] ? pd[63:0] : sv[3]; m[7] = cc[3] ? pd[127:64] : sv[7];
            end else begin
                m[0] = cc[0] ? sv[2] : sv[0];                m[4] = cc[2] ? sv[6] : sv[4];
                m[1] = cc[0] ? rotl2x32(x1, 12) : sv[1];     m[5] = cc[2] ? rotl2x32(x2, 12) : sv[5];
                m[2] = cc[1] ? s1 : sv[2];                   m[6] = cc[3] ? s2 : sv[6];
                m[3] = cc[1] ? sv[1] : sv[3];                m[7] = cc[3] ? sv[5] : sv[7];
            end
        end
        5: begin
            m[0] = s1; m[4] = s2;
            c1 = (CP == 0) ? rotl2x32(x1, 16) : rotl2x32(x1, 8); c2 = (CP == 0) ? rotl2x32(x2, 16) : rotl2x32(x2, 8);
            m[3] = bk[1] ? rotl2x32(x1, 24) : (ff[1] ? sv[3] : c1);
            m[7] = bk[3] ? rotl2x32(x2, 24) : (ff[3] ? sv[7] : c2);
        end
        default: begin
            for (int i = 0; i < 8; i++) m[i] = last[i / 2] ? z[i] : o[i];
            for (int i = 0; i < 8; i++) m[8 + i] = perm[4 + i / 2] ? p[i] : sv[8 + i];
        end
        endcase
    end
endmodule
