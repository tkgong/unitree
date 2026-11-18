import ctypes, multiprocessing as mp, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
SIZES = [int(x) for x in (sys.argv[1] if len(sys.argv) > 1 else "10,16,21").split(",")]
RAPL = "/sys/class/powercap/intel-rapl:0/energy_uj"
U32P = ctypes.POINTER(ctypes.c_uint32)
NAME = {1: "BLAKE3 Merkle", 3: "ChaCha20 GGM", 2: "BLAKE3 GGM", 4: "Monolith-31 Merkle"}
CAND = {1: (0, "official BLAKE3 C hash_many", 16), 3: (2, "AVX2", 18), 2: (2, "AVX2", 14), 4: ("p3", "Plonky3 p3-monolith 0.8.0", 460)}

def worker(kind, impl, L, reps, bar, q):
    NUL = ctypes.cast(None, U32P)
    if impl == "p3":
        p3 = ctypes.CDLL(os.path.join(HERE, "p3mono", "target", "release", "libp3mono.so"))
        p3.p3_mono_tree.restype = ctypes.c_double; p3.p3_mono_tree.argtypes = [ctypes.c_uint32] * 3 + [U32P, U32P]
        f = lambda r: p3.p3_mono_tree(L, r, 1, NUL, NUL)
    else:
        cpu = ctypes.CDLL(os.path.join(HERE, "cpu_trees.so"))
        cpu.cpu_tree.restype = ctypes.c_double; cpu.cpu_tree.argtypes = [ctypes.c_int] * 4 + [U32P, U32P]
        cpu.cpu_init.argtypes = [ctypes.c_int]; cpu.cpu_init(1)
        f = lambda r: cpu.cpu_tree(kind, impl, L, r, NUL, NUL)
    f(1)
    bar.wait()
    q.put(f(reps))

def rapl():
    try:
        return int(open(RAPL).read())
    except OSError:
        return None

def batch(kind, impl, L, P, reps):
    bar = mp.Barrier(P + 1); q = mp.Queue()
    ps = [mp.Process(target=worker, args=(kind, impl, L, reps, bar, q)) for _ in range(P)]
    for p in ps:
        p.start()
    bar.wait()
    e0, t0 = rapl(), time.time()
    ns = [q.get() for _ in ps]
    e1, t1 = rapl(), time.time()
    for p in ps:
        p.join()
    w = (e1 - e0) / 1e6 / (t1 - t0) if e0 is not None and e1 is not None and e1 >= e0 else 0.0
    return 1.0 / sum(1.0 / v for v in ns), w

if __name__ == "__main__":
    e0, t0 = rapl(), time.time(); time.sleep(3.0); e1 = rapl()
    idle = (e1 - e0) / 1e6 / (time.time() - t0) if e0 is not None else 0.0
    P = mp.cpu_count() or 16
    print("workload,leaves_log2,implementation,configuration,ns_per_node,package_w,idle_w", flush=True)
    for kind in (1, 3, 2, 4):
        impl, nm, guess = CAND[kind]
        for L in SIZES:
            reps = max(2, round(2e9 / (guess * ((1 << L) - 1))))
            ns, w = min(batch(kind, impl, L, P, reps) for _ in range(2))
            print("%s,%d,%s,%d processes with one tree each,%.3f,%.1f,%.1f" % (NAME[kind], L, nm, P, ns, w, idle), flush=True)
