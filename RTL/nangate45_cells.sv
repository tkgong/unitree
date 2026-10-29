// nangate45_cells.sv - functional models of the Nangate45 cells alu_add_ks45.sv instantiates, for Verilator (the
// synthesis flow reads the liberty instead: syn.sh KS45=1). Pin names and functions as in NangateOpenCellLibrary.
module AND2_X1  (input logic A1, input logic A2, output logic ZN); assign ZN = A1 & A2; endmodule
module NAND2_X1 (input logic A1, input logic A2, output logic ZN); assign ZN = ~(A1 & A2); endmodule
module NOR2_X1  (input logic A1, input logic A2, output logic ZN); assign ZN = ~(A1 | A2); endmodule
module INV_X1   (input logic A, output logic ZN); assign ZN = ~A; endmodule
module XOR2_X1  (input logic A, input logic B, output logic Z); assign Z = A ^ B; endmodule
module XNOR2_X1 (input logic A, input logic B, output logic ZN); assign ZN = ~(A ^ B); endmodule
module AOI21_X1 (input logic A, input logic B1, input logic B2, output logic ZN); assign ZN = ~(A | (B1 & B2)); endmodule
module OAI21_X1 (input logic A, input logic B1, input logic B2, output logic ZN); assign ZN = ~(A & (B1 | B2)); endmodule
