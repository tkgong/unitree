// mxff_pat.v - syn.sh SDFF=1: the pattern Yosys extract finds in the mapped netlist: a MUX2_X1 whose output drives only the
// D pin of a DFF_X1 (a register that takes one of two values). mxff_map.v turns each match into one SDFF_X1 (the scan
// flip-flop: Q <= SE ? SI : D, 6.118 um^2 against 1.862 + 4.522).
module mxff(input A, input B, input S, input CK, output Q, output QN);
    wire n;
    MUX2_X1 m (.A(A), .B(B), .S(S), .Z(n));
    DFF_X1  f (.D(n), .CK(CK), .Q(Q), .QN(QN));
endmodule
