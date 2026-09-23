"""R1: validate a filled label sheet, then compute precision and recall.

Run on synthetic labels BEFORE any human labelling, so a weekend of work never
lands on a script that has never executed. `--selftest` does exactly that.

WHAT IT COMPUTES

  precision  of an extractor flag: of the papers the machine flagged, how many
             did the human confirm
  recall     of the papers the human marked, how many did the machine find
  Wilson 95% intervals on both, because at k=0 or k=n the normal
             approximation returns a zero-width interval, and a zero-width
             interval on a precision claim is a false statement
  weighted   population rates via inverse-probability weights. The sample is
             STRATIFIED (certified and ISOS oversampled ~9x and ~6x), so an
             unweighted rate would describe the sheet, not the corpus.

  per-model  the same numbers split by the model that produced each card, so
             the qwen3.8-flash / glm-5.3-flash split becomes a measured
             model-agnosticism claim instead of a footnote.

'U' (unclear) is excluded from precision/recall and REPORTED SEPARATELY. It is
a measurement of how often the abstract itself is ambiguous, which is a finding
about the literature, not a labelling failure.

    python -u scripts/studies/label_sheet_analyze.py --selftest
    python -u scripts/studies/label_sheet_analyze.py r1_labels_filled.csv
"""
from __future__ import annotations

import csv
import json
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from studies.study_common import active_run, wilson, write_report  # noqa: E402
from stages.s04_10 import AUDIT_RX, audit_hit  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[3]
SHEET = ROOT / "papers" / "studies" / "label_sheet"

# human column -> the regex flag it audits
FLAG_FOR = {
    "states_pce": "efficiency_stated",
    "states_certified": "certified",
    "states_area": "area_stated",
    "states_t80": None,          # no corpus-tier regex; card-level only
    "isos_protocol": "isos_label",
}
ALLOWED = {"Y", "N", "U", ""}


def validate(rows: list[dict]) -> tuple[list[dict], dict]:
    """Fail closed on anything that would silently corrupt a rate."""
    frame = {r["work_key"]: r for r in json.loads(
        (SHEET / "sampling_frame.json").read_text(encoding="utf-8"))}
    problems, ok = [], []
    for r in rows:
        wk = (r.get("work_key") or "").strip()
        if not wk:
            problems.append("row with no work_key")
            continue
        if wk not in frame:
            problems.append(f"{wk}: not in the sampling frame")
            continue
        bad = [k for k in FLAG_FOR if (r.get(k) or "").strip().upper() not in ALLOWED]
        if bad:
            problems.append(f"{wk}: illegal value in {bad}")
            continue
        ok.append(r)
    seen = [r["work_key"] for r in ok]
    if len(seen) != len(set(seen)):
        problems.append("duplicate work_key rows")
    n_complete = sum(1 for r in ok
                     if all((r.get(k) or "").strip() for k in FLAG_FOR))
    return ok, {"n_rows": len(rows), "n_valid": len(ok),
                "n_complete": n_complete, "problems": problems}


def machine_side() -> dict:
    """Regex flags + card-level facts for the sampled papers, keyed by work_key.

    Computed HERE, never read off the sheet: the sheet is blind by design.
    """
    frame = json.loads((SHEET / "sampling_frame.json").read_text(encoding="utf-8"))
    want = {r["work_key"]: r for r in frame}
    out: dict[str, dict] = {}
    for month in sorted({r["month"] for r in frame}):
        rd = active_run(month)
        ab = {}
        for line in (rd / "private" / "02_abstracts.jsonl").read_text(
                encoding="utf-8").splitlines():
            if line.strip():
                o = json.loads(line)
                ab[o["work_key"].lower()] = o.get("abstract") or ""
        cards = {}
        p = rd / "claim_cards.jsonl"
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    c = json.loads(line)
                    cards[(c.get("work_key") or "").lower()] = c
        for wk, fr in want.items():
            if fr["month"] != month:
                continue
            text = ab.get(wk.lower(), "")
            c = cards.get(wk.lower())
            perf = (c or {}).get("performance") or {}
            stab = (c or {}).get("stability") or {}
            out[wk] = {
                "efficiency_stated": audit_hit("efficiency_stated",
                                               AUDIT_RX["efficiency_stated"], text),
                "certified": audit_hit("certified", AUDIT_RX["certified"], text),
                "area_stated": audit_hit("area_stated", AUDIT_RX["area_stated"], text),
                "isos_label": audit_hit("isos_label", AUDIT_RX["isos_label"], text),
                "has_card": c is not None,
                "card_t80": isinstance(stab.get("t80_h"), dict),
                "card_pce": (perf.get("pce_champion") or {}).get("value")
                            if isinstance(perf.get("pce_champion"), dict) else None,
                "extractor": ((c or {}).get("extractor") or {}).get("model") or "none",
                "weight": fr["weight"],
                "month": fr["month"],
            }
    return out


def pr(tp: int, fp: int, fn: int) -> dict:
    p_n, r_n = tp + fp, tp + fn
    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": round(tp / p_n, 4) if p_n else None,
        "precision_ci95": wilson(tp, p_n) if p_n else None,
        "recall": round(tp / r_n, 4) if r_n else None,
        "recall_ci95": wilson(tp, r_n) if r_n else None,
    }


def analyse(rows: list[dict], mach: dict) -> dict:
    res: dict = {"flags": {}, "by_model": {}, "unclear": {}, "numeric": {}}
    for col, flag in FLAG_FOR.items():
        tp = fp = fn = unc = 0
        w_hum = w_tot = 0.0
        ws: list[float] = []
        n_skipped_no_card = 0
        per_model: dict[str, list[int]] = {}
        for r in rows:
            wk = r["work_key"]
            m = mach.get(wk)
            if not m:
                continue
            h = (r.get(col) or "").strip().upper()
            if h == "":
                continue
            if h == "U":
                unc += 1
                continue
            # POPULATION MISMATCH GUARD. Every flag with a corpus-tier regex is
            # comparable on every sampled paper. states_t80 has no such regex
            # and falls back to a CARD-level field -- but cards exist only for
            # the depth tier, so 49 of the 100 sampled papers have none. Scoring
            # those would charge the extractor a false negative for a paper it
            # was never asked to read, deflating recall by extraction scope
            # rather than by any miss. Same class as the audit-denominator trap
            # that set this sheet's population: compare like with like, and say
            # how many rows the claim actually rests on.
            if flag is None and not m["has_card"]:
                n_skipped_no_card += 1
                continue
            machine = m[flag] if flag else m["card_t80"]
            human = (h == "Y")
            w_tot += m["weight"]
            if human:
                w_hum += m["weight"]
            if machine and human:
                tp += 1
            elif machine and not human:
                fp += 1
            elif human and not machine:
                fn += 1
            b = per_model.setdefault(m["extractor"], [0, 0, 0])
            if machine and human:
                b[0] += 1
            elif machine and not human:
                b[1] += 1
            elif human and not machine:
                b[2] += 1
        d = pr(tp, fp, fn)
        # Inverse-probability weighted population rate. The unweighted rate
        # describes the SHEET; only this describes the corpus.
        d["weighted_population_rate"] = round(w_hum / w_tot, 4) if w_tot else None
        d["n_unclear"] = unc
        res["flags"][col] = d
        res["by_model"][col] = {k: pr(*v) for k, v in sorted(per_model.items())}
        res["unclear"][col] = unc

    # numeric accuracy of the declared headline PCE
    hit = miss = 0
    for r in rows:
        v = (r.get("pce_value") or "").strip()
        m = mach.get(r["work_key"])
        if not v or not m or m["card_pce"] is None:
            continue
        try:
            if abs(float(v) - float(m["card_pce"])) < 0.05:
                hit += 1
            else:
                miss += 1
        except ValueError:
            continue
    n = hit + miss
    res["numeric"] = {"n_compared": n, "exact": hit, "wrong": miss,
                      "accuracy": round(hit / n, 4) if n else None,
                      "accuracy_ci95": wilson(hit, n) if n else None}
    return res


def selftest() -> int:
    """Synthetic labels with a KNOWN answer, so the maths is checked now."""
    mach = machine_side()
    if not mach:
        raise SystemExit("FAIL-CLOSED: no sampled papers; build the sheet first")
    rng = random.Random(7)
    rows = []
    for wk, m in mach.items():
        r = {"work_key": wk}
        for col, flag in FLAG_FOR.items():
            truth = m[flag] if flag else m["card_t80"]
            # agree 85% of the time, 5% unclear -- exercises tp/fp/fn/U
            u = rng.random()
            r[col] = "U" if u < 0.05 else (
                ("Y" if truth else "N") if u < 0.90 else ("N" if truth else "Y"))
        r["pce_value"] = ("" if m["card_pce"] is None else
                          str(m["card_pce"] if rng.random() < 0.8 else 99.9))
        rows.append(r)
    ok, rep = validate(rows)
    assert not rep["problems"], rep["problems"]
    assert rep["n_complete"] == len(mach), rep
    res = analyse(ok, mach)
    for col, d in res["flags"].items():
        assert d["tp"] + d["fp"] + d["fn"] + d["n_unclear"] > 0, col
        if d["precision"] is not None:
            lo, hi = d["precision_ci95"]
            assert lo <= d["precision"] <= hi, (col, d)
    print("[selftest] validate + analyse OK on "
          f"{len(ok)} synthetic rows, {len(res['flags'])} flags")
    print(json.dumps({k: {kk: v[kk] for kk in
                          ("tp", "fp", "fn", "precision", "recall",
                           "weighted_population_rate")}
                      for k, v in res["flags"].items()}, indent=2))
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    src = pathlib.Path(sys.argv[1])
    rows = list(csv.DictReader(src.open(encoding="utf-8-sig")))
    ok, rep = validate(rows)
    print(json.dumps(rep, indent=2))
    if rep["problems"]:
        raise SystemExit("FAIL-CLOSED: fix the problems above before analysing")
    mach = machine_side()
    res = analyse(ok, mach)
    meta = {"source": str(src), "n_labelled": len(ok),
            "n_complete": rep["n_complete"],
            "prereg_sha256": (SHEET / "preregistration.sha256")
            .read_text(encoding="utf-8").strip(),
            "result": res}
    write_report("label_precision_recall", ok, meta)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
