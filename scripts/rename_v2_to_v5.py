"""Standardise the device-family edition from v2 to v5.

Havid (2026-09-10): "there is some confusion in the version, so to standardize,
maybe make all the newest to v5 (instead of v2, because the latest version is
v4)".

He is right and the confusion was mine. The monthly pipeline is at v4, so
naming the new device-family structure "v2" reads as OLDER than v4 when it is
strictly newer. Version numbers that decrease over time are a documentation
defect that costs a reader real time.

WHAT MOVES
    scripts/stages/h1_build_v2.py        -> h1_build_v5.py
    scripts/stages/h1_draft_v2.py        -> h1_draft_v5.py
    scripts/stages/h1_finalize_v2.py     -> h1_finalize_v5.py
    scripts/stages/h1_section_map_v2.py  -> h1_section_map_v5.py
    scripts/probe_h1v2_*.py              -> probe_h1v5_*.py
    manuscript/2026-H1_v2/               -> manuscript/2026-H1_v5/
    runs/2026-H1/12_section_map_v2.json  -> 12_section_map_v5.json
    runs/2026-H1/draft_h1_v2/            -> draft_h1_v5/
    runs/2026-H1/gate_report_v2.json     -> gate_report_v5.json
    runs/2026-H1/manuscript_v2.md        -> manuscript_v5.md
    runs/2026-H1/supplementary_v2.md     -> supplementary_v5.md
    runs/2026-H1/13_draft_h1_v2.json     -> 13_draft_h1_v5.json

WHAT MUST NOT MOVE, and why each one matters
    scripts/stages/s11b_figures_v2.py
        A MONTHLY stage. Its "v2" means the second generation of the monthly
        figure set and has nothing to do with the period edition. Renaming it
        would break the monthly chain, which Havid's standing instruction says
        must not be disturbed.
    scripts/stages/s13d_draft_v4.py, s18d_build_v4.py
        The monthly v4 stages every H1 adapter imports FROM.
    scripts/stages/h1_*.py without a suffix (h1_aggregate, h1_stats,
    h1_figures, h1_tables, h1_title, h1_build, h1_draft, h1_finalize,
    h1_section_map)
        These are the v1 mechanism-structure files plus the shared modules.
        The v1 edition stays reproducible.

Uses `git mv` where the path is tracked so history follows the file, and plain
rename otherwise. Idempotent: a second run finds nothing to do.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

# (path, new_name). Order matters only for readability.
FILE_MOVES = [
    ("scripts/stages/h1_build_v2.py", "h1_build_v5.py"),
    ("scripts/stages/h1_draft_v2.py", "h1_draft_v5.py"),
    ("scripts/stages/h1_finalize_v2.py", "h1_finalize_v5.py"),
    ("scripts/stages/h1_section_map_v2.py", "h1_section_map_v5.py"),
    ("scripts/probe_h1v2_families.py", "probe_h1v5_families.py"),
    ("scripts/probe_h1v2_verify_family.py", "probe_h1v5_verify_family.py"),
    ("scripts/probe_h1v2_area_outliers.py", "probe_h1v5_area_outliers.py"),
]

DIR_MOVES = [
    ("manuscript/2026-H1_v2", "2026-H1_v5"),
    ("runs/2026-H1/draft_h1_v2", "draft_h1_v5"),
]

RUN_FILE_MOVES = [
    ("runs/2026-H1/12_section_map_v2.json", "12_section_map_v5.json"),
    ("runs/2026-H1/gate_report_v2.json", "gate_report_v5.json"),
    ("runs/2026-H1/manuscript_v2.md", "manuscript_v5.md"),
    ("runs/2026-H1/supplementary_v2.md", "supplementary_v5.md"),
    ("runs/2026-H1/13_draft_h1_v2.json", "13_draft_h1_v5.json"),
]

# Files whose CONTENT must be rewritten. Only the H1 v5 stages and the probes:
# never a monthly stage.
CONTENT_FILES = [
    "scripts/stages/h1_build_v5.py",
    "scripts/stages/h1_draft_v5.py",
    "scripts/stages/h1_finalize_v5.py",
    "scripts/stages/h1_section_map_v5.py",
    "scripts/stages/h1_tables.py",
    "scripts/probe_h1v5_families.py",
    "scripts/probe_h1v5_verify_family.py",
    "scripts/probe_h1v5_area_outliers.py",
]

# Ordered longest-first so a short pattern cannot consume a long one.
SUBS = [
    ("h1_section_map_v2", "h1_section_map_v5"),
    ("h1_finalize_v2", "h1_finalize_v5"),
    ("h1_build_v2", "h1_build_v5"),
    ("h1_draft_v2", "h1_draft_v5"),
    ("probe_h1v2", "probe_h1v5"),
    ("12_section_map_v2.json", "12_section_map_v5.json"),
    ("13_draft_h1_v2.json", "13_draft_h1_v5.json"),
    ("gate_report_v2.json", "gate_report_v5.json"),
    ("supplementary_v2", "supplementary_v5"),
    ("manuscript_v2", "manuscript_v5"),
    ("draft_h1_v2", "draft_h1_v5"),
    ("2026-H1_v2", "2026-H1_v5"),
    ('VERSION = "v2"', 'VERSION = "v5"'),
    ('derive_title_v2_standalone', 'derive_title_v5_standalone'),
    ('"version": "v2"', '"version": "v5"'),
    ("h1v2-build", "h1v5-build"),
    ("h1v2-final", "h1v5-final"),
    ("h1v2-13", "h1v5-13"),
    ("h1v2-map", "h1v5-map"),
    ("h1v2-stats", "h1v5-stats"),
    ("h1v2-tables", "h1v5-tables"),
    ("h1v2_abstract", "h1v5_abstract"),
]

# `s11b_figures_v2` contains "figures_v2" and must survive untouched. Assert it.
FORBIDDEN = ["s11b_figures_v5", "s13d_draft_v5", "s18d_build_v5"]


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
        # An untracked-in-index path can still fail git mv; fall back.
    src.rename(dst)
    return "rename"


def main() -> int:
    print("=== FILE MOVES ===")
    for rel, newname in FILE_MOVES + RUN_FILE_MOVES:
        src = ROOT / rel
        dst = src.parent / newname
        print(f"  {move(src, dst):18} {rel} -> {newname}")

    print("\n=== DIR MOVES ===")
    for rel, newname in DIR_MOVES:
        src = ROOT / rel
        dst = src.parent / newname
        print(f"  {move(src, dst):18} {rel} -> {newname}")

    print("\n=== CONTENT REWRITE ===")
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
            n = sum(t0.count(a) for a, _ in SUBS)
            print(f"  rewrote {n:3} refs    {rel}")
        else:
            print(f"  unchanged          {rel}")

    print("\n=== ASSERTIONS ===")
    bad = []
    for f in FORBIDDEN:
        hits = subprocess.run(["git", "grep", "-l", f],
                              cwd=str(ROOT), capture_output=True, text=True)
        if hits.stdout.strip():
            bad.append(f"{f} appears in: {hits.stdout.strip()}")
    # The monthly stage must still exist under its own name.
    for keep in ("scripts/stages/s11b_figures_v2.py",
                 "scripts/stages/s13d_draft_v4.py",
                 "scripts/stages/s18d_build_v4.py",
                 "scripts/stages/h1_build.py",
                 "scripts/stages/h1_section_map.py"):
        if not (ROOT / keep).exists():
            bad.append(f"MISSING (must not have moved): {keep}")
    if bad:
        print("  FAIL:\n    " + "\n    ".join(bad))
        return 1
    print("  OK: monthly stages intact, no monthly file renamed to v5")

    print("\n=== REMAINING v2 REFERENCES (should be monthly-only) ===")
    r = subprocess.run(["git", "grep", "-n", "-I", "_v2"],
                       cwd=str(ROOT), capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "s11b_figures_v2" in line or "OLD/" in line or "archive/" in line:
            continue
        print("  ", line[:150])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
