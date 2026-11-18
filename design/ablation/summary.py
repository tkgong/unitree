import collections, os, re, sys
O = sys.argv[1]
LIB = open(O + "/lib.txt").read().strip()
area, cur = {}, None
for ln in open(LIB, errors="replace"):
    m = re.match(r"\s*cell\s*\(\s*\"?(\w+)\"?\s*\)", ln)
    if m:
        cur = m.group(1)
        continue
    m = re.match(r"\s*area\s*:\s*([\d.]+)", ln)
    if m and cur and cur not in area:
        area[cur] = float(m.group(1))

def split(path):
    s = open(path, errors="replace").read()
    if "=== design hierarchy ===" in s:
        s = s[:s.rfind("=== design hierarchy ===")]
    mods = {}
    for sec in re.split(r"^=== ", s, flags=re.M)[1:]:
        name = sec.split(" ===")[0].strip()
        cells = {}
        for ln in sec.split("\n"):
            m = re.match(r"^\s+(\d+)\s+(?:[\d.E+-]+|-)\s+(\S+)\s*$", ln)
            if m:
                cells[m.group(2)] = int(m.group(1))
                continue
            m = re.match(r"^\s{5,}(\S+)\s+(\d+)\s*$", ln)
            if m and not m.group(1).startswith("Number"):
                cells[m.group(1)] = int(m.group(2))
        cells.pop("cells", None)
        mods[name] = cells
    top = [m for m in mods if re.search(r"unit18_\w+$", m)][0]
    inst, order = {top: 1}, [top]
    for m in order:
        for c, n in mods[m].items():
            if c in mods:
                inst[c] = inst.get(c, 0) + n * inst[m]
                if c not in order:
                    order.append(c)
    d = {"alu": 0.0, "lend": 0.0}
    for m, n in inst.items():
        isalu = re.search(r"(^|\\)alu_", m) is not None
        islend = re.search(r"(^|\\)alu_lend", m) is not None
        for c, k in mods[m].items():
            if c in mods or c not in area or c.startswith("DFF"):
                continue
            if islend:
                d["lend"] += n * k * area[c]
            elif isalu:
                d["alu"] += n * k * area[c]
    return d

def netlist(path):
    cnt, pat = collections.Counter(), re.compile(r"^\s*([A-Z][A-Z0-9]*_X\d+)\s")
    for ln in open(path, errors="replace"):
        m = pat.match(ln)
        if m:
            cnt[m.group(1)] += 1
    return {"total": sum(v * area.get(c, 0.0) for c, v in cnt.items()), "nff": sum(v for c, v in cnt.items() if c.startswith("DFF")),
            "regs": sum(v * area.get(c, 0.0) for c, v in cnt.items() if c.startswith("DFF"))}

def wns(n, f):
    p = O + "/" + n + f
    w = re.findall(r"^wns ([-\d.]+)", open(p, errors="replace").read(), re.M) if os.path.exists(p) else []
    return w[-1] if w else ""

NAME = {"chacha": "ChaCha20 standalone", "blake3": "BLAKE3 standalone", "mono": "Monolith-31 standalone",
        "sep": "Three standalone datapaths", "alu_only": "Shared ALUs only", "reg_strict": "+ Shared registers",
        "reg_lane": "+ Shared registers, ChaCha20 on the BLAKE3 register of the same lane", "bind": "+ Static operand binding"}
KEYS = ("total", "nff", "regs", "alu", "lend", "other")
D = {}
for n in ("chacha", "blake3", "mono", "alu_only", "reg_strict", "reg_lane", "bind"):
    if os.path.exists(O + "/" + n + "_rep.v") and os.path.exists(O + "/" + n + "_ka.txt"):
        d = netlist(O + "/" + n + "_rep.v")
        d.update(split(O + "/" + n + "_ka.txt"))
        d["other"] = d["total"] - d["regs"] - d["alu"] - d["lend"]
        D[n] = d
if all(k in D for k in ("chacha", "blake3", "mono")):
    D["sep"] = {k: sum(D[t][k] for t in ("chacha", "blake3", "mono")) for k in KEYS}
base = D.get("sep")
print("design,area_um2,saved_percent,flip_flops,registers_um2,alu_um2,lend_selects_um2,other_logic_um2,select_overhead_um2,select_overhead_mux2_bits,wns_repair_ns,wns_signoff_ns")
for n in ("chacha", "blake3", "mono", "sep", "alu_only", "reg_strict", "reg_lane", "bind"):
    if n not in D:
        continue
    d = D[n]
    sh = base is not None and n not in ("chacha", "blake3", "mono", "sep")
    ov = d["lend"] + d["other"] - base["other"] if sh else 0.0
    print("%s,%.0f,%s,%d,%.0f,%.0f,%.0f,%.0f,%s,%s,%s,%s" % (
        NAME[n], d["total"], "%.1f" % (100 * (1 - d["total"] / base["total"])) if sh else "", d["nff"], d["regs"], d["alu"], d["lend"], d["other"],
        "%.0f" % ov if sh else "", "%.0f" % (ov / area["MUX2_X1"]) if sh else "", wns(n, "_repair.txt"), wns(n, "_sta.txt")))
