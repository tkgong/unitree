"""flatten_ops.py - level_ops_axn.h without macros -> level_ops_axn_flat.h (for the flattened tops): the include guard
becomes #pragma once, M_BLAKE / AXN_LANES (unused by the flattened tops) go, and #ifndef AXN_MERKLE keeps its branch
(no build defines AXN_MERKLE: the XOF second half is always computed, a Merkle node ignores lanes 4..7).
    python flatten_ops.py [level_ops_axn.h] [level_ops_axn_flat.h]"""
import re, sys
src = sys.argv[1] if len(sys.argv) > 1 else "level_ops_axn.h"
dst = sys.argv[2] if len(sys.argv) > 2 else "level_ops_axn_flat.h"
out = []
for ln in open(src, encoding="utf-8").read().split("\n"):
    s = ln.strip()
    if s == "#ifndef UNITREE_LEVEL_OPS_AXN_H": out.append("#pragma once"); continue
    if s in ("#define UNITREE_LEVEL_OPS_AXN_H", "#define M_BLAKE M_SHA", "#define AXN_LANES 22", "#endif"): continue
    if s.startswith("#ifndef AXN_MERKLE"): out.append("        // XOF second half (GGM: two children per node; a Merkle node ignores lanes 4..7)"); continue
    out.append(ln)
txt = "\n".join(out).rstrip("\n") + "\n"
txt = txt.replace("// level_ops_axn.h - ", "// level_ops_axn_flat.h - level_ops_axn.h with no macros (no include guard, M_BLAKE, AXN_LANES or #ifndef AXN_MERKLE);\n// ", 1)
left = [l for l in txt.split("\n") if re.match(r"\s*#(if|ifdef|ifndef|else|endif|define)", l)]
assert not left, left
open(dst, "w", encoding="utf-8", newline="\n").write(txt)
print(f"{dst}: no #if / #define left")
