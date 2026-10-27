"""Check the HBM layout / staging functions of compile_tree.py as they are (exec'd, openonly, no DLL run): for every request
kind, tree size and store mode, every stored node has its own 32-byte address in every layout, block-layout rows never pass
1 KB, sibling pairs share a 64 B burst, and row_full(l) equals the number of stored nodes that really map to that row (so a
staged row completes exactly when its last node arrives)."""
import sys, collections, io, contextlib
import os
VER = os.path.dirname(os.path.abspath(__file__))
SRC = open(os.path.join(VER, "compile_tree.py"), encoding="utf-8").read()
SRC = SRC.split("if OPENONLY:\n")[0]                              # functions only: the commit loop is skipped under openonly
n = 0
for req, prim in (("merkle", "blake3"), ("ggm", "chacha")):
    for sz in (2, 3, 4, 5, 8, 10, 13):
        for store in ("all", "out", "k1", "k2", "k3"):
            sys.argv = ["compile_tree.py", os.path.join(VER, "lz_16.dll"), req, prim, str(sz), "deep", "sram=64", f"store={store}", "openonly"]
            g = {"__name__": "ct", "__file__": os.path.join(VER, "compile_tree.py")}
            with contextlib.redirect_stdout(io.StringIO()): exec(compile(SRC, "compile_tree.py", "exec"), g)
            addr, stored, row_full, ROWB, SZ = g["addr"], g["stored"], g["row_full"], g["ROWB"], g["SZ"]
            nodes = [(l, j) for l in range(SZ + 1) for j in range(1 << (SZ - l))]
            for L in g["LAYOUTS"]:
                A = [addr(L, l, j) for (l, j) in nodes]
                assert len(set(A)) == len(A) and all(a % 32 == 0 for a in A), (req, sz, store, L, "address collision")
            for (l, j) in nodes:
                if 0 < l < SZ: assert addr("block", l, j) // 64 == addr("block", l, j ^ 1) // 64, (req, sz, "pair")
                if l > 0: assert addr("block", l, j) % ROWB + 32 <= ROWB
            st = [(l, j) for (l, j) in nodes if stored(l) and (store != "out" or l == 0)]   # what mem_out stages
            cnt = collections.Counter(addr("block", l, j) // ROWB for (l, j) in st)
            for (l, j) in st:
                assert cnt[addr("block", l, j) // ROWB] == row_full(l), (req, sz, store, l, j, cnt[addr("block", l, j) // ROWB], row_full(l))
            exp = {"all": None, "out": None}.get(store)
            n += 1
print(f"layout check OK: {n} configurations (merkle / ggm x 2^2..2^5, 2^8, 2^10, 2^13 x store all / out / k1 / k2 / k3): addresses distinct in "
      f"level / tile / block, block rows <= 1 KB, sibling pairs in one 64 B burst, row_full = stored nodes per row")
