"""01_harvest_yearly: harvest ONE WHOLE YEAR from OpenAlex in a single sweep.

HOW THIS DIFFERS FROM THE MONTHLY HARVEST
-----------------------------------------
The monthly project harvests a month and the yearly issue there is an
AGGREGATION of twelve such runs (MASTER_HANDBOOK_YEARLY v1.0 section 1).

This project has no monthly runs and never will: the monthly pipeline is a
separate, working repository that must not be disturbed. So a year is
harvested DIRECTLY, once, and then sliced into twelve months in Python for
the trajectory series.

That inverts v1.0's central rule, so it is justified rather than assumed:

  - v1.0 section 1.2 forbids re-extraction because it PERTURBS cards a
    shipped monthly issue already cited. Nothing here was ever shipped, so
    there is nothing to perturb. The rule is vacuous in backfill mode.
  - v1.0 section 1.3 argues an old month "retrieves worse". That table
    measures FULL TEXT. This pipeline is abstract-first (GENERAL 6.1) and
    guard 1 anchors in the abstract. Measured 2025 abstract reconstruction:
    2025-06 70%, 2025-12 74%, vs the shipped 2026-08 control at 62%.
    Two 2025 months reconstruct BETTER than the month that shipped.

ONE SWEEP, NOT TWELVE
---------------------
Twelve monthly sweeps would issue twelve count assertions and twelve
paginations of the same index. One annual sweep with cursor pagination is
fewer requests and one count band to assert. The per-month values the
trajectory section needs are derived from `publication_date` AFTER the
harvest, which is also the only way to get them CONSISTENTLY: a work whose
date is revised between two monthly sweeps would otherwise appear in two
months or neither.

THE JANUARY LUMPING ARTEFACT -- MEASURED, NOT SUSPECTED
-------------------------------------------------------
Measured on the production filter (scripts/probe_2025.py):

    2025-01: 1,569 works      2025-06:   567
    2025-02:   478            2025-12:   650

January carries ~2.8x every other month. That is not a January surge in
perovskite research. OpenAlex stores an imprecise publication date as the
1st of January, so a work known only as "2025" lands on 2025-01-01.

Untreated this becomes a FABRICATED SPIKE in the trajectory section and on
F5 -- a real number describing something that did not happen, which is the
7.8 misattribution class. So every work carries `date_precision`, and
January-1 works are excluded from the per-month trajectory while remaining
in the annual corpus. They are real papers; only their MONTH is unknown.

Nothing is deleted and nothing is silently reassigned: the count is
reported so the manuscript can state it.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

import requests
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from common.net import SourceFailure, oa, redact          # noqa: E402
from stages.util import (CONFIG, done, period_bounds, reconstruct_abstract,
                         run_dir, write_jsonl, year_months)  # noqa: E402

UA = {"User-Agent": "perovskite-pv-yearly/0.1"}
SELECT = ("id,doi,title,display_name,publication_date,type,language,authorships,"
          "primary_location,best_oa_location,open_access,abstract_inverted_index,"
          "cited_by_count,related_works,is_retracted")

# Identical to the monthly project's filter, deliberately. The yearly issue
# must survey the SAME field by the SAME definition, or its audit percentages
# are not comparable to the monthly ones.
FILTER = 'title_and_abstract.search:perovskite AND ("solar cell" OR photovoltaic)'
TYPES = "type:article|preprint|review"

# A work dated exactly YYYY-01-01 is treated as month-unknown. See module
# docstring: this is imprecise-date defaulting, not a January surge.
IMPRECISE_SUFFIX = "-01-01"
MIN_ABSTRACT_WORDS = 40


def date_precision(pub: str, year: str) -> str:
    """'day' for a real date, 'year' for the Jan-1 imprecise default.

    Kept as a named function with its own test rather than an inline check,
    because it is the single rule standing between the harvest and a
    fabricated January spike.
    """
    if not pub:
        return "unknown"
    return "year" if pub == f"{year}{IMPRECISE_SUFFIX}" else "day"


def harvest_year(year: str, *, max_pages: int = 120) -> dict:
    """Harvest one publication year. Returns the metadata dict it also writes.

    Fails closed on a count outside the yearly band. The assertion runs with
    per-page=1 BEFORE any pagination, because a zero looks exactly like a
    legitimately empty period and by then twelve pages of nothing would look
    like a successful run.
    """
    y = yaml.safe_load((CONFIG / "yearly.yaml").read_text(encoding="utf-8"))
    lo, hi = y["yearly"]["count_band"]

    a, b = period_bounds(year)
    rd = run_dir(year)
    meta: dict = {"period": year, "mode": "yearly_backfill",
                  "filter": FILTER, "sources": {}}

    base = (f"https://api.openalex.org/works?filter={FILTER},"
            f"from_publication_date:{a},to_publication_date:{b},{TYPES}")

    # ---- count band assertion FIRST ----------------------------------
    n = oa(base + "&per-page=1", stage="01y_count")["meta"]["count"]
    meta["openalex_count"] = n
    if n == 0 or not (lo <= n <= hi):
        raise SystemExit(
            f"FAIL-CLOSED: OpenAlex count {n} outside yearly band "
            f"[{lo},{hi}] for {year}. A zero is a bug until proven "
            f"otherwise; a number outside the band means the filter or the "
            f"year is wrong. Fix the query, never the band.")
    print(f"[01y] count band OK: {n} in [{lo},{hi}]")

    # ---- cursor pagination -------------------------------------------
    rows: list[dict] = []
    abstracts: list[dict] = []
    cursor, pages = "*", 0
    while cursor and pages < max_pages:
        u = (f"{base}&sort=publication_date&per-page=200"
             f"&cursor={cursor}&select={SELECT}")
        page = oa(u, stage="01y_harvest")
        got = page.get("results", [])
        for r in got:
            inv = r.pop("abstract_inverted_index", None)
            doi = (r.get("doi") or "").replace("https://doi.org/", "")
            wk = (doi or r.get("id") or "").lower()
            pub = r.get("publication_date") or ""
            r["work_key"] = wk
            r["date_precision"] = date_precision(pub, year)
            rows.append(r)
            abstracts.append({"work_key": wk,
                              "abstract": reconstruct_abstract(inv)})
        pages += 1
        cursor = (page.get("meta") or {}).get("next_cursor")
        print(f"[01y] page {pages}: +{len(got)} (total {len(rows)})")
        if not got:
            break

    if pages >= max_pages and cursor:
        raise SystemExit(
            f"FAIL-CLOSED: pagination hit max_pages={max_pages} with a live "
            f"cursor. The year is truncated, which would silently shrink "
            f"every denominator. Raise max_pages deliberately.")

    meta["sources"]["openalex"] = len(rows)
    meta["pages"] = pages

    # ---- the January artefact, reported not hidden -------------------
    imprecise = sum(1 for r in rows if r["date_precision"] == "year")
    meta["imprecise_dated"] = imprecise
    meta["imprecise_pct"] = round(100.0 * imprecise / len(rows), 1) if rows else 0.0
    print(f"[01y] imprecise-dated (Jan-1 default): {imprecise} "
          f"({meta['imprecise_pct']}%) -- excluded from the month series, "
          f"kept in the annual corpus")

    # ---- per-month distribution, day-precision only ------------------
    by_month = {m: 0 for m in year_months(year)}
    for r in rows:
        if r["date_precision"] != "day":
            continue
        mk = (r.get("publication_date") or "")[:7]
        if mk in by_month:
            by_month[mk] += 1
    meta["by_month_day_precision"] = by_month

    empty = [m for m, c in by_month.items() if c == 0]
    if empty:
        raise SystemExit(
            f"FAIL-CLOSED: months with zero day-precision works: {empty}. "
            f"A yearly trajectory cannot have an empty month; that is the "
            f"silent-zero class, not a quiet year.")

    with_abs = sum(1 for x in abstracts
                   if len((x['abstract'] or '').split()) >= MIN_ABSTRACT_WORDS)
    meta["with_abstract"] = with_abs
    meta["with_abstract_pct"] = (round(100.0 * with_abs / len(rows), 1)
                                 if rows else 0.0)
    print(f"[01y] usable abstracts (>= {MIN_ABSTRACT_WORDS} words): "
          f"{with_abs} ({meta['with_abstract_pct']}%)")

    write_jsonl(rd / "01_openalex.jsonl", rows)
    write_jsonl(rd / "private" / "01_abstracts.jsonl", abstracts)

    # ---- Semantic Scholar: BEST EFFORT, never on the critical path ----
    # Havid asked whether OpenAlex alone is sufficient. It is the primary and
    # only required source. S2 is retained ONLY as an abstract gap-filler
    # (the monthly s02_06 records a 40% gap it used to close) and it may fail
    # entirely without affecting the run. A 429 must never fail a build.
    s2: list[dict] = []
    try:
        su = ("https://api.semanticscholar.org/graph/v1/paper/search/bulk"
              "?query=perovskite+%28%22solar+cell%22+%7C+photovoltaic%29"
              f"&publicationDateOrYear={a}:{b}"
              "&fields=externalIds,title,abstract,publicationDate,venue")
        r = requests.get(su, headers=UA, timeout=90)
        if r.status_code == 200:
            for it in (r.json() or {}).get("data", []) or []:
                ex = it.get("externalIds") or {}
                s2.append({"doi": (ex.get("DOI") or "").lower(),
                           "title": it.get("title") or "",
                           "publication_date": it.get("publicationDate") or "",
                           "venue": it.get("venue") or "",
                           "abstract": it.get("abstract") or ""})
        else:
            print(f"[01y] S2 HTTP {r.status_code} (best-effort, skipped)")
        time.sleep(1)
    except Exception as e:                                  # noqa: BLE001
        print("[01y] S2 soft-fail (best-effort):", redact(str(e)))
    meta["sources"]["s2"] = len(s2)
    meta["s2_status"] = "ok" if s2 else "unavailable"
    write_jsonl(rd / "01_s2.jsonl", s2)

    (rd / "01_meta.json").write_text(json.dumps(meta, indent=2),
                                     encoding="utf-8")
    done(rd, "01_harvest_yearly", **{k: v for k, v in meta.items()
                                     if k != "by_month_day_precision"})
    print("[01y]", json.dumps(meta["sources"]))
    return meta


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    harvest_year(sys.argv[1])
