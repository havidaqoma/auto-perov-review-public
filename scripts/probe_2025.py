"""probe_2025: does OpenAlex actually have 2025 perovskite PV works, with abstracts?

WHY THIS EXISTS
---------------
The 2026-09-09 decision log said "no 2025 data exists". That phrasing was
sloppy and the operator was right to push back. Two different claims got
conflated:

  (a) "no 2025 perovskite PV literature was published"   <- FALSE, absurd
  (b) "no 2025 monthly HARVEST exists in runs/"          <- true, verified

This script measures (a) directly, using the EXACT production filter from
s01_harvest.py. An ad-hoc hand-written query would produce a number that
does not mean what the pipeline's number means, so the filter is imported
rather than retyped.

It also measures the thing that actually decides feasibility: whether 2025
works still carry a reconstructible abstract_inverted_index. Guard 1 anchors
every claim verbatim in the abstract, and GENERAL 6.1 establishes the
pipeline is abstract-first (full text is not required). So if 2025 abstracts
reconstruct, YEARLY 1.3's full-text degradation argument does NOT bind, and
a 2025 backfill is a cost question rather than a data-availability one.

Read-only. Writes one JSON report.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from common.net import oa                                  # noqa: E402
from stages.s01_harvest import FILTER                      # noqa: E402
from stages.util import reconstruct_abstract               # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "runs" / "probe_2025_openalex.json"

TYPES = "type:article|preprint|review"


def count(a: str, b: str) -> int:
    """Count works in [a, b]. per-page=1 BEFORE paginating (GENERAL 6)."""
    u = (f"https://api.openalex.org/works?filter={FILTER},"
         f"from_publication_date:{a},to_publication_date:{b},{TYPES}"
         f"&per-page=1")
    return oa(u, stage="probe_count")["meta"]["count"]


def abstract_sample(a: str, b: str, n: int = 50) -> dict:
    """Fetch n works and report how many reconstruct a usable abstract."""
    u = (f"https://api.openalex.org/works?filter={FILTER},"
         f"from_publication_date:{a},to_publication_date:{b},{TYPES}"
         f"&per-page={n}&select=id,doi,title,publication_date,"
         f"abstract_inverted_index")
    res = oa(u, stage="probe_abs").get("results", [])
    ok = 0
    words = []
    for r in res:
        txt = reconstruct_abstract(r.get("abstract_inverted_index"))
        if txt and len(txt.split()) >= 40:
            ok += 1
            words.append(len(txt.split()))
    return {
        "sampled": len(res),
        "with_usable_abstract": ok,
        "pct": round(100.0 * ok / len(res), 1) if res else 0.0,
        "median_words": sorted(words)[len(words) // 2] if words else 0,
    }


def main() -> int:
    rep: dict = {"filter": FILTER, "years": {}, "months_2025": {},
                 "abstract_probe": {}}

    print(f"production filter: {FILTER}\n")

    # --- year totals, including 2024 for the YoY question ---------------
    print("=== YEAR TOTALS (OpenAlex, production filter) ===")
    for y in (2024, 2025, 2026):
        n = count(f"{y}-01-01", f"{y}-12-31")
        rep["years"][str(y)] = n
        print(f"  {y}: {n:>7,} works")

    # --- per-month 2025, to prove coverage is not lumpy ----------------
    print("\n=== 2025 BY MONTH ===")
    ends = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
            7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}
    for m in range(1, 13):
        a, b = f"2025-{m:02d}-01", f"2025-{m:02d}-{ends[m]}"
        n = count(a, b)
        rep["months_2025"][f"2025-{m:02d}"] = n
        print(f"  2025-{m:02d}: {n:>6,}")

    # --- THE load-bearing measurement: abstract availability -----------
    print("\n=== ABSTRACT RECONSTRUCTION (guard 1 needs this) ===")
    for label, (a, b) in {
        "2025-01": ("2025-01-01", "2025-01-31"),
        "2025-06": ("2025-06-01", "2025-06-30"),
        "2025-12": ("2025-12-01", "2025-12-31"),
        "2026-08 (control, shipped)": ("2026-08-01", "2026-08-31"),
    }.items():
        s = abstract_sample(a, b)
        rep["abstract_probe"][label] = s
        print(f"  {label:<28} {s['with_usable_abstract']}/{s['sampled']} "
              f"= {s['pct']}%  median {s['median_words']} words")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")
    print(f"\nreport -> {OUT.relative_to(ROOT)}")

    tot = rep["years"].get("2025", 0)
    print(f"\nVERDICT: OpenAlex holds {tot:,} works matching the production "
          f"perovskite-PV filter with 2025 publication dates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
