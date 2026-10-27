"""The ALU inventory of the bz unit (RTL/README.md) priced two ways: the README's NAND2-equivalent gate model, and the
Nangate45 area-only synthesis of each module (area_nangate45_area.md, NAND2 eq = area / NAND2_X1 area).
    python3 array_totals.py [area_nangate45_area.md]"""
import re, sys, os
F = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "area_nangate45_area.md")
T = {}
for l in open(F, encoding="utf-8"):
    c = [x.strip() for x in l.strip().strip("|").split("|")]
    if len(c) >= 6 and re.match(r"^[0-9,]+$", c[3] or "x") and re.match(r"^[0-9,]+$", c[4] or "x"):
        T[c[0]] = (int(c[3].replace(",", "")), int(c[4].replace(",", "")))        # synth NAND2 eq, gate model
INV = []   # (table row, instances, label)
for W, n in {32: 222, 33: 88, 34: 52, 35: 33, 36: 20, 37: 17, 38: 13, 39: 8, 40: 2, 41: 1}.items():
    INV.append((f"alu_lend_W{W}", 2 * n, "lent adders (ALU-ADD + lend select)"))
for W, n in {32: 57, 35: 5, 36: 3, 37: 7, 38: 5, 39: 8, 40: 2, 41: 1}.items():
    INV.append((f"alu_add_W{W}", 2 * n, "private adders, datapaths"))
for W, n in {32: 27, 33: 6, 34: 17, 35: 17}.items():
    INV.append((f"alu_add_W{W}", 4 * n, "private adders, Poseidon2 engines"))
INV += [("alu_mul31", 76, "multipliers"), ("alu_mul31_en", 32, "multipliers")]
for H, n in {1: 16, 4: 41, 5: 16, 6: 16, 8: 11, 9: 3, 10: 2}.items():
    INV.append((f"alu_fold_H{H}", 2 * n, "folds"))
INV += [("alu_fold31", 172, "folds"), ("alu_canon_W32", 128, "canon"), ("alu_canon_W31", 64, "canon"),
        ("alu_negm31_W33", 4, "negm31"), ("alu_bar31", 2, "Bars"),
        ("alu_xor", 1005, "64-bit xors (csynth: 64,318 xor bits in bz_16f / 64)")]
cat = {}
for row, n, label in INV:
    s, m = T[row]; a, b, k = cat.get(label, (0, 0, 0)); cat[label] = (a + n * s, b + n * m, k + n)
print("| ALU class | instances | gate model NAND2 | Nangate45 synth NAND2 eq | synth / model |")
print("|---|---:|---:|---:|---:|")
ts = tm = tn = 0
for label, (s, m, n) in cat.items():
    ts += s; tm += m; tn += n
    print(f"| {label} | {n:,} | {m:,} | {s:,} | {s / m:.2f} |")
print(f"| total | {tn:,} | {tm:,} | {ts:,} | {ts / tm:.2f} |")
