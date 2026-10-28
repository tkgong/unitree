// top_mono.sv - the natural Monolith-31 kernel: one mono_core with private adders (alu_addp everywhere).
module top_mono #(
    parameter int MC = 12
) (
    input  logic             clk,
    input  logic             rst,
    input  logic             start,
    input  logic [16*31-1:0] x,
    output logic [16*31-1:0] y,
    output logic             done,
    output logic             busy
);
    logic [mono_pkg::NTREE*32-1:0] ey_unused;
    mono_core #(.MC(MC), .LEND(0)) u_mono (.clk(clk), .rst(rst), .start(start), .x(x), .y(y), .done(done), .busy(busy),
        .ext(1'b0), .ea('0), .eb('0), .ey(ey_unused));
endmodule
