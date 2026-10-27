// arx_ctrl.sv - the FSM of the ARX engine: one controller drives every arx_block of the core in lockstep.
// ChaCha20: 20 half-rounds of 4 steps (a+b, d^=a <<<16 | c+d, b^=c <<<12 | a+b, d^=a <<<8 | c+d, b^=c <<<7), P after each
// half-round, then 4 feed-forward steps (row r += input row r): 84 steps. BLAKE3: 14 half-rounds of 6 steps (a+b | a+mx,
// d^=a >>>16 | c+d, b^=c >>>12 | a+b | a+my, d^=a >>>8 | c+d, b^=c >>>7), P after each half-round, SIGMA on the message
// after every second one: 84 steps. done stays high (outputs valid) until the next start.
module arx_ctrl (
    input  logic       clk,
    input  logic       rst,
    input  logic       start,
    input  logic       blake,
    output logic       ld,
    output logic       en,
    output logic [1:0] add_sel,
    output logic [1:0] ff_row,
    output logic       xr_en,
    output logic       xr_tgt,
    output logic [1:0] rot_sel,
    output logic       msg_y,
    output logic       diag,
    output logic       perm,
    output logic       sigma,
    output logic       done,
    output logic       busy
);
    typedef enum logic [1:0] {IDLE, RUN, FF, FIN} st_t;
    st_t   st;
    logic [2:0] step;                            // step inside the half-round
    logic [4:0] hr;                              // half-round
    logic [1:0] ffr;
    logic       last_step, last_hr;
    assign last_step = blake ? (step == 3'd5) : (step == 3'd3);
    assign last_hr   = blake ? (hr == 5'd13) : (hr == 5'd19);
    always_ff @(posedge clk) begin
        if (rst) begin
            st <= IDLE; step <= '0; hr <= '0; ffr <= '0;
        end else begin
            case (st)
                IDLE: if (start) begin st <= RUN; step <= '0; hr <= '0; ffr <= '0; end
                RUN: begin
                    if (last_step) begin
                        step <= '0;
                        if (last_hr) begin
                            hr <= '0;
                            if (blake) st <= FIN; else st <= FF;
                        end else hr <= hr + 5'd1;
                    end else step <= step + 3'd1;
                end
                FF: begin
                    if (ffr == 2'd3) st <= FIN;
                    ffr <= ffr + 2'd1;
                end
                FIN: if (start) begin st <= RUN; step <= '0; hr <= '0; ffr <= '0; end
            endcase
        end
    end
    assign ld   = start;
    assign en   = (st == RUN) || (st == FF);
    assign busy = en;
    assign done = (st == FIN);
    assign ff_row = ffr;
    assign diag   = hr[0];
    always_comb begin
        add_sel = 2'd0; xr_en = 1'b0; xr_tgt = 1'b0; rot_sel = 2'd0; msg_y = 1'b0; perm = 1'b0; sigma = 1'b0;
        if (st == FF) begin
            add_sel = 2'd3;
        end else if (st == RUN) begin
            if (blake) begin
                case (step)
                    3'd0: begin add_sel = 2'd0; end
                    3'd1: begin add_sel = 2'd1; msg_y = 1'b0; xr_en = 1'b1; xr_tgt = 1'b0; rot_sel = 2'd0; end
                    3'd2: begin add_sel = 2'd2; xr_en = 1'b1; xr_tgt = 1'b1; rot_sel = 2'd1; end
                    3'd3: begin add_sel = 2'd0; end
                    3'd4: begin add_sel = 2'd1; msg_y = 1'b1; xr_en = 1'b1; xr_tgt = 1'b0; rot_sel = 2'd2; end
                    default: begin add_sel = 2'd2; xr_en = 1'b1; xr_tgt = 1'b1; rot_sel = 2'd3; perm = 1'b1; sigma = hr[0]; end
                endcase
            end else begin
                case (step)
                    3'd0: begin add_sel = 2'd0; xr_en = 1'b1; xr_tgt = 1'b0; rot_sel = 2'd0; end
                    3'd1: begin add_sel = 2'd2; xr_en = 1'b1; xr_tgt = 1'b1; rot_sel = 2'd1; end
                    3'd2: begin add_sel = 2'd0; xr_en = 1'b1; xr_tgt = 1'b0; rot_sel = 2'd2; end
                    default: begin add_sel = 2'd2; xr_en = 1'b1; xr_tgt = 1'b1; rot_sel = 2'd3; perm = 1'b1; end
                endcase
            end
        end
    end
endmodule
