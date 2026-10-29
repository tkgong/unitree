"""sweep.py - the memory-model workloads of dse/TOP/README.md (64 KB SRAM) on the ideal bw= pipe and on the Ramulator2 HBM2
(compile_tree.py hbm=<channels>), at the same peak bandwidth, every run with audit and the bit-exact check.
    python3 memsim/sweep.py [jobs]           (Linux, after memsim/build_linux.sh; default 14 parallel runs)
Logs: memsim/results/logs/*.log; table: memsim/results/sweep.md."""
import os, re, subprocess, sys
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__)); TOP = os.path.join(HERE, "..", "dse", "TOP")
LOGS = os.path.join(HERE, "results", "logs"); os.makedirs(LOGS, exist_ok=True)
CT = os.path.join(HERE, "..", "RTL", "compiler", "compile_tree.py")   # the tree compiler
DLL = "verify/lz_16.so"                                     # bz: four primitives (the unit of the README memory-model runs)

WL = {   # workload -> (compile_tree arguments, README bw, channel counts compared)
    "BLAKE3 Merkle 2^18, store=all": ("merkle blake3 18 sram=64 store=all", 172, (4, 8)),
    "ChaCha20 GGM 2^18, store=all": ("ggm chacha 18 sram=64 store=all", 172, (4, 8)),
    "BLAKE3 GGM 2^18, store=all": ("ggm blake3 18 sram=64 store=all", 172, (4, 8)),
    "BLAKE3 Merkle 2^18, store=out": ("merkle blake3 18 sram=64 store=out", 86, (2, 4)),
    "Monolith Merkle 2^16, store=all": ("merkle mono 16 sram=64 store=all", 32, (1, 2)),
    "Poseidon2 Merkle 2^16, store=all": ("merkle pos2 16 sram=64 store=all", 16, (1,)),
}
JOBS = []
for w, (a, bw, chs) in WL.items():
    JOBS.append((w, f"ideal {bw} B/cycle (README)", bw, f"{a} bw={bw} audit"))
    for ch in chs:
        JOBS.append((w, f"ideal {32 * ch} B/cycle", 32 * ch, f"{a} bw={32 * ch} audit"))
        JOBS.append((w, f"HBM2 {ch} ch, RoBaRaCoCh", 32 * ch, f"{a} hbm={ch} audit"))
        JOBS.append((w, f"HBM2 {ch} ch, MOP4CLXOR", 32 * ch, f"{a} hbm={ch} hmap=MOP4CLXOR audit"))
    ch = chs[-1]
    JOBS.append((w, f"HBM2 {ch} ch, RoBaRaCoCh, Ramulator preset nBL 4 (UniZK)", 32 * ch, f"{a} hbm={ch} hnbl=4 audit"))
OPENS = [("BLAKE3 Merkle 2^22 open", "merkle blake3 22 sram=64 store=all openonly open=1,64,1024"),
         ("ChaCha20 GGM 2^22 open", "ggm chacha 22 sram=64 store=all openonly open=1,64,1024")]
for w, a in OPENS:
    for mp in ("RoBaRaCoCh", "MOP4CLXOR"):
        JOBS.append((w, f"HBM2 8 ch, {mp}", 256, f"{a} hbm=8 hmap={mp}"))


def name(j): return re.sub(r"[^A-Za-z0-9]+", "_", f"{j[0]}__{j[1]}").strip("_")


def run(j):
    log = os.path.join(LOGS, name(j) + ".log")
    if os.path.exists(log) and "check:" in open(log).read() or os.path.exists(log) and "openonly" in j[3] and "HBM2 8 ch" in open(log).read():
        return log
    with open(log, "w") as f:
        f.write(f"# python3 ../../RTL/compiler/compile_tree.py {DLL} {j[3]}\n"); f.flush()
        subprocess.run([sys.executable, CT, DLL] + j[3].split(), cwd=TOP, stdout=f, stderr=subprocess.STDOUT)
    return log


def grab(txt, pat, g=1, conv=str):
    m = re.search(pat, txt)
    return conv(m.group(g).replace(",", "")) if m else None


def summarize():
    L = ["| workload | memory | peak B/cycle | cycles | vs ideal at the same peak | achieved B/cycle | row hit | B per ACT | read latency avg / max | SRAM high-water KB | audit, check |",
         "|---|---|---:|---:|---:|---:|---:|---:|---|---:|---|"]
    ideal = {}
    rows = []
    for j in JOBS:
        if "openonly" in j[3]: continue
        t = open(os.path.join(LOGS, name(j) + ".log")).read()
        cyc = grab(t, r"cycles\s+([\d,]+)", conv=int)
        if j[1].startswith("ideal") and "README" not in j[1]: ideal[(j[0], j[2])] = cyc
        rows.append((j, t, cyc))
    for j, t, cyc in rows:
        base = ideal.get((j[0], j[2]))
        vs = f"{100 * (cyc / base - 1):+.1f}%" if (cyc and base and not j[1].startswith("ideal")) else ""
        bpc = grab(t, r"= ([\d.,]+) B/cycle average")
        hit = grab(t, r"row hit ([\d.]+)%"); bpa = grab(t, r"([\d,]+) B per activation;")
        lat = re.search(r"read latency ([\d.]+) cycles average, (\d+) max", t)
        hw = grab(t, r"SRAM high-water\s+[\d,]+ x 32 B = ([\d.,]+) KB")
        ok = ("audit OK" if re.search(r"^  audit\s+OK", t, re.M) else "AUDIT ?") + ", " + ("check OK" if "reference: OK" in t else "CHECK FAIL")
        L.append(f"| {j[0]} | {j[1]} | {j[2]} | {cyc:,} | {vs} | {bpc or ''} | {hit + '%' if hit else ''} | {bpa or ''} | "
                 f"{lat.group(1) + ' / ' + lat.group(2) if lat else ''} | {hw or ''} | {ok} |" if cyc else f"| {j[0]} | {j[1]} | {j[2]} | FAILED (see log) | | | | | | | |")
    O = ["", "Open batches (openonly, 2^22, q = 1 / 64 / 1024), each layout's reads in address order on the HBM2 model:", ""]
    for j in JOBS:
        if "openonly" not in j[3]: continue
        t = open(os.path.join(LOGS, name(j) + ".log")).read()
        O.append(f"{j[0]}, {j[1]}:")
        O += ["    " + l.strip() for l in t.splitlines() if re.match(r"\s+\d+\s+[\d,]+\s+[\d.]+", l) or "HBM2 8 ch:" in l]
    txt = "\n".join(L + O)
    open(os.path.join(HERE, "results", "sweep.md"), "w").write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    with Pool(n) as p:
        for log in p.imap_unordered(run, sorted(JOBS, key=lambda j: ("2^16" in j[0], "openonly" in j[3]))):
            print("done", os.path.basename(log), flush=True)
    summarize()
