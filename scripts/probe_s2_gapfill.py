"""probe_s2_gapfill: does Semantic Scholar still fill OpenAlex's abstract gap?

WHY THIS EXISTS
---------------
Havid proposed dropping Semantic Scholar and harvesting 2025 from OpenAlex
alone, on the reasoning that OpenAlex metadata is "already sufficient".

That is a design question with a measurable answer, and s02_06.py already
records the opposite conclusion in a comment:

    # backfill abstract from S2 when OpenAlex has none (40% gap, P-04b)
    if not abstract and doi in s2:
        abstract = s2[doi].get("abstract") or ""

So S2 is load-bearing for ABSTRACT COVERAGE, not for work discovery. The
abstract is the extraction input AND guard 1's verbatim source, so losing
abstracts loses cards, and losing cards loses citations.

This script measures, on real 2025 works:
  1. how many OpenAlex works carry a usable abstract
  2. of the ones that do NOT, how many S2 can fill by DOI

It reuses the production filter from s01_harvest so the numbers mean what
the pipeline's numbers mean.

Read-only. Writes one JSON report.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from common.net import oa                                  # noqa: E402
from stages.s01_harvest import FILTER, UA                   # noqa: E402
from stages.util import reconstruct_abstract               # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "runs" / "probe_s2_gapfill.json"

TYPES = "type:article|preprint|review"
MIN_WORDS = 40


def openalex_page(a: str, b: str, n: int) -> list[dict]:
    u = (f"https://api.openalex.org/works?filter={FILTER},"
         f"from_publication_date:{a},to_publication_date:{b},{TYPES}"
         f"&per-page={n}&select=id,doi,title,publication_date,"
         f"abstract_inverted_index")
    return oa(u, stage="probe_s2_oa").get("results", [])


def s2_lookup(dois: list[str]) -> dict:
    """Batch-lookup abstracts by DOI. S2 batch endpoint, anonymous."""
    got: dict = {}
    if not dois:
        return got
    try:
        r = requests.post(
            "https://api.semanticscholar.org/graph/v1/paper/batch",
            params={"fields": "externalIds,title,abstract"},
            json={"ids": [f"DOI:{d}" for d in dois]},
            headers=UA, timeout=90,
        )
        if r.status_code != 200:
            print(f"  ! S2 batch HTTP {r.status_code} (soft-fail)")
            return got
        for it in (r.json() or []):
            if not it:
                continue
            ex = (it.get("externalIds") or {})
            doi = (ex.get("DOI") or "").lower()
            ab = it.get("abstract") or ""
            if doi and ab:
                got[doi] = ab
    except Exception as e:                                  # noqa: BLE001
        print(f"  ! S2 batch soft-fail: {e}")
    return got


def probe(label: str, a: str, b: str, n: int = 100) -> dict:
    rows = openalex_page(a, b, n)
    have, missing = [], []
    for r in rows:
        doi = (r.get("doi") or "").replace("https://doi.org/", "").lower()
        txt = reconstruct_abstract(r.get("abstract_inverted_index"))
        if txt and len(txt.split()) >= MIN_WORDS:
            have.append(doi)
        else:
            missing.append(doi)

    miss_with_doi = [d for d in missing if d]
    filled = s2_lookup(miss_with_doi)
    usable_fill = {d: t for d, t in filled.items()
                   if len(t.split()) >= MIN_WORDS}

    oa_only = len(have)
    combined = oa_only + len(usable_fill)
    rec = {
        "sampled": len(rows),
        "openalex_abstract": oa_only,
        "openalex_pct": round(100.0 * oa_only / len(rows), 1) if rows else 0.0,
        "missing": len(missing),
        "missing_with_doi": len(miss_with_doi),
        "s2_filled": len(usable_fill),
        "combined": combined,
        "combined_pct": (round(100.0 * combined / len(rows), 1)
                         if rows else 0.0),
    }
    rec["gain_pp"] = round(rec["combined_pct"] - rec["openalex_pct"], 1)
    print(f"  {label:<12} OA {rec['openalex_pct']:>5}%  "
          f"+S2 {rec['s2_filled']:>3}  -> {rec['combined_pct']:>5}%  "
          f"(gain {rec['gain_pp']:+} pp)")
    return rec


def main() -> int:
    rep: dict = {"filter": FILTER, "min_words": MIN_WORDS, "periods": {}}
    print("Does S2 still fill OpenAlex's abstract gap? (2025)\n")
    print(f"{'period':<14} {'openalex':>8}  {'s2 fill':>7}  {'combined':>8}")
    for label, (a, b) in {
        "2025-01": ("2025-01-01", "2025-01-31"),
        "2025-06": ("2025-06-01", "2025-06-30"),
        "2025-12": ("2025-12-01", "2025-12-31"),
    }.items():
        rep["periods"][label] = probe(label, a, b)
        time.sleep(2)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")
    print(f"\nreport -> {OUT.relative_to(ROOT)}")

    gains = [v["gain_pp"] for v in rep["periods"].values()]
    print(f"\nS2 gain across periods: {gains} pp")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
