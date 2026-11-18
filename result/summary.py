import csv, os
H = os.path.dirname(os.path.abspath(__file__))
rd = lambda f: {(r["workload"], int(r["leaves_log2"])): r for r in csv.DictReader(open(os.path.join(H, f)))}
C, G, U = rd("cpu.csv"), rd("gpu.csv"), rd("unitree.csv")
out = ["workload,leaves_log2,cpu_us_per_tree,gpu_us_per_tree,unitree_us_per_tree,speedup_vs_cpu,speedup_vs_gpu,cpu_nj_per_node,gpu_nj_per_node,unitree_nj_per_node,energy_efficiency_vs_cpu,energy_efficiency_vs_gpu"]
for k, u in U.items():
    n = (1 << k[1]) - 1
    un = int(u["cycles"]) / float(u["nodes"]); uj = float(u["nj_per_node"])
    cn = float(C[k]["ns_per_node"]); cj = cn * float(C[k]["w_above_idle"])
    gn = float(G[k]["ns_per_node"]); gj = gn * (float(G[k]["board_w"]) - float(G[k]["idle_w"]))
    out.append("%s,%d,%.3f,%.3f,%.3f,%.2f,%.2f,%.1f,%.1f,%.2f,%.1f,%.1f" % (k[0], k[1], cn * n / 1e3, gn * n / 1e3, un * n / 1e3, cn / un, gn / un, cj, gj, uj, cj / uj, gj / uj))
open(os.path.join(H, "summary.csv"), "w", newline="\n").write("\n".join(out) + "\n")
