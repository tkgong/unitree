// lane_cap.sv - the result of a finished node from the unit's output lanes (the unpacking of dse/TOP/verify/models.py:
// b3_words / cc_words / mono_words).
//   arx_cap : 18 lanes of a block -> the two 32 B values: Merkle parent = words 0..7 (the chaining value); GGM children =
//             words 0..7 and 8..15. BLAKE3: word 2k, 2k+1 = lane k low / high. ChaCha20: rows a b c from lanes (2,6),
//             (1,5), (0,4) through the P involution, row d from lanes 16, 17.
//   mono_cap: 8 lanes -> the 8 result elements (canonical).
module arx_cap (
    input  logic             blake,
    input  logic [18*64-1:0] lanes,
    output logic [255:0]     out0,
    output logic [255:0]     out1
);
    function automatic logic [31:0] LO(input logic [63:0] v); LO = v[31:0]; endfunction
    function automatic logic [31:0] HI(input logic [63:0] v); HI = v[63:32]; endfunction
    logic [63:0] l [0:17];
    logic [63:0] a0, a1, b0, b1, c0, c1, d0, d1;
    logic [31:0] wb [0:15], wc [0:15];
    always_comb begin
        for (int i = 0; i < 18; i++) l[i] = lanes[i*64 +: 64];
        // _prow(2, lanes[2], lanes[6]) ; _prow(1, lanes[1], lanes[5]) ; _prow(0, lanes[0], lanes[4])
        a0 = {HI(l[2]), LO(l[6])};  a1 = {HI(l[6]), LO(l[2])};
        b0 = {LO(l[1]), HI(l[1])};  b1 = {LO(l[5]), HI(l[5])};
        c0 = {HI(l[4]), LO(l[0])};  c1 = {HI(l[0]), LO(l[4])};
        d0 = l[16]; d1 = l[17];
        wc[0] = LO(a0); wc[1] = HI(a0); wc[2] = LO(a1); wc[3] = HI(a1);
        wc[4] = LO(b0); wc[5] = HI(b0); wc[6] = LO(b1); wc[7] = HI(b1);
        wc[8] = LO(c0); wc[9] = HI(c0); wc[10] = LO(c1); wc[11] = HI(c1);
        wc[12] = LO(d0); wc[13] = HI(d0); wc[14] = LO(d1); wc[15] = HI(d1);
        for (int k = 0; k < 8; k++) begin wb[2*k] = LO(l[k]); wb[2*k + 1] = HI(l[k]); end
        for (int i = 0; i < 8; i++) begin
            out0[i*32 +: 32] = blake ? wb[i] : wc[i];
            out1[i*32 +: 32] = blake ? wb[8 + i] : wc[8 + i];
        end
    end
endmodule

module mono_cap (
    input  logic [8*64-1:0] lanes,
    output logic [255:0]    out0
);
    generate
        for (genvar i = 0; i < 8; i++) begin : g_el
            logic [31:0] v, r;
            logic [30:0] t;
            assign v = lanes[(i/2)*64 + (i%2)*32 +: 32];                   // elements 0..7 = lanes 0..3, low then high word
            assign r = {1'b0, v[30:0]} + {31'd0, v[31]};                  // v mod p for v < 2^32 (one fold, then canon)
            alu_fold31 u_f (.r(r), .t(t));
            alu_canon #(.W(32)) u_c (.t(t), .y(out0[i*32 +: 32]));
        end
    endgenerate
endmodule
