"""flatten_pipe.py - resolve every build-mode conditional of a generated pipe_axn.h for one MODES_MASK:
#if HAS_ARX / #if HAS(M_MONO) / #ifdef AXN_MERKLE / #else / #endif blocks, the HAS() / HAS_ARX macros, and the
mode-dependent ?: expressions (blake bit, lending enable, lane counts). The output has no #if at all (the include guard
becomes #pragma once); plain #defines that other headers read (MODES_MASK, AXN_BL, ...) stay.
    python flatten_pipe.py <pipe_axn.h> <out.h> [mask, default 0x16]"""
import re, sys
src, dst = sys.argv[1], sys.argv[2]
MASK = int(sys.argv[3], 0) if len(sys.argv) > 3 else 0x16
M_SHA, M_CHACHA, M_MONO = 1, 2, 4
HAS = lambda m: (MASK >> m) & 1
HAS_ARX = HAS(M_CHACHA) or HAS(M_SHA)
BLAKE_ONLY, CHACHA_ONLY = (MASK & 0x06) == 0x02, (MASK & 0x06) == 0x04
COND = {"HAS_ARX": HAS_ARX, "HAS(M_MONO)": HAS(M_MONO), "AXN_MERKLE": False}

lines = open(src, encoding="utf-8").read().split("\n")
out, stack = [], []                                  # stack of (taking this branch, any branch taken)
live = lambda: all(t for t, _ in stack)
i = 0
while i < len(lines):
    ln = lines[i]; s = ln.strip()
    if s == "#ifndef UNITREE_PIPE_AXN_H" and lines[i + 1].strip() == "#define UNITREE_PIPE_AXN_H":
        out.append("#pragma once"); stack.append(("guard", True)); i += 2; continue
    if s == "#ifndef MODES_MASK":                    # #ifndef MODES_MASK / #define MODES_MASK x / #endif -> the build's mask
        out.append(f"#define MODES_MASK 0x{MASK:02X}"); i += 3; continue
    if s.startswith("#if ") or s.startswith("#ifdef ") or s.startswith("#ifndef "):
        key = s.split(None, 1)[1].strip()
        assert key in COND, f"unknown condition: {s}"
        v = COND[key] if not s.startswith("#ifndef") else not COND[key]
        stack.append((bool(v), bool(v))); i += 1; continue
    if s == "#else":
        t, taken = stack.pop(); stack.append((not taken, True)); i += 1; continue
    if s == "#endif":
        top = stack.pop(); i += 1
        continue
    if live(): out.append(ln)
    i += 1
assert not [x for x in stack if x[0] != "guard"], "unbalanced #if"
txt = "\n".join(out)

def blk(m):                                           # the blake bit: constant in single-ARX-primitive builds
    return "true" if BLAKE_ONLY else "false" if CHACHA_ONLY else m.group(1)
txt = re.sub(r"\(\(\(\(MODES_MASK\) & 0x06\) == 0x02\) \? true : \(\(\(MODES_MASK\) & 0x06\) == 0x04\) \? false : \(bool\)([A-Za-z_]\w*(?:\[\d+\])?)\)", blk, txt)
txt = re.sub(r"\(HAS_ARX \? !\(bool\)(\w+\[\d+\]) : false\)", (lambda m: "!" + m.group(1)) if HAS_ARX else "false", txt)
rep = [
    ("#define HAS(m) ((MODES_MASK >> (m)) & 1)\n#define HAS_ARX (HAS(M_CHACHA) || HAS(M_BLAKE))\n", ""),
    ("#define AXN_BL (HAS(M_BLAKE) ? 22 : 18)", f"#define AXN_BL {22 if HAS(M_SHA) else 18}"),
]
for a, b in rep:
    assert txt.count(a) == 1, a[:50]; txt = txt.replace(a, b)
txt = re.sub(r"#define AXN_COLOC \(\(HAS_ARX && HAS\(M_MONO\) && HAS\(M_BLAKE\) && !AXN_MERKLE_FLAG\) \? (\d+) : 0\)",
             lambda m: f"#define AXN_COLOC {m.group(1) if (HAS_ARX and HAS(M_MONO) and HAS(M_SHA)) else 0}", txt)
txt = re.sub(r"static constexpr int AXN_BASE = HAS_ARX \? (axn_b\(\d+\)) : 0;", lambda m: f"static constexpr int AXN_BASE = {m.group(1) if HAS_ARX else '0'};", txt)
txt = re.sub(r"static constexpr int LP_NIO = HAS\(M_MONO\) \? ([^:;]+) : AXN_BASE;", lambda m: f"static constexpr int LP_NIO = {m.group(1) if HAS(M_MONO) else 'AXN_BASE'};", txt)
txt = txt.replace('static_assert(!(HAS_ARX && HAS(M_MONO)) || AXN_BASE == MONO_BASE, ', 'static_assert(AXN_BASE == MONO_BASE, ' if (HAS_ARX and HAS(M_MONO)) else 'static_assert(true, ')
txt = re.sub(r"HAS\(M_MONO\) \* (\d+)", lambda m: m.group(1) if HAS(M_MONO) else "0", txt)
txt = re.sub(r"maxi\((?:0|AXN_BASE), (\d+)\)", lambda m: m.group(1) if not HAS_ARX else m.group(0), txt)
txt = re.sub(r"static constexpr int (LV_N\d+) = maxi\(0, (\d+)\);", r"static constexpr int \1 = \2;", txt)
# a dead statement once AXN_COLOC = 0
txt = re.sub(r"\n        if \(AXN_COLOC > 0 && htap [^\n]*", "" if "#define AXN_COLOC 0" in txt else r"\g<0>", txt)
txt = txt.replace('#include "level_ops_axn.h"', '#include "level_ops_axn_flat.h"')   # its macro-free copy (flatten_ops.py)
left = [l for l in txt.split("\n") if re.search(r"#if|#else|#endif|HAS\(|HAS_ARX|MODES_MASK\) & 0x06", l)]
assert not left, left[:5]
open(dst, "w", encoding="utf-8", newline="\n").write(txt.rstrip("\n") + "\n")
print(f"{dst}: {len(lines)} -> {txt.count(chr(10)) + 1} lines, mask 0x{MASK:02X}, no #if / HAS() left")
