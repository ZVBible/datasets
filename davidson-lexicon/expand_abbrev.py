#!/usr/bin/env python3
"""Expand Davidson Analytical Hebrew lexicon grammar abbreviations in OCR JSONL.

Reads abbreviations.json ({"abbr": "expansion"}), applies OCR fixes (sull. -> suff.),
then expands English analysis/gloss/raw tokens with word-boundary matching.
Does not expand inside Hebrew (Unicode Hebrew blocks). Does not invent Hebrew.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HEBREW_RE = re.compile(
    r"[\u0590-\u05FF\uFB1D-\uFB4F]+"  # Hebrew letters / presentation forms
)

# Fields that carry English grammatical gloss text in the sample JSONL.
EXPAND_FIELDS = ("analysis", "gloss", "raw")


def load_abbr_map(path: Path) -> list[tuple[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"abbreviations file must be a JSON object: {path}")
    # Longest keys first so "n. f. s." / "pr. name" win over "n." / "pr."
    items = [(str(k), str(v)) for k, v in data.items() if k and v and str(k) != str(v)]
    items.sort(key=lambda kv: (-len(kv[0]), kv[0].lower()))
    return items


def ocr_fix_english(text: str) -> str:
    """Fix unambiguous English OCR errors before abbreviation expansion."""
    # sull. is OCR for suff. (seen on page 527 and elsewhere)
    text = re.sub(r"(?<![A-Za-z])sull\.(?![A-Za-z])", "suff.", text, flags=re.IGNORECASE)
    # mase. is OCR for masc.
    text = re.sub(r"(?<![A-Za-z])mase\.(?![A-Za-z])", "masc.", text, flags=re.IGNORECASE)
    # Davidson divider X often glued to following n. (n.f.s. / n. m. s.)
    text = re.sub(r"(?<![A-Za-z])X(?=n\.)", "X ", text)
    return text


def _abbr_pattern(abbr: str) -> re.Pattern[str]:
    """Compile a case-sensitive pattern with English word boundaries.

    Allows flexible whitespace inside multi-token abbreviations (e.g. n.f.s. / n. f. s.).
    """
    parts = re.split(r"(\s+)", abbr)
    pieces: list[str] = []
    for part in parts:
        if not part:
            continue
        if part.isspace():
            pieces.append(r"\s+")
        else:
            pieces.append(re.escape(part))
    body = "".join(pieces)
    # Also accept the same abbr with spaces collapsed or inserted around dots
    # for dotted compounds like n.f.s. <-> n. f. s.
    if " " not in abbr and abbr.count(".") >= 2:
        # Build alternate with optional spaces after each internal period
        alt_parts = []
        for i, ch in enumerate(abbr):
            if ch == "." and i < len(abbr) - 1:
                alt_parts.append(r"\.\s*")
            else:
                alt_parts.append(re.escape(ch))
        body = "(?:" + body + "|" + "".join(alt_parts) + ")"
    return re.compile(rf"(?<![A-Za-z]){body}(?![A-Za-z])")


def expand_english(text: str, patterns: list[tuple[re.Pattern[str], str]]) -> str:
    for pat, expansion in patterns:
        text = pat.sub(expansion, text)
    return text


def expand_person_clusters(text: str) -> str:
    """Expand glued person/number/gender clusters like 3p.s.f. / 2p. pl. m.

    These are Davidson-style short parsings (see key note on 3 p. s. m.).
    """

    def repl(m: re.Match[str]) -> str:
        num = m.group("num")
        ord_map = {"1": "1st", "2": "2nd", "3": "3rd"}
        ordinal = ord_map.get(num, num)
        # optional number/gender tail
        number = m.group("number")
        gender = m.group("gender")
        bits = [f"{ordinal} person"]
        if number:
            bits.append("singular" if number.lower().startswith("s") else "plural")
        if gender:
            g = gender.lower().rstrip(".")
            bits.append("masculine" if g.startswith("m") else "feminine")
        return " ".join(bits)

    # 3p.s.f. / 3 p. s. f. / 2p. pl. m. / 3pers. sing. masc. already partly expanded
    pat = re.compile(
        r"(?<![A-Za-z])"
        r"(?P<num>[123])\s*"
        r"(?:p|pers)\.?\s*"
        r"(?:"
        r"(?P<number>s|sing|pl|plur)\.?\s*"
        r"(?P<gender>m|masc|f|fem)\.?"
        r"|"
        r"(?P<number2>s|sing|pl|plur)\.?"
        r"|"
        r"(?P<gender2>m|masc|f|fem)\.?"
        r")?"
        r"(?![A-Za-z])",
        flags=re.IGNORECASE,
    )

    def repl2(m: re.Match[str]) -> str:
        num = m.group("num")
        ordinal = {"1": "1st", "2": "2nd", "3": "3rd"}.get(num, num)
        number = m.group("number") or m.group("number2")
        gender = m.group("gender") or m.group("gender2")
        bits = [f"{ordinal} person"]
        if number:
            n = number.lower().rstrip(".")
            bits.append("singular" if n.startswith("s") else "plural")
        if gender:
            g = gender.lower().rstrip(".")
            bits.append("masculine" if g.startswith("m") else "feminine")
        return " ".join(bits)

    return pat.sub(repl2, text)


def map_over_non_hebrew(text: str, fn) -> str:
    """Apply fn only to non-Hebrew spans; leave Hebrew substrings untouched."""
    out: list[str] = []
    last = 0
    for m in HEBREW_RE.finditer(text):
        if m.start() > last:
            out.append(fn(text[last : m.start()]))
        out.append(m.group(0))
        last = m.end()
    if last < len(text):
        out.append(fn(text[last:]))
    return "".join(out)


# Placeholder so "1 Ch." / "2 Ch." (Chronicles) is not expanded as Chaldee.
_CHRON_PLACEHOLDER = "<<<CHRONICLES>>>"


def protect_chronicles(text: str) -> tuple[str, list[str]]:
    """Mask biblical book refs 1 Ch. / 2 Ch. before Ch. -> Chaldee expansion."""
    saved: list[str] = []

    def repl(m: re.Match[str]) -> str:
        saved.append(m.group(0))
        return f"{_CHRON_PLACEHOLDER}{len(saved) - 1}>>>"

    # Allow optional space: "1 Ch." / "1Ch." / "#2Ch."
    out = re.sub(r"(?<![A-Za-z])([12])\s*Ch\.(?![A-Za-z])", repl, text)
    return out, saved


def restore_chronicles(text: str, saved: list[str]) -> str:
    for i, orig in enumerate(saved):
        text = text.replace(f"{_CHRON_PLACEHOLDER}{i}>>>", orig)
    return text


def expand_text(text: str, patterns: list[tuple[re.Pattern[str], str]]) -> str:
    if not text:
        return text

    def on_english(chunk: str) -> str:
        chunk = ocr_fix_english(chunk)
        chunk, chron = protect_chronicles(chunk)
        chunk = expand_person_clusters(chunk)
        chunk = expand_english(chunk, patterns)
        chunk = restore_chronicles(chunk, chron)
        return chunk

    return map_over_non_hebrew(text, on_english)


def process_record(rec: dict, patterns: list[tuple[re.Pattern[str], str]]) -> dict:
    out = dict(rec)
    for field in EXPAND_FIELDS:
        if field in out and isinstance(out[field], str):
            out[field] = expand_text(out[field], patterns)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--abbr",
        type=Path,
        default=Path(__file__).with_name("abbreviations.json"),
        help="JSON object mapping abbreviation -> expansion",
    )
    ap.add_argument(
        "--in",
        dest="infile",
        type=Path,
        default=Path(__file__).with_name("sample.jsonl"),
    )
    ap.add_argument(
        "--out",
        dest="outfile",
        type=Path,
        default=Path(__file__).with_name("sample-expanded.jsonl"),
    )
    args = ap.parse_args(argv)

    pairs = load_abbr_map(args.abbr)
    patterns = [(_abbr_pattern(k), v) for k, v in pairs]

    n_in = 0
    with args.infile.open(encoding="utf-8") as fin, args.outfile.open(
        "w", encoding="utf-8"
    ) as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            fout.write(json.dumps(process_record(rec, patterns), ensure_ascii=False) + "\n")
            n_in += 1

    print(f"expanded {n_in} lines -> {args.outfile} ({len(pairs)} abbreviations)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
