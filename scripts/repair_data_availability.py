"""Put the public repository link into the Data Availability Statement of every
FINAL shipped manuscript, then re-render its PDF.

WHY A REPAIR SCRIPT AND NOT A REBUILD
The build now emits the new statement itself (stages.boilerplate.
data_availability), so every future issue carries the link. The editions that
already shipped cannot simply be rebuilt: July and August 2026 are
hand-revised prose that s18d would overwrite from its draft caches. So this
script replaces ONE paragraph, the one under "## Data Availability Statement",
with the exact text the build now generates, and re-renders with the build's
own pandoc/tectonic invocation. Nothing else in the markdown changes.

Idempotent: a file already carrying the new statement is left alone.
Superseded editions are not touched; only the final edition of each period is
shipped and maintained.

    python scripts/repair_data_availability.py --check     # report, no writes
    python scripts/repair_data_availability.py              # edit + render
"""
from __future__ import annotations

import argparse
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stages.boilerplate import REPO_URL, data_availability  # noqa: E402

HEAD_MONTHLY = ROOT / "config" / "tex" / "manuscript_head.tex"
HEAD_YEARLY = ROOT / "yearly" / "config" / "tex" / "manuscript_head.tex"

# (markdown copies that must stay identical, period word, pdf targets, head, cwd)
# The first markdown path is the one rendered; the rest are copies of it.
TARGETS = [
    (["manuscript/2026-06_v4/manuscript_v4.md",
      "runs/2026-06_cf764cbb/manuscript_v4.md"],
     "month", ["manuscript/2026-06_v4/manuscript_v4.pdf"], HEAD_MONTHLY, ROOT),
    (["manuscript/2026-07_v5/manuscript_v5.md"],
     "month", ["manuscript/2026-07_v5/manuscript_v5.pdf"], HEAD_MONTHLY, ROOT),
    (["manuscript/2026-08_v5/manuscript_v5.md"],
     "month", ["manuscript/2026-08_v5/manuscript_v5.pdf"], HEAD_MONTHLY, ROOT),
    # H1: s18d wrote the v6 paper under its v4 names; all three are one text.
    (["manuscript/2026-H1_v6/manuscript_v4.md",
      "runs/2026-H1/manuscript_v6.md", "runs/2026-H1/manuscript_v4.md"],
     "half-year", ["manuscript/2026-H1_v6/manuscript_v6.pdf",
                   "manuscript/2026-H1_v6/manuscript_v4.pdf"],
     HEAD_MONTHLY, ROOT),
    (["yearly/manuscript/2025_yearly/manuscript_yearly.md",
      "yearly/runs/2025_6cb0e6ed/manuscript_yearly.md"],
     "year", ["yearly/manuscript/2025_yearly/manuscript_yearly.pdf"],
     HEAD_YEARLY, ROOT / "yearly"),
]

SECTION = re.compile(r"(## Data Availability Statement[ \t]*\r?\n[ \t]*\r?\n)"
                     r"(.+?)(\r?\n)")


def find_pandoc() -> str:
    p = shutil.which("pandoc")
    if p:
        return p
    for c in (pathlib.Path.home() / "AppData/Local/Pandoc/pandoc.exe",
              pathlib.Path(r"C:\Program Files\Pandoc\pandoc.exe")):
        if c.exists():
            return str(c)
    raise SystemExit("FAIL-CLOSED: pandoc not found")


def render(md: pathlib.Path, pdf: pathlib.Path, head: pathlib.Path,
           cwd: pathlib.Path) -> None:
    """The s18d / s18y invocation, byte for byte in its arguments."""
    tmp = pdf.with_name(pdf.stem + ".building.pdf")
    p = subprocess.run(
        [find_pandoc(), str(md),
         "-f", "markdown+raw_tex-implicit_figures",
         "-V", "geometry:margin=2.4cm", "-V", "fontsize=11pt",
         "-V", "linestretch=1.05", "-V", "colorlinks=true",
         "-V", "linkcolor=[HTML]{1A4E8A}", "-V", "urlcolor=[HTML]{1A4E8A}",
         "-H", str(head),
         f"--pdf-engine={shutil.which('tectonic') or 'tectonic'}",
         "-o", str(tmp)],
        capture_output=True, text=True, timeout=1200, cwd=cwd)
    if p.returncode != 0 or not tmp.exists():
        raise SystemExit(f"FAIL-CLOSED: render {md.name} rc={p.returncode}\n"
                         f"{(p.stderr or '')[-1400:]}")
    tmp.replace(pdf)


def new_text(md_text: str, word: str) -> tuple[str, str]:
    m = SECTION.search(md_text)
    if not m:
        raise SystemExit("FAIL-CLOSED: no '## Data Availability Statement' "
                         "paragraph found")
    old = m.group(2)
    return md_text[:m.start(2)] + data_availability(word) + md_text[m.end(2):], old


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--no-render", action="store_true")
    a = ap.parse_args()
    for mds, word, pdfs, head, cwd in TARGETS:
        paths = [ROOT / m for m in mds]
        texts = [p.read_bytes() for p in paths]
        if len(set(texts)) != 1:
            raise SystemExit(f"FAIL-CLOSED: copies differ: {mds}")
        t = texts[0].decode("utf-8")
        if REPO_URL in t:
            print(f"[skip] {mds[0]}: already carries the link")
            continue
        t2, old = new_text(t, word)
        # Exactly one paragraph may change.
        assert t2.replace(data_availability(word), old, 1) == t
        print(f"[edit] {mds[0]} (+{len(mds) - 1} copies)")
        if a.check:
            continue
        for p in paths:
            p.write_bytes(t2.encode("utf-8"))
        if a.no_render:
            continue
        first = ROOT / pdfs[0]
        render(paths[0], first, head, cwd)
        for extra in pdfs[1:]:
            shutil.copy2(first, ROOT / extra)
        print(f"[pdf ] {pdfs[0]}" + (f" (+{len(pdfs) - 1} copy)" if pdfs[1:] else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
