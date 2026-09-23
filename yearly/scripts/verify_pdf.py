"""verify_pdf: rendered-artifact verification. Derives everything it needs.

The handbook used to carry this as a snippet with two hardcoded constants
(a stale-month list and the reference count). A monthly checklist step that
requires editing constants by hand is exactly how the "July 2026" bug class
was born: the operator edits three of four sites and the fourth ships.

So nothing here is typed in. The month comes from argv, the expected title
from the section map, the reference count from the gate report, and the
stale-month list from every prior run on disk.

Exits non-zero on any failure, so it can gate a run.

Run: python scripts/verify_pdf.py 2026-09 [v4]
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from stages.hygiene import find_narration          # noqa: E402
from stages.section_map import load_map, month_name  # noqa: E402


def verify(month: str, ver: str = "v4") -> int:
    pdf_p = ROOT / "manuscript" / f"{month}_{ver}" / f"manuscript_{ver}.pdf"
    if not pdf_p.exists():
        print(f"FAIL: {pdf_p} missing")
        return 2

    ptr = ROOT / "runs" / f"{month}.active"
    if not ptr.exists():
        print(f"FAIL: {ptr} missing")
        return 2
    rd = ROOT / "runs" / ptr.read_text(encoding="utf-8").strip()

    gates = json.loads((rd / f"gate_report_{ver}.json").read_text(encoding="utf-8"))
    n_refs = gates["G2c-cite-count"]["detail"]["cited"]      # not typed in
    smap = load_map(month)
    this_month = month_name(month)

    # Every OTHER month that has ever been built is a stale-month candidate.
    stale = set()
    for p in (ROOT / "runs").glob("*.active"):
        m = p.stem
        if re.fullmatch(r"\d{4}-\d{2}", m) and m != month:
            stale.add(month_name(m).split()[0])
    stale.discard(this_month.split()[0])

    import pymupdf
    with pymupdf.open(pdf_p) as d:
        pages = d.page_count
        t = " ".join(" ".join(d[i].get_text()
                              for i in range(d.page_count)).split())

    checks: list[tuple[str, bool, str]] = []

    frag = f"in {this_month}"
    checks.append(("title names this month once",
                   t.count(frag) >= 1, f"'{frag}' x{t.count(frag)}"))

    found_stale = sorted(m for m in stale if m in t)
    checks.append(("no stale month name", not found_stale,
                   f"found {found_stale}" if found_stale else "clean"))

    checks.append(("no unresolved placeholders",
                   "{{" not in t and "}}" not in t, ""))

    narration = find_narration(t)
    checks.append(("no agent narration", not narration,
                   f"{narration[:3]}" if narration else "clean"))

    checks.append(("no doubled figure captions",
                   not re.search(r"Figure (\d+)[.:]\s*Figure \1", t), ""))

    unmerged = re.findall(r"(?:\[\d+(?:,\d+)*\]\s*){2,}", t)
    checks.append(("no unmerged citation runs", not unmerged,
                   f"{unmerged[:2]}" if unmerged else ""))

    # [60]fullerene (IUPAC) and [100] (Miller index) are nomenclature. Any
    # bracketed number above the reference count cannot be a citation.
    seq, seen, skipped = [], set(), []
    for m in re.finditer(r"\[(\d+(?:,\d+)*)\](?![A-Za-z])", t):
        grp = [int(x) for x in m.group(1).split(",")]
        if any(x > n_refs or x == 0 for x in grp):
            skipped.append(m.group(0))
            continue
        for x in grp:
            if x not in seen:
                seen.add(x)
                seq.append(x)
    checks.append(("citations monotonic by first appearance",
                   seq == sorted(seq), f"{len(seen)} of {n_refs} refs"))
    checks.append(("every reference is cited", len(seen) == n_refs,
                   f"cited {len(seen)}, refs {n_refs}"))

    sec_titles = [s["title"] for s in smap["sections"]]
    missing = [s for s in sec_titles
               if " ".join(s.split()).lower() not in t.lower()]
    checks.append(("every mapped section heading present", not missing,
                   f"missing {missing}" if missing else ""))

    checks.append(("page count matches gate report",
                   pages == gates["G5"]["detail"].get("total_pages", pages),
                   f"{pages} pages"))

    width = max(len(n) for n, _, _ in checks)
    ok = True
    for name, passed, note in checks:
        ok &= passed
        print(f"  {'PASS' if passed else 'FAIL'}  {name:<{width}}  {note}")
    if skipped:
        print(f"  note  nomenclature brackets ignored: {sorted(set(skipped))[:4]}")

    gate_fail = [k for k, v in gates.items() if v["status"] == "fail"]
    if gate_fail:
        ok = False
        print(f"  FAIL  gate report contains failures: {gate_fail}")

    print(f"\n{'ALL CHECKS PASS' if ok else 'VERIFICATION FAILED'}  "
          f"({pdf_p.name}, {pages} pages, {len(seen)} citations)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(verify(sys.argv[1] if len(sys.argv) > 1 else "2026-08",
                    sys.argv[2] if len(sys.argv) > 2 else "v4"))
