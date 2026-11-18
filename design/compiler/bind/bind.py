import collections, sys
from cells import arx_cells, mono_regs

PE_BLOCKS = 54

def arx_graph(U, CP=0):
    per = {prim: arx_cells(prim, CP) for prim in ("chacha", "blake3")}
    nb = PE_BLOCKS // (6 * U)
    G = {}
    for s in range(1, 6 * U + 1):
        st = (s - 1) % 6 + 1
        for b in range(nb):
            for l in range(22):
                for h in range(2):
                    sets = set()
                    for prim in per:
                        for src, _ in per[prim][st][(l, h)]:
                            sets.add(frozenset((s - 1, b, sl, sh) for sl, sh in src))
                    G[(s, b, l, h)] = sets
    return G, nb

def bind(U, verbose=True):
    G, nb = arx_graph(U)
    R = mono_regs()
    levels = 6 * U
    phi, used, used_in = {}, set(), set()
    inputs = [(0, b, l, h) for b in range(nb) for l in range(22) for h in range(2)]
    by_src = collections.defaultdict(list)
    for y, sets in G.items():
        for S in sets: by_src[(y[0], S)].append(y)
    shared_bits = collections.Counter(); total_bits = collections.Counter(); why = collections.Counter()
    for L in range(1, 19):
        for x in sorted((k for k in R if R[k][0] == L), key=lambda k: -R[k][1]):
            _, w, src = R[x]
            total_bits[L] += w
            if L > levels: why["deeper than the ARX pipeline"] += w; continue
            if w > 32: why["wider than a 32-bit word"] += w; continue
            if any(s != "in" and s not in phi for s in src): why["a source is not shared"] += w; continue
            cand = []
            if src == ("in",):
                for y in (y for y in G if y[0] == 1 and y not in used):
                    for S in G[y]:
                        if len(S) == 1 and next(iter(S)) not in used_in: cand.append((y, S)); break
            else:
                S = frozenset(phi[s] for s in src)
                cand = [(y, S) for y in by_src.get((L, S), []) if y not in used]
            if not cand: why["no ARX word reads the same sources"] += w; continue
            y, S = cand[0]
            phi[x] = y; used.add(y); shared_bits[L] += w
            if src == ("in",): used_in.add(next(iter(S)))
    tot, sh = sum(total_bits.values()), sum(shared_bits.values())
    arx_bits = len(G) * 32
    if verbose:
        print(f"U = {U}: ARX {levels} levels x {nb} blocks = {arx_bits:,} register bits; Monolith {tot:,} bits, "
              f"shared with only the op changed {sh:,} ({100 * sh / tot:.1f}%)")
        print("   shared per level:", [shared_bits[L] for L in range(1, 19)])
        for k, v in why.most_common(): print(f"   not shared: {k:40s} {v:6,} bits")
    return sh, tot

if __name__ == "__main__":
    for U in [int(a) for a in sys.argv[1:]] or [1, 3]:
        bind(U)
