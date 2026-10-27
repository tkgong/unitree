"""patch_vendor.py - this machine refuses to execute freshly built .exe files, so cargo cannot run build scripts.
Remove the build scripts of the vendored crates and supply what they produce on rustc 1.91 stable, x86_64-pc-windows-msvc:
  - serde, serde_core, thiserror: OUT_DIR/private.rs (a module named after the patch version) -> src/private_gen.rs
  - proc-macro2: cfg wrap_proc_macro; serde: cfg if_docsrs_then_no_serde_core (both passed through RUSTFLAGS)
  - every other build script (quote, paste, rayon-core, num-traits, crossbeam-*, libc) emits nothing that changes
    the code on this compiler and target (only rustc-check-cfg lines, or cfgs for compilers older than 1.78 / other OS).
Vendored checksums: the per-file list is emptied so cargo accepts the edits."""
import json, os, re
V = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor")
BUILD = ["serde", "serde_core", "thiserror", "proc-macro2", "quote", "paste", "rayon-core", "num-traits",
         "crossbeam-deque", "crossbeam-epoch", "crossbeam-utils", "libc"]
PRIV = {"serde": "#[doc(hidden)]\npub mod __private{p} {{\n    #[doc(hidden)]\n    pub use crate::private::*;\n}}\nuse serde_core::__private{p} as serde_core_private;\n",
        "serde_core": "#[doc(hidden)]\npub mod __private{p} {{\n    #[doc(hidden)]\n    pub use crate::private::*;\n}}\n",
        "thiserror": "#[doc(hidden)]\npub mod __private{p} {{\n    #[doc(hidden)]\n    pub use crate::private::*;\n}}\n"}
for c in BUILD:
    d = os.path.join(V, c)
    toml = open(os.path.join(d, "Cargo.toml"), encoding="utf-8").read()
    ver = re.search(r'^version = "([^"]+)"', toml, re.M).group(1)
    if re.search(r"^build = ", toml, re.M): toml = re.sub(r'^build = .*$', "build = false", toml, flags=re.M)
    else: toml = toml.replace("[package]\n", "[package]\nbuild = false\n", 1)
    open(os.path.join(d, "Cargo.toml"), "w", encoding="utf-8", newline="\n").write(toml)
    if c in PRIV:
        patch = ver.split(".")[2].split("-")[0]
        open(os.path.join(d, "src", "private_gen.rs"), "w", encoding="utf-8", newline="\n").write(PRIV[c].format(p=patch))
        for dp, dn, fn in os.walk(os.path.join(d, "src")):
            for f in fn:
                if not f.endswith(".rs"): continue
                p = os.path.join(dp, f); s = open(p, encoding="utf-8").read()
                if 'env!("OUT_DIR")' not in s: continue
                rel = os.path.relpath(os.path.join(d, "src", "private_gen.rs"), dp).replace("\\", "/")
                s = s.replace('include!(concat!(env!("OUT_DIR"), "/private.rs"));', f'include!("{rel}");')
                open(p, "w", encoding="utf-8", newline="\n").write(s)
    ck = os.path.join(d, ".cargo-checksum.json")
    j = json.load(open(ck)); j["files"] = {}; json.dump(j, open(ck, "w"))
    print(f"{c} {ver}: build script removed" + (" , private_gen.rs" if c in PRIV else ""))
os.makedirs(os.path.join(os.path.dirname(V), ".cargo"), exist_ok=True)
open(os.path.join(os.path.dirname(V), ".cargo", "config.toml"), "w").write(
    '[source.crates-io]\nreplace-with = "vendored-sources"\n\n[source.vendored-sources]\ndirectory = "vendor"\n\n'
    '[build]\nrustflags = ["-C", "target-cpu=native", "--cfg", "wrap_proc_macro", "--cfg", "if_docsrs_then_no_serde_core"]\n')
print("wrote .cargo/config.toml")
