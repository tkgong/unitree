"""act_tcl.py - OpenSTA activity annotation from the measured per-net activity (vcd_act output): every net bit of the gate
netlist <top>_gl.v gets the activity (0 <-> 1 transitions per 1 ns clock period) and duty (fraction of time at 1) measured
in the gate-level replay, set on the output pin of the cell that drives it (set_power_activity -pins) or, for the primary
inputs, on the port (-input_ports). Cell outputs are taken from the cell models (ng45_cells.v, written from the liberty).
    python3 act_tcl.py <cells.v> <top>_gl.v <act.txt> <out.tcl>      -> prints the coverage"""
import re, sys
cells_v, gl_v, act_f, out_f = sys.argv[1:5]
outs = {}                                                    # cell type -> its output pins
cur = None
for ln in open(cells_v):
    m = re.match(r"\s*module\s+(\w+)", ln)
    if m: cur = m.group(1); outs[cur] = set(); continue
    m = re.match(r"\s*output\s+(?:\[[^\]]*\]\s*)?(\w+)", ln)
    if m and cur: outs[cur].add(m.group(1))
drv = {}                                                     # net bit -> "inst/pin"
inputs = set()
ncell = 0; inst = None; ctype = None
for ln in open(gl_v):
    s = ln.strip()
    m = re.match(r"input\s+(?:\[(\d+):(\d+)\]\s*)?(\w+);", s)
    if m:
        if m.group(1): inputs.update(f"{m.group(3)}[{b}]" for b in range(int(m.group(2)), int(m.group(1)) + 1))
        else: inputs.add(m.group(3))
        continue
    m = re.match(r"(\w+)\s+(\\?\S+)\s*\($", s)
    if m and m.group(1) in outs: ctype, inst = m.group(1), m.group(2); ncell += 1; continue
    if inst:
        m = re.match(r"\.(\w+)\((.*)\),?$", s)
        if m and m.group(1) in outs[ctype]:
            net = m.group(2).replace(" ", "")
            drv[net] = f"{inst}/{m.group(1)}"
        if s.startswith(");"): inst = None
span = None; nset = nin = 0; seen = set()
with open(out_f, "w") as o:
    for ln in open(act_f):
        if ln.startswith("SPAN"): span = float(ln.split()[1]); cyc = span / 1000.0; continue
        net, tg, hi = ln.split(); a = int(tg) / cyc; d = int(hi) / span
        if net in drv:
            o.write(f"set_power_activity -pins [get_pins {{{drv[net]}}}] -activity {a:.5f} -duty {d:.4f}\n"); nset += 1; seen.add(net)
        elif net in inputs and net != "clk":
            o.write(f"set_power_activity -input_ports [get_ports {{{net}}}] -activity {a:.5f} -duty {d:.4f}\n"); nin += 1
print(f"act_tcl: {ncell:,} cells, {len(drv):,} driven net bits; annotated {nset:,} cell output pins ({100 * nset / max(1, len(drv)):.2f}%) "
      f"and {nin:,} input port bits; window {cyc:,.0f} cycles")
