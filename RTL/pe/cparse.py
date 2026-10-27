"""cparse.py - a parser for the C++ subset the unit's generators emit (dse/TOP/bz3/*.inc, pipe_axn.h lane_pipe): statements
(declarations, assignments, for / if, blocks, calls) and C expressions with ap_uint casts, .range(h, l) and template calls.
AST nodes are tuples:
  expressions: ('num', v) ('id', name) ('idx', base, index) ('range', base, h, l) ('call', name, targs, args)
               ('un', op, x) ('bin', op, a, b) ('tern', c, a, b) ('cast', type, x)       type: ('ap', W) | 'u32' | 'u64' | 'bool' | 'int'
  statements:  ('for', var, init, cond, step, body) ('if', cond, then, else) ('block', [stmts]) ('decl', type, [(name, [dims], init)])
               ('assign', lhs, rhs) ('expr', e) ('nop',)"""
import re

TOK = re.compile(r"\s+|//[^\n]*|(0[xX][0-9a-fA-F]+[uUlL]*|\d+[uUlL]*)|([A-Za-z_]\w*)|(<<|>>|<=|>=|==|!=|&&|\|\||\+\+|--|\+=|-=|[-+*/%<>=!~^&|?:;,.()\[\]{}])")
TEMPLATE_FUNCS = {"alu_lend", "alu_lendp", "alu_add", "alu_addp", "alu_fold", "alu_canon", "alu_negm31", "rot31", "rotl2x32",
                  "prow", "axn_ff"} | {f"axn_ops{i}" for i in range(1, 7)} | {f"axn_fin{i}" for i in range(1, 7)}
TYPES = {"ap_uint", "word32_t", "lane_t", "bool", "int", "unsigned", "const"}


def tokenize(src):
    out = []
    for m in TOK.finditer(src):
        if m.group(1): out.append(("num", int(m.group(1).rstrip("uUlL"), 0)))
        elif m.group(2): out.append(("id", m.group(2)))
        elif m.group(3): out.append(("op", m.group(3)))
    rest = TOK.sub("", src)
    if rest.strip(): raise SyntaxError("untokenized: " + rest[:80])
    return out


class Parser:
    def __init__(self, src):
        self.t = tokenize(src); self.i = 0

    def peek(self, k=0):
        j = self.i + k
        return self.t[j] if j < len(self.t) else ("eof", None)

    def take(self, val=None):
        tok = self.peek()
        if val is not None and tok[1] != val: raise SyntaxError(f"expected {val!r}, got {tok} near {self.t[max(0, self.i - 8):self.i + 8]}")
        self.i += 1; return tok

    def at(self, val): return self.peek()[1] == val

    # ---------------- types ----------------
    def is_type_start(self, k=0):
        tok = self.peek(k)
        return tok[0] == "id" and tok[1] in TYPES

    def parse_type(self):
        if self.at("const"): self.take()
        tok = self.take()[1]
        if tok == "ap_uint":
            self.take("<"); w = self.parse_expr(no_gt=True); self.take(">"); return ("ap", w)
        if tok == "unsigned":
            if self.peek()[1] in ("long", "int"): self.take()
            if self.peek()[1] == "long": self.take()
            return "int"
        return {"word32_t": "u32", "lane_t": "u64", "bool": "bool", "int": "int"}[tok]

    # ---------------- expressions ----------------
    def parse_expr(self, no_gt=False):
        return self.ternary(no_gt)

    def ternary(self, no_gt):
        c = self.binary(0, no_gt)
        if self.at("?"):
            self.take(); a = self.ternary(no_gt); self.take(":"); b = self.ternary(no_gt)
            return ("tern", c, a, b)
        return c

    PREC = [("||",), ("&&",), ("|",), ("^",), ("&",), ("==", "!="), ("<", "<=", ">", ">="), ("<<", ">>"), ("+", "-"), ("*", "/", "%")]

    def binary(self, lvl, no_gt):
        if lvl == len(self.PREC): return self.unary(no_gt)
        a = self.binary(lvl + 1, no_gt)
        while self.peek()[0] == "op" and self.peek()[1] in self.PREC[lvl] and not (no_gt and self.peek()[1] in (">", ">>")):
            op = self.take()[1]; b = self.binary(lvl + 1, no_gt); a = ("bin", op, a, b)
        return a

    def unary(self, no_gt):
        tok = self.peek()
        if tok[1] in ("!", "~", "-"):
            self.take(); return ("un", tok[1], self.unary(no_gt))
        if tok[1] == "(" and self.is_type_start(1):
            self.take(); ty = self.parse_type(); self.take(")")
            return ("cast", ty, self.unary(no_gt))
        return self.postfix(no_gt)

    def postfix(self, no_gt):
        e = self.primary(no_gt)
        while True:
            if self.at("["):
                self.take(); ix = self.parse_expr(); self.take("]"); e = ("idx", e, ix)
            elif self.at(".") and self.peek(1)[1] == "range":
                self.take(); self.take(); self.take("("); h = self.parse_expr(); self.take(","); l = self.parse_expr(); self.take(")")
                e = ("range", e, h, l)
            else:
                break
        return e

    def primary(self, no_gt):
        tok = self.take()
        if tok[0] == "num": return ("num", tok[1])
        if tok[1] == "(":
            e = self.parse_expr(); self.take(")"); return e
        if tok[0] == "id":
            name = tok[1]
            if name in ("true", "false"): return ("num", 1 if name == "true" else 0)
            targs = None
            if name in TEMPLATE_FUNCS and self.at("<"):
                self.take("<"); targs = []
                while True:
                    targs.append(self.parse_expr(no_gt=True))
                    if self.at(","): self.take(); continue
                    break
                self.take(">")
            if self.at("("):
                self.take("("); args = []
                if not self.at(")"):
                    while True:
                        args.append(self.parse_expr())
                        if self.at(","): self.take(); continue
                        break
                self.take(")")
                return ("call", name, targs, args)
            if targs is not None: raise SyntaxError("template without call: " + name)
            return ("id", name)
        raise SyntaxError(f"unexpected {tok}")

    # ---------------- statements ----------------
    def parse_block_items(self, end=None):
        items = []
        while self.peek()[0] != "eof" and not (end and self.at(end)):
            items.append(self.statement())
        return items

    def statement(self):
        tok = self.peek()
        if tok[1] == ";": self.take(); return ("nop",)
        if tok[1] == "{":
            self.take(); items = self.parse_block_items("}"); self.take("}"); return ("block", items)
        if tok[1] == "for":
            self.take(); self.take("(")
            if self.is_type_start(): self.parse_type()
            var = self.take()[1]; self.take("="); init = self.parse_expr(); self.take(";")
            cond = self.parse_expr(); self.take(";")
            v2 = self.take()[1]; op = self.take()[1]
            assert v2 == var and op in ("++", "--"), (v2, op)
            self.take(")"); body = self.statement()
            return ("for", var, init, cond, 1 if op == "++" else -1, body)
        if tok[1] == "if":
            self.take(); self.take("("); c = self.parse_expr(); self.take(")"); th = self.statement(); el = None
            if self.at("else"): self.take(); el = self.statement()
            return ("if", c, th, el)
        if tok[1] == "(" and self.peek(1)[1] == "void":
            while not self.at(";"): self.take()
            self.take(";"); return ("nop",)
        if self.is_type_start() and not (tok[1] in ("bool", "int") and self.peek(1)[1] == ")"):
            ty = self.parse_type(); decls = []
            while True:
                name = self.take()[1]; dims = []; init = None
                while self.at("["):
                    self.take(); dims.append(self.parse_expr()); self.take("]")
                if self.at("="):
                    self.take(); init = self.parse_expr()
                decls.append((name, dims, init))
                if self.at(","): self.take(); continue
                break
            self.take(";"); return ("decl", ty, decls)
        e = self.parse_expr()
        if self.at("="):
            self.take(); rhs = self.parse_expr(); self.take(";"); return ("assign", e, rhs)
        self.take(";"); return ("expr", e)


def parse_statements(src):
    return Parser(src).parse_block_items()


def strip_pp(src, defined):
    """resolve #if / #ifdef / #ifndef / #else / #endif with the given predicate on the condition text; drop #pragma"""
    out = []; stack = []
    for line in src.splitlines():
        s = line.strip()
        if s.startswith("#pragma"): continue
        m = re.match(r"#\s*(if|ifdef|ifndef)\s+(.*)", s)
        if m:
            kind, cond = m.group(1), m.group(2).split("//")[0].strip()
            val = defined(kind, cond)
            stack.append([val, all(x[0] for x in stack)]); continue
        if re.match(r"#\s*else", s): stack[-1][0] = not stack[-1][0]; continue
        if re.match(r"#\s*endif", s): stack.pop(); continue
        if s.startswith("#"): continue
        if all(x[0] for x in stack): out.append(line)
    return "\n".join(out)
