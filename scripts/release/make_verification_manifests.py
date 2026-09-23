"""make_verification_manifests: record what the shipped artifacts ACTUALLY say.

`reproduce.py` asserts that every gate report still carries the verdict it
carried when the issue shipped, and that every PDF still has its recorded page
count. Those expectations have to come from somewhere. Writing them by hand
would reintroduce exactly the defect the handbook's §4.4 warns about: a
hardcoded constant that drifts from the artifact.

So they are measured. This script reads the built public tree, records what it
finds, and writes two manifests into `<tree>/verification/`. It never asserts
that a gate passed: it records the verdict, pass or fail, so a third party can
see that two monthly issues shipped with a failing G8-novelty and the yearly
issue shipped with G8 in cold-start. Hiding that would make the repository a
worse record of the work than the paper is.

Run AFTER build_public_tree.py, BEFORE pushing.

Usage
-----
    python scripts/release/make_verification_manifests.py --tree ../auto-perov-review-public
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys

# Gate verdicts that are NOT "pass" and are known, accepted, and explained.
# A verdict appearing here is a statement about the shipped record, not a
# waiver: reproduce.py still fails if the verdict CHANGES.
KNOWN_NON_PASS: dict[str, str] = {
    "G8-novelty:fail": (
        "Section-vs-prior-issue similarity exceeded no threshold; the gate "
        "fired on >=12-word shingle reuse (n_shared_shingles: 2), both "
        "instances being the review's own framing sentence carried over from "
        "the prior issue. Every per-section ratio was far under the 0.25 "
        "bound (worst 0.061) and the abstract ratio was 0.014 against 0.30. "
        "It shipped as a recorded failure rather than being waived, because "
        "handbook 6.1 forbids widening a gate to make output pass."),
    "G8-novelty:cold-start": (
        "First yearly issue in its repository. There is no prior yearly "
        "issue to measure similarity against, so the gate reports cold-start "
        "rather than a pass it cannot justify."),
    "G8-novelty:skip": (
        "First issue on record for that cadence, so there is no prior issue "
        "to measure section similarity against. The gate reports skip rather "
        "than a pass it never computed, which is the same distinction "
        "handbook 6 draws for G3d."),
    "G5:fail": (
        "The 2026-07 issue measured total_pages 13 against total_band [8, 10] "
        "while content_pages 6.6 sat inside content_band [6, 7]. The band was "
        "written for the v1 two-column layout and was never migrated when v3 "
        "moved to single column, 11pt and ~80 references, so the gate was "
        "comparing a v3 artifact to a v1 expectation. The recorded fix was to "
        "add paper_v3 bands (content [8, 11], total [12, 17]) bracketed on "
        "the measured artifact, NOT to widen the original band; the failing "
        "verdict on this older report is left standing because rewriting a "
        "shipped gate report to look clean is the behaviour handbook 6.1 "
        "forbids."),
    "G3d-illumination:skip": (
        "The illumination classifier is part of the period layer. A build "
        "without that layer reports the gate skipped rather than passing a "
        "check it never ran."),
}


def collect_gate_reports(tree: pathlib.Path) -> dict:
    reports: dict[str, dict] = {}
    unexplained: list[str] = []
    for p in sorted(tree.rglob("gate_report*.json")):
        rel = p.relative_to(tree).as_posix()
        # Only the reports that back a SHIPPED issue. A run directory holds
        # intermediate versions (v2, v3) that were superseded; recording those
        # as expectations would freeze superseded work into the contract.
        if "/data/" in rel:
            continue
        try:
            rep = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(f"  skip {rel}: {e}", file=sys.stderr)
            continue
        if not isinstance(rep, dict) or not rep:
            continue
        statuses = {k: (v.get("status") if isinstance(v, dict) else v)
                    for k, v in rep.items()}
        notes = {}
        for gate, st in statuses.items():
            if st == "pass":
                continue
            key = f"{gate}:{st}"
            if key in KNOWN_NON_PASS:
                notes[gate] = KNOWN_NON_PASS[key]
            else:
                unexplained.append(f"{rel} -> {key}")
        reports[rel] = {"gates": len(statuses), "statuses": statuses,
                        "non_pass_explained": notes}
    return {"reports": reports, "unexplained": unexplained}


def collect_pdfs(tree: pathlib.Path) -> dict:
    import pymupdf
    pdfs: dict[str, dict] = {}
    for p in sorted(tree.rglob("*.pdf")):
        rel = p.relative_to(tree).as_posix()
        # Figures are verified by the figure checks, not by page count.
        if "/fig/" in rel or "/figures/" in rel:
            continue
        try:
            doc = pymupdf.open(p)
        except Exception as e:                       # noqa: BLE001
            print(f"  skip {rel}: {e}", file=sys.stderr)
            continue
        first = doc[0].get_text() if doc.page_count else ""
        # Anchor on the year, which every title block carries and which no
        # font-subsetting change can alter. Deliberately NOT the full title:
        # a title is prose and prose gets revised, so pinning it here would
        # make a legitimate edit look like a reproducibility failure.
        needles = [y for y in ("2025", "2026") if y in first[:1200]][:1]
        pdfs[rel] = {"pages": doc.page_count, "first_page_contains": needles}
        doc.close()
    return {"pdfs": pdfs}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", required=True)
    a = ap.parse_args()
    tree = pathlib.Path(a.tree).resolve()
    if not tree.is_dir():
        print(f"FAIL: {tree} is not a directory", file=sys.stderr)
        return 2

    out = tree / "verification"
    out.mkdir(exist_ok=True)
    stamp = dt.date.today().isoformat()

    print("[gates] scanning")
    g = collect_gate_reports(tree)
    (out / "gate_verdicts.json").write_text(json.dumps({
        "note": ("Gate verdicts as recorded by the builds that produced the "
                 "shipped issues, measured from the reports in this tree on "
                 f"{stamp}. reproduce.py fails if any verdict CHANGES. "
                 "Non-pass verdicts are part of the record and are explained "
                 "per gate; see non_pass_explained."),
        "recorded": stamp,
        "reports": g["reports"],
    }, indent=1) + "\n", encoding="utf-8")
    npass = sum(1 for r in g["reports"].values()
                for s in r["statuses"].values() if s != "pass")
    print(f"[gates] {len(g['reports'])} reports, {npass} non-pass verdicts")
    if g["unexplained"]:
        print("[gates] UNEXPLAINED non-pass verdicts (add them to "
              "KNOWN_NON_PASS with a reason, do not delete them):",
              file=sys.stderr)
        for u in g["unexplained"]:
            print(f"        {u}", file=sys.stderr)
        return 1

    print("[pdfs] opening")
    p = collect_pdfs(tree)
    (out / "pdf_inventory.json").write_text(json.dumps({
        "note": ("Page count and a year anchor for every shipped manuscript "
                 f"and supplement, measured on {stamp}. Byte-identical "
                 "rebuilds are NOT expected: tectonic embeds a build "
                 "timestamp and subsets fonts. Page count plus gates passing "
                 "is the reproduction criterion."),
        "recorded": stamp,
        "pdfs": p["pdfs"],
    }, indent=1) + "\n", encoding="utf-8")
    print(f"[pdfs] {len(p['pdfs'])} documents, "
          f"{sum(v['pages'] for v in p['pdfs'].values())} pages total")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
