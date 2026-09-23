"""Standardise the device-family edition from v5 to v6.

Havid (2026-09-11): "still need revision, therefore make it v6".

A revision that changes what the reader sees gets a new version number. This
cycle changed: the extraction model pin, the Table 1 and Table 2 first column,
the missing Figure S1, both doubled SI captions, and the orphaned Table S4. The
v5 PDF a reader might already hold is not the v6 PDF, so they must not share a
name.

WHAT MOVES
    scripts/stages/h1_build_v5.py        -> h1_build_v6.py
    scripts/stages/h1_draft_v5.py        -> h1_draft_v6.py
    scripts/stages/h1_finalize_v5.py     -> h1_finalize_v6.py
    scripts/stages/h1_section_map_v5.py  -> h1_section_map_v6.py
    scripts/probe_h1v5_*.py              -> probe_h1v6_*.py
    manuscript/2026-H1_v5/               -> manuscript/2026-H1_v6/
    runs/2026-H1/12_section_map_v5.json  -> 12_section_map_v6.json
    runs/2026-H1/draft_h1_v5/            -> draft_h1_v6/
    runs/2026-H1/gate_report_v5.json     -> gate_report_v6.json
    runs/2026-H1/manuscript_v5.md        -> manuscript_v6.md
    runs/2026-H1/supplementary_v5.md     -> supplementary_v6.md
    runs/2026-H1/13_draft_h1_v5.json     -> 13_draft_h1_v6.json

WHAT MUST NOT MOVE
    scripts/stages/s11b_figures_v2.py    a MONTHLY stage; its "v2" is the
                                         second generation of the monthly
                                         figure set and unrelated to the period
                                         edition. Renaming it breaks the
                                         monthly chain.
    scripts/stages/s13d_draft_v4.py, s18d_build_v4.py
                                         the monthly v4 stages every H1 adapter
                                         imports FROM.
    scripts/stages/h1_*.py (unsuffixed)  the v1 mechanism edition plus the
                                         shared modules. v1 stays reproducible.
    manuscript/2026-H1_v4/               the v1 artifact.

The v5 run-dir files are MOVED rather than copied: keeping both would leave two
gate reports differing only in a suffix, and the next reader would have to guess
which describes the shipped PDF. The v5 manuscript directory moves wholesale for
the same reason. Git history follows each file via `git mv` where the path is
tracked.

Idempotent: a second run finds nothing to do.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OLDV, NEWV = "v5", "v6"

FILE_MOVES = [
    ("scripts/stages/h1_build_v5.py", "h1_build_v6.py"),
    ("scripts/stages/h1_draft_v5.py", "h1_draft_v6.py"),
    ("scripts/stages/h1_finalize_v5.py", "h1_finalize_v6.py"),
    ("scripts/stages/h1_section_map_v5.py", "h1_section_map_v6.py"),
    ("scripts/probe_h1v5_families.py", "probe_h1v6_families.py"),
    ("scripts/probe_h1v5_verify_family.py", "probe_h1v6_verify_family.py"),
    ("scripts/probe_h1v5_area_outliers.py", "probe_h1v6_area_outliers.py"),
]
DIR_MOVES = [
    ("manuscript/2026-H1_v5", "2026-H1_v6"),
    ("runs/2026-H1/draft_h1_v5", "draft_h1_v6"),
]
RUN_FILE_MOVES = [
    ("runs/2026-H1/12_section_map_v5.json", "12_section_map_v6.json"),
    ("runs/2026-H1/gate_report_v5.json", "gate_report_v6.json"),
    ("runs/2026-H1/manuscript_v5.md", "manuscript_v6.md"),
    ("runs/2026-H1/supplementary_v5.md", "supplementary_v6.md"),
    ("runs/2026-H1/13_draft_h1_v5.json", "13_draft_h1_v6.json"),
]
CONTENT_FILES = [
    "scripts/stages/h1_build_v6.py",
    "scripts/stages/h1_draft_v6.py",
    "scripts/stages/h1_finalize_v6.py",
    "scripts/stages/h1_section_map_v6.py",
    "scripts/stages/h1_tables.py",
    "scripts/stages/h1_figures.py",
    "scripts/stages/h1_si_extra.py",
    "scripts/probe_h1v6_families.py",
    "scripts/probe_h1v6_verify_family.py",
    "scripts/probe_h1v6_area_outliers.py",
]
SUBS = [
    ("h1_section_map_v5", "h1_section_map_v6"),
    ("h1_finalize_v5", "h1_finalize_v6"),
    ("h1_build_v5", "h1_build_v6"),
    ("h1_draft_v5", "h1_draft_v6"),
    ("probe_h1v5", "probe_h1v6"),
    ("12_section_map_v5.json", "12_section_map_v6.json"),
    ("13_draft_h1_v5.json", "13_draft_h1_v6.json"),
    ("gate_report_v5.json", "gate_report_v6.json"),
    ("supplementary_v5", "supplementary_v6"),
    ("manuscript_v5", "manuscript_v6"),
    ("draft_h1_v5", "draft_h1_v6"),
    ("2026-H1_v5", "2026-H1_v6"),
    ('VERSION = "v5"', 'VERSION = "v6"'),
    ("derive_title_v5_standalone", "derive_title_v6_standalone"),
    ('"version": "v5"', '"version": "v6"'),
    ("h1v5-build", "h1v6-build"),
    ("h1v5-final", "h1v6-final"),
    ("h1v5-13", "h1v6-13"),
    ("h1v5-map", "h1v6-map"),
    ("h1v5-stats", "h1v6-stats"),
    ("h1v5-tables", "h1v6-tables"),
    ("h1v5_abstract", "h1v6_abstract"),
]
FORBIDDEN = ["s11b_figures_v6", "s13d_draft_v6", "s18d_build_v6"]
MUST_EXIST = [
    "scripts/stages/s11b_figures_v2.py",
    "scripts/stages/s13d_draft_v4.py",
    "scripts/stages/s18d_build_v4.py",
    "scripts/stages/h1_build.py",
    "scripts/stages/h1_section_map.py",
    "manuscript/2026-H1_v4",
]


def tracked(p: pathlib.Path) -> bool:
    r = subprocess.run(["git", "ls-files", "--error-unmatch", str(p)],
                       cwd=str(ROOT), capture_output=True, text=True)
    return r.returncode == 0


def move(src: pathlib.Path, dst: pathlib.Path) -> str:
    if not src.exists():
        return "skip (absent)"
    if dst.exists():
        return "skip (target exists)"
    if tracked(src):
        r = subprocess.run(["git", "mv", str(src), str(dst)],
                           cwd=str(ROOT), capture_output=True, text=True)
        if r.returncode == 0:
            return "git mv"
    src.rename(dst)
    return "rename"


def main() -> int:
    print(f"=== {OLDV} -> {NEWV} ===\n--- files ---")
    for rel, new in FILE_MOVES + RUN_FILE_MOVES:
        src = ROOT / rel
        print(f"  {move(src, src.parent / new):18} {rel} -> {new}")

    print("--- dirs ---")
    for rel, new in DIR_MOVES:
        src = ROOT / rel
        print(f"  {move(src, src.parent / new):18} {rel} -> {new}")

    print("--- content ---")
    for rel in CONTENT_FILES:
        p = ROOT / rel
        if not p.exists():
            print(f"  skip (absent)      {rel}")
            continue
        t0 = p.read_text(encoding="utf-8")
        t = t0
        for a, b in SUBS:
            t = t.replace(a, b)
        if t != t0:
            p.write_text(t, encoding="utf-8")
            print(f"  rewrote            {rel}")
        else:
            print(f"  unchanged          {rel}")

    print("\n--- assertions ---")
    bad = []
    for f in FORBIDDEN:
        r = subprocess.run(["git", "grep", "-l", f], cwd=str(ROOT),
                           capture_output=True, text=True)
        if r.stdout.strip():
            bad.append(f"{f} appears in {r.stdout.strip()}")
    for keep in MUST_EXIST:
        if not (ROOT / keep).exists():
            bad.append(f"MISSING (must not have moved): {keep}")
    if bad:
        print("  FAIL:\n    " + "\n    ".join(bad))
        return 1
    print("  OK: monthly stages and the v1 edition are intact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
