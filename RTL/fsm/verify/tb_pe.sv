// tb_pe.sv - the four tops against the Python reference models (vec/*.hex from gen_vectors.py): NT runs of every
// primitive the top supports, every output word compared. TOP selects top_mono / top_chacha / top_blake3 / top_shared.
`timescale 1ns/1ps
`ifndef NB
`define NB 4
`endif
`ifndef NT
`define NT 3
`endif
`ifndef TOP
`define TOP shared
`endif
`define S(x) `"x`"
module tb_pe;
    localparam int NB = `NB, NT = `NT;
    logic clk = 0, rst = 1, start = 0;
    always #5 clk = ~clk;
    logic [1:0] prim;
    logic [16*31-1:0] mono_x, mono_y;
    logic [NB*512-1:0] arx_v, arx_m, arx_out;
    logic [NB*256-1:0] arx_h;
    logic done, busy;
    logic has_mono = 0, has_cc = 0, has_b3 = 0;
`ifdef TOP_MONO
    top_mono dut (.clk(clk), .rst(rst), .start(start), .x(mono_x), .y(mono_y), .done(done), .busy(busy));
    assign arx_out = '0; initial has_mono = 1;
`elsif TOP_CHACHA
    top_chacha #(.NB(NB)) dut (.clk(clk), .rst(rst), .start(start), .in_v(arx_v), .out(arx_out), .done(done), .busy(busy));
    assign mono_y = '0; initial has_cc = 1;
`elsif TOP_BLAKE3
    top_blake3 #(.NB(NB)) dut (.clk(clk), .rst(rst), .start(start), .in_v(arx_v), .in_m(arx_m), .in_h(arx_h), .out(arx_out), .done(done), .busy(busy));
    assign mono_y = '0; initial has_b3 = 1;
`else
    top_shared #(.NB(NB)) dut (.clk(clk), .rst(rst), .start(start), .prim(prim), .mono_x(mono_x), .mono_y(mono_y),
        .arx_v(arx_v), .arx_m(arx_m), .arx_h(arx_h), .arx_out(arx_out), .done(done), .busy(busy));
    initial begin has_mono = 1; has_cc = 1; has_b3 = 1; end
`endif
    logic [31:0] cc_in [0:NT*NB*16-1], cc_out [0:NT*NB*16-1], b3_v [0:NT*NB*16-1], b3_m [0:NT*NB*16-1], b3_h [0:NT*NB*8-1],
                 b3_out [0:NT*NB*16-1], mo_in [0:NT*16-1], mo_out [0:NT*16-1];
    int t, b, i, bad = 0, cyc, n = 0;
    task automatic run(input logic [1:0] p);
        @(negedge clk); start = 1; prim = p; @(negedge clk); start = 0; cyc = 0;
        while (!done) begin @(negedge clk); cyc++; end
    endtask
    initial begin
        $readmemh("vec/cc_in.hex", cc_in); $readmemh("vec/cc_out.hex", cc_out);
        $readmemh("vec/b3_v.hex", b3_v); $readmemh("vec/b3_m.hex", b3_m); $readmemh("vec/b3_h.hex", b3_h); $readmemh("vec/b3_out.hex", b3_out);
        $readmemh("vec/mono_in.hex", mo_in); $readmemh("vec/mono_out.hex", mo_out);
        prim = 0; mono_x = '0; arx_v = '0; arx_m = '0; arx_h = '0;
        repeat (2) @(negedge clk); rst = 0;
        for (t = 0; t < NT; t++) begin
            if (has_cc) begin
                for (b = 0; b < NB; b++) for (i = 0; i < 16; i++) begin arx_v[(b*16 + i)*32 +: 32] = cc_in[(t*NB + b)*16 + i]; arx_m[(b*16 + i)*32 +: 32] = cc_in[(t*NB + b)*16 + i]; end
                run(2'd0); n++;
                for (b = 0; b < NB; b++) for (i = 0; i < 16; i++)
                    if (arx_out[(b*16 + i)*32 +: 32] !== cc_out[(t*NB + b)*16 + i]) begin bad++; if (bad <= 5) $display("ChaCha run %0d block %0d word %0d: got %h expected %h", t, b, i, arx_out[(b*16 + i)*32 +: 32], cc_out[(t*NB + b)*16 + i]); end
                $display("ChaCha20 run %0d: %0d cycles, %0d blocks", t, cyc, NB);
            end
            if (has_b3) begin
                for (b = 0; b < NB; b++) begin
                    for (i = 0; i < 16; i++) begin arx_v[(b*16 + i)*32 +: 32] = b3_v[(t*NB + b)*16 + i]; arx_m[(b*16 + i)*32 +: 32] = b3_m[(t*NB + b)*16 + i]; end
                    for (i = 0; i < 8; i++) arx_h[(b*8 + i)*32 +: 32] = b3_h[(t*NB + b)*8 + i];
                end
                run(2'd1); n++;
                for (b = 0; b < NB; b++) for (i = 0; i < 16; i++)
                    if (arx_out[(b*16 + i)*32 +: 32] !== b3_out[(t*NB + b)*16 + i]) begin bad++; if (bad <= 5) $display("BLAKE3 run %0d block %0d word %0d: got %h expected %h", t, b, i, arx_out[(b*16 + i)*32 +: 32], b3_out[(t*NB + b)*16 + i]); end
                $display("BLAKE3 run %0d: %0d cycles, %0d blocks", t, cyc, NB);
            end
            if (has_mono) begin
                for (i = 0; i < 16; i++) mono_x[i*31 +: 31] = mo_in[t*16 + i][30:0];
                run(2'd2); n++;
                for (i = 0; i < 16; i++)
                    if (mono_y[i*31 +: 31] !== mo_out[t*16 + i][30:0]) begin bad++; if (bad <= 5) $display("Monolith run %0d word %0d: got %h expected %h", t, i, mono_y[i*31 +: 31], mo_out[t*16 + i]); end
                $display("Monolith run %0d: %0d cycles", t, cyc);
            end
        end
        $display("SUMMARY: top %s NB %0d: %0d runs, %0d mismatching words", `S(`TOP), NB, n, bad);
        $finish;
    end
endmodule
