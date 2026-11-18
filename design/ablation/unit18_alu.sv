module unit18_alu (
    input  logic              clk,
    input  logic              rst,
    input  logic [324*64-1:0] lin_c,
    output logic [324*64-1:0] lout_c,
    input  logic [396*64-1:0] lin_b,
    output logic [396*64-1:0] lout_b,
    input  logic [16*64-1:0]  lin_m,
    output logic [16*64-1:0]  lout_m,
    input  logic              mono, mono2, blake,
    input  logic [8:0]        r, r2,
    input  logic [2*9-1:0]    rg_c,
    input  logic [2*9-1:0]    rg_b
);
    localparam int NA  = 216;
    localparam int MPR = 4;
    localparam int NBC = NA / MPR;
    logic [NA*32-1:0] ca0, cb0, ca1, cb1;
    logic [NA*32-1:0] ba0, bb0, ba1, bb1;
    logic [NA*32-1:0] ea0, eb0, ey0, ea1, eb1, ey1;
    logic [NBC-1:0]   bi0, bi1, bq0, bq1;
`ifdef KS45
    generate for (genvar c = 0; c < NBC; c++) begin : g_bc
        BUF_X1 u_0 (.A(blake), .Z(bi0[c]));
        BUF_X1 u_1 (.A(blake), .Z(bi1[c]));
    end endgenerate
`else
    assign bi0 = {NBC{blake}};
    assign bi1 = {NBC{blake}};
`endif
    (* keep *) always_ff @(posedge clk) begin bq0 <= bi0; bq1 <= bi1; end
    generate for (genvar q = 0; q < NA; q++) begin : g_op
        assign ea0[q*32 +: 32] = bq0[q / MPR] ? ba0[q*32 +: 32] : ca0[q*32 +: 32];
        assign eb0[q*32 +: 32] = bq0[q / MPR] ? bb0[q*32 +: 32] : cb0[q*32 +: 32];
        assign ea1[q*32 +: 32] = bq1[q / MPR] ? ba1[q*32 +: 32] : ca1[q*32 +: 32];
        assign eb1[q*32 +: 32] = bq1[q / MPR] ? bb1[q*32 +: 32] : cb1[q*32 +: 32];
    end endgenerate
    mono_dp18 #(.NL(NA)) u_dp0 (.clk(clk), .rst(rst), .x(lin_m[0 +: 8*64]), .mono(mono), .r(r), .y(lout_m[0 +: 8*64]),
        .ea(ea0), .eb(eb0), .ey(ey0));
    mono_dp18 #(.NL(NA)) u_dp1 (.clk(clk), .rst(rst), .x(lin_m[8*64 +: 8*64]), .mono(mono2), .r(r2), .y(lout_m[8*64 +: 8*64]),
        .ea(ea1), .eb(eb1), .ey(ey1));
    arx_group #(.NBK(9), .BL(18), .CP(0), .PRIV(0), .BKC(0)) u_c0 (.clk(clk), .x(lin_c[0 +: 9*18*64]), .r(rg_c[0 +: 9]), .blake(1'b0),
        .y(lout_c[0 +: 9*18*64]), .ea(ca0), .eb(cb0), .ey(ey0));
    arx_group #(.NBK(9), .BL(18), .CP(1), .PRIV(0), .BKC(0)) u_c1 (.clk(clk), .x(lin_c[162*64 +: 9*18*64]), .r(rg_c[9 +: 9]), .blake(1'b0),
        .y(lout_c[162*64 +: 9*18*64]), .ea(ca1), .eb(cb1), .ey(ey1));
    arx_group #(.NBK(9), .BL(22), .CP(0), .PRIV(0), .BKC(1)) u_b0 (.clk(clk), .x(lin_b[0 +: 9*22*64]), .r(rg_b[0 +: 9]), .blake(1'b1),
        .y(lout_b[0 +: 9*22*64]), .ea(ba0), .eb(bb0), .ey(ey0));
    arx_group #(.NBK(9), .BL(22), .CP(1), .PRIV(0), .BKC(1)) u_b1 (.clk(clk), .x(lin_b[198*64 +: 9*22*64]), .r(rg_b[9 +: 9]), .blake(1'b1),
        .y(lout_b[198*64 +: 9*22*64]), .ea(ba1), .eb(bb1), .ey(ey1));
endmodule
