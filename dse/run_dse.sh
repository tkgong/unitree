#!/bin/sh
# run_dse.sh [component-dir ...]   (default: every dir under dse/E*/ holding an hls_config.cfg)
# Runs Vitis C synthesis for each component. Work dirs go on the local disk:
# builds on D: are slower and the generated binaries are blocked there.
ROOT=$(cd "$(dirname "$0")" && pwd)
WORKROOT=/c/temp/claude/D--unitree/dea63833-fad7-46bd-9e00-2f0958ed2049/dse_work
VPP="C:/Xilinx/Vitis/2025.2/Vitis/bin/v++.bat"
mkdir -p "$WORKROOT"
list="$*"
[ -z "$list" ] && list=$(find "$ROOT" -mindepth 2 -name hls_config.cfg -exec dirname {} \; | sort)
for d in $list; do
  d=${d%/}
  name=$(echo "$d" | sed "s|^$ROOT/||; s|/|_|g")
  w="$WORKROOT/$name"
  mkdir -p "$w"
  printf '=== %-28s ' "$name"
  if (cd "$d" && "$VPP" -c --mode hls --config hls_config.cfg --work_dir "$(cygpath -w "$w")" \
        > "$w/build.log" 2>&1); then
    echo "OK"
  else
    echo "FAILED (see $w/build.log)"
    grep -m3 -E "^ERROR" "$w/build.log" | sed 's/^/      /'
  fi
done
echo "work dirs under $WORKROOT"
