"""Regression tests for deterministic notation formatting.

Every case here is either a defect Havid found in the shipped August v4 PDF
("cm2", "V-1", "Na+", "PbI2") or a near-miss that shaped the protection rules
while the module was written.
"""
from __future__ import annotations

import pathlib
import re
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from stages.notation import (KNOWN_FIXES, KNOWN_UNTOUCHED,  # noqa: E402
                             check_notation, format_notation)


@pytest.mark.parametrize("src,want", KNOWN_FIXES)
def test_known_notation_fixes(src, want):
    got, _ = format_notation(src)
    assert got == want


@pytest.mark.parametrize("src", KNOWN_UNTOUCHED)
def test_protected_text_is_byte_identical(src):
    """Existing math, DOIs, hyperlinks and domain vocabulary must survive."""
    got, _ = format_notation(src)
    assert got == src


def test_formatting_is_idempotent():
    """A second pass must change nothing, or a rebuild would double-wrap
    "cm$^2$" into "cm$^$^2$$"."""
    src = ("Aperture 61.2 cm2 with Pb2+ and residual PbI2 on SnO2, "
           "mobility 12 cm2 V-1 s-1, Na+ drift, C60 anchoring.")
    once, _ = format_notation(src)
    twice, counts = format_notation(once)
    assert twice == once
    assert not counts, f"second pass still substituted: {counts}"


def test_doi_digits_are_never_mangled():
    src = "see https://doi.org/10.1002/adma.74461 and 10.1038/s41467-026-76266-0"
    got, _ = format_notation(src)
    assert "10.1002/adma.74461" in got
    assert "10.1038/s41467-026-76266-0" in got
    assert "$" not in got


def test_hyperlinked_citation_survives():
    """Citations become \\href{...}{[12]}; formatting must not touch either
    the target or the label. Updated for the siunitx migration: the expected
    unit is now \\qty{}, not $^2$."""
    src = r"passivation improves Voc \href{https://doi.org/10.1/x}{[12]} at 1.0 cm2"
    got, _ = format_notation(src)
    assert r"\href{https://doi.org/10.1/x}{[12]}" in got
    assert r"\qty{1.0}{\centi\meter\squared}" in got


def test_defined_terms_are_not_notation():
    for term in ("T80", "ISOS-L-1", "p-i-n", "2T", "TOPCon", "C60-PA",
                 "I-V curve"):
        got, _ = format_notation(f"the {term} value")
        assert term in got, f"{term} was mangled into {got!r}"


def test_check_notation_flags_the_shipped_defects():
    """The gate must fail on exactly what Havid found. Labels were renamed in
    the siunitx migration ("unit exponent" -> "unit flat exponent") because
    the v2 gate distinguishes flat-vs-scripted rather than present-vs-absent."""
    bad = "aperture 61.2 cm2, Na+ drift, PbI2 residue, 12 cm2 V-1 s-1"
    rep = check_notation(bad)
    assert rep["defects"], "gate missed the shipped defect classes"
    labels = set(rep["defects"])
    assert "unit flat exponent" in labels
    assert "unit flat inverse" in labels
    assert "flat cation" in labels
    assert "flat formula" in labels


def test_gate_sees_unicode_minus_too():
    """THE v1 bug: the writer emits U+2212 and the ASCII-only gate reported
    PASS on the broken electron-mobility line. Both alphabets must fail."""
    ascii_bad = "mobility 12 cm2 V-1 s-1"
    uni_bad = "mobility 12 cm2 V\u22121 s\u22121"
    for src in (ascii_bad, uni_bad):
        rep = check_notation(src)
        assert rep["defects"], f"gate blind to {src!r}"


def test_ordinary_numbers_are_not_powers_of_ten():
    """Tenth instance of 7.3: `\\b10[-\u2212]?\\d\\b` with an OPTIONAL minus
    matched "100", "101", "102" and failed the whole manuscript on page
    counts and paper counts. The minus is required."""
    for src in ("100 nm thick", "105 papers were read", "at 102 K",
                "1015 works indexed"):
        rep = check_notation(src)
        assert "power of ten flat" not in rep["defects"], \
            f"false positive on {src!r}"
    rep = check_notation("a coefficient of 10-3 here")
    assert "power of ten flat" in rep["defects"]


def test_an_unknown_unit_does_not_drop_its_neighbours():
    """July 2026: the writer reported an interfacial fracture energy of
    "0.94 to 4.82 J m-2". "J" was missing from _UNITS, so the unit RUN
    "J m-2" could not match at all and G9a reported the surviving "m-2" as
    flat on the rendered page. The lesson is not "add J" -- it is that a
    unit run fails as a whole, so one unknown token silently leaves every
    unit beside it in plain text."""
    for src in ("fracture energy rose to 4.82 J m-2 after treatment",
                "a pulse energy of 12 mJ cm-2 was used"):
        got, _ = format_notation(src)
        assert "\\qty{" in got, f"joule quantity not converted: {src!r}"
        assert not check_notation(got)["defects"], \
            f"still defective after formatting: {src!r} -> {got!r}"


def test_journal_abbreviations_are_not_read_as_units():
    """Adding "J" must not make "J. Mater. Chem." a quantity. A unit needs a
    preceding value, so an abbreviation with no number stays prose."""
    src = "reported in J. Mater. Chem. A and elsewhere"
    got, _ = format_notation(src)
    assert got == src, f"journal name was rewritten: {got!r}"



def test_e_notation_values_are_typeset():
    """June 2026: the writer wrote "1.6e17 cm-3" rather than
    "1.6 x 1017 cm-3". _VAL matched only the second spelling, so the whole
    quantity was skipped, the unit shipped flat, and G9a reported
    "unit flat inverse: cm-3" on the rendered page. A writer may spell a power
    of ten either way and both must be typeset."""
    for src in ("densities up to 1.6e17 cm-3 confirm",
                "traps at 3.2E15 cm-3 remain",
                "a mobility of 1.3e-3 cm2 V-1 s-1 was measured"):
        got, _ = format_notation(src)
        assert "\\qty{" in got, f"e-notation quantity not converted: {src!r}"
        assert not check_notation(got)["defects"], \
            f"still defective after formatting: {src!r} -> {got!r}"


def test_e_notation_exponent_sign_is_siunitx_safe():
    """siunitx rejects a '+' exponent, so 1.6E+17 must normalise to 1.6e17."""
    got, _ = format_notation("a density of 1.6E+17 cm-3 here")
    assert "\\qty{1.6e17}{" in got, got


def test_check_notation_is_clean_after_formatting():
    bad = ("aperture 61.2 cm2, Na+ and Pb2+ drift, PbI2 on SnO2, "
           "12 cm2 V-1 s-1, C60 layer")
    good, _ = format_notation(bad)
    rep = check_notation(good)
    assert not rep["defects"], f"still defective after formatting: {rep}"


def test_anions_are_reported_not_converted():
    """"I-" is ambiguous: "I-V curve" is a real term. A silent wrong guess in
    a formula is worse than a flagged one, so anions are report-only."""
    src = "the I- species migrates"
    got, _ = format_notation(src)
    assert got == src, "bare anion must not be auto-converted"
    rep = check_notation(src)
    assert rep["ambiguous"], "bare anion should be reported for human review"


def test_real_august_drafts_format_clean():
    """The actual shipped drafts must contain no residual defects after a
    formatting pass."""
    dd = ROOT / "runs" / "2026-08_b086357d" / "draft_v4"
    if not dd.exists():
        pytest.skip("August drafts not present")
    residual = {}
    for f in sorted(dd.glob("*.md")):
        out, _ = format_notation(f.read_text(encoding="utf-8"))
        rep = check_notation(out)
        if rep["defects"]:
            residual[f.name] = rep["defects"]
    assert not residual, f"drafts still defective: {residual}"


def test_august_drafts_actually_needed_formatting():
    """Guard against a no-op formatter passing the test above by doing nothing:
    the August drafts are known to contain cm2, Pb2+, PbI2 and friends."""
    dd = ROOT / "runs" / "2026-08_b086357d" / "draft_v4"
    if not dd.exists():
        pytest.skip("August drafts not present")
    total = 0
    for f in sorted(dd.glob("*.md")):
        _, counts = format_notation(f.read_text(encoding="utf-8"))
        total += sum(counts.values())
    assert total > 20, f"expected many substitutions, got {total}"
