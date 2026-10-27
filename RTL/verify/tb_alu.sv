// tb_alu.sv - every module of D:\unitree\RTL against the HLS C++ reference vectors (vec/*.hex from gen_vectors.py).
// Each vector line: 64-bit fields, inputs first, expected output last. Run from the directory that holds vec/.
`timescale 1ns/1ps
`define NV 4096

module chk_add #(parameter int W = 32) ();
    logic [W-1:0] a, b, y; logic [191:0] m [0:`NV-1]; int i, e = 0;
    alu_add #(.W(W)) dut (.a(a), .b(b), .y(y));
    initial begin
        $readmemh($sformatf("vec/add_%0d.hex", W), m);
        for (i = 0; i < `NV; i++) begin
            a = m[i][191:128]; b = m[i][127:64]; #1;
            if (y !== m[i][W-1:0]) begin e++; if (e < 4) $display("FAIL add W=%0d a=%h b=%h y=%h exp=%h", W, a, b, y, m[i][W-1:0]); end
        end
        tb_alu.report($sformatf("alu_add<%0d>", W), e);
    end
endmodule

module chk_addp #(parameter int W = 32) ();
    logic [W-1:0] a, b, y; logic [191:0] m [0:`NV-1]; int i, e = 0;
    alu_addp #(.W(W)) dut (.a(a), .b(b), .y(y));
    initial begin
        $readmemh($sformatf("vec/addp_%0d.hex", W), m);
        for (i = 0; i < `NV; i++) begin
            a = m[i][191:128]; b = m[i][127:64]; #1;
            if (y !== m[i][W-1:0]) begin e++; if (e < 4) $display("FAIL addp W=%0d a=%h b=%h y=%h exp=%h", W, a, b, y, m[i][W-1:0]); end
        end
        tb_alu.report($sformatf("alu_addp<%0d>", W), e);
    end
endmodule

module chk_lend #(parameter int W = 32) ();
    logic ext; logic [W-1:0] ea, eb, a, b, y; logic [383:0] m [0:`NV-1]; int i, e = 0;
    alu_lend #(.W(W)) dut (.ext(ext), .ea(ea), .eb(eb), .a(a), .b(b), .y(y));
    initial begin
        $readmemh($sformatf("vec/lend_%0d.hex", W), m);
        for (i = 0; i < `NV; i++) begin
            ext = m[i][320]; ea = m[i][319:256]; eb = m[i][255:192]; a = m[i][191:128]; b = m[i][127:64]; #1;
            if (y !== m[i][W-1:0]) begin e++; if (e < 4) $display("FAIL lend W=%0d ext=%0d y=%h exp=%h", W, ext, y, m[i][W-1:0]); end
        end
        tb_alu.report($sformatf("alu_lend<%0d>", W), e);
    end
endmodule

module chk_lendp #(parameter int W = 32) ();
    logic ext; logic [W-1:0] ea, eb, a, b, y; logic [383:0] m [0:`NV-1]; int i, e = 0;
    alu_lendp #(.W(W)) dut (.ext(ext), .ea(ea), .eb(eb), .a(a), .b(b), .y(y));
    initial begin
        $readmemh($sformatf("vec/lendp_%0d.hex", W), m);
        for (i = 0; i < `NV; i++) begin
            ext = m[i][320]; ea = m[i][319:256]; eb = m[i][255:192]; a = m[i][191:128]; b = m[i][127:64]; #1;
            if (y !== m[i][W-1:0]) begin e++; if (e < 4) $display("FAIL lendp W=%0d ext=%0d y=%h exp=%h", W, ext, y, m[i][W-1:0]); end
        end
        tb_alu.report($sformatf("alu_lendp<%0d>", W), e);
    end
endmodule

module chk_mul31 ();
    logic [30:0] a, b; logic [61:0] y; logic [191:0] m [0:`NV-1]; int i, e = 0;
    alu_mul31 dut (.a(a), .b(b), .y(y));
    initial begin
        $readmemh("vec/mul31.hex", m);
        for (i = 0; i < `NV; i++) begin
            a = m[i][158:128]; b = m[i][94:64]; #1;
            if (y !== m[i][61:0]) begin e++; if (e < 4) $display("FAIL mul31 a=%h b=%h y=%h exp=%h", a, b, y, m[i][61:0]); end
        end
        tb_alu.report("alu_mul31", e);
    end
endmodule

module chk_mul31_en ();
    logic en; logic [30:0] a, b; logic [61:0] y; logic [255:0] m [0:`NV-1]; int i, e = 0;
    alu_mul31_en dut (.en(en), .a(a), .b(b), .y(y));
    initial begin
        $readmemh("vec/mul31_en.hex", m);
        for (i = 0; i < `NV; i++) begin
            en = m[i][192]; a = m[i][158:128]; b = m[i][94:64]; #1;
            if (y !== m[i][61:0]) begin e++; if (e < 4) $display("FAIL mul31_en en=%0d a=%h b=%h y=%h exp=%h", en, a, b, y, m[i][61:0]); end
        end
        tb_alu.report("alu_mul31_en", e);
    end
endmodule

module chk_fold #(parameter int H = 31) ();     // H = 31: alu_fold31 and alu_fold<31> both
    logic [31:0] r; logic [30:0] t, t31; logic [127:0] m [0:`NV-1]; int i, e = 0;
    alu_fold #(.H(H)) dut (.r(r), .t(t));
    generate if (H == 31) begin : g31 alu_fold31 dut31 (.r(r), .t(t31)); end endgenerate
    initial begin
        if (H == 31) $readmemh("vec/fold31.hex", m); else $readmemh($sformatf("vec/fold_%0d.hex", H), m);
        for (i = 0; i < `NV; i++) begin
            r = m[i][95:64]; #1;
            if (t !== m[i][30:0]) begin e++; if (e < 4) $display("FAIL fold H=%0d r=%h t=%h exp=%h", H, r, t, m[i][30:0]); end
            if (H == 31 && t31 !== m[i][30:0]) begin e++; if (e < 4) $display("FAIL fold31 r=%h t=%h exp=%h", r, t31, m[i][30:0]); end
        end
        if (H == 31) tb_alu.report("alu_fold31 + alu_fold<31>", e); else tb_alu.report($sformatf("alu_fold<%0d>", H), e);
    end
endmodule

module chk_canon #(parameter int W = 32) ();
    logic [30:0] t; logic [W-1:0] y; logic [127:0] m [0:`NV-1]; int i, e = 0;
    alu_canon #(.W(W)) dut (.t(t), .y(y));
    initial begin
        $readmemh($sformatf("vec/canon_%0d.hex", W), m);
        for (i = 0; i < `NV; i++) begin
            t = m[i][94:64]; #1;
            if (y !== m[i][W-1:0]) begin e++; if (e < 4) $display("FAIL canon W=%0d t=%h y=%h exp=%h", W, t, y, m[i][W-1:0]); end
        end
        tb_alu.report($sformatf("alu_canon<%0d>", W), e);
    end
endmodule

module chk_negm31 #(parameter int W = 33) ();
    logic [30:0] t; logic [W-1:0] y; logic [127:0] m [0:`NV-1]; int i, e = 0;
    alu_negm31 #(.W(W)) dut (.t(t), .y(y));
    initial begin
        $readmemh($sformatf("vec/negm31_%0d.hex", W), m);
        for (i = 0; i < `NV; i++) begin
            t = m[i][94:64]; #1;
            if (y !== m[i][W-1:0]) begin e++; if (e < 4) $display("FAIL negm31 W=%0d t=%h y=%h exp=%h", W, t, y, m[i][W-1:0]); end
        end
        tb_alu.report($sformatf("alu_negm31<%0d>", W), e);
    end
endmodule

module chk_bar_chunk #(parameter int W = 8) ();
    logic [W-1:0] x, y; logic [127:0] m [0:`NV-1]; int i, e = 0;
    alu_bar_chunk #(.W(W)) dut (.x(x), .y(y));
    initial begin
        $readmemh($sformatf("vec/bar_chunk_%0d.hex", W), m);
        for (i = 0; i < `NV; i++) begin
            x = m[i][64+W-1:64]; #1;
            if (y !== m[i][W-1:0]) begin e++; if (e < 4) $display("FAIL bar_chunk W=%0d x=%h y=%h exp=%h", W, x, y, m[i][W-1:0]); end
        end
        tb_alu.report($sformatf("alu_bar_chunk<%0d> (exhaustive)", W), e);
    end
endmodule

module chk_bar31 ();
    logic [31:0] x, y; logic [127:0] m [0:`NV-1]; int i, e = 0;
    alu_bar31 dut (.x(x), .y(y));
    initial begin
        $readmemh("vec/bar31.hex", m);
        for (i = 0; i < `NV; i++) begin
            x = m[i][95:64]; #1;
            if (y !== m[i][31:0]) begin e++; if (e < 4) $display("FAIL bar31 x=%h y=%h exp=%h", x, y, m[i][31:0]); end
        end
        tb_alu.report("alu_bar31", e);
    end
endmodule

module chk_xor ();
    logic [63:0] a, b, y; logic [191:0] m [0:`NV-1]; int i, e = 0;
    alu_xor dut (.a(a), .b(b), .y(y));
    initial begin
        $readmemh("vec/xor.hex", m);
        for (i = 0; i < `NV; i++) begin
            a = m[i][191:128]; b = m[i][127:64]; #1;
            if (y !== m[i][63:0]) begin e++; if (e < 4) $display("FAIL xor a=%h b=%h y=%h exp=%h", a, b, y, m[i][63:0]); end
        end
        tb_alu.report("alu_xor", e);
    end
endmodule

module chk_rot31 #(parameter int R = 0) ();
    logic [30:0] v, y; logic [127:0] m [0:`NV-1]; int i, e = 0;
    rot31 #(.R(R)) dut (.v(v), .y(y));
    initial begin
        $readmemh($sformatf("vec/rot31_%0d.hex", R), m);
        for (i = 0; i < `NV; i++) begin
            v = m[i][94:64]; #1;
            if (y !== m[i][30:0]) begin e++; if (e < 4) $display("FAIL rot31 R=%0d v=%h y=%h exp=%h", R, v, y, m[i][30:0]); end
        end
        tb_alu.report($sformatf("rot31<%0d>", R), e);
    end
endmodule

module tb_alu ();
    int blocks = 0, fails = 0, vectors = 0;
    task automatic report(input string name, input int e);
        blocks++; vectors += `NV; if (e != 0) fails++;
        if (e == 0) $display("%-34s OK    (%0d vectors)", name, `NV); else $display("%-34s FAIL  (%0d vectors, %0d mismatches)", name, `NV, e);
    endtask
    genvar W, H, R;
    generate
        for (W = 32; W <= 41; W++) begin : g_add
            chk_add  #(.W(W)) u_add ();
            chk_addp #(.W(W)) u_addp ();
            chk_lend #(.W(W)) u_lend ();
            chk_lendp #(.W(W)) u_lendp ();
        end
        for (H = 1; H <= 31; H++) begin : g_fold chk_fold #(.H(H)) u (); end
        for (W = 31; W <= 35; W++) begin : g_neg chk_negm31 #(.W(W)) u (); end
        for (R = 0; R <= 30; R++) begin : g_rot chk_rot31 #(.R(R)) u (); end
    endgenerate
    chk_mul31 u_mul (); chk_mul31_en u_mulen ();
    chk_canon #(.W(32)) u_canon32 (); chk_canon #(.W(31)) u_canon31 ();
    chk_bar_chunk #(.W(8)) u_bc8 (); chk_bar_chunk #(.W(7)) u_bc7 (); chk_bar31 u_bar ();
    chk_xor u_xor ();
    initial begin
        #(`NV + 100);
        $display("SUMMARY: %0d module instances, %0d vectors, %0d instances with mismatches", blocks, vectors, fails);
        $finish;
    end
endmodule
