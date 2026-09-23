"""Every final manuscript names the public repository in its Data Availability
Statement, and the build emits the same statement for every future issue.

The link was added on 2026-09-23 when the reproducibility repository went
public. It is defined once (stages.boilerplate.REPO_URL). This test reads the
shipped markdown AND the rendered PDF, because a statement in the markdown
that never reached the PDF is the failure mode handbook 10.1 warns about.
"""
import pathlib
import re
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from stages import editions  # noqa: E402
from stages.boilerplate import REPO_URL, data_availability  # noqa: E402


def _yearly(stem: str, ext: str) -> pathlib.Path:
    return ROOT / "yearly" / "manuscript" / "2025_yearly" / f"{stem}_yearly{ext}"


def _docs():
    for p in editions.FINAL:
        yield (p, editions.manuscript_md(ROOT, p),
               editions.edition_file(ROOT, p, "manuscript", ".pdf"))
    yield "2025-yearly", _yearly("manuscript", ".md"), _yearly("manuscript", ".pdf")


DOCS = list(_docs())


def _statement(md: str) -> str:
    m = re.search(r"## Data Availability Statement\s*\n\s*\n(.+?)\n", md)
    assert m, "no Data Availability Statement"
    return m.group(1).strip()


@pytest.mark.parametrize("period,md,pdf", DOCS, ids=[d[0] for d in DOCS])
def test_statement_links_the_public_repository(period, md, pdf):
    st = _statement(md.read_text(encoding="utf-8"))
    word = ("year" if period.endswith("yearly") else
            "half-year" if "-H" in period else "month")
    assert st == data_availability(word), period


@pytest.mark.parametrize("period,md,pdf", DOCS, ids=[d[0] for d in DOCS])
def test_rendered_pdf_carries_a_live_link(period, md, pdf):
    pymupdf = pytest.importorskip("pymupdf")
    with pymupdf.open(str(pdf)) as doc:
        uris = [lk.get("uri") for pg in doc for lk in pg.get_links()]
    assert REPO_URL in uris, f"{pdf.name}: no clickable link to {REPO_URL}"


def test_every_build_emits_the_shared_statement():
    """Monthly/H1 and yearly builds must call the shared function, not carry
    their own copy of the paragraph."""
    for rel in ("scripts/stages/s18d_build_v4.py",
                "yearly/scripts/stages/s18y_build_yearly.py",
                "yearly/scripts/stages/s18d_build_v4.py"):
        src = (ROOT / rel).read_text(encoding="utf-8")
        assert "data_availability(" in src, rel
        assert "are provided as Supplementary \"\n" not in src, rel
