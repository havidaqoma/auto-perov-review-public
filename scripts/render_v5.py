"""Render the v5 manuscript and SI PDFs for a monthly edition.

WHY THIS EXISTS
The v5 directories were created by copying v4 and renaming the files. That
rename gave us `manuscript_v5.pdf` while its BYTES were still the v4 render:
verified with cmp, the v5 PDF was byte-identical to v4 even after the markdown
had been rewritten. Shipping that would put a stale PDF behind a revised
source, which is worse than having no PDF at all, because the filename claims
a revision the pages do not contain.

s18d_build_v4.py cannot be reused directly: it rebuilds the whole edition from
the draft caches and the section map, which would DISCARD the hand-revised v5
markdown. So this renders the existing markdown with the identical pandoc and
tectonic invocation lifted from s18d_build_v4.py (lines ~1126-1147), keeping
geometry, font size, line stretch, link colours and the shared LaTeX preamble
the same as every shipped issue.

    python scripts/render_v5.py 2026-07 2026-08
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
HEAD = ROOT / "config" / "tex" / "manuscript_head.tex"


def find_pandoc() -> str:
    p = shutil.which("pandoc")
    if p:
        return p
    for c in (pathlib.Path.home() / "AppData/Local/Pandoc/pandoc.exe",
              pathlib.Path(r"C:\Program Files\Pandoc\pandoc.exe")):
        if c.exists():
            return str(c)
    raise SystemExit("FAIL-CLOSED: pandoc not found")


def render(md: pathlib.Path, pdf: pathlib.Path) -> None:
    pandoc = find_pandoc()
    tectonic = shutil.which("tectonic") or "tectonic"
    if not HEAD.exists():
        raise SystemExit(f"FAIL-CLOSED: missing preamble {HEAD}")
    before = pdf.stat().st_mtime if pdf.exists() else 0
    p = subprocess.run(
        [pandoc, str(md),
         "-f", "markdown+raw_tex-implicit_figures",
         "-V", "geometry:margin=2.4cm", "-V", "fontsize=11pt",
         "-V", "linestretch=1.05", "-V", "colorlinks=true",
         "-V", "linkcolor=[HTML]{1A4E8A}", "-V", "urlcolor=[HTML]{1A4E8A}",
         "-H", str(HEAD),
         f"--pdf-engine={tectonic}", "-o", str(pdf)],
        capture_output=True, text=True, timeout=900, cwd=ROOT)
    if p.returncode != 0 or not pdf.exists():
        err = (p.stdout or "") + "\n" + (p.stderr or "")
        (md.parent / f"{md.stem}_render_error.txt").write_text(err, encoding="utf-8")
        raise SystemExit(f"FAIL-CLOSED: pandoc rc={p.returncode}\n{err[-1400:]}")
    # A render that silently left the old file in place is a failure too.
    if pdf.stat().st_mtime <= before:
        raise SystemExit(f"FAIL-CLOSED: {pdf.name} was not rewritten")
    print(f"  rendered {pdf.relative_to(ROOT)}  {pdf.stat().st_size:,} bytes")


def main(months: list[str]) -> int:
    if not months:
        print(__doc__)
        return 2
    for mon in months:
        d = ROOT / "manuscript" / f"{mon}_v5"
        if not d.is_dir():
            raise SystemExit(f"FAIL-CLOSED: {d} does not exist")
        print(f"=== {mon} ===")
        for stem in ("manuscript_v5", "supplementary_v5"):
            md = d / f"{stem}.md"
            if not md.exists():
                raise SystemExit(f"FAIL-CLOSED: {md} missing")
            render(md, d / f"{stem}.pdf")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
