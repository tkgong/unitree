module unit18_blake3 (
    input  logic            clk,
    input  logic            rst,
    input  logic [396*64-1:0] lin,
    output logic [396*64-1:0] lout,
    input  logic            mono, mono2, htap, blake,
    input  logic [8:0]      r, r2,
    input  logic [2*9-1:0]  rg
);
    localparam int BL = 22;
    logic [216*32-1:0] nc_a0, nc_b0, nc_a1, nc_b1;
    arx_group #(.NBK(9), .BL(BL), .CP(0), .PRIV(1), .BKC(1)) u_g0 (.clk(clk), .x(lin[0 +: 9*BL*64]), .r(rg[0 +: 9]), .blake(1'b1),
        .y(lout[0 +: 9*BL*64]), .ea(nc_a0), .eb(nc_b0), .ey('0));
    arx_group #(.NBK(9), .BL(BL), .CP(1), .PRIV(1), .BKC(1)) u_g1 (.clk(clk), .x(lin[198*64 +: 9*BL*64]), .r(rg[9 +: 9]), .blake(1'b1),
        .y(lout[198*64 +: 9*BL*64]), .ea(nc_a1), .eb(nc_b1), .ey('0));
endmodule
