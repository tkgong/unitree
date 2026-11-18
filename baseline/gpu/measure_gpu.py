import ctypes, json, os, random, subprocess, sys, threading, time
HERE = os.path.dirname(os.path.abspath(__file__))
LEAVES = int(sys.argv[1]) if len(sys.argv) > 1 else 24
SEC = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
SIZES = [int(x) for x in (sys.argv[3] if len(sys.argv) > 3 else "10,16,21").split(",")]
NAME = {1: "BLAKE3 Merkle", 3: "ChaCha20 GGM", 2: "BLAKE3 GGM", 4: "Monolith-31 Merkle"}
PROG = {1: (4, "zeknox tree builder"), 4: (4, "zeknox tree builder"), 3: (3, "GPU-DPF hybrid"), 2: (3, "GPU-DPF hybrid")}
g = ctypes.CDLL(os.path.join(HERE, "gpu_trees2.so"))
U32P = ctypes.POINTER(ctypes.c_uint32)
g.gpu_init.argtypes = [ctypes.c_char_p, ctypes.c_char_p]; g.gpu_name.restype = ctypes.c_char_p
g.tree2_run.argtypes = [ctypes.c_int] * 5 + [U32P, U32P]
g.tree2_bench.restype = ctypes.c_double; g.tree2_bench.argtypes = [ctypes.c_int] * 6 + [ctypes.POINTER(ctypes.c_double)]
MRC = json.load(open(os.path.join(HERE, "..", "..", "design", "model", "mono_constants.json")))
assert g.gpu_init(bytes(256), b"".join(v.to_bytes(4, "little") for row in MRC for v in row)) == 0

class GpuPower:
    def __init__(self):
        self.s = []
        self.p = subprocess.Popen(["nvidia-smi", "--query-gpu=power.draw.instant", "--format=csv,noheader,nounits", "-lms", "20"], stdout=subprocess.PIPE, text=True)
        threading.Thread(target=self.rd, daemon=True).start()

    def rd(self):
        for line in self.p.stdout:
            try:
                self.s.append((time.time(), float(line.strip())))
            except ValueError:
                pass

    def mean(self, t0, t1):
        v = [w for t, w in self.s if t0 <= t <= t1]
        return sum(v) / len(v) if v else 0.0

def check(kind, L, T, F):
    rng = random.Random(1000 * kind + L)
    if kind in (1, 4):
        words = T * (8 << L); blk = min(words, 1 << 16)
        b = bytes((ctypes.c_uint32 * blk)(*[rng.randrange(1 << 31) for _ in range(blk)]))
        inp = (ctypes.c_uint32 * words).from_buffer_copy(b * (words // blk)); n_out = 8 * T
    else:
        inp = (ctypes.c_uint32 * (8 * T))(*[rng.randrange(1 << 31) for _ in range(8 * T)]); n_out = T * (8 << L)
    ref = (ctypes.c_uint32 * n_out)(); r = (ctypes.c_uint32 * n_out)()
    if g.tree2_run(kind, 1, 1, L, T, inp, ref) != 0 or g.tree2_run(kind, 1, F, L, T, inp, r) != 0:
        return "FAIL"
    return "OK" if bytes(r) == bytes(ref) else "FAIL"

gp = GpuPower(); time.sleep(1.0)
print("workload,leaves_log2,trees_per_program,program,check,ns_per_node,board_w,idle_w", flush=True)
for kind in (1, 3, 2, 4):
    for L in SIZES:
        T = max(1, 1 << (LEAVES - L)); nodes = T * ((1 << L) - 1); F, pname = PROG[kind]
        ck = check(kind, L, T, F)
        ns = min(g.tree2_bench(kind, 1, F, L, T, 5, None) for _ in range(3))
        if ns <= 0:
            continue
        reps = max(1, int(0.3 / (ns * nodes * 1e-9)))
        time.sleep(2.0); t0 = time.time(); time.sleep(3.0); idle = gp.mean(t0, time.time())
        g.tree2_bench(kind, 1, F, L, T, reps, None)
        t0 = time.time()
        while time.time() - t0 < SEC:
            g.tree2_bench(kind, 1, F, L, T, reps, None)
        w = gp.mean(t0, time.time())
        print("%s,%d,%d,%s,%s,%.3f,%.1f,%.1f" % (NAME[kind], L, T, pname, ck, ns, w, idle), flush=True)
gp.p.terminate()
