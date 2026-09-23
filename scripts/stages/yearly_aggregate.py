"""Yearly aggregation: build one year's corpus from the twelve monthly runs.

Why this is an AGGREGATOR and not a harvest
--------------------------------------------
The naive yearly issue re-runs the monthly chain with M=2026. That fails on
three counts, all measured:

1. Cost. Extraction is the long stage: ~35 min per 144 papers (handbook 1.1).
   Twelve months is ~7 hours of model time to re-derive cards that already
   exist on disk and are already anchor-verified.
2. Perturbation. Re-extracting a month changes every card in it, including the
   ones a shipped monthly issue already cited. The repair-not-re-run rule
   (handbook 7.8) exists for exactly this reason.
3. Indexing. 3.4 measured that a fourteen-month-old month retrieves WORSE
   than a two-month-old one (2.5% vs 5.0% full text) because publisher WAFs
   refuse the fetch. Re-harvesting January in December does not recover
   January; it loses it.

So the year is the UNION of the twelve monthly runs, plus one delta pass for
works that were indexed after their month was built. Nothing is re-extracted.

The silent-zero rule (7.1) applies with more force here, not less: this stage
reads twelve directories and a missing pointer looks exactly like an empty
month. Every month is therefore REQUIRED to resolve, and a month that yields
zero cards raises instead of contributing nothing.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from stages.util import RUNS, read_jsonl, run_dir  # noqa: E402


def months_of(year: str) -> list[str]:
    """The twelve month ids of a year, as '<year>-01' .. '<year>-12'."""
    return [f"{year}-{m:02d}" for m in range(1, 13)]


def available_months(year: str) -> list[str]:
    """Months of `year` that have a pinned run dir AND claim cards on disk.

    Deliberately does not fabricate a partial year. The caller decides whether
    a partial year is acceptable; this only reports what physically exists.
    """
    out = []
    for m in months_of(year):
        if not (RUNS / f"{m}.active").exists():
            continue
        rd = run_dir(m, create=False)
        if (rd / "claim_cards.jsonl").exists() and (rd / "stats.json").exists():
            out.append(m)
    return out


def canon_work_key(k: str) -> str:
    """Canonical form for cross-month duplicate detection.

    Mirrors s18d.canon_work_key deliberately: a work indexed in two months
    (published late in one, backfilled into the next) must collapse to ONE
    work, or the yearly corpus count is inflated and every percentage
    computed against it is wrong.

    Elsevier's '/j.' is dropped because the July 2026 writer transcribed
    '10.1016/joule...' for a card keyed '10.1016/j.joule...' (handbook 7.7 #1).
    """
    s = (k or "").lower()
    s = s.replace("/j.", "/")
    return "".join(ch for ch in s if ch.isalnum())


def aggregate(year: str, require_full_year: bool = True) -> dict:
    """Union the year's monthly runs into one corpus + card set.

    Returns the aggregate WITHOUT writing it, so a caller can assert on it
    before anything lands on disk.
    """
    avail = available_months(year)
    if not avail:
        raise SystemExit(
            f"FAIL-CLOSED: no monthly runs on disk for {year}. A yearly issue "
            f"is assembled from monthly runs; it is never harvested fresh.")
    if require_full_year and len(avail) != 12:
        missing = [m for m in months_of(year) if m not in avail]
        raise SystemExit(
            f"FAIL-CLOSED: {year} has {len(avail)}/12 months built. Missing: "
            f"{missing}. Build them first, oldest month first (the monthly G8 "
            f"compares against the latest prior issue on disk). To produce a "
            f"deliberate partial-year issue, pass require_full_year=False and "
            f"record the decision -- the manuscript must then state its own "
            f"coverage.")

    corpus: dict[str, dict] = {}
    cards: dict[str, dict] = {}
    per_month: dict[str, dict] = {}
    dupes = 0

    for m in avail:
        rd = run_dir(m, create=False)
        c_rows = read_jsonl(rd / "05_corpus.jsonl")
        k_rows = read_jsonl(rd / "claim_cards.jsonl")
        stats = json.loads((rd / "stats.json").read_text(encoding="utf-8"))

        # 7.1: a zero is a bug until proven otherwise. A month that
        # contributes no cards would silently shrink the year.
        if not k_rows:
            raise SystemExit(
                f"FAIL-CLOSED: {m} resolves but has zero claim cards. "
                f"That is the silent-zero class (handbook 7.1), not an empty "
                f"month.")

        for r in c_rows:
            ck = canon_work_key(r.get("work_key", ""))
            if not ck:
                continue
            if ck in corpus:
                dupes += 1
                continue
            corpus[ck] = {**r, "source_month": m}
        for r in k_rows:
            ck = canon_work_key(r.get("work_key", ""))
            if not ck:
                continue
            if ck in cards:
                continue
            cards[ck] = {**r, "source_month": m}

        per_month[m] = {
            "corpus_n": stats.get("corpus.n"),
            "depth_n": stats.get("selection.n_depth"),
            "cards_n": len(k_rows),
            "axis_depth": {k.split(".")[1]: v for k, v in stats.items()
                           if k.startswith("axes.") and k.endswith(".n_depth")},
        }

    # Extractor provenance across the whole year (8.4: from records, never
    # from live config). A yearly issue spanning an extractor swap must SAY
    # so rather than declaring one model for cards two models produced.
    extractors: dict[str, int] = {}
    for c in cards.values():
        mdl = ((c.get("extractor") or {}).get("model")) or "unknown"
        extractors[mdl] = extractors.get(mdl, 0) + 1

    return {
        "year": year,
        "months": avail,
        "n_months": len(avail),
        "corpus_n": len(corpus),
        "cards_n": len(cards),
        "cross_month_duplicates": dupes,
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
    yr = sys.argv[1] if len(sys.argv) > 1 else "2026"
    full = "--partial" not in sys.argv
    a = aggregate(yr, require_full_year=full)
    print(json.dumps({k: v for k, v in a.items()
                      if k not in ("corpus", "cards")}, indent=2))
    print("axis mass:", json.dumps(axis_mass(a)))
