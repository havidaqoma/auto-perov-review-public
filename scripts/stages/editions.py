"""editions: where the FINAL edition of a period lives, in either tree layout.

The private repository keeps every edition an issue went through, under
versioned names: manuscript/2026-07_v5/manuscript_v5.md, runs/<run>/draft_v4/,
runs/<run>/gate_report_v4.json. The public release ships only the final
edition and drops the version token from output names:
manuscript/2026-07/manuscript.md, runs/<run>/draft/, runs/<run>/gate_report.json
(scripts/release/release_layout.py does that rename).

Tests that read shipped artifacts run in both trees, so they ask this module
for paths instead of spelling out a layout. The layout is detected from the
release's own rename record, never guessed from which files happen to exist:
guessing from existence is how a test silently skips in one tree while
claiming to pass.
"""
from __future__ import annotations

import pathlib

# period -> final edition version. Must agree with release_layout.FINAL;
# tests/test_editions.py checks that it does.
FINAL: dict[str, str] = {"2026-06": "v4", "2026-07": "v5", "2026-08": "v5",
                         "2026-H1": "v6"}

# s18d writes these names whatever the edition, so a build's own run outputs
# carry "_v4" even for the v6 H1 paper.
BUILD_VER = "v4"


def is_release_tree(root: pathlib.Path) -> bool:
    return (root / "verification" / "release_renames.json").is_file()


def _tag(root: pathlib.Path, ver: str) -> str:
    return "" if is_release_tree(root) else f"_{ver}"


def edition_dir(root: pathlib.Path, period: str) -> pathlib.Path:
    if is_release_tree(root):
        return root / "manuscript" / period
    return root / "manuscript" / f"{period}_{FINAL[period]}"


def edition_file(root: pathlib.Path, period: str, stem: str,
                 ext: str) -> pathlib.Path:
    """manuscript/supplementary/gate_report of the final edition."""
    return edition_dir(root, period) / f"{stem}{_tag(root, FINAL[period])}{ext}"


def run_dir(root: pathlib.Path, period: str) -> pathlib.Path | None:
    ptr = root / "runs" / f"{period}.active"
    if not ptr.is_file():
        return None
    return root / "runs" / ptr.read_text(encoding="utf-8").strip()


def manuscript_md(root: pathlib.Path, period: str) -> pathlib.Path:
    """The final manuscript markdown.

    Private H1 is the one exception: its edition folder holds the v6 text
    under s18d's v4 name, and the canonical v6 copy is in the run folder.
    """
    if period == "2026-H1" and not is_release_tree(root):
        return root / "runs" / "2026-H1" / "manuscript_v6.md"
    return edition_file(root, period, "manuscript", ".md")


def build_gate_report(root: pathlib.Path, rd: pathlib.Path) -> pathlib.Path:
    """The gate report s18d wrote into a run folder."""
    return rd / f"gate_report{_tag(root, BUILD_VER)}.json"


def build_manuscript(root: pathlib.Path, rd: pathlib.Path) -> pathlib.Path:
    """The manuscript s18d wrote into a run folder."""
    return rd / f"manuscript{_tag(root, BUILD_VER)}.md"


def draft_dir(root: pathlib.Path, rd: pathlib.Path) -> pathlib.Path:
    """The monthly section-draft cache s13d writes and s18d reads."""
    return rd / ("draft" if is_release_tree(root) else f"draft_{BUILD_VER}")
