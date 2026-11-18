import collections, sys
from cells import arx_cells, mono_regs

def top_op(key):
    op = key[0]
    if op == "reg": return "move"
    if op.startswith("rotl"): return top_op(key[1])
    return op

def arx_ops(CP):
    per = {p: arx_cells(p, CP) for p in ("chacha", "blake3")}
    count = collections.Counter()
    for s in range(1, 7):
        for w in per["chacha"][s]:
            ops = frozenset(top_op(k) for p in per for _, k in per[p][s][w])
            ops = ops - {"move"} or ops
            count[ops] += 9
    return count

def mono_ops():
    R = mono_regs()
    count = collections.Counter()
    for k, (L, w, src) in R.items():
        nw = -(-w // 32)
        if k.startswith("xb1."): op = "sbox" if int(k.split(".")[1]) < 8 else "move"
        elif k.startswith(("xb2", "xb3")) or ".d" in k: op = "move"
        elif k.startswith("sq"): op = "mul"
        elif k.startswith(("br", "rq", "of")): op = "add"
        else: op = "add"
        count[frozenset([op])] += nw
    return count

if __name__ == "__main__":
    for CP in (0, 1):
        A, M = arx_ops(CP), mono_ops()
        print(f"PE {CP} (block copy {CP}), 32-bit registers by atomic op:")
        keys = sorted(set(A) | set(M), key=lambda k: sorted(k))
        tot_sep = tot_sh = 0
        for k in keys:
            a, m = A.get(k, 0), M.get(k, 0)
            tot_sep += a + m; tot_sh += max(a, m)
            print(f"   {'+'.join(sorted(k)):10s} ARX {a:5d}   Monolith {m:5d}   separate {a + m:5d}   shared {max(a, m):5d}")
        print(f"   total               separate {tot_sep:5d}   shared {tot_sh:5d}  ({100 * (tot_sep - tot_sh) / tot_sep:.1f}% fewer)")
