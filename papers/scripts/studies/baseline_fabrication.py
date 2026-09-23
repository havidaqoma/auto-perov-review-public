"""Item 3: does the guard layer actually prevent fabrication?

DESIGN -- the guards are the ONLY variable.

Comparing our pipeline against STORM or AutoSurvey would confound three things
at once: a different model, a different corpus, and a different guard layer. A
reviewer could attribute any gap to the model. So both arms here use the SAME
extractor model (config's qwen3.8-flash), the SAME papers, and the SAME
abstracts. The only difference is the guard layer:

  ARM A (ungated)  plain extraction prompt, no anchor requirement, no
                   verbatim check, no truncate-then-verify, no guard 5.
                   This is what an ordinary RAG pipeline emits.
  ARM B (pipeline) the shipped claim_cards.jsonl for the same month, which
                   passed the three anchor guards and verify_anchors.

METRIC -- grounding, measured deterministically, never by a model.

A number is GROUNDED if it appears in its own source abstract. That is a
script-checkable property, so nothing here depends on an LLM's opinion of its
own output. Three rates are reported per arm:

  ungrounded_rate   value absent from the cited paper's abstract  (fabrication)
  cross_paper_rate  value absent from ITS paper but present in another paper of
                    the same batch (the misattribution shape of 7.8: a real
                    number on the wrong paper)
  sq_violation_rate value presented as single junction above 29.4%

Wilson intervals throughout: at k=0 the normal approximation reports a zero-width
interval, and a zero-width interval on a fabrication rate is a false claim.

Run: python -u scripts/studies/baseline_fabrication.py [month] [n_papers]
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from studies.study_common import (active_run, norm_text,  # noqa: E402
                                  number_present, numbers_in, wilson,
                                  write_report)
from stages.s09_cards import call_opencode, parse_array, MODEL  # noqa: E402

MONTH = sys.argv[1] if len(sys.argv) > 1 else "2026-07"
N_PAPERS = int(sys.argv[2]) if len(sys.argv) > 2 else 60
BATCH = 12

# An ordinary RAG extraction prompt. It asks for the same fields the pipeline
# asks for, and deliberately omits every guard: no verbatim quotation, no
# 25-word cap, no instruction to bind the device label to the number's own
# sentence. This is the control, not a straw man -- it is what the same model
# produces when you simply ask it for the numbers.
UNGATED_PROMPT = """You are extracting performance data from perovskite solar cell paper abstracts.

For each paper below, return the key device performance figures.

Return a JSON array, one object per paper:
[{"i": <the paper index>,
  "architecture": "p-i-n" | "n-i-p" | "tandem_2T" | "module" | "unknown",
  "pce_champion": <best efficiency in percent, or null>,
  "pce_certified": <certified efficiency in percent, or null>,
  "active_area_cm2": <area in cm2, or null>,
  "t80_h": <hours to 80% of initial performance, or null>}]

Return ONLY the JSON array.

PAPERS:

"""

FIELDS = ("pce_champion", "pce_certified", "active_area_cm2", "t80_h")


def load_corpus():
    rd = active_run(MONTH)
    abst = {}
    for line in (rd / "private" / "02_abstracts.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            o = json.loads(line)
            abst[o["work_key"].lower()] = o.get("abstract") or ""
    cards = [json.loads(l) for l in
             (rd / "claim_cards.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    # Evaluate on the papers our pipeline actually extracted performance from,
    # so both arms answer the same question about the same papers. Selecting
    # papers the baseline happened to like would rig the comparison.
    pool = [c for c in cards
            if (c.get("performance") or {}) and abst.get((c.get("work_key") or "").lower())]
    pool.sort(key=lambda c: c["work_key"])        # deterministic, not sampled
    return pool[:N_PAPERS], abst


def _val(c, field):
    src = c.get("stability") if field == "t80_h" else c.get("performance")
    v = (src or {}).get(field)
    if isinstance(v, dict):
        v = v.get("value")
    return v if isinstance(v, (int, float)) else None


def _arch(c):
    return ((c.get("device") or {}).get("architecture")) or "unknown"


def score(arm: str, rows: list[dict], abst: dict, batch_of: dict) -> list[dict]:
    """One record per extracted numeric value, with its grounding verdict."""
    out = []
    for r in rows:
        wk = r["work_key"].lower()
        src = norm_text(abst.get(wk, ""))
        peers = batch_of.get(wk, [])
        for f in FIELDS:
            v = r.get(f)
            if v is None:
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
            out.append(dict(arm=arm, work_key=r["work_key"], field=f, value=v,
                            architecture=r.get("architecture"),
                            grounded=grounded, cross_paper=cross,
                            sq_violation=bool(sq)))
    return out


def summarise(arm: str, recs: list[dict]) -> dict:
    n = len(recs)
    ung = [r for r in recs if not r["grounded"]]
    crs = [r for r in recs if r["cross_paper"]]
    sqv = [r for r in recs if r["sq_violation"]]
    return dict(arm=arm, n_values=n,
                n_ungrounded=len(ung),
                ungrounded_rate=round(len(ung) / n, 4) if n else 0.0,
                ungrounded_ci95=wilson(len(ung), n),
                n_cross_paper=len(crs),
                cross_paper_rate=round(len(crs) / n, 4) if n else 0.0,
                n_sq_violation=len(sqv),
                sq_violation_rate=round(len(sqv) / n, 4) if n else 0.0)


def main() -> int:
    pool, abst = load_corpus()
    print(f"[bl] {MONTH}: {len(pool)} papers, model {MODEL} (both arms)")

    # ---- ARM A: ungated extraction, same model, same abstracts -----------
    arm_a, batch_of = [], {}
    for b0 in range(0, len(pool), BATCH):
        batch = pool[b0:b0 + BATCH]
        keys = [c["work_key"].lower() for c in batch]
        for k in keys:
            batch_of[k] = keys
        body = []
        for i, c in enumerate(batch):
            a = abst.get(c["work_key"].lower(), "")
            body.append(f"[{i}] TITLE: {c.get('title','')}\nABSTRACT: {a}")
        t0 = time.time()
        raw, meta = call_opencode(UNGATED_PROMPT + "\n\n".join(body), timeout=900)
        try:
            arr = parse_array(raw)
        except Exception as e:
            print(f"[bl] batch {b0//BATCH}: parse failed {e}")
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
                rec["work_key"] = batch[i]["work_key"]
                arm_a.append(rec)
                got += 1
        print(f"[bl] batch {b0//BATCH}: {got}/{len(batch)} papers, "
              f"{round(time.time()-t0,1)}s")

    # ---- ARM B: the shipped, guarded cards for the SAME papers -----------
    arm_b = []
    for c in pool:
        rec = {f: _val(c, f) for f in FIELDS}
        rec["architecture"] = _arch(c)
        rec["work_key"] = c["work_key"]
        arm_b.append(rec)

    recs = (score("ungated_baseline", arm_a, abst, batch_of)
            + score("guarded_pipeline", arm_b, abst, batch_of))
    sa = summarise("ungated_baseline", [r for r in recs if r["arm"] == "ungated_baseline"])
    sb = summarise("guarded_pipeline", [r for r in recs if r["arm"] == "guarded_pipeline"])

    meta = dict(month=MONTH, n_papers=len(pool), model=MODEL,
                design="same model, same papers, guards are the only variable",
                arms=[sa, sb])
    csv_p, _ = write_report("baseline_fabrication", recs, meta)
    print("\n== SUMMARY ==")
    print(json.dumps(meta["arms"], indent=2))
    print(csv_p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
