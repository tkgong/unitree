// pe_map.svh - where the Monolith datapath's registers live in its PE's register vector (unit18_shared, mono_dp18 PB > 0);
// included in both modules (Yosys reads no package that refers to another package).
// The PE vector = the level registers of the PE's two ARX block groups: group A (5 blocks) levels 1..6, then group B (4 blocks)
// levels 1..6, each level NBK x 22 lanes x 64 bits.
//  * A lent adder's sum: its register is the ARX lane word that holds the same sum (the same adder output, so no select).
//    With blake = 0 and rg = 0 (the Monolith programs) step s writes the four sums of its block, sum q = EY[q], as:
//      steps 1, 4: lane 16 = {sum1, sum0}, lane 17 = {sum3, sum2}
//      steps 2, 5: lane 0 = {sum1, sum0}, lane 4 = {sum3, sum2} (copy 1, step 2: lane 0 = {sum1, sum2}, lane 4 = {sum3, sum0})
//      steps 3, 6: lane 2 = {sum1, sum0}, lane 6 = {sum3, sum2} (copy 1, step 6: lane 2 = {sum1, sum2}, lane 6 = {sum3, sum0})
//    (RTL/compiler/bind: the ARX steps on symbols). Bits above 31 of a lent sum stay a register of the datapath.
//  * Every other Monolith register: its own free lane u (bits 0..W-1): a lane of the PE vector that is not a sum lane and
//    is not dead (levels 2, 3 lanes 16, 17: written, never read). Lanes in order of group, level, block, lane.
//      u = node id (registers of the adders that are not lent) | NN + rank (first delays) | then the second delays, the
//      third delays, the 41 reductions, xb1 / xb2 / xb3 / br (4 x 16), the 16 K constants, the 16 outputs.
    localparam int PM_NN = kara_pkg::NN;
    localparam int PM_LW = 22 * 64;                           // bits of one block at one level

    // delay-k registers of the nodes before id (a leaf with a life has all three); one table slice per node, no nested
    // calls: Yosys evaluates constant functions slowly
    function automatic integer rank_dly(input integer id, input integer k);
        integer j;
        reg [49:0] t;
        begin
            rank_dly = 0;
            for (j = 0; j < id; j = j + 1) begin
                t = kara_pkg::NODE_TAB[j*50 +: 50];
                if (t[46:42] != 0 && t[49:47] != 5 && (t[49:47] == 2 ? t[4:0] >= 1 : t[4:0] >= k)) rank_dly = rank_dly + 1;
            end
        end
    endfunction
    localparam int N1 = rank_dly(PM_NN, 1);
    localparam int N2 = rank_dly(PM_NN, 2);
    localparam int N3 = rank_dly(PM_NN, 3);
    localparam int U_D1  = PM_NN;
    localparam int U_D2  = U_D1 + N1;
    localparam int U_D3  = U_D2 + N2;
    localparam int U_RQ  = U_D3 + N3;
    localparam int U_XB  = U_RQ + 41;
    localparam int U_KC  = U_XB + 64;
    localparam int U_OUT = U_KC + 16;
    localparam int NU    = U_OUT + 16;                        // free lanes used

    // The excluded lanes (sum lanes, dead lanes) per level: 1, 4: 16 17 | 2: 0 4 16 17 | 3: 2 6 16 17 | 5: 0 4 | 6: 2 6.
    // Closed forms, no loops (Yosys evaluates constant functions slowly).
    function automatic integer nfree(input integer lv);       // free lanes of one block at level lv
        begin
            nfree = (lv == 2 || lv == 3) ? 18 : 20;
        end
    endfunction
    function automatic integer nbelow(input integer lv);      // free lanes of one block at the levels below lv
        begin
            case (lv)
                1: nbelow = 0;   2: nbelow = 20;  3: nbelow = 38;
                4: nbelow = 56;  5: nbelow = 76;  6: nbelow = 96;
                default: nbelow = 116;
            endcase
        end
    endfunction
    function automatic integer fidx(input integer lv, input integer l);       // free index of lane l (-1: excluded)
        begin
            case (lv)
                1, 4: fidx = (l < 16) ? l : (l < 18) ? -1 : l - 2;
                2:    fidx = (l == 0 || l == 4 || l == 16 || l == 17) ? -1 : (l < 4) ? l - 1 : (l < 16) ? l - 2 : l - 4;
                3:    fidx = (l == 2 || l == 6 || l == 16 || l == 17) ? -1 : (l < 2) ? l : (l < 6) ? l - 1 : (l < 16) ? l - 2 : l - 4;
                5:    fidx = (l == 0 || l == 4) ? -1 : (l < 4) ? l - 1 : l - 2;
                default: fidx = (l == 2 || l == 6) ? -1 : (l < 2) ? l : (l < 6) ? l - 1 : l - 2;
            endcase
        end
    endfunction
    function automatic integer flane(input integer lv, input integer k);      // lane of free index k
        begin
            case (lv)
                1, 4: flane = (k < 16) ? k : k + 2;
                2:    flane = (k < 3) ? k + 1 : (k < 14) ? k + 2 : k + 4;
                3:    flane = (k < 2) ? k : (k < 5) ? k + 1 : (k < 14) ? k + 2 : k + 4;
                5:    flane = (k < 3) ? k + 1 : k + 2;
                default: flane = (k < 2) ? k : (k < 5) ? k + 1 : k + 2;
            endcase
        end
    endfunction
    function automatic integer lane_pos(input integer u);    // first bit of free lane u in the PE vector
        integer g, nb, r, lv, rr;
        begin
            g  = (u < 5 * 116) ? 0 : 1;
            nb = (g == 0) ? 5 : 4;
            r  = (g == 0) ? u : u - 5 * 116;
            lv = (r < nb * 20) ? 1 : (r < nb * 38) ? 2 : (r < nb * 56) ? 3 : (r < nb * 76) ? 4 : (r < nb * 96) ? 5 : 6;
            rr = r - nb * nbelow(lv);
            lane_pos = g * 6 * 5 * PM_LW + (lv - 1) * nb * PM_LW + ((rr / nfree(lv)) * 22 + flane(lv, rr % nfree(lv))) * 64;
        end
    endfunction
    function automatic integer lane_u(input integer g, input integer lv, input integer b, input integer l);  // inverse:
        integer nb, k;                                         // the free lane u of group g, level lv, block b, lane l
        begin                                                  // (-1: a sum / dead lane, or no register on it)
            nb = (g == 0) ? 5 : 4;
            k  = fidx(lv, l);
            lane_u = (k < 0) ? -1 : g * 5 * 116 + nb * nbelow(lv) + b * nfree(lv) + k;
            if (lane_u >= NU) lane_u = -1;
        end
    endfunction
    function automatic integer twin_pos(input integer ld, input integer cp);  // first bit of lent sum ld's lane word
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
