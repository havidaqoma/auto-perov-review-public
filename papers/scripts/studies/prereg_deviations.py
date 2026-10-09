"""Which pre-registered R1 analyses were NOT run, and why. Computed, not typed.

The pre-registration (papers/studies/label_sheet/preregistration.json) lists
three secondary metrics. A paper that reports only the ones that ran, without
saying the others did not, has quietly changed its plan. This script checks
each one against the artifacts and writes the result:

  numeric PCE accuracy   -> needs a human pce_value per labelled row
  intra-rater kappa      -> needs r1_relabel_filled.csv (it exists; ran)
  per-extractor-model    -> needs more than one extractor model in the
                            claim cards behind the labelled months

No model is called. Run:  python papers/scripts/studies/prereg_deviations.py
"""
import csv
import json
import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[3]
LS = ROOT / "papers" / "studies" / "label_sheet"
OUT = ROOT / "papers" / "studies" / "prereg_deviations.json"


def extractor_models(months):
    per_month = {}
    for m in months:
        act = ROOT / "runs" / f"{m}.active"
        if not act.exists():
            raise SystemExit(f"FAIL-CLOSED: {act.name} missing")
        run = ROOT / "runs" / act.read_text(encoding="utf-8").strip()
        cards = run / "claim_cards.jsonl"
        if not cards.exists():
            raise SystemExit(f"FAIL-CLOSED: {cards} missing")
        c = Counter()
        for line in cards.read_text(encoding="utf-8").splitlines():
            if line.strip():
                c[(json.loads(line).get("extractor") or {}).get("model", "UNRECORDED")] += 1
        per_month[m] = dict(c)
    return per_month


def analysis_changes(rows):
    """Changes to the registered analysis made after the labels were seen.

    A pre-registration is only worth its timestamp if every later change is
    listed. Two are on record in git: the lifetime population guard (added in
    the commit that also added the labels) and the timing of the re-label. The
    guard's effect is recomputed here, not typed.
    """
    sys.path.insert(0, str(ROOT / "papers" / "scripts"))
    sys.path.insert(0, str(ROOT / "papers" / "scripts" / "studies"))
    from label_sheet_analyze import machine_side
    mach = machine_side()
    with_card = [r for r in rows if r.get("states_t80") == "Y" and mach[r["work_key"]]["has_card"]]
    no_card = [r for r in rows if r.get("states_t80") == "Y" and not mach[r["work_key"]]["has_card"]]
    tp = sum(1 for r in with_card if mach[r["work_key"]]["card_t80"])
    return [
        {"change": "lifetime (states_t80) recall scored only on sampled papers that have a claim "
                   "card; papers without a card are excluded instead of counted as misses",
         "when": "2026-09-12 15:35 +0800, commit 165735c, the same commit that added the 100 labels",
         "registered": "precision and recall of each extractor flag vs human label, all sampled rows",
         "effect": {"n_human_yes_with_card": len(with_card), "n_human_yes_no_card": len(no_card),
                    "tp": tp,
                    "recall_with_guard": round(tp / len(with_card), 4) if with_card else None,
                    "recall_without_guard": round(tp / (len(with_card) + len(no_card)), 4)
                    if (with_card or no_card) else None},
         "status": "reported with the guard; the unguarded value is given beside it"},
        {"change": "the 20-paper re-label was done 24 minutes after the first pass, in the same "
                   "session, so it measures same-session consistency, not stability over time",
         "when": "2026-09-12 15:59 +0800, commit 024ea13",
         "registered": "intra-rater agreement (kappa) on a 20-paper re-label (timing not fixed)",
         "effect": None,
         "status": "reported as a same-session repeat; inter-rater kappa is the primary reliability figure"},
    ]


def main():
    pre = json.loads((LS / "preregistration.json").read_text(encoding="utf-8"))
    with open(LS / "r1_labels_filled.csv", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    n_pce_value = sum(1 for r in rows if (r.get("pce_value") or "").strip())
    n_states_pce = sum(1 for r in rows if r.get("states_pce") == "Y")
    relabel = (LS / "r1_relabel_filled.csv").exists()
    models = extractor_models(pre["months"])
    all_models = sorted({k for v in models.values() for k in v})

    sec = pre["secondary_metrics"]
    changes = analysis_changes(rows)
    items = [
        {"metric": sec[0], "ran": n_pce_value > 0,
         "evidence": {"rows_labelled": len(rows), "rows_states_pce_Y": n_states_pce,
                      "rows_with_human_pce_value": n_pce_value},
         "reason": None if n_pce_value else
         "the labeller filled the yes/no flags only; the pce_value column is "
         "blank in every row, so there is no human number to score against"},
        {"metric": sec[1], "ran": relabel,
         "evidence": {"r1_relabel_filled.csv": relabel},
         "reason": None if relabel else "relabel sheet not filled"},
        {"metric": sec[2], "ran": len(all_models) > 1,
         "evidence": {"extractor_models_in_labelled_months": all_models,
                      "cards_per_month": models},
         "reason": None if len(all_models) > 1 else
         f"every claim card in the labelled months was extracted by "
         f"{all_models[0] if all_models else 'no model'}; there is no second "
         f"model to compare"},
    ]
    rep = {"meta": {"preregistration": "papers/studies/label_sheet/preregistration.json",
                    "n_secondary": len(items),
                    "n_ran": sum(i["ran"] for i in items),
                    "n_not_run": sum(not i["ran"] for i in items),
                    "n_rows_with_pce_value": n_pce_value,
                    "n_rows_labelled": len(rows),
                    "n_extractor_models": len(all_models),
                    "extractor_models": all_models,
                    "n_analysis_changes_after_labels": len(changes),
                    "t80_recall_without_guard": changes[0]["effect"]["recall_without_guard"],
                    "t80_n_excluded_by_guard": changes[0]["effect"]["n_human_yes_no_card"]},
           "items": items,
           "analysis_changes_after_labels": changes}
    OUT.write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    for i in items:
        print(("RAN     " if i["ran"] else "NOT RUN ") + i["metric"]
              + ("" if i["ran"] else f"  -- {i['reason']}"))
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
