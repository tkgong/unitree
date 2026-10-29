// alu_fold31: the whole 31-bit word plus the carry bit r[31] (mod 2^31): r = lo31 + hi31 <= 2^32 - 2, so the result
// is <= p and never wraps (r[31] = 1 implies r[30:0] <= 2^31 - 3).
module alu_fold31 (
    input  logic [31:0] r,
    output logic [30:0] t
);
    assign t = r[30:0] + r[31];
endmodule
