"""Independent re-verification of every shipped anchor (handbook 3.2).

This script exists because stage 09's own counters cannot be trusted to
validate stage 09. On the July run s09 reported nulled_number=0 while five
fields shipped quotations that ended immediately before their own number.
The bug was found only by re-checking the shipped cards against the source
abstracts with code that shares nothing with the extractor.

So: no import from s09_cards, no reuse of 09_cards_summary.json. Reads
claim_cards.jsonl and private/02_abstracts.jsonl and re-derives every count.

Four invariants, any violation exits non-zero:
  1. every anchor appears word for word in its source abstract
  2. no anchor exceeds anchor_word_max (25) words
  3. every numeric field value appears inside its own truncated anchor
  4. the corpus is not empty (a zero is a bug until proven otherwise)

Usage:  python scripts/verify_anchors.py 2026-08
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"
ANCHOR_WORD_MAX = 25

NUM = re.compile(r"\d+(?:[.,]\d+)?")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def isnum(s: str) -> bool:
    try:
        float(s)
        return True
    except Exception:
        return False


def num_in(want: str, text: str) -> bool:
    """True if `want` occurs as a number in `text`, tolerant of , vs . decimals."""
    want = str(want).replace(",", ".")
    if not isnum(want):
        return False
    for m in NUM.finditer(text):
        g = m.group(0).replace(",", ".")
        if isnum(g) and abs(float(want) - float(g)) < 1e-6:
            return True
    return False


def read_jsonl(p: pathlib.Path):
    with p.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def iter_anchored(card: dict):
    """Yield (kind, label, value_or_None, anchor) for everything carrying an anchor."""
    for group in ("performance", "stability"):
        for k, v in (card.get(group) or {}).items():
            if isinstance(v, dict) and v.get("anchor"):
                yield group, k, v.get("value"), v["anchor"]
    for c in card.get("claims") or []:
        if isinstance(c, dict) and c.get("anchor"):
            yield "claim", c.get("id") or "?", None, c["anchor"]


def verify(month: str) -> int:
    ptr = RUNS / f"{month}.active"
    if not ptr.exists():
        print(f"FAIL: {ptr} missing -- no pinned run for {month}")
        return 2
    rd = RUNS / ptr.read_text(encoding="utf-8").strip()

    cards_p = rd / "claim_cards.jsonl"
    abs_p = rd / "private" / "02_abstracts.jsonl"
    for p in (cards_p, abs_p):
        if not p.exists():
            print(f"FAIL: {p} missing")
            return 2

    abstracts = {norm(a["work_key"]).lower(): a.get("abstract") or ""
                 for a in read_jsonl(abs_p)}

    n_cards = n_anchor = 0
    not_verbatim: list = []
    over_long: list = []
    number_missing: list = []
    no_abstract: list = []

    for card in read_jsonl(cards_p):
        n_cards += 1
        wk = norm(card.get("work_key")).lower()
        src = norm(abstracts.get(wk, ""))
        if not src:
            no_abstract.append(wk)
            continue
        low_src = src.lower()
        for kind, label, value, anchor in iter_anchored(card):
            n_anchor += 1
            a = norm(anchor)
            ref = f"{wk}:{kind}.{label}"

            # invariant 1 -- verbatim in the source abstract
            if a.lower() not in low_src:
                not_verbatim.append({"ref": ref, "anchor": a[:120]})
                continue

            # invariant 2 -- length cap
            words = a.split()
            if len(words) > ANCHOR_WORD_MAX:
                over_long.append({"ref": ref, "words": len(words)})
                continue

            # invariant 3 -- the value is provable from its own shipped quote
            if value is not None and not num_in(value, a):
                number_missing.append({"ref": ref, "value": value,
                                       "anchor": a[:120]})

    ok = (not not_verbatim and not over_long and not number_missing
          and not no_abstract and n_anchor > 0)

    report = {
        "month": month,
        "run": rd.name,
        "cards": n_cards,
        "anchors": n_anchor,
        "verbatim": n_anchor - len(not_verbatim),
        "not_verbatim": len(not_verbatim),
        "over_word_max": len(over_long),
        "number_missing_from_own_anchor": len(number_missing),
        "cards_without_source_abstract": len(no_abstract),
        "status": "pass" if ok else "fail",
        "samples": {
            "not_verbatim": not_verbatim[:5],
            "over_word_max": over_long[:5],
            "number_missing": number_missing[:5],
            "no_abstract": no_abstract[:5],
        },
    }
    out = rd / "09_anchor_verification.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps({k: v for k, v in report.items() if k != "samples"}, indent=2))
    if not ok:
        print("\nFAIL samples:")
        print(json.dumps(report["samples"], indent=2)[:2000])
        if n_anchor == 0:
            print("\nzero anchors -- a zero is a bug until proven otherwise")
        return 1
    print(f"\nPASS  {n_anchor} anchors, all verbatim, "
          f"all <= {ANCHOR_WORD_MAX} words, every value inside its own quote")
    print(f"report: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(verify(sys.argv[1] if len(sys.argv) > 1 else "2026-08"))
