# UniTree

## design/

| path | content |
|---|---|
| [design/env.sh](design/env.sh) | source lists, tool and library paths |
| [design/rtl/alu/](design/rtl/alu) | ALUs |
| [design/rtl/shared/unit18_shared.sv](design/rtl/shared/unit18_shared.sv) | UniTree unit: ChaCha20 + BLAKE3 + Monolith-31 |
| [design/rtl/shared/mono_dp18.sv](design/rtl/shared/mono_dp18.sv) | Monolith-31 datapath |
| [design/rtl/shared/kara_pkg.sv](design/rtl/shared/kara_pkg.sv) | Monolith-31 node tables |
| [design/rtl/shared/pe_map.svh](design/rtl/shared/pe_map.svh) | register and operand map |
| [design/rtl/shared/arx_group.sv](design/rtl/shared/arx_group.sv) | ChaCha20 / BLAKE3 block group |
| [design/rtl/shared/axn_step.sv](design/rtl/shared/axn_step.sv), [axn_func.svh](design/rtl/shared/axn_func.svh) | ChaCha20 / BLAKE3 step |
| [design/rtl/standalone/](design/rtl/standalone) | standalone ChaCha20, BLAKE3, Monolith-31 units |
| [design/compiler/compile_tree.py](design/compiler/compile_tree.py) | tree compiler and memory scheduler |
| [design/compiler/compile_forest.py](design/compiler/compile_forest.py) | one tree on several units |
| [design/compiler/bind/](design/compiler/bind) | static operand binding |
| [design/model/](design/model) | unit model and reference models |
| [design/memsim/hbm.py](design/memsim/hbm.py), [hbm_capi.cpp](design/memsim/hbm_capi.cpp) | DRAM interface |
| [design/memsim/gddr6.yaml](design/memsim/gddr6.yaml), [hbm2.yaml](design/memsim/hbm2.yaml) | DRAM configurations |
| [design/memsim/ramsim/](design/memsim/ramsim) | Ramulator2 |
| [design/memsim/build_linux.sh](design/memsim/build_linux.sh) | build: DRAM model, unit models |
| [design/syn/syn.sh](design/syn/syn.sh) | synthesis |
| [design/syn/repair.sh](design/syn/repair.sh) | timing repair |
| [design/flow/timing/sta.sh](design/flow/timing/sta.sh) | timing sign-off |
| [design/flow/power/](design/flow/power) | power |
| [design/flow/area/](design/flow/area) | area report |
| [design/flow/sram/](design/flow/sram) | SRAM macros |
| [design/test/](design/test) | testbenches, traces, regression |
| [design/ablation/unit18_alu.sv](design/ablation/unit18_alu.sv) | ablation: shared ALUs only |
| [design/ablation/unit18_reg.sv](design/ablation/unit18_reg.sv), [unit18_regr.sv](design/ablation/unit18_regr.sv) | ablation: shared ALUs + shared registers |
| [design/ablation/slots/](design/ablation/slots) | ablation: Monolith-31 datapath without operand binding |
| [design/ablation/run.sh](design/ablation/run.sh), [summary.py](design/ablation/summary.py) | ablation: synthesis run and table |
| [design/ablation/sim.sh](design/ablation/sim.sh) | ablation: simulation |
| [design/measure/unitree.sh](design/measure/unitree.sh), [energy.py](design/measure/energy.py) | UniTree measurement |

## baseline/

| path | content |
|---|---|
| [baseline/cpu/cpu_trees.cpp](baseline/cpu/cpu_trees.cpp) | CPU trees |
| [baseline/cpu/blake3_c/](baseline/cpu/blake3_c) | BLAKE3 C library |
| [baseline/cpu/p3mono/](baseline/cpu/p3mono) | Plonky3 Monolith-31 |
| [baseline/cpu/build_cpu_linux.sh](baseline/cpu/build_cpu_linux.sh) | build |
| [baseline/cpu/run_cpu_trees.py](baseline/cpu/run_cpu_trees.py) | check and timing |
| [baseline/cpu/measure_cpu.py](baseline/cpu/measure_cpu.py), [measure_cpu_batch.py](baseline/cpu/measure_cpu_batch.py) | CPU measurement |
| [baseline/gpu/gpu_trees2.cu](baseline/gpu/gpu_trees2.cu), [gpu_prims.cu](baseline/gpu/gpu_prims.cu) | GPU trees: zeknox tree builder, GPU-DPF hybrid |
| [baseline/gpu/build_gpu_trees2_linux.sh](baseline/gpu/build_gpu_trees2_linux.sh) | build |
| [baseline/gpu/run_gpu_trees2.py](baseline/gpu/run_gpu_trees2.py) | check and timing |
| [baseline/gpu/measure_gpu.py](baseline/gpu/measure_gpu.py) | GPU measurement |

## result/

| path | content |
|---|---|
| [result/cpu.csv](result/cpu.csv) | CPU measurement |
| [result/gpu.csv](result/gpu.csv) | GPU measurement |
| [result/unitree.csv](result/unitree.csv) | UniTree measurement |
| [result/summary.csv](result/summary.csv), [summary.py](result/summary.py) | runtime, speedup, energy efficiency |
| [result/asic/area.csv](result/asic/area.csv) | area at 1 GHz |
| [result/asic/sharing.csv](result/asic/sharing.csv) | area saved by sharing |
| [result/asic/power_toggle25.csv](result/asic/power_toggle25.csv) | power at 25% toggle rate |
| [result/asic/power_program.csv](result/asic/power_program.csv) | power per workload |
| [result/asic/sram.csv](result/asic/sram.csv) | memory parameters |
| [result/ablation/sharing.csv](result/ablation/sharing.csv) | sharing ablation |
| [result/ablation/steps.csv](result/ablation/steps.csv) | sharing ablation, step by step |
