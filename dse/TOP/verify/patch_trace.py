"""patch_trace.py - add trace=<file> to compile_tree.py: per cycle the controls, the lanes the program writes fresh, the
lanes it copies from the previous output (recirculation / span passing), and at every node finish the expected values of
the lanes the result is read from (the DLL's output; ARX exact, Monolith mod p). The RTL testbench (RTL/unit18/verify)
replays the program closed-loop: the copies come from the RTL's own previous output.
    python patch_trace.py          (idempotent)"""
import os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "compile_tree.py")
s = open(p, encoding="utf-8").read()
if "TRACE_F" in s:
    print("already patched"); raise SystemExit
def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (s.count(a), a[:80]); s = s.replace(a, b)
NL = chr(10)
rep('''OPENONLY = MEMSIM and "openonly" in sys.argv[5:]
''', '''OPENONLY = MEMSIM and "openonly" in sys.argv[5:]
TRACE_F = next((a[6:] for a in sys.argv[5:] if a.startswith("trace=")), "")    # closed-loop trace for the RTL testbench
TRF = open(TRACE_F, "w") if TRACE_F else None
if TRF: TRF.write(f"H {NIO} {NG}" + chr(10))
tr_cp, tr_fr, tr_ck = [], [], []
def T_CP(dlo, n, slo):
    if TRF: tr_cp.append((dlo, n, slo))
def T_FR(lo, vals):
    if TRF: tr_fr.append((lo, list(vals)))
def T_CK(lo, n, mode):
    if TRF: tr_ck.append((lo, n, mode, [prev[lo + i] for i in range(n)]))
''')
rep('''                s["r"] += 1; mono_now[d] = 1; r[d] = s["r"]; lanes[B:B + 8] = prev[B:B + 8]''',
    '''                s["r"] += 1; mono_now[d] = 1; r[d] = s["r"]; lanes[B:B + 8] = prev[B:B + 8]; T_CP(B, 8, B)''')
rep('''                finish(s["node"], out_words(prev[B:B + 8], 4)); mem_writes += 1''',
    '''                T_CK(B, 8, 1); finish(s["node"], out_words(prev[B:B + 8], 4)); mem_writes += 1''')
rep('''            body, _ = node_in(nd); lanes[B:B + len(body)] = body; mono_now[d] = 1; r[d] = 0''',
    '''            body, _ = node_in(nd); lanes[B:B + len(body)] = body; mono_now[d] = 1; r[d] = 0; T_FR(B, body)''')
rep('''                lanes[lo:hi] = prev[S_["llo"]:S_["lhi"]]              # the last span's output re-enters span 0''',
    '''                lanes[lo:hi] = prev[S_["llo"]:S_["lhi"]]; T_CP(lo, hi - lo, S_["llo"])   # the last span's output re-enters span 0''')
rep('''                    jb = S_["lblocks"][b]; finish(nd, out_words(prev[BB[jb]:BB[jb] + 18], nd.prim)); mem_writes += 1''',
    '''                    jb = S_["lblocks"][b]; T_CK(BB[jb], 18, 0); finish(nd, out_words(prev[BB[jb]:BB[jb] + 18], nd.prim)); mem_writes += 1''')
rep('''                lanes[BB[bi]:BB[bi] + len(body)] = body
                if h is not None and not (bi < COLOC): lanes[HB[bi]:HB[bi] + 4] = h''',
    '''                lanes[BB[bi]:BB[bi] + len(body)] = body; T_FR(BB[bi], body)
                if h is not None and not (bi < COLOC): lanes[HB[bi]:HB[bi] + 4] = h; T_FR(HB[bi], h)''')
rep('''            lanes[GLO[gi]:GHI[gi]] = prev[GLO[gp]:GHI[gp]]; rg[gi] = RV(sp["r"])''',
    '''            lanes[GLO[gi]:GHI[gi]] = prev[GLO[gp]:GHI[gp]]; T_CP(GLO[gi], GHI[gi] - GLO[gi], GLO[gp]); rg[gi] = RV(sp["r"])''')
rep('''        if not any(mono_now): lanes[BASE:BASE + 8] = prev[BASE:BASE + 8]; htap = 1''',
    '''        if not any(mono_now): lanes[BASE:BASE + 8] = prev[BASE:BASE + 8]; T_CP(BASE, 8, BASE); htap = 1''')
rep('''                    if h is not None: lanes[BASE + 4 * b:BASE + 4 * b + 4] = h''',
    '''                    if h is not None: lanes[BASE + 4 * b:BASE + 4 * b + 4] = h; T_FR(BASE + 4 * b, h)''')
rep('''    o = ARR()
    if NENG: stepe(''', '''    if TRF:
        rgv = 0
        for g in range(NG): rgv |= (rg[g] & 511) << (9 * g)
        TRF.write(f"T {mono_now[0]} {mono_now[1] if NDP == 2 else 0} {htap} {BLAKE} {r[0]} {r[1] if NDP == 2 else 0} {rgv:x}" + chr(10))
        for lo, n, mode, vals in tr_ck: TRF.write(f"E {lo} {n} {mode} " + " ".join(f"{v:x}" for v in vals) + chr(10))
        for lo, vals in tr_fr: TRF.write(f"F {lo} " + " ".join(f"{v:x}" for v in vals) + chr(10))
        for dlo, n, slo in tr_cp: TRF.write(f"P {dlo} {n} {slo}" + chr(10))
        tr_cp.clear(); tr_fr.clear(); tr_ck.clear()
    o = ARR()
    if NENG: stepe(''')
rep('''print(f"  instruction stream  {cycles:,} words''', '''if TRF: TRF.write("Z" + chr(10)); TRF.close(); print(f"  trace               {TRACE_F}: {cycles:,} cycles")
print(f"  instruction stream  {cycles:,} words''')
open(p, "w", encoding="utf-8", newline="").write(s)
print("patched")
