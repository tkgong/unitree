// pe_map.svh - where the Monolith datapath's registers live in its PE's register vector (unit18_shared, mono_dp18 PB > 0);
// included in both modules (Yosys reads no package that refers to another package).
// The PE vector = the level registers of the PE's two ARX block groups: group A (5 blocks) levels 1..6, then group B (4 blocks)
// levels 1..6, each level NBK x 22 lanes x 64 bits. In the Monolith programs (blake = 0, rg = 0; RTL/compiler/bind):
//  * step s writes its four sums (sum q = EY[q]) to lanes 16 / 17 (steps 1, 4), 0 / 4 (steps 2, 5), 2 / 6 (steps 3, 6)
//    ({sum1, sum0}, {sum3, sum2}; copy 1, steps 2 and 6: {sum1, sum2}, {sum3, sum0}): a lent adder's sum register is that
//    lane word (the same adder output: no select). Bits above 31 of a lent sum stay a register of the datapath.
//  * lanes 8..15 and 18..21 pass unchanged at every step: a chain register -> its delays sits in lane 8..15, 18 or 19,
//    the head at level 1 (selected), the delays at levels 2, 3 (the ARX pass: the same value, no select). Chains: the
//    private adders with delays (q, d1[, d2]), the leaves with delays (q1, q2, q3), xb1 -> xb2 -> xb3 (3 levels at most).
//    10 chain columns per block.
//  * every other register is selected on a generic lane: a lane the ARX step of its level does not write in any program
//    (wmask), so that the select sits after a register-to-register ARX path (timing):
//      level 1, 2: 20 21 | 3: 0 3 4 7 20 21 | 4: 8..15 18..21 | 5: 1 2 5 6 16 17 8..15 18..21 | 6: 16..21
//    (46 per block; no sum lane, no dead lane, no chain cell).
//      generic slots: private adders without delays | delays of the lent adders (d1, then d2, then d3) | the 41 reductions |
//      br (16) | the 16 K constants | the 16 outputs | the 15 squarer outputs | the 15 squarer first stages (4 slots
//      each); then the chain heads.
    localparam int PM_NN = kara_pkg::NN;
    localparam int PM_LW = 22 * 64;                           // bits of one block at one level

    // ranks(sel, k)[id*10 +: 10]: how many nodes before id are of kind sel (entry PM_NN: all of them); one pass over the
    // table per kind (Yosys evaluates constant functions slowly):
    //   0 private adder without delay | 1 private adder with delays | 2 leaf with delays | 3 lent adder with a k-th delay
    function automatic [(PM_NN+1)*10-1:0] ranks(input integer sel, input integer k);
        integer j, n;
        reg [49:0] t;
        reg add, lent, hit;
        begin
            n = 0;
            ranks = '0;
            for (j = 0; j < PM_NN; j = j + 1) begin
                ranks[j*10 +: 10] = n;
                t = kara_pkg::NODE_TAB[j*50 +: 50];
                add  = t[46:42] != 0 && t[49:47] != 2 && t[49:47] != 5;
                lent = t[13:5] < 216;
                case (sel)
                    0: hit = add && !lent && t[4:0] == 0;
                    1: hit = add && !lent && t[4:0] >= 1;
                    2: hit = t[46:42] != 0 && t[49:47] == 2 && t[4:0] >= 1;
                    default: hit = add && lent && t[4:0] >= k;
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
    localparam int V_SQ  = V_OUT + 16;                        // squarer i = 1..15: output at V_SQ + i - 1,
    localparam int V_S1  = V_SQ + 15;                         // first stage (233 bits) at V_S1 + 4 (i - 1) + 0..3
    localparam int NV    = V_S1 + 60;
    localparam int C_LF  = NPA;                               // chains
    localparam int C_XB  = C_LF + NLF;
    localparam int NC    = C_XB + 16;
    localparam int NS    = NV + NC;                           // selected slots: generic lanes, then the chain heads

    // generic lanes (closed forms, no loops)
    function automatic integer gfree(input integer lv);       // generic lanes of one block at level lv: 2 2 6 12 18 6
        begin
            case (lv)
                1, 2: gfree = 2;  3: gfree = 6;  4: gfree = 12;  5: gfree = 18;
                default: gfree = 6;
            endcase
        end
    endfunction
    function automatic integer gbelow(input integer lv);      // generic lanes of one block at the levels below lv
        begin
            case (lv)
                1: gbelow = 0;   2: gbelow = 2;   3: gbelow = 4;
                4: gbelow = 10;  5: gbelow = 22;  6: gbelow = 40;
                default: gbelow = 46;
            endcase
        end
    endfunction
    function automatic integer gidx(input integer lv, input integer l);       // generic index of lane l (-1: none)
        begin
            case (lv)
                1, 2: gidx = (l >= 20) ? l - 20 : -1;
                3:    gidx = (l == 0) ? 0 : (l == 3) ? 1 : (l == 4) ? 2 : (l == 7) ? 3 : (l >= 20) ? l - 16 : -1;
                4:    gidx = (l >= 8 && l <= 15) ? l - 8 : (l >= 18) ? l - 10 : -1;
                5:    gidx = (l == 1 || l == 2) ? l - 1 : (l == 5 || l == 6) ? l - 3 : (l == 16 || l == 17) ? l - 12 :
                             (l >= 8 && l <= 15) ? l - 2 : (l >= 18) ? l - 4 : -1;
                default: gidx = (l >= 16) ? l - 16 : -1;
            endcase
        end
    endfunction
    function automatic integer glane(input integer lv, input integer k);      // lane of generic index k
        begin
            case (lv)
                1, 2: glane = k + 20;
                3:    glane = (k == 0) ? 0 : (k == 1) ? 3 : (k == 2) ? 4 : (k == 3) ? 7 : k + 16;
                4:    glane = (k < 8) ? k + 8 : k + 10;
                5:    glane = (k < 2) ? k + 1 : (k < 4) ? k + 3 : (k < 6) ? k + 12 : (k < 14) ? k + 2 : k + 4;
                default: glane = k + 16;
            endcase
        end
    endfunction
    function automatic integer gpos(input integer v);         // first bit of generic slot v in the PE vector
        integer g, nb, r, lv, rr;
        begin
            g  = (v < 5 * 46) ? 0 : 1;
            nb = (g == 0) ? 5 : 4;
            r  = (g == 0) ? v : v - 5 * 46;
            lv = (r < nb * 2) ? 1 : (r < nb * 4) ? 2 : (r < nb * 10) ? 3 : (r < nb * 22) ? 4 : (r < nb * 40) ? 5 : 6;
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
            if (k >= 0) begin
                v = g * 5 * 46 + nb * gbelow(lv) + b * gfree(lv) + k;
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
            if (cp == 1 && (s == 2 || s == 6) && (w == 0 || w == 2)) w = 2 - w;   // the lo words of the two lanes swap
            lane  = (s == 1 || s == 4) ? 16 : (s == 2 || s == 5) ? 0 : 2;
            if (w >= 2) lane = lane + ((s == 1 || s == 4) ? 1 : 4);
            half  = w % 2;
            twin_pos = gbase + (s - 1) * nb * PM_LW + (b * 22 + lane) * 64 + half * 32;
        end
    endfunction
