"""The ALU inventory of one unit (bz = four primitives, bz3 = ChaCha20 + BLAKE3 + Monolith, no Poseidon2) priced three
ways: the README gate model, the Nangate45 area-only synthesis (area_nangate45_area.md) and the OpenROAD timing-driven
placement at 1 ns (orfs_results.md: ALU logic um^2 per design, no wrapper flip-flops).
    python3 unit_alus.py bz3 [--md out.md]"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); unit = sys.argv[1] if len(sys.argv) > 1 else "bz3"
out = sys.argv[sys.argv.index("--md") + 1] if "--md" in sys.argv else ""
NAND2 = 0.798
def table(path):
    T = {}
    for l in open(path, encoding="utf-8"):
        c = [x.strip() for x in l.strip().strip("|").split("|")]
        if len(c) >= 3 and c[0] and not c[0].startswith("-") and c[0] not in ("module", "design (between registers)"): T[c[0]] = c
    return T
A = table(os.path.join(HERE, "area_nangate45_area.md"))         # tag -> [tag, cells, area, nand2, model, ratio, what]
O = table(os.path.join(HERE, "orfs_results.md"))                 # name -> [name, total, ffs, buf, alu logic, slack, met]
def orfs_key(mod, params):                                        # the orfs table names
    if mod in ("alu_lend", "alu_add", "alu_canon", "alu_negm31"): return f"{mod} W={params['W']}"
    if mod == "alu_fold": return f"alu_fold H={params['H']}"
    return {"alu_mul31": "alu_mul31 (one stage, reference)", "alu_mul31_p2": "alu_mul31_p2 (Dadda, two stages)",
            "alu_mul31_en_p2": "alu_mul31_en_p2 (two stages)"}.get(mod, mod)
def tag(mod, params): return mod + "".join(f"_{k}{v}" for k, v in params.items())
# inventories: (module, params, instances, class)
if unit == "bz3":
    INV = [("alu_lend", {"W": W}, 2 * n, "lent adders") for W, n in {32: 210, 33: 100, 34: 52, 35: 33, 36: 20, 37: 17, 38: 13, 39: 8, 40: 2, 41: 1}.items()]
    INV += [("alu_add", {"W": W}, 2 * n, "private adders") for W, n in {32: 19, 33: 3, 35: 5, 36: 3, 37: 7, 38: 5, 39: 8, 40: 2, 41: 1}.items()]
    INV += [("alu_mul31_en_p2", {}, 30, "multipliers (two-stage)")]
    INV += [("alu_fold", {"H": H}, 2 * n, "folds") for H, n in {2: 15, 4: 41, 8: 11, 9: 3, 10: 2}.items()]
    INV += [("alu_canon", {"W": 32}, 62, "canon"), ("alu_bar31", {}, 16, "Bars"), ("alu_xor", {}, 798, "64-bit xors (counted in the generated unit, RTL/pe)")]
else:
    INV = [("alu_lend", {"W": W}, 2 * n, "lent adders") for W, n in {32: 222, 33: 88, 34: 52, 35: 33, 36: 20, 37: 17, 38: 13, 39: 8, 40: 2, 41: 1}.items()]
    INV += [("alu_add", {"W": W}, 2 * n, "private adders") for W, n in {32: 57, 35: 5, 36: 3, 37: 7, 38: 5, 39: 8, 40: 2, 41: 1}.items()]
    INV += [("alu_add", {"W": W}, 4 * n, "private adders (engines)") for W, n in {32: 27, 33: 6, 34: 17, 35: 17}.items()]
    INV += [("alu_mul31_p2", {}, 76, "multipliers (two-stage)"), ("alu_mul31_en_p2", {}, 32, "multipliers (two-stage)")]
    INV += [("alu_fold", {"H": H}, 2 * n, "folds") for H, n in {1: 16, 4: 41, 5: 16, 6: 16, 8: 11, 9: 3, 10: 2}.items()]
    INV += [("alu_fold31", {}, 172, "folds"), ("alu_canon", {"W": 32}, 128, "canon"), ("alu_canon", {"W": 31}, 64, "canon"),
            ("alu_negm31", {"W": 33}, 4, "negm31"), ("alu_bar31", {}, 16, "Bars"), ("alu_xor", {}, 1005, "64-bit xors (csynth xor bits / 64)")]
def num(x): return float(x.replace(",", "")) if x and x not in ("-", "") else 0.0
L = ["| ALU | instances | gate model NAND2 each | area-only um^2 each | timing-driven (1 ns) ALU logic um^2 each | slack | x instances: model NAND2 | area-only um^2 | timing-driven um^2 |",
     "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
tot = {}
for mod, params, n, cls in INV:
    a = A[tag(mod, params)]; o = O.get(orfs_key(mod, params))
    model = num(a[4]); area = num(a[2]); tdr = num(o[4]) if o else 0.0; slack = o[5] if o else "n/a"
    t = tot.setdefault(cls, [0, 0.0, 0.0, 0.0]); t[0] += n; t[1] += n * model; t[2] += n * area; t[3] += n * tdr
    L.append(f"| {mod} {params if params else ''} | {n} | {model:,.0f} | {area:,.1f} | {tdr:,.0f} | {slack} | {n * model:,.0f} | {n * area:,.0f} | {n * tdr:,.0f} |")
L += ["", "| class | instances | gate model NAND2 | area-only um^2 (NAND2 eq) | timing-driven um^2 (NAND2 eq) |", "|---|---:|---:|---:|---:|"]
G = [0, 0.0, 0.0, 0.0]
for cls, t in tot.items():
    for i in range(4): G[i] += t[i]
    L.append(f"| {cls} | {t[0]:,} | {t[1]:,.0f} | {t[2]:,.0f} ({t[2] / NAND2:,.0f}) | {t[3]:,.0f} ({t[3] / NAND2:,.0f}) |")
L.append(f"| **total {unit}** | {G[0]:,} | {G[1]:,.0f} | {G[2]:,.0f} ({G[2] / NAND2:,.0f}) | {G[3]:,.0f} ({G[3] / NAND2:,.0f}) |")
txt = "\n".join(L); print(txt)
if out: open(out, "w", encoding="utf-8").write(txt + "\n")
