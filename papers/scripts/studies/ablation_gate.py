"""R5: the gate ablation. One extraction, scored with the guard OFF and ON.

Why this exists. R3 compared a fresh September ungated call (a short open
prompt) against the SHIPPED cards (the s09 anchor-demanding prompt, extracted
months earlier). The model was held fixed, but the prompt, the run date and the
sampling were not, so R3 measured the whole guarded extraction path against an
ungated path. It could not attribute the difference to the gate alone.

This study removes every difference except the gate:

  * one call per batch, with the EXACT s09 prompt, batch size, body format and
    2600-character abstract cut the shipped pipeline used;
  * the model is the one the shipped cards record (qwen3.8-flash), rebound from
    the cards exactly as R3 does, never read from live config;
  * the SAME raw model output is scored twice:
        gate_off  every numeric value the model returned, as returned;
        gate_on   the same objects passed through s09's guards 1-3
                  (anchor verbatim, truncate to 25 words, value inside anchor).

So any difference between the arms is caused by the guard and nothing else.
The raw replies are persisted before any scoring, so the scoring can be re-run
(or audited) without a single new model call.

Two guard variants are scored because the shipped guard had a defect: its
number parser read a thousands separator as a decimal point, so "1,080 h"
never matched a value of 1080 and the guard nulled correct values. Reporting
only the fixed guard would hide what the published issues actually did.

    python -u papers/scripts/studies/ablation_gate.py --run      # model calls
    python -u papers/scripts/studies/ablation_gate.py --score    # no calls
    python -u papers/scripts/studies/ablation_gate.py --run --limit 1
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "scripts"))
from studies.study_common import (ROOT, active_run, explain_ungrounded,  # noqa: E402
                                  norm_text, number_present,
                                  number_present_legacy, wilson, write_report)
import stages.s09_cards as s09  # noqa: E402

MONTHS = ["2026-01", "2026-02", "2026-03", "2026-04",
          "2026-05", "2026-06", "2026-07", "2026-08"]
FIELDS = ("pce_champion", "pce_certified", "active_area_cm2", "t80_h")
RAW_DIR = ROOT / "runs" / "studies" / "ablation_raw"
ABSTRACT_CUT = 2600          # s09.cards() slices abst[wk][:2600]
P_FLOOR = 1e-12


def load_pool():
    """Identical selection to R3 (baseline_scaled.load_month), all months."""
    pool, abst, models = [], {}, set()
    for m in MONTHS:
        rd = active_run(m)
        a = {}
        for line in (rd / "private" / "02_abstracts.jsonl").read_text(
                encoding="utf-8").splitlines():
            if line.strip():
                o = json.loads(line)
                a[o["work_key"].lower()] = o.get("abstract") or ""
        cards = [json.loads(l) for l in (rd / "claim_cards.jsonl").read_text(
            encoding="utf-8").splitlines() if l.strip()]
        models |= {(c.get("extractor") or {}).get("model") for c in cards}
        sel = [c for c in cards if (c.get("performance") or {})
               and a.get((c.get("work_key") or "").lower())]
        sel.sort(key=lambda c: c["work_key"])
        pool += [(m, c) for c in sel]
        abst.update(a)
    models.discard(None)
    if len(models) != 1:
        raise SystemExit(f"FAIL-CLOSED: cards disagree about the extractor: {models}")
    return pool, abst, models.pop()


def run(limit: int | None) -> int:
    pool, abst, model = load_pool()
    if s09.MODEL != model:
        print(f"[r5] rebinding extractor {s09.MODEL} -> {model} (from the cards)")
        s09.MODEL = model
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    nb = (len(pool) + s09.BATCH - 1) // s09.BATCH
    print(f"[r5] papers={len(pool)} batches={nb} model={model}")
    done_now = 0
    shard, nshard = 0, 1
    if "--shard" in sys.argv:      # e.g. --shard 2/4; batches are independent calls
        shard, nshard = map(int, sys.argv[sys.argv.index("--shard") + 1].split("/"))
    for bi in range(nb):
        if bi % nshard != shard:
            continue
        out = RAW_DIR / f"batch_{bi:03d}.json"
        if out.exists():
            continue                      # idempotent: never re-call a batch
        if limit is not None and done_now >= limit:
            break
        batch = pool[bi * s09.BATCH:(bi + 1) * s09.BATCH]
        body = []
        for n, (_m, c) in enumerate(batch):
            wk = c["work_key"]
            body.append(f"--- PAPER {n} ---\nTITLE: {c.get('title', '')}\n"
                        f"ABSTRACT: {abst[wk.lower()][:ABSTRACT_CUT]}")
        t0 = time.time()
        try:
            raw, tok = s09.call_opencode(s09.PROMPT + "\n\n".join(body))
            err = None
        except Exception as e:            # recorded, never silently skipped
            raw, tok, err = "", {}, f"{type(e).__name__}: {e}"
        rec = {"batch": bi, "model": model, "work_keys": [c["work_key"] for _m, c in batch],
               "months": [m for m, _c in batch], "raw": raw, "tokens": tok,
               "error": err, "sec": round(time.time() - t0, 1),
               "tools": "off (s09._no_tools_env + --pure; any tool part fails the call)",
               "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        if err is None:
            out.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        else:
            (RAW_DIR / f"batch_{bi:03d}.FAILED.json").write_text(
                json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        n_obj = len(s09.parse_array(raw)) if raw else 0
        print(f"[r5] batch {bi}/{nb}: {n_obj}/{len(batch)} objects "
              f"({rec['sec']}s){' FAILED ' + err if err else ''}", flush=True)
        done_now += 1
    return 0


# --------------------------------------------------------------------------
# scoring (no model calls)
# --------------------------------------------------------------------------

def _num_in_legacy(want: str, text: str) -> bool:
    """s09._num_in exactly as shipped in every published issue (comma = decimal)."""
    want = want.replace(",", ".")
    try:
        w = float(want)
    except Exception:
        return False
    for m in re.finditer(r"\d+(?:[.,]\d+)?", text):
        try:
            if abs(w - float(m.group(0).replace(",", "."))) < 1e-6:
                return True
        except Exception:
            pass
    return False


def guard(fld, source: str, num_in) -> tuple[dict | None, str]:
    """s09.guard_field guards 1-3 with a pluggable number matcher.

    Returns (shipped_field_or_None, reason). Kept line-for-line equivalent to
    s09.guard_field so the ablation tests the shipped guard, not a re-design.
    """
    if not isinstance(fld, dict):
        return None, "not_object"
    anchor = s09.norm(fld.get("anchor"))
    if not anchor or anchor.lower() not in s09.norm(source).lower():
        return None, "anchor_not_verbatim"
    words = anchor.split()
    if len(words) > 25:
        val_s = str(fld.get("value")) if fld.get("value") is not None else None
        head = " ".join(words[:25])
        if val_s and not num_in(val_s, head):
            for start in range(1, max(1, len(words) - 24)):
                win = " ".join(words[start:start + 25])
                if num_in(val_s, win):
                    head = win
                    break
        anchor = head
    val = fld.get("value")
    if val is not None and not num_in(str(val), anchor):
        return None, "value_not_in_anchor"
    return {"value": val, "anchor": anchor}, "shipped"


def _fixed_num_in(want: str, text: str) -> bool:
    """The guard as it now ships (s09._num_in with digit grouping)."""
    return s09._num_in(want, text)


def _value(fld):
    v = fld.get("value") if isinstance(fld, dict) else fld
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def fisher_exact(a: int, b: int, c: int, d: int) -> float:
    import math
    row1, col1 = a + b, a + c
    n = row1 + c + d
    if n == 0:
        return 1.0

    def lc(k, m):
        if m < 0 or m > k:
            return float("-inf")
        return math.lgamma(k + 1) - math.lgamma(m + 1) - math.lgamma(k - m + 1)

    def pmf(x):
        lp = lc(col1, x) + lc(n - col1, row1 - x) - lc(n, row1)
        return math.exp(lp) if lp > float("-inf") else 0.0

    p_obs = pmf(a)
    p = sum(pmf(x) for x in range(max(0, col1 - (n - row1)), min(col1, row1) + 1)
            if pmf(x) <= p_obs * (1 + 1e-9))
    return max(min(1.0, p), P_FLOOR)


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar test: binomial(b + c, 0.5) on the discordant pairs."""
    import math
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def score() -> int:
    pool, abst, model = load_pool()
    files = sorted(RAW_DIR.glob("batch_[0-9][0-9][0-9].json"))
    stale = [f.name for f in files
             if not str(json.loads(f.read_text(encoding="utf-8")).get("tools", "")).startswith("off")]
    if stale:
        raise SystemExit(f"FAIL-CLOSED: batches made with tools enabled: {stale[:5]}")
    nb = (len(pool) + s09.BATCH - 1) // s09.BATCH
    if len(files) != nb and "--allow-partial" not in sys.argv:
        raise SystemExit(f"FAIL-CLOSED: {len(files)} of {nb} batches cached; "
                         "finish the run or pass --allow-partial for a preview")
    rows, n_obj_missing = [], 0
    for f in files:
        rec = json.loads(f.read_text(encoding="utf-8"))
        got = {}
        for o in s09.parse_array(rec["raw"]):
            if isinstance(o, dict) and str(o.get("i", "")).isdigit():
                got[int(o["i"])] = o
        for n, wk in enumerate(rec["work_keys"]):
            o = got.get(n)
            if o is None:
                n_obj_missing += 1
                continue
            src = abst[wk.lower()][:ABSTRACT_CUT]
            for fld in FIELDS:
                raw_f = o.get(fld)
                v = _value(raw_f)
                if v is None:
                    continue
                g_leg, why_leg = guard(raw_f, src, _num_in_legacy)
                g_fix, why_fix = guard(raw_f, src, _fixed_num_in)
                grounded = number_present(v, src)
                rows.append({
                    "work_key": wk, "month": rec["months"][n], "field": fld,
                    "value": v,
                    "grounded": grounded,
                    "grounded_legacy_metric": number_present_legacy(v, src),
                    "ungrounded_class": "" if grounded else explain_ungrounded(v, fld, src),
                    "shipped_legacy_guard": g_leg is not None,
                    "legacy_guard_reason": why_leg,
                    "shipped_fixed_guard": g_fix is not None,
                    "fixed_guard_reason": why_fix,
                })

    def arm(sel, label):
        n = len(sel)
        u = sum(1 for r in sel if not r["grounded"])
        return {"arm": label, "n_values": n, "n_ungrounded": u,
                "ungrounded_rate": round(u / n, 4) if n else 0.0,
                "ungrounded_ci95": wilson(u, n),
                "values_per_100_papers": None}

    n_papers = sum(len(json.loads(f.read_text(encoding="utf-8"))["work_keys"])
                   for f in files)
    off = arm(rows, "gate_off")
    on_leg = arm([r for r in rows if r["shipped_legacy_guard"]], "gate_on_shipped_guard")
    on_fix = arm([r for r in rows if r["shipped_fixed_guard"]], "gate_on_fixed_guard")
    for a in (off, on_leg, on_fix):
        a["values_per_100_papers"] = round(100 * a["n_values"] / n_papers, 1) if n_papers else None
    tests = {}
    for a, key in ((on_leg, "shipped_legacy_guard"), (on_fix, "shipped_fixed_guard")):
        p = fisher_exact(off["n_ungrounded"], off["n_values"] - off["n_ungrounded"],
                         a["n_ungrounded"], a["n_values"] - a["n_ungrounded"])
        # The arms are the SAME values scored twice, so they are paired and
        # Fisher's independence assumption does not hold (kept for audit of
        # earlier drafts only). The paired test is exact McNemar on each value's
        # "ungrounded value in the output" status: b = ungrounded values the
        # guard removed, c = ungrounded values present only with the guard on
        # (structurally 0, the guarded arm is a subset of the ungated one).
        b = sum(1 for r in rows if not r["grounded"] and not r[key])
        c = 0
        pm = mcnemar_exact(b, c)
        tests[a["arm"]] = {"fisher_exact_p": p,
                           "fisher_exact_p_repr": f"< {P_FLOOR:.0e}" if p <= P_FLOOR else f"{p:.3e}",
                           "fisher_note": "invalid for paired arms; superseded by mcnemar_exact_p",
                           "mcnemar_b": b, "mcnemar_c": c,
                           "mcnemar_exact_p": pm,
                           "mcnemar_exact_p_repr": f"{pm:.3e}",
                           "removed_ungrounded": b,
                           "removed_grounded": sum(1 for r in rows if r["grounded"] and not r[key])}

    # what the gate removed: grounded values it nulled, and ungrounded ones it caught
    by_field = {}
    for fld in FIELDS:
        fr = [r for r in rows if r["field"] == fld]
        by_field[fld] = {
            "gate_off_values": len(fr),
            "gate_off_grounded": sum(r["grounded"] for r in fr),
            "gate_off_ungrounded": sum(not r["grounded"] for r in fr),
            "shipped_guard_kept": sum(r["shipped_legacy_guard"] for r in fr),
            "fixed_guard_kept": sum(r["shipped_fixed_guard"] for r in fr),
            "grounded_lost_shipped_guard": sum(r["grounded"] and not r["shipped_legacy_guard"] for r in fr),
            "grounded_lost_fixed_guard": sum(r["grounded"] and not r["shipped_fixed_guard"] for r in fr),
            "ungrounded_caught_fixed_guard": sum((not r["grounded"]) and not r["shipped_fixed_guard"] for r in fr),
        }
    cls = {}
    for r in rows:
        if not r["grounded"]:
            cls[r["ungrounded_class"]] = cls.get(r["ungrounded_class"], 0) + 1
    reasons = {}
    for r in rows:
        if r["grounded"] and not r["shipped_fixed_guard"]:
            reasons[r["fixed_guard_reason"]] = reasons.get(r["fixed_guard_reason"], 0) + 1

    n_grounded_off = sum(r["grounded"] for r in rows)
    n_grounded_kept = sum(r["grounded"] and r["shipped_fixed_guard"] for r in rows)
    # "absent" = no arithmetic link at all (not a rounding, unit or decimal
    # restatement): the strict reading of fabrication, reported beside the
    # raw ungrounded count so neither can be quoted without the other
    n_abs_off = sum(1 for r in rows if not r["grounded"] and r["ungrounded_class"] == "absent")
    n_abs_on = sum(1 for r in rows if not r["grounded"] and r["ungrounded_class"] == "absent"
                   and r["shipped_fixed_guard"])
    absent_only = {"gate_off": n_abs_off, "gate_off_ci95": wilson(n_abs_off, off["n_values"]),
                   "gate_on_fixed_guard": n_abs_on,
                   "fisher_exact_p": fisher_exact(n_abs_off, off["n_values"] - n_abs_off,
                                                  n_abs_on, on_fix["n_values"] - n_abs_on)}
    # Hand-read verdicts (reviewer != generator), joined fail-closed: every
    # ungrounded gate-off row needs exactly one verdict whose quote occurs
    # verbatim in the abstract. Only a complete run is reviewed.
    review = None
    if len(files) == nb:
        rp = ROOT / "papers" / "studies" / "r5_ungrounded_review.json"
        if not rp.exists():
            raise SystemExit(f"FAIL-CLOSED: {rp.name} missing; every ungrounded "
                             "gate-off value needs a hand-read verdict")
        rv = json.loads(rp.read_text(encoding="utf-8"))
        by = {(x["work_key"].lower(), x["field"], float(x["value"])): x for x in rv["rows"]}
        got = {(r["work_key"].lower(), r["field"], float(r["value"]))
               for r in rows if not r["grounded"]}
        if set(by) != got:
            raise SystemExit(f"FAIL-CLOSED: review rows != ungrounded rows "
                             f"(missing {sorted(got - set(by))[:3]}, extra {sorted(set(by) - got)[:3]})")
        counts = {}
        for k, x in by.items():
            if x["verdict"] not in rv["classes"]:
                raise SystemExit(f"FAIL-CLOSED: unknown verdict {x['verdict']!r}")
            if x["quote"] not in abst[k[0]][:ABSTRACT_CUT]:
                raise SystemExit(f"FAIL-CLOSED: quote not verbatim in the abstract of {k[0]}")
            counts[x["verdict"]] = counts.get(x["verdict"], 0) + 1
        err = rv.get("counts_as_error")
        if not err or any(c not in rv["classes"] for c in err):
            raise SystemExit("FAIL-CLOSED: review file lacks a valid counts_as_error ruling")
        n_err = sum(counts.get(c, 0) for c in err)
        n_nc = n_err + (0 if "footprint_as_area" in err else counts.get("footprint_as_area", 0))
        def removed(classes):
            return sum(1 for r in rows if not r["grounded"] and not r["shipped_fixed_guard"]
                       and by[(r["work_key"].lower(), r["field"], float(r["value"]))]["verdict"]
                       in classes)
        caught = removed(set(err) | {"footprint_as_area"})
        review = {"reviewer": rv["reviewer"], "by_verdict": counts,
                  "counts_as_error": err, "ruling": rv.get("counts_as_error_source"),
                  "n_error": n_err,
                  "error_rate": round(n_err / off["n_values"], 4),
                  "error_ci95": wilson(n_err, off["n_values"]),
                  "error_removed_by_fixed_guard": removed(set(err)),
                  "n_not_correct": n_nc,
                  "not_correct_is": "sensitivity: errors plus footprints (stricter reading, overruled)",
                  "not_correct_rate": round(n_nc / off["n_values"], 4),
                  "not_correct_ci95": wilson(n_nc, off["n_values"]),
                  "not_correct_removed_by_fixed_guard": caught,
                  "quotes_verified_verbatim": True}
    meta = {"study": "R5 gate ablation", "model": model, "months": MONTHS,
            "extractor_tools": "off (s09._no_tools_env + --pure; any tool part fails the call)",
            "complete": len(files) == nb,
            "n_papers_pool": len(pool), "n_batches_expected": nb,
            "n_batches_scored": len(files), "n_papers_scored": n_papers,
            "n_papers_no_object": n_obj_missing,
            "yield": {"gate_off_grounded": n_grounded_off,
                      "fixed_guard_grounded_kept": n_grounded_kept,
                      "fixed_guard_grounded_lost": n_grounded_off - n_grounded_kept,
                      "fixed_guard_grounded_kept_frac": round(n_grounded_kept / n_grounded_off, 4)
                      if n_grounded_off else None},
            "prompt": "s09_cards.PROMPT (verbatim)", "abstract_cut_chars": ABSTRACT_CUT,
            "arms": [off, on_leg, on_fix], "tests_vs_gate_off": tests,
            "gate_off_ungrounded_by_class": cls,
            "absent_only": absent_only,
            "review": review,
            "grounded_lost_fixed_guard_by_reason": reasons,
            "by_field": by_field}
    write_report("ablation_gate", rows, meta)
    print(json.dumps(meta, indent=1))
    return 0


if __name__ == "__main__":
    lim = None
    if "--limit" in sys.argv:
        lim = int(sys.argv[sys.argv.index("--limit") + 1])
    if "--run" in sys.argv:
        run(lim)
    if "--score" in sys.argv:
        score()
