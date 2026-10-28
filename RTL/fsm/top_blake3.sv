// top_blake3.sv - the natural BLAKE3 kernel: NB b3_block in lockstep under one arx_ctrl, every block's four adds on its
// own four alu_addp (4 NB private 32-bit adders).
module top_blake3 #(
    parameter int NB = 64
) (
    input  logic              clk,
    input  logic              rst,
    input  logic              start,
    input  logic [NB*512-1:0] in_v,
    input  logic [NB*512-1:0] in_m,
    input  logic [NB*256-1:0] in_h,
    output logic [NB*512-1:0] out,
    output logic              done,
    output logic              busy
);
    logic ld, en, xr_en, xr_tgt, msg_y, diag, perm, sigma;
    logic [1:0] add_sel, ff_row, rot_sel;
    arx_ctrl u_ctrl (.clk(clk), .rst(rst), .start(start), .blake(1'b1), .ld(ld), .en(en), .add_sel(add_sel), .ff_row(ff_row),
        .xr_en(xr_en), .xr_tgt(xr_tgt), .rot_sel(rot_sel), .msg_y(msg_y), .diag(diag), .perm(perm), .sigma(sigma), .done(done), .busy(busy));
    generate
        for (genvar b = 0; b < NB; b++) begin : g_blk
            logic [4*32-1:0] ea, eb, ey;
            b3_block u_blk (.clk(clk), .ld(ld), .en(en), .add_sel(add_sel), .xr_en(xr_en), .xr_tgt(xr_tgt), .rot_sel(rot_sel),
                .msg_y(msg_y), .diag(diag), .perm(perm), .sigma(sigma), .in_v(in_v[b*512 +: 512]), .in_m(in_m[b*512 +: 512]),
                .in_h(in_h[b*256 +: 256]), .out(out[b*512 +: 512]), .ea(ea), .eb(eb), .ey(ey));
            for (genvar q = 0; q < 4; q++) begin : g_add
                alu_addp #(.W(32)) u_add (.a(ea[q*32 +: 32]), .b(eb[q*32 +: 32]), .y(ey[q*32 +: 32]));
            end
        end
    endgenerate
endmodule
