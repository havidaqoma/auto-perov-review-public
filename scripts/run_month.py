"""run_month: one-command driver for a monthly review issue (PLAN v5 T-43).

The handbook (1.1) lists the stage order as shell lines. A cron job cannot run
a list of shell lines and report honestly about it: if stage 09 fails, the
remaining lines still execute and the last one's exit code is what cron sees.
This script runs the same order in-process, stops at the first failure, and
prints a machine-checkable summary that names the stage that failed.

Design rules taken from the handbook:

  1.2  resume is the stage's own job (is_done reads the marker PAYLOAD), so
       this driver never skips a stage itself -- it always invokes it and lets
       the stage decide. A driver that duplicated resume logic would be a
       second source of truth for "done".
  0.3  the run is verified against the artifact: the PDF must exist and the
       gate report must say every gate passed. A zero exit from s18d is not
       accepted as evidence on its own.
  1.1  s19/s20/s21 take a trailing `v4`; everything else takes the month.

Usage
-----
    python scripts/run_month.py 2026-09
    python scripts/run_month.py --previous-month
    python scripts/run_month.py 2026-09 --dry-run
    python scripts/run_month.py 2026-09 --until s13d_draft_v4

Exit code is non-zero on any stage failure or any failed verification, so cron
sees a real failure instead of a cheerful log.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"
VERSION = "v4"

#: (label, path relative to ROOT, extra args after the month)
STAGES: list[tuple[str, str, list[str]]] = [
    ("s01_harvest",      "scripts/stages/s01_harvest.py",     []),
    ("s02_06",           "scripts/stages/s02_06.py",          []),
    ("s04_10",           "scripts/stages/s04_10.py",          []),
    ("s09_cards",        "scripts/stages/s09_cards.py",       []),
    ("verify_anchors",   "scripts/verify_anchors.py",         []),
    ("s11b_figures_v2",  "scripts/stages/s11b_figures_v2.py", []),
    ("s13d_draft_v4",    "scripts/stages/s13d_draft_v4.py",   []),
    ("s18d_build_v4",    "scripts/stages/s18d_build_v4.py",   []),
    ("s19_si",           "scripts/stages/s19_si.py",          [VERSION]),
    ("s20_chemrxiv",     "scripts/stages/s20_chemrxiv.py",    [VERSION]),
    ("s21_tokens",       "scripts/stages/s21_tokens.py",      [VERSION]),
]

# Stage 09 extracts ~144 abstracts through an LLM (~35 min) and 13d writes the
# whole body (~25 min); the handbook's own timings are the floor for these.
TIMEOUT_S = {
    "s01_harvest": 3600,
    "s09_cards": 10800,
    "s13d_draft_v4": 10800,
}
DEFAULT_TIMEOUT_S = 1800


def previous_month(today: dt.date | None = None) -> str:
    """The month before the current one, as YYYY-MM.

    The cron runs on day `cron_day` and builds the month that has finished,
    never the month in progress: OpenAlex is still ingesting the current month
    (P-07), so a run against it would harvest a partial corpus and pass every
    gate while misstating its own scope.
    """
    d = today or dt.date.today()
    first = d.replace(day=1)
    prev = first - dt.timedelta(days=1)
    return f"{prev.year:04d}-{prev.month:02d}"


def resolve_run_dir(month: str) -> pathlib.Path | None:
    """Follow runs/<month>.active. Never construct the path (handbook 1.2)."""
    ptr = RUNS / f"{month}.active"
    if not ptr.exists():
        return None
    d = RUNS / ptr.read_text(encoding="utf-8").strip()
    return d if d.is_dir() else None


def run_stage(label: str, rel: str, month: str, extra: list[str]) -> dict:
    script = ROOT / rel
    if not script.is_file():
        return {"stage": label, "ok": False, "rc": None,
                "error": f"missing script {rel}", "seconds": 0.0}
    cmd = [sys.executable, str(script), month, *extra]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=ROOT, text=True,
                           capture_output=True,
                           timeout=TIMEOUT_S.get(label, DEFAULT_TIMEOUT_S))
        rc, out, err = p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as e:
        rc, out, err = None, (e.stdout or ""), "TIMEOUT"
    dur = time.time() - t0
    tail = "\n".join((out or "").strip().splitlines()[-15:])
    etail = "\n".join((err or "").strip().splitlines()[-15:])
    return {"stage": label, "ok": rc == 0, "rc": rc, "seconds": round(dur, 1),
            "stdout_tail": tail, "stderr_tail": etail}


def verify_artifacts(month: str) -> tuple[bool, list[str]]:
    """Assert on what is physically on disk, not on stage exit codes (0.3)."""
    problems: list[str] = []
    rd = resolve_run_dir(month)
    if rd is None:
        return False, [f"no runs/{month}.active pointer or run dir"]

    report = rd / f"gate_report_{VERSION}.json"
    pdf = ROOT / "manuscript" / f"{month}_{VERSION}" / f"manuscript_{VERSION}.pdf"
    if not report.is_file():
        problems.append(f"missing {report.name}")
    else:
        try:
            g = json.loads(report.read_text(encoding="utf-8"))
        except Exception as e:
            problems.append(f"{report.name} unreadable: {e}")
            g = {}
        failed = _failed_gates(g)
        if failed:
            problems.append("failed gates: " + ", ".join(sorted(failed)))

    pdf = ROOT / "manuscript" / f"{month}_{VERSION}" / "manuscript.pdf"
    if not pdf.is_file():
        problems.append(f"missing {pdf}")
    elif pdf.stat().st_size < 50_000:
        problems.append(f"{pdf.name} is only {pdf.stat().st_size} bytes")

    return (not problems), problems


def _failed_gates(g: dict) -> list[str]:
    """Collect gate names whose recorded verdict is not a pass.

    The report shape has moved between versions, so this walks whatever is
    there rather than assuming one layout: a verifier that silently finds no
    gates would report a clean run for a broken build (0.3 corollary).
    """
    failed: list[str] = []
    seen = 0
    stack = [("", g)]
    while stack:
        prefix, node = stack.pop()
        if isinstance(node, dict):
            for k, v in node.items():
                name = f"{prefix}.{k}" if prefix else str(k)
                if isinstance(v, bool) and (k.lower() in ("ok", "pass", "passed")
                                            or str(prefix).upper().startswith("G")):
                    seen += 1
                    if not v:
                        failed.append(prefix or name)
                elif isinstance(v, str) and v.upper() in ("PASS", "FAIL"):
                    seen += 1
                    if v.upper() == "FAIL":
                        failed.append(name)
                else:
                    stack.append((name, v))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                stack.append((f"{prefix}[{i}]", v))
    if seen == 0:
        failed.append("gate report contained no readable verdicts")
    return sorted(set(failed))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("month", nargs="?", help="YYYY-MM to build")
    ap.add_argument("--previous-month", action="store_true",
                    help="build the month before today (the cron default)")
    ap.add_argument("--until", metavar="STAGE",
                    help="stop after this stage label")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan and the current run state, run nothing")
    a = ap.parse_args()

    if a.previous_month:
        month = previous_month()
    elif a.month:
        month = a.month
    else:
        ap.error("give a month or --previous-month")

    try:
        y, m = month.split("-")
        assert len(y) == 4 and len(m) == 2 and 1 <= int(m) <= 12
    except Exception:
        print(f"FAIL: month must be YYYY-MM, got {month!r}")
        return 2

    plan = STAGES
    if a.until:
        labels = [s[0] for s in STAGES]
        if a.until not in labels:
            print(f"FAIL: --until {a.until} is not one of {labels}")
            return 2
        plan = STAGES[: labels.index(a.until) + 1]

    rd = resolve_run_dir(month)
    print(f"=== run_month {month} ({VERSION}) ===")
    print(f"root      : {ROOT}")
    print(f"run dir   : {rd if rd else '(not pinned yet)'}")
    print(f"stages    : {len(plan)}")

    if a.dry_run:
        for label, rel, extra in plan:
            marker = "?"
            if rd:
                cand = list(rd.glob(f"*{label.split('_', 1)[-1]}*.done"))
                marker = "done" if cand else "todo"
            print(f"  - {label:18s} {rel} {' '.join(extra)}  [{marker}]")
        ok, problems = verify_artifacts(month)
        print(f"artifact check: {'PASS' if ok else 'FAIL'}")
        for p in problems:
            print(f"  ! {p}")
        return 0

    results = []
    t0 = time.time()
    for label, rel, extra in plan:
        print(f"\n--- {label} ---", flush=True)
        r = run_stage(label, rel, month, extra)
        results.append(r)
        print(r["stdout_tail"] or "(no stdout)")
        if not r["ok"]:
            print(f"STAGE FAILED: {label} rc={r['rc']} after {r['seconds']}s")
            print(r["stderr_tail"] or "(no stderr)")
            break

    failed = [r for r in results if not r["ok"]]
    total = round(time.time() - t0, 1)

    print("\n=== summary ===")
    for r in results:
        print(f"  {'ok  ' if r['ok'] else 'FAIL'} {r['stage']:18s} {r['seconds']:>7}s")
    print(f"  total {total}s")

    if failed:
        print(f"\nRESULT: FAIL at {failed[0]['stage']} — nothing downstream ran.")
        return 1

    if a.until:
        print(f"\nRESULT: partial run to {a.until} completed (no artifact check).")
        return 0

    ok, problems = verify_artifacts(month)
    if not ok:
        print("\nRESULT: stages exited 0 but the artifact check FAILED:")
        for p in problems:
            print(f"  ! {p}")
        return 1

    rd = resolve_run_dir(month)
    pdf = ROOT / "manuscript" / f"{month}_{VERSION}" / "manuscript.pdf"
    print(f"\nRESULT: PASS — {month} {VERSION}")
    print(f"  run dir : {rd.name if rd else '?'}")
    print(f"  pdf     : {pdf}  ({pdf.stat().st_size} bytes)")
    print("  all gates in the report passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
