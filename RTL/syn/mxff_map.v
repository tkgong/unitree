// mxff_map.v - syn.sh SDFF=1: a matched MUX2_X1 -> DFF_X1 pair (mxff_pat.v) as one SDFF_X1 (MUX2_X1: Z = S ? B : A).
module mxff(input A, input B, input S, input CK, output Q, output QN);
    SDFF_X1 _TECHMAP_REPLACE_ (.D(A), .SI(B), .SE(S), .CK(CK), .Q(Q), .QN(QN));
endmodule
