// mono_pkg.sv - constants of Monolith-31 (width 16) and the elaboration-time functions of the Concrete adder tree.
// ROW: the circulant MDS row (Plonky3 / Monolith paper, Mersenne31 width 16). RC: the five round constants
// (dse/TOP/mono_constants.json). The MDS product y_i = sum_k ROW[k] * x_{(i+k) mod 16} is built from the canonical signed
// digit (CSD) recoding of every ROW[k]: a digit (s, +1) is the term x << s, a digit (s, -1) the term (p - x) << s = (~x) << s
// (x < 2^31, p = 2^31 - 1), so every term is positive and the sum is reduced mod p once at the end (fold).
package mono_pkg;
    localparam int P31W = 31;
    localparam logic [30:0] P31 = 31'h7FFF_FFFF;
    function automatic int ROW(input int k);                    // the circulant MDS row
        case (k)
            0: ROW = 61402;
            1: ROW = 17845;
            2: ROW = 26798;
            3: ROW = 59689;
            4: ROW = 12021;
            5: ROW = 40901;
            6: ROW = 41351;
            7: ROW = 27521;
            8: ROW = 56951;
            9: ROW = 12034;
            10: ROW = 53865;
            11: ROW = 43244;
            12: ROW = 7454;
            13: ROW = 33823;
            14: ROW = 28750;
            15: ROW = 1108;
            default: ROW = 0;
        endcase
    endfunction
    localparam int NSH = 17;                                       // CSD shifts 0..16 (the constants are 16 bits)
    function automatic logic [30:0] RC(input int r, input int i);   // round constant i of round r (0..4)
        case (r * 16 + i)
            0: RC = 31'h3d98fe90;
            1: RC = 31'h14cb3ccb;
            2: RC = 31'h7c0b1f93;
            3: RC = 31'h3b4d56cd;
            4: RC = 31'h03deae45;
            5: RC = 31'h285f40b2;
            6: RC = 31'h676dc2ac;
            7: RC = 31'h0196224e;
            8: RC = 31'h5bac69ca;
            9: RC = 31'h65ee092f;
            10: RC = 31'h3b5d6dfb;
            11: RC = 31'h4fa77b75;
            12: RC = 31'h7a4c68ae;
            13: RC = 31'h1aaa334f;
            14: RC = 31'h6d1012dc;
            15: RC = 31'h2ad9c57e;
            16: RC = 31'h1c46a94c;
            17: RC = 31'h20bbface;
            18: RC = 31'h08624421;
            19: RC = 31'h26524ae0;
            20: RC = 31'h136e2ee2;
            21: RC = 31'h7c6d25ca;
            22: RC = 31'h5531244d;
            23: RC = 31'h200bce3b;
            24: RC = 31'h7b8d385f;
            25: RC = 31'h2a2ce224;
            26: RC = 31'h1cc7e6b9;
            27: RC = 31'h316e341b;
            28: RC = 31'h3c97cc8e;
            29: RC = 31'h08d45359;
            30: RC = 31'h17b576d8;
            31: RC = 31'h02fb1e41;
            32: RC = 31'h35778631;
            33: RC = 31'h23a29605;
            34: RC = 31'h173e09e7;
            35: RC = 31'h41a52825;
            36: RC = 31'h4e98962a;
            37: RC = 31'h74828a97;
            38: RC = 31'h6aa64557;
            39: RC = 31'h1f886887;
            40: RC = 31'h366e5c49;
            41: RC = 31'h65c69913;
            42: RC = 31'h24c3ebda;
            43: RC = 31'h0bbf3f2c;
            44: RC = 31'h465af76d;
            45: RC = 31'h0e644935;
            46: RC = 31'h65584d01;
            47: RC = 31'h68aa622d;
            48: RC = 31'h724dc1f9;
            49: RC = 31'h4aa58253;
            50: RC = 31'h4be9c141;
            51: RC = 31'h0caa81bf;
            52: RC = 31'h4b9cf923;
            53: RC = 31'h53a8ff1e;
            54: RC = 31'h24893eb2;
            55: RC = 31'h3d175171;
            56: RC = 31'h5c33806c;
            57: RC = 31'h68706e51;
            58: RC = 31'h2d262d0a;
            59: RC = 31'h369cc105;
            60: RC = 31'h67abd856;
            61: RC = 31'h3c562a5c;
            62: RC = 31'h4aca8f2e;
            63: RC = 31'h6f36eff3;
            64: RC = 31'h1fe21035;
            65: RC = 31'h76e719ed;
            66: RC = 31'h5f44064b;
            67: RC = 31'h1e74c8c5;
            68: RC = 31'h6f5b4896;
            69: RC = 31'h4738677f;
            70: RC = 31'h1584389a;
            71: RC = 31'h4db0403a;
            72: RC = 31'h141dc716;
            73: RC = 31'h4985b4fd;
            74: RC = 31'h3f138de3;
            75: RC = 31'h5441fa11;
            76: RC = 31'h2fa873d0;
            77: RC = 31'h02dee437;
            78: RC = 31'h4fd16101;
            79: RC = 31'h42372f45;
            default: RC = 31'd0;
        endcase
    endfunction

    // CSD digit of constant c at shift s: -1, 0 or +1 (non-adjacent form, computed from the low bits upwards)
    function automatic int csd_digit(input int c, input int s);
        int n, i, r;
        n = c; csd_digit = 0;
        for (i = 0; i <= s; i++) begin
            if (n & 1) begin
                r = 2 - (n & 3);                                   // +1 when n = 1 mod 4, -1 when n = 3 mod 4
                if (i == s) csd_digit = r;
                n = n - r;
            end
            n = n >> 1;
        end
    endfunction
    // The per-shift tables, evaluated once here (a generate block must not call the digit loops thousands of times):
    //   DIGV: digit of constant k at shift s (2 bits: 0 none, 1 = +1, 2 = -1)    TIDV: position of constant k among the
    //   terms at shift s (5 bits)    NTV: terms at shift s (8 bits)    ADV: adders of one output's tree at shift s (nterm - 1)
    //   OFV: adders of all 16 outputs at the shifts below s (16 bits)
    function automatic logic [16*NSH*2-1:0] mk_dig();
        int k, s, d;
        mk_dig = '0;
        for (k = 0; k < 16; k++) for (s = 0; s < NSH; s++) begin
            d = csd_digit(ROW(k), s);
            mk_dig[(k*NSH + s)*2 +: 2] = (d > 0) ? 2'd1 : (d < 0) ? 2'd2 : 2'd0;
        end
    endfunction
    localparam logic [16*NSH*2-1:0] DIGV = mk_dig();
    function automatic logic [1:0] dig(input int k, input int s);
        dig = DIGV[(k*NSH + s)*2 +: 2];
    endfunction
    function automatic logic [NSH*8-1:0] mk_nt();
        int k, s;
        mk_nt = '0;
        for (s = 0; s < NSH; s++) for (k = 0; k < 16; k++) if (dig(k, s) != 2'd0) mk_nt[s*8 +: 8] = mk_nt[s*8 +: 8] + 8'd1;
    endfunction
    localparam logic [NSH*8-1:0] NTV = mk_nt();
    function automatic int nterm(input int s);
        nterm = NTV[s*8 +: 8];
    endfunction
    function automatic logic [16*NSH*5-1:0] mk_tid();
        int k, s, n;
        mk_tid = '0;
        for (s = 0; s < NSH; s++) begin
            n = 0;
            for (k = 0; k < 16; k++) begin
                mk_tid[(k*NSH + s)*5 +: 5] = n[4:0];
                if (dig(k, s) != 2'd0) n = n + 1;
            end
        end
    endfunction
    localparam logic [16*NSH*5-1:0] TIDV = mk_tid();
    function automatic int tidx(input int s, input int k);
        tidx = TIDV[(k*NSH + s)*5 +: 5];
    endfunction
    function automatic int clog2i(input int n);                    // ceil(log2 n), 0 for n <= 1
        int v;
        clog2i = 0; v = 1;
        while (v < n) begin v = v * 2; clog2i = clog2i + 1; end
    endfunction
    function automatic int grp_adders(input int s);                // adders of one output's tree at shift s
        grp_adders = (nterm(s) > 1) ? nterm(s) - 1 : 0;
    endfunction
    function automatic logic [(NSH+1)*16-1:0] mk_off();
        int s;
        mk_off = '0;
        for (s = 0; s < NSH; s++) mk_off[(s+1)*16 +: 16] = mk_off[s*16 +: 16] + 16 * grp_adders(s);
    endfunction
    localparam logic [(NSH+1)*16-1:0] OFV = mk_off();
    function automatic int grp_off(input int s);                   // adders of all groups s' < s, for all 16 outputs
        grp_off = OFV[s*16 +: 16];
    endfunction
    localparam int NARROW = grp_off(NSH);                          // narrow-tree adders (all outputs, all shifts)
    localparam int NWIDE  = 16 * (NSH - 1);                        // the combine over the 17 shifted group sums, per output
    localparam int NTREE  = NARROW + NWIDE;                        // every adder of the Concrete tree (all >= 32 bits, lendable)
    localparam int WSUM   = 55;                                    // bound of the full sum: 90 terms < 2^31 x 2^16
endpackage
