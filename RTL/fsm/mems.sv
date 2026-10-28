// mems.sv - the memories of the accelerator, behavioural (they are memory macros, black boxes in the synthesis of the
// controller; their sizes are reported in bits):
//   slot_sram : NSLOT x 256-bit on-chip SRAM (32 B slots), NRP combinational read ports, NWP + 1 write ports
//   prog_mem  : the two program banks (tile / subtree program, top program): control words (CTRLW bits per cycle) and
//               the descriptor groups of every ring (7 x DESCW bits per group); loaded by the testbench
module slot_sram #(
    parameter int NSLOT = 4096,
    parameter int NRP   = 112,
    parameter int NWP   = 111
) (
    input  logic                clk,
    input  logic [NRP*16-1:0]   rd_addr,
    output logic [NRP*256-1:0]  rd_data,
    input  logic [NWP-1:0]      wr_en,
    input  logic [NWP*16-1:0]   wr_addr,
    input  logic [NWP*256-1:0]  wr_data
);
    logic [255:0] mem [0:NSLOT-1];
    generate
        for (genvar i = 0; i < NRP; i++) begin : g_rd
            assign rd_data[i*256 +: 256] = mem[rd_addr[i*16 +: 16]];
        end
    endgenerate
    generate
        for (genvar i = 0; i < NWP; i++) begin : g_wr
            always_ff @(posedge clk) if (wr_en[i]) mem[wr_addr[i*16 +: 16]] <= wr_data[i*256 +: 256];
        end
    endgenerate
endmodule

module prog_mem #(
    parameter int CTRLW = 306,
    parameter int DESCW = 104,
    parameter int NRING = 16,
    parameter int NCTRL = 4096,                     // control words per bank
    parameter int NDESC = 1024                      // descriptor groups per ring per bank
) (
    input  logic                       bank,
    input  logic [15:0]                pc,
    output logic [CTRLW-1:0]           ctrl,
    input  logic [NRING-1:0][15:0]     dptr,
    output logic [NRING*7*DESCW-1:0]   dgrp
);
    logic [CTRLW-1:0]   cmem [0:1][0:NCTRL-1];
    logic [7*DESCW-1:0] dmem [0:1][0:NRING-1][0:NDESC-1];
    assign ctrl = cmem[bank][pc];
    generate
        for (genvar k = 0; k < NRING; k++) begin : g_d
            assign dgrp[k*7*DESCW +: 7*DESCW] = dmem[bank][k][dptr[k]];
        end
    endgenerate
endmodule

// write FIFO of result events towards the HBM (depth DEPTH, one pop per cycle)
module ev_fifo #(
    parameter int NWP   = 111,
    parameter int DEPTH = 4096
) (
    input  logic                clk,
    input  logic                rst,
    input  logic [NWP-1:0]      in_valid,
    input  logic [NWP*32-1:0]   in_addr,            // HBM byte address
    input  logic [NWP*256-1:0]  in_data,
    output logic                out_valid,
    output logic [31:0]         out_addr,
    output logic [255:0]        out_data,
    input  logic                out_ready,
    output logic                empty,
    output logic [15:0]         count
);
    localparam int AW = $clog2(DEPTH);
    logic [287:0] mem [0:DEPTH-1];
    logic [AW:0]  wp, rp;
    logic [AW:0]  pos [0:NWP];                           // write position of port i: wp + the valid ports before it
    always_comb begin
        pos[0] = wp;
        for (int i = 0; i < NWP; i++) pos[i + 1] = pos[i] + (in_valid[i] ? 1 : 0);
    end
    generate
        for (genvar i = 0; i < NWP; i++) begin : g_push
            always_ff @(posedge clk) if (in_valid[i] && !rst) mem[pos[i][AW-1:0]] <= {in_addr[i*32 +: 32], in_data[i*256 +: 256]};
        end
    endgenerate
    always_ff @(posedge clk) begin
        if (rst) begin wp <= '0; rp <= '0; end
        else begin
            wp <= pos[NWP];
            if (out_valid && out_ready) rp <= rp + 1;
        end
    end
    assign empty = (wp == rp);
    assign count = wp - rp;
    assign out_valid = !empty;
    assign {out_addr, out_data} = mem[rp[AW-1:0]];
endmodule
