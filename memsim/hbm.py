"""hbm.py - Ramulator2 HBM2 (UniZK's RamSim, memsim/ramsim) as a cycle-level memory for the unit's Python simulators.

    from hbm import HBM
    m = HBM(channels=8)                 # one HBM2 stack, memsim/hbm2.yaml
    ok = m.send(addr, write, tag)       # one 32 B access; False = the channel's controller queue is full (retry later)
    done = m.tick()                     # one memory clock (= one unit cycle at 1 GHz); tags of the reads completed in it
    m.cmd("ACT"), m.stats()             # DRAM commands issued so far

Built on Linux by memsim/build_linux.sh (libramulator.so next to memsim/ramsim/CMakeLists.txt). UNITREE_RAMSIM overrides
the library path."""
import ctypes, os

HERE = os.path.dirname(os.path.abspath(__file__))
TX = 32                                          # bytes per RD / WR (hbm2.yaml: channel_width 128, prefetch 2)
ROW = 1024                                       # bytes per row (32 columns x 32 B)
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


class HBM:
    CMDS = ("ACT", "PRE", "PREA", "RD", "WR", "RDA", "WRA", "REFab", "REFsb")

    def __init__(s, channels=8, mapper="RoBaRaCoCh", nbl=2, yaml=None, extra=()):
        L = lib()                                    # nbl=2: JEDEC HBM2 burst (hbm2.yaml); nbl=4: the Ramulator2 preset
        ov = [f"MemorySystem.DRAM.org.channel={channels}", f"MemorySystem.AddrMapper.impl={mapper}", f"MemorySystem.DRAM.timing.nBL={nbl}", *extra]
        s.h = L.hbm_new((yaml or os.path.join(HERE, "hbm2.yaml")).encode(), "\n".join(ov).encode())
        s.L, s.channels, s.mapper, s.nbl = L, channels, mapper, nbl
        s.peak = TX * channels                       # B per cycle
        s.tck = L.hbm_tck_ns(s.h)
        s._buf = (ctypes.c_uint64 * 65536)()
        s.clk = 0

    def send(s, addr, write, tag=0):
        return s.L.hbm_send(s.h, addr, 1 if write else 0, tag) == 1

    def tick(s):
        n = s.L.hbm_tick(s.h, s._buf, 65536); s.clk += 1
        return s._buf[:n]

    def cmd(s, name):
        return s.L.hbm_cmd(s.h, name.encode())

    def stats(s):
        c = {k: s.cmd(k) for k in s.CMDS}
        col = c["RD"] + c["WR"] + c["RDA"] + c["WRA"]
        c["col"] = col
        c["row_hit"] = 1 - c["ACT"] / col if col else 0.0           # column accesses that found their row open
        c["B_per_act"] = TX * col / c["ACT"] if c["ACT"] else 0.0
        return c

    def describe(s):
        return (f"Ramulator2 HBM2 (UniZK RamSim): {s.channels} channel(s) x 128 bit at 2 Gb/s, tCK {s.tck:g} ns, {TX} B per access, "
                f"nBL {s.nbl}, 1 KB rows, FR-FCFS, all-bank refresh, {s.mapper}; peak {s.peak} B/cycle")


def batch(addrs, channels=8, mapper="RoBaRaCoCh", write=False, port=None, max_cycles=10_000_000, nbl=2):
    """Issue the 32 B accesses in order (as many per cycle as the controllers take, at most `port`), until all reads have
    returned -> (cycles, stats, latencies of the reads). The open phase and the microbenchmarks use it."""
    m = HBM(channels, mapper, nbl); port = port or channels
    i, t, out, sent = 0, 0, 0, {}
    lat = []
    while (i < len(addrs) or sent) and t < max_cycles:
        n = 0
        while i < len(addrs) and n < port and m.send(addrs[i], write, i):
            if not write: sent[i] = t
            i += 1; n += 1
        for tag in m.tick(): lat.append(t + 1 - sent.pop(tag))
        t += 1
    return t, m.stats(), lat
