import ctypes, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
SEC = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0
SIZES = [int(x) for x in (sys.argv[2] if len(sys.argv) > 2 else "10,16,21").split(",")]
NAME = {1: "BLAKE3 Merkle", 3: "ChaCha20 GGM", 2: "BLAKE3 GGM", 4: "Monolith-31 Merkle"}
RAPL = "/sys/class/powercap/intel-rapl:0"
U32P = ctypes.POINTER(ctypes.c_uint32)
NUL = ctypes.cast(None, U32P)

def rapl():
    try:
        return int(open(RAPL + "/energy_uj").read())
    except OSError:
        return None

try:
    RANGE = int(open(RAPL + "/max_energy_range_uj").read())
except OSError:
    RANGE = 1 << 32
cpu = ctypes.CDLL(os.path.join(HERE, "cpu_trees.so"))
p3 = ctypes.CDLL(os.path.join(HERE, "p3mono", "target", "release", "libp3mono.so"))
cpu.cpu_tree.restype = ctypes.c_double; cpu.cpu_tree.argtypes = [ctypes.c_int] * 4 + [U32P, U32P]
cpu.cpu_init.argtypes = [ctypes.c_int]
p3.p3_mono_tree.restype = ctypes.c_double; p3.p3_mono_tree.argtypes = [ctypes.c_uint32] * 3 + [U32P, U32P]
J = json.load(open(os.path.join(HERE, "cpu_trees_linux.json")))
e0 = rapl(); t0 = time.time(); time.sleep(3.0); e1 = rapl()
idle = ((e1 - e0) % RANGE) / 1e6 / (time.time() - t0) if e0 is not None else 0.0
print("workload,leaves_log2,implementation,configuration,ns_per_node,package_w,idle_w", flush=True)
for kind in (1, 3, 2, 4):
    for L in SIZES:
        cand = [r for r in J["rows"] if r["kind"] == kind and r["L"] == L]
        if not cand:
            continue
        r = min(cand, key=lambda x: x["best_ns"]); T = r["best_threads"]; nodes = (1 << L) - 1
        reps = max(2, int(2e9 / (r["best_ns"] * nodes)))
        if r["impl"] in ("p3", "p3p"):
            cpu.cpu_stop(); call = lambda: p3.p3_mono_tree(L, reps, T, NUL, NUL)
        else:
            cpu.cpu_init(T); impl = int(r["impl"]); call = lambda: cpu.cpu_tree(kind, impl, L, reps, NUL, NUL)
        call(); e0 = rapl(); t0 = time.time(); ns = []
        while time.time() - t0 < SEC:
            ns.append(call())
        t1 = time.time(); e1 = rapl()
        w = ((e1 - e0) % RANGE) / 1e6 / (t1 - t0) if e0 is not None else 0.0
        cpu.cpu_stop()
        print("%s,%d,%s,one tree at a time on %d threads,%.3f,%.1f,%.1f" % (NAME[kind], L, r["name"].replace(",", ";"), T, min(min(ns), r["best_ns"]), w, idle), flush=True)
