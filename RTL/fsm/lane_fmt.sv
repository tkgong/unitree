// lane_fmt.sv - the input lanes of one node issue, built from the SRAM values and the node descriptor (the lane packing
// of dse/TOP/verify/models.py: b3_lanes / cc_lanes / mono_lanes). One 32 B slot value = 8 words, word w at bits 32w.
//   arx_fmt : one ARX block (22 lanes of 64 bits). Merkle (kind 0): BLAKE3 parent compress(IV, l || r, PARENT [| ROOT]).
//             GGM (kind 1): BLAKE3-XOF node compress(seed, [idx, idx >> 32, level, 0..], KEYED | START | END | ROOT) when
//             blake, else the ChaCha20 block Block(CC | seed | idx, idx >> 32, level, 0).
//   mono_fmt: one Monolith-31 state (8 lanes): the 16 elements l || r, two per lane.
module arx_fmt (
    input  logic         blake,
    input  logic         kind,          // 0 Merkle parent, 1 GGM node
    input  logic         root,
    input  logic [255:0] va,            // Merkle: left child; GGM: the seed
    input  logic [255:0] vb,            // Merkle: right child
    input  logic [31:0]  idx,
    input  logic [4:0]   level,
    output logic [22*64-1:0] lanes
);
    localparam logic [8*32-1:0] IVP = {32'h5BE0CD19, 32'h1F83D9AB, 32'h9B05688C, 32'h510E527F, 32'hA54FF53A, 32'h3C6EF372, 32'hBB67AE85, 32'h6A09E667};
    localparam logic [4*32-1:0] CCP = {32'h6B206574, 32'h79622D32, 32'h3320646E, 32'h61707865};
    function automatic int CP(input int i); CP = (i < 4) ? 2 * i : 2 * (i - 4) + 1; endfunction   // lane i holds words 2 CP(i), 2 CP(i) + 1
    logic [31:0] v [0:15], m [0:15], h [0:7], w [0:15];
    logic [31:0] flags;
    assign flags = kind ? 32'd27 : (root ? 32'd12 : 32'd4);      // KEYED|START|END|ROOT = 16+1+2+8 ; PARENT [| ROOT]
    always_comb begin
        for (int i = 0; i < 8; i++) begin
            h[i] = kind ? va[i*32 +: 32] : IVP[i*32 +: 32];
            v[i] = h[i];
        end
        for (int i = 0; i < 4; i++) v[8 + i] = IVP[i*32 +: 32];
        v[12] = 32'd0; v[13] = 32'd0; v[14] = 32'd64; v[15] = flags;
        for (int i = 0; i < 16; i++) m[i] = 32'd0;
        if (kind) begin m[0] = idx; m[1] = 32'd0; m[2] = {27'd0, level}; end
        else for (int i = 0; i < 8; i++) begin m[i] = va[i*32 +: 32]; m[8 + i] = vb[i*32 +: 32]; end
        // ChaCha20 words: constants, seed, counter / nonce
        for (int i = 0; i < 4; i++) w[i] = CCP[i*32 +: 32];
        for (int i = 0; i < 8; i++) w[4 + i] = va[i*32 +: 32];
        w[12] = idx; w[13] = 32'd0; w[14] = {27'd0, level}; w[15] = 32'd0;
    end
    logic [22*64-1:0] lb, lc;
    always_comb begin
        lb = '0; lc = '0;
        for (int i = 0; i < 8; i++) begin
            lb[i*64 +: 64] = {v[2*CP(i) + 1], v[2*CP(i)]};
            lc[i*64 +: 64] = {w[2*CP(i) + 1], w[2*CP(i)]};
        end
        lb[8*64 +: 64]  = {m[2], m[0]};   lb[9*64 +: 64]  = {m[3], m[1]};   lb[10*64 +: 64] = {m[6], m[4]};   lb[11*64 +: 64] = {m[7], m[5]};
        lb[12*64 +: 64] = {m[14], m[8]};  lb[13*64 +: 64] = {m[15], m[9]};  lb[14*64 +: 64] = {m[10], m[12]}; lb[15*64 +: 64] = {m[11], m[13]};
        for (int i = 0; i < 4; i++) lb[(18 + i)*64 +: 64] = {h[2*i + 1], h[2*i]};
        // ChaCha: the input copy rows a0 b0 a1 b1 c0 d0 c1 d1 in lanes 8..15
        lc[8*64 +: 64]  = {w[1], w[0]};   lc[9*64 +: 64]  = {w[5], w[4]};   lc[10*64 +: 64] = {w[3], w[2]};   lc[11*64 +: 64] = {w[7], w[6]};
        lc[12*64 +: 64] = {w[9], w[8]};   lc[13*64 +: 64] = {w[13], w[12]}; lc[14*64 +: 64] = {w[11], w[10]}; lc[15*64 +: 64] = {w[15], w[14]};
    end
    assign lanes = (kind && !blake) ? lc : lb;
endmodule

module mono_fmt (
    input  logic [255:0] va,
    input  logic [255:0] vb,
    output logic [8*64-1:0] lanes
);
    assign lanes = {vb, va};                                      // lane k = elements 2k (low) and 2k+1 (high)
endmodule
