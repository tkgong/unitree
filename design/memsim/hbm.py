import ctypes, os

HERE = os.path.dirname(os.path.abspath(__file__))
TX = 32
ROW = 1024
_lib = None

def lib():
    global _lib
    if _lib is None:
        path = os.environ.get("UNITREE_RAMSIM", os.path.join(HERE, "ramsim", "libramulator.so"))
        _lib = ctypes.CDLL(path)
        _lib.hbm_new.restype = ctypes.c_void_p; _lib.hbm_new.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        _lib.hbm_send.restype = ctypes.c_int; _lib.hbm_send.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_int, ctypes.c_uint64]
        _lib.hbm_tick.restype = ctypes.c_int; _lib.hbm_tick.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint64), ctypes.c_int]
        _lib.hbm_cmd.restype = ctypes.c_uint64; _lib.hbm_cmd.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        _lib.hbm_level.restype = ctypes.c_int; _lib.hbm_level.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        _lib.hbm_tck_ns.restype = ctypes.c_double; _lib.hbm_tck_ns.argtypes = [ctypes.c_void_p]
        _lib.hbm_free.restype = None; _lib.hbm_free.argtypes = [ctypes.c_void_p]
    return _lib

def model_timing(yaml_path, impl, nbl):
    import re
    blk = re.search(r"^    timing:\n((?:      .*\n?)+)", open(yaml_path).read(), re.M).group(1)
    ent = dict(re.findall(r"^\s+(\w+):\s*(\S+)", blk, re.M))
    tm = {}
    if "preset" in ent:
        src = open(os.path.join(HERE, "ramsim", "src", "dram", "impl", impl + ".cpp")).read()
        src = src[src.index("timing_presets"):]
        names = re.search(r"//\s*name\s+(.*)", src).group(1).split()
        vals = re.search(r'\{"%s",\s*\{([^}]*)\}' % ent.pop("preset"), src).group(1).split(",")
        tm = {n: int(v) for n, v in zip(names, vals)}
    tm.update({k: int(v) for k, v in ent.items()})
    tm["nBL"] = nbl
    return tm

class HBM:
    CMDS = ("ACT", "PRE", "PREA", "RD", "WR", "RDA", "WRA", "REFab", "REFsb")
    IMPL = "HBM2"
    RATIO = 1, 1
    RTW = 2
    SUSTAINED = 0.748

    def __init__(s, channels=8, mapper="RoBaRaCoCh", nbl=2, yaml=None, extra=()):
        L = lib()
        ov = [f"MemorySystem.DRAM.org.channel={channels}", f"MemorySystem.AddrMapper.impl={mapper}", f"MemorySystem.DRAM.timing.nBL={nbl}", *extra]
        s.h = L.hbm_new((yaml or os.path.join(HERE, "hbm2.yaml")).encode(), "\n".join(ov).encode())
        s.L, s.channels, s.mapper, s.nbl = L, channels, mapper, nbl
        s.peak = TX * channels
        s.tck = L.hbm_tck_ns(s.h)
        s._buf = (ctypes.c_uint64 * 65536)()
        s.clk = 0
        s.tm = tm = model_timing(yaml or os.path.join(HERE, "hbm2.yaml"), s.IMPL, nbl)
        ck = lambda n: -(-n * s.RATIO[1] // s.RATIO[0])
        s.rt_cycles = ck(tm["nRCDRD"] + tm["nCL"] + tm["nBL"])
        import re
        src = os.path.join(HERE, "ramsim", "src")
        low = float(re.search(r'"wr_low_watermark"\).*?default_val\(([0-9.]+)f\)', open(os.path.join(src, "dram_controller", "impl", "generic_dram_controller.cpp")).read()).group(1))
        qsz = int(re.search(r"max_size\s*=\s*(\d+)", open(os.path.join(src, "base", "request.h")).read()).group(1))
        s.wdrain_cycles = ck(int(-(-(1 - low) * qsz // 1)) * tm["nCCDL"])
        s.turn_cycles = ck(tm["nCL"] + s.RTW + tm["nWTRS"])

    def send(s, addr, write, tag=0):
        return s.L.hbm_send(s.h, addr, 1 if write else 0, tag) == 1

    def tick(s):
        n = s.L.hbm_tick(s.h, s._buf, 65536); s.clk += 1
        return s._buf[:n]

    def mem_clocks(s):
        return s.clk

    def cmd(s, name):
        return s.L.hbm_cmd(s.h, name.encode())

    def stats(s):
        c = {k: s.cmd(k) for k in s.CMDS}
        col = c["RD"] + c["WR"] + c["RDA"] + c["WRA"]
        c["col"] = col
        c["row_hit"] = 1 - c["ACT"] / col if col else 0.0
        c["B_per_act"] = TX * col / c["ACT"] if c["ACT"] else 0.0
        return c

    def describe(s):
        return (f"Ramulator2 HBM2 (UniZK RamSim): {s.channels} channel(s) x 128 bit at 2 Gb/s, tCK {s.tck:g} ns, {TX} B per access, "
                f"nBL {s.nbl}, 1 KB rows, FR-FCFS, all-bank refresh, {s.mapper}; peak {s.peak} B/cycle")

class GDDR6(HBM):
    RATIO = 7, 4
    IMPL = "GDDR6"
    RTW = 4
    SUSTAINED = 0.786

    def __init__(s, channels=16, mapper="RoBaRaCoCh", nbl=2, extra=()):
        rows = 65536 // channels
        HBM.__init__(s, channels, mapper, nbl, yaml=os.path.join(HERE, "gddr6.yaml"), extra=(f"MemorySystem.DRAM.org.row={rows}", *extra))
        s.peak = 16 * s.RATIO[0] / s.RATIO[1] * channels
        s.acc = 0

    def tick(s):
        s.acc += s.RATIO[0]
        out = []
        while s.acc >= s.RATIO[1]:
            s.acc -= s.RATIO[1]
            n = s.L.hbm_tick(s.h, s._buf, 65536); s.clk += 1
            out.extend(s._buf[:n])
        return out

    def describe(s):
        return (f"Ramulator2 GDDR6 (the RTX 3070's memory: 16 channels x 16 bit at 14 Gb/s = 448 GB/s): {s.channels} channel(s) "
                f"= {28 * s.channels} GB/s, CK 1.75 GHz (tCK {s.tck:g} ns, 7 memory clocks per 4 unit cycles), {TX} B per access "
                f"(BL16, nBL {s.nbl}), 2 KB rows, FR-FCFS, all-bank refresh, {s.mapper}; peak {s.peak:g} B/cycle")

def batch(addrs, channels=8, mapper="RoBaRaCoCh", write=False, port=None, max_cycles=10_000_000, nbl=2, kind="hbm"):
    m = GDDR6(channels, mapper, nbl) if kind == "gddr" else HBM(channels, mapper, nbl); port = port or channels
    wr = write if isinstance(write, (list, tuple)) else [write] * len(addrs)
    i, t, out, sent = 0, 0, 0, {}
    lat = []
    while (i < len(addrs) or sent) and t < max_cycles:
        n = 0
        while i < len(addrs) and n < port and m.send(addrs[i], wr[i], i):
            if not wr[i]: sent[i] = t
            i += 1; n += 1
        for tag in m.tick():
            if tag in sent: lat.append(t + 1 - sent.pop(tag))
        t += 1
    return t, m.stats(), lat
