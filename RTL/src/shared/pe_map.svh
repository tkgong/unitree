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

    function automatic integer fld(input integer id, input integer hi, input integer lo);
        reg [49:0] t;
        begin
            t = kara_pkg::NODE_TAB[id*50 +: 50];
            fld = (t >> lo) & ((1 << (hi - lo + 1)) - 1);
        end
    endfunction
    function automatic integer is_add(input integer id);      // bank / pre / tree / post adder
        begin
            is_add = fld(id, 46, 42) != 0 && fld(id, 49, 47) != 2 && fld(id, 49, 47) != 5;
        end
    endfunction
    function automatic integer has_dly(input integer id, input integer k);   // node id has a k-th delay register
        begin
            if (fld(id, 46, 42) == 0 || fld(id, 49, 47) == 5) has_dly = 0;
            else if (fld(id, 49, 47) == 2) has_dly = fld(id, 4, 0) >= 1;     // a leaf with a life has all three
            else has_dly = fld(id, 4, 0) >= k;
        end
    endfunction
    function automatic integer rank_dly(input integer id, input integer k);  // delay-k registers of the nodes before id
        integer j;
        begin
            rank_dly = 0;
            for (j = 0; j < id; j = j + 1) rank_dly = rank_dly + has_dly(j, k);
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

    function automatic integer excl(input integer lv, input integer lane);    // a sum lane or a dead lane
        begin
            case (lv)
                1, 4:    excl = (lane == 16 || lane == 17);
                2:       excl = (lane == 0 || lane == 4 || lane == 16 || lane == 17);
                3:       excl = (lane == 2 || lane == 6 || lane == 16 || lane == 17);
                5:       excl = (lane == 0 || lane == 4);
                default: excl = (lane == 2 || lane == 6);
            endcase
        end
    endfunction
    function automatic integer nfree(input integer lv);       // free lanes of one block at level lv
        integer l;
        begin
            nfree = 0;
            for (l = 0; l < 22; l = l + 1) nfree = nfree + (excl(lv, l) ? 0 : 1);
        end
    endfunction
    function automatic integer lane_pos(input integer u);    // first bit of free lane u in the PE vector
        integer g, nb, base, r, lv, k, l;
        begin
            lane_pos = -1;
            r = u;
            base = 0;
            for (g = 0; g < 2; g = g + 1) begin
                nb = (g == 0) ? 5 : 4;
                for (lv = 1; lv <= 6; lv = lv + 1) begin
                    if (lane_pos < 0 && r < nb * nfree(lv)) begin
                        k = r % nfree(lv);
                        for (l = 0; l < 22; l = l + 1) begin
                            if (!excl(lv, l)) begin
                                if (k == 0 && lane_pos < 0) lane_pos = base + (lv - 1) * nb * PM_LW + (r / nfree(lv)) * PM_LW + l * 64;
                                k = k - 1;
                            end
                        end
                    end else if (lane_pos < 0) r = r - nb * nfree(lv);
                end
                base = base + 6 * nb * PM_LW;
            end
        end
    endfunction
    function automatic integer lane_u(input integer g, input integer lv, input integer b, input integer l);  // inverse:
        integer nb, k, j;                                      // the free lane u of group g, level lv, block b, lane l
        begin                                                  // (-1: a sum / dead lane, or no register on it)
            nb = (g == 0) ? 5 : 4;
            if (excl(lv, l)) lane_u = -1;
            else begin
                lane_u = (g == 0) ? 0 : 5 * (nfree(1) + nfree(2) + nfree(3) + nfree(4) + nfree(5) + nfree(6));
                for (k = 1; k < lv; k = k + 1) lane_u = lane_u + nb * nfree(k);
                lane_u = lane_u + b * nfree(lv);
                for (j = 0; j < l; j = j + 1) lane_u = lane_u + (excl(lv, j) ? 0 : 1);
                if (lane_u >= NU) lane_u = -1;
            end
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
