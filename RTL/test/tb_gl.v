// tb_gl.v - Icarus Verilog: the gate-level netlist <top>_gl.v (zero delay, the Nangate45 cells' functions written by Yosys
// from the liberty) replays a program phase by phase from the stimulus the RTL testbench wrote (tb_unit18.cpp STIM=: every
// input per clock phase, and the RTL's lout after that phase), checks lout against the RTL at every phase after the reset /
// warm-up, and dumps every net of the netlist between phases FROM and TO (VCD) for the switching activity
// (benchmark/power/power_vcd.sh).
//   iverilog -g2012 -DTOP=unit18_<top> -Ptb.W=<lane bits> -Ptb.RG=<rg bits> ng45_cells.v <top>_gl.v tb_gl.v  (once per top)
//   vvp -n <compiled> +STIM=<file> +VCD=<file> +FROM=<phase> +TO=<phase>   (stops after phase TO)
`timescale 1ps/1ps
module tb;
    parameter integer W = 20736, RG = 18, CHK = 43;
    integer FROM, TO;
    reg [8*1024-1:0] stimf, vcdf;
    reg clk, rst, mono, mono2, htap, blake;
    reg [8:0] r, r2;
    reg [RG-1:0] rg;
    reg [W-1:0] lin, ex;
    wire [W-1:0] lout;
    `TOP dut (.clk(clk), .rst(rst), .mono(mono), .mono2(mono2), .htap(htap), .blake(blake), .r(r), .r2(r2), .rg(rg),
              .lin(lin), .lout(lout));
    integer f, n, ph, bad, badph;
    initial begin
        if (!$value$plusargs("STIM=%s", stimf) || !$value$plusargs("VCD=%s", vcdf) || !$value$plusargs("FROM=%d", FROM)
            || !$value$plusargs("TO=%d", TO)) begin $display("usage: +STIM= +VCD= +FROM= +TO="); $finish; end
        f = $fopen(stimf, "r"); ph = 0; bad = 0; badph = 0;
        $dumpfile(vcdf); $dumpvars(1, dut); $dumpoff;
        while (f != 0) begin
            n = $fscanf(f, "%d %d %d %d %d %d %h %h %h %h %h\n", clk, rst, mono, mono2, htap, blake, r, r2, rg, lin, ex);
            if (n != 11) begin $display("STIM read stops at phase %0d (%0d fields)", ph, n); $fclose(f); f = 0; end
            else begin
                if (ph == FROM) $dumpon;
                #1;
                if (ph >= CHK && lout !== ex) begin
                    bad = bad + 1;
                    if (badph < 3) $display("phase %0d: lout differs from the RTL", ph);
                    badph = badph + 1;
                end
                if (ph == TO) begin $dumpoff; $fclose(f); f = 0; end
                #499;
                ph = ph + 1;
            end
        end
        $display("GATE: %0d phases replayed, %0d phases with lout different from the RTL (checked from phase %0d)", ph, bad, CHK);
        $finish;
    end
endmodule
