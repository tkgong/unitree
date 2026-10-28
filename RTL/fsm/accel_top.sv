// accel_top.sv - the accelerator: the bz3 unit + sequencer (seq), the slot SRAM, the program memories, the HBM DMA,
// and the FSM that schedules memory against compute the way the DSE memory model does (dse/TOP/README.md):
//   Merkle: the tree in tiles of 2^TK leaves; the leaves of tile i+1 are prefetched from the HBM into the other half of
//           the leaf buffer while tile i computes (the tile program, relative slots, re-based per tile); every finished
//           node goes to the HBM write FIFO as it finishes; the tile roots stay on chip; the top program hashes them.
//   GGM:    the top program expands the seed to the 2^(SZ-TK) subtree seeds (on chip); each subtree program expands one
//           to 2^TK leaves, double-buffered on chip and streamed to the HBM while the next subtree computes.
// A run executes one primitive (the programs are compiled for it); the FSM never schedules inside the unit.
// SRAM map (slots): leaf buffers A, B [0, 2 NLT); internal buffers A, B [2 NLT, 4 NLT); top leaves / subtree seeds
// [4 NLT, 4 NLT + NT); top internal [4 NLT + NT, 4 NLT + 2 NT); the root / seed slot 4 NLT + 2 NT.
module accel_top
    import unit_cfg::*;
#(
    parameter int CTRLW = 306,
    parameter int DESCW = 104,
    parameter int NSLOT = 8192,
    parameter int NCTRL = 8192,
    parameter int NDESC = 2048,
    parameter int FDEPTH = 8192
) (
    input  logic        clk,
    input  logic        rst,
    // configuration (stable during a run)
    input  logic        cfg_ggm,            // 0 Merkle, 1 GGM
    input  logic [4:0]  cfg_sz,             // log2 leaves of the whole tree
    input  logic [4:0]  cfg_tk,             // log2 leaves of a tile / subtree
    input  logic [15:0] cfg_ncyc_tile,      // control words of the tile program (bank 0)
    input  logic [15:0] cfg_ncyc_top,       // control words of the top program (bank 1)
    input  logic [31:0] cfg_hbm_leaf,       // HBM byte address of the leaves (Merkle: input; GGM: output)
    input  logic [31:0] cfg_hbm_int,        // HBM byte address of the stored internal nodes / seeds
    input  logic [31:0] cfg_hbm_root,       // HBM byte address of the root (Merkle) / the seed (GGM)
    input  logic        start,
    output logic        done,
    // HBM read channel (32 B)
    output logic        rd_valid,
    output logic [31:0] rd_addr,
    output logic [15:0] rd_tag,             // the SRAM slot the data goes to
    input  logic        rd_ready,
    input  logic        rsp_valid,
    input  logic [15:0] rsp_tag,
    input  logic [255:0] rsp_data,
    // HBM write channel (32 B)
    output logic        wr_valid,
    output logic [31:0] wr_addr,
    output logic [255:0] wr_data,
    input  logic        wr_ready,
    // statistics
    output logic [31:0] st_cycles, st_compute, st_fetch, st_overlap, st_wpend_max,
    // program memories (loaded by the testbench through hierarchical references)
    output logic [15:0] dbg_pc
);
    localparam int NRP = 2 * NB + 2 * NM, NWP = 2 * NB + NM;
    // ---------------- geometry ----------------
    logic [15:0] NLT, NT;                               // leaves per tile, tiles
    assign NLT = 16'd1 << cfg_tk;
    assign NT  = 16'd1 << (cfg_sz - cfg_tk);
    logic [15:0] LEAF_A, LEAF_B, INT_A, INT_B, TOPS, TOPINT, ROOTSLOT;
    assign LEAF_A = 16'd0; assign LEAF_B = NLT; assign INT_A = 2 * NLT; assign INT_B = 3 * NLT;
    assign TOPS = 4 * NLT; assign TOPINT = TOPS + NT; assign ROOTSLOT = TOPINT + NT;
    // ---------------- the sequencer, the unit, the memories ----------------
    logic seq_run, seq_busy, seq_done;
    logic [15:0] seq_ncyc, s_r1, s_r2, s_b0, s_b1, s_b2, s_root_slot, s_root_dst;
    logic [4:0]  s_lv_off;
    logic [31:0] s_tile;
    logic        bank;
    logic [15:0] pc;
    logic [CTRLW-1:0] ctrl;
    logic [NR+NM-1:0][15:0] dptr;
    logic [(NR+NM)*7*DESCW-1:0] dgrp;
    logic [NRP*16-1:0] srd_addr;
    logic [NRP*256-1:0] srd_data;
    logic [NWP-1:0] swr_en;
    logic [NWP*16-1:0] swr_addr;
    logic [NWP*256-1:0] swr_data;
    logic [NWP-1:0] ev_valid;
    logic [NWP*16-1:0] ev_addr;
    logic [NWP*256-1:0] ev_data;
    logic [NIO*64-1:0] lin, lout;
    logic mono, mono2, htap, blake;
    logic [8:0] r, r2;
    logic [NG*9-1:0] rg;
    seq #(.CTRLW(CTRLW), .DESCW(DESCW)) u_seq (.clk(clk), .rst(rst), .run(seq_run), .ncyc(seq_ncyc), .busy(seq_busy), .done(seq_done),
        .reg1(s_r1), .reg2(s_r2), .base0(s_b0), .base1(s_b1), .base2(s_b2), .root_slot(s_root_slot), .root_dst(s_root_dst),
        .lv_off(s_lv_off), .tile_idx(s_tile), .pc(pc), .ctrl(ctrl), .dptr(dptr), .dgrp(dgrp),
        .rd_addr(srd_addr), .rd_data(srd_data), .wr_en(swr_en), .wr_addr(swr_addr), .wr_data(swr_data),
        .ev_valid(ev_valid), .ev_addr(ev_addr), .ev_data(ev_data),
        .lin(lin), .lout(lout), .mono(mono), .mono2(mono2), .htap(htap), .blake(blake), .r(r), .r2(r2), .rg(rg));
    assign dbg_pc = pc;
    unit_bz3 u_unit (.clk(clk), .rst(rst), .lin(lin), .lout(lout), .mono(mono), .mono2(mono2), .htap(htap), .blake(blake), .r(r), .r2(r2), .rg(rg));
    prog_mem #(.CTRLW(CTRLW), .DESCW(DESCW), .NRING(NR + NM), .NCTRL(NCTRL), .NDESC(NDESC)) u_prog (.bank(bank), .pc(pc), .ctrl(ctrl), .dptr(dptr), .dgrp(dgrp));
    // SRAM: the sequencer's ports + one DMA write port
    logic dma_we;
    logic [15:0] dma_waddr;
    logic [255:0] dma_wdata;
    slot_sram #(.NSLOT(NSLOT), .NRP(NRP), .NWP(NWP + 1)) u_sram (.clk(clk), .rd_addr(srd_addr), .rd_data(srd_data),
        .wr_en({dma_we, swr_en}), .wr_addr({dma_waddr, swr_addr}), .wr_data({dma_wdata, swr_data}));
    // ---------------- result events -> HBM addresses -> write FIFO ----------------
    // Merkle: internal nodes of tile i (INT buffer) -> hbm_int + (i (NLT-1) + off) 32; tile roots (TOPS) -> after them;
    //         top internal -> after those; the root -> hbm_root.  GGM: leaves (LEAF buffer) -> hbm_leaf + ((i << TK) + off) 32;
    //         seeds (INT / TOPS / TOPINT) -> hbm_int + (same order) 32.
    logic [15:0] cur_tile;
    logic [NWP*32-1:0] ev_hbm;
    logic [NWP-1:0] ev_store;
    generate
        for (genvar i = 0; i < NWP; i++) begin : g_ev
            logic [15:0] a, intb, leafb;
            logic [31:0] h;
            logic st;
            assign a = ev_addr[i*16 +: 16];
            assign intb  = cur_tile[0] ? INT_B : INT_A;
            assign leafb = cur_tile[0] ? LEAF_B : LEAF_A;
            always_comb begin
                h = '0; st = 1'b0;
                if (!cfg_ggm) begin
                    if (a >= intb && a < intb + NLT) begin h = cfg_hbm_int + 32 * (cur_tile * (NLT - 1) + (a - intb)); st = 1'b1; end
                    else if (a >= TOPS && a < TOPINT) begin h = cfg_hbm_int + 32 * (NT * (NLT - 1) + (a - TOPS)); st = 1'b1; end
                    else if (a >= TOPINT && a < ROOTSLOT) begin h = cfg_hbm_int + 32 * (NT * (NLT - 1) + NT + (a - TOPINT)); st = 1'b1; end
                    else if (a == ROOTSLOT) begin h = cfg_hbm_root; st = 1'b1; end
                end else begin
                    if (a >= leafb && a < leafb + NLT) begin h = cfg_hbm_leaf + 32 * ((cur_tile << cfg_tk) + (a - leafb)); st = 1'b1; end
                    else if (a >= intb && a < intb + NLT) begin h = cfg_hbm_int + 32 * (cur_tile * (NLT - 1) + (a - intb)); st = 1'b1; end
                    else if (a >= TOPS && a < TOPINT) begin h = cfg_hbm_int + 32 * (NT * (NLT - 1) + (a - TOPS)); st = 1'b1; end
                    else if (a >= TOPINT && a < ROOTSLOT) begin h = cfg_hbm_int + 32 * (NT * (NLT - 1) + NT + (a - TOPINT)); st = 1'b1; end
                end
            end
            assign ev_hbm[i*32 +: 32] = h;
            assign ev_store[i] = ev_valid[i] & st;
        end
    endgenerate
    logic f_valid, f_empty;
    logic [31:0] f_addr;
    logic [255:0] f_data;
    logic [15:0] f_count;
    ev_fifo #(.NWP(NWP), .DEPTH(FDEPTH)) u_fifo (.clk(clk), .rst(rst), .in_valid(ev_store), .in_addr(ev_hbm), .in_data(ev_data),
        .out_valid(f_valid), .out_addr(f_addr), .out_data(f_data), .out_ready(wr_ready), .empty(f_empty), .count(f_count));
    assign wr_valid = f_valid;
    assign wr_addr  = f_addr;
    assign wr_data  = f_data;
    // ---------------- HBM read DMA: count slots from hbm_base into sram_base ----------------
    logic        dma_go, dma_busy;
    logic [31:0] dma_hbm;
    logic [15:0] dma_sram, dma_n, dma_sent, dma_rcvd;
    always_ff @(posedge clk) begin
        if (rst) begin dma_busy <= 1'b0; dma_sent <= '0; dma_rcvd <= '0; end
        else if (dma_go) begin dma_busy <= 1'b1; dma_sent <= '0; dma_rcvd <= '0; end
        else if (dma_busy) begin
            if (rd_valid && rd_ready) dma_sent <= dma_sent + 16'd1;
            if (rsp_valid) begin
                dma_rcvd <= dma_rcvd + 16'd1;
                if (dma_rcvd + 16'd1 == dma_n) dma_busy <= 1'b0;
            end
        end
    end
    assign rd_valid = dma_busy && (dma_sent < dma_n);
    assign rd_addr  = dma_hbm + 32 * dma_sent;
    assign rd_tag   = dma_sram + dma_sent;
    assign dma_we    = rsp_valid;
    assign dma_waddr = rsp_tag;
    assign dma_wdata = rsp_data;
    // ---------------- the FSM ----------------
    typedef enum logic [3:0] {IDLE, FETCH0, TILE_START, TILE_RUN, TOP_START, TOP_RUN, GTOP_START, GTOP_RUN, GSUB_START, GSUB_RUN, DRAIN, DONE} st_t;
    st_t st;
    logic [15:0] tile;
    assign cur_tile = tile;
    always_ff @(posedge clk) begin
        seq_run <= 1'b0; dma_go <= 1'b0; done <= 1'b0;
        if (rst) begin st <= IDLE; tile <= '0; end
        else case (st)
            IDLE: if (start) begin
                tile <= '0;
                dma_hbm <= cfg_ggm ? cfg_hbm_root : cfg_hbm_leaf; dma_sram <= cfg_ggm ? ROOTSLOT : LEAF_A; dma_n <= cfg_ggm ? 16'd1 : NLT;
                dma_go <= 1'b1; st <= FETCH0;
            end
            FETCH0: if (!dma_busy && !dma_go) begin if (cfg_ggm) st <= GTOP_START; else st <= TILE_START; end
            // ---- Merkle ----
            TILE_START: begin                                   // run tile program on buffer (tile & 1); prefetch tile + 1
                bank <= 1'b0; seq_ncyc <= cfg_ncyc_tile;
                s_r1 <= NLT; s_r2 <= 16'hFFFF; s_b0 <= tile[0] ? LEAF_B : LEAF_A; s_b1 <= tile[0] ? INT_B : INT_A; s_b2 <= '0;
                s_root_slot <= 2 * NLT - 16'd2; s_root_dst <= TOPS + tile; s_lv_off <= '0; s_tile <= '0;
                seq_run <= 1'b1;
                if (tile + 16'd1 < NT) begin
                    dma_hbm <= cfg_hbm_leaf + 32 * ((tile + 16'd1) << cfg_tk); dma_sram <= tile[0] ? LEAF_A : LEAF_B; dma_n <= NLT; dma_go <= 1'b1;
                end
                st <= TILE_RUN;
            end
            TILE_RUN: if (seq_done) begin if (tile + 16'd1 < NT) st <= TILE_START; else st <= TOP_START; end
            TOP_START: begin
                bank <= 1'b1; seq_ncyc <= cfg_ncyc_top;
                s_r1 <= NT; s_r2 <= 16'hFFFF; s_b0 <= TOPS; s_b1 <= TOPINT; s_b2 <= '0;
                s_root_slot <= 2 * NT - 16'd2; s_root_dst <= ROOTSLOT; seq_run <= 1'b1; st <= TOP_RUN;
            end
            TOP_RUN: if (seq_done) st <= DRAIN;
            // ---- GGM ----
            GTOP_START: begin                                   // seed -> the NT subtree seeds (TOPS), internal seeds (TOPINT)
                bank <= 1'b1; seq_ncyc <= cfg_ncyc_top;
                s_r1 <= 16'd1; s_r2 <= NT - 16'd1; s_b0 <= ROOTSLOT; s_b1 <= TOPINT; s_b2 <= TOPS;
                s_root_slot <= 16'hFFFF; s_root_dst <= '0; s_lv_off <= '0; s_tile <= '0; seq_run <= 1'b1; st <= GTOP_RUN;
            end
            GTOP_RUN: if (seq_done) st <= GSUB_START;
            GSUB_START: begin                                   // subtree tile: seed TOPS + tile -> leaves in buffer (tile & 1)
                bank <= 1'b0; seq_ncyc <= cfg_ncyc_tile;
                s_r1 <= 16'd1; s_r2 <= NLT - 16'd1; s_b0 <= TOPS + tile; s_b1 <= tile[0] ? INT_B : INT_A; s_b2 <= tile[0] ? LEAF_B : LEAF_A;
                s_root_slot <= 16'hFFFF; s_lv_off <= cfg_sz - cfg_tk; s_tile <= {16'd0, tile}; seq_run <= 1'b1; st <= GSUB_RUN;
            end
            GSUB_RUN: if (seq_done) begin if (tile + 16'd1 < NT) st <= GSUB_START; else st <= DRAIN; end
            DRAIN: if (f_empty) begin done <= 1'b1; st <= DONE; end
            DONE: st <= IDLE;
            default: st <= IDLE;
        endcase
        if ((st == TILE_RUN || st == GSUB_RUN) && seq_done) tile <= tile + 16'd1;
    end
    // ---------------- statistics ----------------
    always_ff @(posedge clk) begin
        if (rst || start) begin st_cycles <= '0; st_compute <= '0; st_fetch <= '0; st_overlap <= '0; st_wpend_max <= '0; end
        else if (st != IDLE && st != DONE) begin
            st_cycles <= st_cycles + 1;
            if (seq_busy) st_compute <= st_compute + 1;
            if (dma_busy) st_fetch <= st_fetch + 1;
            if (seq_busy && dma_busy) st_overlap <= st_overlap + 1;
            if (f_count > st_wpend_max[15:0]) st_wpend_max <= {16'd0, f_count};
        end
    end
endmodule
