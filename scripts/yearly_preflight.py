"""yearly_preflight: deterministic coverage evidence for a yearly build.

YEARLY 5.4 (G11-coverage) exists because a yearly issue built from a partial
year is internally consistent, passes every other gate, and misstates its own
scope. Nothing else can see it.

This script produces the EVIDENCE for that gate before any model is invoked,
so a blocked year is a computed fact with a machine-readable record rather
than an operator's impression. It reads only; it writes one JSON report.

Every month is resolved through runs/<YYYY-MM>.active, never by constructing
a path (YEARLY 1.4): a relocated run dir once produced 0 venues from a
655-work corpus with no crash.

Usage
-----
    python scripts/yearly_preflight.py 2025

Exit code is non-zero when the year cannot be built, so this belongs in the
yearly checklist as a gate rather than a suggestion.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"


def resolve_month(month: str) -> dict:
    """Resolve one month through its .active pointer and report what is there.

    A missing pointer and an empty run dir must be distinguishable: they are
    different failures and they need different fixes.
    """
    rec: dict = {
        "month": month,
        "active_pointer": False,
        "run_id": None,
        "run_dir_exists": False,
        "corpus_n": 0,
        "cards_n": 0,
        "anchor_verified": False,
        "status": "MISSING",
    }
    ptr = RUNS / f"{month}.active"
    if not ptr.exists():
        return rec
    rec["active_pointer"] = True
    run_id = ptr.read_text(encoding="utf-8").strip()
    rec["run_id"] = run_id or None
    if not run_id:
        rec["status"] = "EMPTY_POINTER"
        return rec

    d = RUNS / run_id
    rec["run_dir_exists"] = d.is_dir()
    if not d.is_dir():
        # The pointer names a directory that is not there. This is the
        # relocated-run-dir failure, and it is NOT the same as a missing
        # month: the month was built and then lost.
        rec["status"] = "DANGLING_POINTER"
        return rec

    corpus = d / "05_corpus.jsonl"
    cards = d / "claim_cards.jsonl"
    if corpus.exists():
        rec["corpus_n"] = sum(
            1 for ln in corpus.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        )
    if cards.exists():
        rec["cards_n"] = sum(
            1 for ln in cards.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        )
    # verify_anchors.py writes its marker here. A month that was never
    # anchor-verified contaminates the year INVISIBLY, because the yearly
    # path inherits cards and never re-runs the guards (YEARLY 10).
    for cand in ("verify_anchors.done", "anchors_verified.json",
                 "09_cards.done"):
        if (d / cand).exists():
            rec["anchor_verified"] = True
            break

    # A zero is a bug until proven otherwise (monthly 7.1). A run dir that
    # exists but carries no cards is the silent-zero class.
    if rec["cards_n"] == 0 or rec["corpus_n"] == 0:
        rec["status"] = "SILENT_ZERO"
    elif not rec["anchor_verified"]:
        rec["status"] = "UNVERIFIED"
    else:
        rec["status"] = "OK"
    return rec


def preflight(year: str) -> tuple[dict, int]:
    months = [f"{year}-{m:02d}" for m in range(1, 13)]
    recs = [resolve_month(m) for m in months]
    ok = [r for r in recs if r["status"] == "OK"]
    report = {
        "year": year,
        "n_months_expected": 12,
        "n_months_ok": len(ok),
        "months": recs,
        "missing": [r["month"] for r in recs if r["status"] == "MISSING"],
        "problem_months": [
            {"month": r["month"], "status": r["status"]}
            for r in recs if r["status"] not in ("OK", "MISSING")
        ],
        "corpus_n_total": sum(r["corpus_n"] for r in ok),
        "cards_n_total": sum(r["cards_n"] for r in ok),
        "buildable": len(ok) == 12,
    }
    report["verdict"] = (
        "BUILDABLE" if report["buildable"]
        else f"BLOCKED: {len(ok)}/12 months usable"
    )
    return report, (0 if report["buildable"] else 1)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    year = argv[1]
    if not (year.isdigit() and len(year) == 4):
        print(f"expected a 4-digit year, got {year!r}")
        return 2

    report, rc = preflight(year)
    out = RUNS / f"{year}_yearly_preflight.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"YEARLY PREFLIGHT {year}")
    print(f"  verdict         {report['verdict']}")
    print(f"  months usable   {report['n_months_ok']}/12")
    print(f"  corpus total    {report['corpus_n_total']}")
    print(f"  cards total     {report['cards_n_total']}")
    if report["missing"]:
        print(f"  MISSING ({len(report['missing'])}): "
              f"{', '.join(report['missing'])}")
    for p in report["problem_months"]:
        print(f"  ! {p['month']}: {p['status']}")
    print(f"  report          {out.relative_to(ROOT)}")
    if rc:
        print("\nA yearly issue is the union of twelve VERIFIED monthly runs "
              "(YEARLY 1.3). Re-harvesting an old month LOSES it rather than "
              "recovering it, so the missing months cannot be back-filled by "
              "running the chain over old literature.")
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
