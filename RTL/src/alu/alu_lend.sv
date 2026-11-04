// ALU-ADD operand select (alu_lend<W>): the ARX operands (ea, eb) when ext (no datapath issue at this level), else the
// datapath's own (a, b); the sum feeds both (the ARX block takes y[31:0] as EY).
// MA / MB = 1: the ARX operand path already delivers a / b in the datapath's programs (the ARX register the ARX operand
// reads is the register of the datapath operand, kara_pkg LEND_TAB): no select on bits 31..0; the bits above (the
// datapath's only) are 0 when ext.
module alu_lend #(
    parameter int W  = 32,
    parameter bit MA = 0,
    parameter bit MB = 0
) (
    input  logic         ext,
    input  logic [W-1:0] ea,
    input  logic [W-1:0] eb,
    input  logic [W-1:0] a,
    input  logic [W-1:0] b,
    output logic [W-1:0] y
);
    logic [W-1:0] la, lb;
    generate
        if (MA) begin : g_ma
            assign la[31:0] = ea[31:0];
            if (W > 32) begin : g_hi
                assign la[W-1:32] = ext ? '0 : a[W-1:32];
            end
        end else begin : g_sa
            assign la = ext ? ea : a;
        end
        if (MB) begin : g_mb
            assign lb[31:0] = eb[31:0];
            if (W > 32) begin : g_hi
                assign lb[W-1:32] = ext ? '0 : b[W-1:32];
            end
        end else begin : g_sb
            assign lb = ext ? eb : b;
        end
    endgenerate
    alu_add #(.W(W)) u_add (.a(la), .b(lb), .y(y));
endmodule
