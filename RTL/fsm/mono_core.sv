// mono_core.sv - the Monolith-31 permutation (width 16): 16 state registers of 31 bits, one mono_round, an FSM.
// A permutation is 7 passes of the round function: pass 0 Concrete only (bypass), passes 1..6 Bars + Bricks + Concrete
// with the round constant RC[pass-1] on passes 1..5. The round is a multicycle combinational path: the FSM holds the state
// for MC cycles per pass and then latches the result, so 7 x MC cycles per permutation (84 at MC = 12).
// start loads x (canonical elements, 31 bits each) and runs; done is high while the result is on y (canonical).
module mono_core
#(
    parameter int MC   = 12,
    parameter int LEND = 1
) (
    input  logic                clk,
    input  logic                rst,
    input  logic                start,
    input  logic [16*31-1:0]    x,
    output logic [16*31-1:0]    y,
    output logic                done,
    output logic                busy,
    input  logic                ext,          // the tree adders serve the ARX blocks (the FSM is idle then)
    input  logic [mono_pkg::NTREE*32-1:0] ea,
    input  logic [mono_pkg::NTREE*32-1:0] eb,
    output logic [mono_pkg::NTREE*32-1:0] ey
);
    logic [16*31-1:0] s, rnd, rc;
    logic [2:0]       pass;                    // 0..6
    logic [7:0]       cnt;
    logic             run;
    logic             bypass;
    assign bypass = (pass == 3'd0);
    generate
        for (genvar i = 0; i < 16; i++) begin : g_rc
            always_comb begin
                case (pass)
                    3'd1: rc[i*31 +: 31] = mono_pkg::RC(0, i);
                    3'd2: rc[i*31 +: 31] = mono_pkg::RC(1, i);
                    3'd3: rc[i*31 +: 31] = mono_pkg::RC(2, i);
                    3'd4: rc[i*31 +: 31] = mono_pkg::RC(3, i);
                    3'd5: rc[i*31 +: 31] = mono_pkg::RC(4, i);
                    default: rc[i*31 +: 31] = '0;
                endcase
            end
        end
    endgenerate
    mono_round #(.LEND(LEND)) u_round (.x(s), .bypass(bypass), .rc(rc), .y(rnd), .ext(ext), .ea(ea), .eb(eb), .ey(ey));
    always_ff @(posedge clk) begin
        if (rst) begin
            run <= 1'b0; done <= 1'b0; pass <= '0; cnt <= '0; s <= '0;
        end else if (start) begin
            s <= x; run <= 1'b1; done <= 1'b0; pass <= '0; cnt <= '0;
        end else if (run) begin
            if (cnt == MC - 1) begin
                s <= rnd; cnt <= '0;
                if (pass == 3'd6) begin run <= 1'b0; done <= 1'b1; end
                else pass <= pass + 3'd1;
            end else cnt <= cnt + 8'd1;
        end
    end
    assign busy = run;
    generate
        for (genvar i = 0; i < 16; i++) begin : g_out
            alu_canon #(.W(31)) u_canon (.t(s[i*31 +: 31]), .y(y[i*31 +: 31]));
        end
    endgenerate
endmodule
