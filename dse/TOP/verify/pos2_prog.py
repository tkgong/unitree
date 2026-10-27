"""pos2_prog.py - the Poseidon2-M31 permutation as the unit's issue program (software precompilation, no hardware mode).
One permutation = 67 issues on one Monolith/Poseidon2 datapath; every issue is one of the datapath's fixed traversals:
    SQ    products P_k = B[k] * C[k] land in Y_{k+1} (brk = 0), read at the Y tap after SQD levels
    INIT  Y = A (brk = 1, no products), M_E + row-0 constants, read at the E tap
    X5E r Y_{k+1} = B[k] * C[k] (the x^5 step of an external round), M_E + constant row r, E tap
    X5I r Y_0 = B[15] * C[15], Y_k = A[k] (brk = 1): the internal S-box merged into the state, M_I + row r, I tap
The lane sets of an issue: A = state lanes BASE..BASE+7, B = BASE+8.., C = BASE+16.. (16 words each, two per lane);
taps: Y = out[BASE+8..], E = out[BASE+16..], I = out[BASE+24..]. The Monolith issues of the same datapath use
A = B = x, C = x with word 15 = 0 (so that Y_0 = x_0): mono_issue_lanes()."""
from models import P, pk, mono_lanes, mono_words

def words(lanes8): return [v % P for k in range(8) for v in (lanes8[k] & 0xFFFFFFFF, lanes8[k] >> 32)]
def lanes(w16): return [pk(w16[2 * k], w16[2 * k + 1]) for k in range(8)]
def mono_issue_lanes(x):
    """A = B = x, C = x with x_15 = 0 -> 24 lanes (the Monolith round on the Poseidon2-capable datapath)"""
    return mono_lanes(x) + mono_lanes(x) + mono_lanes(x[:15] + [0])
STEPS = ([("INIT", 0)] + [s for e in range(4) for s in (("SQ", None), ("SQ", None), ("X5E", e + 1))]
         + [s for i in range(14) for s in (("SQI", None), ("SQI", None), ("X5I", i))]
         + [s for e in range(4) for s in (("SQ", None), ("SQ", None), ("X5E", 5 + e))])
assert len(STEPS) == 67


class P2Prog:
    """One permutation. codes: dict with R_SQ, R_INIT, R_X5E, R_X5I (the r values), SQD, LE, LI (tap levels)."""
    def __init__(self, x, codes):
        self.s = list(x); self.t = None; self.u = None; self.i = 0; self.c = codes; self.steps = STEPS
    def done(self): return self.i >= len(self.steps)
    def step(self): return self.steps[self.i]
    def issue(self):
        """-> (r, 24 lanes, exit level, tap offset 8 / 16 / 24) of the next issue"""
        kind, row = self.steps[self.i]; c = self.c; z = [0] * 16; s = self.s
        if kind == "INIT": return c["R_INIT"], lanes(s[-1:] + s[:-1]) + lanes(z) + lanes(z), c["LE"], 16   # M_E input i = Y_{i+1}: A[k] = s_{k-1}
        if kind == "SQ":
            v = s if self.t is None else self.t
            return c["R_SQ"], lanes(z) + lanes(v) + lanes(v), c["SQD"], 8
        if kind == "X5E": return c["R_X5E"] + row - 1, lanes(z) + lanes(self.u) + lanes(s), c["LE"], 16
        if kind == "SQI":
            v = s[0] if self.t is None else self.t
            b = z[:15] + [v]
            return c["R_SQ"], lanes(z) + lanes(b) + lanes(b), c["SQD"], 8
        if kind == "X5I": return c["R_X5I"] + row, lanes([0] + s[1:]) + lanes(z[:15] + [self.u]) + lanes(z[:15] + [s[0]]), c["LI"], 24
        raise ValueError(kind)
    def take(self, tap16):
        """the tap words of the issue just completed"""
        kind, row = self.steps[self.i]
        if kind == "SQ":
            v = tap16[1:] + tap16[:1]                              # Y_{k+1} holds element k
            if self.t is None: self.t = v
            else: self.u = v; self.t = None
        elif kind == "SQI":
            if self.t is None: self.t = tap16[0]
            else: self.u = tap16[0]; self.t = None
        else:
            self.s = list(tap16); self.t = self.u = None
        self.i += 1
    def expected_tap(self):
        """the tap words the model predicts for the pending issue (debug aid)"""
        kind, row = self.steps[self.i]; s = self.s
        if kind == "SQ":
            v = s if self.t is None else self.t
            sq = [x * x % P for x in v]; return sq[-1:] + sq[:-1]
        if kind == "SQI":
            v = s[0] if self.t is None else self.t
            return [v * v % P] + [0] * 15
        from models import p2_ext, p2_int, P2E_ROWS, P2I_ROWS
        if kind == "INIT": y = p2_ext(s); return [(a + b) % P for a, b in zip(y, P2E_ROWS[0])]
        if kind == "X5E": y = p2_ext([a * b % P for a, b in zip(self.u, s)]); return [(a + b) % P for a, b in zip(y, P2E_ROWS[row])]
        y = p2_int([self.u * s[0] % P] + s[1:]); return [(a + b) % P for a, b in zip(y, P2I_ROWS[row])]


# ---- internal S-boxes packed across programs (software only): the scheduler issues three pack traversals for up to 16
# programs at the same internal round (slot k = program k: x0^2, x0^4, x0^4 * x0 on multiplier k), then every program
# runs its own M_I issue with x0^5 placed in A[0] (brk = 1, no products) ----
STEPS_P = ([("INIT", 0)] + [s for e in range(4) for s in (("SQ", None), ("SQ", None), ("X5E", e + 1))]
           + [s for i in range(14) for s in (("PK", 1), ("PK", 2), ("PK", 3), ("X5I2", i))]
           + [s for e in range(4) for s in (("SQ", None), ("SQ", None), ("X5E", 5 + e))])


class P2ProgPacked(P2Prog):
    def __init__(self, x, codes):
        P2Prog.__init__(self, x, codes); self.steps = STEPS_P
    def step(self): return self.steps[self.i]
    def issue(self):
        kind, row = self.steps[self.i]; c = self.c; z = [0] * 16; s = self.s
        if kind == "X5I2": return c["R_X5I"] + row, lanes([self.u] + s[1:]) + lanes(z) + lanes(z), c["LI"], 24
        assert kind != "PK"
        return P2Prog.issue(self)
    def pack_ops(self):
        """(B word, C word) of this program's slot in the next pack issue"""
        stage = self.steps[self.i][1]; s0 = self.s[0]
        return (s0, s0) if stage == 1 else (self.t, self.t) if stage == 2 else (self.u, s0)
    def expected_pack(self):
        b, cc = self.pack_ops(); return b * cc % P
    def take_pack(self, word):
        stage = self.steps[self.i][1]
        if stage == 1: self.t = word
        elif stage == 2: self.u = word
        else: self.u = word; self.t = None                    # x0^5
        self.i += 1
    def take(self, tap16):
        kind, row = self.steps[self.i]
        if kind == "X5I2": self.s = list(tap16); self.t = self.u = None; self.i += 1
        else: P2Prog.take(self, tap16)
    def expected_tap(self):
        kind, row = self.steps[self.i]
        if kind == "X5I2":
            from models import p2_int, P2I_ROWS
            y = p2_int([self.u] + self.s[1:]); return [(a + b) % P for a, b in zip(y, P2I_ROWS[row])]
        return P2Prog.expected_tap(self)


# ---- three multiplier ranks (MONO_P2_MUL3): one issue per round, 23 per permutation ----
STEPS_M = [("INIT", 0)] + [("X5E", e + 1) for e in range(4)] + [("X5I", i) for i in range(14)] + [("X5E", 5 + e) for e in range(4)]


class P2ProgMul3(P2Prog):
    def __init__(self, x, codes):
        P2Prog.__init__(self, x, codes); self.steps = STEPS_M
    def issue(self):
        kind, row = self.steps[self.i]; c = self.c; z = [0] * 16; s = self.s
        if kind == "INIT": return c["R_INIT"], lanes(s) + lanes(z) + lanes(z), c["LE"], 16          # M_E of the state (ini)
        if kind == "X5E": return c["R_X5E"] + row - 1, lanes(z) + lanes(s) + lanes(s), c["LE"], 16   # x^5 of all 16 on the chain, M_E
        return c["R_X5I"] + row, lanes([0] + s[1:]) + lanes(z[:15] + [s[0]]) + lanes(z[:15] + [s[0]]), c["LI"], 24   # slot 15: x0^5; M_I
    def take(self, tap16): self.s = list(tap16); self.i += 1
    def expected_tap(self):
        from models import p2_ext, p2_int, p2_sbox, P2E_ROWS, P2I_ROWS
        kind, row = self.steps[self.i]; s = self.s
        if kind == "INIT": y = p2_ext(s); return [(a + b) % P for a, b in zip(y, P2E_ROWS[0])]
        if kind == "X5E": y = p2_ext([p2_sbox(v) for v in s]); return [(a + b) % P for a, b in zip(y, P2E_ROWS[row])]
        y = p2_int([p2_sbox(s[0])] + s[1:]); return [(a + b) % P for a, b in zip(y, P2I_ROWS[row])]


class P2ProgMul3A1(P2ProgMul3):
    """MONO_P2_A1: no operand lanes; every issue delivers the state in the A lanes (the chain squares A, the internal
    S-box runs on slot 0, M_E reads A on the initial layer); B / C lanes stay zero (ignored by the hardware)"""
    def issue(self):
        kind, row = self.steps[self.i]; c = self.c; z = [0] * 16; s = self.s
        if kind == "INIT": return c["R_INIT"], lanes(s) + lanes(z) + lanes(z), c["LE"], 16
        if kind == "X5E": return c["R_X5E"] + row - 1, lanes(s) + lanes(z) + lanes(z), c["LE"], 16
        return c["R_X5I"] + row, lanes(s) + lanes(z) + lanes(z), c["LI"], 24


class P2ProgEng(P2ProgMul3A1):
    """the 14 internal rounds on an internal-round engine (p2_engine.h): the datapath runs INIT and the 8 external
    rounds (9 issues), the engine one internal round per issue (state in its 8 lanes, round index er = row)"""
    def on_engine(self): return self.steps[self.i][0] == "X5I"
    def eng_issue(self):
        kind, row = self.steps[self.i]; assert kind == "X5I"
        return row, lanes(self.s)
