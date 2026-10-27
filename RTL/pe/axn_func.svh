// axn_func.svh - wiring helpers of the ARX steps (lanes.h / level_ops_axn.h), included inside axn_ops / axn_fin.
// Constant rotations and the row permutation P: no logic, every call has constant amounts.
function automatic [63:0] pk(input [31:0] lo, input [31:0] hi);
    pk = {hi, lo};
endfunction
function automatic [31:0] rotl32(input [31:0] x, input integer n);
    rotl32 = (n == 0) ? x : ((x << n) | (x >> (32 - n)));
endfunction
function automatic [63:0] rotl2x32(input [63:0] x, input integer n);          // both halves left by n
    rotl2x32 = {rotl32(x[63:32], n), rotl32(x[31:0], n)};
endfunction
// prow<X>: the column <-> diagonal involution P on one row (lo = columns 0,1, hi = columns 2,3); result {ohi, olo}
function automatic [127:0] prow(input integer X, input [63:0] lo, input [63:0] hi);
    case (X)
        0: prow = {pk(hi[31:0], lo[63:32]), pk(lo[31:0], hi[63:32])};
        1: prow = {pk(hi[63:32], hi[31:0]), pk(lo[63:32], lo[31:0])};
        2: prow = {pk(lo[31:0], hi[63:32]), pk(hi[31:0], lo[63:32])};
        default: prow = {pk(lo[63:32], lo[31:0]), pk(hi[63:32], hi[31:0])};
    endcase
endfunction
