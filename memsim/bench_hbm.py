"""bench_hbm.py - calibrate the Ramulator2 HBM2 model (memsim/hbm2.yaml) against the ideal bw= pipe of compile_tree.py:
achieved B/cycle vs the peak (32 B per channel per cycle) for the access patterns the tree programs produce.
    python3 bench_hbm.py [channels ...] [--md out.md]"""
import random, sys
from hbm import batch, HBM, TX

args = [a for a in sys.argv[1:] if not a.startswith("--")]
out = sys.argv[sys.argv.index("--md") + 1] if "--md" in sys.argv else ""
if out in args: args.remove(out)
CHS = [int(a) for a in args] or [1, 2, 4, 8]
N = 1 << 15                                                  # accesses per pattern (1 MB)
rnd = random.Random(1)
PATS = {
    "sequential read": (lambda: [i * TX for i in range(N)], False),
    "sequential write": (lambda: [i * TX for i in range(N)], True),
    "random 32 B read (256 MB)": (lambda: [rnd.randrange(1 << 23) * TX for _ in range(N)], False),
    "random 1 KB-row read, whole row": (lambda: [r * 1024 + c * TX for r in (rnd.randrange(1 << 18) for _ in range(N // 32)) for c in range(32)], False),
}
L = ["| pattern | channels | peak B/cycle | cycles | achieved B/cycle | of peak | row hit | B per ACT | read latency avg / max (cycles) |",
     "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
for name, (gen, wr) in PATS.items():
    for ch in CHS:
        addrs = gen()
        cyc, st, lat = batch(addrs, channels=ch, write=wr)
        bpc = len(addrs) * TX / cyc
        la = f"{sum(lat) / len(lat):.1f} / {max(lat)}" if lat else "- (writes complete at acceptance)"
        L.append(f"| {name} | {ch} | {TX * ch} | {cyc:,} | {bpc:.1f} | {100 * bpc / (TX * ch):.0f}% | {100 * st['row_hit']:.1f}% | {st['B_per_act']:,.0f} | {la} |")
        print(L[-1], flush=True)
m = HBM(1)
txt = m.describe() + "\n\n" + "\n".join(L)
print(txt)
if out: open(out, "w").write(txt + "\n")
