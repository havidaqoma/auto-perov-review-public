"""Record the operator's confirmation of the R3/R5 hand verdicts.

Reads papers/studies/verdict_confirmations.csv (exported from
verdict_review.html by the operator) and writes verdict_confirmation.json.
Fails closed if any value is unanswered or the CSV does not match the
current review files. A disagreement is resolved only by an operator ruling
in verdict_rulings.json that names it (triggered_by); any other disagreement
is listed and exits 1, and the verdict must be corrected and the page re-done.

    python papers/scripts/studies/confirm_verdicts.py "Havid Aqoma"
"""
import csv
import datetime
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "papers" / "scripts"))
from studies.verdict_review_build import REVIEWS, rows  # noqa: E402

ST = ROOT / "papers" / "studies"
CSV = ST / "verdict_confirmations.csv"
OUT = ST / "verdict_confirmation.json"
RULINGS = ST / "verdict_rulings.json"


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit('usage: confirm_verdicts.py "Your Name"')
    if not CSV.exists():
        raise SystemExit(f"FAIL-CLOSED: {CSV.relative_to(ROOT)} not found. "
                         "Open verdict_review.html, answer, press Export CSV.")
    want = {r["id"] for r in rows()}
    got = {r["id"]: r for r in csv.DictReader(open(CSV, encoding="utf-8",
                                                   newline=""))}
    if set(got) != want:
        raise SystemExit("FAIL-CLOSED: the CSV does not match the current "
                         "review files; rebuild the page and answer again.")
    blank = [i for i, r in got.items() if r["answer"] not in ("agree", "disagree")]
    if blank:
        raise SystemExit(f"FAIL-CLOSED: {len(blank)} value(s) unanswered.")
    no = [(i, got[i]["note"]) for i in sorted(got) if got[i]["answer"] == "disagree"]
    ruled = set()
    if RULINGS.exists():
        rl = json.loads(RULINGS.read_text(encoding="utf-8"))
        ruled = {rl["triggered_by"]} if rl.get("ruled_by") else set()
    open_ = [(i, n) for i, n in no if i not in ruled]
    rec = {
        "confirmed_by": sys.argv[1],
        "date": datetime.date.today().isoformat(),
        "n_values": len(got),
        "n_agree": len(got) - len(no),
        "n_disagree": len(no),
        "disagreements": [{"id": i, "note": n,
                           "resolved_by": ("verdict_rulings.json" if i in ruled else None)}
                          for i, n in no],
        "n_unresolved": len(open_),
        "review_files_sha256": {
            f: hashlib.sha256((ST / f).read_bytes()).hexdigest()
            for _, f, _ in REVIEWS},
    }
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"{rec['n_agree']} of {rec['n_values']} agreed -> "
          f"{OUT.relative_to(ROOT)}")
    for i, n in no:
        print(f"  DISAGREE {i}: {n}" + ("  [resolved by ruling]" if i in ruled else ""))
    return 1 if open_ else 0


if __name__ == "__main__":
    sys.exit(main())
