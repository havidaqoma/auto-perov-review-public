"""Regression tests for the v4 writing pipeline.

Every test here corresponds to a defect that actually occurred or a threshold
that was actually decided. A test that encodes no incident is noise.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from stages.section_map import build_map, month_name, TITLE_BANK  # noqa: E402
from stages.s13d_draft_v4 import AGENT_NARRATION, clean  # noqa: E402
from stages.hygiene import (KNOWN_LEAKS, KNOWN_CLEAN,  # noqa: E402
                            strip_narration, find_narration)
from stages import hygiene, s13d_draft_v4, s18d_build_v4, s19_si  # noqa: E402
from stages.s18d_build_v4 import (novelty_gate, resolve_placeholders,  # noqa: E402
                                  canon_work_key, _strip_back_matter)

CONFIG = ROOT / "config"
GATES = yaml.safe_load((CONFIG / "gates.yaml").read_text(encoding="utf-8"))


# --- month derivation -----------------------------------------------------
def test_month_name_derives_and_crosses_year_boundary():
    """v3 hardcoded 'July 2026' in five places; an August run drafted August
    evidence under July headings."""
    assert month_name("2026-08") == "August 2026"
    assert month_name("2026-07") == "July 2026"
    assert month_name("2026-12") == "December 2026"
    assert month_name("2027-01") == "January 2027"


def test_no_july_literal_in_the_v4_code_path():
    """The Figure 1 caption kept a 'July 2026' literal through the whole
    August build and only a human reading the PDF caught it."""
    for name in ("s13d_draft_v4.py", "s18d_build_v4.py", "section_map.py"):
        src = (ROOT / "scripts" / "stages" / name).read_text(encoding="utf-8")
        code = "\n".join(ln for ln in src.splitlines()
                         if not ln.lstrip().startswith("#"))
        code = re.sub(r'""".*?"""', "", code, flags=re.S)
        assert "July 2026" not in code, f"{name} carries a month literal"


# --- section map ----------------------------------------------------------
def _stats(month: str) -> dict:
    ptr = ROOT / "runs" / f"{month}.active"
    if not ptr.exists():
        pytest.skip(f"no run for {month}")
    rd = ROOT / "runs" / ptr.read_text(encoding="utf-8").strip()
    return json.loads((rd / "stats.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("month", ["2026-07", "2026-08"])
def test_section_map_shape(month):
    m = build_map(month, _stats(month))
    roles = [s["role"] for s in m["sections"]]
    assert roles[0] == "intro"
    assert roles[1] == "frontier"
    assert roles[-1] == "gaps", "Research Gaps must be the last section"
    assert 4 <= roles.count("mechanism") <= 5
    ids = [s["id"] for s in m["sections"]]
    assert ids == [str(i + 1) for i in range(len(ids))], "ids must be 1..n"


@pytest.mark.parametrize("month", ["2026-07", "2026-08"])
def test_section_map_is_deterministic(month):
    """Same inputs must give the same map, or resumes would redraft forever."""
    s = _stats(month)
    assert build_map(month, s)["sha256"] == build_map(month, s)["sha256"]


def test_section_map_follows_evidence_mass():
    """August depth tier: defects 42, interfaces 32, composition 25,
    architecture 17, stability 16, scale_up 12. v3 gave scale_up (thinnest) a
    full section and composition (3rd largest) none."""
    m = build_map("2026-08", _stats("2026-08"))
    mech = [s for s in m["sections"] if s["role"] == "mechanism"]
    axes = [s["axis"] for s in mech]
    assert "composition" in axes, "composition earned a section in August"
    assert "defects" in axes and "interfaces" in axes
    ceilings = [s["ceiling"] for s in mech]
    assert ceilings == sorted(ceilings, reverse=True), \
        "ceilings must fall with evidence mass"


def test_every_axis_reaches_the_writer():
    """An axis without its own section must be folded into one that exists,
    never silently dropped."""
    m = build_map("2026-08", _stats("2026-08"))
    covered = {a for s in m["sections"] for a in s["axes"]}
    assert set(m["depth_distribution"]) <= covered


def test_titles_rotate_between_consecutive_months():
    """Two issues running the same axis must not reuse one phrasing."""
    j = {s["axis"]: s["title"] for s in build_map("2026-07", _stats("2026-07"))["sections"]}
    a = {s["axis"]: s["title"] for s in build_map("2026-08", _stats("2026-08"))["sections"]}
    shared = [ax for ax in j if ax and ax in a]
    assert shared, "expected overlapping axes between July and August"
    assert any(j[ax] != a[ax] for ax in shared), "titles did not rotate"


def test_title_bank_has_no_claim_words():
    banned = ("breakthrough", "unprecedented", "novel", "record",
              "superior", "remarkable")
    for axis, bank in TITLE_BANK.items():
        assert len(bank) >= 3, f"{axis} needs alternatives to rotate"
        for t in bank:
            assert not any(b in t.lower() for b in banned), f"{axis}: {t}"


# --- narration guard ------------------------------------------------------
def test_narration_guard_catches_every_known_leak_class():
    """26 inline (?i) groups made this regex crash the module at import on
    Python 3.11, so it must be re-proven after any edit."""
    leaks = [
        "Waiting for the task to complete.",
        "The command has been launched.",
        "Let me check the output.",
        "I will wait for the timer to fire.",
        "Saved to runs/2026-08/sec8.md",
        "This section is 1030 words, over the 900 limit.",
        "Gate checks pass.",
        "As requested, here is the section.",
        "OK: done.",
        "stdout was empty",
        "I have drafted the section.",
        "Now I will condense.",
        "Next, I will verify the counts.",
    ]
    missed = [s for s in leaks if not AGENT_NARRATION.search(s)]
    assert not missed, f"leak classes missed: {missed}"


def test_narration_guard_leaves_real_prose_alone():
    prose = [
        "Buried-interface passivation improves open-circuit voltage.",
        "Certified efficiency reached 27.12% on a 1.0 cm2 aperture.",
        "Wide-bandgap absorbers remain limited by halide segregation.",
        "Operational stability was tracked for 2125 h under one sun.",
        "Ion migration accelerates under forward bias.",
    ]
    hits = [s for s in prose if AGENT_NARRATION.search(s)]
    assert not hits, f"false positives: {hits}"


def test_clean_strips_per_line_not_per_section():
    """An early version discarded whole sections and threw away three usable
    drafts because one status line was wrapped around real content."""
    out = clean("Waiting for the task.\nIon migration accelerates.\nOK: done.")
    assert "Ion migration accelerates." in out
    assert "Waiting" not in out and "OK:" not in out


# --- abstract contract ----------------------------------------------------
def _cards(month: str) -> list:
    ptr = ROOT / "runs" / f"{month}.active"
    if not ptr.exists():
        pytest.skip(f"no run for {month}")
    rd = ROOT / "runs" / ptr.read_text(encoding="utf-8").strip()
    f = rd / "claim_cards.jsonl"
    return [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]


def test_placeholders_resolve_to_canonical_numbers():
    """The writer never sees a digit; this substitution is the only path a
    number takes into the abstract."""
    S, cl = _stats("2026-08"), _cards("2026-08")
    ab, vals, used = resolve_placeholders(
        "This month {{N_CORPUS}} works, {{N_DEPTH}} read closely, "
        "top certified {{P_TOP_CERT}}.", S, cl)
    assert "{{" not in ab
    assert str(S["corpus.n"]) in ab and str(S["selection.n_depth"]) in ab
    assert set(used) == {"N_CORPUS", "N_DEPTH", "P_TOP_CERT"}


def test_work_key_canon_recovers_a_dropped_elsevier_prefix():
    """June 2026: the writer cited "10.1016/joule.2026.102538" for the card
    "10.1016/j.joule.2026.102538". G1 correctly refused it. The alias lookup
    recovers the intended card without widening the gate, because the two keys
    share one canonical form."""
    assert (canon_work_key("10.1016/joule.2026.102538")
            == canon_work_key("10.1016/j.joule.2026.102538"))


def test_work_key_canon_does_not_collide_across_real_papers():
    """The canonical form is lossy, so it is only safe while distinct papers
    stay distinct. Assert that on every real card of both shipped months: if
    two cards ever collapsed together, the alias lookup would have to fail
    closed rather than pick one."""
    for month in ("2026-07", "2026-08"):
        keys = [c["work_key"] for c in _cards(month)]
        canon = [canon_work_key(k) for k in keys]
        dupes = {c for c in canon if canon.count(c) > 1}
        assert not dupes, f"{month}: canonical collision {dupes}"


def test_p_top_sj_rejects_a_tandem_value_whose_title_looks_single_junction():
    """June 2026 shipped "32.95% in single-junction inverted cells" in its
    abstract. 32.95% is a perovskite/Si tandem, stated as such in the card's
    own anchor, and it is above the single-junction Shockley-Queisser limit,
    so it could not have been a single cell at all. The old filter tested only
    the TITLE, and that paper's title names neither tandem nor silicon while
    its abstract reports a tandem result beside its own single-junction one.

    The anchor is the text that was verified verbatim against the source, so
    the anchor decides what the number describes. Havid found this by reading
    the PDF and checking the source abstract."""
    card = {
        "work_key": "10.1038/s41467-026-73276-w",
        "title": ("Buried-interface homogenization by asymmetric polymeric "
                  "self-assembled layers powers efficient, durable flexible "
                  "perovskite photovoltaics"),
        "device": {"architecture": "p-i-n"},
        "performance": {"pce_certified": {
            "value": 32.95,
            "anchor": "a certified 32.95% perovskite/Si tandem efficiency"}},
        "stability": {},
    }
    single = {
        "work_key": "10.0000/single",
        "title": "A passivation strategy for inverted perovskite solar cells",
        "device": {"architecture": "p-i-n"},
        "performance": {"pce_certified": {
            "value": 27.28,
            "anchor": "achieved certified power conversion efficiency of 27.28%"}},
        "stability": {},
    }
    S = {"corpus.n": 600, "selection.n_depth": 150,
         "audit.corpus.efficiency_stated.pct": 48.1,
         "audit.corpus.certified.pct": 5.9}
    out, used, missing = resolve_placeholders("top single junction {{P_TOP_SJ}}",
                                              S, [card, single])
    assert "32.95" not in out, "a tandem value was reported as single junction"
    assert "27.28" in out, f"expected the real single junction value: {out!r}"



def test_unknown_placeholder_fails_closed():
    """A hole in the abstract must stop the build, never ship."""
    S, cl = _stats("2026-08"), _cards("2026-08")
    with pytest.raises(SystemExit):
        resolve_placeholders("bogus {{P_NOT_A_TOKEN}} here", S, cl)


def test_abstract_word_band_is_actually_configured():
    """gates.yaml carried abstract_word_max: 250 while the August abstract
    shipped 326 words and no gate read it."""
    lo, hi = GATES["abstract"]["word_band"]
    assert lo < hi and 200 <= lo <= 300 and 300 <= hi <= 400


# --- G8 novelty -----------------------------------------------------------
def test_g8_thresholds_are_the_agreed_ones():
    n = GATES["novelty"]
    assert n["body_max_ratio"] == 0.25
    assert n["abstract_max_ratio"] == 0.30
    assert n["shingle_words"] == 12


def test_g8_skips_on_cold_start():
    """First issue of a new topic has nothing to compare against."""
    r = novelty_gate("1990-01", {"1": "text " * 60}, "abs " * 60,
                     {"sections": [{"id": "1", "title": "T"}]}, GATES)
    assert r["status"] == "skip"


def test_g8_strips_back_matter_before_comparing():
    """631 of the first self-test's shared shingles were the funding number
    and the AI declaration, which MUST repeat every month."""
    md = ("## 1. Intro\nreal prose here\n\n## Acknowledgements\n"
          "financial support from Xiamen University Malaysia\n"
          "## References\n1. something\n")
    out = _strip_back_matter(md)
    assert "real prose here" in out
    assert "Xiamen" not in out and "References" not in out


def test_g8_ignores_mandated_abbreviation_expansions():
    """G7 requires "ISOS" to be expanded at first use and the build inserts
    that expansion itself, so the long form recurs in every issue by design.
    July 2026 failed G8 on six shingles that were all that expansion plus the
    DOI after it: G8 was failing prose for obeying G7. Text the pipeline
    authors cannot count as the writer reusing a sentence."""
    long = "International Summit on Organic Photovoltaic Stability"
    shared = (f"only four papers named an {long} (ISOS) protocol "
              "https://doi.org/10.1002/adma.74243 in this sample ")
    prior = ROOT / "runs" / "2026-06_cf764cbb" / "manuscript_v4.md"
    if not prior.exists():
        pytest.skip("June v4 manuscript not present")
    secs = {"1": shared + ("wholly different words about contacts here " * 12)}
    smap = {"sections": [{"id": "1", "title": "s1"}]}
    r = novelty_gate("2026-07", secs, "abs " * 60, smap, GATES,
                     prior_path=prior)
    assert not any(long.lower() in s for s in
                   r["detail"].get("shared_shingles", [])), \
        "a mandated expansion was counted as writer reuse"



def test_g8_would_have_failed_the_v3_august_issue():
    """This is the whole point of the gate: Havid caught the sameness by eye,
    so the gate must catch it mechanically.

    The prior file is named EXPLICITLY. This assertion is about a specific
    historical pair (August v3 vs July v3), and it silently began passing once
    July's run dir also held a manuscript_v4.md, because the gate compared
    against the newest prior it could find. A self-test that pins known-bad
    output must pin both sides of the comparison."""
    rd = ROOT / "runs" / "2026-08_b086357d"
    prior = ROOT / "runs" / "2026-07_197abe83" / "manuscript_v3.md"
    if not (rd / "manuscript_v3.md").exists() or not prior.exists():
        pytest.skip("August/July v3 manuscripts not present")
    t = (rd / "manuscript_v3.md").read_text(encoding="utf-8")
    ab = t.split("## Abstract")[1].split("##")[0]
    parts = re.split(r"\n## (\d)\. ", t)
    secs = {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}
    smap = {"sections": [{"id": k, "title": f"s{k}"} for k in secs]}
    r = novelty_gate("2026-08", secs, ab, smap, GATES, prior_path=prior)
    assert r["status"] == "fail", "G8 must reject the issue that prompted it"
    assert r["detail"]["n_shared_shingles"] > 0


# --- citation regex carried forward --------------------------------------
def test_cite_rx_ignores_iupac_nomenclature():
    """'[60]fullerene-phosphonic acid' was counted as citation 60 and failed
    G2b on a correctly ordered manuscript."""
    CITE_RX = r"\[(\d+(?:,\d+)*)\](?![A-Za-z])"
    text = "Anchoring [60]fullerene on SnO2 [12] improves contact [13]."
    found = [m.group(1) for m in re.finditer(CITE_RX, text)]
    assert found == ["12", "13"]


def test_cite_rx_still_flags_real_disorder():
    CITE_RX = r"\[(\d+(?:,\d+)*)\](?![A-Za-z])"
    seq, seen = [], set()
    for m in re.finditer(CITE_RX, "Alpha [5]. Beta [3]."):
        for g in m.group(1).split(","):
            if g not in seen:
                seen.add(g)
                seq.append(int(g))
    assert seq != sorted(seq)


# --- narration filter unification (August v4 shipped-PDF leak) -----------
def test_all_stages_share_one_narration_filter():
    """Three divergent copies existed. The build-side copy was the narrowest,
    so a line that slipped the draft filter ALSO passed G4 and reached the
    shipped August v4 PDF under the section 8 heading. Identity, not equality:
    equal-looking patterns drift, the same object cannot."""
    assert s13d_draft_v4.AGENT_NARRATION is hygiene.AGENT_NARRATION
    assert s13d_draft_v4.SELF_REF is hygiene.AGENT_NARRATION
    assert s19_si.SELF_REF is hygiene.AGENT_NARRATION
    assert hygiene.LEAK_RX is hygiene.AGENT_NARRATION


def test_the_august_v4_shipped_leak_is_caught():
    """The exact sentence Havid found by reading the rendered PDF."""
    s = "I have launched the search command and will wait for it to finish."
    assert AGENT_NARRATION.search(s)
    assert find_narration(s)
    kept, removed = strip_narration(
        s + chr(10) + "Ion migration accelerates under bias.")
    assert "Ion migration accelerates under bias." in kept
    assert len(removed) == 1


@pytest.mark.parametrize("s", KNOWN_LEAKS)
def test_every_known_leak_still_matches(s):
    """Grammar classes, not remembered strings: the old pattern wanted the
    exact phrase 'the command has been launched' and 'I will wait' adjacent,
    and missed all three clauses of the real sentence."""
    assert AGENT_NARRATION.search(s), f"leak class regressed: {s!r}"


@pytest.mark.parametrize("s", KNOWN_CLEAN)
def test_legitimate_prose_is_never_stripped(s):
    """'research' contains 'search'; a review says 'further research is
    required' and 'a systematic search of the literature'. Tool-noun and
    first-person scoping is what keeps those safe."""
    assert not AGENT_NARRATION.search(s), f"false positive: {s!r}"


def test_g4_is_fail_closed_on_narration():
    """G4 reported pass on leaked text, which is worse than no gate: it teaches
    you to trust output you should be checking. Any narration surviving to
    build time now fails the gate."""
    src = (ROOT / "scripts" / "stages" / "s18d_build_v4.py").read_text(encoding="utf-8")
    assert "find_narration(prose)" in src
    assert "LEAK_RX = (" not in src, "s18d must not carry a private copy again"


# --- guard 5: device label must describe the NUMBER, not the paper ---------
def test_certified_anchor_naming_a_tandem_forces_a_tandem_architecture():
    """June 2026 shipped "certified PCE reached 32.95%" under single-junction
    inverted cells, in the abstract AND in the body. The paper is a p-i-n
    flexible cell, so the label was right about the paper -- but the certified
    value's anchor reads "a certified 32.95% perovskite/Si tandem efficiency".
    One abstract held two devices and the label followed the wrong one.

    The same defect was then found in July (33.1%, a perovskite/silicon
    tandem labelled p-i-n), which is why this is a guard and not a one-off
    correction."""
    from repair_arch_from_anchor import needs_fix
    tandem_anchor = {
        "device": {"architecture": "p-i-n"},
        "performance": {"pce_certified": {
            "value": 32.95,
            "anchor": "a certified 32.95% perovskite/Si tandem efficiency"}}}
    assert needs_fix(tandem_anchor) == "tandem_2T"

    real_single = {
        "device": {"architecture": "p-i-n"},
        "performance": {"pce_certified": {
            "value": 26.8,
            "anchor": "a PCE of 27.12% (certified 26.80%) for small-area cells"}}}
    assert needs_fix(real_single) is None

    already_tandem = {
        "device": {"architecture": "tandem_2T"},
        "performance": {"pce_certified": {
            "value": 33.6,
            "anchor": "we achieved a certified efficiency of 33.6% tandem"}}}
    assert needs_fix(already_tandem) is None


def test_shipped_months_carry_no_tandem_value_labelled_single_junction():
    """The corrected cards stay corrected. This reads the real shipped runs, so
    a re-extraction that reintroduces the mislabel fails here."""
    from repair_arch_from_anchor import needs_fix
    for month, h in (("2026-06", "cf764cbb"), ("2026-07", "197abe83"),
                     ("2026-08", "b086357d")):
        f = ROOT / "runs" / f"{month}_{h}" / "claim_cards.jsonl"
        if not f.exists():
            continue
        bad = [json.loads(ln)["work_key"] for ln in
               f.read_text(encoding="utf-8").splitlines() if ln.strip()
               and needs_fix(json.loads(ln))]
        assert not bad, f"{month}: tandem value labelled single junction: {bad}"
