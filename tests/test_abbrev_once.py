"""An abbreviation is expanded once per document, not once per section.

The 2026-06 issue printed "International Summit on Organic Photovoltaic
Stability (ISOS)" four times: each section is drafted on its own, the writer
is told to spell out abbreviations at first use, and the build expanded each
section again. The 2026-07 issue also printed "(ISOS)-O-1", an expansion
spliced into a protocol designation.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from stages.boilerplate import expand_abbrev  # noqa: E402

FULL = "International Summit on Organic Photovoltaic Stability"


def _body(sections):
    done, out = [], []
    for s in sections:
        t, e = expand_abbrev(s, skip=done)
        done += e
        out.append(t)
    return " ".join(out)


def test_writer_expansions_collapse_after_the_first_section():
    body = _body([f"only 3 named an {FULL} (ISOS) protocol.",
                  f"aged under {FULL} (ISOS) protocols.",
                  f"tested under {FULL} (ISOS) ISOS-L-1 conditions."])
    assert body.count(FULL) == 1
    assert "under ISOS protocols" in body
    assert "under ISOS-L-1 conditions" in body


def test_designation_is_never_split():
    t, done = expand_abbrev("after 61 days of ISOS-O-1 outdoor aging")
    assert "(ISOS)-O-1" not in t
    assert f"{FULL} (ISOS) ISOS-O-1" in t
    assert done == ["ISOS"]


def test_bare_first_use_still_expands_once():
    body = _body(["devices under ISOS testing.", "a second ISOS mention."])
    assert body.count(FULL) == 1


@pytest.mark.skipif(not (ROOT / "papers" / "scripts" / "build_paper.py").exists(),
                    reason="the system-paper builder is not part of the public release")
def test_paper_builder_copy_behaves_the_same():
    # papers/scripts/build_paper.py carries its own expand_abbrev; a NameError
    # in its skip branch once reached a commit because no test imported it.
    sys.path.insert(0, str(ROOT / "papers" / "scripts"))
    import build_paper
    done, out = [], []
    for sec in (f"under {FULL} (ISOS) protocols.", f"and {FULL} (ISOS) ISOS-L-1 tests."):
        t, e = build_paper.expand_abbrev(sec, skip=done)
        done += e
        out.append(t)
    body = " ".join(out)
    assert body.count(FULL) == 1 and "and ISOS-L-1 tests" in body
