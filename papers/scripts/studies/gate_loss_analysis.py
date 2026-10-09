"""Why did the gate discard correct values? (retention cost of failing closed)

In the gate ablation (ablation_gate.py) the verification layer removed
grounded values: numbers that do appear in their own abstract, but whose
verbatim anchor failed the guard. A reviewer asked how large that loss is per
field and what causes it. This script answers both from the ablation's own
cached model outputs, with no new model calls.

For every value that is grounded but not shipped by the fixed guard, the
failed anchor is compared with the source abstract (same 2,600-character
window the extractor saw) and assigned ONE cause, by deterministic rules
tested in this order:

  typography   anchor matches once Unicode (NFKC), dashes, quotes, spaces,
               and case are unified; the verifier was stricter than needed.
               The step that is actually needed is recorded per row.
  elided       anchor contains an ellipsis or joins pieces that are each
               verbatim but not adjacent in the source
  outside_cut  anchor is verbatim in the full abstract but lies beyond the
               window the extractor was given
  paraphrase   none of the above: the model reworded the source
  not_object   the field was not returned in the required object form

No rule depends on a model, and the per-row output records the evidence for
each assignment, so the counts can be re-derived by hand.

Counterfactual: the guard is re-run on ALL ablation values with hyphen and
dash variants mapped to an ASCII hyphen on both sides. The script reports how
many correct values that recovers and how many ungrounded values it would let
through, so a proposed fix is judged on both sides of the trade.

Outputs papers/studies/gate_loss.json (per-field loss + cause counts + rows).

  python papers/scripts/studies/gate_loss_analysis.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import unicodedata

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "scripts"))
import studies.ablation_gate as ag  # noqa: E402
from studies.study_common import ROOT, wilson  # noqa: E402

OUT = ROOT / "papers" / "studies" / "gate_loss.json"
ABL = ROOT / "papers" / "studies" / "ablation_gate.json"
DASH = dict.fromkeys(map(ord, "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"), "-")
QUOTE = dict.fromkeys(map(ord, "\u2018\u2019\u201a\u201b\u2032"), "'") | \
    dict.fromkeys(map(ord, "\u201c\u201d\u201e\u2033"), '"')


def loose(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "").translate(DASH).translate(QUOTE)
    return re.sub(r"\s+", " ", s).strip().lower()


def pieces_verbatim(anchor: str, src: str) -> bool:
    parts = [p.strip(" ,;:") for p in re.split(r"\.{3}|\u2026|\s-\s|;", anchor)]
    parts = [p for p in parts if len(p.split()) >= 2]
    if len(parts) < 2:
        return False
    return all(loose(p) in loose(src) for p in parts)


def dash_only(s: str) -> str:
    return (s or "").translate(DASH)


def needed_step(a: str, src: str) -> str:
    base = lambda t: re.sub(r"\s+", " ", t).strip().lower()  # noqa: E731
    if base(dash_only(a)) in base(dash_only(src)):
        return "dash"
    if base(a.translate(QUOTE)) in base(src.translate(QUOTE)):
        return "quote"
    return "nfkc_or_combined"


def cause(fld, src_cut: str, src_full: str) -> tuple[str, str]:
    if not isinstance(fld, dict):
        return "not_object", f"field returned as {type(fld).__name__}"
    a = fld.get("anchor") or ""
    if loose(a) and loose(a) in loose(src_cut):
        return "typography", "needs: " + needed_step(a, src_cut)
    if "..." in a or "\u2026" in a or pieces_verbatim(a, src_cut):
        return "elided", "pieces verbatim, not contiguous in the source"
    if loose(a) and loose(a) in loose(src_full):
        return "outside_cut", "verbatim only beyond the extractor's input window"
    return "paraphrase", "reworded; not recoverable by normalisation"


def main() -> int:
    abl = json.loads(ABL.read_text(encoding="utf-8"))
    lost_keys = {(r["work_key"], r["field"]) for r in abl["rows"]
                 if r["grounded"] and not r["shipped_fixed_guard"]}
    kept = {}
    for r in abl["rows"]:
        if r["grounded"]:
            k = kept.setdefault(r["field"], [0, 0])
            k[0] += 1
            k[1] += 0 if r["shipped_fixed_guard"] else 1
    _pool, abst, model = ag.load_pool()
    rows = []
    for f in sorted(ag.RAW_DIR.glob("batch_[0-9][0-9][0-9].json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        got = {int(o["i"]): o for o in ag.s09.parse_array(rec["raw"])
               if isinstance(o, dict) and str(o.get("i", "")).isdigit()}
        for n, wk in enumerate(rec["work_keys"]):
            o = got.get(n) or {}
            for fld in ag.FIELDS:
                if (wk, fld) not in lost_keys:
                    continue
                full = abst[wk.lower()]
                c, why = cause(o.get(fld), full[:ag.ABSTRACT_CUT], full)
                raw = o.get(fld)
                rows.append({"work_key": wk, "field": fld,
                             "value": raw.get("value") if isinstance(raw, dict) else raw,
                             "anchor": raw.get("anchor") if isinstance(raw, dict) else None,
                             "cause": c, "evidence": why})
    if len(rows) != len(lost_keys):
        raise SystemExit(f"FAIL-CLOSED: classified {len(rows)} of {len(lost_keys)} lost values; "
                         "the cached batches do not match ablation_gate.json")
    # counterfactual guard with dash variants unified on both sides
    cf_kept = cf_bad = 0
    for f in sorted(ag.RAW_DIR.glob("batch_[0-9][0-9][0-9].json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        got = {int(o["i"]): o for o in ag.s09.parse_array(rec["raw"])
               if isinstance(o, dict) and str(o.get("i", "")).isdigit()}
        for n, wk in enumerate(rec["work_keys"]):
            o = got.get(n)
            if o is None:
                continue
            src = abst[wk.lower()][:ag.ABSTRACT_CUT]
            for fld in ag.FIELDS:
                raw = o.get(fld)
                v = ag._value(raw)
                if v is None:
                    continue
                f2 = dict(raw, anchor=dash_only(raw.get("anchor"))) if isinstance(raw, dict) else raw
                shipped, _ = ag.guard(f2, dash_only(src), ag._fixed_num_in)
                if shipped is None:
                    continue
                if ag.number_present(v, src):
                    cf_kept += 1
                else:
                    cf_bad += 1
    causes = {}
    for r in rows:
        causes[r["cause"]] = causes.get(r["cause"], 0) + 1
    per_field = {fld: {"grounded": g, "lost": l, "lost_rate": round(l / g, 4) if g else 0.0,
                       "lost_ci95": wilson(l, g)} for fld, (g, l) in sorted(kept.items())}
    meta = {"source": "papers/studies/ablation_gate.json + runs/studies/ablation_raw",
            "model": model, "n_lost": len(rows), "by_cause": causes,
            "per_field": per_field,
            "recoverable_by_normalisation": causes.get("typography", 0),
            "steps_needed": {k: sum(1 for r in rows if r["evidence"] == "needs: " + k)
                             for k in ("dash", "quote", "nfkc_or_combined")},
            "counterfactual_dash_guard": {
                "grounded_kept": cf_kept,
                "grounded_lost": sum(g for g, _ in kept.values()) - cf_kept,
                "ungrounded_admitted": cf_bad,
                "rule": "hyphen and dash variants mapped to ASCII hyphen in anchor and abstract"},
            "note": "loss is measured on grounded values only; the gate's protective "
                    "effect is reported separately in ablation_gate.json"}
    OUT.write_text(json.dumps({"meta": meta, "rows": rows}, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    print(json.dumps(meta, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
