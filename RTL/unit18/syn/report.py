"""report.py - area and resource sharing of the hand-written 18-block units from the Yosys stat files (syn.sh):
total / flip-flops / logic (flat run), ALU instances and their area (hier run: every alu_* module instance x its own area).
Sharing of unit18_shared against unit18_mono + unit18_chacha + unit18_blake3 (the same throughput: the same pipelines and
ring periods, the programs are cycle-identical): logic-only, ALU-only, registers, total; the operator counts.
    python3 report.py [--md out.md]"""
import os, re, sys
W = os.path.join(os.path.dirname(os.path.abspath(__file__)), "work")
DFF = 4.522                                                    # NangateOpenCellLibrary DFF_X1 um^2

def flat(t):
    s = open(os.path.join(W, f"{t}_flat.txt")).read()
    area = float(re.findall(r"Chip area for (?:top )?module '\\?unit18_\w+':\s*([\d.]+)", s)[-1])
    cells = int(re.findall(r"^\s*(\d+)\s+[\d.E+]+\s+cells\s*$", s, re.M)[-1])
    dff = sum(int(m.group(1)) for m in re.finditer(r"^\s*(\d+)\s+[\d.E+]+\s+DFF\w*\s*$", s, re.M))
    return {"total": area, "regs": dff * DFF, "ndff": dff, "logic": area - dff * DFF, "cells": cells}

def hier(t):
    s = open(os.path.join(W, f"{t}_hier.txt")).read()
    body = s[:s.rfind("=== design hierarchy ===")]
    own, kids = {}, {}
    for sec in re.split(r"^=== ", body, flags=re.M)[1:]:
        name = sec.split(" ===")[0].strip()
        a = re.search(r"Chip area for module '.*':\s*([\d.]+)", sec)
        own[name] = float(a.group(1)) if a else 0.0
        kids[name] = {m.group(2): int(m.group(1)) for m in re.finditer(r"^\s*(\d+)\s+-\s+(\S+)\s*$", sec, re.M)}
    top = next(m for m in own if m.startswith("unit18_") or m.endswith("unit18_" + t))
    inst = {top: 1}; order = [top]
    for m in order:
        for c, n in kids.get(m, {}).items():
            if c not in own: continue
            inst[c] = inst.get(c, 0) + n * inst[m]
            if c not in order: order.append(c)
    alu, rows = 0.0, {}
    for m, a in own.items():
        if re.search(r"(^|\\)alu_", m):
            key = re.sub(r"^\$paramod\\", "", m); key = re.sub(r"\\(\w+)=s32'0*(\d+)", lambda g: f" {g.group(1)}={int(g.group(2), 2)}", key)
            n = inst.get(m, 0); rows[key] = (n, a); alu += n * a
    return alu, rows

D = {}
for t in ("shared", "mono", "chacha", "blake3"):
    if os.path.exists(os.path.join(W, f"{t}_flat.txt")) and os.path.exists(os.path.join(W, f"{t}_hier.txt")):
        d = flat(t); d["alu"], d["rows"] = hier(t); D[t] = d
L = ["| unit | cells | total um^2 | flip-flops um^2 (count) | logic um^2 | ALU instances um^2 |", "|---|---:|---:|---:|---:|---:|"]
for t, d in D.items():
    L.append(f"| unit18_{t} | {d['cells']:,} | {d['total']:,.0f} | {d['regs']:,.0f} ({d['ndff']:,}) | {d['logic']:,.0f} | {d['alu']:,.0f} |")
if len(D) == 4:
    sep = {k: sum(D[t][k] for t in ("mono", "chacha", "blake3")) for k in ("logic", "alu", "regs", "total")}
    L += ["", "| sharing: unit18_shared vs unit18_mono + unit18_chacha + unit18_blake3 | separate um^2 | shared um^2 | saved |", "|---|---:|---:|---:|"]
    for k, lab in (("logic", "logic only (all non-flip-flop cells)"), ("alu", "ALU instances only"), ("regs", "registers"), ("total", "total")):
        L.append(f"| {lab} | {sep[k]:,.0f} | {D['shared'][k]:,.0f} | {100 * (1 - D['shared'][k] / sep[k]):+.1f}% |")
    keys = sorted({k for d in D.values() for k in d["rows"]})
    L += ["", "| ALU (instances x um^2 each) | " + " | ".join(f"unit18_{t}" for t in D) + " | separate sum | shared |", "|---|" + "---:|" * (len(D) + 2)]
    for k in keys:
        n = {t: D[t]["rows"].get(k, (0, 0.0)) for t in D}
        L.append(f"| {k} | " + " | ".join(f"{n[t][0]:,} x {n[t][1]:,.0f}" if n[t][0] else "" for t in D) +
                 f" | {sum(n[t][0] for t in ('mono', 'chacha', 'blake3')):,} | {n['shared'][0]:,} |")
txt = "\n".join(L); print(txt)
if "--md" in sys.argv: open(sys.argv[sys.argv.index("--md") + 1], "w").write(txt + "\n")
