"""H1 backfill driver: run the PROVEN monthly chain for the missing months.

This edits nothing on the monthly path. It shells the existing stage scripts in
the documented order (handbook 1.1) and stops the whole backfill on the first
non-zero exit, because a partial month silently contributing zero cards to a
six-month union is the silent-zero class (handbook 7.1).

Every stage's .done payload is re-read afterwards and a zero count is treated as
a failure even when the stage exited 0.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
STAGES = ROOT / "scripts" / "stages"

CHAIN = [
    ("01", STAGES / "s01_harvest.py"),
    ("02_06", STAGES / "s02_06.py"),
    ("04_10", STAGES / "s04_10.py"),
    ("09", STAGES / "s09_cards.py"),
]
VERIFY = ROOT / "scripts" / "verify_anchors.py"


def sh(script: pathlib.Path, month: str) -> int:
    cmd = [sys.executable, str(script), month]
    print(f"\n=== {time.strftime('%H:%M:%S')}  {script.name} {month} ===", flush=True)
    return subprocess.call(cmd, cwd=str(ROOT))


def active_run(month: str) -> pathlib.Path | None:
    p = ROOT / "runs" / f"{month}.active"
    if not p.exists():
        return None
    return ROOT / "runs" / p.read_text(encoding="utf-8").strip()


# Counts that CANNOT legitimately be zero: a zero here means a stage produced
# nothing and reported success (handbook 7.1).
#
# The complement matters just as much. `n_review`, `n_retracted`, `n_preprint`
# and `n_dropped` are legitimately zero all the time -- February 2026 published
# no review-type papers, and an earlier version of this checker aborted a fully
# verified month (131 cards, 475/475 verbatim anchors) over `n_review=0`.
# That is the 7.3 class: the check disagreed with the artifact and the CHECK was
# wrong. Enumerate what must be positive; never assume every counter must be.
MUST_BE_POSITIVE = {
    "n",              # 02_normalize: works normalised
    "n_corpus",       # 05_dedupe: corpus after dedupe
    "n_kept",         # 06_label: works surviving the scope filter
    "n_distinct",     # 04_venues: distinct venues
    "n_eligible",     # 08_select: selection pool
    "n_depth",        # 08_select: the depth tier itself
    "n_cards",        # 09_cards: extraction records
    "with_abstract",  # no abstracts means nothing can be extracted
}


def zero_check(month: str) -> list[str]:
    """Re-read every .done payload; a zero in a REQUIRED count is a bug."""
    rd = active_run(month)
    if rd is None or not rd.exists():
        return [f"{month}: no active run dir"]
    bad = []
    for m in sorted(rd.glob("*.done")):
        try:
            payload = json.loads(m.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            bad.append(f"{month}/{m.name}: unreadable ({e})")
            continue
        for k, v in payload.items():
            if k in MUST_BE_POSITIVE and isinstance(v, int) and v == 0:
                bad.append(f"{month}/{m.name}: {k}=0")
    return bad


def main(months: list[str]) -> int:
    t0 = time.time()
    for month in months:
        for _, script in CHAIN:
            rc = sh(script, month)
            if rc != 0:
                print(f"ABORT: {script.name} {month} exited {rc}")
                return rc
        rc = sh(VERIFY, month)
        if rc != 0:
            print(f"ABORT: verify_anchors {month} exited {rc}")
            return rc
        bad = zero_check(month)
        if bad:
            print("ABORT: silent zero detected:\n  " + "\n  ".join(bad))
            return 2
        rd = active_run(month)
        print(f"OK {month} -> {rd.name if rd else '?'}  ({(time.time()-t0)/60:.1f} min elapsed)")
    print(f"\nBACKFILL COMPLETE: {len(months)} months in {(time.time()-t0)/60:.1f} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
