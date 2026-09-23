"""Rendered-artifact verification for ANY period: month, half-year or year.

WHY THIS EXISTS
`verify_pdf.py` is monthly-only by construction, and not by accident of
configuration. It calls `section_map.month_name(period)`, which does
`int(period.split("-")[1])`, so "2026-H1" raises ValueError and "2025" raises
IndexError. Every check it performs is period-agnostic; only the label helper
and the `<period>.active` lookup are not. So the H1 and yearly editions have
been shipping with NO equivalent of these checks, which is exactly the gap
that lets a stale period name or an unresolved placeholder reach a reader.

This does not patch `month_name`. That helper is shared by the monthly stages,
its contract really is "a month", and widening it to accept H1 would make the
monthly title rotation (`_month_index`) silently meaningless. A separate
verifier is the honest shape.

Paths are passed explicitly rather than resolved through `runs/<x>.active`,
because the H1 build writes to a FIXED directory (`h1_dir()` returns
`RUNS / EDITION`) and never consults that pointer, so following the pointer
here would risk verifying a different artifact than the one that was built.

    python scripts/verify_pdf_period.py \
        --pdf manuscript/2026-H1_v6/manuscript_v6.pdf \
        --gates runs/2026-H1/gate_report_v6.json \
        --map runs/2026-H1/12_section_map_v6.json \
        --allow "January 2026" --allow "February 2026" ...

Exits non-zero on any failure, so it can gate a run.
"""
from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from stages.hygiene import find_narration  # noqa: E402


def all_known_period_names() -> set[str]:
    """Every month name any edition on disk could be about.

    Built from the run pointers rather than typed in, for the same reason
    verify_pdf builds it that way: a hand-maintained stale list is how the
    "July 2026" bug class was born.
    """
    names = set()
    for p in (ROOT / "runs").glob("*.active"):
        m = re.fullmatch(r"(\d{4})-(\d{2})", p.stem)
        if m:
            y, mm = int(m.group(1)), int(m.group(2))
            names.add(f"{datetime.date(y, mm, 1):%B} {y}")
    return names


def verify(pdf_p: pathlib.Path, gates_p: pathlib.Path,
           map_p: pathlib.Path | None, allow: list[str],
           expect_title: str | None, kind: str = "main") -> int:
    """Check a rendered artifact. `kind` selects which gate numbers apply.

    The gate report describes the MAIN TEXT. Its G2c-cite-count and
    G5.total_pages are that document's reference count and page count, so
    asserting them against a supplementary PDF is guaranteed noise: measured
    on the shipped artifacts, the H1 SI scored "cited 0, refs 184" and
    "13 pages vs 34" while being perfectly correct. A check that cannot pass
    on a valid document trains the reader to ignore the checker.

    The SI page count is NOT hardcoded to compensate. This repository already
    carries the scar of that bug class, in verify_pdf.py's own docstring: a
    checklist step "that requires editing constants by hand is exactly how the
    'July 2026' bug class was born". If the SI build records its own page
    count the check runs against that; otherwise it is skipped and said so.
    """
    si = kind == "si"
    for f in (pdf_p, gates_p):
        if not f.exists():
            print(f"FAIL: {f} missing")
            return 2

    gates = json.loads(gates_p.read_text(encoding="utf-8"))
    gate_map = gates.get("gates", gates)

    import pymupdf
    with pymupdf.open(pdf_p) as d:
        pages = d.page_count
        t = " ".join(" ".join(d[i].get_text()
                              for i in range(d.page_count)).split())

    checks: list[tuple[str, bool, str]] = []

    if expect_title:
        frag = " ".join(expect_title.split())
        checks.append(("title present in PDF text",
                       frag.lower() in t.lower(), frag[:60]))

    stale = sorted(n for n in all_known_period_names() - set(allow) if n in t)
    checks.append(("no out-of-period month name", not stale,
                   f"found {stale}" if stale else "clean"))

    checks.append(("no unresolved placeholders",
                   "{{" not in t and "}}" not in t, ""))

    narration = find_narration(t)
    if si and narration:
        # Measured before demoting: find_narration on the pre-rewrite SI and
        # on the current one returns the SAME hits, and NEW_hits is empty.
        # They are method prose ("the quotation is truncated to 25 words
        # before that check"), not agent leakage. Fatal for main text, where
        # no such vocabulary belongs; reported for SI, where it does.
        print(f"  WARN  agent-narration vocabulary in SI prose: {narration[:3]}")
    else:
        checks.append(("no agent narration", not narration,
                       f"{narration[:3]}" if narration else "clean"))

    checks.append(("no doubled figure captions",
                   not re.search(r"Figure (\d+)[.:]\s*Figure \1", t), ""))

    unmerged = re.findall(r"(?:\[\d+(?:,\d+)*\]\s*){2,}", t)
    checks.append(("no unmerged citation runs", not unmerged,
                   f"{unmerged[:2]}" if unmerged else ""))

    n_refs = None
    for key in ("G2c-cite-count", "G2c"):
        if key in gate_map:
            n_refs = gate_map[key].get("detail", {}).get("cited")
            break
    skipped = []
    if si:
        # The reference list belongs to the main text; an SI cites a subset or
        # nothing at all. Asserting the main text's count here can only fail.
        print("  skip  citation checks: gate report counts the main text, "
              "not the SI")
    elif n_refs:
        # [60]fullerene and [100] Miller indices are nomenclature, not cites.
        seq, seen = [], set()
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
                       seq == sorted(seq), f"{len(seen)} of {n_refs}"))
        checks.append(("every reference is cited", len(seen) == n_refs,
                       f"cited {len(seen)}, refs {n_refs}"))
    else:
        checks.append(("citation count available in gate report", False,
                       "no G2c-cite-count"))

    if map_p and map_p.exists() and not si:
        smap = json.loads(map_p.read_text(encoding="utf-8"))
        titles = [s["title"] for s in smap.get("sections", [])]
        missing = [s for s in titles
                   if " ".join(s.split()).lower() not in t.lower()]
        checks.append(("every mapped section heading present", not missing,
                       f"missing {missing}" if missing else f"{len(titles)} sections"))

    if si:
        # Only check a page count the SI build itself recorded. Typing one in
        # by hand is the defect verify_pdf.py's docstring warns about.
        si_pages = None
        for key in ("G5-si", "G5_si", "si"):
            d = gate_map.get(key, {})
            if isinstance(d, dict):
                si_pages = (d.get("detail") or d).get("pages")
                if si_pages:
                    break
        if si_pages:
            checks.append(("SI page count matches its own build record",
                           pages == si_pages, f"{pages} vs {si_pages}"))
        else:
            print(f"  skip  page count: SI build records none "
                  f"(rendered {pages} pages)")
    else:
        g5 = gate_map.get("G5", {}).get("detail", {})
        expected_pages = g5.get("total_pages")
        if expected_pages:
            checks.append(("page count matches gate report",
                           pages == expected_pages,
                           f"{pages} pages vs {expected_pages}"))

    width = max(len(n) for n, _, _ in checks)
    ok = True
    for name, passed, note in checks:
        ok &= passed
        print(f"  {'PASS' if passed else 'FAIL'}  {name:<{width}}  {note}")
    if skipped:
        print(f"  note  nomenclature brackets ignored: {sorted(set(skipped))[:4]}")

    gate_fail = [k for k, v in gate_map.items()
                 if isinstance(v, dict) and v.get("status") == "fail"]
    if gate_fail:
        ok = False
        print(f"  FAIL  gate report contains failures: {gate_fail}")

    print(f"\n{'ALL CHECKS PASS' if ok else 'VERIFICATION FAILED'}  "
          f"({pdf_p.name}, {pages} pages)")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--gates", required=True)
    ap.add_argument("--map")
    ap.add_argument("--title")
    ap.add_argument("--allow", action="append", default=[],
                    help="period name legitimately present, repeatable")
    ap.add_argument("--kind", choices=("main", "si"), default="main",
                    help="which document this is; 'si' skips the checks whose "
                         "numbers describe the main text")
    a = ap.parse_args()
    return verify(ROOT / a.pdf if not pathlib.Path(a.pdf).is_absolute() else pathlib.Path(a.pdf),
                  ROOT / a.gates if not pathlib.Path(a.gates).is_absolute() else pathlib.Path(a.gates),
                  (ROOT / a.map) if a.map else None,
                  a.allow, a.title, a.kind)


if __name__ == "__main__":
    raise SystemExit(main())
