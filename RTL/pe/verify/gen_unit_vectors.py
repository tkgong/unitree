#!/usr/bin/env python3
"""Reference vectors for unit_bz3.sv from the HLS C++ itself: dse/TOP/verify/lz3_16.dll (lane_pipe of dse/TOP/bz3/pipe_axn.h,
one call = one clock). Random issue controls and lanes every cycle (mono, mono2, htap, blake bits; r, r2 and the 28 group round
indices over 0..511, so every decode, feed-forward, diagonal and last-round path is taken), from the all-zero reset state.
    python gen_unit_vectors.py [cycles] [seed]      -> vec/ctrl.hex, vec/lin.hex, vec/lout.hex"""
import ctypes, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
DLL = os.path.normpath(os.path.join(HERE, "..", "..", "..", "dse", "TOP", "verify", "lz3_16.dll"))
N = int(sys.argv[1]) if len(sys.argv) > 1 else 300
rnd = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 20261027)
L = ctypes.CDLL(DLL)
NIO = L.lp_info(9); NG = L.lp_info(14)
U64 = ctypes.c_ulonglong * NIO; I32 = ctypes.c_int * NG
L.lp_step_x.argtypes = [ctypes.c_int] * 6 + [ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_ulonglong), ctypes.POINTER(ctypes.c_ulonglong)]
os.makedirs(os.path.join(HERE, "vec"), exist_ok=True)
fc = open(os.path.join(HERE, "vec", "ctrl.hex"), "w"); fi = open(os.path.join(HERE, "vec", "lin.hex"), "w"); fo = open(os.path.join(HERE, "vec", "lout.hex"), "w")
nz = 0
for t in range(N):
    mono, mono2, htap, blake = (rnd.getrandbits(1) for _ in range(4))
    r, r2 = rnd.randrange(512), rnd.randrange(512)
    rg = [rnd.randrange(512) for _ in range(NG)]
    # a quarter of the cycles use the round indices a real program issues (0..13, the last one with bit 8)
    if t % 4 == 0:
        r, r2 = rnd.randrange(7), rnd.randrange(7)
        rg = [rnd.choice([rnd.randrange(14), 13 | 256]) for _ in range(NG)]
    lin = U64(*(rnd.getrandbits(64) for _ in range(NIO))); out = U64()
    L.lp_step_x(mono, mono2, htap, blake, r, r2, I32(*rg), lin, out)
    word = 0
    for g in reversed(range(NG)): word = (word << 9) | rg[g]
    word = (((((word << 9 | r2) << 9 | r) << 1 | blake) << 1 | htap) << 1 | mono2) << 1 | mono
    fc.write(f"{word:x}\n")
    fi.write("".join(f"{lin[i]:016x}\n" for i in range(NIO)))
    fo.write("".join(f"{out[i]:016x}\n" for i in range(NIO)))
    nz += sum(1 for i in range(NIO) if out[i])
print(f"{N} cycles x {NIO} lanes, {NG} groups; nonzero expected output lanes: {nz:,} of {N * NIO:,}")
