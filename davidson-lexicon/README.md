# Davidson Analytical Hebrew and Chaldee Lexicon (OCR)

Machine-readable OCR of Benjamin Davidson's *The Analytical Hebrew and Chaldee Lexicon* (1848), taken from the Internet Archive Bagster/Harper reprint scan.

## Source

- Internet Archive item: [analyticalhebrew0000unse_a3b2](https://archive.org/details/analyticalhebrew0000unse_a3b2)
- Page images: JPEG2000 archive at the IA download URL (not redistributed here; ~390 MB). OCR was run with Tesseract (`heb+eng`) on 888 converted page images (leaves 0000–0887).
- Public domain (1848 work).

## Files

| File | Description | Size |
|---|---|---|
| `davidson-ocr.jsonl.zip` | Raw Tesseract output, one JSON object per OCR line | ~3.5 MB |
| `davidson-expanded.jsonl.zip` | Same lines with English grammar abbreviations expanded from Davidson's own key | ~3.5 MB |
| `abbreviations.json` | 153 abbreviation → expansion pairs taken from Davidson's list | ~4 KB |
| `expand_abbrev.py` | Script that produced the expanded JSONL from the raw OCR + key | ~8 KB |

**Not included:** page scan images (too large). Download them from Internet Archive if you need them.

## Counts

- 888 pages (front matter, lexicon body, paradigms)
- 83,790 non-empty OCR lines (JSONL records)
- No pages failed OCR (every leaf produced at least one line)

## Schema

Each JSONL line is an object:

| Field | Type | Meaning |
|---|---|---|
| `source` | string | Original page image filename (e.g. `analyticalhebrew0000unse_a3b2_0042.jpg`) |
| `page` | int | 0-based leaf index (0–887) |
| `column` | int | Column on the page (1 or 2) |
| `line` | int | Line within the column |
| `headword` | string | Best-effort Latin/Hebrew headword from OCR |
| `hebrew_form` | string | Hebrew form when detected |
| `analysis` | string | Grammatical analysis (English; expanded in the expanded file) |
| `root` | string | Root when detected |
| `gloss` | string | Gloss / sense |
| `raw` | string | Raw OCR line text |
| `quality` | string | Heuristic quality label (e.g. `medium`) |
| `kind` | string | e.g. `lexicon_entry` |

### Example

```json
{
  "source": "analyticalhebrew0000unse_a3b2_0042.jpg",
  "page": 42,
  "column": 1,
  "line": 12,
  "headword": "אב",
  "hebrew_form": "",
  "analysis": "noun masculine singular",
  "root": "",
  "gloss": "father",
  "raw": "…",
  "quality": "medium",
  "kind": "lexicon_entry"
}
```

(Real lines vary; early leaves and poor scans are noisy.)

## Method

1. Download IA JPEG2000 page archive; convert leaves to JPEG.
2. OCR each page with Tesseract `heb+eng`.
3. Parse two-column layout into per-line records → `davidson-ocr.jsonl`.
4. Expand English abbreviations using `abbreviations.json` via `expand_abbrev.py` (word-boundary match; longest keys first; Hebrew Unicode blocks left alone). `1 Ch.` / `2 Ch.` (Chronicles) are left unexpanded by design.

## Limitations

- **Hebrew consonants are often wrong.** Tesseract on 19th-century type is unreliable for pointed and unpointed Hebrew.
- Vowel points were **not** corrected.
- Front matter and paradigm tables are included as OCR lines; they are not structured lexicon entries.
- Abbreviation expansion only covers Davidson's listed English abbreviations; OCR garbling of those abbreviations may leave some unexpanded.


## Changelog

- **2026-10-27** — Fixed dual-sense abbreviation `acc.`. Davidson's own key lists both *accent* and *accusative*. The expander now chooses *accent* when context indicates stress placement (e.g. `acc. shifted`, `drawn`, `retracted`, `on ult.`, `Milel`, `id.`, `dist. acc.`), and *accusative* otherwise. Regenerated `davidson-expanded.jsonl` (312 lines changed; 0 remaining `accusative shifted`). Author attribution corrected to Benjamin Davidson.

## License

Derived OCR JSONL and the expansion script outputs: [CC0 1.0](../LICENSE). `expand_abbrev.py`: [MIT](../LICENSE-CODE). Underlying printed work: public domain.
