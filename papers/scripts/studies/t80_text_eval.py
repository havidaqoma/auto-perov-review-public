"""Score the pre-specified T80 text detector against the R1 human labels, ONCE.

stages.protocol.T80_IN_TEXT was written (commit 00f12d6, 2026-09-12) from how
the perovskite stability literature reports lifetime, before it was measured.
Its own comment says it is to be "evaluated ONCE and reported whatever it
says". It had never been scored. This script scores it on the same 100 R1
labels and writes the result, whatever it is.

Unlike the card-level T80 flag (recall 0.077, which could only be scored on
papers that had a claim card), a text detector reads every abstract, so every
labelled paper is comparable.

Caveat carried into the artifact: the pattern was committed AFTER the R1
labels (labels 165735c, 2026-09-12 15:35 +0800; pattern 00f12d6, 16:03 the
same day). The commit states it was not fitted to them; that cannot be checked
mechanically, so the artifact says so and the result is treated as in-sample.

Writes papers/studies/label_t80_text.json. No model call.
"""
import csv
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "scripts"))
from studies.study_common import active_run, wilson  # noqa: E402
from stages.protocol import t80_in_text  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[3]
SHEET = ROOT / "papers" / "studies" / "label_sheet"
OUT = ROOT / "papers" / "studies" / "label_t80_text.json"


def abstracts(months: set) -> dict:
    ab = {}
    for month in sorted(months):
        rd = active_run(month)
        for line in (rd / "private" / "02_abstracts.jsonl").read_text(
                encoding="utf-8").splitlines():
            if line.strip():
                o = json.loads(line)
                ab[o["work_key"].lower()] = o.get("abstract") or ""
    return ab


def main() -> int:
    frame = {r["work_key"]: r for r in json.loads(
        (SHEET / "sampling_frame.json").read_text(encoding="utf-8"))}
    rows = list(csv.DictReader(open(SHEET / "r1_labels_filled.csv",
                                    encoding="utf-8", newline="")))
    ab = abstracts({frame[r["work_key"]]["month"] for r in rows
                    if r["work_key"] in frame})
    tp = fp = fn = tn = unc = 0
    per = []
    for r in rows:
        wk = r["work_key"]
        if wk not in frame:
            raise SystemExit(f"FAIL-CLOSED: {wk} not in the sampling frame")
        h = (r.get("states_t80") or "").strip().upper()
        if h == "U":
            unc += 1
            continue
        if h not in ("Y", "N"):
            raise SystemExit(f"FAIL-CLOSED: {wk} has no states_t80 label")
        text = ab.get(wk.lower())
        if text is None:
            raise SystemExit(f"FAIL-CLOSED: no abstract for {wk}")
        m = t80_in_text(text)
        hy = h == "Y"
        if m and hy:
            tp += 1
        elif m and not hy:
            fp += 1
        elif hy:
            fn += 1
        else:
            tn += 1
        per.append({"work_key": wk, "human": h, "machine": m})
    n_pos, n_flag = tp + fn, tp + fp
    meta = {
        "what": "pre-specified T80 text detector (stages.protocol.T80_IN_TEXT, "
                "commit 00f12d6) scored once against the R1 states_t80 labels",
        "labels": str(SHEET.relative_to(ROOT) / "r1_labels_filled.csv"),
        "n_scored": len(per), "n_unclear": unc,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": round(tp / n_flag, 4) if n_flag else None,
        "precision_ci95": wilson(tp, n_flag) if n_flag else None,
        "recall": round(tp / n_pos, 4) if n_pos else None,
        "recall_ci95": wilson(tp, n_pos) if n_pos else None,
        "card_level_recall_for_comparison":
            "papers/studies/label_precision_recall.json states_t80 "
            "(card field, depth-tier papers only)",
        "caveat": "Pattern committed after the labels (labels 165735c "
                  "2026-09-12 15:35 +0800; pattern 00f12d6 16:03 same day); "
                  "stated as not fitted to them, which cannot be verified "
                  "mechanically. Treat as in-sample.",
    }
    OUT.write_text(json.dumps({"meta": meta, "rows": per}, indent=1,
                              ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: meta[k] for k in ("n_scored", "tp", "fp", "fn", "tn",
                                           "precision", "precision_ci95",
                                           "recall", "recall_ci95")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
