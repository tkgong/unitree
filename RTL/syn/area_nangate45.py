#!/usr/bin/env python3
"""Standard-cell area of every ALU module in RTL/ (Yosys + ABC mapped to the NangateOpenCellLibrary, the ORFS nangate45
platform), against the NAND2-equivalent gate model the README's area numbers were computed with (dse/DSE2/asic_price.py:
add 7.5 / bit, xor 2.3 / bit, and/or 1.3 / bit, 2:1 select 2.3 / bit, multiplier 6.0 per partial-product bit, compare
1.5 / bit). Area is converted to NAND2 equivalents with the library's NAND2_X1 cell area.
    python3 area_nangate45.py [--lib PATH] [--period PS] [--jobs N] [--out results.md]
--period PS adds an ABC delay target (abc -D); without it ABC optimises area only."""
import argparse, os, re, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__)); RTL = os.path.normpath(os.path.join(HERE, ".."))
ap = argparse.ArgumentParser()
ap.add_argument("--lib", default=os.path.expanduser("~/eda/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib"))
ap.add_argument("--period", type=int, default=0, help="ABC delay target in ps (0 = area only)")
ap.add_argument("--jobs", type=int, default=8)
ap.add_argument("--yosys", default="yosys")
ap.add_argument("--out", default="")
A = ap.parse_args()
SV = [os.path.join(RTL, f) for f in sorted(os.listdir(RTL)) if f.endswith(".sv")]
P = 7.5; X = 2.3; AO = 1.3; SEL = 2.3; MUL = 6.0; CMP = 1.5
# (module, {param: value}, gate-model NAND2 equivalents, what the model counts)
CASES = []
for W in range(32, 42):
    CASES.append(("alu_add", {"W": W}, P * W, f"add {W} b"))
    CASES.append(("alu_lend", {"W": W}, P * W + 2 * SEL * W, f"add {W} b + 2 selects {W} b"))
CASES += [("alu_addp", {"W": 32}, P * 32, "add 32 b"),
          ("alu_mul31", {}, MUL * 31 * 31, "31 x 31 partial products"),
          ("alu_mul31_en", {}, MUL * 31 * 31 + SEL * 62, "31 x 31 + select 62 b"),
          ("alu_mul31_p2", {}, MUL * 31 * 31 + 6 * 233, "31 x 31 + 233 stage flip-flops x 6"),
          ("alu_mul31_en_p2", {}, MUL * 31 * 31 + SEL * 62 + 6 * 234, "31 x 31 + select 62 b + 234 flip-flops x 6")]
for H in (1, 4, 5, 6, 8, 9, 10):
    CASES.append(("alu_fold", {"H": H}, P * H, f"add {H} b (increment)"))
CASES += [("alu_fold", {"H": 31}, P * 31, "add 31 b (increment)"),
          ("alu_fold31", {}, P * 31, "add 31 b (increment)"),
          ("alu_canon", {"W": 32}, CMP * 31 + SEL * 31, "compare 31 b + select 31 b"),
          ("alu_canon", {"W": 31}, CMP * 31 + SEL * 31, "compare 31 b + select 31 b"),
          ("alu_negm31", {"W": 33}, P * 31, "subtract 31 b"),
          ("alu_bar_chunk", {"W": 8}, 8 * (2 * AO + X), "per bit: 2 and + 1 xor (3-input and)"),
          ("alu_bar_chunk", {"W": 7}, 7 * (AO + X), "per bit: 1 and + 1 xor"),
          ("alu_bar31", {}, 3 * 8 * (2 * AO + X) + 7 * (AO + X), "3 x 8-bit + 7-bit chunks"),
          ("alu_xor", {}, X * 64, "xor 64 b"),
          ("rot31", {"R": 7}, 0.0, "wiring")]
nand2 = None
for m in re.finditer(r"cell\s*\(\s*\"?(NAND2_X1)\"?\s*\)\s*\{(.*?)\n\s*\}\n", open(A.lib, errors="ignore").read(), re.S):
    a = re.search(r"\barea\s*:\s*([\d.]+)", m.group(2)); nand2 = float(a.group(1)) if a else None
if nand2 is None:
    s = open(A.lib, errors="ignore").read(); i = s.index("cell (NAND2_X1)"); nand2 = float(re.search(r"area\s*:\s*([\d.]+)", s[i:i + 4000]).group(1))
def run(case):
    mod, params, model, what = case
    tag = mod + "".join(f"_{k}{v}" for k, v in params.items())
    with tempfile.TemporaryDirectory() as d:
        ys = os.path.join(d, tag + ".ys"); log = os.path.join(d, tag + ".log")
        chp = " ".join(f"-chparam {k} {v}" for k, v in params.items())
        abc = f"abc -liberty {A.lib}" + (f" -D {A.period}" if A.period else "")
        open(ys, "w").write("\n".join([*(f"read_verilog -sv {f}" for f in SV), f"hierarchy -top {mod} {chp}", f"synth -top {mod} -flatten",
                                       f"dfflibmap -liberty {A.lib}", abc, "opt_clean -purge", f"stat -liberty {A.lib}", ""]))
        r = subprocess.run([A.yosys, "-q", "-l", log, "-s", ys], capture_output=True, text=True)
        out = open(log, errors="ignore").read() if os.path.exists(log) else ""
        if r.returncode != 0: return (tag, None, None, None, model, what, (r.stderr or out)[-400:])
        m = re.findall(r"Chip area for (?:top )?module '[^']*':\s*([\d.]+)", out)
        cells = re.findall(r"^\s+(\d+)\s+[\d.]+\s+cells\s*$", out, re.M) or re.findall(r"Number of cells:\s*(\d+)", out)
        nocell = re.search(r"Computing hashes of 0 cells", out) is not None and not m
        area = float(m[-1]) if m else (0.0 if nocell else None); ncell = int(cells[-1]) if cells else (0 if nocell else None)
        kinds = dict((k, int(n)) for k, n in re.findall(r"^\s+(\d+)\s+[\d.]+\s+([A-Z][A-Z0-9_]*)\s*$", out, re.M)[::-1] and
                     [(k, n) for n, k in re.findall(r"^\s+(\d+)\s+[\d.]+\s+([A-Z][A-Z0-9_]*)\s*$", out, re.M)])
        return (tag, area, ncell, kinds, model, what, "")
print(f"library {A.lib}\nNAND2_X1 area {nand2} um^2; ABC {'delay target ' + str(A.period) + ' ps' if A.period else 'area only'}; yosys {subprocess.run([A.yosys, '-V'], capture_output=True, text=True).stdout.strip()}")
with ThreadPoolExecutor(A.jobs) as ex: R = list(ex.map(run, CASES))
lines = ["| module | cells | area um^2 | NAND2 eq | gate model | synth / model | model counts |", "|---|---:|---:|---:|---:|---:|---|"]
for tag, area, ncell, kinds, model, what, err in R:
    if area is None: lines.append(f"| {tag} | FAILED | | | | | {err.strip().splitlines()[-1] if err.strip() else ''} |"); continue
    ne = area / nand2
    lines.append(f"| {tag} | {ncell} | {area:,.1f} | {ne:,.0f} | {model:,.0f} | {(f'{ne / model:.2f}' if model else '-')} | {what} |")
txt = "\n".join(lines); print(txt)
if A.out: open(A.out, "w").write(txt + "\n")
