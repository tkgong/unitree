// wiring: rot31<R>, the 31-bit left rotation = 2^R * v mod p (R = 0..30). No logic, a constant permutation of wires.
module rot31 #(
    parameter int R = 0
) (
    input  logic [30:0] v,
    output logic [30:0] y
);
    generate
        if (R == 0) begin : g0
            assign y = v;
        end else begin : gr
            assign y = {v[30-R:0], v[30:31-R]};
        end
    endgenerate
endmodule
