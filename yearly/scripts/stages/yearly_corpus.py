"""yearly_corpus: the backfill-mode replacement for yearly_aggregate.

WHY THIS FILE EXISTS INSTEAD OF yearly_aggregate.py
---------------------------------------------------
The monthly project's `yearly_aggregate.py` unions TWELVE monthly run
directories, resolving each through `runs/<YYYY-MM>.active`. That is correct
there and impossible here: this project harvests a year in one sweep and has
no monthly runs at all. Copying it would have produced a module that fails
closed on day one with "0/12 months built" -- and it would have been right.

So this module presents the SAME CONTRACT from a different source. Every key
`yearly_stats.py` and `yearly_section_map.py` read is produced identically:

    year, months, n_months, corpus_n, cards_n, cross_month_duplicates,
    per_month{corpus_n, depth_n, cards_n, axis_depth}, extractors,
    corpus[], cards[]

Keeping the contract is what lets the two verified downstream modules be
reused UNCHANGED. Their arithmetic (pooled rates, not the mean of monthly
rates) is the part worth keeping, and it does not care where the rows came
from -- only that `source_month` is present and honest.

WHAT CHANGES, AND WHY EACH CHANGE IS SAFE
-----------------------------------------
1. `source_month` is DERIVED from publication_date, not from which directory
   a row sat in. Only day-precision works get a month; imprecise Jan-1 works
   are month-unknown and excluded from the per-month series (see
   s01_harvest_yearly). They remain in the annual corpus because they are
   real papers whose month is merely unknown.

2. `cross_month_duplicates` is structurally 0 and is reported as such with a
   reason. In the monthly project a nonzero count is expected, because a work
   published late in June is backfilled into July's index and appears in two
   sweeps. One annual sweep cannot produce that, so a 0 here is a PROPERTY of
   the design, not the suspicious zero v1.0 section 1.5 warns about. The
   distinction is recorded in the returned dict so no reader has to infer it.

3. Duplicate collapse still runs, on `canon_work_key`, because one sweep can
   still return the same work twice across cursor pages. Dedupe DROPS A WHOLE
   CARD and never merges two cards' fields: a number and its label must come
   from the same sentence, and that survives only if the card stays intact.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from stages.util import (RUNS, is_year, read_jsonl, run_dir,  # noqa: E402
                         year_months)


def canon_work_key(k: str) -> str:
    """Canonical form for duplicate detection.

    Mirrors the monthly s18d.canon_work_key EXACTLY. Elsevier's '/j.' is
    dropped because a writer once transcribed '10.1016/joule...' for a card
    keyed '10.1016/j.joule...' and the citation silently failed to resolve.
    """
    s = (k or "").lower()
    s = s.replace("/j.", "/")
    return "".join(ch for ch in s if ch.isalnum())


def yearly_dir(year: str, create: bool = True) -> pathlib.Path:
    d = RUNS / f"{year}_yearly"
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def month_of(row: dict) -> str | None:
    """The row's month, or None when its date precision cannot support one."""
    if row.get("date_precision") != "day":
        return None
    mk = (row.get("publication_date") or "")[:7]
    return mk or None


def aggregate(year: str, require_full_year: bool = True) -> dict:
    """Build the annual corpus + card set from ONE annual run directory.

    Signature matches yearly_aggregate.aggregate so the downstream modules
    need no edit. `require_full_year` here asserts twelve months are
    REPRESENTED in the harvested data, rather than twelve directories
    existing.
    """
    if not is_year(year):
        raise SystemExit(f"expected a 4-digit year, got {year!r}")

    ptr = RUNS / f"{year}.active"
    if not ptr.exists():
        raise SystemExit(
            f"FAIL-CLOSED: no harvest for {year}. Run "
            f"scripts/stages/s01_harvest_yearly.py {year} first. This "
            f"project harvests a year directly; it does not aggregate "
            f"monthly runs (those live in the monthly project).")

    rd = run_dir(year, create=False)
    c_rows = read_jsonl(rd / "05_corpus.jsonl")
    k_rows = read_jsonl(rd / "claim_cards.jsonl")

    # A zero is a bug until proven otherwise. An empty corpus with a
    # successful-looking run dir is the silent-zero class.
    if not c_rows:
        raise SystemExit(
            f"FAIL-CLOSED: {year} has zero corpus rows. Run the scope stage "
            f"before aggregating.")
    if not k_rows:
        raise SystemExit(
            f"FAIL-CLOSED: {year} has zero claim cards. That is the "
            f"silent-zero class, not an empty year.")

    corpus: dict[str, dict] = {}
    cards: dict[str, dict] = {}
    dupes = 0
    month_unknown_corpus = 0
    month_unknown_cards = 0

    for r in c_rows:
        ck = canon_work_key(r.get("work_key", ""))
        if not ck:
            continue
        if ck in corpus:
            dupes += 1
            continue
        m = month_of(r)
        if m is None:
            month_unknown_corpus += 1
        corpus[ck] = {**r, "source_month": m}

    for r in k_rows:
        ck = canon_work_key(r.get("work_key", ""))
        if not ck:
            continue
        if ck in cards:
            continue
        m = month_of(r)
        if m is None:
            month_unknown_cards += 1
        cards[ck] = {**r, "source_month": m}

    # ---- per-month blocks, matching the aggregator's shape ------------
    months_present = sorted({c["source_month"] for c in corpus.values()
                             if c["source_month"]})
    per_month: dict[str, dict] = {}
    for m in months_present:
        m_corpus = [c for c in corpus.values() if c["source_month"] == m]
        m_cards = [c for c in cards.values() if c["source_month"] == m]
        axis_depth: dict[str, int] = {}
        for c in m_cards:
            ax = c.get("axis")
            if ax:
                axis_depth[ax] = axis_depth.get(ax, 0) + 1
        per_month[m] = {
            "corpus_n": len(m_corpus),
            "depth_n": len(m_cards),
            "cards_n": len(m_cards),
            "axis_depth": axis_depth,
        }

    if require_full_year and len(months_present) != 12:
        missing = [m for m in year_months(year) if m not in months_present]
        raise SystemExit(
            f"FAIL-CLOSED: {year} has {len(months_present)}/12 months "
            f"represented. Missing: {missing}. A yearly issue built from a "
            f"partial year is internally consistent and misstates its own "
            f"scope; every other gate would pass. To ship a deliberate "
            f"partial issue, pass require_full_year=False and record the "
            f"decision -- the manuscript must then state its own coverage.")

    # Provenance from RECORDS, never from live config. A back-matter fact
    # about which model did what is prose reaching a reader.
    extractors: dict[str, int] = {}
    for c in cards.values():
        mdl = ((c.get("extractor") or {}).get("model")) or "unknown"
        extractors[mdl] = extractors.get(mdl, 0) + 1

    return {
        "year": year,
        "mode": "yearly_backfill",
        "months": months_present,
        "n_months": len(months_present),
        "corpus_n": len(corpus),
        "cards_n": len(cards),
        "cross_month_duplicates": dupes,
        # v1.0 section 1.5 says a zero duplicate count across twelve months is
        # suspicious. That reasoning assumes twelve separate sweeps. One
        # annual sweep cannot double-index a work across months, so the
        # expected value here is 0 and only within-sweep repeats are counted.
        "duplicate_semantics": ("within a single annual sweep; cross-month "
                                "double-indexing is structurally impossible "
                                "in backfill mode"),
        "month_unknown_corpus": month_unknown_corpus,
        "month_unknown_cards": month_unknown_cards,
        "per_month": per_month,
        "extractors": extractors,
        "corpus": list(corpus.values()),
        "cards": list(cards.values()),
    }


def axis_mass(agg: dict) -> dict[str, int]:
    """Annual depth-tier mass per mechanism axis, from the aggregated cards."""
    out: dict[str, int] = {}
    for c in agg["cards"]:
        a = c.get("axis")
        if a:
            out[a] = out.get(a, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


if __name__ == "__main__":
    yr = sys.argv[1] if len(sys.argv) > 1 else "2025"
    full = "--partial" not in sys.argv
    a = aggregate(yr, require_full_year=full)
    print(json.dumps({k: v for k, v in a.items()
                      if k not in ("corpus", "cards")}, indent=2))
    print("axis mass:", json.dumps(axis_mass(a)))
