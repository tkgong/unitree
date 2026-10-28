// unit_cfg.sv - the lane map of the bz3 unit (RTL/pe/unit_bz3.sv), as compile_tree.py reads it from the HLS header:
// 54 blocks of 22 lanes (block j at 22 j), 14 ARX rings (one block set each; its spans are groups of consecutive
// levels), two Monolith datapaths at lanes 1188 and 1240. Copied from the generator's meta (dse/TOP/bz3): the ring's
// span-0 lane range (lo..hi), its last span's lane range (llo..lhi), its block indices (first span) and lblocks (last
// span), the group ranges (glo..ghi) and the span chains.
package unit_cfg;
    localparam int NIO = 1248, NG = 28, NR = 14, NM = 2, NB = 54, BL = 22;
    localparam int BASE0 = 1188, BASE1 = 1240;
    // rings: blocks of the first span, lane ranges
    function automatic int ring_nb(input int r);       // blocks per ring
        case (r) 0: ring_nb = 7; 1: ring_nb = 4; 2: ring_nb = 3; 3: ring_nb = 1; 4: ring_nb = 2; 5: ring_nb = 1; 6: ring_nb = 1;
                 7: ring_nb = 7; 8: ring_nb = 4; 9: ring_nb = 3; 10: ring_nb = 1; 11: ring_nb = 2; 12: ring_nb = 1; default: ring_nb = 1; endcase
    endfunction
    function automatic int ring_b0(input int r);       // first block of the ring's first span (blocks are consecutive)
        case (r) 0: ring_b0 = 0; 1: ring_b0 = 7; 2: ring_b0 = 11; 3: ring_b0 = 14; 4: ring_b0 = 15; 5: ring_b0 = 19; 6: ring_b0 = 22;
                 7: ring_b0 = 27; 8: ring_b0 = 34; 9: ring_b0 = 38; 10: ring_b0 = 41; 11: ring_b0 = 42; 12: ring_b0 = 46; default: ring_b0 = 49; endcase
    endfunction
    function automatic int ring_lb0(input int r);      // first block of the ring's last span
        case (r) 0: ring_lb0 = 0; 1: ring_lb0 = 7; 2: ring_lb0 = 11; 3: ring_lb0 = 14; 4: ring_lb0 = 17; 5: ring_lb0 = 21; 6: ring_lb0 = 26;
                 7: ring_lb0 = 27; 8: ring_lb0 = 34; 9: ring_lb0 = 38; 10: ring_lb0 = 41; 11: ring_lb0 = 44; 12: ring_lb0 = 48; default: ring_lb0 = 53; endcase
    endfunction
    function automatic int blk_ring(input int p);      // the ring whose FIRST span holds block p, else -1
        blk_ring = -1;
        for (int k = 0; k < NR; k++) if (p >= ring_b0(k) && p < ring_b0(k) + ring_nb(k)) blk_ring = k;
    endfunction
    function automatic int lblk_ring(input int p);     // the ring whose LAST span holds block p, else -1
        lblk_ring = -1;
        for (int k = 0; k < NR; k++) if (p >= ring_lb0(k) && p < ring_lb0(k) + ring_nb(k)) lblk_ring = k;
    endfunction
    localparam int NSPAN = 28;                           // the 28 groups = spans; span s covers lanes glo(s) .. ghi(s)
    function automatic int glo(input int g);
        case (g) 0: glo = 0; 1: glo = 154; 2: glo = 242; 3: glo = 308; 4: glo = 330; 5: glo = 374; 6: glo = 418; 7: glo = 440; 8: glo = 462;
                 9: glo = 484; 10: glo = 506; 11: glo = 528; 12: glo = 550; 13: glo = 572; 14: glo = 594; 15: glo = 748; 16: glo = 836;
                 17: glo = 902; 18: glo = 924; 19: glo = 968; 20: glo = 1012; 21: glo = 1034; 22: glo = 1056; 23: glo = 1078; 24: glo = 1100;
                 25: glo = 1122; 26: glo = 1144; default: glo = 1166; endcase
    endfunction
    function automatic int ghi(input int g);
        ghi = (g == NSPAN - 1) ? 1188 : glo(g + 1);
    endfunction
    // the chain of each ring: its spans in step order (span s passes its lanes to span s+1 of the chain every cycle)
    function automatic int ring_nspan(input int r);
        case (r) 0, 1, 2, 3, 7, 8, 9, 10: ring_nspan = 1; 4, 11: ring_nspan = 2; 5, 12: ring_nspan = 3; default: ring_nspan = 5; endcase
    endfunction
    function automatic int ring_span(input int r, input int i);   // the i-th span of ring r
        case (r)
            0: ring_span = 0; 1: ring_span = 1; 2: ring_span = 2; 3: ring_span = 3; 4: ring_span = 4 + i; 5: ring_span = 6 + i; 6: ring_span = 9 + i;
            7: ring_span = 14; 8: ring_span = 15; 9: ring_span = 16; 10: ring_span = 17; 11: ring_span = 18 + i; 12: ring_span = 20 + i; default: ring_span = 23 + i;
        endcase
    endfunction
endpackage
