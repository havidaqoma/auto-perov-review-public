"""An SI must name the paper it supports and count that paper's citations.

Why this file exists
--------------------
The 2026-H1 v6 Supplementary Information shipped with July's subtitle
("Buried-Interface Chemistry, Defect Tolerance and the Certified Efficiency
Frontier") on its front page while the manuscript it supports is titled "The
Certified Frontier From Cell to Module". Its corpus table also said
"Cited in the main text | 0" beside a body carrying 184 linked citations.
All 17 gates passed and 223 tests passed, because nothing compared the SI with
its own manuscript. It was caught by reading the rendered PDF.

Both faults were a second code path producing a fact that the built
manuscript already states. So these tests read BOTH files and compare them,
and one test reads the RENDERED PDF, per handbook H1 10.1 (verify the
rendered artifact, not the gate report).

KNOWN_DEFECTS below is not a waiver list. It records editions shipped before
this gate existed that still carry the defect, so the gate can be strict for
everything else. It may only shrink: a listed edition that has been fixed
fails the test until its entry is removed, so the list cannot quietly go
stale.
"""
from __future__ import annotations

import pathlib

import pytest

from stages.si_facts import (manuscript_title, measured_citations,
                             pdf_front_has_title, si_cited, si_title)

ROOT = pathlib.Path(__file__).resolve().parents[1]
MS = ROOT / "manuscript"

# The period edition the public release ships. Gated strictly: no allowance.
H1 = MS / "2026-H1_v6"

# (edition dir, SI file) -> the defect it shipped with before this gate.
KNOWN_DEFECTS = {
    # v3 manuscripts were revised after their SI was built (fb4a151 "80
    # citations"), so the SI row still carries the pre-revision count:
    # 2026-07 SI says 75 vs 80 in the body, 2026-08 says 74 vs 82.
    ("2026-07_v3", "supplementary_v3.md"): {"cited_mismatch"},
    ("2026-08_v3", "supplementary_v3.md"): {"cited_mismatch"},
    # v4 SIs said "Cited in the main text | 0": s19 counted only plain [n]
    # while the v4+ build emits \href-wrapped markers. Fixed in s19 and the
    # five shipped editions repaired in place on 2026-09-23 by
    # scripts/repair_monthly_si_citations.py (citation rows + Figure S1 only).
    # Superseded H1 v1 edition. Its manuscript_v4.md was overwritten by the v6
    # build before a9a8130 fixed that write-through, so the pair no longer
    # describes one paper at all. Kept for history, not shipped.
    ("2026-H1_v4", "supplementary_v4.md"): {"title", "cited_zero"},
    ("2026-H1_v6", "supplementary_v4.md"): {"title", "cited_zero"},
}

# The shipped v4+ editions whose rendered SI is gated strictly: the PDF shows
# the manuscript's citation count, and Figure S1 draws Table S2's numbers.
STRICT_RENDERED = ["2026-06_v4", "2026-07_v4", "2026-08_v4",
                   "2026-07_v5", "2026-08_v5", "2026-H1_v6"]
_TABLE_S2 = ["Passed the scope gate", "Usable abstract (eligibility)",
             "Depth tier (selected for close reading)",
             "Extraction records surviving all guards",
             "Cited in the main text"]

# Pairs whose SI predates the v3 SI format (no "Cited in the main text" row,
# or a v2 title scheme). Listed so the scan below is explicit about scope.
PRE_V3 = {("2026-07_v2", "supplementary.md"),
          ("2026-07_v3", "supplementary.md")}


def _pairs():
    for d in sorted(MS.glob("*_v[0-9]")):
        for si in sorted(d.glob("supplementary*.md")):
            key = (d.name, si.name)
            if key in PRE_V3:
                continue
            ver = si.stem.replace("supplementary", "")      # "_v6" / ""
            m = d / f"manuscript{ver}.md"
            if not m.exists():
                cands = sorted(d.glob("manuscript*.md"))
                if not cands:
                    continue
                m = cands[-1]
            yield key, si, m


def _defects(si: pathlib.Path, m: pathlib.Path) -> set[str]:
    st = si.read_text(encoding="utf-8")
    mt = m.read_text(encoding="utf-8")
    out = set()
    if si_title(st) != manuscript_title(mt):
        out.add("title")
    n_refs, n_cited = measured_citations(mt)
    got = si_cited(st)
    if got is not None and got != n_cited:
        out.add("cited_zero" if got == 0 else "cited_mismatch")
    return out


PAIRS = list(_pairs())


def test_scan_found_editions():
    # A glob that silently matched nothing would make every test below pass.
    assert len(PAIRS) >= 8, [k for k, *_ in PAIRS]


@pytest.mark.parametrize("key,si,m", PAIRS, ids=[f"{a}/{b}" for (a, b), *_ in PAIRS])
def test_si_matches_its_manuscript(key, si, m):
    found = _defects(si, m)
    expected = KNOWN_DEFECTS.get(key, set())
    assert not (found - expected), (
        f"{key}: SI disagrees with {m.name} on {sorted(found - expected)}")
    assert not (expected - found), (
        f"{key}: {sorted(expected - found)} is fixed; remove it from "
        f"KNOWN_DEFECTS so the gate is strict for this edition again")


def test_h1_v6_si_is_strict():
    """The shipped period SI: exact title, exact citation count, no allowance."""
    st = (H1 / "supplementary_v6.md").read_text(encoding="utf-8")
    mt = (H1.parent.parent / "runs" / "2026-H1" / "manuscript_v6.md"
          ).read_text(encoding="utf-8")
    title = manuscript_title(mt)
    assert title and "Cell to Module" in title
    assert si_title(st) == title
    n_refs, n_cited = measured_citations(mt)
    assert n_refs > 0 and n_cited > 0
    assert si_cited(st) == n_cited


@pytest.mark.parametrize("pdf", [H1 / "supplementary_v6.pdf",
                                 H1 / "chemrxiv" / "supplementary_v6.pdf"],
                         ids=["edition", "chemrxiv-package"])
def test_h1_v6_rendered_si_names_the_manuscript(pdf):
    """The RENDERED SI, both copies: the one in the edition and the one the
    ChemRxiv package uploads. The 17 Sep hand-patched PDF lived only in the
    package copy, which is how the two came to disagree."""
    pytest.importorskip("pymupdf")
    mt = (ROOT / "runs" / "2026-H1" / "manuscript_v6.md").read_text(
        encoding="utf-8")
    assert pdf.exists(), pdf
    assert pdf_front_has_title(pdf, manuscript_title(mt)), (
        f"{pdf.name}: front page does not carry the manuscript title")
    assert not pdf_front_has_title(
        pdf, "Buried-Interface Chemistry, Defect Tolerance")
    # The count too: the 17 Sep hand-patched PDF fixed the title but still
    # rendered "Cited in the main text 0", so a title check alone passed it.
    import re
    import pymupdf
    with pymupdf.open(str(pdf)) as doc:
        text = " ".join(p.get_text() for p in doc)
    got = re.search(r"Cited in the main text\s+(\d+)", text)
    assert got, f"{pdf.name}: no 'Cited in the main text' row rendered"
    assert int(got.group(1)) == measured_citations(mt)[1]


def test_counter_sees_both_marker_forms():
    """The unit behind the cited_zero defect, on a synthetic manuscript."""
    body = ("Text [\\href{https://doi.org/10.1/a}{1}] and "
            "[\\href{https://doi.org/10.1/b}{2}], plain [3], "
            "a C[60]fullerene, [100] growth.\n\n## References\n\n"
            "1. A\n2. B\n3. C\n")
    assert measured_citations(body) == (3, 3)


def _edition_files(ed: str):
    ver = ed.rsplit("_", 1)[1]
    d = MS / ed
    m = d / f"manuscript_{ver}.md"
    if ed == "2026-H1_v6":        # the edition copy is the v2 render's name
        m = ROOT / "runs" / "2026-H1" / "manuscript_v6.md"
    return d / f"supplementary_{ver}.md", m, d / f"supplementary_{ver}.pdf"


@pytest.mark.parametrize("ed", STRICT_RENDERED)
def test_rendered_si_prints_the_manuscript_count(ed):
    """Every shipped v4+ SI PDF, and its ChemRxiv copy where one exists,
    renders the count the manuscript body actually cites."""
    pytest.importorskip("pymupdf")
    import re
    import pymupdf
    _, m, pdf = _edition_files(ed)
    n_cited = measured_citations(m.read_text(encoding="utf-8"))[1]
    assert n_cited > 0
    for p in [pdf, pdf.parent / "chemrxiv" / pdf.name]:
        if p == pdf:
            assert p.exists(), p
        if not p.exists():
            continue
        with pymupdf.open(str(p)) as doc:
            text = " ".join(pg.get_text() for pg in doc)
        got = re.search(r"Cited in the main text\s+(\d+)", text)
        assert got, f"{p}: no 'Cited in the main text' row rendered"
        assert int(got.group(1)) == n_cited, (p, got.group(1), n_cited)


@pytest.mark.parametrize("ed", STRICT_RENDERED)
def test_funnel_figure_draws_table_s2(ed):
    """Figure S1's bars are Table S2's rows. The figure stages drew the last
    bar from stats.json's selection.n_cited, a pre-drafting cap: July's bar
    read 180 for a manuscript citing 79 and H1's read 209 against 184."""
    pytest.importorskip("pymupdf")
    import re
    from stages.si_facts import funnel_pdf_counts
    si, _, _ = _edition_files(ed)
    st = si.read_text(encoding="utf-8")
    rows = dict(re.findall(r"^\| (.+?) \| (\d+) \|[ \t]*$", st, re.M))
    want = [int(rows[k]) for k in _TABLE_S2]
    refs = re.findall(r"\]\(([^)]*?S2_corpus_funnel\.pdf)\)", st)
    assert len(refs) == 1, refs
    fig = pathlib.Path(refs[0])
    if not fig.is_absolute():      # the public tree rewrites to repo-relative
        fig = ROOT / fig
    assert funnel_pdf_counts(fig) == want, (fig, want)
    shipped = si.parent / "fig" / fig.name
    if shipped.exists():
        assert funnel_pdf_counts(shipped) == want, (shipped, want)
