// arx_block.sv - one ChaCha20 / BLAKE3 block: 16 state words v (rows a b c d, hardware columns 0..3), 16 words m (the
// ChaCha input copy for the feed-forward / the BLAKE3 message) and, for BLAKE3, the 8 chaining words h. Every cycle the
// block executes one ARX step on its four hardware columns in place: 4 additions (on the four adders behind ea / eb / ey:
// the block has no adders of its own), 4 xor + rotate. The diagonal half-rounds are column half-rounds on the P-permuted
// layout: at the end of every half-round (perm) word (r, j) <- word (r, (r - j) mod 4), an involution, so the hardware
// columns always hold (a_j, b_j, c_j, d_j) of the quarter-rounds to do. This is the block of the SHARED PE: it runs
// either primitive (blake selects the rotations, the message adds, the finalisation); the natural kernels use
// cc_block / b3_block. Controls come from arx_ctrl.
module arx_block (
    input  logic         clk,
    input  logic         ld,            // v <- in_v, m <- in_m, h <- in_h
    input  logic         en,            // a step executes this cycle (else the block holds)
    input  logic         blake,
    input  logic [1:0]   add_sel,       // 0: a + b   1: a + message   2: c + d   3: feed-forward v[row] + m[row]
    input  logic [1:0]   ff_row,
    input  logic         xr_en,         // xor + rotate this step
    input  logic         xr_tgt,        // 0: d <- rot(d ^ a')   1: b <- rot(b ^ c')
    input  logic [1:0]   rot_sel,       // 0: 16   1: 12 (ChaCha) / 20 (BLAKE3)   2: 8 / 24   3: 7 / 25   (rotate left)
    input  logic         msg_y,         // message word: 0 = mx (even), 1 = my (odd)
    input  logic         diag,          // diagonal half-round: message words 8..15 in P column order
    input  logic         perm,          // apply P at this step's write-back
    input  logic         sigma,         // permute m by SIGMA at this step (end of a BLAKE3 round)
    input  logic [511:0] in_v,
    input  logic [511:0] in_m,
    input  logic [255:0] in_h,
    output logic [511:0] out,           // ChaCha: v; BLAKE3: v[i] ^ v[i+8], v[i+8] ^ h[i]
    output logic [4*32-1:0] ea,
    output logic [4*32-1:0] eb,
    input  logic [4*32-1:0] ey
);
    function automatic int SIGMA(input int j);                   // BLAKE3 message permutation
        case (j)
            0: SIGMA = 2;
            1: SIGMA = 6;
            2: SIGMA = 3;
            3: SIGMA = 10;
            4: SIGMA = 7;
            5: SIGMA = 0;
            6: SIGMA = 4;
            7: SIGMA = 13;
            8: SIGMA = 1;
            9: SIGMA = 11;
            10: SIGMA = 12;
            11: SIGMA = 5;
            12: SIGMA = 9;
            13: SIGMA = 14;
            14: SIGMA = 15;
            15: SIGMA = 8;
            default: SIGMA = 0;
        endcase
    endfunction
    logic [511:0] v, m, w, vn;
    logic [255:0] h;
    function automatic logic [31:0] rotl(input logic [31:0] x, input int n);
        rotl = (x << n) | (x >> (32 - n));
    endfunction
    generate
        for (genvar j = 0; j < 4; j++) begin : g_col
            logic [31:0] a, b, c, d, sum, msg, opa, opb, xi, xo, r0, r1, r2, r3;
            assign a = v[j*32 +: 32];
            assign b = v[(4 + j)*32 +: 32];
            assign c = v[(8 + j)*32 +: 32];
            assign d = v[(12 + j)*32 +: 32];
            // message word of this column: columns take m[2j], m[2j+1]; the diagonal i sits in column (4 - i) % 4
            localparam int DI = (4 - j) % 4;
            assign msg = diag ? (msg_y ? m[(8 + 2*DI + 1)*32 +: 32] : m[(8 + 2*DI)*32 +: 32])
                              : (msg_y ? m[(2*j + 1)*32 +: 32] : m[(2*j)*32 +: 32]);
            assign opa = (add_sel == 2'd2) ? c : (add_sel == 2'd3) ? v[(4*ff_row + j)*32 +: 32] : a;
            assign opb = (add_sel == 2'd0) ? b : (add_sel == 2'd1) ? msg : (add_sel == 2'd2) ? d : m[(4*ff_row + j)*32 +: 32];
            assign ea[j*32 +: 32] = opa;
            assign eb[j*32 +: 32] = opb;
            assign sum = ey[j*32 +: 32];
            // xor + rotate
            assign xi = xr_tgt ? b : d;
            logic [63:0] xx;
            alu_xor u_xor (.a({32'd0, xi}), .b({32'd0, sum}), .y(xx));
            assign r0 = rotl(xx[31:0], 16);
            assign r1 = blake ? rotl(xx[31:0], 20) : rotl(xx[31:0], 12);
            assign r2 = blake ? rotl(xx[31:0], 24) : rotl(xx[31:0], 8);
            assign r3 = blake ? rotl(xx[31:0], 25) : rotl(xx[31:0], 7);
            assign xo = (rot_sel == 2'd0) ? r0 : (rot_sel == 2'd1) ? r1 : (rot_sel == 2'd2) ? r2 : r3;
            // write-back of the four words of this column
            assign w[j*32 +: 32]        = (add_sel == 2'd0 || add_sel == 2'd1 || (add_sel == 2'd3 && ff_row == 2'd0)) ? sum : a;
            assign w[(4 + j)*32 +: 32]  = (xr_en && xr_tgt) ? xo : (add_sel == 2'd3 && ff_row == 2'd1) ? sum : b;
            assign w[(8 + j)*32 +: 32]  = (add_sel == 2'd2 || (add_sel == 2'd3 && ff_row == 2'd2)) ? sum : c;
            assign w[(12 + j)*32 +: 32] = (xr_en && !xr_tgt) ? xo : (add_sel == 2'd3 && ff_row == 2'd3) ? sum : d;
        end
        // P: word (r, j) <- word (r, (r - j) mod 4)
        for (genvar r = 0; r < 4; r++) begin : g_prow
            for (genvar j = 0; j < 4; j++) begin : g_pcol
                localparam int SRC = ((r - j) % 4 + 4) % 4;
                assign vn[(4*r + j)*32 +: 32] = perm ? w[(4*r + SRC)*32 +: 32] : w[(4*r + j)*32 +: 32];
            end
        end
    endgenerate
    logic [511:0] ms;
    generate
        for (genvar j = 0; j < 16; j++) begin : g_sig
            assign ms[j*32 +: 32] = m[SIGMA(j)*32 +: 32];
        end
    endgenerate
    always_ff @(posedge clk) begin
        if (ld) begin
            v <= in_v; m <= in_m;
        end else if (en) begin
            v <= vn;
            if (sigma) m <= ms;
        end
        if (ld) h <= in_h;
    end
    // output: ChaCha20 the state; BLAKE3 the finalisation xors (8 alu_xor of 64 bits = 16 words)
    generate
        for (genvar k = 0; k < 8; k++) begin : g_fx
            logic [63:0] xa, xb, xy;
            assign xa = {v[(2*k + 1)*32 +: 32], v[(2*k)*32 +: 32]};
            if (k < 4) begin : g_lo
                assign xb = blake ? {v[(2*k + 9)*32 +: 32], v[(2*k + 8)*32 +: 32]} : 64'd0;
            end else begin : g_hi
                assign xb = blake ? {h[(2*k - 7)*32 +: 32], h[(2*k - 8)*32 +: 32]} : 64'd0;
            end
            alu_xor u_fx (.a(xa), .b(xb), .y(xy));
            assign out[(2*k)*32 +: 32]     = xy[31:0];
            assign out[(2*k + 1)*32 +: 32] = xy[63:32];
        end
    endgenerate
endmodule
