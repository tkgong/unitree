"""report_fsm.py - area and sharing of the FSM cores from the Yosys stat outputs (syn_all.sh: work/<name>_flat.txt,
work/<name>_hier.txt). Per design: total / flip-flops / combinational (flat run), ALU instances and their area (hier run:
the alu_* modules kept as hierarchy). Sharing of the shared PE against the sum of the three natural kernels at the same
NB, as logic-only / ALU-only / registers / total.
    python3 report_fsm.py <NB> [<NB> ...] [--md out.md]"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); W = os.path.join(HERE, "work")
NAND2 = 0.798

def flat(name):
    """-> (total area, dff area, dff count, cells) of the flattened design"""
    t = open(os.path.join(W, f"{name}_flat.txt")).read()
    area = float(re.findall(r"Chip area for (?:top )?module '\\?pe_core':\s*([\d.]+)", t)[-1])
    cells = int(re.findall(r"^\s*(\d+)\s+cells\s*$", t, re.M)[-1]) if re.findall(r"^\s*(\d+)\s+cells\s*$", t, re.M) else int(re.findall(r"Number of cells:\s*(\d+)", t)[-1])
    dff = 0; dffa = 0.0
    for m in re.finditer(r"^\s*(\d+)\s+(DFF\w*|SDFF\w*|DFFR\w*)\s*$", t, re.M):          # "   166081 DFF_X1"
        dff += int(m.group(1))
    for m in re.finditer(r"^\s*(DFF\w*)\s+(\d+)\s*$", t, re.M):                            # older "DFF_X1  166081"
        dff += int(m.group(2))
    dffa = dff * 4.522                                                                   # NangateOpenCellLibrary DFF_X1 area
    return area, dffa, dff, cells

def hier(name):
    """-> {module: (instances in the design, area each)} for the alu_* modules, and the hierarchy total"""
    t = open(os.path.join(W, f"{name}_hier.txt")).read()
    mods = {}
    for sec in re.split(r"^=== ", t, flags=re.M)[1:]:
        mname = sec.split(" ===")[0].strip().strip("\\")
        a = re.search(r"Chip area for module '[^']*':\s*([\d.]+)", sec)
        if a: mods[mname] = float(a.group(1))
    top = re.search(r"Chip area for top module '[^']*':\s*([\d.]+)", t)
    inst = {}
    hsec = t[t.rfind("design hierarchy"):] if "design hierarchy" in t else ""
    for m in re.finditer(r"^\s*(?:\\)?(\w+)\s+(\d+)\s*$", hsec, re.M): inst[m.group(1)] = int(m.group(2))
    for m in re.finditer(r"^\s*(\d+)\s+(?:\\)?(\w+)\s*$", hsec, re.M): inst[m.group(2)] = int(m.group(1))
    return mods, inst, float(top.group(1)) if top else None

def alu_area(name):
    mods, inst, top = hier(name)
    tot = 0.0; rows = {}
    for m, a in mods.items():
        base = re.sub(r"\$paramod.*?\\", "", m)
        if "alu_" in m or m.startswith("rot31"):
            n = inst.get(m, 0)
            key = re.sub(r"^\$paramod\\?", "", m)
            key = re.sub(r"\\", "", key)
            rows[key] = (n, a, n * a); tot += n * a
    return tot, rows, top

def design(name):
    area, dffa, dff, cells = flat(name)
    alu, rows, top = alu_area(name)
    return {"name": name, "total": area, "dff": dffa, "ndff": dff, "logic": area - dffa, "alu": alu, "rows": rows, "htop": top, "cells": cells}

def pct(sep, uni): return f"{100 * (1 - uni / sep):+.1f}%" if sep else "n/a"

out = sys.argv[sys.argv.index("--md") + 1] if "--md" in sys.argv else ""
NBS = [int(a) for a in sys.argv[1:] if a.isdigit()]
L = []
for nb in NBS:
    D = {n: design(n) for n in ("mono", f"cc_{nb}", f"b3_{nb}", f"shared_{nb}") if os.path.exists(os.path.join(W, f"{n}_flat.txt")) and os.path.exists(os.path.join(W, f"{n}_hier.txt"))}
    L += [f"### NB = {nb}", "", "| design | cells | total um^2 | flip-flops (count) | logic um^2 | ALU instances um^2 (hier) | hier total |", "|---|---:|---:|---:|---:|---:|---:|"]
    for n, d in D.items():
        L.append(f"| {n} | {d['cells']:,} | {d['total']:,.0f} | {d['dff']:,.0f} ({d['ndff']:,}) | {d['logic']:,.0f} | {d['alu']:,.0f} | {d['htop']:,.0f} |" if d["htop"] else f"| {n} | {d['cells']:,} | {d['total']:,.0f} | {d['dff']:,.0f} ({d['ndff']:,}) | {d['logic']:,.0f} | {d['alu']:,.0f} | |")
    seps = [D[n] for n in ("mono", f"cc_{nb}", f"b3_{nb}") if n in D]
    if len(seps) == 3 and f"shared_{nb}" in D:
        u = D[f"shared_{nb}"]
        S = lambda k: sum(d[k] for d in seps)
        L += ["", f"| sharing, shared_{nb} vs mono + cc_{nb} + b3_{nb} | separate | shared | saved |", "|---|---:|---:|---:|"]
        for k, lab in (("logic", "logic only (all non-flip-flop cells)"), ("alu", "ALU instances only"), ("dff", "registers"), ("total", "total")):
            L.append(f"| {lab} | {S(k):,.0f} | {u[k]:,.0f} | {pct(S(k), u[k])} |")
        L += ["", "ALU instances (hier run; instances x area each = um^2):", "", "| ALU | " + " | ".join(d["name"] for d in seps + [u]) + " |", "|---|" + "---:|" * (len(seps) + 1)]
        keys = sorted({k for d in seps + [u] for k in d["rows"]})
        for k in keys:
            L.append(f"| {k} | " + " | ".join((f"{d['rows'][k][0]:,} x {d['rows'][k][1]:,.0f} = {d['rows'][k][2]:,.0f}" if k in d["rows"] else "") for d in seps + [u]) + " |")
    L.append("")
txt = "\n".join(L); print(txt)
if out: open(out, "w").write(txt + "\n")
