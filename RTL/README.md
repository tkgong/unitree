# RTL/ - the ALUs of the unified tree unit in SystemVerilog

One module per function of `dse/TOP/alu_core.h`, the file every arithmetic or logic operator of the bz unit calls.
Each module is the C++ function transcribed, same name, same parameter (W / H / R), same port widths; nothing else
(no registers, no control: the pipeline registers, operand selects beyond `ext`, rotations and lane packing are
wiring in the generated datapath and stay in the HLS sources).

| file | module | C++ (alu_core.h) | role in the bz unit | instances |
|---|---|---|---|---:|
| alu_add.sv | `alu_add #(W)` | `alu_add<W>` | ALU-ADD: the lendable W-bit adder, plain integer add (no modulus: the ARX side takes y[31:0] = mod 2^32, the M31 side folds once at the end of its adder tree) | 912 (W = 32..41: 444 / 176 / 104 / 66 / 40 / 34 / 26 / 16 / 4 / 2) |
| alu_lend.sv | `alu_lend #(W)` | `alu_lend<W>` | the operand select in front of it: ARX operands (ea, eb) when `ext`, else the datapath's (a, b) | 912 |
| alu_addp.sv | `alu_addp #(W)` | `alu_addp<W>` | ALU-ADP: private adder (engine part sums / constants, reduction first adders that are not lent) | 236 datapaths (W = 32..41) + 268 engines (W = 32..35) |
| alu_lendp.sv | `alu_lendp #(W)` | `alu_lendp<W>` | lend select in front of a private adder (builds without MONO_LEND_MOD; not in bz) | 0 |
| alu_mul31.sv | `alu_mul31` | `alu_mul31` | ALU-MUL: 31 x 31 -> 62 (chain ranks 2 and 3 of x^5, the engines' products) | 64 (datapaths) + 12 (engines) |
| alu_mul31_en.sv | `alu_mul31_en` | `alu_mul31_en` | the same, 0 when the issue has no Bricks (rank 1) | 32 (datapaths) |
| alu_fold.sv | `alu_fold #(H)` | `alu_fold<H>` | ALU-FLD: M31 end-around carry on the low H bits of a 32-bit sum (H = 31 is alu_fold31) | 210 (datapaths; per datapath H = 1 x16, 4 x41, 5 x16, 6 x16, 8 x11, 9 x3, 10 x2) |
| alu_fold31.sv | `alu_fold31` | `alu_fold31` | the whole 31-bit word + carry | 96 (datapaths) + 76 (engines) |
| alu_canon.sv | `alu_canon #(W)` | `alu_canon<T>` | p -> 0 (W = output width, 31 or 32) | 128 (datapaths, W = 32) + 64 (engines, W = 31) |
| alu_negm31.sv | `alu_negm31 #(W)` | `alu_negm31<W>` | p - t, zero-extended to W | 4 (engines, W = 33) |
| alu_bar_chunk.sv | `alu_bar_chunk #(W)` | `alu_bar_chunk<W>` | Monolith Bars on one 8- or 7-bit chunk | 4 per alu_bar31 |
| alu_bar31.sv | `alu_bar31` | `alu_bar31` | ALU-BAR: Bars S-box on a 31-bit element, 8 / 8 / 8 / 7 chunks | 2 (one per datapath, on slot 0) |
| alu_xor.sv | `alu_xor` | `alu_xor` | ALU-XOR: 64-bit xor, the ARX blocks' only own logic | 22 call sites in level_ops_axn.h (the ARX step functions, instantiated per block) |
| rot31.sv | `rot31 #(R)` | `rot31<R>` | wiring: 2^R x mod p, a constant rotation (no logic) | - |

Instance counts: `alu_add` from the bz_16f csynth report (the non-inlined modules); the rest are call sites in the
generated sources, comments excluded (`bz/lane_mono_kl.inc` x 2 datapaths, `p2_engine.h` x 4 engines; the engine's
`p2e_canon` / `p2e_fold62` helpers are counted per use), `level_ops_axn.h`.

## Why alu_add has no modulus and the same width in and out

The same adder serves two moduli: the ARX blocks need (a + b) mod 2^32, the M31 datapaths need mod 2^31 - 1. So the
adder is a plain integer adder; the ARX side takes the low 32 bits of the sum, the M31 side keeps full-width partial
sums through its adder tree and reduces once at the end (lo31 + hi in an `alu_addp<32>`, then `alu_fold<H>` /
`alu_fold31`, then `alu_canon`). W is the generator's bound on the sum: the operands are zero-extended to W, so the W-bit
result is the exact sum. That every emitted W holds the worst case is checked statically
(`dse/TOP/verify/check_adder_widths.py`: 550 adders, 153 reductions, the hosted Poseidon2 values; 0 violations).

## Verification (2026-10-27)

`sh verify/run_tb.sh` compares every module, at every parameter value the unit uses (and more), with the C++ it was
transcribed from:

1. `verify/ref_alu.cpp` exports the C++ ALUs of `alu_core.h` (every W = 31..41, 62, 64; H = 1..30; R = 0..30) and is
   compiled to `ref_alu.dll` by `dse/verify/build_dll.sh` (clang++ on the Vitis `ap_uint` headers, the same route as
   the unit's own simulator).
2. `verify/gen_vectors.py` drives the DLL and writes 115 vector files, 4096 vectors each: edge values (0, 1, 2^W - 1,
   2^(W-1), p, p +/- 1, 2^32 - 1, every lo / hi corner of the folds), the 8- and 7-bit Bars chunks exhaustively, the rest
   random. 471,040 vectors in all.
3. `verify/tb_alu.sv` instantiates alu_add / addp / lend / lendp at W = 32..41, alu_fold at H = 1..31 (+ alu_fold31),
   alu_canon at W = 31 / 32, alu_negm31 at W = 31..35, rot31 at R = 0..30, and the fixed-width modules: 115 instances,
   every output compared with `!==` against the expected field.

Result: 115 instances OK, 471,040 vectors, 0 mismatches (Icarus Verilog 13.0, `verify/sim.log`). The testbench was
also run on mutated copies (fold using r[30] instead of r[31], the 7-bit Bars chunk with three rotations, mul31_en
ignoring `en`): it reported every mutated instance (33 FAIL lines), so it does detect errors.

Vivado 2025.2 `xvlog -sv` analyzes all 14 files without warnings and `xelab` elaborates every top (alu_lend, alu_lendp,
alu_mul31, alu_mul31_en, alu_fold, alu_fold31, alu_canon, alu_negm31, alu_bar31, alu_xor, rot31). xsim's compiled
snapshot cannot be launched on this machine (the same endpoint policy that blocks csim.exe), hence Icarus for the
simulation.

Not covered here: synthesis of these files (the area numbers in `dse/TOP/README.md` are csynth's gate model of the HLS
unit, not of this RTL), and the datapath / pipeline around the ALUs, which exists only as the generated HLS C++.
