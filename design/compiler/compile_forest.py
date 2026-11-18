import concurrent.futures as cf, hashlib, heapq, math, os, random, re, subprocess, sys
CDIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(CDIR, "..", "model", "verify"))
from models import *

DLL, REQ, PRIM = os.path.abspath(sys.argv[1]), sys.argv[2], sys.argv[3]
SIZES = [int(x) for x in sys.argv[4].split(",")]
def opt(k, d): return next((a[len(k) + 1:] for a in sys.argv[5:] if a.startswith(k + "=")), d)
PES, SUB, JOBS, WORK = int(opt("pes", "8")), opt("sub", ""), int(opt("jobs", "8")), opt("work", "/tmp/forest")
PASS = [a for a in sys.argv[5:] if a.split("=")[0] not in ("pes", "sub", "jobs", "work")]
prim = {"blake3": 1, "chacha": 2, "mono": 4}[PRIM]
CC_CONST = [0x61707865, 0x3320646e, 0x79622d32, 0x6b206574]
os.makedirs(WORK, exist_ok=True)
hexl = lambda v: " ".join(f"{w:x}" for w in v) + "\n"

def merkle_fn(l, r, is_root):
    if prim == 4: return mono(l + r)[:8]
    return compress16(IV, l + r, 0, 64, PARENT | (ROOT if is_root else 0))[:8]

def ggm_fn(seed, level, idx):
    if prim == 2: o = cc_block(CC_CONST + seed + [idx & M32, (idx >> 32) & M32, level, 0])
    else: o = compress16(seed, [idx & M32, (idx >> 32) & M32, level] + [0] * 13, 0, 64, KEYED_HASH | CHUNK_START | CHUNK_END | ROOT)
    return o[:8], o[8:16]

def run(job):
    cmd = [sys.executable, os.path.join(CDIR, "compile_tree.py"), DLL, REQ, PRIM, str(job["size"])] + job["args"] + PASS
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    open(os.path.join(WORK, job["name"] + ".log"), "w").write(" ".join(cmd) + "\n" + out)
    m = re.search(r"^\s*cycles\s+([\d,]+)", out, re.M)
    assert m, f"{job['name']}: no result, see {WORK}/{job['name']}.log"
    job["cycles"] = int(m.group(1).replace(",", ""))
    job["nodes"] = int(re.search(r"nodes computed\s+([\d,]+)", out).group(1).replace(",", ""))
    job["ok"] = "vs Python reference: OK" in out and ("audit" not in PASS or len(re.findall(r"^\s*audit.*OK", out, re.M)) >= 1) and "FAIL" not in out
    s = re.search(r"leaves sha256: (\w+)", out); job["sha"] = s.group(1) if s else None
    return job

trees, jobs = [], []
for t, n in enumerate(SIZES):
    s = min(n, int(SUB)) if SUB else max(1, n - math.ceil(math.log2(PES)))
    k = n - s; T = {"t": t, "n": n, "s": s, "k": k, "bot": [], "top": None}
    rng = random.Random(1000 + t); pre = os.path.join(WORK, f"t{t}")
    if REQ == "merkle":
        T["leaves"] = [[rng.randrange(P) for _ in range(8)] if prim == 4 else [rng.getrandbits(32) for _ in range(8)] for _ in range(1 << n)]
        for j in range(1 << k):
            open(f"{pre}_leaves{j}.txt", "w").write("".join(hexl(v) for v in T["leaves"][j << s:(j + 1) << s]))
            T["bot"].append({"name": f"t{t}_sub{j}", "tree": t, "kind": 1, "idx": j, "size": s,
                             "args": [f"leaves={pre}_leaves{j}.txt", f"rootout={pre}_root{j}.txt"] + (["noroot"] if k else [])})
        if k: T["top"] = {"name": f"t{t}_top", "tree": t, "kind": 2, "idx": 0, "size": k, "args": [f"leaves={pre}_roots.txt", f"rootout={pre}_root.txt", "handin"]}
    else:
        T["seed"] = [rng.getrandbits(32) for _ in range(8)]
        open(f"{pre}_seed.txt", "w").write(hexl(T["seed"]))
        if k:
            T["top"] = {"name": f"t{t}_top", "tree": t, "kind": 0, "idx": 0, "size": k, "args": [f"seedin={pre}_seed.txt", "gbase=0:0", f"leafout={pre}_seeds.txt"]}
            for j in range(1 << k):
                T["bot"].append({"name": f"t{t}_sub{j}", "tree": t, "kind": 1, "idx": j, "size": s, "args": [f"seedin={pre}_seeds.txt", f"gbase={k}:{j}", "leafsha", "handin"]})
        else:
            T["bot"].append({"name": f"t{t}_sub0", "tree": t, "kind": 1, "idx": 0, "size": s, "args": [f"seedin={pre}_seed.txt", "gbase=0:0", "leafsha"]})
    trees.append(T)

with cf.ThreadPoolExecutor(JOBS) as ex:
    if REQ == "merkle":
        list(ex.map(run, [j for T in trees for j in T["bot"]]))
        for T in trees:
            if T["top"]:
                pre = os.path.join(WORK, f"t{T['t']}")
                open(f"{pre}_roots.txt", "w").write("".join(open(f"{pre}_root{j}.txt").read() for j in range(1 << T["k"])))
        list(ex.map(run, [T["top"] for T in trees if T["top"]]))
    else:
        list(ex.map(run, [T["top"] for T in trees if T["top"]]))
        list(ex.map(run, [j for T in trees for j in T["bot"]]))
for T in trees: jobs += ([T["top"]] if T["top"] else []) + T["bot"]

ok = all(j["ok"] for j in jobs)
for T in trees:
    n, s, k, pre = T["n"], T["s"], T["k"], os.path.join(WORK, f"t{T['t']}")
    if REQ == "merkle":
        lv = T["leaves"]
        for l in range(1, n + 1): lv = [merkle_fn(lv[2 * i], lv[2 * i + 1], l == n) for i in range(len(lv) // 2)]
        got = [int(x, 16) for x in open(f"{pre}_root.txt" if k else f"{pre}_root0.txt").read().split()]
        T["ok"] = got == lv[0]
    else:
        fr = [T["seed"]]
        for l in range(k): fr = [c for i, sd in enumerate(fr) for c in ggm_fn(sd, l, i)]
        T["ok"] = True
        for j, sd in enumerate(fr):
            sub = [sd]
            for l in range(s): sub = [c for i, x in enumerate(sub) for c in ggm_fn(x, k + l, (j << l) + i)]
            T["ok"] &= hashlib.sha256(b"".join(w.to_bytes(4, "little") for v in sub for w in v)).hexdigest() == T["bot"][j]["sha"]
    ok &= T["ok"]

done_at = {}
def ready_at(j):
    T = trees[j["tree"]]
    if REQ == "merkle": deps = T["bot"] if j["kind"] == 2 else []
    else: deps = [T["top"]] if j["kind"] == 1 and T["top"] else []
    if any(d["name"] not in done_at for d in deps): return None
    return max([done_at[d["name"]] for d in deps], default=0)
pend = sorted(jobs, key=lambda j: (j["tree"], j["kind"], j["idx"]))
free = [(0, p) for p in range(PES)]; heapq.heapify(free)
running, sched = [], []
while pend:
    tm, pe = heapq.heappop(free)
    while True:
        while running and running[0][0] <= tm: e, nm = heapq.heappop(running); done_at[nm] = e
        rs = [(r, j) for j in pend if (r := ready_at(j)) is not None]
        cand = [j for r, j in rs if r <= tm]
        if cand: break
        tm = min([r for r, j in rs] + ([running[0][0]] if running else []))
    j = cand[0]; pend.remove(j)
    j["pe"], j["start"], j["end"] = pe, tm, tm + j["cycles"]
    heapq.heappush(running, (j["end"], j["name"])); heapq.heappush(free, (j["end"], pe)); sched.append(j)
span = max(j["end"] for j in jobs); nodes = sum(j["nodes"] for j in jobs); busy = sum(j["cycles"] for j in jobs)

print(f"forest: {len(trees)} x {PRIM} {REQ} " + ", ".join(f"2^{T['n']} (subtrees 2^{T['s']}: {len(T['bot'])} bottom" + (" + 1 top" if T["top"] else "") + ")" for T in trees)
      + f" on {PES} PEs; per PE: {' '.join(PASS) or 'no memory model'}")
print("| tree | program | PE | start | end | cycles | nodes | check |")
print("|---|---|---:|---:|---:|---:|---:|---|")
for j in sorted(sched, key=lambda j: (j["start"], j["pe"])):
    print(f"| {j['tree']} | {'top' if j['kind'] != 1 else 'subtree ' + str(j['idx'])} ({REQ} 2^{j['size']}) | {j['pe']} | {j['start']:,} | {j['end']:,} | {j['cycles']:,} | {j['nodes']:,} | {'OK' if j['ok'] else 'FAIL'} |")
for T in trees:
    fin = max(j["end"] for j in ([T["top"]] if T["top"] else []) + T["bot"])
    print(f"  tree {T['t']} (2^{T['n']}): finished at cycle {fin:,}; whole-tree reference: {'OK' if T['ok'] else 'FAIL'}")
print(f"  makespan {span:,} cycles for {nodes:,} nodes = {nodes / span:.3f} nodes/cycle ({1000 * span / nodes / 1000:.4f} cycles per node); "
      f"PE utilization {100 * busy / (PES * span):.1f}% ({busy:,} busy PE-cycles of {PES * span:,})")
print(f"  check: every program vs the Python reference and the composition vs the whole-tree reference: {'OK' if ok else 'FAIL'}")
