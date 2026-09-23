"""yearly_audit: per-month audit series computed from ONE annual corpus.

WHY THIS REPLACES monthly_series()
----------------------------------
`yearly_stats.monthly_series()` reads each month's own `stats.json`:

    for m in months:
        rd = run_dir(m, create=False)
        S = json.loads((rd / "stats.json").read_text(...))

That is exactly right in the monthly project -- it makes the yearly issue
report the SAME numbers the twelve shipped monthly issues reported, so a
yearly figure can never disagree with a shipped monthly one.

Here there are no monthly runs and no twelve `stats.json` files. So the
series is recomputed from the annual corpus, sliced by month. The audit
regexes are IMPORTED from `s04_10`, never retyped: a second copy of a
detection regex is a second definition of what the paper is measuring, and
the monthly project already paid for divergent copies once (a narration
filter existed in three versions and the narrowest one let a leak ship).

WHAT IS PRESERVED EXACTLY
-------------------------
1. The pooled-rate arithmetic in `yearly_stats.annual_rates()` is untouched
   and still consumes this module's output. An annual percentage is summed
   numerator over summed denominator, NEVER the mean of twelve monthly
   percentages -- months have different denominators, so averaging weights a
   thin month equally with a thick one. That is a five-fold error in the
   handbook's own worked example.

2. `audit_hit()` is imported, so the `area_stated` exclusion still applies:
   a current density written "24.1 mA cm-2" must not count as a stated
   device area.

3. The denominator is the count of works WITH AN ABSTRACT, matching
   `audit_over`'s `pool` semantics. Counting works without abstracts in the
   denominator would silently depress every rate, and the depression would
   look like a finding about the field.

THE MONTH-UNKNOWN EXCLUSION
---------------------------
Works dated YYYY-01-01 are OpenAlex's imprecise-date default, not January
papers. They are excluded from every per-month bucket and counted separately.
They stay in the annual corpus because they are real papers whose month is
merely unknown. Including them would put ~2.8x a normal month into January
and produce a fabricated spike in the trajectory section and on F5.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from stages.s04_10 import AUDIT_RX, audit_hit             # noqa: E402
from stages.util import year_months                        # noqa: E402

# Same six quantities, same order, as yearly_stats.AUDIT_KEYS. Imported
# there rather than redefined; this list exists only to assert agreement.
AUDIT_KEYS = [
    "efficiency_stated",
    "certified",
    "stabilised",
    "area_stated",
    "isos_label",
    "hysteresis",
]

MIN_ABSTRACT_WORDS = 40


def _usable(text: str) -> bool:
    return bool(text) and len(text.split()) >= MIN_ABSTRACT_WORDS


def audit_one(text: str) -> dict[str, bool]:
    """Fire every audit regex against one abstract.

    Delegates to the imported `audit_hit` so the area/Jsc exclusion and any
    future correction apply here automatically.
    """
    return {name: audit_hit(name, rx, text) for name, rx in AUDIT_RX.items()}


def monthly_series(year: str, months: list[str], corpus: list[dict],
                   abstracts: dict[str, str]) -> dict:
    """Per-month audit series, shaped exactly like yearly_stats expects.

    Emits `<key>.n`, `<key>.denominator`, `<key>.pct` per audit key plus
    `corpus_n` and `depth_n`, in `months` order, so `annual_rates()` consumes
    it unchanged.
    """
    series: dict = {"months": months, "corpus_n": [], "depth_n": []}
    for k in AUDIT_KEYS:
        series[f"{k}.n"] = []
        series[f"{k}.denominator"] = []
        series[f"{k}.pct"] = []

    by_month: dict[str, list[dict]] = {m: [] for m in months}
    month_unknown = 0
    for r in corpus:
        m = r.get("source_month")
        if not m:
            month_unknown += 1
            continue
        if m in by_month:
            by_month[m].append(r)

    for m in months:
        rows = by_month[m]
        pool = [abstracts.get(r.get("work_key", ""), "") for r in rows]
        pool = [t for t in pool if _usable(t)]
        den = len(pool)

        series["corpus_n"].append(len(rows))
        series["depth_n"].append(sum(1 for r in rows if r.get("depth")))

        hits = {k: 0 for k in AUDIT_KEYS}
        for t in pool:
            fired = audit_one(t)
            for k in AUDIT_KEYS:
                if fired.get(k):
                    hits[k] += 1

        for k in AUDIT_KEYS:
            series[f"{k}.n"].append(hits[k])
            series[f"{k}.denominator"].append(den)
            # Guard the zero-denominator case explicitly. max(den,1) would
            # silently report 0.0% for a month with no abstracts, which is
            # indistinguishable from a month where nothing fired.
            series[f"{k}.pct"].append(
                round(100.0 * hits[k] / den, 1) if den else None)

    series["month_unknown"] = month_unknown
    return series


def assert_month_coverage(year: str, series: dict) -> None:
    """Fail closed on an empty month.

    A yearly trajectory with a hole in it is not a quiet month; it is the
    silent-zero class. Twelve real months must each carry works.
    """
    holes = [m for m, n in zip(series["months"], series["corpus_n"]) if not n]
    if holes:
        raise SystemExit(
            f"FAIL-CLOSED: {year} has months with zero works: {holes}. "
            f"A trajectory cannot be plotted across a hole.")
    missing = [m for m in year_months(year) if m not in series["months"]]
    if missing:
        raise SystemExit(
            f"FAIL-CLOSED: {year} is missing months entirely: {missing}.")
