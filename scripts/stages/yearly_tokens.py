"""yearly_tokens: measure the real cost of a yearly issue from the ledgers.

Why this exists
---------------
The yearly handbook v1.0 asserted "~7 hours of model time" for a naive
re-extraction. That number was WRONG in two directions at once, and the only
way to find out was to read `runs/*/tokens.jsonl` instead of reasoning about
it:

- it counted EXTRACTION ONLY (35 min x 12), omitting the draft stage, so the
  end-to-end sequential figure is roughly double
- it was stated as a round assertion with no ledger behind it, which is
  precisely the "self-report instead of measurement" habit the monthly
  handbook 0.3 forbids

So the cost argument for aggregation is now computed, not claimed.

What the ledger can and cannot tell us
--------------------------------------
Monthly 8.3 already records that reported and estimated must never be mixed
into one figure. Reading the real rows adds two further caveats that the
handbook did not carry:

1. `agy -p` prints prose to stdout and reports NO usage. Every writer row has
   tokens_in = tokens_out = 0 and carries `words` instead. Writer cost is
   therefore ALWAYS an estimate (words x 1.33), and any yearly cost table
   that presents it beside the extractor's reported numbers without labelling
   the difference is misleading.

2. The extractor's `tokens_in` is not credible. Measured across the three
   shipped 2026 issues: 42 calls reporting 252 input tokens in total, i.e.
   ~6 per call, while each call carries twelve abstracts of ~187 words. The
   provider is reporting something other than prompt tokens. This module
   reports it verbatim and FLAGS it rather than silently substituting an
   estimate, because a fabricated input count is worse than a missing one.

A zero is a bug until proven otherwise (monthly 7.1); an implausible number
is the same class, and the honest response is to surface it.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from stages.util import RUNS, run_dir  # noqa: E402

# Monthly 8.3: agy reports no usage, so writer output is estimated from words.
WORDS_TO_TOKENS = 1.33

# Per-stage wall-clock, as STATED in MASTER_HANDBOOK 1.1. These are the
# handbook's own published figures, not measurements taken here: the ledger
# timestamps are unreliable for duration because s09 OVERWRITES tokens.jsonl
# and s13d appends to it, so the file's first timestamp is not the run's
# start. Deriving a duration from those spans would be a verifier bug of the
# 7.3 class -- a check that disagrees with reality because it measured the
# wrong thing.
HANDBOOK_MIN_EXTRACT = 35   # minutes per ~144 papers
HANDBOOK_MIN_DRAFT = 25     # minutes per monthly draft


def month_ledger(month: str) -> dict:
    """Read one month's token ledger. Returns measured values only."""
    rd = run_dir(month, create=False)
    f = rd / "tokens.jsonl"
    if not f.exists():
        raise SystemExit(f"FAIL-CLOSED: {f} missing; run s09/s13d first")
    rows = [json.loads(l) for l in f.open(encoding="utf-8") if l.strip()]
    if not rows:
        raise SystemExit(f"FAIL-CLOSED: {f} is empty (silent-zero class)")

    ext = [r for r in rows if r.get("stage") == "09_cards"]
    wri = [r for r in rows if r.get("cli") == "agy"]

    def s(rs, k):
        return sum(r.get(k) or 0 for r in rs)

    return {
        "month": month,
        "n_rows": len(rows),
        "extractor": {
            "calls": len(ext),
            "tokens_out": s(ext, "tokens_out"),
            "tokens_in_reported": s(ext, "tokens_in"),
            "cache_read": s(ext, "cache_read"),
            "n_papers": s(ext, "n_papers"),
            "token_source": "reported",
        },
        "writer": {
            "calls": len(wri),
            "words": s(wri, "words"),
            "est_tokens_out": round(s(wri, "words") * WORDS_TO_TOKENS),
            "tokens_out_reported": s(wri, "tokens_out"),
            "token_source": "estimated",
        },
    }


def credibility_flags(agg: dict) -> list[str]:
    """Surface implausible ledger values instead of consuming them silently."""
    flags = []
    e = agg["extractor"]
    if e["calls"] and e["tokens_in_reported"] / max(e["calls"], 1) < 100:
        flags.append(
            f"extractor tokens_in is NOT CREDIBLE: {e['tokens_in_reported']} "
            f"over {e['calls']} calls (~{e['tokens_in_reported']/max(e['calls'],1):.0f}"
            f"/call) while each call carries ~12 abstracts. The provider is "
            f"reporting something other than prompt tokens. Do not quote an "
            f"input-token total from this ledger; report it as unavailable.")
    w = agg["writer"]
    if w["calls"] and w["tokens_out_reported"] == 0:
        flags.append(
            f"writer reported 0 tokens across {w['calls']} calls, as "
            f"expected: agy -p reports no usage. Writer cost is ESTIMATED "
            f"(words x {WORDS_TO_TOKENS}) and must never be summed into one "
            f"figure with the extractor's reported tokens (8.3).")
    if e["tokens_out"] == 0:
        flags.append("extractor tokens_out is zero -- a zero is a bug until "
                     "proven otherwise (7.1)")
    return flags


def aggregate_year(year: str) -> dict:
    """Sum the ledgers of every built month of `year`, plus projections."""
    months = []
    for m in (f"{year}-{i:02d}" for i in range(1, 13)):
        if (RUNS / f"{m}.active").exists():
            rd = run_dir(m, create=False)
            if (rd / "tokens.jsonl").exists():
                months.append(m)
    if not months:
        raise SystemExit(f"FAIL-CLOSED: no token ledgers on disk for {year}")

    per = [month_ledger(m) for m in months]
    ext = {"calls": 0, "tokens_out": 0, "tokens_in_reported": 0,
           "cache_read": 0, "n_papers": 0, "token_source": "reported"}
    wri = {"calls": 0, "words": 0, "est_tokens_out": 0,
           "tokens_out_reported": 0, "token_source": "estimated"}
    for p in per:
        for k in ("calls", "tokens_out", "tokens_in_reported", "cache_read",
                  "n_papers"):
            ext[k] += p["extractor"][k]
        for k in ("calls", "words", "est_tokens_out", "tokens_out_reported"):
            wri[k] += p["writer"][k]

    n = len(per)
    out = {
        "year": year,
        "months_measured": months,
        "n_months_measured": n,
        "extractor": ext,
        "writer": wri,
        "per_month": per,
    }
    out["flags"] = credibility_flags(out)

    # ---- the cost argument for aggregation, computed ----
    ext_per_month = ext["tokens_out"] / n if n else 0
    out["projection"] = {
        "basis": f"{n} measured months",
        "extractor_tokens_out_per_month": round(ext_per_month),
        # A naive yearly re-extraction re-derives all twelve months.
        "naive_reextract_12mo_tokens_out": round(ext_per_month * 12),
        "naive_reextract_minutes": HANDBOOK_MIN_EXTRACT * 12,
        "naive_end_to_end_minutes": (HANDBOOK_MIN_EXTRACT
                                     + HANDBOOK_MIN_DRAFT) * 12,
        # The aggregate path re-extracts NOTHING. Its only LLM cost is one
        # draft pass over a body 2.9x the monthly size.
        "aggregate_extractor_tokens_out": 0,
        "aggregate_draft_scale_vs_monthly": 7000 / 2400,
        "aggregate_minutes_estimate": round(HANDBOOK_MIN_DRAFT * 7000 / 2400),
        "note": ("minutes are the handbook 1.1 published per-stage figures, "
                 "not measured here; ledger timestamps cannot give durations "
                 "because s09 overwrites tokens.jsonl and s13d appends"),
    }
    p = out["projection"]
    p["minutes_saved_vs_naive"] = (p["naive_end_to_end_minutes"]
                                   - p["aggregate_minutes_estimate"])
    p["extractor_tokens_saved"] = p["naive_reextract_12mo_tokens_out"]
    return out


def _table(agg: dict) -> str:
    e, w, p = agg["extractor"], agg["writer"], agg["projection"]
    L = []
    L.append(f"MEASURED over {agg['n_months_measured']} months "
             f"({', '.join(agg['months_measured'])})")
    L.append(f"  extractor  {e['calls']:>3} calls  "
             f"{e['tokens_out']:>10,} tokens_out (reported)  "
             f"cache_read {e['cache_read']:,}")
    L.append(f"  writer     {w['calls']:>3} calls  "
             f"{w['est_tokens_out']:>10,} tokens_out (ESTIMATED from "
             f"{w['words']:,} words)")
    L.append("")
    L.append("NAIVE 12-MONTH RE-EXTRACTION vs AGGREGATION")
    L.append(f"  naive extractor tokens_out   {p['naive_reextract_12mo_tokens_out']:>10,}")
    L.append(f"  naive extraction wall-clock  {p['naive_reextract_minutes']:>10} min "
             f"({p['naive_reextract_minutes']/60:.1f} h)  <- v1.0's '7h'")
    L.append(f"  naive END-TO-END wall-clock  {p['naive_end_to_end_minutes']:>10} min "
             f"({p['naive_end_to_end_minutes']/60:.1f} h)  <- the honest figure")
    L.append(f"  aggregate extractor tokens   {p['aggregate_extractor_tokens_out']:>10,}")
    L.append(f"  aggregate wall-clock est     {p['aggregate_minutes_estimate']:>10} min "
             f"({p['aggregate_minutes_estimate']/60:.1f} h)")
    L.append(f"  saved                        {p['minutes_saved_vs_naive']:>10} min "
             f"({p['minutes_saved_vs_naive']/60:.1f} h) and "
             f"{p['extractor_tokens_saved']:,} extractor tokens")
    if agg["flags"]:
        L.append("")
        L.append("LEDGER CREDIBILITY FLAGS")
        for f in agg["flags"]:
            L.append(f"  ! {f}")
    return "\n".join(L)


if __name__ == "__main__":
    yr = sys.argv[1] if len(sys.argv) > 1 else "2026"
    a = aggregate_year(yr)
    if "--json" in sys.argv:
        print(json.dumps(a, indent=2))
    else:
        print(_table(a))
