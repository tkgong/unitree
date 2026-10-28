// b3_block.sv - one BLAKE3 block of the natural BLAKE3 kernel: 16 state words v, the 16 message words m, the 8 chaining
// words h. One ARX step per cycle in place on the four hardware columns: 4 additions on the adders behind ea / eb / ey,
// 4 xor + rotate right 16 / 12 / 8 / 7 (= rotate left 16 / 20 / 24 / 25). Diagonal half-rounds on the P-permuted layout
// (perm at every half-round end); the message is permuted by SIGMA at every round end; the output is the finalisation
// v[i] ^ v[i+8], v[i+8] ^ h[i].
module b3_block (
    input  logic            clk,
    input  logic            ld,
    input  logic            en,
    input  logic [1:0]      add_sel,       // 0: a + b   1: a + message   2: c + d
    input  logic            xr_en,
    input  logic            xr_tgt,        // 0: d <- rotr(d ^ a', R)   1: b <- rotr(b ^ c', R)
    input  logic [1:0]      rot_sel,       // rotate right 0: 16   1: 12   2: 8   3: 7
    input  logic            msg_y,         // 0 = mx (even message word), 1 = my (odd)
    input  logic            diag,          // diagonal half-round: message words 8..15 in P column order
    input  logic            perm,
    input  logic            sigma,
    input  logic [511:0]    in_v,
    input  logic [511:0]    in_m,
    input  logic [255:0]    in_h,
    output logic [511:0]    out,
    output logic [4*32-1:0] ea,
    output logic [4*32-1:0] eb,
    input  logic [4*32-1:0] ey
);
    function automatic int SIGMA(input int j);
        case (j)
            0: SIGMA = 2;   1: SIGMA = 6;   2: SIGMA = 3;   3: SIGMA = 10;  4: SIGMA = 7;   5: SIGMA = 0;   6: SIGMA = 4;   7: SIGMA = 13;
            8: SIGMA = 1;   9: SIGMA = 11;  10: SIGMA = 12; 11: SIGMA = 5;  12: SIGMA = 9;  13: SIGMA = 14; 14: SIGMA = 15; 15: SIGMA = 8;
            default: SIGMA = 0;
        endcase
    endfunction
    logic [511:0] v, m, w, vn, ms;
    logic [255:0] h;
    function automatic logic [31:0] rotl(input logic [31:0] x, input int n);
        rotl = (x << n) | (x >> (32 - n));
    endfunction
    generate
        for (genvar j = 0; j < 4; j++) begin : g_col
            localparam int DI = (4 - j) % 4;                    // the diagonal held by hardware column j
            logic [31:0] a, b, c, d, sum, msg, opa, opb, xi, xo;
            logic [63:0] xx;
            assign a = v[j*32 +: 32];
            assign b = v[(4 + j)*32 +: 32];
            assign c = v[(8 + j)*32 +: 32];
            assign d = v[(12 + j)*32 +: 32];
            assign msg = diag ? (msg_y ? m[(8 + 2*DI + 1)*32 +: 32] : m[(8 + 2*DI)*32 +: 32])
                              : (msg_y ? m[(2*j + 1)*32 +: 32] : m[(2*j)*32 +: 32]);
            assign opa = (add_sel == 2'd2) ? c : a;
            assign opb = (add_sel == 2'd0) ? b : (add_sel == 2'd1) ? msg : d;
            assign ea[j*32 +: 32] = opa;
            assign eb[j*32 +: 32] = opb;
            assign sum = ey[j*32 +: 32];
            assign xi = xr_tgt ? b : d;
            alu_xor u_xor (.a({32'd0, xi}), .b({32'd0, sum}), .y(xx));
            assign xo = (rot_sel == 2'd0) ? rotl(xx[31:0], 16) : (rot_sel == 2'd1) ? rotl(xx[31:0], 20)
                      : (rot_sel == 2'd2) ? rotl(xx[31:0], 24) : rotl(xx[31:0], 25);
            assign w[j*32 +: 32]        = (add_sel == 2'd0 || add_sel == 2'd1) ? sum : a;
            assign w[(4 + j)*32 +: 32]  = (xr_en && xr_tgt) ? xo : b;
            assign w[(8 + j)*32 +: 32]  = (add_sel == 2'd2) ? sum : c;
            assign w[(12 + j)*32 +: 32] = (xr_en && !xr_tgt) ? xo : d;
        end
        for (genvar r = 0; r < 4; r++) begin : g_prow
            for (genvar j = 0; j < 4; j++) begin : g_pcol
                localparam int SRC = ((r - j) % 4 + 4) % 4;
                assign vn[(4*r + j)*32 +: 32] = perm ? w[(4*r + SRC)*32 +: 32] : w[(4*r + j)*32 +: 32];
            end
        end
        for (genvar j = 0; j < 16; j++) begin : g_sig
            assign ms[j*32 +: 32] = m[SIGMA(j)*32 +: 32];
        end
    endgenerate
    always_ff @(posedge clk) begin
        if (ld) begin v <= in_v; m <= in_m; h <= in_h; end
        else if (en) begin
            v <= vn;
            if (sigma) m <= ms;
        end
    end
    generate
        for (genvar k = 0; k < 8; k++) begin : g_fx              // words 2k, 2k+1: k < 4 -> v ^ v[+8], k >= 4 -> v ^ h
            logic [63:0] xa, xb, xy;
            assign xa = {v[(2*k + 1)*32 +: 32], v[(2*k)*32 +: 32]};
            if (k < 4) begin : g_lo
                assign xb = {v[(2*k + 9)*32 +: 32], v[(2*k + 8)*32 +: 32]};
            end else begin : g_hi
                assign xb = {h[(2*k - 7)*32 +: 32], h[(2*k - 8)*32 +: 32]};
            end
            alu_xor u_fx (.a(xa), .b(xb), .y(xy));
            assign out[(2*k)*32 +: 32]     = xy[31:0];
            assign out[(2*k + 1)*32 +: 32] = xy[63:32];
        end
    endgenerate
endmodule
