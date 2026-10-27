// tb_unit.sv - unit_bz3 (two PEs) against the HLS C++ (lz3_16.dll), clock by clock, every output lane every cycle.
// The DLL call t computes lout from the registers before its update, then updates them: here the inputs of cycle t are
// applied after the falling edge, lout is compared before the rising edge, and the rising edge is the update.
`timescale 1ns/1ps
`ifndef NCYC
`define NCYC 300
`endif
module tb_unit;
    localparam int NIO = 1248, NG = 28, N = `NCYC;
    logic clk = 0, rst = 1;
    always #5 clk = ~clk;
    logic [NIO*64-1:0] lin, lout;
    logic mono, mono2, htap, blake;
    logic [8:0] r, r2;
    logic [NG*9-1:0] rg;
    unit_bz3 dut (.clk(clk), .rst(rst), .lin(lin), .lout(lout), .mono(mono), .mono2(mono2), .htap(htap), .blake(blake), .r(r), .r2(r2), .rg(rg));
    logic [NG*9+21:0] ctrl [0:N-1];
    logic [63:0] vin  [0:N*NIO-1];
    logic [63:0] vout [0:N*NIO-1];
    int t, i, bad = 0, badcyc = 0, nz = 0;
    initial begin
        $readmemh("vec/ctrl.hex", ctrl); $readmemh("vec/lin.hex", vin); $readmemh("vec/lout.hex", vout);
        {rg, r2, r, blake, htap, mono2, mono} = '0; lin = '0;
        @(posedge clk); #1 rst = 0;                               // reset clears every register (the DLL starts from zero)
        for (t = 0; t < N; t++) begin
            @(negedge clk);
            {rg, r2, r, blake, htap, mono2, mono} = ctrl[t];
            for (i = 0; i < NIO; i++) lin[64*i +: 64] = vin[t*NIO + i];
            #1;
            begin
                int e; e = 0;
                for (i = 0; i < NIO; i++) begin
                    if (lout[64*i +: 64] !== vout[t*NIO + i]) begin
                        e++; if (bad + e <= 5) $display("cycle %0d lane %0d: got %h expected %h", t, i, lout[64*i +: 64], vout[t*NIO + i]);
                    end
                    if (vout[t*NIO + i] != 0) nz++;
                end
                bad += e; if (e) badcyc++;
            end
        end
        $display("SUMMARY: %0d cycles x %0d lanes compared, %0d nonzero expected lanes, %0d mismatching lanes in %0d cycles", N, NIO, nz, bad, badcyc);
        $finish;
    end
endmodule
