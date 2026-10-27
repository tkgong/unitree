"""gen_vectors.py - random test vectors for pe_core (RTL/fsm) from the Python reference models (dse/TOP/verify/models.py).
    python gen_vectors.py <NB> <runs>        -> vec/{cc,b3,mono}_{in,out}.hex (one 32-bit word per line)
ChaCha20: 16 input words per block -> cc_block. BLAKE3: random h, m, counter, block_len, flags -> compress16; the block's
in_v is the initial state h | IV[0..3] | counter | block_len | flags, in_m the message, in_h = h. Monolith: 16 canonical
elements -> mono."""
import os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "dse", "TOP", "verify"))
from models import cc_block, compress16, mono, IV, P, M32

NB, NT = int(sys.argv[1]), int(sys.argv[2])
rnd = random.Random(2026)
os.makedirs(os.path.join(HERE, "vec"), exist_ok=True)
def w(name, words): open(os.path.join(HERE, "vec", name), "w").write("".join(f"{x & M32:08x}\n" for x in words))
cc_in, cc_out, b3_v, b3_m, b3_h, b3_out, mo_in, mo_out = [], [], [], [], [], [], [], []
for t in range(NT):
    for b in range(NB):
        x = [rnd.getrandbits(32) for _ in range(16)]
        cc_in += x; cc_out += cc_block(x)
        h = [rnd.getrandbits(32) for _ in range(8)]; m = [rnd.getrandbits(32) for _ in range(16)]
        counter = rnd.getrandbits(64); block_len = rnd.randrange(65); flags = rnd.getrandbits(6)
        b3_v += h + IV[:4] + [counter & M32, (counter >> 32) & M32, block_len, flags]; b3_m += m; b3_h += h
        b3_out += compress16(h, m, counter, block_len, flags)
    x = [rnd.randrange(P) for _ in range(16)]
    mo_in += x; mo_out += mono(x)
w("cc_in.hex", cc_in); w("cc_out.hex", cc_out); w("b3_v.hex", b3_v); w("b3_m.hex", b3_m); w("b3_h.hex", b3_h); w("b3_out.hex", b3_out)
w("mono_in.hex", mo_in); w("mono_out.hex", mo_out)
print(f"vectors: NB {NB}, {NT} runs per primitive")
