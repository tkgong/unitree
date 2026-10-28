// axn_step.sv - the ARX block steps of dse/TOP/level_ops_axn.h (ChaCha20 / BLAKE3 on SIX steps per traversal), one block
// = 22 lanes of 64 bits (block-relative: rows A 0,4  B 1,5  C 2,6  D 3,7, message / copy 8..15, T 16,17, h 18..21).
// axn_ops #(STEP, CP): the operands EA / EB of the block's four 32-bit adds (they run on lent Monolith adders, alu_lend in the
//                      datapath levels; EA[q] = word q of the 4 x 32 bus).
// axn_fin #(STEP, CP): the step's result lanes from the sums EY: the xors (alu_xor instances), constant rotations and the row
//                      permutation P (wiring). Lanes the step does not write are output as 0 (arx_group keeps X_s there: WMASK).
// CP: the copy of the block group (ChaCha20 alternates copies 0 / 1, see level_ops_axn.h). Transcribed by hand from the C++;
// verified in the unit18 tops against the HLS C++ DLL (verify/run_tb.sh, closed-loop traces).

module axn_ops #(
    parameter int STEP = 1,
    parameter int CP   = 0
) (
    input  logic [22*64-1:0] S,
    input  logic [8:0]       r,
    input  logic             blake,
    output logic [4*32-1:0]  EA,
    output logic [4*32-1:0]  EB
);
    logic [21:0][63:0] sv;
    assign sv = S;
    logic ff, diag, msg;
    assign ff   = (CP == 1) && !blake && r[8];               // axn_ff<CP>: ChaCha20 feed-forward traversal
    assign diag = r[0];
    assign msg  = blake || ff;
    logic [63:0] a0, a1, b0, b1;                             // words(a0, a1, EA), words(b0, b1, EB)
    always_comb begin : ops_c
        case (STEP)
            1: begin a0 = sv[1]; a1 = sv[5];
                     b0 = blake ? (diag ? sv[12] : sv[8]) : sv[0]; b1 = blake ? (diag ? sv[14] : sv[10]) : sv[4]; end
            2: if (CP == 0) begin a0 = sv[0]; a1 = sv[4]; b0 = blake ? sv[16] : sv[1]; b1 = blake ? sv[17] : sv[5]; end
               else begin a0 = blake ? sv[0] : sv[2]; a1 = blake ? sv[4] : sv[6]; b0 = blake ? sv[16] : sv[3]; b1 = blake ? sv[17] : sv[7]; end
            3: begin a0 = sv[2]; a1 = sv[6]; b0 = ff ? sv[8] : sv[3]; b1 = ff ? sv[10] : sv[7]; end
            4: begin a0 = sv[1]; a1 = sv[5];
                     b0 = msg ? (diag ? sv[13] : sv[9]) : sv[0]; b1 = msg ? (diag ? sv[15] : sv[11]) : sv[4]; end
            5: begin a0 = sv[0]; a1 = sv[4];
                     b0 = blake ? sv[16] : (ff ? sv[12] : sv[1]); b1 = blake ? sv[17] : (ff ? sv[14] : sv[5]); end
            default: begin a0 = ff ? sv[9] : sv[2]; a1 = ff ? sv[11] : sv[6]; b0 = sv[3]; b1 = sv[7]; end
        endcase
    end
    assign EA = {a1, a0};                                    // EA[0] = LO(a0), EA[1] = HI(a0), EA[2] = LO(a1), EA[3] = HI(a1)
    assign EB = {b1, b0};
endmodule

module axn_fin #(
    parameter int STEP = 1,
    parameter int CP   = 0
) (
    input  logic [22*64-1:0] S,
    input  logic [8:0]       r,
    input  logic             blake,
    input  logic [4*32-1:0]  EY,
    output logic [22*64-1:0] M
);
    `include "axn_func.svh"
    logic [21:0][63:0] sv, m;
    assign sv = S;
    assign M  = m;
    logic ff, diag, last, cc, g, perm;
    assign ff   = (CP == 1) && !blake && r[8];
    assign diag = r[0];
    assign last = blake && r[8];                              // BLAKE3 last half-round: r = 13 | 256
    assign cc   = !blake && !ff;
    assign g    = (CP == 1) || blake;
    assign perm = blake && diag;
    logic [63:0] s1, s2;                                      // s1 = pk(EY[0], EY[1]), s2 = pk(EY[2], EY[3])
    assign s1 = EY[63:0];
    assign s2 = EY[127:64];
    // the step's two row xors: steps 3, 6 xor B (sv1, sv5) with the sums, the others D (sv3, sv7)
    logic [63:0] xa, xb, x1, x2;
    assign xa = (STEP == 3 || STEP == 6) ? sv[1] : sv[3];
    assign xb = (STEP == 3 || STEP == 6) ? sv[5] : sv[7];
    alu_xor u_x1 (.a(xa), .b(s1), .y(x1));
    alu_xor u_x2 (.a(xb), .b(s2), .y(x2));
    logic [63:0] y1, y2;                                      // step 2 CP 1: b' = rotl7(B ^ c')
    logic [7:0][63:0] o, z;                                   // step 6: rows after P; z = the last-round finalisation xors
    if (STEP == 2 && CP == 1) begin : g_y
        alu_xor u_y1 (.a(sv[1]), .b(s1), .y(y1));
        alu_xor u_y2 (.a(sv[5]), .b(s2), .y(y2));
    end else begin : g_noy
        assign y1 = '0;
        assign y2 = '0;
    end
    if (STEP == 6) begin : g_z                                // o0^o2, o4^o6, o1^o3, o5^o7, then o2^h0, o6^h1, o3^h2, o7^h3 (XOF)
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
    // step 6 rows before / after P (combinational, feed the z xors)
    logic [63:0] b61, b62, c61, c62;
    logic [127:0] p6a, p6b, p6c, p6d;
    assign b61 = blake ? rotl2x32(x1, 25) : (ff ? s1 : ((CP == 0) ? rotl2x32(x1, 12) : rotl2x32(x1, 7)));
    assign b62 = blake ? rotl2x32(x2, 25) : (ff ? s2 : ((CP == 0) ? rotl2x32(x2, 12) : rotl2x32(x2, 7)));
    assign c61 = ff ? sv[2] : s1;
    assign c62 = ff ? sv[6] : s2;
    assign p6a = prow(0, sv[0], sv[4]);
    assign p6b = prow(1, b61, b62);
    assign p6c = prow(2, c61, c62);
    assign p6d = prow(3, sv[3], sv[7]);
    assign o[0] = g ? p6a[63:0] : sv[0];  assign o[4] = g ? p6a[127:64] : sv[4];
    assign o[1] = g ? p6b[63:0] : b61;    assign o[5] = g ? p6b[127:64] : b62;
    assign o[2] = g ? p6c[63:0] : c61;    assign o[6] = g ? p6c[127:64] : c62;
    assign o[3] = g ? p6d[63:0] : sv[3];  assign o[7] = g ? p6d[127:64] : sv[7];
    // step 6: sigma = 2 6 3 10 7 0 4 13 1 11 12 5 9 14 15 8 on the message lanes (wiring)
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
            if (CP == 0) begin
                m[0] = blake ? sv[0] : sv[2];                m[4] = blake ? sv[4] : sv[6];
                m[1] = blake ? sv[1] : rotl2x32(x1, 16);     m[5] = blake ? sv[5] : rotl2x32(x2, 16);
                m[2] = blake ? sv[2] : s1;                   m[6] = blake ? sv[6] : s2;
                m[3] = blake ? sv[3] : sv[1];                m[7] = blake ? sv[7] : sv[5];
            end else begin
                m[0] = blake ? sv[0] : s1;                   m[4] = blake ? sv[4] : s2;
                m[1] = sv[1];                                m[5] = sv[5];
                m[2] = sv[2];                                m[6] = sv[6];
                m[3] = blake ? sv[3] : rotl2x32(x1, 8);      m[7] = blake ? sv[7] : rotl2x32(x2, 8);
            end
        end
        2: begin
            if (CP == 0) begin
                m[0] = s1; m[4] = s2;
                m[3] = blake ? rotl2x32(x1, 16) : rotl2x32(x1, 12); m[7] = blake ? rotl2x32(x2, 16) : rotl2x32(x2, 12);
                m[1] = sv[1]; m[5] = sv[5]; m[2] = sv[2]; m[6] = sv[6];
            end else begin
                b1 = rotl2x32(y1, 7); b2 = rotl2x32(y2, 7);
                pc = prow(2, s1, s2);                        // c' -> A
                pd = prow(3, sv[3], sv[7]);                  // d  -> B
                pa = prow(0, sv[0], sv[4]);                  // a  -> C
                pb = prow(1, b1, b2);                        // b' -> D
                m[0] = blake ? s1 : pc[63:0];                m[4] = blake ? s2 : pc[127:64];
                m[1] = blake ? sv[1] : pd[63:0];             m[5] = blake ? sv[5] : pd[127:64];
                m[2] = blake ? sv[2] : pa[63:0];             m[6] = blake ? sv[6] : pa[127:64];
                m[3] = blake ? rotl2x32(x1, 16) : pb[63:0];  m[7] = blake ? rotl2x32(x2, 16) : pb[127:64];
            end
        end
        3: begin
            m[2] = s1; m[6] = s2;
            c1 = (CP == 0) ? rotl2x32(x1, 8) : rotl2x32(x1, 16); c2 = (CP == 0) ? rotl2x32(x2, 8) : rotl2x32(x2, 16);
            m[1] = blake ? rotl2x32(x1, 20) : (ff ? sv[1] : c1);
            m[5] = blake ? rotl2x32(x2, 20) : (ff ? sv[5] : c2);
        end
        4: begin
            m[16] = s1; m[17] = s2;
            if (CP == 0) begin
                b1 = rotl2x32(x1, 7); b2 = rotl2x32(x2, 7);
                pa = prow(0, sv[2], sv[6]);                  // a  -> A
                pb = prow(1, b1, b2);                        // b' -> B
                pc = prow(2, s1, s2);                        // c' -> C
                pd = prow(3, sv[1], sv[5]);                  // d  -> D
                m[0] = cc ? pa[63:0] : sv[0]; m[4] = cc ? pa[127:64] : sv[4];
                m[1] = cc ? pb[63:0] : sv[1]; m[5] = cc ? pb[127:64] : sv[5];
                m[2] = cc ? pc[63:0] : sv[2]; m[6] = cc ? pc[127:64] : sv[6];
                m[3] = cc ? pd[63:0] : sv[3]; m[7] = cc ? pd[127:64] : sv[7];
            end else begin
                m[0] = cc ? sv[2] : sv[0];                   m[4] = cc ? sv[6] : sv[4];
                m[1] = cc ? rotl2x32(x1, 12) : sv[1];        m[5] = cc ? rotl2x32(x2, 12) : sv[5];
                m[2] = cc ? s1 : sv[2];                      m[6] = cc ? s2 : sv[6];
                m[3] = cc ? sv[1] : sv[3];                   m[7] = cc ? sv[5] : sv[7];
            end
        end
        5: begin
            m[0] = s1; m[4] = s2;
            c1 = (CP == 0) ? rotl2x32(x1, 16) : rotl2x32(x1, 8); c2 = (CP == 0) ? rotl2x32(x2, 16) : rotl2x32(x2, 8);
            m[3] = blake ? rotl2x32(x1, 24) : (ff ? sv[3] : c1);
            m[7] = blake ? rotl2x32(x2, 24) : (ff ? sv[7] : c2);
        end
        default: begin                                       // 6
            for (int i = 0; i < 8; i++) m[i] = last ? z[i] : o[i];   // last: finalisation + XOF second half (GGM build)
            for (int i = 0; i < 8; i++) m[8 + i] = perm ? p[i] : sv[8 + i];
        end
        endcase
    end
endmodule
