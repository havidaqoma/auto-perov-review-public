"""H1 stats: the half-year number set, plus the six-month SERIES.

Adapts yearly_stats to a six-month window. Same two hard rules:

1. A period percentage is NOT the mean of the monthly percentages. Months have
   different denominators (January 475 works, June 623), so averaging the rates
   weights a thin month equally with a thick one. Every rate here is
   summed_numerator / summed_denominator, with the monthly series reported
   alongside so a reader sees the spread instead of trusting one aggregate.

2. Every key emitted is a key the manuscript may cite, so every key must be
   recomputable from disk. A stats key that cannot be recomputed is a key that
   will eventually be wrong and unfalsifiable.

Adds one thing the yearly module does not need: MONTH COVERAGE. June indexes
better than January (handbook 3.4), so an H1 issue can silently become a
May-June review wearing a six-month title. The shares computed here feed the
coverage gate.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from stages.util import RUNS, run_dir  # noqa: E402

AUDIT_KEYS = [
    "efficiency_stated",
    "certified",
    "stabilised",
    "area_stated",
    "isos_label",
    "hysteresis",
    # The SI's reporting-audit table prints this row too. It was missing from
    # this list while s19 read it, so the SI raised KeyError rather than
    # printing a wrong number -- fail-closed working as intended, but the fix
    # is to COMPUTE it, not to drop the row.
    "triplet_complete",
]

# Corpus counts that are simple sums across the six months, and the monthly key
# each is summed from. Named explicitly rather than pattern-matched: a key that
# silently stops being summed would leave the SI describing one month.
_SUM_KEYS = [
    "corpus.n_preprint",
    "corpus.n_translated",
    "corpus.n_with_abstract",
    "selection.core_n",
    "selection.n_eligible",
]


def _v(card: dict, key: str):
    """Read a numeric field from a card, wherever the schema puts it."""
    for sub in ("performance", "stability", "device", None):
        d = card.get(sub) if sub else card
        if isinstance(d, dict) and key in d:
            val = d[key]
            if isinstance(val, dict):
                val = val.get("value")
            if isinstance(val, (int, float)):
                return val
    return None


def monthly_series(months: list[str]) -> dict:
    """Per-month series for every audit rate, plus corpus and depth counts.

    Reads each month's own stats.json rather than recomputing, so the H1 issue
    reports the SAME numbers the monthly issues shipped.
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


def period_rates(series: dict) -> dict:
    """Pooled half-year rates: summed numerator over summed denominator."""
    out: dict = {}
    for k in AUDIT_KEYS:
        ns = [x for x in series[f"{k}.n"] if isinstance(x, (int, float))]
        ds = [x for x in series[f"{k}.denominator"] if isinstance(x, (int, float))]
        if not ns or not ds:
            continue
        num, den = sum(ns), sum(ds)
        out[f"audit.h1.{k}.n"] = num
        out[f"audit.h1.{k}.denominator"] = den
        out[f"audit.h1.{k}.pct"] = round(100.0 * num / den, 1) if den else None
        pcts = [p for p in series[f"{k}.pct"] if isinstance(p, (int, float))]
        if pcts:
            out[f"audit.h1.{k}.month_min_pct"] = min(pcts)
            out[f"audit.h1.{k}.month_max_pct"] = max(pcts)
    return out


def frontier_series(agg: dict) -> dict:
    """Best certified and best champion value per month, in month order.

    Simulation and review papers are excluded from the MEASURED frontier for
    the reason in handbook 5.1: a drift-diffusion study reporting ~30.8% sat
    beside certified hardware until a human noticed.
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


def month_coverage(agg: dict) -> dict:
    """Depth/card share per month -- the input to the coverage gate.

    An issue titled "January-June" must actually read all six months. This is
    the measurement that makes the title falsifiable.
    """
    per = agg["per_month"]
    total_cards = sum(v["cards_n"] for v in per.values())
    total_depth = sum(v["depth_n"] for v in per.values())
    out = {"months": sorted(per), "card_share_pct": {}, "depth_share_pct": {}}
    for m in sorted(per):
        out["card_share_pct"][m] = round(100.0 * per[m]["cards_n"] / total_cards, 1)
        out["depth_share_pct"][m] = round(100.0 * per[m]["depth_n"] / total_depth, 1)
    out["min_card_share_pct"] = min(out["card_share_pct"].values())
    out["min_depth_share_pct"] = min(out["depth_share_pct"].values())
    return out


def _axis_mass(agg: dict) -> dict[str, int]:
    out: dict[str, int] = {}
    for c in agg["cards"]:
        a = c.get("axis")
        if a:
            out[a] = out.get(a, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


def build_stats(agg: dict) -> dict:
    """The complete H1 number set. Deterministic, no model."""
    months = agg["months"]
    series = monthly_series(months)

    S: dict = {
        "edition": agg["edition"],
        "n_months": agg["n_months"],
        "months": months,
        "corpus.n": agg["corpus_n"],
        "corpus.cross_month_duplicates": agg["cross_month_duplicates"],
        "cards.n": agg["cards_n"],
        "series.months": series["months"],
        "series.corpus_n": series["corpus_n"],
        "series.depth_n": series["depth_n"],
    }
    S["selection.n_depth"] = sum(x for x in series["depth_n"]
                                 if isinstance(x, int))

    # Sums across the six months, read from each month's own stats.json so the
    # H1 issue reports what the monthly issues reported. Nothing is invented:
    # a key absent from a month raises rather than contributing a silent zero.
    for k in _SUM_KEYS:
        vals = []
        for m in months:
            rd = run_dir(m, create=False)
            MS = json.loads((rd / "stats.json").read_text(encoding="utf-8"))
            if k not in MS:
                raise SystemExit(
                    f"FAIL-CLOSED: {m} stats.json has no {k!r}; the H1 total "
                    f"would silently describe fewer than six months.")
            vals.append(MS[k])
        S[k] = sum(vals)

    # The audit denominator is the count of works carrying a usable abstract,
    # pooled the same way as the numerators (7.x: an aggregate rate is
    # summed_n / summed_denominator, never a mean of the monthly rates).
    S["audit.corpus.denominator"] = S["corpus.n_with_abstract"]

    # DEPTH-TIER audit, pooled the same way as the corpus tier.
    #
    # The SI reports both tiers with their denominators, which is the point of
    # the table: a rate over 3328 indexed abstracts and a rate over 884 closely
    # read papers are different measurements and must not be shown as one.
    # Pooled as summed_n / summed_denominator across the six months, never as a
    # mean of six monthly percentages -- the months have different depth tiers
    # (January 122, April 164), so averaging the rates would weight a thin
    # month equally with a thick one.
    depth_den = 0
    depth_num: dict[str, int] = {}
    for m in months:
        rd = run_dir(m, create=False)
        MS = json.loads((rd / "stats.json").read_text(encoding="utf-8"))
        d = MS.get("audit.depth.denominator")
        if not isinstance(d, int):
            raise SystemExit(
                f"FAIL-CLOSED: {m} stats.json has no audit.depth.denominator; "
                f"the H1 depth-tier rates would describe fewer than six months.")
        depth_den += d
        for k in AUDIT_KEYS:
            v = MS.get(f"audit.depth.{k}.n")
            if isinstance(v, (int, float)):
                depth_num[k] = depth_num.get(k, 0) + int(v)
    S["audit.depth.denominator"] = depth_den
    for k, num in depth_num.items():
        S[f"audit.depth.{k}.n"] = num
        S[f"audit.depth.{k}.pct"] = (round(100.0 * num / depth_den, 1)
                                     if depth_den else None)

    # Selection reproducibility. jaccard_median is a MEDIAN of medians across
    # six runs, which is reported as such rather than as a single run's value.
    jac = []
    for m in months:
        rd = run_dir(m, create=False)
        MS = json.loads((rd / "stats.json").read_text(encoding="utf-8"))
        if isinstance(MS.get("selection.jaccard_median"), (int, float)):
            jac.append(MS["selection.jaccard_median"])
    if jac:
        S["selection.jaccard_median"] = round(sorted(jac)[len(jac) // 2], 3)
        S["selection.jaccard_median_month_min"] = min(jac)
        S["selection.jaccard_median_month_max"] = max(jac)
    # Same draw count in every monthly run (config/gates.yaml sensitivity_draws).
    S["selection.sensitivity_draws"] = 200

    S.update(period_rates(series))

    for k in AUDIT_KEYS:
        S[f"series.{k}.pct"] = series[f"{k}.pct"]

    # Monthly-namespace aliases for the pooled half-year rates.
    #
    # audit.h1.* is authoritative: a pooled six-month rate is a different
    # quantity from one month's rate and must be nameable as such. But s18d's
    # abstract boundary and s19's audit table were written against the MONTHLY
    # key namespace (audit.corpus.*), and rewriting those consumers would fork
    # guards that currently exist once. So publish both names for the same
    # computed value. The alias is written HERE rather than patched into the
    # build adapter, because two consumers needed it and a fix applied in only
    # one consumer is the divergence of handbook 7.6 #12.
    for k in AUDIT_KEYS:
        for suffix in ("pct", "n"):
            src, dst = f"audit.h1.{k}.{suffix}", f"audit.corpus.{k}.{suffix}"
            if src in S:
                S[dst] = S[src]

    fs = frontier_series(agg)
    S["frontier.months"] = fs["months"]
    S["frontier.top_certified_series"] = fs["top_certified"]
    S["frontier.top_champion_series"] = fs["top_champion"]
    S["frontier.n_certified_series"] = fs["n_certified"]

    certs = [x for x in fs["top_certified"] if isinstance(x, (int, float))]
    if certs:
        S["frontier.h1_top_certified"] = max(certs)
        S["frontier.h1_first_certified"] = certs[0]
        S["frontier.h1_last_certified"] = certs[-1]
        # An explicit delta, not a growth rate: a percentage change between two
        # percentages is routinely misread. The manuscript says "rose from A to B".
        S["frontier.certified_delta_pp"] = round(certs[-1] - certs[0], 2)

    cov = month_coverage(agg)
    S["coverage.card_share_pct"] = cov["card_share_pct"]
    S["coverage.depth_share_pct"] = cov["depth_share_pct"]
    S["coverage.min_card_share_pct"] = cov["min_card_share_pct"]
    S["coverage.min_depth_share_pct"] = cov["min_depth_share_pct"]

    for a, n in _axis_mass(agg).items():
        S[f"axes.{a}.n_depth_h1"] = n

    # Per-axis corpus/depth/share in the MONTHLY key names, summed across the
    # six months. The SI's axis-distribution table reads these three keys for
    # every axis in config/axes.yaml, so a missing axis raises rather than
    # printing a table with a hole in it. Shares are recomputed from the summed
    # counts, never averaged from six monthly shares.
    axis_corpus: dict[str, int] = {}
    axis_depth: dict[str, int] = {}
    for m in months:
        rd = run_dir(m, create=False)
        MS = json.loads((rd / "stats.json").read_text(encoding="utf-8"))
        for k, v in MS.items():
            if k.startswith("axes.") and k.endswith(".n_corpus"):
                axis_corpus[k.split(".")[1]] = axis_corpus.get(k.split(".")[1], 0) + int(v or 0)
            elif k.startswith("axes.") and k.endswith(".n_depth"):
                axis_depth[k.split(".")[1]] = axis_depth.get(k.split(".")[1], 0) + int(v or 0)
    tot_axis = sum(axis_corpus.values()) or 1
    for a in sorted(set(axis_corpus) | set(axis_depth)):
        S[f"axes.{a}.n_corpus"] = axis_corpus.get(a, 0)
        S[f"axes.{a}.n_depth"] = axis_depth.get(a, 0)
        S[f"axes.{a}.share_pct"] = round(100.0 * axis_corpus.get(a, 0) / tot_axis, 1)

    S["n_keys"] = len(S)
    return S


def h1_dir(create: bool = True) -> pathlib.Path:
    d = RUNS / "2026-H1"
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def main() -> int:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from stages.h1_aggregate import aggregate
    agg = aggregate()
    S = build_stats(agg)
    d = h1_dir()
    (d / "stats.json").write_text(json.dumps(S, indent=2), encoding="utf-8")
    print(f"[h1-stats] {S['n_keys']} keys; corpus.n={S['corpus.n']} "
          f"depth={S['selection.n_depth']} cards={S['cards.n']}")
    print(f"[h1-stats] certified series: {S.get('frontier.top_certified_series')}")
    print(f"[h1-stats] min month card share: {S['coverage.min_card_share_pct']}%")
    for k in AUDIT_KEYS:
        print(f"    {k}: {S.get(f'audit.h1.{k}.pct')} % "
              f"(month range {S.get(f'audit.h1.{k}.month_min_pct')}-"
              f"{S.get(f'audit.h1.{k}.month_max_pct')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
