// unit18_arx.sv - the ChaCha20 + BLAKE3 unit without Monolith-31, hand-written: the four block groups of unit18_shared
// (5 + 4 blocks per PE, copies 0 / 1, the same lanes and controls) with private adders (4 per block step). The pair
// baseline of the Monolith <-> ARX sharing: unit18_mono + unit18_arx against unit18_shared. The shared ChaCha20 layout
// (LAY = 1, axn_step.sv) as in unit18_shared: it saves the same selects here.
module unit18_arx (
    input  logic            clk,
    input  logic            rst,
    input  logic [396*64-1:0] lin,
    output logic [396*64-1:0] lout,
    input  logic            mono, mono2, htap, blake,
    input  logic [8:0]      r, r2,
    input  logic [4*9-1:0]  rg
);
    localparam int BL = 22;
    logic [120*32-1:0] nc_a0, nc_b0, nc_a2, nc_b2;
    logic [96*32-1:0]  nc_a1, nc_b1, nc_a3, nc_b3;
    arx_group #(.NBK(5), .BL(BL), .CP(0), .PRIV(1), .LAY(1)) u_g0 (.clk(clk), .x(lin[0 +: 5*BL*64]), .r(rg[0 +: 9]), .blake(blake),
        .y(lout[0 +: 5*BL*64]), .ea(nc_a0), .eb(nc_b0), .ey('0));
    arx_group #(.NBK(4), .BL(BL), .CP(0), .PRIV(1), .LAY(1)) u_g1 (.clk(clk), .x(lin[110*64 +: 4*BL*64]), .r(rg[9 +: 9]), .blake(blake),
        .y(lout[110*64 +: 4*BL*64]), .ea(nc_a1), .eb(nc_b1), .ey('0));
    arx_group #(.NBK(5), .BL(BL), .CP(1), .PRIV(1), .LAY(1)) u_g2 (.clk(clk), .x(lin[198*64 +: 5*BL*64]), .r(rg[18 +: 9]), .blake(blake),
        .y(lout[198*64 +: 5*BL*64]), .ea(nc_a2), .eb(nc_b2), .ey('0));
    arx_group #(.NBK(4), .BL(BL), .CP(1), .PRIV(1), .LAY(1)) u_g3 (.clk(clk), .x(lin[308*64 +: 4*BL*64]), .r(rg[27 +: 9]), .blake(blake),
        .y(lout[308*64 +: 4*BL*64]), .ea(nc_a3), .eb(nc_b3), .ey('0));
endmodule
