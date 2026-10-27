#!/usr/bin/env python3
"""gen_pe.py - the bz3 unit (ChaCha20 + BLAKE3 + Monolith-31, dse/TOP/bz3) in SystemVerilog, assembled from the ALUs of RTL/.

Structure. The unit is two identical processing elements (PE) side by side; a PE is one Monolith-31 datapath (18 pipeline
levels: Bars, Bricks squares, Karatsuba Concrete tree, folds) plus the 27 ChaCha20 / BLAKE3 blocks whose 4-wide adds run on
that datapath's lendable adders (alu_lend). PE k = datapath k + the block groups of copy k (CP = k: ChaCha20 alternates the
two copies). The PEs share nothing but the issue controls (blake); each has its own lanes, registers and round indices.

Source of truth. Everything is derived from the C++ the HLS unit is built from, not re-designed:
  dp_l<k>.sv   level k of the datapath, translated from monk_lx<k> in dse/TOP/bz3/lane_mono_kl.inc (every ALU call becomes an
               instance of the RTL/alu_*.sv module of the same name; wiring stays wiring). Datapath 1 (lane_mono2_kl.inc) is
               translated too and must give the identical module.
  axn_step.sv  the six ARX steps (hand transcription of dse/TOP/level_ops_axn.h).
  pe.sv        lane_pipe of dse/TOP/bz3/pipe_axn.h executed symbolically (every lane of every level traced to its source),
               restricted to one copy; generated for both copies, which must give the identical module up to CP.
  unit_bz3.sv  two PEs + the lane map of lane_pipe's in / out ports.
Verification: RTL/pe/verify (cycle-by-cycle against the HLS C++ compiled as verify/lz3_16.dll)."""
import ctypes, os, re, sys
from cparse import parse_statements, strip_pp

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
TOP = os.path.join(REPO, "dse", "TOP")
SRC = os.path.join(TOP, "bz3")
DLL = os.path.join(TOP, "verify", "lz3_16.dll")
INC = [open(os.path.join(SRC, f), encoding="utf-8").read() for f in ("lane_mono_kl.inc", "lane_mono2_kl.inc")]
PIPE = open(os.path.join(SRC, "pipe_axn.h"), encoding="utf-8").read()

# ---------------------------------------------------------------- constants
def defines(text):
    d = {}
    for m in re.finditer(r"^#define (\w+) (0x[0-9a-fA-F]+|-?\d+)\s*(//.*)?$", text, re.M): d[m.group(1)] = int(m.group(2), 0)
    return d
def carray(text, name):
    m = re.search(r"static const ap_uint<\d+> " + name + r"\[[^=]*= (\{.*?\});", text, re.S)
    return eval(m.group(1).replace("{", "[").replace("}", "]").replace("u", ""))
C = {}
C.update(defines(INC[0])); C.update(defines(INC[1])); C.update(defines(PIPE))
L = ctypes.CDLL(DLL); L.lp_info.restype = ctypes.c_int; L.lp_info.argtypes = [ctypes.c_int]
NB = L.lp_info(1); NG = L.lp_info(14); C["AXN_BL"] = L.lp_info(11); C["LP_NIO"] = L.lp_info(9)
assert L.lp_info(13) == 0, "COLOC must be 0 (every block's h lanes inside the block)"
axn_b = lambda j: L.lp_info(1000 + 2 * j); axn_h = lambda j: L.lp_info(1001 + 2 * j)
C["AXN_BASE"] = axn_b(NB - 1) + C["AXN_BL"]; C["AXN_COLOC"] = 0     # lp_info answers axn_b only for j < NB
axn_bx = lambda j: axn_b(j) if j < NB else C["AXN_BASE"]
for m in re.finditer(r"(AXN_GLO\d+) = axn_b\((\d+)\), (AXN_GHI\d+) = axn_b\((\d+)\)", PIPE):
    C[m.group(1)] = axn_bx(int(m.group(2))); C[m.group(3)] = axn_bx(int(m.group(4)))
for m in re.finditer(r"LV_N(\d+) = maxi\((\w+), HAS\(M_MONO\) \* (\d+)\)", PIPE):
    first = C["AXN_BASE"] if m.group(2) == "AXN_BASE" else int(m.group(2)); C["LV_N" + m.group(1)] = max(first, int(m.group(3)))
NLEV = C["LP_DEPTH_M"]
C["LV_NMAX"] = max([C["LP_NIO"]] + [C[f"LV_N{k}"] for k in range(1, NLEV + 1)])
C["HAS_ARX"] = 1
MB = [C["MONO_BASE"], C["MONO2_BASE"]]; NDL = MB[1] - MB[0]               # lanes of one datapath (52)
NBP = NB // 2; NGP = NG // 2; NAL = NBP * C["AXN_BL"]                   # blocks, groups, ARX lanes of one PE
NPL = NAL + NDL                                                          # lanes of one PE
DEC = [carray(INC[0], "MONO_DEC_K"), carray(INC[1], "MONO2_DEC_K")]
KC = [carray(INC[0], "MONO_KC"), carray(INC[1], "MONO2_KC")]
assert DEC[0] == DEC[1] and KC[0] == KC[1]
LEND = [C["MONO_LEND_MAX"], C["MONO2_LEND_MAX"]]; assert LEND[0] == LEND[1]; NLEND = LEND[0]
assert C["MONO_XLEND_MAX"] <= 1 and all(C.get(f"MONO_XLEND_{k}", 0) == 0 for k in range(1, NLEV + 1)), "no lent xors in bz3"
WMASK = {1: [0, 1, 2, 3, 4, 5, 6, 7, 16, 17], 2: list(range(8)), 3: [1, 2, 5, 6], 4: [0, 1, 2, 3, 4, 5, 6, 7, 16, 17],
         5: [0, 3, 4, 7], 6: list(range(16))}


def cop(op, a, b):
    """C integer operator on python ints (only the one asked for)"""
    if op == "+": return a + b
    if op == "-": return a - b
    if op == "*": return a * b
    if op == "/": return a // b
    if op == "%": return a % b
    if op == "<": return int(a < b)
    if op == "<=": return int(a <= b)
    if op == ">": return int(a > b)
    if op == ">=": return int(a >= b)
    if op == "==": return int(a == b)
    if op == "!=": return int(a != b)
    if op == "&&": return int(bool(a) and bool(b))
    if op == "||": return int(bool(a) or bool(b))
    if op == "&": return a & b
    if op == "|": return a | b
    if op == "^": return a ^ b
    if op == "<<": return a << b
    if op == ">>": return a >> b
    raise ValueError(op)

# ---------------------------------------------------------------- datapath levels -> dp_l<k>.sv
def functions(inc, prefix):
    out = {}
    for m in re.finditer(r"static inline void " + prefix + r"_lx(\d+)\([^)]*\) \{\n(.*?)\n\}\n", inc, re.S):
        out[int(m.group(1))] = m.group(2)
    return out

class DPGen:
    """structural SV of one datapath level from its C++ body: ALU calls -> instances, everything else -> assigns"""
    def __init__(self, k, mb):
        self.k, self.mb = k, mb
        self.decl, self.body = [], []
        self.n = 0; self.vars = {}; self.seg = {}; self.arr = {}; self.env = {}
        self.sin = set(); self.cond = []; self.kc = {}; self.ninst = {}

    # values: int, or (expr, width, is_name)
    def tmp(self, w, expr, base="t"):
        name = f"{base}{self.n}"; self.n += 1
        self.decl.append(f"    logic [{w - 1}:0] {name};"); self.body.append(f"    assign {name} = {expr};")
        return (name, w, True)
    def nm(self, v):
        if isinstance(v, int): return self.tmp(64, f"64'd{v}")
        return v if v[2] else self.tmp(v[1], v[0])
    def cast(self, v, w):
        if isinstance(v, int): return (f"{w}'h{v:x}", w, False)
        if v[1] == w: return v
        return (f"{w}'({v[0]})", w, False)
    def inst(self, mod, params, ports, outw, outport, dest=None):
        self.ninst[mod] = self.ninst.get(mod, 0) + 1
        name = dest or f"a{self.n}"; self.n += 1
        if dest is None: self.decl.append(f"    logic [{outw - 1}:0] {name};")
        p = ("#(" + ", ".join(f".{a}({b})" for a, b in params) + ") ") if params else ""
        conns = ", ".join(f".{a}({b[0] if not isinstance(b, str) else b})" for a, b in ports)
        self.body.append(f"    {mod} {p}u_{name} ({conns}, .{outport}({name}));")
        return (name, outw, True)

    def ev(self, e, dest=None):
        t = e[0]
        if t == "num": return e[1]
        if t == "id":
            n = e[1]
            if n in self.env: return self.env[n]
            if n in self.vars: return self.vars[n]
            if n == "ext": return ("ext", 1, True)
            if n == "dec": return ("dec", 8, True)
            if n in ("MONO_P31", "MONO2_P31"): return ("31'h7fffffff", 31, False)
            if n in C: return C[n]
            raise KeyError(n)
        if t == "idx":
            base = e[1]
            if base[0] == "idx" and base[1] == ("id", "MONO_KC") or base[0] == "idx" and base[1] == ("id", "MONO2_KC"):
                ci = self.ev(base[2]); tt = self.ev(e[2]); assert isinstance(tt, int)
                if tt not in self.kc:
                    ci = self.nm(ci); expr = "31'h0"
                    for c in range(len(KC[0]) - 1, -1, -1): expr = f"({ci[0]} == {ci[1]}'d{c}) ? 31'h{KC[0][c][tt]:x} : {expr}"
                    self.kc[tt] = self.tmp(31, expr, "kc")
                return self.kc[tt]
            name = base[1]; ix = self.ev(e[2])
            if name == "S":
                rel = ix - self.mb; assert 0 <= rel < NDL, (self.k, ix); self.sin.add(rel); return (f"s{rel}", 64, True)
            if name in ("EA", "EB"): return (f"{name}[{32 * ix} +: 32]", 32, False)
            if name == "dec": return (f"dec[{ix}]", 1, False)
            return self.arr[name].get(ix, 0)
        if t == "range":
            b = self.nm(self.ev(e[1])); h = self.ev(e[2]); l = self.ev(e[3])
            return (f"{b[0]}[{h}:{l}]", h - l + 1, False)
        if t == "cast":
            ty = e[1]; v = self.ev(e[2])
            w = self.ev(ty[1]) if isinstance(ty, tuple) else {"u32": 32, "u64": 64, "bool": 1}.get(ty)
            if ty == "int": return v
            return self.cast(v, w)
        if t == "un":
            v = self.ev(e[2])
            if isinstance(v, int): return {"!": int(not v), "-": -v, "~": ~v}[e[1]]
            assert e[1] == "~"; v = self.nm(v); return self.tmp(v[1], f"~{v[0]}")
        if t == "bin":
            op = e[1]; a = self.ev(e[2])
            if op in ("&&", "||") and isinstance(a, int) and (bool(a) == (op == "||")): return int(op == "||")
            b = self.ev(e[3])
            if isinstance(a, int) and isinstance(b, int):
                return cop(op, a, b)
            if op == "^":
                w = max(x[1] for x in (a, b) if not isinstance(x, int)) if not (isinstance(a, int) or isinstance(b, int)) else (a[1] if not isinstance(a, int) else b[1])
                a, b = self.cast(a, w), self.cast(b, w); return self.tmp(w, f"{a[0]} ^ {b[0]}")
            if op == "<<":
                assert isinstance(b, int); a = self.nm(a); return self.tmp(a[1], f"{a[0]} << {b}")
            raise ValueError(e)
        if t == "tern":
            c = self.ev(e[1]); assert isinstance(c, int), e
            return self.ev(e[2] if c else e[3], dest)
        if t == "call":
            n, targs, args = e[1], e[2], e[3]
            tv = [self.ev(x) if x[0] != "id" or x[1] not in ("word32_t",) else 32 for x in (targs or [])]
            A = lambda i, w: self.cast(self.ev(args[i]), w)
            if n in ("alu_lend", "alu_lendp"):
                W = tv[0]
                return self.inst(n, [("W", W)], [("ext", self.ev(args[0])), ("ea", A(1, W)), ("eb", A(2, W)), ("a", A(3, W)), ("b", A(4, W))], W, "y", dest)
            if n in ("alu_addp", "alu_add"):
                W = tv[0]; return self.inst(n, [("W", W)], [("a", A(0, W)), ("b", A(1, W))], W, "y", dest)
            if n == "alu_fold": return self.inst("alu_fold", [("H", tv[0])], [("r", A(0, 32))], 31, "t", dest)
            if n == "alu_fold31": return self.inst("alu_fold31", [], [("r", A(0, 32))], 31, "t", dest)
            if n == "alu_canon": return self.inst("alu_canon", [("W", tv[0])], [("t", A(0, 31))], tv[0], "y", dest)
            if n == "alu_negm31": return self.inst("alu_negm31", [("W", tv[0])], [("t", A(0, 31))], tv[0], "y", dest)
            if n == "alu_mul31_en": return self.inst("alu_mul31_en", [], [("en", self.ev(args[0])), ("a", A(1, 31)), ("b", A(2, 31))], 62, "y", dest)
            if n == "alu_mul31": return self.inst("alu_mul31", [], [("a", A(0, 31)), ("b", A(1, 31))], 62, "y", dest)
            if n == "alu_bar31": return self.inst("alu_bar31", [], [("x", A(0, 32))], 32, "y", dest)
            if n == "rot31": return self.inst("rot31", [("R", tv[0])], [("v", A(0, 31))], 31, "y", dest)
            if n == "pk":
                lo, hi = A(0, 32), A(1, 32); return (f"{{{hi[0]}, {lo[0]}}}", 64, False)
            raise ValueError(n)
        raise ValueError(e)

    def write(self, arr, ix, v):
        if self.cond:
            old = self.arr[arr].get(ix, 0); w = 64 if arr == "M" else 32
            v, old = self.cast(v, w), self.cast(old, w)
            v = self.tmp(w, f"{self.cond[-1]} ? {v[0]} : {old[0]}")
        self.arr[arr][ix] = v

    def run(self, stmts):
        for s in stmts: self.stmt(s)

    def stmt(self, s):
        t = s[0]
        if t in ("nop",): return
        if t == "block": self.run(s[1]); return
        if t == "for":
            var, init, cond, step, body = s[1:]
            self.env[var] = self.ev(init)
            while self.ev(cond):
                self.stmt(body); self.env[var] += step
            del self.env[var]; return
        if t == "if":
            c = self.nm(self.ev(s[1])); assert s[3] is None
            self.cond.append(c[0]); self.stmt(s[2]); self.cond.pop(); return
        if t == "decl":
            ty = s[1]; w = self.ev(ty[1]) if isinstance(ty, tuple) else {"u32": 32, "u64": 64, "bool": 1, "int": None}[ty]
            for name, dims, init in s[2]:
                if dims: self.arr[name] = {}; continue
                if init is None:
                    self.seg[name] = (w, []); self.decl.append(f"    logic [{w - 1}:0] {name};"); self.vars[name] = (name, w, True); continue
                if init[0] == "call" and init[1].startswith(("alu_", "rot31")):
                    v = self.ev(init, dest=None)
                    if v[1] == w:                                        # rename the instance output to the C++ name
                        self.decl.append(f"    logic [{w - 1}:0] {name};"); self.body.append(f"    assign {name} = {v[0]};")
                        self.vars[name] = (name, w, True); continue
                v = self.cast(self.ev(init), w)
                self.decl.append(f"    logic [{w - 1}:0] {name};"); self.body.append(f"    assign {name} = {v[0]};")
                self.vars[name] = (name, w, True)
            return
        if t == "assign":
            lhs, rhs = s[1], s[2]
            v = self.ev(rhs)
            if lhs[0] == "range" and lhs[1][0] == "id":                     # var.range(h, l) = ...
                name = lhs[1][1]; h = self.ev(lhs[2]); l = self.ev(lhs[3]); assert not self.cond
                self.seg[name][1].append((h, l, self.cast(v, h - l + 1)[0])); return
            if lhs[0] == "range" and lhs[1][0] == "idx" and lhs[1][1] == ("id", "M"):   # M[lane].range(h, l) = ...
                ix = self.ev(lhs[1][2]); h = self.ev(lhs[2]); l = self.ev(lhs[3]); assert not self.cond
                old = self.arr["M"].get(ix, 0); val = self.cast(v, h - l + 1)[0]
                if not isinstance(old, int): old = self.nm(old)
                parts = []
                if h < 63: parts.append(f"{old[0]}[63:{h + 1}]" if not isinstance(old, int) else f"{63 - h}'d0")
                parts.append(val)
                if l > 0: parts.append(f"{old[0]}[{l - 1}:0]" if not isinstance(old, int) else f"{l}'d0")
                self.arr["M"][ix] = self.tmp(64, "{" + ", ".join(parts) + "}", "m"); return
            if lhs[0] == "idx" and lhs[1][0] == "id":
                arr = lhs[1][1]; ix = self.ev(lhs[2])
                if arr == "EY": self.arr.setdefault("EY", {}); self.write("EY", ix, self.cast(v, 32)); return
                if arr == "M": self.write("M", ix, self.cast(v, 64) if not isinstance(v, int) else v); return
                self.write(arr, ix, self.cast(v, 32) if not isinstance(v, int) else v); return
            raise ValueError(s)
        if t == "expr": raise ValueError(s)

    def module(self, body_text):
        self.arr["M"] = {}; self.arr["EY"] = {}
        self.run(parse_statements(strip_pp(body_text, lambda k, c: False)))
        out = []
        for name, (w, segs) in self.seg.items():
            segs = sorted(segs, key=lambda x: -x[0]); parts = []; top = w - 1
            for h, l, ex in segs:
                if h < top: parts.append(f"{top - h}'d0")
                parts.append(ex); top = l - 1
            if top >= 0: parts.append(f"{top + 1}'d0")
            out.append(f"    assign {name} = {{{', '.join(parts)}}};")
        for ix, v in self.arr["M"].items():
            rel = ix - self.mb
            if rel < 0: assert v == 0 or v[0] == "64'h0", (self.k, ix, v); continue
            assert rel < NDL
        mlines = []
        for rel in range(NDL):
            v = self.arr["M"].get(self.mb + rel, 0)
            mlines.append(f"    assign M[{64 * rel} +: 64] = {self.cast(v, 64)[0]};")
        eylines = [f"    assign EY[{32 * q} +: 32] = {self.cast(self.arr['EY'].get(q, 0), 32)[0]};" for q in range(NLEND)]
        sl = [f"    logic [63:0] s{i};\n    assign s{i} = S[{64 * i} +: 64];" for i in sorted(self.sin)]
        hdr = [f"// dp_l{self.k}.sv - GENERATED by RTL/pe/gen_pe.py from monk_lx{self.k} (dse/TOP/bz3/lane_mono_kl.inc): level {self.k} of the",
               f"// Monolith-31 datapath, lanes relative to the datapath's base. Every ALU call of the C++ is an instance of RTL/alu_*.sv.",
               f"// Instances: " + ", ".join(f"{m} {n}" for m, n in sorted(self.ninst.items())),
               f"module dp_l{self.k} (", "    input  logic [7:0]            dec,", "    input  logic                  ext,",
               f"    input  logic [{NDL}*64-1:0]      S,", f"    input  logic [{NLEND}*32-1:0]      EA,", f"    input  logic [{NLEND}*32-1:0]      EB,",
               f"    output logic [{NLEND}*32-1:0]      EY,", f"    output logic [{NDL}*64-1:0]      M", ");"]
        return "\n".join(hdr + sl + self.decl + self.body + out + mlines + eylines + ["endmodule", ""]), sorted(self.sin)

DP_SIN = {}
dp_text = {}
for k in range(1, NLEV + 1):
    texts = []
    for d, prefix in ((0, "monk"), (1, "monk2")):
        body = functions(INC[d], prefix)[k]
        txt, sin = DPGen(k, MB[d]).module(body)
        texts.append(txt); DP_SIN[k] = sin
    assert texts[0] == texts[1], f"datapath 0 and 1 differ at level {k}"
    dp_text[k] = texts[0]

# ---------------------------------------------------------------- lane_pipe, symbolic
lp_src = PIPE[PIPE.index("void lane_pipe("):]
lp_src = lp_src[lp_src.index("{") + 1:]
lp_src = "\n".join(l for l in lp_src.splitlines() if not re.match(r"\s*static (lane_t|ap_uint)", l))
lp_src = lp_src[:lp_src.rindex("}")]                                         # the function's closing brace (then only the include guard)
lp_src = strip_pp(lp_src, lambda kind, cond: {"HAS_ARX": True, "HAS(M_MONO)": True}[cond])
STATIC = re.compile(r"^(R\d+|rr|dd|mp|dd2|mp2|ar\d+|bk\d+)$")

class LP:
    def __init__(self):
        self.arr = {"in": None, "rg": None, "out": {}}; self.static = {}; self.env = {}; self.insts = []
    def ev(self, e):
        t = e[0]
        if t == "num": return e[1]
        if t == "id":
            n = e[1]
            if n in self.env: return self.env[n]
            if n in C: return C[n]
            if n in ("mono", "mono2", "htap", "blake", "r", "r2", "cfg"): return ("inp", n)
            raise KeyError(n)
        if t == "idx":
            name = e[1][1]; ix = self.ev(e[2]); assert isinstance(ix, int)
            if name == "in": return ("in", ix)
            if name == "rg": return ("rg", ix)
            if STATIC.match(name): return self.static.setdefault(name, {}).get(ix, ("reg", name, ix))
            a = self.arr[name]
            if ix not in a: raise KeyError(f"{name}[{ix}] read before written")
            return a[ix]
        if t == "cast": return self.ev(e[2])
        if t == "un":
            v = self.ev(e[2])
            if isinstance(v, int): return {"!": int(not v), "-": -v, "~": ~v}[e[1]]
            assert e[1] == "!"; return ("not", v)
        if t == "bin":
            op = e[1]; a = self.ev(e[2])
            if op in ("&&", "||") and isinstance(a, int) and (bool(a) == (op == "||")): return int(op == "||")
            b = self.ev(e[3])
            assert isinstance(a, int) and isinstance(b, int), e
            return cop(op, a, b)
        if t == "tern":
            c = self.ev(e[1]); assert isinstance(c, int), e
            return self.ev(e[2] if c else e[3])
        if t == "call":
            n = e[1]
            if n == "axn_b": return axn_bx(self.ev(e[3][0]))
            if n == "axn_h": return axn_h(self.ev(e[3][0]))
            if n == "maxi": return max(self.ev(e[3][0]), self.ev(e[3][1]))
        raise ValueError(e)
    def setv(self, lhs, v):
        if lhs[0] == "id": self.env[lhs[1]] = v; return
        name = lhs[1][1]; ix = self.ev(lhs[2])
        if STATIC.match(name): self.static.setdefault(name, {})[ix] = v
        else: self.arr[name][ix] = v
    def call(self, e):
        n, targs, args = e[1], e[2], e[3]
        m = re.match(r"axn_(ops|fin)(\d)$", n)
        if m:
            kind, step = m.group(1), int(m.group(2)); B = self.ev(targs[0]); cp = self.ev(targs[1])
            X = args[0][1]; lev = int(X[1:]); J = B // C["AXN_BL"]; assert axn_b(J) == B
            if len(targs) == 3: assert self.ev(targs[2]) == B + 18
            inst = {"kind": kind, "step": step, "cp": cp, "J": J, "lev": lev, "r": self.ev(args[1]), "blake": self.ev(args[2]),
                    "S": [self.arr[X][B + i] for i in range(C["AXN_BL"])]}
            pa = args[3]; assert pa[0] == "bin" and pa[1] == "+"; q = self.ev(pa[3]); ea = pa[2][1]
            if kind == "ops":
                eb = args[4][2][1]; inst["q"] = q
                self.insts.append(inst)
                for i in range(4): self.arr[ea][q + i] = ("ea", id(inst), i); self.arr[eb][q + i] = ("eb", id(inst), i)
            else:
                inst["EY"] = [self.arr[ea][q + i] for i in range(4)]; a = args[4][1]
                self.insts.append(inst)
                for i in WMASK[step]: self.arr[a][B + i] = ("fin", id(inst), i)
            return
        m = re.match(r"monk(2?)_lx(\d+)$", n)
        if m:
            d = 1 if m.group(1) else 0; lev = int(m.group(2)); X = args[0][1]; mm = args[2][1]
            EA, EB, EY = args[4][1], args[5][1], args[6][1]
            inst = {"kind": "dp", "d": d, "lev": lev, "dec": self.ev(args[1]), "ext": self.ev(args[3]),
                    "S": [self.arr[X].get(MB[d] + i, 0) if i in DP_SIN[lev] else 0 for i in range(NDL)],
                    "EA": [self.arr[EA][q] for q in range(NLEND)], "EB": [self.arr[EB][q] for q in range(NLEND)]}
            self.insts.append(inst)
            nm_ = C[("MONO2" if d else "MONO") + f"_K_N{lev}"] - MB[d]          # lanes the level writes
            for i in range(NDL): self.arr[mm][MB[d] + i] = ("dpm", id(inst), i) if i < nm_ else 0
            for q in range(NLEND): self.arr[EY][q] = ("dpey", id(inst), q)
            return
        raise ValueError(n)
    def run(self, stmts):
        for s in stmts: self.stmt(s)
    def stmt(self, s):
        t = s[0]
        if t == "nop": return
        if t == "block": self.run(s[1]); return
        if t == "for":
            var, init, cond, step, body = s[1:]; old = self.env.get(var)
            self.env[var] = self.ev(init)
            while self.ev(cond): self.stmt(body); self.env[var] += step
            if old is None: del self.env[var]
            else: self.env[var] = old
            return
        if t == "if":
            c = self.ev(s[1]); assert isinstance(c, int), s
            if c: self.stmt(s[2])
            elif s[3]: self.stmt(s[3])
            return
        if t == "decl":
            for name, dims, init in s[2]:
                if dims: self.arr[name] = {}; continue
                if name in ("dec", "dec2"): self.env[name] = ("dec", 0 if name == "dec" else 1); continue
                self.env[name] = self.ev(init) if init is not None else 0
            return
        if t == "assign": self.setv(s[1], self.ev(s[2])); return
        if t == "expr": self.call(s[1]); return
        raise ValueError(s)

lp = LP(); lp.run(parse_statements(lp_src))
by_id = {id(i): i for i in lp.insts}
for i in lp.insts:                                   # which datapath each ops instance feeds (from where its EA is read)
    if i["kind"] == "ops": i["dp"] = None
for i in lp.insts:
    if i["kind"] == "dp":
        for v in i["EA"] + i["EB"]:
            if isinstance(v, tuple) and v[0] in ("ea", "eb"): by_id[v[1]]["dp"] = i["d"]
for i in lp.insts:
    if i["kind"] == "fin":
        ds = {by_id[v[1]]["d"] for v in i["EY"] if isinstance(v, tuple)}; assert len(ds) == 1; i["dp"] = ds.pop()

# ---------------------------------------------------------------- registers: constant-0 propagation and liveness
nxt = {}                                             # (name, idx) -> next value
for name, a in lp.static.items():
    for ix, v in a.items(): nxt[(name, ix)] = v
def is_zero_reg(key, seen=None):
    seen = seen or set()
    if key in seen: return True                      # a cycle of holds: stays at its reset value 0
    seen.add(key)
    v = nxt.get(key, ("reg",) + key)
    if v == ("reg",) + key: return True
    if isinstance(v, int): return v == 0
    if v[0] == "reg": return is_zero_reg((v[1], v[2]), seen)
    return False
ZERO = {key for key in nxt if is_zero_reg(key)}
def norm(v):
    if isinstance(v, tuple) and v[0] == "reg" and ((v[1], v[2]) in ZERO or (v[1], v[2]) not in nxt): return 0
    if isinstance(v, tuple) and v[0] == "not": return ("not", norm(v[1]))
    return v

# ---------------------------------------------------------------- one PE
def copy_of_lane(l): return (l // NAL) if l < C["AXN_BASE"] else (0 if l < MB[1] else 1)
def loc(l, c):
    if l < C["AXN_BASE"]: assert l // NAL == c, (l, c); return l - NAL * c
    d = 0 if l < MB[1] else 1; assert d == c, (l, c); return NAL + l - MB[d]
def inst_copy(i): return i["d"] if i["kind"] == "dp" else i["J"] // NBP
def reg_copy(name, ix):
    if name.startswith("R"): return copy_of_lane(ix)
    m = re.match(r"(ar|bk)(\d+)$", name)
    if m: return int(m.group(2)) // NGP
    return {"dd": 0, "mp": 0, "dd2": 1, "mp2": 1, "rr": None}[name]
def reg_name(name, ix, c):
    if name.startswith("R"): return f"R{name[1:]}_{loc(ix, c)}"
    m = re.match(r"(ar|bk)(\d+)$", name)
    if m: return f"{m.group(1)}{int(m.group(2)) - NGP * c}_{ix}"
    return f"{name.rstrip('2')}_{ix}"
def reg_width(name): return 64 if name.startswith("R") else 9 if name.startswith(("ar", "rr")) else 8 if name.startswith("dd") else 1

def pe_text(c):
    I = [i for i in lp.insts if inst_copy(i) == c]
    iname = {}
    for i in I:
        iname[id(i)] = f"dp{i['lev']}" if i["kind"] == "dp" else f"{i['kind']}{i['lev']}_b{i['J'] - NBP * c}"
    used = set()
    def ex(v, w):
        v = norm(v)
        if isinstance(v, int): return f"{w}'d{v}"
        k = v[0]
        if k == "in": return f"pin[{64 * loc(v[1], c)} +: 64]"
        if k == "reg":
            assert reg_copy(v[1], v[2]) in (c, None); used.add((v[1], v[2])); return reg_name(v[1], v[2], c)
        if k == "rg": g = v[1] - NGP * c; assert 0 <= g < NGP; return f"rg[{9 * g} +: 9]"
        if k == "inp":
            n = v[1]
            if n == "blake": return "blake"
            if (n in ("mono", "r") and c == 0) or (n in ("mono2", "r2") and c == 1): return n.rstrip("2")
            raise AssertionError(v)
        if k == "dec": assert v[1] == c; return "dec"
        if k == "not": return f"!{ex(v[1], 1)}"
        if k in ("ea", "eb"): return f"{iname[v[1]]}_{k}[{32 * v[2]} +: 32]"
        if k == "fin": return f"{iname[v[1]]}_m[{64 * v[2]} +: 64]"
        if k == "dpm": return f"{iname[v[1]]}_m[{64 * v[2]} +: 64]"
        if k == "dpey": return f"{iname[v[1]]}_ey[{32 * v[2]} +: 32]"
        raise ValueError(v)
    def cat(vals, w): return "{" + ", ".join(ex(v, w) for v in reversed(vals)) + "}"
    body = []
    for i in sorted(I, key=lambda i: (i["lev"], {"ops": 0, "dp": 1, "fin": 2}[i["kind"]], i.get("J", 0))):
        n = iname[id(i)]
        if i["kind"] == "ops":
            assert i["cp"] == c
            body += [f"    logic [4*32-1:0] {n}_ea, {n}_eb;",
                     f"    axn_ops #(.STEP({i['step']}), .CP(CP)) u_{n} (.S({cat(i['S'], 64)}), .r({ex(i['r'], 9)}), .blake({ex(i['blake'], 1)}), .EA({n}_ea), .EB({n}_eb));"]
        elif i["kind"] == "fin":
            assert i["cp"] == c
            body += [f"    logic [22*64-1:0] {n}_m;",
                     f"    axn_fin #(.STEP({i['step']}), .CP(CP)) u_{n} (.S({cat(i['S'], 64)}), .r({ex(i['r'], 9)}), .blake({ex(i['blake'], 1)}), .EY({cat(i['EY'], 32)}), .M({n}_m));"]
        else:
            body += [f"    logic [{NLEND}*32-1:0] {n}_ey;", f"    logic [{NDL}*64-1:0] {n}_m;",
                     f"    dp_l{i['lev']} u_{n} (.dec({ex(i['dec'], 8)}), .ext({ex(i['ext'], 1)}), .S({cat(i['S'], 64)}), .EA({cat(i['EA'], 32)}), .EB({cat(i['EB'], 32)}), .EY({n}_ey), .M({n}_m));"]
    outs = []
    for l in range(NPL):
        gl = l + NAL * c if l < NAL else MB[c] + l - NAL
        v = lp.arr["out"].get(gl, 0) if gl < C["LP_NIO"] else 0
        outs.append(f"    assign pout[{64 * l} +: 64] = {ex(v, 64)};")
    # registers: the live ones, transitively from what the outputs and instances read
    regs = []; done = set(); stack = list(used)
    while stack:
        key = stack.pop()
        if key in done: continue
        done.add(key); nv = norm(nxt[key])
        before = set(used); expr = ex(nv, reg_width(key[0])); stack += list(used - before)
        regs.append((key, expr))
    regs.sort(key=lambda kv: (kv[0][0][0], int(re.sub(r"\D", "", kv[0][0]) or 0), kv[0][1]))
    decl = [f"    logic [{reg_width(k[0]) - 1}:0] {reg_name(k[0], k[1], c)};" for k, _ in regs]
    ff = ["    always_ff @(posedge clk) begin", "        if (rst) begin"] + \
         [f"            {reg_name(k[0], k[1], c)} <= '0;" for k, _ in regs] + ["        end else begin"] + \
         [f"            {reg_name(k[0], k[1], c)} <= {e};" for k, e in regs] + ["        end", "    end"]
    dec = "    assign dec = mono ? (" + " : ".join(f"(r == 9'd{i}) ? 8'd{v}" for i, v in enumerate(DEC[0])) + f" : 8'd{DEC[0][0]}) : 8'd0;"
    nreg = sum(reg_width(k[0]) for k, _ in regs)
    hdr = ["// pe.sv - GENERATED by RTL/pe/gen_pe.py from lane_pipe (dse/TOP/bz3/pipe_axn.h): one processing element of the bz3 unit,",
           f"// = one Monolith-31 datapath (dp_l1..dp_l{NLEV}, {NDL} lanes) + the {NBP} ChaCha20 / BLAKE3 blocks of copy CP ({NGP} block groups,",
           f"// {NAL} lanes) whose adds run on that datapath's lent adders. {NLEV} pipeline levels, II = 1; {len(regs)} registers ({nreg:,} bits).",
           "// Lanes: 0..%d the blocks (block j at 22 j), %d..%d the datapath. rg: round index of each of the PE's %d block groups." % (NAL - 1, NAL, NPL - 1, NGP),
           "module pe #(", "    parameter int CP = 0", ") (", "    input  logic                 clk,", "    input  logic                 rst,",
           f"    input  logic [{NPL}*64-1:0]    pin,", f"    output logic [{NPL}*64-1:0]    pout,", "    input  logic                 mono,",
           "    input  logic [8:0]           r,", "    input  logic                 blake,", f"    input  logic [{NGP}*9-1:0]       rg", ");",
           "    logic [7:0] dec;", dec]
    return "\n".join(hdr + decl + body + ff + outs + ["endmodule", ""]), len(regs), nreg, I

pe0, nreg0, bits0, I0 = pe_text(0)
pe1, nreg1, bits1, I1 = pe_text(1)
assert pe0 == pe1, "the two copies give different PEs"

# ---------------------------------------------------------------- write
os.makedirs(HERE, exist_ok=True)
for k, t in dp_text.items(): open(os.path.join(HERE, f"dp_l{k}.sv"), "w", newline="\n").write(t)
open(os.path.join(HERE, "pe.sv"), "w", newline="\n").write(pe0)
NIO = C["LP_NIO"]
unit = [f"// unit_bz3.sv - GENERATED by RTL/pe/gen_pe.py: the bz3 unit = two PEs (pe.sv, CP = 0 / 1); ports as lane_pipe in",
        f"// dse/TOP/bz3/pipe_axn.h ({NIO} lanes in / out, one issue per clock; the HLS call = one clock edge).",
        "module unit_bz3 (", "    input  logic                 clk,", "    input  logic                 rst,",
        f"    input  logic [{NIO}*64-1:0]   lin,", f"    output logic [{NIO}*64-1:0]   lout,",
        "    input  logic                 mono, mono2, htap, blake,", "    input  logic [8:0]           r, r2,",
        f"    input  logic [{NG}*9-1:0]       rg", ");"]
for c in range(2):
    unit.append(f"    logic [{NPL}*64-1:0] pin{c}, pout{c};")
    for l in range(NPL):
        gl = l + NAL * c if l < NAL else MB[c] + l - NAL
        unit.append(f"    assign pin{c}[{64 * l} +: 64] = " + (f"lin[{64 * gl} +: 64];" if gl < NIO else "64'd0;"))
    unit.append(f"    pe #(.CP({c})) u_pe{c} (.clk(clk), .rst(rst), .pin(pin{c}), .pout(pout{c}), .mono({'mono' if c == 0 else 'mono2'}), "
                f".r({'r' if c == 0 else 'r2'}), .blake(blake), .rg(rg[{9 * NGP * c} +: {9 * NGP}]));")
for gl in range(NIO):
    c = copy_of_lane(gl); unit.append(f"    assign lout[{64 * gl} +: 64] = pout{c}[{64 * loc(gl, c)} +: 64];")
unit += ["endmodule", ""]
open(os.path.join(HERE, "unit_bz3.sv"), "w", newline="\n").write("\n".join(unit))
cnt = {}
for k in range(1, NLEV + 1):
    for m in re.finditer(r"// Instances: (.*)", dp_text[k]):
        for part in m.group(1).split(", "):
            mod, n = part.rsplit(" ", 1); cnt[mod] = cnt.get(mod, 0) + int(n)
print(f"PE: {len(I0)} level instances ({sum(1 for i in I0 if i['kind'] == 'dp')} datapath levels, {sum(1 for i in I0 if i['kind'] == 'ops')} ARX ops, "
      f"{sum(1 for i in I0 if i['kind'] == 'fin')} ARX fin), {nreg0} registers ({bits0:,} bits); copies 0 and 1 identical up to CP")
print("ALU instances in one datapath:", ", ".join(f"{m} {n}" for m, n in sorted(cnt.items())))
print("written:", ", ".join(sorted(f for f in os.listdir(HERE) if f.endswith(".sv"))))
