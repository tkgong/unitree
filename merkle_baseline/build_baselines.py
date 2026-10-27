"""build_baselines.py - one table: the unit (br, bt, bu; compiled schedules executed cycle by cycle on the corrected DLLs)
against the best CPU (cpu/cpu_trees.json) and the GPU (gpu_trees2.json) for the five tree workloads, 2^10 .. 2^22.
Unit time = cycles x 1 ns: the 1 GHz ASIC clock is an ASSUMPTION (no ASIC synthesis / timing); ratios scale with it.
    python build_baselines.py <unit_trees.log>     -> RESULTS_BASELINES.md"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
NAME = {1: "BLAKE3 Merkle", 2: "BLAKE3-XOF GGM", 3: "ChaCha20 GGM", 4: "Monolith-31 Merkle", 5: "Poseidon2-M31 Merkle"}
REQ = {("merkle", "blake3"): 1, ("ggm", "blake3"): 2, ("ggm", "chacha"): 3, ("merkle", "mono"): 4, ("merkle", "pos2"): 5}
UNITS = ["br", "bt", "bu", "bw"]
unit = {}
for line in open(sys.argv[1], encoding="utf-8", errors="ignore"):
    m = re.match(r"UNIT (\w+) \| (\w+) (\w+) (\d+) \w+ \|.*?cycles ([\d,]+).*?check: .*?: (OK|FAIL)", line)
    if m: unit[(m.group(1), REQ[(m.group(2), m.group(3))], int(m.group(4)))] = (int(m.group(5).replace(",", "")), m.group(6))
cpu = {}
for r in json.load(open(os.path.join(HERE, "cpu", "cpu_trees.json")))["rows"]:
    k = (r["kind"], r["L"])
    if k not in cpu or r["best_ns"] < cpu[k]["best_ns"]: cpu[k] = r
gpu = {tuple(map(int, k.split("_"))): v for k, v in json.load(open(os.path.join(HERE, "gpu_trees2.json"))).items()}
o = ["# Unit vs CPU vs GPU on the tree workloads (2026-10-23)", "",
     "- **Unit**: compiled schedules executed cycle by cycle on the corrected DLLs (Monolith Bars fixed), one tree per program, "
     "Merkle BFS / GGM DFS; every run bit-exact against the Python models. br = 37 ARX blocks + 1 Monolith datapath (adder chains); "
     "bt = 38 blocks + 2 Monolith datapaths with multipliers; bu = bt with Poseidon2 on both datapaths, one multiplier rank (67 issues per permutation); bw = three multiplier ranks, Poseidon2's linear layers on the Concrete adders (23 issues); their ARX / Monolith cycles equal bt's. The final unit bz (bw fed from the state lanes only, 3,847,813 gates, 36.0% sharing) has the identical schedule: same cycle counts (verified at 2^10 for every workload), so the bw column is bz's. "
     "**Time = cycles x 1 ns: the 1 GHz clock is an assumption, not a measurement.**",
     "- **CPU**: i7-12700K, best of 1 / 16 / 20 threads and of the implementations in RESULTS_CPU_TREES.md (official BLAKE3 C 1.8.2, "
     "Plonky3 p3-monolith / Poseidon2 0.8.0, our AVX2 / 8-way kernels).",
     "- **GPU**: RTX 3070, gpu_trees2.cu (fused small levels, 32-bit Monolith MDS), device-resident data, kernel time only; "
     "x8 = 8 trees per program (throughput regime). PCIe transfers are listed in RESULTS_GPU_TREES2.md and are not included.", "",
     "| tree | size | unit br us | unit bt us | unit bu us | unit bw us | CPU best us (impl, threads) | GPU 1 tree us | GPU x8 ns/node | best unit: CPU / unit | best unit: GPU / unit |",
     "|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|"]
for kind in (1, 2, 3, 4, 5):
    for L in (10, 14, 18, 22):
        nodes = (1 << L) - 1
        us_ = {u: unit.get((u, kind, L)) for u in UNITS}
        c = cpu.get((kind, L)); g = gpu.get((kind, L))
        if c is None and g is None and not any(us_.values()): continue
        cus = c["best_ns"] * nodes / 1e3 if c else None
        g1 = g[1][0] * nodes / 1e3 if g else None
        def us(u): return (f"{u[0] / 1e3:,.1f}" + ("" if u[1] == "OK" else " FAIL")) if u else "-"
        best = min((u for u in us_.values() if u), key=lambda u: u[0], default=None)
        def ratio(a): return f"{a / (best[0] / 1e3):.2f}x" if (a and best) else "-"
        o.append(f"| {NAME[kind]} | 2^{L} | {us(us_['br'])} | {us(us_['bt'])} | {us(us_['bu'])} | {us(us_['bw'])} | "
                 f"{(f'{cus:,.1f} ({c['name']}, {c['best_threads']})') if c else '-'} | "
                 f"{(f'{g1:,.1f}') if g else '-'} | {(f'{g[2][0]:.3f}') if g else '-'} | {ratio(cus)} | {ratio(g1)} |")
o += ["", "Ratios > 1: the fastest unit (at the assumed 1 GHz) finishes the tree faster. Missing unit entries (-) were not run "
      "(Monolith 2^22 and Poseidon2 2^22: 7-280 M cycles of cycle-by-cycle simulation)."]
open(os.path.join(HERE, "RESULTS_BASELINES.md"), "w", encoding="utf-8").write("\n".join(o) + "\n")
print("\n".join(o))
