import glob, re, sys
O = sys.argv[1]
E_SRAM = 8.365e-3 / 100e6 * 1.21
P_LEAK = 4 * 0.0684e-3 * 1.1
E_DRAM_BIT = 7.5e-12
UNITS = 8
W = (("BLAKE3 Merkle", "merkle_blake3", 3.0521, False), ("ChaCha20 GGM", "ggm_chacha", 2.7692, True),
     ("BLAKE3 GGM", "ggm_blake3", 2.7620, True), ("Monolith-31 Merkle", "merkle_mono", 3.2384, False))
num = lambda s: int(s.replace(",", ""))

def acc(path, ggm):
    t = open(path).read()
    m = re.search(r"memory traffic\s+([\d,]+) reads, ([\d,]+) writes", t)
    g = re.search(r"RD\s+([\d,]+)\s+WR\s+([\d,]+)", t)
    n = num(re.search(r"nodes computed\s+([\d,]+)", t).group(1))
    c = num(re.search(r"^\s*cycles\s+([\d,]+)", t, re.M).group(1))
    a, b = (num(m.group(1)), num(m.group(2))) if m else (0, 0)
    rd, wr = (num(g.group(1)), num(g.group(2))) if g else (0, 0)
    return c, n, a + b + rd + wr + (n if ggm else 0), rd + wr

print("workload,leaves_log2,program,units,trees,nodes,cycles,ns_per_node,unit_nj_per_node,sram_nj_per_node,dram_nj_per_node,nj_per_node")
for name, key, pw, ggm in W:
    for L in (10, 16, 21):
        b = "%s/batch_%s_%d.log" % (O, key, L); f = "%s/forest_%s_%d.md" % (O, key, L)
        if glob.glob(b):
            cyc, n, sa, da = acc(b, ggm)
            trees = n // ((1 << L) - 1)
            t = cyc * 1e-9; ns = cyc / (n * float(UNITS)); core = pw * t / n; sr = (sa * E_SRAM + P_LEAK * t) / n; dr = da * 256 * E_DRAM_BIT / n
            prog = "%d trees in one program of a unit" % trees; trees *= UNITS; n *= UNITS
        elif glob.glob(f):
            cyc = num(re.search(r"makespan ([\d,]+) cycles for ([\d,]+) nodes", open(f).read()).group(1))
            n = sa = da = 0
            for g in glob.glob("%s/forest_%s_%d/*.log" % (O, key, L)):
                c_, n_, s_, d_ = acc(g, ggm); n += n_; sa += s_; da += d_
            t = cyc * 1e-9; ns = cyc / float(n); core = UNITS * pw * t / n; sr = (sa * E_SRAM + UNITS * P_LEAK * t) / n; dr = da * 256 * E_DRAM_BIT / n
            prog = "one tree on %d units" % UNITS; trees = 1
        else:
            continue
        print("%s,%d,%s,%d,%d,%d,%d,%.4f,%.2f,%.2f,%.2f,%.2f" % (name, L, prog, UNITS, trees, n, cyc, ns, core * 1e9, sr * 1e9, dr * 1e9, (core + sr + dr) * 1e9))
