// arx_group.sv - one ARX block group of the HLS unit (dse/TOP/level_ops_axn.h, pipe_axn.h): NBK blocks of BL lanes
// (22: ChaCha20 / BLAKE3 with the chaining-value lanes, 18: ChaCha20 only) enter together from the input vector and pass
// six pipeline levels, one ARX step per level: step s reads the block lanes X_s (s = 1: the input; else the level s-1
// register), axn_ops forms the four adds' operands, the adders return the sums, axn_fin forms the step's lanes, and the
// level register takes them on the lanes the step writes (WMASK) and X_s elsewhere. The traversal's round index r and
// blake travel with the group, registered per block (level 1 uses the inputs, level s the copies registered at level
// s-1: the selects they drive are the critical path, so no copy fans out beyond its block). Out: the level-6 register.
// Latency 6 (the program's ring of 7 slots re-issues the group).
// PRIV = 1: each block step has its own four alu_addp (the natural units); PRIV = 0: the 4 x NBK x 6 adds go out on
// ea / eb and come back on ey (the shared unit lends them from a Monolith datapath).
module arx_group #(
    parameter int NBK  = 5,
    parameter int BL   = 22,
    parameter int CP   = 0,
    parameter int PRIV = 0,
    parameter int NA   = 4 * NBK * 6
) (
    input  logic                 clk,
    input  logic [NBK*BL*64-1:0] x,
    input  logic [8:0]           r,
    input  logic                 blake,
    output logic [NBK*BL*64-1:0] y,
    output logic [NA*32-1:0]     ea,
    output logic [NA*32-1:0]     eb,
    input  logic [NA*32-1:0]     ey
);
    function automatic bit wmask(input int s, input int l);   // lanes step s writes
        case (s)
            1, 4: wmask = (l < 8) || (l == 16) || (l == 17);
            2:    wmask = (l < 8);
            3:    wmask = (l == 1) || (l == 2) || (l == 5) || (l == 6);
            5:    wmask = (l == 0) || (l == 3) || (l == 4) || (l == 7);
            default: wmask = (l < 16);
        endcase
    endfunction
    wire  [NBK*BL*64-1:0] R [0:6];                           // R[0] = the input, R[s] = the level-s register
    wire  [8:0]           ar [0:5][0:NBK-1];                 // r / blake at level s for block b
    wire                  bk [0:5][0:NBK-1];
    assign R[0] = x;
    generate
        for (genvar b = 0; b < NBK; b++) begin : g_ctl0
            assign ar[0][b] = r;
            assign bk[0][b] = blake;
        end
        for (genvar s = 1; s <= 5; s++) begin : g_ctl
            for (genvar b = 0; b < NBK; b++) begin : g_blk
                logic [8:0] ar_q;
                logic       bk_q;
                (* keep *) always_ff @(posedge clk) begin ar_q <= ar[s - 1][b]; bk_q <= bk[s - 1][b]; end   // keep: no opt_merge of the copies
                assign ar[s][b] = ar_q;
                assign bk[s][b] = bk_q;
            end
        end
    endgenerate
    generate
        for (genvar s = 1; s <= 6; s++) begin : g_step
            logic [NBK*BL*64-1:0] nxt;
            for (genvar b = 0; b < NBK; b++) begin : g_blk
                localparam int Q = ((s - 1) * NBK + b) * 4;        // the block step's four adds
                logic [22*64-1:0] sv, m;
                logic [4*32-1:0]  a, bb, sum;
                if (BL == 22) begin : g_22
                    assign sv = R[s - 1][b*BL*64 +: BL*64];
                end else begin : g_18
                    assign sv = {{((22 - BL)*64){1'b0}}, R[s - 1][b*BL*64 +: BL*64]};
                end
                axn_ops #(.STEP(s), .CP(CP)) u_ops (.S(sv), .r(ar[s - 1][b]), .blake(bk[s - 1][b]), .EA(a), .EB(bb));
                if (PRIV) begin : g_priv
                    for (genvar q = 0; q < 4; q++) begin : g_add
                        alu_addp #(.W(32)) u_add (.a(a[q*32 +: 32]), .b(bb[q*32 +: 32]), .y(sum[q*32 +: 32]));
                    end
                    assign ea[Q*32 +: 128] = '0;
                    assign eb[Q*32 +: 128] = '0;
                end else begin : g_lend
                    assign ea[Q*32 +: 128] = a;
                    assign eb[Q*32 +: 128] = bb;
                    assign sum = ey[Q*32 +: 128];
                end
                axn_fin #(.STEP(s), .CP(CP)) u_fin (.S(sv), .r(ar[s - 1][b]), .blake(bk[s - 1][b]), .EY(sum), .M(m));
                for (genvar l = 0; l < BL; l++) begin : g_lane
                    if (wmask(s, l)) begin : g_w
                        assign nxt[(b*BL + l)*64 +: 64] = m[l*64 +: 64];
                    end else begin : g_p
                        assign nxt[(b*BL + l)*64 +: 64] = sv[l*64 +: 64];
                    end
                end
            end
            logic [NBK*BL*64-1:0] q;
            always_ff @(posedge clk) q <= nxt;
            assign R[s] = q;
        end
    endgenerate
    assign y = R[6];
endmodule
