// cc_block.sv - one ChaCha20 block of the natural ChaCha20 kernel: 16 state words v (rows a b c d, hardware columns 0..3)
// and the 16-word input copy m for the feed-forward. One ARX step per cycle in place on the four columns: 4 additions on
// the adders behind ea / eb / ey (the block has no adders of its own), 4 xor + rotate (16 / 12 / 8 / 7). The diagonal
// half-rounds are column half-rounds on the P-permuted layout: at every half-round end (perm) word (r, j) <- (r, (r - j) mod 4).
module cc_block (
    input  logic            clk,
    input  logic            ld,            // v, m <- in_v
    input  logic            en,            // a step executes this cycle
    input  logic [1:0]      add_sel,       // 0: a + b   2: c + d   3: feed-forward v[row] + m[row]
    input  logic [1:0]      ff_row,
    input  logic            xr_en,
    input  logic            xr_tgt,        // 0: d <- rotl(d ^ a', R)   1: b <- rotl(b ^ c', R)
    input  logic [1:0]      rot_sel,       // 0: 16   1: 12   2: 8   3: 7
    input  logic            perm,
    input  logic [511:0]    in_v,
    output logic [511:0]    out,
    output logic [4*32-1:0] ea,
    output logic [4*32-1:0] eb,
    input  logic [4*32-1:0] ey
);
    logic [511:0] v, m, w, vn;
    function automatic logic [31:0] rotl(input logic [31:0] x, input int n);
        rotl = (x << n) | (x >> (32 - n));
    endfunction
    generate
        for (genvar j = 0; j < 4; j++) begin : g_col
            logic [31:0] a, b, c, d, sum, opa, opb, xi, xo;
            logic [63:0] xx;
            assign a = v[j*32 +: 32];
            assign b = v[(4 + j)*32 +: 32];
            assign c = v[(8 + j)*32 +: 32];
            assign d = v[(12 + j)*32 +: 32];
            assign opa = (add_sel == 2'd2) ? c : (add_sel == 2'd3) ? v[(4*ff_row + j)*32 +: 32] : a;
            assign opb = (add_sel == 2'd0) ? b : (add_sel == 2'd2) ? d : m[(4*ff_row + j)*32 +: 32];
            assign ea[j*32 +: 32] = opa;
            assign eb[j*32 +: 32] = opb;
            assign sum = ey[j*32 +: 32];
            assign xi = xr_tgt ? b : d;
            alu_xor u_xor (.a({32'd0, xi}), .b({32'd0, sum}), .y(xx));
            assign xo = (rot_sel == 2'd0) ? rotl(xx[31:0], 16) : (rot_sel == 2'd1) ? rotl(xx[31:0], 12)
                      : (rot_sel == 2'd2) ? rotl(xx[31:0], 8) : rotl(xx[31:0], 7);
            assign w[j*32 +: 32]        = (add_sel == 2'd0 || (add_sel == 2'd3 && ff_row == 2'd0)) ? sum : a;
            assign w[(4 + j)*32 +: 32]  = (xr_en && xr_tgt) ? xo : (add_sel == 2'd3 && ff_row == 2'd1) ? sum : b;
            assign w[(8 + j)*32 +: 32]  = (add_sel == 2'd2 || (add_sel == 2'd3 && ff_row == 2'd2)) ? sum : c;
            assign w[(12 + j)*32 +: 32] = (xr_en && !xr_tgt) ? xo : (add_sel == 2'd3 && ff_row == 2'd3) ? sum : d;
        end
        for (genvar r = 0; r < 4; r++) begin : g_prow
            for (genvar j = 0; j < 4; j++) begin : g_pcol
                localparam int SRC = ((r - j) % 4 + 4) % 4;
                assign vn[(4*r + j)*32 +: 32] = perm ? w[(4*r + SRC)*32 +: 32] : w[(4*r + j)*32 +: 32];
            end
        end
    endgenerate
    always_ff @(posedge clk) begin
        if (ld) begin v <= in_v; m <= in_v; end
        else if (en) v <= vn;
    end
    assign out = v;
endmodule
