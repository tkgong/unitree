import os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "model", "verify"))
from models import M32, IV, PARENT, ROOT, KEYED_HASH, CHUNK_START, CHUNK_END, compress16, b3_lanes, b3_words, cc_block, cc_lanes, cc_words
from arx_steps import traversal, schedule

split = lambda L: [(v & M32, v >> 32) for v in L]
join = lambda L: [lo | (hi << 32) for lo, hi in L]

def run(lanes, prim, cp0=0):
    x = split(lanes)
    for CP, r in schedule(prim):
        x = traversal(x, CP ^ cp0 if prim == "blake3" else CP, prim == "blake3", r)
    return join(x)

rng = random.Random(1)
bad = 0
for t in range(200):
    h = [rng.getrandbits(32) for _ in range(8)]
    m = [rng.getrandbits(32) for _ in range(16)]
    flags = rng.choice([PARENT, PARENT | ROOT, KEYED_HASH | CHUNK_START | CHUNK_END | ROOT])
    want = compress16(h, m, 0, 64, flags)
    for cp0 in (0, 1):
        got = b3_words(run(b3_lanes(h, m, 0, 64, flags, 22), "blake3", cp0))
        if got != want: bad += 1
kat = [0x61707865, 0x3320646e, 0x79622d32, 0x6b206574] + [0x03020100, 0x07060504, 0x0b0a0908, 0x0f0e0d0c, 0x13121110,
       0x17161514, 0x1b1a1918, 0x1f1e1d1c] + [1, 0x09000000, 0x4a000000, 0]
cases = [kat] + [[rng.getrandbits(32) for _ in range(16)] for _ in range(200)]
for w in cases:
    if cc_words(run(cc_lanes(w, 22), "chacha")) != cc_block(w): bad += 1
print("arx_steps:", "OK" if bad == 0 else f"{bad} mismatches", f"(400 BLAKE3 blocks on both copies, {len(cases)} ChaCha20 blocks incl. the RFC KAT)")
sys.exit(1 if bad else 0)
