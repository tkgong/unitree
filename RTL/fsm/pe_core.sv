// pe_core.sv - one processing element: the Monolith-31 core (mono_core) and NB ARX blocks (arx_block, one arx_ctrl).
// HAS_MONO / HAS_CC / HAS_B3 select the primitives the core supports; a run executes ONE primitive (prim) on the whole core.
//   natural kernels: pe_core #(1,0,0) Monolith; #(0,1,0,NB) ChaCha20 (the blocks' adds on 4 NB private alu_addp);
//                    #(0,0,1,NB) BLAKE3
//   shared PE:       pe_core #(1,1,1,NB): the NB blocks' 4 NB adds run on the first 4 NB adders of the Concrete tree
//                    (alu_lend, ext = 1 while prim != MONO); NB <= NTREE / 4 (356 for the 17-shift CSD tree).
// Ports: start with prim; done when the result is on mono_y (prim 2) or arx_out (prim 0 / 1).
module pe_core
#(
    parameter int HAS_MONO = 1,
    parameter int HAS_CC   = 1,
    parameter int HAS_B3   = 1,
    parameter int NB       = 4,
    parameter int MC       = 12
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
    localparam int HAS_ARX = (HAS_CC || HAS_B3) ? 1 : 0;
    localparam int LEND    = (HAS_MONO && HAS_ARX) ? 1 : 0;
    localparam int MODE    = (HAS_CC && HAS_B3) ? 2 : HAS_B3 ? 1 : 0;
    logic ext, m_start, a_start, m_done, a_done, m_busy, a_busy;
    assign ext     = (prim != 2'd2);
    assign m_start = start && (prim == 2'd2);
    assign a_start = start && (prim != 2'd2);
    logic [mono_pkg::NTREE*32-1:0] ea, eb, ey;
    logic [NB*4*32-1:0]  bea, beb, bey;
    generate
        if (HAS_MONO) begin : g_mono
            mono_core #(.MC(MC), .LEND(LEND)) u_mono (.clk(clk), .rst(rst), .start(m_start), .x(mono_x), .y(mono_y),
                .done(m_done), .busy(m_busy), .ext(ext && LEND), .ea(ea), .eb(eb), .ey(ey));
        end else begin : g_nomono
            assign mono_y = '0; assign m_done = 1'b0; assign m_busy = 1'b0; assign ey = '0;
        end
        if (HAS_ARX) begin : g_arx
            logic ld, en, xr_en, xr_tgt, msg_y, diag, perm, sigma, blake;
            logic [1:0] add_sel, ff_row, rot_sel;
            assign blake = (HAS_CC && HAS_B3) ? (prim == 2'd1) : (HAS_B3 ? 1'b1 : 1'b0);
            arx_ctrl u_ctrl (.clk(clk), .rst(rst), .start(a_start), .blake(blake), .ld(ld), .en(en), .add_sel(add_sel),
                .ff_row(ff_row), .xr_en(xr_en), .xr_tgt(xr_tgt), .rot_sel(rot_sel), .msg_y(msg_y), .diag(diag), .perm(perm),
                .sigma(sigma), .done(a_done), .busy(a_busy));
            for (genvar b = 0; b < NB; b++) begin : g_blk
                arx_block #(.MODE(MODE)) u_blk (.clk(clk), .ld(ld), .en(en), .blake(blake), .add_sel(add_sel), .ff_row(ff_row),
                    .xr_en(xr_en), .xr_tgt(xr_tgt), .rot_sel(rot_sel), .msg_y(msg_y), .diag(diag), .perm(perm), .sigma(sigma),
                    .in_v(arx_v[b*512 +: 512]), .in_m(arx_m[b*512 +: 512]), .in_h(arx_h[b*256 +: 256]), .out(arx_out[b*512 +: 512]),
                    .ea(bea[b*128 +: 128]), .eb(beb[b*128 +: 128]), .ey(bey[b*128 +: 128]));
            end
            if (LEND) begin : g_lend                      // the blocks' adds on the tree adders 0 .. 4 NB - 1
                assign ea = {{((mono_pkg::NTREE - 4*NB)*32){1'b0}}, bea};
                assign eb = {{((mono_pkg::NTREE - 4*NB)*32){1'b0}}, beb};
                assign bey = ey[NB*128-1:0];
            end else begin : g_priv                       // private adders
                assign ea = '0; assign eb = '0;
                for (genvar q = 0; q < 4*NB; q++) begin : g_add
                    alu_addp #(.W(32)) u_add (.a(bea[q*32 +: 32]), .b(beb[q*32 +: 32]), .y(bey[q*32 +: 32]));
                end
            end
        end else begin : g_noarx
            assign arx_out = '0; assign a_done = 1'b0; assign a_busy = 1'b0; assign ea = '0; assign eb = '0; assign bey = '0;
        end
    endgenerate
    assign done = (prim == 2'd2) ? m_done : a_done;
    assign busy = m_busy || a_busy;
endmodule
