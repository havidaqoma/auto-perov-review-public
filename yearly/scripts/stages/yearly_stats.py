"""Yearly stats: the annual number set, plus the monthly SERIES and YoY delta.

What this adds over twelve monthly stats.json files
---------------------------------------------------
A yearly issue can cite two things a monthly issue cannot:

- a TRAJECTORY: the same quantity measured twelve times, in order
- a YEAR-OVER-YEAR DELTA: this year's value against last year's

Both are computed here, deterministically, from cards and monthly stats that
already exist. Nothing is re-extracted and no model runs.

Every key emitted here is a key the manuscript may cite, so every key must be
derivable and checkable. The G3 abstract gate traces each abstract numeral to
stats, a card, or an explicitly allow-listed computed value; a stats key that
cannot be recomputed from disk is a key that will eventually be wrong and
unfalsifiable.

The percentage trap, paid for once already
------------------------------------------
An annual percentage is NOT the mean of twelve monthly percentages. Months
have different denominators (June 623 works, August 531), so averaging the
rates silently weights a thin month equally with a thick one. Every rate here
is recomputed as summed_numerator / summed_denominator, and the monthly series
is reported alongside so a reader can see the spread rather than trusting one
aggregate.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from stages.util import RUNS, run_dir  # noqa: E402

# Audit rates carried as a twelve-point series. These are the reporting-practice
# quantities the monthly issues already compute, so the yearly issue can show
# their trajectory rather than restating one month's value.
AUDIT_KEYS = [
    "efficiency_stated",
    "certified",
    "stabilised",
    "area_stated",
    "isos_label",
    "hysteresis",
]


def _v(card: dict, key: str):
    """Numeric value of a guarded performance/stability field, or None."""
    perf = card.get("performance") or {}
    if key in perf:
        return (perf[key] or {}).get("value")
    if key == "t80_h":
        return ((card.get("stability") or {}).get("t80_h") or {}).get("value")
    return None


def monthly_series(year: str, months: list[str]) -> dict:
    """Per-month series for every audit rate, plus corpus and depth counts.

    Reads each month's own stats.json rather than recomputing, so the yearly
    issue reports the SAME numbers the monthly issues shipped. A yearly figure
    that disagrees with a shipped monthly issue is a defect in one of them,
    and this is the cheapest place to make them agree by construction.
    """
    series: dict = {"months": months, "corpus_n": [], "depth_n": []}
    for k in AUDIT_KEYS:
        series[f"{k}.n"] = []
        series[f"{k}.denominator"] = []
        series[f"{k}.pct"] = []

    for m in months:
        rd = run_dir(m, create=False)
        S = json.loads((rd / "stats.json").read_text(encoding="utf-8"))
        series["corpus_n"].append(S.get("corpus.n"))
        series["depth_n"].append(S.get("selection.n_depth"))
        den = S.get("audit.corpus.denominator")
        for k in AUDIT_KEYS:
            series[f"{k}.n"].append(S.get(f"audit.corpus.{k}.n"))
            series[f"{k}.denominator"].append(den)
            series[f"{k}.pct"].append(S.get(f"audit.corpus.{k}.pct"))
    return series


def annual_rates(series: dict) -> dict:
    """Pooled annual rates: summed numerator over summed denominator.

    NOT the mean of the monthly percentages. See the module docstring.
    """
    out: dict = {}
    for k in AUDIT_KEYS:
        ns = [x for x in series[f"{k}.n"] if isinstance(x, (int, float))]
        ds = [x for x in series[f"{k}.denominator"]
              if isinstance(x, (int, float))]
        if not ns or not ds:
            continue
        num, den = sum(ns), sum(ds)
        out[f"audit.year.{k}.n"] = num
        out[f"audit.year.{k}.denominator"] = den
        out[f"audit.year.{k}.pct"] = round(100.0 * num / den, 1) if den else None
        # The spread matters more than the mean for a reporting audit: a rate
        # that swung 3%-15% across the year is a different finding from one
        # that sat flat, and the pooled number hides which happened.
        pcts = [p for p in series[f"{k}.pct"] if isinstance(p, (int, float))]
        if pcts:
            out[f"audit.year.{k}.month_min_pct"] = min(pcts)
            out[f"audit.year.{k}.month_max_pct"] = max(pcts)
    return out


def frontier_series(agg: dict) -> dict:
    """Best certified and best champion value per month, in month order.

    Feeds the yearly trajectory figure and the trajectory section. Values come
    from cards, which are anchor-verified, so every point on the curve traces
    to a verbatim quotation.

    Simulation and review papers are excluded from the MEASURED frontier for
    the reason recorded in handbook 5.1: a drift-diffusion study reporting
    ~30.8% sat beside certified hardware until a human noticed.
    """
    by_month: dict[str, dict] = {}
    for c in agg["cards"]:
        m = c.get("source_month")
        if not m:
            continue
        d = by_month.setdefault(m, {"certified": [], "champion": [],
                                    "n_cards": 0, "n_cert": 0})
        d["n_cards"] += 1
        if c.get("lens") in ("theory", "review"):
            continue
        cert = _v(c, "pce_certified")
        champ = _v(c, "pce_champion")
        if isinstance(cert, (int, float)):
            d["certified"].append(cert)
            d["n_cert"] += 1
        if isinstance(champ, (int, float)):
            d["champion"].append(champ)

    months = sorted(by_month)
    return {
        "months": months,
        "top_certified": [max(by_month[m]["certified"]) if by_month[m]["certified"]
                          else None for m in months],
        "top_champion": [max(by_month[m]["champion"]) if by_month[m]["champion"]
                         else None for m in months],
        "n_certified": [by_month[m]["n_cert"] for m in months],
        "n_cards": [by_month[m]["n_cards"] for m in months],
    }


def prior_year_stats(year: str) -> dict | None:
    """Last year's yearly stats, if a yearly issue exists for it on disk.

    Returns None rather than raising: the FIRST yearly issue legitimately has
    no prior, exactly as the first monthly issue is a legitimate G8 cold
    start. A missing prior is a cold start; a prior that exists and is ignored
    would be a bug.
    """
    f = RUNS / f"{int(year) - 1}_yearly" / "stats_yearly.json"
    if not f.exists():
        return None
    return json.loads(f.read_text(encoding="utf-8"))


def build_stats(agg: dict, abstracts: dict | None = None) -> dict:
    """The complete yearly number set. Deterministic, no model.

    BACKFILL WIRING. `monthly_series` above reads each month's own stats.json
    so a yearly figure can never disagree with a shipped monthly issue. That
    is right in the monthly project and impossible here: this repo harvests a
    year in one sweep and has no per-month run directories at all.

    So when `abstracts` is supplied the series is recomputed from the annual
    corpus by stages.yearly_audit, which IMPORTS the audit regexes from
    s04_10 rather than restating them. Two copies of a detection regex would
    be two definitions of what the paper measures.

    The pooled arithmetic in annual_rates() is untouched either way: an
    annual percentage is summed numerator over summed denominator, never the
    mean of twelve monthly percentages.
    """
    year = agg["year"]
    months = agg["months"]
    if abstracts is not None:
        from stages.yearly_audit import (assert_month_coverage,
                                         monthly_series as backfill_series)
        series = backfill_series(year, months, agg["corpus"], abstracts)
        assert_month_coverage(year, series)
    else:
        series = monthly_series(year, months)

    S: dict = {
        "year": year,
        "n_months": agg["n_months"],
        "corpus.n": agg["corpus_n"],
        "corpus.cross_month_duplicates": agg["cross_month_duplicates"],
        "cards.n": agg["cards_n"],
    }
    S.update(annual_rates(series))

    fs = frontier_series(agg)
    S["frontier.months"] = fs["months"]
    S["frontier.top_certified_series"] = fs["top_certified"]
    S["frontier.top_champion_series"] = fs["top_champion"]
    S["frontier.n_certified_series"] = fs["n_certified"]

    certs = [x for x in fs["top_certified"] if isinstance(x, (int, float))]
    if certs:
        S["frontier.year_top_certified"] = max(certs)
        S["frontier.year_first_certified"] = certs[0]
        S["frontier.year_last_certified"] = certs[-1]
        # Reported as an explicit delta rather than a growth rate: a
        # percentage change between two percentages is a quantity readers
        # routinely misread, and the manuscript should say "rose from A to B".
        S["frontier.certified_delta_pp"] = round(certs[-1] - certs[0], 2)

    # Per-axis annual mass, for the section map and the effort figure.
    for a, n in _axis_mass(agg).items():
        S[f"axes.{a}.n_depth_year"] = n

    # Year-over-year, when a prior yearly issue exists.
    prev = prior_year_stats(year)
    if prev:
        S["yoy.prior_year"] = prev.get("year")
        for k in ("corpus.n", "cards.n", "frontier.year_top_certified",
                  "audit.year.certified.pct"):
            if isinstance(prev.get(k), (int, float)) and isinstance(S.get(k), (int, float)):
                S[f"yoy.delta.{k}"] = round(S[k] - prev[k], 2)
    else:
        S["yoy.prior_year"] = None

    S["n_keys"] = len(S)
    return S


def _axis_mass(agg: dict) -> dict[str, int]:
    out: dict[str, int] = {}
    for c in agg["cards"]:
        a = c.get("axis")
        if a:
            out[a] = out.get(a, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


def yearly_dir(year: str, create: bool = True) -> pathlib.Path:
    d = RUNS / f"{year}_yearly"
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


if __name__ == "__main__":
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from stages.util import read_jsonl, run_dir
    from stages.yearly_corpus import aggregate

    if len(sys.argv) < 2:
        raise SystemExit("usage: yearly_stats.py <YYYY> [--partial]  "
                         "No default: the period must be stated.")
    yr = sys.argv[1]
    partial = "--partial" in sys.argv
    a = aggregate(yr, require_full_year=not partial)

    rd = run_dir(yr, create=False)
    abstracts = {x["work_key"]: x["abstract"]
                 for x in read_jsonl(rd / "private" / "02_abstracts.jsonl")}
    if not abstracts:
        raise SystemExit(
            f"FAIL-CLOSED: no abstracts for {yr}. The audit series is "
            f"computed over abstracts; an empty pool would report every "
            f"reporting rate as 0% and that zero would look like a finding "
            f"about the field.")

    st = build_stats(a, abstracts=abstracts)
    out = yearly_dir(yr) / "stats_yearly.json"
    out.write_text(json.dumps(st, indent=2), encoding="utf-8")
    print(f"[stats] {st['n_keys']} keys -> {out}")
    print(f"[stats] corpus.n={st['corpus.n']} cards.n={st['cards.n']} "
          f"n_months={st['n_months']}")
    print(f"[stats] frontier certified series: "
          f"{st.get('frontier.top_certified_series')}")
    print(f"[stats] certified pooled: {st.get('audit.year.certified.pct')}% "
          f"(monthly {st.get('audit.year.certified.month_min_pct')}-"
          f"{st.get('audit.year.certified.month_max_pct')}%)")
