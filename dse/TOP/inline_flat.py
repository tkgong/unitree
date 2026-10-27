"""inline_flat.py - make a flattened top (flatten_pipe.py output) self-contained: every call of a datapath level
(monk_lx<k> / monk2_lx<k>, lane_mono*_kl.inc), an ARX step (axn_ops<j> / axn_fin<j>, level_ops_axn_flat.h) and a
Poseidon2 engine (p2eng<E>, p2_engine.h) is replaced by that function's body, so lane_pipe itself reads as calls of the
ALUs in alu_core.h (alu_lend / alu_add, alu_addp, alu_mul31, alu_fold, alu_canon, alu_bar31, alu_xor, ...) plus wiring.
The included files stay for constants and wiring helpers (pk, words, prow, rot31, rotl2x32, axn_ff).
    python inline_flat.py <pipe_axn_flat.h> [out, default: in place]
Substitution: template parameters -> their (constant) values, scalar parameters -> (argument), array parameters ->
the argument array with its offset folded into the index (EA[i] -> EA10[28 + i]); a body local whose name occurs in the
call's arguments is renamed first (name_i), so no argument is shadowed. #pragma HLS INLINE and (void) lines go."""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
src = sys.argv[1]; dst = sys.argv[2] if len(sys.argv) > 2 else src
top = open(src, encoding="utf-8").read()
d = os.path.dirname(os.path.abspath(src))
assert "#define AXN_COLOC 0" in top
AXN_BL = int(re.search(r"#define AXN_BL (\d+)", top).group(1))
axn_b = lambda j: j * AXN_BL

def functions(path):
    """name -> (template params, [(kind, name)], body lines) for every top-level function definition in path"""
    L = open(path, encoding="utf-8").read().split("\n"); F = {}
    i = 0
    while i < len(L):
        m = re.match(r"^(?:template<([^>]*)>\s*)?static inline void (\w+)\((.*)\)\s*\{", L[i])
        if m:
            tps = [t.split()[-1] for t in m.group(1).split(",")] if m.group(1) else []
            ps = []
            for p in m.group(3).split(","):
                p = p.strip(); arr = p.endswith("]")
                ps.append(("arr" if arr else "scal", re.match(r".*?(\w+)\s*(?:\[[^\]]*\])?$", p).group(1)))
            j = i + 1; body = []
            while L[j] != "}": body.append(L[j]); j += 1
            F[m.group(2)] = (tps, ps, body); i = j
        i += 1
    return F

F = {}
for inc in ("lane_mono_kl.inc", "lane_mono2_kl.inc"):
    p = os.path.join(d, inc)
    if os.path.exists(p): F.update({k: v for k, v in functions(p).items() if re.match(r"monk2?_lx\d+$", k)})
F.update({k: v for k, v in functions(os.path.join(HERE, "level_ops_axn_flat.h")).items() if re.match(r"axn_(ops|fin)\d$", k)})
if "p2eng<" in top: F.update({k: v for k, v in functions(os.path.join(HERE, "p2_engine.h")).items() if k == "p2eng"})

def split_top(s):
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch in "([<": depth += 1
        if ch in ")]>": depth -= 1
        if ch == "," and depth == 0: out.append(cur.strip()); cur = ""
        else: cur += ch
    out.append(cur.strip()); return out

def evalc(e):
    return int(eval(e, {"axn_b": axn_b, "axn_h": lambda j: axn_b(j) + 18}))   # AXN_COLOC = 0: h lanes 18..21 of the block

hoisted = []                                                     # BIND_STORAGE pragmas on globals: once, at the top
def inline(name, targs, args, ind):
    tps, ps, body = F[name]
    assert len(targs) == len(tps) and len(args) == len(ps), (name, targs, args)
    txt = "\n".join(body)
    # 1. rename body locals that would shadow an argument's identifiers
    pnames = {n for _, n in ps} | set(tps)
    for t in sorted({t for a in args for t in re.findall(r"[A-Za-z_]\w*", a)} - pnames - {"false", "true"}):
        if re.search(r"\b%s\b" % re.escape(t), txt): txt = re.sub(r"\b%s\b" % re.escape(t), t + "_i", txt)
    # 2. substitute the parameters (one pass)
    sub = {}
    for tp, ta in zip(tps, targs): sub[tp] = str(evalc(ta))
    arrs = {}
    for (kind, n), a in zip(ps, args):
        if kind == "arr":
            m = re.match(r"^(\w+)(?:\s*\+\s*(\d+))?$", a); assert m, (name, a)
            arrs[n] = (m.group(1), int(m.group(2) or 0))
        else: sub[n] = a if re.match(r"^\w+$", a) else f"({a})"
    def rep(m):
        n = m.group(1)
        if n in arrs:
            base, off = arrs[n]
            if m.group(2): return f"{base}[{off} + " if off else f"{base}["
            return f"({base} + {off})" if off else base
        return sub[n] + (m.group(2) or "")
    keys = sorted(set(sub) | set(arrs), key=len, reverse=True)
    txt = re.sub(r"(?<![\w.])(%s)\b(\[)?" % "|".join(map(re.escape, keys)), rep, txt)
    out = []
    for ln in txt.split("\n"):
        s = ln.strip()
        if s == "#pragma HLS INLINE" or s.startswith("(void)"): continue
        if s.startswith("#pragma HLS BIND_STORAGE"):
            if s not in hoisted: hoisted.append(s)
            continue
        out.append(ln if ln.startswith("#") else ind + ln)
    tl = f"<{', '.join(targs)}>" if targs else ""
    return [f"{ind}{{   // {name}{tl}({', '.join(args)})"] + out + [f"{ind}}}"]

res, n = [], 0
callre = re.compile(r"^(\s*)(monk2?_lx\d+|axn_(?:ops|fin)\d|p2eng)(?:<(.*?)>)?\((.*)\);\s*$")
for ln in top.split("\n"):
    m = callre.match(ln)
    if m and m.group(2) in F:
        res += inline(m.group(2), split_top(m.group(3)) if m.group(3) else [], split_top(m.group(4)), m.group(1)); n += 1
    else: res.append(ln)
txt = "\n".join(res)
anchor = "#pragma HLS PIPELINE II=1\n"
assert txt.count(anchor) == 1
txt = txt.replace(anchor, anchor + "".join(h + "\n" for h in hoisted if h not in txt))
txt = txt.replace("// pipe_axn.h - GENERATED", "// pipe_axn_flat.h - flattened and self-contained (flatten_pipe.py + inline_flat.py): every operator is an\n// alu_core.h ALU call written in lane_pipe itself.\n// pipe_axn.h - GENERATED", 1)
left = [l for l in txt.split("\n") if callre.match(l) and callre.match(l).group(2) in F]
assert not left, left[:3]
open(dst, "w", encoding="utf-8", newline="\n").write(txt.rstrip("\n") + "\n")
print(f"{dst}: {n} calls inlined, {txt.count(chr(10)) + 1} lines; ALU calls: " +
      ", ".join(f"{k} {len(re.findall(re.escape(k) + r'[<(]', txt))}" for k in ("alu_lend", "alu_addp", "alu_mul31", "alu_mul31_en", "alu_fold", "alu_fold31", "alu_canon", "alu_negm31", "alu_bar31", "alu_xor")))
