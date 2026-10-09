"""R6: score the extractor's numbers against numbers a human typed (frozen).

This file is hashed into papers/studies/r6_numeric/preregistration.json BEFORE
the sheet is opened. Changing it after labelling starts is a deviation and
must be listed by prereg_deviations.py; the hash check below enforces that.

WHAT IT MEASURES. R1 scored yes/no flags against text patterns. It never
compared a number the extractor wrote with a number a person read (external
review, 2026-10-09). R6 does exactly that, for three card fields:

    pce_champion     the headline efficiency of the paper's own best device
    pce_certified    an independently certified efficiency
    active_area_cm2  the device area

and one binding check: when the extractor's champion value is wrong, is it
the CONTROL device's value (the right number bound to the wrong condition)?

RULES (pre-registered):
  * Machine side = the shipped claim card (after anchor verification), joined
    by work_key here, never shown on the sheet.
  * Exact match after unit normalisation: % for efficiency; cm2 for area with
    mm2 / 100 and m2 * 10000. Equal when |m - h| <= 1e-6 * max(1, |h|).
  * Wilson 95% intervals. No P values: there is no comparison to test.
  * Unweighted. The rows are the PCE-stating subset of the stratified R1
    sample, so the rates describe this sample, not the corpus.
  * Fail-closed: the analysis refuses to run unless every row is marked done.

Run: python papers/scripts/studies/r6_analyze.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "papers" / "scripts"))
from studies.study_common import active_run, wilson  # noqa: E402

DIR = ROOT / "papers" / "studies" / "r6_numeric"
LABELS = DIR / "r6_labels_filled.csv"
FIELDS = ("pce_champion", "pce_certified", "active_area_cm2")
NUM = re.compile(r"(\d+(?:\.\d+)?)")


def parse(raw: str, field: str):
    """Human entry -> float in the card's unit, or None when left blank."""
    s = (raw or "").strip().lower().replace(",", "").replace("²", "2")
    if not s:
        return None
    m = NUM.search(s)
    if not m:
        raise SystemExit(f"FAIL-CLOSED: unreadable entry {raw!r} for {field}")
    x = float(m.group(1))
    if field == "active_area_cm2":
        if "mm" in s:
            x /= 100.0
        elif re.search(r"\bm2\b", s):
            x *= 10000.0
    return x


def same(a: float, b: float) -> bool:
    return abs(a - b) <= 1e-6 * max(1.0, abs(b))


def machine(frame: list) -> dict:
    out = {}
    for month in sorted({r["month"] for r in frame}):
        cards = {}
        p = active_run(month) / "claim_cards.jsonl"
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                c = json.loads(line)
                cards[(c.get("work_key") or "").lower()] = c
        for r in frame:
            if r["month"] != month:
                continue
            c = cards.get(r["work_key"].lower())
            perf = (c or {}).get("performance") or {}
            out[r["work_key"]] = {"has_card": c is not None, **{
                f: (perf[f].get("value") if isinstance(perf.get(f), dict) else None)
                for f in FIELDS}}
    return out


def score(rows: list, mach: dict) -> dict:
    res = {}
    for f in FIELDS:
        both = match = human_only_nocard = human_only_null = machine_only = 0
        wrong = []
        for r in rows:
            h, m = parse(r[f], f), mach[r["work_key"]][f]
            if h is not None and m is not None:
                both += 1
                if same(float(m), h):
                    match += 1
                else:
                    wrong.append({"work_key": r["work_key"], "human": h, "machine": m,
                                  "human_control": parse(r.get("pce_control", ""), f)
                                  if f == "pce_champion" else None})
            elif h is not None:
                if mach[r["work_key"]]["has_card"]:
                    human_only_null += 1
                else:
                    human_only_nocard += 1
            elif m is not None:
                machine_only += 1
        lo, hi = wilson(match, both)
        d = {"n_both": both, "n_exact": match, "exact_rate": match / both if both else None,
             "wilson95": [lo, hi], "human_only_no_card": human_only_nocard,
             "human_only_card_null": human_only_null, "machine_only": machine_only,
             "mismatches": wrong}
        if f == "pce_champion":
            d["binding_errors"] = sum(1 for w in wrong if w["human_control"] is not None
                                      and same(float(w["machine"]), w["human_control"]))
            d["n_with_human_control"] = sum(1 for r in rows if parse(r.get("pce_control", ""), f)
                                            is not None)
        res[f] = d
    return res


def main() -> int:
    pre = json.loads((DIR / "preregistration.json").read_text(encoding="utf-8"))
    me = hashlib.sha256(pathlib.Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if me != pre["analysis_script_sha256"]:
        raise SystemExit("FAIL-CLOSED: r6_analyze.py changed after pre-registration; "
                         "list the change in prereg_deviations.py first")
    frame = json.loads((DIR / "sampling_frame.json").read_text(encoding="utf-8"))
    if not LABELS.exists():
        print(json.dumps({"status": "awaiting_labels", "n_rows": len(frame)}))
        return 3
    rows = list(csv.DictReader(LABELS.open(encoding="utf-8")))
    want = {r["work_key"] for r in frame}
    got = {r["work_key"] for r in rows if (r.get("done") or "").strip() == "1"}
    if want - got:
        raise SystemExit(f"FAIL-CLOSED: {len(want - got)} of {len(want)} rows not marked done")
    rows = [r for r in rows if r["work_key"] in want]
    out = {"meta": {"study": pre["study"], "n_rows": len(rows),
                    "labeller": pre["labeller"], "weighted": False,
                    "prereg_sha256": hashlib.sha256(
                        (DIR / "preregistration.json").read_bytes()).hexdigest()},
           "fields": score(rows, machine(frame))}
    (ROOT / "papers" / "studies" / "r6_numeric_accuracy.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    for f, d in out["fields"].items():
        print(f"[r6] {f}: {d['n_exact']}/{d['n_both']} exact, "
              f"human-only {d['human_only_no_card'] + d['human_only_card_null']}, "
              f"machine-only {d['machine_only']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
