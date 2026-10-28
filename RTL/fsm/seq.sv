// seq.sv - the sequencer: executes the compiled program (compile_tree.py hw=) on the bz3 unit, one control word per
// cycle, no run-time scheduling. Per cycle it (1) drives the unit's controls (mono, blake, r, rg) from the control word,
// (2) issues the rings flagged in the word: reads their next descriptor group (SRAM slots of the inputs, GGM idx / level,
// result slots), reads the SRAM, formats the block / state lanes (lane_fmt) into the unit's input vector, (3) recirculates
// every ring's last-span lanes into its first span and passes each span's lanes to the next span of the chain (the
// HLS driver's prev -> lanes copies; ChaCha20 swaps the two copies), (4) captures the finishing rings' results from the
// previous output vector (lane_cap) and writes them to the SRAM and to the result event port (for the HBM write-out).
// The previous output vector is a register (prev): the HLS call computes out from the registers before the update.
// Slot addresses of the program are relative; the FSM gives the translation (three regions and the root slot).
module seq
#(
    parameter int CTRLW = 306,
    parameter int DESCW = 104,
    parameter int NRP   = 2 * unit_cfg::NB + 2 * unit_cfg::NM,            // SRAM read ports (two per block / state issue)
    parameter int NWP   = 2 * unit_cfg::NB + unit_cfg::NM                 // SRAM write ports (two per finishing block, one per state)
) (
    input  logic                 clk,
    input  logic                 rst,
    input  logic                 run,                 // start the program at pc = 0
    input  logic [15:0]          ncyc,
    output logic                 busy,
    output logic                 done,                // the cycle after the last control word
    // slot translation: slot < reg1: base0 + slot; < reg2: base1 + (slot - reg1); else base2 + (slot - reg2); root_slot -> root_dst
    input  logic [15:0]          reg1, reg2, base0, base1, base2, root_slot, root_dst,
    input  logic [4:0]           lv_off,              // GGM: level' = level + lv_off, idx' = (tile << level') | idx
    input  logic [31:0]          tile_idx,
    // program memories (combinational reads)
    output logic [15:0]          pc,
    input  logic [CTRLW-1:0]     ctrl,
    output logic [unit_cfg::NR+unit_cfg::NM-1:0][15:0] dptr,              // descriptor group pointer per ring / datapath
    input  logic [(unit_cfg::NR+unit_cfg::NM)*7*DESCW-1:0] dgrp,          // the group at dptr (7 descriptor slots per ring, nb used)
    // SRAM
    output wire  [NRP*16-1:0]    rd_addr,
    input  logic [NRP*256-1:0]   rd_data,
    output wire  [NWP-1:0]       wr_en,
    output wire  [NWP*16-1:0]    wr_addr,
    output wire  [NWP*256-1:0]   wr_data,
    // result events (the same writes, for the HBM write-out): valid, translated slot, data
    output logic [NWP-1:0]       ev_valid,
    output logic [NWP*16-1:0]    ev_addr,
    output logic [NWP*256-1:0]   ev_data,
    // the unit
    output wire  [unit_cfg::NIO*64-1:0]    lin,
    input  logic [unit_cfg::NIO*64-1:0]    lout,
    output logic                 mono, mono2, htap, blake,
    output logic [8:0]           r, r2,
    output logic [unit_cfg::NG*9-1:0]      rg
);
    // ---------------- program counter ----------------
    logic running;
    always_ff @(posedge clk) begin
        if (rst) begin running <= 1'b0; pc <= '0; done <= 1'b0; end
        else if (run) begin running <= 1'b1; pc <= '0; done <= 1'b0; end
        else if (running) begin
            if (pc == ncyc - 16'd1) begin running <= 1'b0; done <= 1'b1; end
            pc <= pc + 16'd1;
        end else done <= 1'b0;
    end
    assign busy = running;
    // ---------------- the control word ----------------
    logic [15:0] issue, fin;
    assign mono  = running & ctrl[0];
    assign mono2 = running & ctrl[1];
    assign htap  = running & ctrl[2];
    assign blake = ctrl[3];
    assign r     = ctrl[12:4];
    assign r2    = ctrl[21:13];
    assign rg    = ctrl[22 +: unit_cfg::NG*9];
    assign issue = running ? ctrl[22 + unit_cfg::NG*9 +: 16] : 16'd0;
    assign fin   = running ? ctrl[38 + unit_cfg::NG*9 +: 16] : 16'd0;
    logic alt;
    assign alt = !blake;                                 // ChaCha20 programs: the two copies alternate (the Monolith rings ignore it)
    // ---------------- prev: the unit's output of the previous cycle ----------------
    logic [unit_cfg::NIO*64-1:0] prev;
    always_ff @(posedge clk) prev <= lout;
    // ---------------- slot translation ----------------
    function automatic logic [15:0] tr(input logic [15:0] s);
        if (s == root_slot) tr = root_dst;
        else if (s < reg1) tr = base0 + s;
        else if (s < reg2) tr = base1 + (s - reg1);
        else tr = base2 + (s - reg2);
    endfunction
    // ---------------- descriptor pointers and the in-flight queues ----------------
    // a queue entry per issued group: for each of its (up to 7) nodes: kind, out0, out1 (translated)
    localparam int QW = 7 * 34, QD = 32;                 // per node: valid, out1, out0, kind
    logic [QW-1:0] q [0:unit_cfg::NR+unit_cfg::NM-1][0:QD-1];
    logic [4:0]    qh [0:unit_cfg::NR+unit_cfg::NM-1], qt [0:unit_cfg::NR+unit_cfg::NM-1];
    logic [unit_cfg::NR+unit_cfg::NM-1:0] issue_v, fin_v;
    always_ff @(posedge clk) begin
        for (int k = 0; k < unit_cfg::NR + unit_cfg::NM; k++) begin
            if (rst || run) begin dptr[k] <= '0; qh[k] <= '0; qt[k] <= '0; end
            else begin
                if (issue[k]) begin dptr[k] <= dptr[k] + 16'd1; qt[k] <= qt[k] + 5'd1; end
                if (fin[k]) qh[k] <= qh[k] + 5'd1;
            end
        end
    end
    // ---------------- issue: SRAM reads, lane formatting ----------------
    wire  [unit_cfg::NIO*64-1:0] lanes_new;                        // the formatted lanes of the issued blocks / states
    wire  [unit_cfg::NIO-1:0]    lane_sel;                         // 1: take lanes_new, else the recirculation
    wire  [QW-1:0]     qin [0:unit_cfg::NR+unit_cfg::NM-1];
    generate
        for (genvar p = 0; p < unit_cfg::NB; p++) begin : g_blk                     // block position p: issued by ring unit_cfg::blk_ring(p) (first span)
            localparam int K = unit_cfg::blk_ring(p);
            if (K >= 0) begin : g_use
                localparam int B = p - unit_cfg::ring_b0(K);
                logic [DESCW-1:0] d;
                logic [15:0] sl, sr, o0, o1;
                logic [31:0] idx, idxt;
                logic [4:0]  lev, levt;
                logic kind, root, dv;
                assign d = dgrp[(K*7 + B)*DESCW +: DESCW];
                assign kind = d[0]; assign sl = d[16:1]; assign sr = d[32:17]; assign idx = d[64:33]; assign lev = d[69:65]; assign root = d[70]; assign dv = d[103];
                assign o0 = d[86:71]; assign o1 = d[102:87];
                assign levt = lev + lv_off;
                assign idxt = (tile_idx << levt) | idx;
                assign rd_addr[(2*p)*16 +: 16]     = tr(sl);
                assign rd_addr[(2*p + 1)*16 +: 16] = tr(sr);
                logic [22*64-1:0] fl;
                arx_fmt u_fmt (.blake(blake), .kind(kind), .root(root), .va(rd_data[(2*p)*256 +: 256]), .vb(rd_data[(2*p + 1)*256 +: 256]),
                               .idx(idxt), .level(levt), .lanes(fl));
                assign lanes_new[p*unit_cfg::BL*64 +: unit_cfg::BL*64] = fl;
                assign lane_sel[p*unit_cfg::BL +: unit_cfg::BL] = {unit_cfg::BL{issue[K]}};
                assign qin[K][B*34 +: 34] = {dv, tr(o1), tr(o0), kind};
            end else begin : g_pass                                      // a later-span block: never issued from memory
                assign rd_addr[(2*p)*16 +: 32] = '0;
                assign lanes_new[p*unit_cfg::BL*64 +: unit_cfg::BL*64] = '0;
                assign lane_sel[p*unit_cfg::BL +: unit_cfg::BL] = '0;
            end
        end
        for (genvar k = 0; k < unit_cfg::NR; k++) begin : g_qpad                     // unused descriptor slots of each ring's queue entry
            for (genvar b = unit_cfg::ring_nb(k); b < 7; b++) begin : g_z
                assign qin[k][b*34 +: 34] = '0;
            end
        end
        for (genvar d_ = 0; d_ < unit_cfg::NM; d_++) begin : g_mono
            localparam int BI = unit_cfg::NB + d_;                   // read ports 2 BI, 2 BI + 1
            localparam int BASE = (d_ == 0) ? unit_cfg::BASE0 : unit_cfg::BASE1;
            logic [DESCW-1:0] d;
            logic [15:0] sl, sr, o0;
            assign d = dgrp[((unit_cfg::NR + d_)*7)*DESCW +: DESCW];
            assign sl = d[16:1]; assign sr = d[32:17]; assign o0 = d[86:71];
            assign rd_addr[(2*BI)*16 +: 16]     = tr(sl);
            assign rd_addr[(2*BI + 1)*16 +: 16] = tr(sr);
            mono_fmt u_fmt (.va(rd_data[(2*BI)*256 +: 256]), .vb(rd_data[(2*BI + 1)*256 +: 256]), .lanes(lanes_new[BASE*64 +: 8*64]));
            assign lane_sel[BASE +: 8] = {8{issue[unit_cfg::NR + d_]}};
            assign qin[unit_cfg::NR + d_] = {{(QW - 34){1'b0}}, 1'b1, 16'd0, tr(o0), 1'b0};
        end
    endgenerate
    always_ff @(posedge clk) begin
        for (int k = 0; k < unit_cfg::NR + unit_cfg::NM; k++) if (issue[k]) q[k][qt[k]] <= qin[k];
    end
    // the remaining lanes are never issued from memory
    generate
        for (genvar l = unit_cfg::NB * unit_cfg::BL; l < unit_cfg::NIO; l++) begin : g_rest
            if (!(l >= unit_cfg::BASE0 && l < unit_cfg::BASE0 + 8) && !(l >= unit_cfg::BASE1 && l < unit_cfg::BASE1 + 8)) begin : g_z
                assign lanes_new[l*64 +: 64] = '0;
                assign lane_sel[l] = 1'b0;
            end
        end
    endgenerate
    // ---------------- recirculation and span passing (prev -> lanes) ----------------
    wire  [unit_cfg::NIO*64-1:0] lanes_rec;
    generate
        for (genvar k = 0; k < unit_cfg::NR; k++) begin : g_rec
            localparam int SELF = k, PART = (k + unit_cfg::NR / 2) % unit_cfg::NR;
            localparam int S0 = unit_cfg::ring_span(k, 0), SL_ = unit_cfg::ring_span(k, unit_cfg::ring_nspan(k) - 1);
            localparam int LO = unit_cfg::glo(S0), W = unit_cfg::ghi(S0) - unit_cfg::glo(S0);                 // span-0 lanes of this ring
            localparam int LLO_S = unit_cfg::glo(unit_cfg::ring_span(SELF, unit_cfg::ring_nspan(SELF) - 1));  // last-span lanes (same width in both copies)
            localparam int LLO_P = unit_cfg::glo(unit_cfg::ring_span(PART, unit_cfg::ring_nspan(PART) - 1));
            assign lanes_rec[LO*64 +: W*64] = alt ? prev[LLO_P*64 +: W*64] : prev[LLO_S*64 +: W*64];
            for (genvar i = 1; i < unit_cfg::ring_nspan(k); i++) begin : g_span
                localparam int GI = unit_cfg::ring_span(k, i), GP = unit_cfg::ring_span(k, i - 1);
                assign lanes_rec[unit_cfg::glo(GI)*64 +: (unit_cfg::ghi(GI) - unit_cfg::glo(GI))*64] = prev[unit_cfg::glo(GP)*64 +: (unit_cfg::ghi(GP) - unit_cfg::glo(GP))*64];
            end
        end
        for (genvar d_ = 0; d_ < unit_cfg::NM; d_++) begin : g_mrec
            localparam int BASE = (d_ == 0) ? unit_cfg::BASE0 : unit_cfg::BASE1;
            assign lanes_rec[BASE*64 +: 8*64] = prev[BASE*64 +: 8*64];
        end
        for (genvar l = 0; l < unit_cfg::NIO; l++) begin : g_lin
            if ((l >= unit_cfg::NB * unit_cfg::BL && !(l >= unit_cfg::BASE0 && l < unit_cfg::BASE0 + 8) && !(l >= unit_cfg::BASE1 && l < unit_cfg::BASE1 + 8))) begin : g_z
                assign lin[l*64 +: 64] = '0;
            end else begin : g_m
                assign lin[l*64 +: 64] = lane_sel[l] ? lanes_new[l*64 +: 64] : lanes_rec[l*64 +: 64];
            end
        end
    endgenerate
    // ---------------- finish: capture from prev, write the SRAM, raise the events ----------------
    generate
        for (genvar p = 0; p < unit_cfg::NB; p++) begin : g_fin                     // block position p: the write ports 2p, 2p+1 belong to the ring
            localparam int K = unit_cfg::blk_ring(p);                               // issued at first-span position p (its result lanes are at the
            if (K >= 0) begin : g_use                                    // last-span position of the ring traversed last)
                localparam int B = p - unit_cfg::ring_b0(K), PART = (K + unit_cfg::NR / 2) % unit_cfg::NR;
                localparam int JS = unit_cfg::ring_lb0(K) + B, JP = unit_cfg::ring_lb0(PART) + B;
                logic [QW-1:0] qe;
                logic [18*64-1:0] bl;
                logic [255:0] o0, o1;
                logic kind, qv;
                assign qe = q[K][qh[K]];
                assign qv = qe[B*34 + 33];
                assign bl = alt ? prev[JP*unit_cfg::BL*64 +: 18*64] : prev[JS*unit_cfg::BL*64 +: 18*64];
                arx_cap u_cap (.blake(blake), .lanes(bl), .out0(o0), .out1(o1));
                assign kind = qe[B*34];
                assign wr_en[2*p]     = fin[K] & qv;
                assign wr_en[2*p + 1] = fin[K] & qv & kind;                  // the second child of a GGM node
                assign wr_addr[(2*p)*16 +: 16]     = qe[B*34 + 1 +: 16];
                assign wr_addr[(2*p + 1)*16 +: 16] = qe[B*34 + 17 +: 16];
                assign wr_data[(2*p)*256 +: 256]     = o0;
                assign wr_data[(2*p + 1)*256 +: 256] = o1;
            end else begin : g_none
                assign wr_en[2*p +: 2] = 2'b00;
                assign wr_addr[(2*p)*16 +: 32] = '0;
                assign wr_data[(2*p)*256 +: 512] = '0;
            end
        end
        for (genvar d_ = 0; d_ < unit_cfg::NM; d_++) begin : g_mfin
            localparam int BASE = (d_ == 0) ? unit_cfg::BASE0 : unit_cfg::BASE1, WI = 2 * unit_cfg::NB + d_;
            logic [255:0] o0;
            mono_cap u_cap (.lanes(prev[BASE*64 +: 8*64]), .out0(o0));
            assign wr_en[WI] = fin[unit_cfg::NR + d_];
            assign wr_addr[WI*16 +: 16] = q[unit_cfg::NR + d_][qh[unit_cfg::NR + d_]][1 +: 16];
            assign wr_data[WI*256 +: 256] = o0;
        end
    endgenerate
    assign ev_valid = wr_en;
    assign ev_addr  = wr_addr;
    assign ev_data  = wr_data;
endmodule
