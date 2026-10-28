"""run_energy.py - energy per tree of the CPU and GPU baselines on Linux (dana336), the four workloads of the unit at
one size: each measured as a sustained run of >= SEC seconds (the program repeated) while the power is sampled.
  GPU  gpu_trees2.so, fused+opt, 8 trees per program (the x8 throughput regime of run_gpu_trees2.py); board power from
       nvidia-smi (power.draw.instant, every 20 ms), integrated over the run; idle board power measured before
  CPU  cpu_trees.so / libp3mono.so, the best implementation and thread count of run_cpu_trees.py (cpu/cpu_trees_linux.json);
       package energy from the RAPL counter (/sys/class/powercap/intel-rapl:0/energy_uj, must be readable), idle measured before
Energy per tree = energy of the run / trees computed; "above idle" subtracts idle power x run time.
    python3 run_energy.py [log2=18] [sec=5]          -> RESULTS_ENERGY_linux.md
"""
import ctypes, json, os, subprocess, sys, threading, time
HERE = os.path.dirname(os.path.abspath(__file__))
L = int(sys.argv[1]) if len(sys.argv) > 1 else 18
SEC = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
NAME = {1: "BLAKE3 Merkle", 2: "BLAKE3-XOF GGM", 3: "ChaCha20 GGM", 4: "Monolith-31 Merkle"}
NODES = (1 << L) - 1
U32P = ctypes.POINTER(ctypes.c_uint32)
NUL = ctypes.cast(None, U32P)

class GpuPower:                                              # nvidia-smi sampler: (host time, watts)
    def __init__(self):
        self.s = []; self.p = subprocess.Popen(["nvidia-smi", "--query-gpu=power.draw.instant", "--format=csv,noheader,nounits", "-lms", "20"],
                                               stdout=subprocess.PIPE, text=True)
        threading.Thread(target=self.rd, daemon=True).start()
    def rd(self):
        for line in self.p.stdout:
            try: self.s.append((time.time(), float(line.strip())))
            except ValueError: pass
    def mean(self, t0, t1):
        v = [w for t, w in self.s if t0 <= t <= t1]
        return sum(v) / len(v), len(v)
    def stop(self): self.p.terminate()

RAPL = "/sys/class/powercap/intel-rapl:0"
def rapl():
    return int(open(f"{RAPL}/energy_uj").read())
def rapl_ok():
    try: rapl(); return True
    except OSError: return False
RANGE = int(open(f"{RAPL}/max_energy_range_uj").read()) if os.path.exists(f"{RAPL}/max_energy_range_uj") else 1 << 32
def rapl_j(e0, e1): return ((e1 - e0) % RANGE) / 1e6

def sustain(call, per_call_trees):                          # repeat call() for >= SEC s; (t0, t1, trees)
    call()                                                   # warm-up
    t0 = time.time(); n = 0
    while time.time() - t0 < SEC:
        call(); n += 1
    return t0, time.time(), n * per_call_trees

lines = []
def out(s=""):
    print(s, flush=True); lines.append(s)
cpu_name = next((l.split(":", 1)[1].strip() for l in open("/proc/cpuinfo") if l.startswith("model name")), "?")
gpu_name = subprocess.run(["nvidia-smi", "--query-gpu=name,power.limit", "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()
out(f"# Energy per tree, CPU and GPU baselines (2^{L}, {NODES:,} nodes per tree)\n")
out(f"CPU {cpu_name}, package RAPL. GPU {gpu_name}, nvidia-smi power.draw.instant every 20 ms (board power).")
out(f"Each measurement: the program repeated for >= {SEC:g} s after a warm-up; idle power measured for {SEC:g} s before the runs.\n")
rows = []

# ---------------- GPU ----------------
g = ctypes.CDLL(os.path.join(HERE, "gpu_trees2.so"))
g.gpu_init.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
g.tree2_bench.restype = ctypes.c_double; g.tree2_bench.argtypes = [ctypes.c_int] * 6 + [ctypes.POINTER(ctypes.c_double)]
MRC = json.load(open(os.path.join(HERE, "..", "dse", "TOP", "mono_constants.json")))
assert g.gpu_init(bytes(256), b"".join(v.to_bytes(4, "little") for row in MRC for v in row)) == 0
gp = GpuPower(); time.sleep(1.0)
t0 = time.time(); time.sleep(SEC); gidle, _ = gp.mean(t0, time.time())
for kind in NAME:
    pc = ctypes.c_double(0); reps = 4
    t0, t1, trees = sustain(lambda: g.tree2_bench(kind, 1, 1, L, 8, reps, ctypes.byref(pc)), 8 * reps)
    w, ns = gp.mean(t0, t1); dt = t1 - t0
    rows.append(("GPU", kind, dt / trees * 1e6, w, gidle, w * dt / trees * 1e6, (w - gidle) * dt / trees * 1e6, ns))
gp.stop()

# ---------------- CPU ----------------
if rapl_ok():
    cpu = ctypes.CDLL(os.path.join(HERE, "cpu", "cpu_trees.so"))
    p3 = ctypes.CDLL(os.path.join(HERE, "p3mono", "target", "release", "libp3mono.so"))
    cpu.cpu_tree.restype = ctypes.c_double; cpu.cpu_tree.argtypes = [ctypes.c_int] * 4 + [U32P, U32P]
    cpu.cpu_init.argtypes = [ctypes.c_int]
    p3.p3_mono_tree.restype = ctypes.c_double; p3.p3_mono_tree.argtypes = [ctypes.c_uint32] * 3 + [U32P, U32P]
    best = {}
    for r in json.load(open(os.path.join(HERE, "cpu", "cpu_trees_linux.json")))["rows"]:
        if r["L"] == L and r["kind"] in NAME and (r["kind"] not in best or r["best_ns"] < best[r["kind"]]["best_ns"]): best[r["kind"]] = r
    e0 = rapl(); t0 = time.time(); time.sleep(SEC); cidle = rapl_j(e0, rapl()) / (time.time() - t0)
    for kind in NAME:
        r = best[kind]; T = r["best_threads"]; reps = 2
        if r["impl"] == "p3":
            cpu.cpu_stop(); call = lambda: p3.p3_mono_tree(L, reps, T, NUL, NUL)
        else:
            cpu.cpu_init(T); impl = int(r["impl"]); call = lambda: cpu.cpu_tree(kind, impl, L, reps, NUL, NUL)
        call(); e0 = rapl()
        t0, t1, trees = sustain(call, reps)
        dt = t1 - t0; j = rapl_j(e0, rapl()); w = j / dt
        rows.append(("CPU", kind, dt / trees * 1e6, w, cidle, j / trees * 1e6, (w - cidle) * dt / trees * 1e6, f"{r['name']}, {T} thr"))
    cpu.cpu_stop()
else:
    out(f"CPU: {RAPL}/energy_uj is not readable (root only); CPU energy not measured.\n")

out("| platform | tree | us per tree (sustained) | power W | idle W | energy per tree uJ | above idle uJ | note |")
out("|---|---|---:|---:|---:|---:|---:|---|")
for pf, kind, us, w, idle, e, ea, note in rows:
    out(f"| {pf} | {NAME[kind]} | {us:,.1f} | {w:.1f} | {idle:.1f} | {e:,.0f} | {ea:,.0f} | {note if pf == 'CPU' else f'{note} samples'} |")
open(os.path.join(HERE, "RESULTS_ENERGY_linux.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
