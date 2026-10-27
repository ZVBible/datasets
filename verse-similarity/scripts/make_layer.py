#!/usr/bin/env python3
"""Build the supplemental "NCD parallels" reference layer from high-sim-pairs.

Keeps an unordered verse pair when
  * symmetric gzip NCD <= --max-ncd (default 0.35; TSK share of pairs falls
    off sharply above ~0.375, see README.md),
  * both verses have >= --minlen words (default 8; removes "Then the LORD said
    to Moses," and list fragments),
  * they are not within 2 verses of each other in the same chapter,
  * each verse has <= --max-degree such pairs (default 5; drops boilerplate
    formulas like "the word of the LORD came to me, saying" that match
    hundreds of verses).

Writes OUTDIR/bsb-ncd-parallels.tsv.gz, OUTDIR/bsb-ncd-parallels.json in the
JSON map shape {fromVid: [[toVid, score]]} (score = round(100*(1-ncd)),
both directions) and OUTDIR/layer-stats.json.

Usage: python3 make_layer.py RUNDIR OUTDIR
"""
import argparse, collections, csv, gzip, json, pathlib

ap = argparse.ArgumentParser()
ap.add_argument('run'); ap.add_argument('outdir')
ap.add_argument('--max-ncd', type=float, default=0.35)
ap.add_argument('--minlen', type=int, default=8)
ap.add_argument('--max-degree', type=int, default=5)
a = ap.parse_args()
RUN = pathlib.Path(a.run); OUT = pathlib.Path(a.outdir); OUT.mkdir(parents=True, exist_ok=True)
vid = {v['ref']: v['vid'] for v in json.loads((RUN / 'verses.json').read_text())['verses']}
rows = list(csv.DictReader(gzip.open(RUN / 'out' / 'high-sim-pairs.tsv.gz', 'rt'), delimiter='\t'))
sel = [r for r in rows if float(r['ncd_sym']) <= a.max_ncd and min(int(r['words_a']), int(r['words_b'])) >= a.minlen and r['adjacent'] == '0']
deg = collections.Counter()
for r in sel: deg[r['ref_a']] += 1; deg[r['ref_b']] += 1
layer = [r for r in sel if deg[r['ref_a']] <= a.max_degree and deg[r['ref_b']] <= a.max_degree]
book = lambda ref: ref.rsplit(' ', 1)[0]
with gzip.open(OUT / 'bsb-ncd-parallels.tsv.gz', 'wt', compresslevel=9) as f:
    f.write('vid_a\tref_a\tvid_b\tref_b\tncd\ttsk_votes\n')
    for r in layer:
        f.write(f"{vid[r['ref_a']]}\t{r['ref_a']}\t{vid[r['ref_b']]}\t{r['ref_b']}\t{r['ncd_sym']}\t{r['in_tsk_votes']}\n")
shape = collections.defaultdict(list)
for r in layer:
    s = round(100 * (1 - float(r['ncd_sym'])))
    shape[str(vid[r['ref_a']])].append([vid[r['ref_b']], s]); shape[str(vid[r['ref_b']])].append([vid[r['ref_a']], s])
for k in shape: shape[k].sort(key=lambda x: -x[1])
(OUT / 'bsb-ncd-parallels.json').write_text(json.dumps(dict(sorted(shape.items(), key=lambda kv: int(kv[0]))), separators=(',', ':')))
in_tsk = sum(r['in_tsk_votes'] != '0' for r in layer)
stats = {'params': vars(a) | {'run': None, 'outdir': None}, 'candidate_pairs': len(sel), 'pairs': len(layer),
         'in_tsk': in_tsk, 'in_tsk_frac': round(in_tsk / max(1, len(layer)), 4), 'not_in_tsk': len(layer) - in_tsk,
         'cross_book': sum(book(r['ref_a']) != book(r['ref_b']) for r in layer),
         'not_in_tsk_cross_book': sum(book(r['ref_a']) != book(r['ref_b']) and r['in_tsk_votes'] == '0' for r in layer),
         'verses_covered': len(shape)}
(OUT / 'layer-stats.json').write_text(json.dumps(stats, indent=1))
print(json.dumps(stats, indent=1))
