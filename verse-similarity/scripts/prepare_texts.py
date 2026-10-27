#!/usr/bin/env python3
"""Normalize BSB verses for NCD scoring.

Reads a BSB JSON file with shape {"source","fetchedAt","verses":[{vid,ref,text},...]}
and writes OUTDIR/texts.txt (one normalized verse per line) and OUTDIR/verses.json.

Normalization: lowercase, every char outside [a-z0-9\\s] becomes a space,
whitespace collapsed, trimmed. (So "LORD" -> "lord", "God's" -> "god s".)

Usage: python3 prepare_texts.py OUTDIR [bsb-full.json]
"""
import json, re, sys, pathlib

here = pathlib.Path(__file__).resolve().parent
out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else here / '..' / 'workdir')
out.mkdir(parents=True, exist_ok=True)
bsb_path = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else out / 'bsb-full.json')
src = json.loads(bsb_path.read_text())

def normalize(t: str) -> str:
    t = t.lower()
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()

verses = sorted(src['verses'], key=lambda v: v['vid'])
rows = []
with open(out / 'texts.txt', 'w', encoding='ascii') as f:
    for i, v in enumerate(verses):
        n = normalize(v['text'])
        assert n, v
        f.write(n + '\n')
        rows.append({'i': i, 'vid': v['vid'], 'ref': v['ref'], 'text': v['text'], 'norm': n})
(out / 'verses.json').write_text(json.dumps({'source': src['source'], 'fetchedAt': src['fetchedAt'], 'verses': rows}))
print(f'{len(rows)} verses -> {out}/texts.txt')
