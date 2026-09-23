"""Repair the citation rows of already-shipped monthly SIs, in place.

WHY THIS EXISTS
Every v4/v5 monthly SI says "Cited in the main text | 0". s19 counted only
plain [12] markers while the v4 build emits [\\href{https://doi.org/...}{12}],
so it found none. The same SIs carry Figure S1 (the corpus funnel), whose last
bar was drawn from stats.json's selection.n_cited: a PRE-DRAFTING CAP
(min(depth, max_body_citations)), not what the body cites. July's bar read 180
for a manuscript that cites 79.

s19 is fixed for future builds. Re-running it on a shipped edition is NOT a
repair, though: its note prose comes from the style-pass text that was later
revised by hand in the shipped markdown, and the byline date is taken from
the day of the build. A re-run on 2026-07 v4 moved four prose sentences and
the date (checked, then restored). So this repairs the shipped markdown
directly and changes nothing but:

  1. the two citation rows of Table S2 (si_facts.correct_si_cited), and
  2. Figure S1, redrawn from Table S2's own numbers (si_facts.draw_funnel).

Then it re-renders with the renderer that made the edition: s19.render_pdf
for v4 (10pt), render_v5.render for v5 (11pt + shared preamble). Fails closed
if the markdown diff touches any other line.

    python scripts/repair_monthly_si_citations.py 2026-06_v4 2026-07_v4 ...
"""
from __future__ import annotations

import difflib
import json
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stages.si_facts import correct_si_cited, draw_funnel  # noqa: E402

ROW = re.compile(r"^\| (.+?) \| (\d+) \|[ \t]*$", re.M)
FUNNEL_REF = re.compile(r"\]\(([^)]*?/fig/S2_corpus_funnel\.pdf)\)")
TABLE_ROWS = ["Passed the scope gate", "Usable abstract (eligibility)",
              "Depth tier (selected for close reading)",
              "Extraction records surviving all guards",
              "Cited in the main text"]
LABELS = ["Passed the scope gate", "Usable abstract",
          "Depth tier (close reading)", "Verified extraction record",
          "Cited in the main text"]


def _write_keeping_eol(path: pathlib.Path, text: str) -> None:
    """Write text with the file's existing line endings, so the git diff is
    the two rows and not a whole-file EOL flip."""
    eol = "\r\n" if b"\r\n" in path.read_bytes() else "\n"
    path.write_bytes(text.replace("\r\n", "\n").replace("\n", eol)
                     .encode("utf-8"))


def repair(edition: str) -> dict:
    d = ROOT / "manuscript" / edition
    ver = edition.rsplit("_", 1)[1]
    si = d / f"supplementary_{ver}.md"
    ms = d / f"manuscript_{ver}.md"
    old = si.read_text(encoding="utf-8")
    new, facts = correct_si_cited(old, ms.read_text(encoding="utf-8"))

    changed = [l for l in difflib.unified_diff(
        old.splitlines(), new.splitlines(), lineterm="", n=0)
        if l[:1] in "+-" and not l.startswith(("+++", "---"))]
    allowed = re.compile(r"^[+-]\| (Cited in the main text|Audited but not "
                         r"cited individually) \| \d+ \|$")
    bad = [l for l in changed if not allowed.match(l)]
    if bad or len(changed) != 4:
        raise SystemExit(f"FAIL-CLOSED {edition}: diff is not exactly the two "
                         f"citation rows: {changed}")

    rows = dict(ROW.findall(new))
    counts = [int(rows[k]) for k in TABLE_ROWS]
    refs = FUNNEL_REF.findall(new)
    if len(refs) != 1:
        raise SystemExit(f"FAIL-CLOSED {edition}: {len(refs)} funnel refs")
    fig = pathlib.Path(refs[0])
    if not fig.is_absolute():
        fig = d / fig
    draw_funnel(fig, LABELS, counts)
    if (d / "fig").is_dir():
        shutil.copy(fig, d / "fig" / fig.name)

    _write_keeping_eol(si, new)
    run_si = fig.parent.parent / si.name          # runs/<hash>/supplementary_v4.md
    if ver == "v4" and run_si.exists():
        _write_keeping_eol(run_si, new)

    pdf = d / f"supplementary_{ver}.pdf"
    if ver == "v5":
        import render_v5
        render_v5.render(si, pdf)
    else:
        from stages import s19_si
        s19_si.render_pdf(si, pdf, fig.parent.parent)
    chem = d / "chemrxiv" / pdf.name
    if chem.exists():
        shutil.copy(pdf, chem)
        _swap_tar_member(d, pdf)
    out = {"edition": edition, **facts, "funnel": counts,
           "figure": str(fig.relative_to(ROOT)), "chemrxiv_copy": chem.exists()}
    print(json.dumps(out))
    return out


def _swap_tar_member(d: pathlib.Path, pdf: pathlib.Path) -> None:
    """Replace only the SI inside the edition's ChemRxiv tarball.

    Re-running s20 would regenerate manuscript.tex, the metadata and the
    checklist too; the repair must not touch the main-text package. Every
    other member is copied across byte for byte, in the original order.
    """
    import io
    import tarfile
    tgzs = sorted(d.glob("chemrxiv_*.tar.gz"))
    if len(tgzs) != 1:
        raise SystemExit(f"FAIL-CLOSED: expected one tarball in {d}, "
                         f"found {len(tgzs)}")
    tgz = tgzs[0]
    with tarfile.open(tgz, "r:gz") as src:
        members = [(m, src.extractfile(m).read() if m.isfile() else None)
                   for m in src.getmembers()]
    if pdf.name not in [m.name for m, _ in members]:
        raise SystemExit(f"FAIL-CLOSED: {pdf.name} not in {tgz.name}")
    tmp = tgz.with_suffix(".tmp")
    with tarfile.open(tmp, "w:gz") as dst:
        for m, data in members:
            if m.name == pdf.name:
                data = pdf.read_bytes()
                m.size = len(data)
                m.mtime = int(pdf.stat().st_mtime)
            dst.addfile(m, io.BytesIO(data) if data is not None else None)
    tmp.replace(tgz)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    for e in sys.argv[1:]:
        repair(e)
