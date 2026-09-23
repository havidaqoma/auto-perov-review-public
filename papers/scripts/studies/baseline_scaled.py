"""R3 + R4: the scaled and harsh-regime arms of the fabrication comparison.

R3 -- SCALE. baseline_fabrication.py measured one month (159 vs 152 values) and
the Wilson intervals overlapped, so it established a method rather than a
difference. This pools every month's performance-bearing papers to reach ~1000
values per arm, where a ~1% base rate becomes separable from zero. Fisher exact
replaces interval-crossing as the decision rule, and the intervals stay in the
report so a reader can check the test.

R4 -- HARSH REGIME. The R3 baseline shows the model the whole abstract, so it
measures CARELESS extraction. The regime people actually fear is closed-book:
given only a title, invent a plausible number. The ungated arm then receives
the title alone while the grounding check is unchanged. The independent opinion
predicted misattribution would surface here; the abstract-in-context run found
none, so this is the test of that prediction.

Both regimes use the SAME extractor model as the pipeline, and grounding stays
deterministic -- is the value present in its own source abstract. No model is
asked to judge its own output.

    python -u scripts/studies/baseline_scaled.py                 # R3
    python -u scripts/studies/baseline_scaled.py --harsh         # R4
    python -u scripts/studies/baseline_scaled.py --harsh 2026-07 # one month
"""
from __future__ import annotations

import json
import math
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from studies.study_common import (active_run, norm_text,  # noqa: E402
                                  number_present, wilson, write_report)
from stages.s09_cards import call_opencode, parse_array  # noqa: E402


def extractor_of(cards: list) -> str:
    """The model that ACTUALLY extracted these cards, from the records.

    NEVER read config/models.yaml here. The extractor was repinned from
    qwen3.8-flash to glm-5.3-flash on 2026-09-11, AFTER every shipped month was
    extracted. Reading live config would run the ungated arm on glm while the
    guarded arm's cards came from qwen, so a model difference would be
    confounded with the guard difference -- destroying the one property this
    study exists to have (guards as the only variable). Same failure class as
    handbook 8.4, where AI_DECL read live config and shipped a false
    provenance statement.
    """
    seen = {(c.get("extractor") or {}).get("model") for c in cards}
    seen.discard(None)
    if len(seen) != 1:
        raise SystemExit(f"FAIL-CLOSED: cards disagree about the extractor: {seen}")
    return seen.pop()

HARSH = "--harsh" in sys.argv
MONTHS = [a for a in sys.argv[1:] if not a.startswith("--")] or [
    "2026-01", "2026-02", "2026-03", "2026-04",
    "2026-05", "2026-06", "2026-07", "2026-08"]

# Batch of 12 matches the shipped extractor (s09_cards.BATCH). A larger batch
# truncates the reply and loses papers: the first title-only smoke run lost 24
# of 36 papers in its last two batches for exactly that reason.
BATCH = 12

# Smallest p this test will ever REPORT. Not a numerical limit -- float64 holds
# 8.9e-15 perfectly well -- but an honesty floor: a two-arm count comparison at
# n~1200 cannot license a claim stronger than "below 1e-12", and printing a
# bare 0.0 asserts impossible certainty. The 767-paper title-only run stored
# exactly 0.0, and the cause was round(p, 8) in the summary block, NOT
# underflow. Diagnosed wrong once already; recorded here so it is not
# re-diagnosed wrong later.
P_FLOOR = 1e-12

_COMMON_SCHEMA = """Return a JSON array, one object per paper:
[{"i": <the paper index>,
  "architecture": "p-i-n" | "n-i-p" | "tandem_2T" | "module" | "unknown",
  "pce_champion": <best efficiency in percent, or null>,
  "pce_certified": <certified efficiency in percent, or null>,
  "active_area_cm2": <area in cm2, or null>,
  "t80_h": <hours to 80% of initial performance, or null>}]

Return ONLY the JSON array.

PAPERS:

"""

# The harsh prompt explicitly PERMITS null. A prompt that demanded a number
# would manufacture the result it claims to measure -- the finding has to be
# the model volunteering numbers it was told it could withhold.
HARSH_PROMPT = ("You are reporting device performance data for perovskite solar cell papers.\n\n"
                "For each paper below you are given its TITLE ONLY. Report the device\n"
                "performance figures for that paper. If you do not know a figure, use null.\n\n"
                + _COMMON_SCHEMA)

OPEN_PROMPT = ("You are extracting performance data from perovskite solar cell paper abstracts.\n\n"
               "For each paper below, return the key device performance figures.\n\n"
               + _COMMON_SCHEMA)

UNGATED_PROMPT = HARSH_PROMPT if HARSH else OPEN_PROMPT
FIELDS = ("pce_champion", "pce_certified", "active_area_cm2", "t80_h")


def load_month(month: str):
    rd = active_run(month)
    abst = {}
    for line in (rd / "private" / "02_abstracts.jsonl").read_text(
            encoding="utf-8").splitlines():
        if line.strip():
            o = json.loads(line)
            abst[o["work_key"].lower()] = o.get("abstract") or ""
    cards = [json.loads(l) for l in (rd / "claim_cards.jsonl").read_text(
        encoding="utf-8").splitlines() if l.strip()]
    pool = [c for c in cards
            if (c.get("performance") or {})
            and abst.get((c.get("work_key") or "").lower())]
    pool.sort(key=lambda c: c["work_key"])       # deterministic, never sampled
    return pool, abst


def _val(c, field):
    src = c.get("stability") if field == "t80_h" else c.get("performance")
    v = (src or {}).get(field)
    if isinstance(v, dict):
        v = v.get("value")
    return v if isinstance(v, (int, float)) else None


def fisher_exact(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact on [[a,b],[c,d]] via the hypergeometric pmf.

    No scipy dependency. At these rates (single-digit counts against ~1000) a
    chi-square is invalid and a normal approximation is worse, so Fisher is the
    honest test rather than the convenient one.

    RETURNS A FLOOR, NEVER A ZERO. The 767-paper title-only run summed to
    exactly 0.0 in float64 because the observed table (12/84 vs 0/1084) has
    log-pmf -32.35 and the tail underflows. Reporting "p = 0.0" would assert
    an impossible certainty -- the same class of defect as a hardcoded
    statistic. Anything below the floor is reported as the floor and the
    caller prints "< floor".
    """
    row1, col1 = a + b, a + c
    n = row1 + c + d
    if n == 0:
        return 1.0

    def lchoose(k: int, m: int) -> float:
        if m < 0 or m > k:
            return float("-inf")
        return math.lgamma(k + 1) - math.lgamma(m + 1) - math.lgamma(k - m + 1)

    def pmf(x: int) -> float:
        lp = lchoose(col1, x) + lchoose(n - col1, row1 - x) - lchoose(n, row1)
        return math.exp(lp) if lp > float("-inf") else 0.0

    lo, hi = max(0, col1 - (n - row1)), min(col1, row1)
    p_obs = pmf(a)
    p = sum(pmf(x) for x in range(lo, hi + 1) if pmf(x) <= p_obs * (1 + 1e-9))
    return max(min(1.0, p), P_FLOOR)


def main() -> int:
    pool, abst, titles = [], {}, {}
    for m in MONTHS:
        try:
            mp, ma = load_month(m)
        except FileNotFoundError as e:
            print(f"[r3] skip {m}: {e}")
            continue
        for c in mp:
            pool.append((m, c))
            titles[c["work_key"]] = c.get("title", "")
        abst.update(ma)
        print(f"[r3] {m}: {len(mp)} papers")

    regime = "title_only" if HARSH else "abstract_in_context"
    model = extractor_of([c for _m, c in pool])
    # Force the ungated arm onto the model that extracted the cards.
    # call_opencode reads s09_cards.MODEL, which now resolves to the NEW pin
    # (glm-5.3-flash, repinned 2026-09-11) while every card here was extracted
    # by qwen3.8-flash. Without this rebind the two arms differ by model AND
    # by guards, and the study loses the only property that makes it readable.
    import stages.s09_cards as _s09
    if _s09.MODEL != model:
        print(f"[r3] rebinding extractor {_s09.MODEL} -> {model} (from the cards)")
        _s09.MODEL = model
    print(f"[r3] regime={regime} papers={len(pool)} model={model} (from the cards)")

    # ---- ungated arm ----------------------------------------------------
    arm_a, batch_of, n_lost = [], {}, 0
    nb = (len(pool) + BATCH - 1) // BATCH
    for b0 in range(0, len(pool), BATCH):
        batch = pool[b0:b0 + BATCH]
        keys = [c["work_key"].lower() for _m, c in batch]
        for k in keys:
            batch_of[k] = keys
        body = []
        for i, (_m, c) in enumerate(batch):
            t = titles.get(c["work_key"], "")
            if HARSH:
                body.append(f"[{i}] TITLE: {t}")
            else:
                body.append(f"[{i}] TITLE: {t}\n"
                            f"ABSTRACT: {abst.get(c['work_key'].lower(), '')}")
        t0 = time.time()
        try:
            raw, _meta = call_opencode(UNGATED_PROMPT + "\n\n".join(body),
                                       timeout=900)
            arr = parse_array(raw)
        except Exception as e:
            print(f"[r3] batch {b0//BATCH}: FAILED {type(e).__name__}: {e}")
            arr = []
        got = 0
        for o in arr:
            try:
                i = int(o.get("i"))
            except Exception:
                continue
            if 0 <= i < len(batch):
                rec = {k: o.get(k) for k in FIELDS}
                rec["architecture"] = o.get("architecture")
                rec["work_key"] = batch[i][1]["work_key"]
                rec["month"] = batch[i][0]
                arm_a.append(rec)
                got += 1
        # A partial batch is DROPPED COVERAGE, not a clean result. Report it
        # rather than letting a short reply quietly shrink the denominator.
        if got < len(batch):
            n_lost += len(batch) - got
            print(f"[r3] batch {b0//BATCH}/{nb}: PARTIAL {got}/{len(batch)} "
                  f"({round(time.time()-t0,1)}s)")
        else:
            print(f"[r3] batch {b0//BATCH}/{nb}: {got}/{len(batch)} "
                  f"({round(time.time()-t0,1)}s)")

    # ---- guarded arm: the shipped cards for the SAME papers -------------
    arm_b = []
    for m, c in pool:
        rec = {f: _val(c, f) for f in FIELDS}
        rec["architecture"] = ((c.get("device") or {}).get("architecture")) or "unknown"
        rec["work_key"] = c["work_key"]
        rec["month"] = m
        arm_b.append(rec)

    def score(arm: str, src_rows: list[dict]) -> list[dict]:
        out = []
        for r in src_rows:
            wk = r["work_key"].lower()
            src = norm_text(abst.get(wk, ""))
            peers = batch_of.get(wk, [])
            for f in FIELDS:
                v = r.get(f)
                if not isinstance(v, (int, float)):
                    continue
                grounded = number_present(v, src)
                cross = False
                if not grounded:
                    for pk in peers:
                        if pk != wk and number_present(v, norm_text(abst.get(pk, ""))):
                            cross = True
                            break
                sq = (f == "pce_certified" and v > 29.4
                      and r.get("architecture") in ("p-i-n", "n-i-p"))
                out.append(dict(arm=arm, month=r["month"], work_key=r["work_key"],
                                field=f, value=v, architecture=r.get("architecture"),
                                grounded=grounded, cross_paper=cross,
                                sq_violation=bool(sq)))
        return out

    arm_label = "ungated_title_only" if HARSH else "ungated_baseline"
    rows = score(arm_label, arm_a) + score("guarded_pipeline", arm_b)

    def summ(arm: str) -> dict:
        rs = [r for r in rows if r["arm"] == arm]
        n = len(rs)
        ung = sum(1 for r in rs if not r["grounded"])
        return dict(arm=arm, n_values=n, n_ungrounded=ung,
                    ungrounded_rate=round(ung / n, 4) if n else 0.0,
                    ungrounded_ci95=wilson(ung, n),
                    n_cross_paper=sum(1 for r in rs if r["cross_paper"]),
                    n_sq_violation=sum(1 for r in rs if r["sq_violation"]))

    sa, sb = summ(arm_label), summ("guarded_pipeline")
    p = fisher_exact(sa["n_ungrounded"], sa["n_values"] - sa["n_ungrounded"],
                     sb["n_ungrounded"], sb["n_values"] - sb["n_ungrounded"])
    # NEVER round a p-value to fixed decimals. round(p, 8) turned a real
    # 8.885779466077036e-15 into a stored 0.0, which reads as impossible
    # certainty and was then mis-diagnosed as float underflow. float64 holds
    # this value exactly; the defect was the presentation, not the arithmetic.
    # Store full precision, plus a reader-facing string that says "< floor"
    # when the value is below what this design can honestly license.
    p_repr = f"< {P_FLOOR:.0e}" if p <= P_FLOOR else f"{p:.3e}"
    meta = dict(regime=regime, months=MONTHS, n_papers=len(pool), model=model,
                n_papers_lost_to_partial_batches=n_lost,
                arms=[sa, sb], fisher_exact_p=p, fisher_exact_p_repr=p_repr,
                p_floor=P_FLOOR,
                significant_at_0_05=bool(p < 0.05))
    name = "baseline_title_only" if HARSH else "baseline_scaled"
    csv_p, json_p = write_report(name, rows, meta)
    print("\n== SUMMARY ==")
    print(json.dumps(meta, indent=2))
    print(csv_p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
