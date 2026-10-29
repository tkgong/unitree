// wrap_shared_b.sv - area-attribution harness only (not a design top): unit18_shared with blake tied to BLK, so the
// flat synthesis folds the other primitive's ARX paths exactly as the natural unit18_chacha (BLK = 0) / unit18_blake3
// (BLK = 1) tops do. Compares what the live blake select costs the shared unit.
module wrap_shared_b #(
    parameter int BLK = 0
) (
    input  logic            clk,
    input  logic            rst,
    input  logic [456*64-1:0] lin,
    output logic [456*64-1:0] lout,
    input  logic            mono, mono2, htap,
    input  logic [8:0]      r, r2,
    input  logic [4*9-1:0]  rg
);
    unit18_shared u (.clk(clk), .rst(rst), .lin(lin), .lout(lout), .mono(mono), .mono2(mono2), .htap(htap),
                     .blake(BLK[0]), .r(r), .r2(r2), .rg(rg));
endmodule
