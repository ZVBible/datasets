# ZVBible public datasets

Public-domain data products used by **[ZVBible](https://zvbible.com)** ("Encounter The Word"): an offline-first Bible study app.

- Web: https://zvbible.com
- Android (beta): https://play.google.com/store/apps/details?id=com.zvbible.beta

This repository publishes **derived datasets** (OCR, scores, clusters) that ZVBible generates from public-domain sources. The underlying sources themselves remain available from their original hosts.

## Datasets

| Folder | Contents | Approx. size |
|---|---|---|
| [`davidson-lexicon/`](davidson-lexicon/) | OCR of Davidson's *Analytical Hebrew and Chaldee Lexicon* (1848 / Bagster–Harper reprint), raw and abbreviation-expanded | ~7 MB compressed |
| [`verse-similarity/`](verse-similarity/) | All-pairs gzip NCD verse similarity over the Berean Standard Bible (BSB), evaluated against Treasury of Scripture Knowledge (TSK) | ~7 MB compressed |
| [`cross-references/`](cross-references/) | TSK-derived Gospel clusters (with gzip similarity scores) and a TSK edge list | ~2.3 MB compressed |

Each folder has its own README with schema, example records, method, and limitations.

## Licenses

- **Data** in this repository is dedicated to the public domain under [CC0 1.0](LICENSE).
- **Scripts** under `*/scripts/` are [MIT](LICENSE-CODE).
- **Underlying sources** (not redistributed as page images here):
  - Samuel Davidson, *The Analytical Hebrew and Chaldee Lexicon* (1848; Internet Archive scan) — public domain.
  - Berean Standard Bible (BSB) — public domain ([Bible Hub / Berean Bible](https://berean.bible/)).
  - Treasury of Scripture Knowledge via [OpenBible.info](https://www.openbible.info/labs/cross-references/) — [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Keep that attribution when you reuse TSK-derived files.

## How to cite

> ZVBible datasets. https://github.com/ZVBible/datasets (CC0 for derived data; see folder READMEs for source attributions).

For TSK-derived files, also cite OpenBible.info / Treasury of Scripture Knowledge (CC BY 4.0).

## Contributing / feedback

Feedback and dataset requests: open an issue at https://github.com/ZVBible/discover/issues

Please do not open pull requests that add personal names, private emails, local machine paths, credentials, or references to other private repositories.
