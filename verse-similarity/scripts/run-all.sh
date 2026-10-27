#!/usr/bin/env bash
# Full BSB all-pairs gzip NCD pipeline (resumable via RUNDIR/done.u8).
# Needs: gcc + zlib headers, python3 + numpy, ~4 GB free disk for RUNDIR,
#        a BSB JSON at RUNDIR/bsb-full.json, and either RUNDIR/tsk-edges.tsv
#        or RUNDIR/cross_references.txt (OpenBible.info dump).
#
# Usage: ./run-all.sh [RUNDIR] [TSKFILE]
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$(cd "$HERE/.." && pwd)"
RUN="${1:-$OUT/workdir}"
mkdir -p "$RUN" "$OUT"
cd "$HERE"
[ -f "$RUN/bsb-full.json" ] || { echo "Missing $RUN/bsb-full.json (BSB verse JSON)"; exit 1; }
TSK="${2:-$RUN/tsk-edges.tsv}"
if [ ! -f "$TSK" ]; then
  [ -f "$RUN/cross_references.txt" ] || { echo "Missing TSK edges or cross_references.txt"; exit 1; }
  node build-tsk-edges.mjs "$RUN" "$RUN/cross_references.txt"
  TSK="$RUN/tsk-edges.tsv"
fi
python3 prepare_texts.py "$RUN" "$RUN/bsb-full.json"
gcc -O3 -march=native -pthread -Wall ncd_matrix.c -lz -o "$RUN/ncd_matrix"
"$RUN/ncd_matrix" "$RUN/texts.txt" "$RUN" "$(nproc)"
python3 symmetrize.py "$RUN"
python3 analyze.py "$RUN" "$TSK" --workers "$(nproc)"
python3 export_topk.py "$RUN" "$TSK" "$OUT"
python3 make_layer.py "$RUN" "$OUT"
cp "$RUN/out/evaluation.json" "$OUT/evaluation.json"
cp "$RUN/out/high-sim-pairs.tsv.gz" "$OUT/high-sim-pairs.tsv.gz"
echo "Outputs written under $OUT"
