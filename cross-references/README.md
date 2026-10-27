# Cross-references (TSK-derived)

Derived products from the Treasury of Scripture Knowledge via [OpenBible.info](https://www.openbible.info/labs/cross-references/) (CC BY 4.0).

## Files

| File | Description | Size |
|---|---|---|
| `gospel-clusters.json` | Multi-Gospel clusters built from cross-Gospel TSK edges, annotated with BSB gzip similarity | ~93 KB |
| `tsk-edges.tsv.gz` | Directed TSK edges used in the NCD evaluation: `from_vid`, `to_vid`, `votes` | ~2.1 MB |

## Schema: gospel-clusters.json

Top-level object:

| Field | Meaning |
|---|---|
| `source` | Attribution string |
| `url` | OpenBible download URL |
| `generatedAt` | ISO timestamp |
| `minVotes` | Minimum TSK vote weight to keep an edge (5) |
| `maxClusterVerses` | Cap on cluster size (40) |
| `crossGospelOnly` | Only edges that cross Gospels |
| `clusterCount` / `verseCount` / `edgeCount` | Totals |
| `gzipSimilarity` | Metadata for the BSB NCD similarity pass |
| `clusters` | Array of cluster objects |

Each cluster:

| Field | Meaning |
|---|---|
| `id` | e.g. `gc-00001` |
| `verseIds` | Integer vids in the cluster |
| `verseCount` / `edgeCount` | Sizes |
| `byGospel` | `{ matt, mark, luke, john }` → vid lists |
| `gzipSimilarity` (when present) | `{ mean, min, pairs: { "matt\|mark": 0.42, ... } }` where values are `1 - NCD` |

### Example (abbreviated)

```json
{
  "source": "OpenBible.info Treasury of Scripture Knowledge (CC BY 4.0)",
  "url": "https://a.openbible.info/data/cross-references.zip",
  "minVotes": 5,
  "clusterCount": 137,
  "clusters": [
    {
      "id": "gc-00001",
      "verseIds": [40005006, 41008034, 42009023],
      "byGospel": { "matt": [40005006], "mark": [41008034], "luke": [42009023], "john": [] },
      "gzipSimilarity": { "mean": 0.41, "min": 0.28, "pairs": { "matt|mark": 0.45 } }
    }
  ]
}
```

## Schema: tsk-edges.tsv.gz

No header. Three tab-separated columns:

```
from_vid	to_vid	votes
1001001	43001001	369
```

601,204 directed edges. Verse ids use the same `book*1e6 + chapter*1e3 + verse` scheme as the verse-similarity dataset.

## Method (Gospel clusters)

1. Take OpenBible TSK edges with vote weight ≥ 5 that link two different Gospels.
2. Agglomerate into size-capped clusters (max 40 verses) suitable for side-by-side reading.
3. For each multi-Gospel cluster, concatenate BSB text per Gospel and score every Gospel pair with `similarity = 1 - NCD(gzip-9)`.

## Limitations

- Clusters are **TSK-driven**, not a traditional synopsis harmony. Some clusters mix thematically related sayings rather than the same pericope.
- Vote weights reflect OpenBible's aggregated data and can change when OpenBible updates its dump.
- Gzip similarity is lexical (English BSB), not a claim about Synoptic dependence.

## License

Derived JSON/TSV: [CC0 1.0](../LICENSE) for the packaging, but the **TSK content** remains [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) OpenBible.info / Treasury of Scripture Knowledge — you must keep that attribution. BSB: public domain.
