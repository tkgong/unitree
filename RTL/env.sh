# env.sh - sourced by every script under RTL/ after it sets R (the RTL directory): the source lists of the design and the
# tool / library paths of dana336, the Linux machine every flow runs on.
#   R=$(cd "$(dirname "$0")/.." && pwd); . "$R/env.sh"
A=$R/src/alu; S=$R/src/shared
SRC_ALU="$A/alu_add.sv $A/alu_addp.sv $A/alu_lend.sv $A/alu_fold.sv $A/alu_fold31.sv $A/alu_addf.sv $A/alu_csa31.sv $A/alu_canon.sv $A/alu_bar_chunk.sv $A/alu_bar31.sv $A/alu_mul31_en_p2.sv $A/alu_xor.sv"
SRC_KS45="$A/alu_add_ks45.sv"                 # the structural Kogge-Stone adder (`define KS45, the timing flow)
SRC_CELLS="$A/nangate45_cells.sv"             # Nangate45 cell models of alu_add_ks45 for simulation
SRC_BLK="$S/kara_pkg.sv $S/pe_map_pkg.sv $S/mono_dp18.sv $S/arx_group.sv $S/axn_step.sv"
INC="-I$S"                                    # axn_func.svh
top_sv() { case $1 in shared) echo "$S/unit18_shared.sv";; *) echo "$R/src/standalone/unit18_$1.sv";; esac; }
TOPS="shared mono chacha blake3"
ORFS=/home/dana336/eda/OpenROAD-flow-scripts/flow
PLAT=$ORFS/platforms/nangate45
LIBDIR=$PLAT/lib
LIB=$LIBDIR/NangateOpenCellLibrary_typical.lib
OSS=/home/dana336/eda/oss-cad-suite/bin        # iverilog / vvp
OPENLANE=ghcr.io/efabless/openlane2:2.3.10     # OpenROAD / OpenSTA (docker)
