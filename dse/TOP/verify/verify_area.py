"""Recompute the README area / sharing claims from the csynth reports (gate model and register rule of report_axn.py)."""
import os, sys
HERE = r"D:\unitree\_archive_2026-10-23\dse\TOP"
sys.argv = [sys.argv[0], "b"]; __file__ = os.path.join(HERE, "report_p2.py")
exec(open(os.path.join(HERE, "report_lp.py")).read().split("units = [")[0])
sys.path.insert(0, os.path.join(HERE, "..", "DSE2")); import asic_price as AP
src = open(os.path.join(HERE, "report_axn.py")).read()
exec(src.split("def syn(")[1].split("\nU = {")[0].join(["def syn(", ""]))
def get(d):
    p = os.path.join(W, "TOP_syn_" + d, "hls", "syn", "report", "lane_pipe_csynth.rpt")
    return (syn("TOP_syn_" + d), ops("TOP_syn_" + d)) if os.path.exists(p) else None
def alu(r): p = r["parts"]; return p["adders"] + p["xor"] + p["and/or"] + p["mult"] + p["instances"]
def pct(a, b): return f"{(1 - b / a) * 100:+.1f}%"
D = {}
for d in ("bz_16f", "bz_16f_prealu", "bz_16f_flat", "n38c_04", "n38c_04_prealu", "n38_02", "btf_10", "pwe_10", "pwe_10_prealu", "bz_12e", "bz_10e"):
    D[d] = get(d)
    if D[d]:
        r, o = D[d]; print(f"{d:16s} gates {r['gates']:>12,.0f}  logic {r['gates'] - r['parts']['registers']:>11,.0f}  regs {r['parts']['registers']:>11,.0f}  ALU {alu(r):>11,.0f}  LUT {r['lut']:>8,}  FF {r['ff']:>8,}  "
                           f"adders {o.get('adder', (0, 0))}  xor {o.get('xor', (0, 0))}  mul? {r['parts'].get('mult', 0):,.0f}")
    else: print(f"{d:16s} (no report)")
def share(uni, seps, title):
    if any(D[k] is None for k in seps + [uni]): print(title, "missing"); return
    S = lambda f: sum(f(D[k][0]) for k in seps)
    g = lambda r: r["gates"]; rg = lambda r: r["parts"]["registers"]; lg = lambda r: r["gates"] - r["parts"]["registers"]
    u = D[uni][0]
    print(f"{title}: separate {S(g):,.0f} -> {g(u):,.0f}; logic {pct(S(lg), lg(u))}, ALU {pct(S(alu), alu(u))}, registers {pct(S(rg), rg(u))}, total {pct(S(g), g(u))}")
share("bz_16f", ["n38c_04", "n38_02", "btf_10", "pwe_10"], "bz_16f (current reports) vs n38c_04 + n38_02 + btf_10 + pwe_10")
share("bz_16f_prealu", ["n38c_04_prealu", "n38_02", "btf_10", "pwe_10_prealu"], "bz_16f_prealu vs prealu naturals")
share("bz_12e", ["n38_02", "btf_10", "pwe_10"], "bz_12e vs n38_02 + btf_10 + pwe_10")
share("bz_10e", ["btf_10", "pwe_10"], "bz_10e vs btf_10 + pwe_10")
