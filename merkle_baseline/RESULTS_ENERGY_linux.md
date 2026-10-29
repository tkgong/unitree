# Energy per tree, CPU and GPU baselines (2^18, 262,143 nodes per tree)

CPU Intel(R) Core(TM) i7-10700K CPU @ 3.80GHz, package RAPL. GPU NVIDIA GeForce RTX 3070, 240.00 W, nvidia-smi power.draw.instant every 20 ms (board power).
Each measurement: the program repeated for >= 5 s after a warm-up; idle power measured for 5 s before the runs.

CPU: /sys/class/powercap/intel-rapl:0/energy_uj is not readable (root only); CPU energy not measured.

| platform | tree | us per tree (sustained) | power W | idle W | energy per tree uJ | above idle uJ | note |
|---|---|---:|---:|---:|---:|---:|---|
| GPU | BLAKE3 Merkle | 72.2 | 234.5 | 48.4 | 16,936 | 13,440 | 259 samples |
| GPU | BLAKE3-XOF GGM | 149.8 | 211.4 | 48.4 | 31,672 | 24,421 | 268 samples |
| GPU | ChaCha20 GGM | 147.0 | 225.3 | 48.4 | 33,122 | 26,006 | 264 samples |
| GPU | Monolith-31 Merkle | 451.3 | 227.2 | 48.4 | 102,557 | 80,714 | 269 samples |
