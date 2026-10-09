"""Deployment history of the monthly pipeline, read from the repository.

The manuscript once said the undercount went unnoticed "for months" and that
issues "shipped". The record says otherwise (external review, 2026-10-09), so
every history statement in the paper now comes from this file:

  * repo_start        date of the first commit
  * n_monthly_runs    monthly run pointers runs/2026-MM.active
  * issues_built      monthly editions in manuscript/ whose gate report passes
  * halfyear_built    half-year editions whose gate report passes
  * n_posted          editions with a recorded preprint DOI (ChemRxiv 10.26434)

Run: python papers/scripts/studies/deployment_history.py
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from stages.gate_policy import verdict  # noqa: E402

OUT = ROOT / "papers" / "studies" / "deployment_history.json"
PREPRINT_DOI = re.compile(r"10\.26434/chemrxiv[-.\w/]+", re.I)


def main() -> int:
    first = subprocess.run(["git", "-C", str(ROOT), "log", "--reverse", "--format=%ad",
                            "--date=short"], capture_output=True, text=True, timeout=60,
                           check=True).stdout.split()[0]
    runs = sorted(p.stem for p in (ROOT / "runs").glob("2026-[0-9][0-9].active"))
    built, half, posted = [], [], []
    for d in sorted((ROOT / "manuscript").glob("2026-*_v*")):
        reps = sorted(d.glob("gate_report_v*.json"))
        if not reps or (d / "BUILD_FAILED.json").exists():
            continue
        if not verdict(json.loads(reps[-1].read_text(encoding="utf-8")))["ok"]:
            continue
        period = d.name.split("_")[0]
        (half if "H" in period else built).append(d.name)
        for f in d.rglob("*.json"):
            if PREPRINT_DOI.search(f.read_text(encoding="utf-8", errors="ignore")):
                posted.append(d.name)
                break
    import datetime
    d0 = datetime.date.fromisoformat(first)
    rec = {"repo_start": first, "repo_start_text": f"{d0.day} {d0:%B %Y}",
           "n_monthly_runs": len(runs), "monthly_runs": runs,
           "issues_built": sorted({b.split("_")[0] for b in built}),
           "n_issues_built": len({b.split("_")[0] for b in built}),
           "editions_passing": built, "halfyear_built": half,
           "n_halfyear_built": len({h.split("_")[0] for h in half}),
           "n_posted": len(posted), "posted": posted,
           "posted_rule": "a ChemRxiv DOI (10.26434) recorded in the edition folder"}
    OUT.write_text(json.dumps(rec, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in rec.items() if not isinstance(v, list)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
