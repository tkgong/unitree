"""report_fsm.py - area and sharing of the FSM cores from the Yosys stat outputs (syn_all.sh: work/<name>_flat.txt,
work/<name>_hier.txt; names mono, chacha_<NB>, blake3_<NB>, shared_<NB>). Per design: total / flip-flops / combinational (flat run), ALU instances and their area (hier run:
the alu_* modules kept as hierarchy). Sharing of the shared PE against the sum of the three natural kernels at the same
NB, as logic-only / ALU-only / registers / total.
    python3 report_fsm.py <NB> [<NB> ...] [--md out.md]"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); W = os.path.join(HERE, "work")
NAND2 = 0.798

def flat(name):
    """-> (total area, dff area, dff count, cells) of the flattened design (Yosys 0.61 stat -liberty format)"""
    t = open(os.path.join(W, f"{name}_flat.txt")).read()
    area = float(re.findall(r"Chip area for (?:top )?module '\\?top_\w+':\s*([\d.]+)", t)[-1])
    cells = int(re.findall(r"^\s*(\d+)\s+[\d.E+]+\s+cells\s*$", t, re.M)[-1])
    dff = sum(int(m.group(1)) for m in re.finditer(r"^\s*(\d+)\s+[\d.E+]+\s+(DFF\w*)\s*$", t, re.M))
    return area, dff * 4.522, dff, cells                                             # NangateOpenCellLibrary DFF_X1 = 4.522 um^2

def hier(name):
    """-> ({module: own area}, {module: {child: count per instance}}, top area with submodules) from the hierarchical run"""
    t = open(os.path.join(W, f"{name}_hier.txt")).read()
    own, kids = {}, {}
    body = t[:t.rfind("=== design hierarchy ===")] if "=== design hierarchy ===" in t else t
    for sec in re.split(r"^=== ", body, flags=re.M)[1:]:
        mname = sec.split(" ===")[0].strip()
        a = re.search(r"Chip area for module '.*':\s*([\d.]+)", sec)
        own[mname] = float(a.group(1)) if a else 0.0
        kids[mname] = {m.group(2): int(m.group(1)) for m in re.finditer(r"^\s*(\d+)\s+-\s+(\S+)\s*$", sec, re.M)}
    top = re.search(r"Chip area for top module '.*':\s*([\d.]+)", t)
    return own, kids, float(top.group(1)) if top else None

def alu_area(name):
    own, kids, top = hier(name)
    topm = next(m for m in own if m.startswith("top_"))
    inst = {topm: 1}                                                                     # total instances of every module
    order = [topm]
    for m in order:
        for c, n in kids.get(m, {}).items():
            if c not in own: continue
            inst[c] = inst.get(c, 0) + n * inst[m]
            if c not in order: order.append(c)
    tot = 0.0; rows = {}
    for m, a in own.items():
        if "alu_" in m or "rot31" in m:
            key = re.sub(r"^\$paramod\\", "", m); key = re.sub(r"\\(\w+)=s32'0*(\d+)", lambda g: f" {g.group(1)}={int(g.group(2), 2)}", key)
            n = inst.get(m, 0); rows[key] = (n, a, n * a); tot += n * a
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
    D = {n: design(n) for n in ("mono", f"chacha_{nb}", f"blake3_{nb}", f"shared_{nb}") if os.path.exists(os.path.join(W, f"{n}_flat.txt")) and os.path.exists(os.path.join(W, f"{n}_hier.txt"))}
    L += [f"### NB = {nb}", "", "| design | cells | total um^2 | flip-flops (count) | logic um^2 | ALU instances um^2 (hier) | hier total |", "|---|---:|---:|---:|---:|---:|---:|"]
    for n, d in D.items():
        L.append(f"| {n} | {d['cells']:,} | {d['total']:,.0f} | {d['dff']:,.0f} ({d['ndff']:,}) | {d['logic']:,.0f} | {d['alu']:,.0f} | {d['htop']:,.0f} |" if d["htop"] else f"| {n} | {d['cells']:,} | {d['total']:,.0f} | {d['dff']:,.0f} ({d['ndff']:,}) | {d['logic']:,.0f} | {d['alu']:,.0f} | |")
    seps = [D[n] for n in ("mono", f"chacha_{nb}", f"blake3_{nb}") if n in D]
    if len(seps) == 3 and f"shared_{nb}" in D:
        u = D[f"shared_{nb}"]
        S = lambda k: sum(d[k] for d in seps)
        L += ["", f"| sharing, shared_{nb} vs mono + chacha_{nb} + blake3_{nb} | separate | shared | saved |", "|---|---:|---:|---:|"]
        for k, lab in (("logic", "logic only (all non-flip-flop cells)"), ("alu", "ALU instances only"), ("dff", "registers"), ("total", "total")):
            L.append(f"| {lab} | {S(k):,.0f} | {u[k]:,.0f} | {pct(S(k), u[k])} |")
        L += ["", "ALU instances (hier run; instances x area each = um^2):", "", "| ALU | " + " | ".join(d["name"] for d in seps + [u]) + " |", "|---|" + "---:|" * (len(seps) + 1)]
        keys = sorted({k for d in seps + [u] for k in d["rows"]})
        for k in keys:
            L.append(f"| {k} | " + " | ".join((f"{d['rows'][k][0]:,} x {d['rows'][k][1]:,.0f} = {d['rows'][k][2]:,.0f}" if k in d["rows"] else "") for d in seps + [u]) + " |")
    L.append("")
txt = "\n".join(L); print(txt)
if out: open(out, "w").write(txt + "\n")
