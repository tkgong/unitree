// top_shared.sv - the shared PE: the Monolith-31 core (its Concrete tree built of alu_lend adders) and NB arx_block
// (ChaCha20 / BLAKE3) whose 4 NB adds run on the first 4 NB adders of that tree. A run executes one primitive (prim) on
// the whole PE; ext = 1 (the tree adders take the blocks' operands) whenever the run is not Monolith. NB <= NTREE / 4.
module top_shared #(
    parameter int NB = 64,
    parameter int MC = 12
) (
    input  logic              clk,
    input  logic              rst,
    input  logic              start,
    input  logic [1:0]        prim,          // 0 ChaCha20, 1 BLAKE3, 2 Monolith-31
    input  logic [16*31-1:0]  mono_x,
    output logic [16*31-1:0]  mono_y,
    input  logic [NB*512-1:0] arx_v,
    input  logic [NB*512-1:0] arx_m,
    input  logic [NB*256-1:0] arx_h,
    output logic [NB*512-1:0] arx_out,
    output logic              done,
    output logic              busy
);
    localparam int NTREE = mono_pkg::NTREE;
    logic ext, blake, m_start, a_start, m_done, a_done, m_busy, a_busy;
    assign ext     = (prim != 2'd2);
    assign blake   = (prim == 2'd1);
    assign m_start = start && (prim == 2'd2);
    assign a_start = start && (prim != 2'd2);
    logic [NTREE*32-1:0] ea, eb, ey;
    logic [NB*4*32-1:0]  bea, beb;
    mono_core #(.MC(MC), .LEND(1)) u_mono (.clk(clk), .rst(rst), .start(m_start), .x(mono_x), .y(mono_y), .done(m_done),
        .busy(m_busy), .ext(ext), .ea(ea), .eb(eb), .ey(ey));
    assign ea = {{((NTREE - 4*NB)*32){1'b0}}, bea};
    assign eb = {{((NTREE - 4*NB)*32){1'b0}}, beb};
    logic ld, en, xr_en, xr_tgt, msg_y, diag, perm, sigma;
    logic [1:0] add_sel, ff_row, rot_sel;
    arx_ctrl u_ctrl (.clk(clk), .rst(rst), .start(a_start), .blake(blake), .ld(ld), .en(en), .add_sel(add_sel), .ff_row(ff_row),
        .xr_en(xr_en), .xr_tgt(xr_tgt), .rot_sel(rot_sel), .msg_y(msg_y), .diag(diag), .perm(perm), .sigma(sigma), .done(a_done), .busy(a_busy));
    generate
        for (genvar b = 0; b < NB; b++) begin : g_blk
            arx_block u_blk (.clk(clk), .ld(ld), .en(en), .blake(blake), .add_sel(add_sel), .ff_row(ff_row), .xr_en(xr_en),
                .xr_tgt(xr_tgt), .rot_sel(rot_sel), .msg_y(msg_y), .diag(diag), .perm(perm), .sigma(sigma),
                .in_v(arx_v[b*512 +: 512]), .in_m(arx_m[b*512 +: 512]), .in_h(arx_h[b*256 +: 256]), .out(arx_out[b*512 +: 512]),
                .ea(bea[b*128 +: 128]), .eb(beb[b*128 +: 128]), .ey(ey[b*128 +: 128]));
        end
    endgenerate
    assign done = (prim == 2'd2) ? m_done : a_done;
    assign busy = m_busy || a_busy;
endmodule
