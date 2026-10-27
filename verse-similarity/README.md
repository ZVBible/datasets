# Verse similarity (gzip NCD) over BSB, compared with TSK

Every Berean Standard Bible (BSB) verse compared with every other BSB verse using **gzip normalized compression distance (NCD)**, then measured against Treasury of Scripture Knowledge (TSK) cross-references.

English only. **31,086** BSB verses (BSB omits 17 KJV-numbered verses).

## Files

| File | Description |
|---|---|
| `bsb-ncd-sym-top20.jsonl.gz` | Per verse: top 20 nearest neighbours by **symmetric** NCD |
| `bsb-ncd-csls-top20.jsonl.gz` | Same, re-ranked with a CSLS-style hubness correction |
| `bsb-ncd-parallels.json` | Supplemental "wording parallels" layer (JSON map) |
| `bsb-ncd-parallels.tsv.gz` | Same pairs as TSV |
| `high-sim-pairs.tsv.gz` | High-similarity unordered pairs with TSK flags |
| `evaluation.json` | Precision / recall / hit@K vs TSK for each NCD variant |
| `layer-stats.json` | Stats for the parallels layer filters |
| `scripts/` | Self-contained generators to reproduce the scores (needs BSB JSON + TSK dump as inputs) |

## Schema: top-20 JSONL

One JSON object per verse:

| Field | Type | Meaning |
|---|---|---|
| `vid` | int | `book*1e6 + chapter*1e3 + verse` (English versification; Gen 1:1 = 1001001) |
| `ref` | string | Human reference, e.g. `"Genesis 1:1"` |
| `words` | int | Word count after normalization |
| `n` | array | Nearest neighbours: `[otherVid, ncd, tskVotes]` sorted best-first. `tskVotes` is 0 when the pair is not in TSK |

### Example

```json
{
  "vid": 1001001,
  "ref": "Genesis 1:1",
  "words": 10,
  "n": [[19113006, 0.3433, 0], [43001002, 0.3906, 369]]
}
```

## Schema: parallels JSON

Map from `fromVid` (string keys) to arrays of `[toVid, score]` where `score = round(100 * (1 - ncd))`, written in both directions.

```json
{ "1001001": [[19113006, 66]] }
```

## Schema: high-sim-pairs TSV

Header:

```
ref_a	ref_b	ncd_sym	in_tsk_votes	adjacent	words_a	words_b
```

## Method

**Text.** BSB, all 66 books. Normalization: lowercase; replace every character outside `[a-z0-9\s]` with a space; collapse whitespace.

**Distance.** `C(s)` = gzip length (zlib deflate level 9, gzip wrapper). For verses `x` and `y` joined by `"\n"`:

```
NCD(x, y) = (C(x\ny) − min(C(x), C(y))) / max(C(x), C(y))
```

- `xy`: query verse first
- `sym` (primary): `min(C(x\ny), C(y\nx))`
- `csls`: hubness correction `2·NCD − r(x) − r(y)` (`r` = mean NCD to 10 nearest neighbours)
- `minlen`: `sym` restricted to verses with at least 8 words

**All pairs.** `scripts/ncd_matrix.c` computes the full ordered compression-length matrix (~966M gzip compressions). On an 8-vCPU machine this took about 19 minutes. Symmetrization and evaluation are Python.

**TSK evaluation.** OpenBible.info TSK edges (CC BY 4.0), treated as undirected. Headline result with `sym`: nearest neighbour is a TSK cross-reference about **37%** of the time (~325× random). Recall@20 is only ~6% — TSK is mostly thematic; NCD only sees shared wording. See `evaluation.json` for full tables.

**Parallels layer filters** (see `layer-stats.json`): NCD ≤ 0.35, ≥ 8 words each, not within 2 verses in the same chapter, max degree 5 per verse.

## Reproducing

1. Obtain a BSB verse JSON of shape `{"source","fetchedAt","verses":[{"vid","ref","text"},...]}` and place it at `workdir/bsb-full.json`.
2. Obtain the OpenBible.info `cross_references.txt` dump (or use the prebuilt `../cross-references/tsk-edges.tsv.gz`).
3. From `scripts/`: `./run-all.sh ../workdir`

Requires `gcc`, zlib headers, Python 3 + NumPy, Node.js (only if rebuilding TSK edges from the text dump), and about 4 GB free disk for the run directory.

## Limitations

- English BSB only; no Hebrew/Greek source text.
- NCD captures **lexical** similarity, not doctrine or typology. Many TSK links will never appear in the top 20.
- Short formulaic verses ("And the LORD said…") can still hub despite filters.
- Full pair matrices (`pair.u16`, `sym.u16`, ~1.8 GB each) are **not** published here.

## License

Derived scores: [CC0 1.0](../LICENSE). Scripts: [MIT](../LICENSE-CODE). BSB text: public domain. TSK: OpenBible.info, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — keep that attribution.
