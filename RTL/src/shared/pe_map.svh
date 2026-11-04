// pe_map.svh - where the Monolith datapath's registers live in its PE's register vector (unit18_shared, mono_dp18 PB > 0);
// included in both modules (Yosys reads no package that refers to another package).
// The PE vector = the level registers of the PE's two ARX block groups: group A (5 blocks) levels 1..6, then group B (4 blocks)
// levels 1..6, each level NBK x 22 lanes x 64 bits. In the Monolith programs (the ARX controls of BLAKE3: blake = 1, rg = 0;
// RTL/compiler/bind):
//  * step s writes its four sums (sum q = EY[q]) to lanes 16 / 17 (steps 1, 4), 0 / 4 (steps 2, 5), 2 / 6 (steps 3, 6)
//    ({sum1, sum0}, {sum3, sum2}; step 6: {sum1, sum2}, {sum3, sum0}): a lent adder's sum register is that lane word
//    (the same adder output: no select). Bits above 31 of a lent sum stay a register of the datapath.
//  * lanes 8..15 and 18..21 pass unchanged at every step: a chain register -> its delays sits in lane 8..15, 18 or 19,
//    the head at level 1 (selected), the delays at levels 2, 3 (the ARX pass: the same value, no select). Chains: the
//    private adders with delays (q, d1[, d2]), the leaves with delays (q1, q2, q3), xb1 -> xb2 -> xb3 (3 levels at most).
//    10 chain columns per block.
//  * a lent sum's delays: where the ARX steps after the sum's step only move its word into a register the ARX reads
//    (lfree / ldpos: step 2, 3, 4 sums two delays, step 1, 5 sums one), a delay is that lane word (no select); the bits
//    above 31 stay registers of the datapath. The ARX adder of step 2 / 5 reads the sum of step 1 / 4 (lane 16 / 17), of
//    step 5 / 6 the sum of step 2 / 3 two levels on: the lend binding (kara_pkg LEND_TAB) puts Monolith adders that read
//    each other so, and that operand needs no lend select (mono_dp18).
//  * every other register is selected on a generic lane: a lane whose ARX value in no program is an XOR of a sum of the
//    same step (the select sits after an ARX path without the add -> XOR depth: timing), no sum lane, no lane holding a
//    lent delay, no chain cell:
//      level 2: 1 5 20 21 | 3: 3 7 20 21 | 4: 3 7..15 18..21 | 5: 1 5 8..15 18..21 | 6: 18..21 (40 per block;
//      level 6 lane 7: copy 0's ChaCha20 step 6 writes B' there in the shared layout, axn_step.sv LAY = 1;
//      level 1 holds the clean slots and the chain heads, levels 2 / 5 lanes 2 / 6 the operand lanes)
//      generic slots: private adders without delays | the lent delays that are not free (d1, then d2, then d3) | the 41
//      reductions | br (16) | the 16 K constants | the 16 outputs | the first stage's 4th slot of squarers 13..15 | the
//      packed slots (the bits above 31 of the lent sums and their delays, the state's r); then the chain heads; then the
//      clean slots (the squarers, below).
//  * the chain heads of xb1 (the state after Bars, from the datapath's input lanes: 0 in the ARX programs) and the clean
//    slots are written mn | an (no select, unit18_shared).
    localparam int PM_NN = kara_pkg::NN;
    localparam int PM_LW = 22 * 64;                           // bits of one block at one level

    // ranks(sel, k)[id*10 +: 10]: how many nodes before id are of kind sel (entry PM_NN: all of them); one pass over the
    // table per kind (Yosys evaluates constant functions slowly):
    //   0 private adder without delay | 1 private adder with delays | 2 leaf with delays | 3 lent adder with a k-th delay
    function automatic [(PM_NN+1)*10-1:0] ranks(input integer sel, input integer k);
        integer j, n, ld, s;
        reg [49:0] t;
        reg add, lent, hit, free;
        begin
            n = 0;
            ranks = '0;
            for (j = 0; j < PM_NN; j = j + 1) begin
                ranks[j*10 +: 10] = n;
                t = kara_pkg::NODE_TAB[j*50 +: 50];
                add  = t[46:42] != 0 && t[49:47] != 2 && t[49:47] != 5;
                ld   = kara_pkg::LEND_TAB[j*11 +: 9];
                lent = ld < 216;
                s    = (ld < 120) ? ld / 20 + 1 : (ld - 120) / 16 + 1;
                free = (k == 1 && s != 6) || (k == 2 && s >= 2 && s <= 4);    // = lfree(ld, k)
                case (sel)
                    0: hit = add && !lent && t[4:0] == 0;
                    1: hit = add && !lent && t[4:0] >= 1;
                    2: hit = t[46:42] != 0 && t[49:47] == 2 && t[4:0] >= 1;
                    default: hit = add && lent && t[4:0] >= k && !free;
                endcase
                if (hit) n = n + 1;
            end
            ranks[PM_NN*10 +: 10] = n;
        end
    endfunction
    localparam logic [(PM_NN+1)*10-1:0] R_PN  = ranks(0, 0);
    localparam logic [(PM_NN+1)*10-1:0] R_PA  = ranks(1, 0);
    localparam logic [(PM_NN+1)*10-1:0] R_LF  = ranks(2, 0);
    localparam logic [(PM_NN+1)*10-1:0] R_LD1 = ranks(3, 1);
    localparam logic [(PM_NN+1)*10-1:0] R_LD2 = ranks(3, 2);
    localparam logic [(PM_NN+1)*10-1:0] R_LD3 = ranks(3, 3);
    localparam int NPN  = R_PN[PM_NN*10 +: 10];
    localparam int NPA  = R_PA[PM_NN*10 +: 10];
    localparam int NLF  = R_LF[PM_NN*10 +: 10];
    localparam int NLD1 = R_LD1[PM_NN*10 +: 10];
    localparam int NLD2 = R_LD2[PM_NN*10 +: 10];
    localparam int NLD3 = R_LD3[PM_NN*10 +: 10];
    localparam int V_LD1 = NPN;                               // generic slots
    localparam int V_LD2 = V_LD1 + NLD1;
    localparam int V_LD3 = V_LD2 + NLD2;
    localparam int V_RQ  = V_LD3 + NLD3;
    localparam int V_BR  = V_RQ + 41;
    localparam int V_KC  = V_BR + 16;
    localparam int V_OUT = V_KC + 16;
    localparam int V_S4  = V_OUT + 16;                        // squarers 13..15: the first stage's 4th slot (the rest: clean slots)
    // packed slots (bit fields, several registers per slot): the bits above 31 of each lent sum and of its moved delays
    // (R_HI: first bit of node id's fields), then the state's r at levels 1..RRN (9 bits each)
    function automatic [(PM_NN+1)*12-1:0] hranks(input integer dummy);
        integer j, n, ld, s, nd, w;
        reg [49:0] t;
        begin
            n = 0;
            hranks = '0;
            for (j = 0; j < PM_NN; j = j + 1) begin
                hranks[j*12 +: 12] = n;
                t  = kara_pkg::NODE_TAB[j*50 +: 50];
                ld = kara_pkg::LEND_TAB[j*11 +: 9];
                w  = t[41:36];
                if (ld < 216 && w > 32 && t[46:42] != 0 && t[49:47] != 2 && t[49:47] != 5) begin
                    s  = (ld < 120) ? ld / 20 + 1 : (ld - 120) / 16 + 1;
                    nd = ((t[4:0] >= 1 && s != 6) ? 1 : 0) + ((t[4:0] >= 2 && s >= 2 && s <= 4) ? 1 : 0);   // lfree
                    n  = n + (w - 32) * (1 + nd);
                end
            end
            hranks[PM_NN*12 +: 12] = n;
        end
    endfunction
    function automatic integer kclast(input integer dummy);   // the last level that reads a K constant
        integer j;
        reg [49:0] t;
        begin
            kclast = 0;
            for (j = 0; j < PM_NN; j = j + 1) begin
                t = kara_pkg::NODE_TAB[j*50 +: 50];
                if (t[46:42] != 0 && t[49:47] != 0 && t[49:47] != 2 && t[49:47] != 5 &&
                    kara_pkg::NODE_TAB[t[35:26]*50 + 47 +: 3] == 5 && t[46:42] > kclast) kclast = t[46:42];
            end
        end
    endfunction
    localparam logic [(PM_NN+1)*12-1:0] R_HI = hranks(0);
    localparam int NHB   = R_HI[PM_NN*12 +: 12];
    localparam int RRN   = kclast(0) - 2;                     // r at levels 1..RRN (the K constants read r two levels early)
    localparam int V_PK  = V_S4 + 3;
    localparam int NPK   = (NHB + 9 * RRN + 63) / 64;
    localparam int NV    = V_PK + NPK;
    localparam int C_LF  = NPA;                               // chains
    localparam int C_XB  = C_LF + NLF;
    localparam int NC    = C_XB + 16;
    localparam int NCL   = 72;                                // clean slots (level 1, 8 lanes per block)
    localparam int CL0   = NV + NC;
    localparam int OP0   = NV + NC + NCL;                     // operand lanes: 36 per PE (kara_pkg OPW_TAB)
    localparam int NS    = OP0 + 36;                          // slots: generic lanes, chain heads, clean slots, operand lanes

    // operand lanes: level 2 / 5, lanes 2 / 6 of every block (the a operands of the ARX adds of step 3 / 6). Lane
    // oi = (group A: 0, B: 20) + 4 block + 2 (level 5) + (lane 6); word ow = 2 oi + half holds the register of a reduction
    // (OPW_TAB), rotated so that the word is the CSD leaf the lent adder at that position reads (no lend select). The
    // unused words select nothing (a step-3 sum's second delay is the ARX move into its level-5 word).
    function automatic integer op_lane(input integer g, input integer lv, input integer b, input integer l);
        begin
            op_lane = ((lv == 2 || lv == 5) && (l == 2 || l == 6)) ? (g == 0 ? 0 : 20) + 4 * b + (lv == 5 ? 2 : 0) + (l == 6 ? 1 : 0) : -1;
        end
    endfunction
    function automatic integer opos(input integer ow);        // first bit of operand word ow
        integer oi, g, r, nb;
        begin
            oi   = ow / 2;
            g    = (oi < 20) ? 0 : 1;
            nb   = (g == 0) ? 5 : 4;
            r    = (g == 0) ? oi : oi - 20;
            opos = g * 6 * 5 * PM_LW + ((r % 4 >= 2) ? 4 : 1) * nb * PM_LW + ((r / 4) * 22 + ((r % 2 == 1) ? 6 : 2)) * 64 + (ow % 2) * 32;
        end
    endfunction
    function automatic integer rq_word(input integer m);      // the operand word of reduction m (-1: a generic slot)
        integer ow;
        reg [11:0] e;
        begin
            rq_word = -1;
            for (ow = 0; ow < 72; ow = ow + 1) begin
                e = kara_pkg::OPW_TAB[ow*12 +: 12];
                if (e[11] && e[10:5] == m) rq_word = ow;
            end
        end
    endfunction

    // clean slots: the level-1 lanes whose ARX value in a Monolith program is 0 (the step-1 lane of an input lane, and the
    // Monolith programs drive 0 on the block lanes) and that no ARX program writes with an add -> XOR: 0 2 4 6 20 21 and
    // 3 7 (copy 0) / 1 5 (copy 1). A register there whose Monolith value is 0 in the ARX programs (the squarers: their
    // input is gated by the state's valid bit, and the output by the enable) is written mn | an: an OR, no select.
    // Clean slot k: group k < 40 ? 0 : 1, block (k mod 40) / 8, lane clane((k mod 40) % 8). Squarer i = 1..15: output at
    // k = i - 1, first-stage slots 0..2 at 15 + 3 (i - 1) + j, slot 3 at 60 + i - 1 (i <= 12; 13..15: generic V_S4).
    function automatic integer clane(input integer j, input integer cp);
        begin
            clane = (j < 4) ? 2 * j : (j < 6) ? j + 16 : (cp == 0) ? ((j == 6) ? 3 : 7) : ((j == 6) ? 1 : 5);
        end
    endfunction
    function automatic integer clpos(input integer k, input integer cp);       // first bit of clean slot k
        integer g, r;
        begin
            g = (k < 40) ? 0 : 1;
            r = (g == 0) ? k : k - 40;
            clpos = g * 6 * 5 * PM_LW + ((r / 8) * 22 + clane(r % 8, cp)) * 64;
        end
    endfunction
    function automatic integer lane_clean(input integer g, input integer lv, input integer b, input integer l, input integer cp);
        integer j;
        begin
            lane_clean = -1;
            if (lv == 1)
                for (j = 0; j < 8; j = j + 1)
                    if (clane(j, cp) == l) lane_clean = (g == 0 ? 0 : 40) + b * 8 + j;
        end
    endfunction
    function automatic integer sq_clean(input integer i, input integer j);    // squarer i: clean slot of output (j = -1)
        begin                                                                  // / first-stage slot j (-1: generic)
            if (j < 0) sq_clean = i - 1;
            else if (j < 3) sq_clean = 15 + 3 * (i - 1) + j;
            else if (i <= 12) sq_clean = 60 + i - 1;
            else sq_clean = -1;
        end
    endfunction

    // generic lanes (closed forms, no loops); level 1 holds the clean slots and the chain heads only
    function automatic integer gfree(input integer lv);       // generic lanes of one block at level lv: 0 4 4 14 14 4
        begin
            case (lv)
                1: gfree = 0;  2, 3: gfree = 4;  4, 5: gfree = 14;
                default: gfree = 4;
            endcase
        end
    endfunction
    function automatic integer gbelow(input integer lv);      // generic lanes of one block at the levels below lv
        begin
            case (lv)
                1, 2: gbelow = 0;  3: gbelow = 4;
                4: gbelow = 8;  5: gbelow = 22;  6: gbelow = 36;
                default: gbelow = 40;
            endcase
        end
    endfunction
    function automatic integer gidx(input integer lv, input integer l);       // generic index of lane l (-1: none)
        begin
            case (lv)
                1:    gidx = -1;
                2:    gidx = (l == 1) ? 0 : (l == 5) ? 1 : (l >= 20) ? l - 18 : -1;
                3:    gidx = (l == 3) ? 0 : (l == 7) ? 1 : (l >= 20) ? l - 18 : -1;
                4:    gidx = (l == 3) ? 0 : (l >= 7 && l <= 15) ? l - 6 : (l >= 18) ? l - 8 : -1;
                5:    gidx = (l == 1) ? 0 : (l == 5) ? 1 : (l >= 8 && l <= 15) ? l - 6 : (l >= 18) ? l - 8 : -1;
                default: gidx = (l >= 18) ? l - 18 : -1;
            endcase
        end
    endfunction
    function automatic integer glane(input integer lv, input integer k);      // lane of generic index k
        begin
            case (lv)
                1:    glane = (k < 4) ? 2 * k : k + 16;
                2:    glane = (k == 0) ? 1 : (k == 1) ? 5 : k + 18;
                3:    glane = (k == 0) ? 3 : (k == 1) ? 7 : k + 18;
                4:    glane = (k == 0) ? 3 : (k < 10) ? k + 6 : k + 8;
                5:    glane = (k == 0) ? 1 : (k == 1) ? 5 : (k < 10) ? k + 6 : k + 8;
                default: glane = k + 18;
            endcase
        end
    endfunction
    function automatic integer gpos(input integer v);         // first bit of generic slot v in the PE vector
        integer g, nb, r, lv, rr;
        begin
            g  = (v < 5 * 40) ? 0 : 1;
            nb = (g == 0) ? 5 : 4;
            r  = (g == 0) ? v : v - 5 * 40;
            lv = (r < nb * 4) ? 2 : (r < nb * 8) ? 3 : (r < nb * 22) ? 4 : (r < nb * 36) ? 5 : 6;
            rr = r - nb * gbelow(lv);
            gpos = g * 6 * 5 * PM_LW + (lv - 1) * nb * PM_LW + ((rr / gfree(lv)) * 22 + glane(lv, rr % gfree(lv))) * 64;
        end
    endfunction
    // chain columns: lanes 8..15, 18, 19 of every block (levels 1..3), column c = (group, block, lane)
    function automatic integer chidx(input integer l);        // chain lane index of lane l (-1: none)
        begin
            chidx = (l >= 8 && l <= 15) ? l - 8 : (l == 18 || l == 19) ? l - 10 : -1;
        end
    endfunction
    function automatic integer cpos(input integer c, input integer k);        // first bit of chain c's register k
        integer g, nb, r;                                                      // (k = 0: the head at level 1)
        begin
            g  = (c < 5 * 10) ? 0 : 1;
            nb = (g == 0) ? 5 : 4;
            r  = (g == 0) ? c : c - 5 * 10;
            cpos = g * 6 * 5 * PM_LW + k * nb * PM_LW + ((r / 10) * 22 + ((r % 10) < 8 ? (r % 10) + 8 : (r % 10) + 10)) * 64;
        end
    endfunction
    // the selected slot of group g, level lv, block b, lane l (-1: the ARX value only)
    function automatic integer lane_slot(input integer g, input integer lv, input integer b, input integer l);
        integer nb, k, v;
        begin
            nb = (g == 0) ? 5 : 4;
            k  = gidx(lv, l);
            lane_slot = -1;
            if (op_lane(g, lv, b, l) >= 0) begin
                lane_slot = OP0 + op_lane(g, lv, b, l);
            end else if (k >= 0) begin
                v = g * 5 * 40 + nb * gbelow(lv) + b * gfree(lv) + k;
                if (v < NV) lane_slot = v;
            end else if (lv == 1 && chidx(l) >= 0) begin
                v = g * 5 * 10 + b * 10 + chidx(l);
                if (v < NC) lane_slot = NV + v;
            end
        end
    endfunction
    // the lane word of lent sum ld (block-group copy cp)
    function automatic integer twin_pos(input integer ld, input integer cp);
        integer nb, gbase, q, s, b, w, lane, half;
        begin
            nb    = (ld < 120) ? 5 : 4;
            gbase = (ld < 120) ? 0 : 6 * 5 * PM_LW;
            q     = (ld < 120) ? ld : ld - 120;
            s     = q / (4 * nb) + 1;
            b     = (q / 4) % nb;
            w     = q % 4;                                    // sum w = EY[w]
            if (s == 6 && (w == 0 || w == 2)) w = 2 - w;      // step 6: the lo words of the two lanes swap
            lane  = (s == 1 || s == 4) ? 16 : (s == 2 || s == 5) ? 0 : 2;
            if (w >= 2) lane = lane + ((s == 1 || s == 4) ? 1 : 4);
            half  = w % 2;
            twin_pos = gbase + (s - 1) * nb * PM_LW + (b * 22 + lane) * 64 + half * 32;
        end
    endfunction
    // delay k of lent sum ld is free when the next ARX steps only move the sum's word into a register the ARX reads (the
    // step ld's sum is in: 1..6): step 1 -> level 2 lanes 16 / 17 (read by step 2; level 3 lanes 16 / 17 no ARX program
    // reads: synthesis removes them in the ARX unit, and a flip-flop kept for the Monolith only costs more than a select);
    // steps 2, 3, 4 -> two levels on (lanes 0 / 4, 2 / 6, 16 / 17 pass); step 5 -> step 6 (lanes 0 / 4, the hi words cross)
    function automatic integer lfree(input integer ld, input integer k);
        integer s;
        begin
            s     = (ld < 120) ? ld / 20 + 1 : (ld - 120) / 16 + 1;
            lfree = ((k == 1 && s != 6) || (k == 2 && s >= 2 && s <= 4)) ? 1 : 0;
        end
    endfunction
    // the lane word holding delay k of lent sum ld (lfree(ld, k)): the sum's own word k levels on, but after step 6 the hi
    // words of lanes 0 / 4 cross
    function automatic integer ldpos(input integer ld, input integer cp, input integer k);
        integer nb, gbase, q, s, b, w, lane, half, l2;
        begin
            nb    = (ld < 120) ? 5 : 4;
            gbase = (ld < 120) ? 0 : 6 * 5 * PM_LW;
            q     = (ld < 120) ? ld : ld - 120;
            s     = q / (4 * nb) + 1;
            b     = (q / 4) % nb;
            w     = q % 4;
            lane  = (s == 1 || s == 4) ? 16 : (s == 2 || s == 5) ? 0 : 2;
            if (w >= 2) lane = lane + ((s == 1 || s == 4) ? 1 : 4);
            half  = w % 2;
            l2    = (s == 5 && half == 1) ? 4 - lane : lane;
            ldpos = gbase + (s - 1 + k) * nb * PM_LW + (b * 22 + l2) * 64 + half * 32;
        end
    endfunction
