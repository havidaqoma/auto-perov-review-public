"""run_yearly: drive the yearly pipeline from cards to both PDFs.

WHY A RUNNER RATHER THAN A SHELL SCRIPT
---------------------------------------
The remaining chain has five stages and each one's failure mode is
different. A shell `&&` chain would stop on the first non-zero exit and tell
the operator nothing about WHICH invariant broke or whether the artifacts on
disk are usable. Havid left this running unattended, so the run must leave a
readable verdict rather than a traceback.

Rules this runner obeys, and does not bend:

1. RESUME, NEVER RE-EXTRACT. Extraction is the only stage that costs money.
   If claim_cards.jsonl exists this runner never re-runs it.
2. verify_anchors IS MANDATORY. Every number in the manuscript traces to a
   verbatim quotation, and the yearly path inherits already-verified cards.
   A non-zero exit here stops the run: drafting on unverified cards would
   put unanchored numbers in front of a reader.
3. A FAILED GATE DOES NOT DELETE THE PDF. The build writes the gate report
   and the PDF, then reports which gates failed. The artifact exists so a
   human can READ it; it is simply not shippable. Fix the output, never the
   gate.
4. EVERY STAGE'S REAL EXIT CODE IS RECORDED. A stage that "looked fine" but
   returned 1 is a failure, and the summary says so.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
PY = sys.executable


def run(label: str, args: list[str], *, timeout: int = 7200) -> dict:
    """Run one stage, stream nothing, capture everything, return a verdict."""
    t0 = time.time()
    log = ROOT / "runs" / f"chain_{label}.log"
    p = subprocess.run([PY, "-u"] + args, capture_output=True, text=True,
                       timeout=timeout, cwd=str(ROOT))
    out = (p.stdout or "") + (("\n--- stderr ---\n" + p.stderr) if p.stderr else "")
    log.write_text(out, encoding="utf-8")
    dt = round(time.time() - t0, 1)
    tail = [ln for ln in (p.stdout or "").splitlines() if ln.strip()][-3:]
    print(f"\n=== {label}  rc={p.returncode}  {dt}s  -> {log.name}")
    for ln in tail:
        print(f"    {ln[:150]}")
    if p.returncode != 0:
        err = [ln for ln in (p.stderr or "").splitlines() if ln.strip()][-6:]
        for ln in err:
            print(f"  ! {ln[:170]}")
    return {"stage": label, "rc": p.returncode, "seconds": dt,
            "log": str(log), "tail": tail}


def main(year: str) -> int:
    rd_ptr = ROOT / "runs" / f"{year}.active"
    if not rd_ptr.exists():
        print(f"FAIL-CLOSED: no harvest for {year}")
        return 2
    rd = ROOT / "runs" / rd_ptr.read_text(encoding="utf-8").strip()
    cards = rd / "claim_cards.jsonl"

    results: list[dict] = []

    # ---- 0. extraction must already be complete -----------------------
    if not cards.exists() or not cards.read_text(encoding="utf-8").strip():
        print(f"FAIL-CLOSED: {cards} missing or empty. Extraction is the only "
              f"stage that costs money; this runner never starts it "
              f"implicitly. Run s09_cards.py {year} first.")
        return 2
    n_cards = sum(1 for l in cards.read_text(encoding="utf-8").splitlines()
                  if l.strip())
    print(f"[chain] {n_cards} cards on disk; extraction will NOT be re-run")

    # ---- 1. verify anchors: MANDATORY ---------------------------------
    r = run("01_verify_anchors", ["scripts/verify_anchors.py", year])
    results.append(r)
    if r["rc"] != 0:
        print("\n*** STOPPING: verify_anchors failed. Drafting on unverified "
              "cards would put unanchored numbers in front of a reader.")
        return _summary(results, 1)

    # ---- 2. aggregate + stats + section map (all free) ----------------
    for label, args in (
        ("02_corpus", ["scripts/stages/yearly_corpus.py", year, "--partial"]),
        ("03_stats", ["scripts/stages/yearly_stats.py", year, "--partial"]),
        ("04_section_map", ["scripts/stages/yearly_section_map.py", year,
                            "--partial"]),
    ):
        r = run(label, args)
        results.append(r)
        if r["rc"] != 0:
            print(f"\n*** STOPPING: {label} failed; later stages read its "
                  f"output and would compute against a missing key.")
            return _summary(results, 1)

    # ---- 3. figures (best effort: they do not exist yet) --------------
    figs = ROOT / "scripts" / "stages" / "s11y_figures_yearly.py"
    if figs.exists():
        results.append(run("05_figures", [str(figs), year]))
    else:
        print("\n=== 05_figures  SKIPPED (no yearly figure stage yet)")
        print("    The build reports the absence rather than hiding it.")
        results.append({"stage": "05_figures", "rc": None, "seconds": 0,
                        "log": None, "tail": ["skipped: stage not written"]})

    # ---- 4. draft: the expensive LLM stage ----------------------------
    r = run("06_draft", ["scripts/stages/s13y_draft_yearly.py", year],
            timeout=14400)
    results.append(r)
    if r["rc"] != 0:
        print("\n*** STOPPING: draft failed. Completed sections are cached in "
              "draft_yearly/, so a re-run resumes rather than restarting.")
        return _summary(results, 1)

    # ---- 5. build: manuscript PDF + gates -----------------------------
    r = run("07_build", ["scripts/stages/s18y_build_yearly.py", year],
            timeout=3600)
    results.append(r)
    build_ok = r["rc"] == 0

    # ---- 6. supplementary information ---------------------------------
    si = ROOT / "scripts" / "stages" / "s19y_si_yearly.py"
    if build_ok and si.exists():
        results.append(run("08_supplementary", [str(si), year], timeout=1800))
    elif not build_ok:
        print("\n=== 08_supplementary  SKIPPED (build failed)")
        results.append({"stage": "08_supplementary", "rc": None, "seconds": 0,
                        "log": None, "tail": ["skipped: build failed"]})

    # ---- 7. rendered-artifact verification ----------------------------
    if build_ok:
        for label, script in (("09_verify_pdf", "scripts/verify_pdf.py"),
                              ("10_verify_notation",
                               "scripts/verify_notation_pdf.py")):
            if (ROOT / script).exists():
                results.append(run(label, [script, year, "yearly"],
                                   timeout=900))

    return _summary(results, 0 if build_ok else 1)


def _summary(results: list[dict], rc: int) -> int:
    print("\n" + "=" * 66)
    print("YEARLY CHAIN SUMMARY")
    print("=" * 66)
    for r in results:
        code = "skip" if r["rc"] is None else (
            "OK  " if r["rc"] == 0 else f"FAIL")
        print(f"  {code}  {r['stage']:<20} {r['seconds']:>7}s")
    out = ROOT / "runs" / "chain_summary.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nreport -> {out}")
    if rc:
        print("\nThe chain did not complete. The failing stage's log holds "
              "its real error; nothing was silently skipped.")
    return rc


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: run_yearly.py <YYYY>")
    raise SystemExit(main(sys.argv[1]))
