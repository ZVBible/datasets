/**
 * Build a TSK edge list from the OpenBible.info cross_references.txt dump:
 * expand same-chapter ranges verse by verse, keep only positive votes,
 * keep the max vote per (from,to) pair.
 *
 * Input : INPUT/cross_references.txt  (OpenBible.info TSK dump)
 * Output: OUTDIR/tsk-edges.tsv        from_vid \t to_vid \t votes
 *
 * Usage: node build-tsk-edges.mjs [OUTDIR] [INPUT_TXT]
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseTskLine } from './tsk-book-abbrev.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUTDIR = process.argv[2] || path.join(HERE, '..', 'workdir');
const TXT = process.argv[3] || path.join(OUTDIR, 'cross_references.txt');

const lines = fs.readFileSync(TXT, 'utf8').split(/\r?\n/).filter(Boolean);
/** @type {Map<number, Map<number, number>>} */
const out = new Map();
for (const line of lines) {
  if (line.startsWith('From Verse') || line.includes('openbible.info')) continue;
  const rec = parseTskLine(line);
  if (!rec) continue;
  let m = out.get(rec.fromVid);
  if (!m) out.set(rec.fromVid, (m = new Map()));
  for (const to of rec.targets) {
    if (rec.votes > (m.get(to) ?? 0)) m.set(to, rec.votes);
  }
}
fs.mkdirSync(OUTDIR, { recursive: true });
const rows = [];
for (const [from, m] of out) for (const [to, v] of m) rows.push(`${from}\t${to}\t${v}`);
fs.writeFileSync(path.join(OUTDIR, 'tsk-edges.tsv'), rows.join('\n') + '\n');
console.log(`${rows.length} TSK edges from ${out.size} source verses → ${OUTDIR}/tsk-edges.tsv`);
