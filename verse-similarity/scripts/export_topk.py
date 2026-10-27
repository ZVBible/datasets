#!/usr/bin/env python3
"""Export per-verse NCD nearest neighbours as JSONL.gz for the repo.

One line per verse:
  {"vid": 1001001, "ref": "Genesis 1:1", "words": 10,
   "n": [[vid, ncd, tskVotes], ...]}      # nearest first; tskVotes 0 = not in TSK
Variant sym: raw symmetric NCD (both concatenation orders, min). Variant csls:
same NCD, re-ranked with the hubness correction (score column = raw NCD).

Usage: python3 export_topk.py RUNDIR TSKFILE OUTDIR [--k 20]
"""
import argparse, gzip, json, pathlib
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('run'); ap.add_argument('tsk'); ap.add_argument('outdir')
ap.add_argument('--k', type=int, default=20)
a = ap.parse_args()
RUN = pathlib.Path(a.run); OUT = pathlib.Path(a.outdir); OUT.mkdir(parents=True, exist_ok=True)
V = json.loads((RUN / 'verses.json').read_text())['verses']
N = len(V)
C = np.fromfile(RUN / 'clen.u16', dtype='<u2').astype(np.float32)
z = dict(np.load(RUN / 'out' / 'topk.npz'))  # materialise once; npz members re-decompress on every access
vid = z['vid']
p = pathlib.Path(a.tsk)
T = {}
if p.suffix == '.json':
    for f, lst in json.loads(p.read_text()).items():
        for t, v in lst:
            f = int(f); T[(f, t)] = max(T.get((f, t), 0), v); T[(t, f)] = max(T.get((t, f), 0), v)
else:
    for line in p.read_text().splitlines():
        f, t, v = map(int, line.split('\t')); T[(f, t)] = max(T.get((f, t), 0), v); T[(t, f)] = max(T.get((t, f), 0), v)
S = np.memmap(RUN / 'sym.u16', dtype='<u2', mode='r', shape=(N, N))

for var in ('sym', 'csls'):
    path = OUT / f'bsb-ncd-{var}-top{a.k}.jsonl.gz'
    with gzip.open(path, 'wt', compresslevel=9) as f:
        for i, v in enumerate(V):
            js = z[var][i, :a.k].astype(np.int64)
            row = np.asarray(S[i, js], dtype=np.float32)  # one fancy-indexed read per row
            d = (row - np.minimum(C[i], C[js])) / np.maximum(C[i], C[js])
            nb = [[int(vid[j]), round(float(x), 4), T.get((int(vid[i]), int(vid[j])), 0)] for j, x in zip(js, d)]
            f.write(json.dumps({'vid': int(v['vid']), 'ref': v['ref'], 'words': len(v['norm'].split()), 'n': nb}, separators=(',', ':')) + '\n')
    print(path, path.stat().st_size)
