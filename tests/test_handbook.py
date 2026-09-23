"""The handbook must not drift from the code it documents.

MASTER_HANDBOOK.md is the monthly operating contract: the operator reads it,
then runs what it says. Every defect class in it exists because a document and
an artifact disagreed and the document was believed.

So the handbook gates itself. Per §0.2, a defect becomes an assertion, and
"the handbook went stale" is a defect class this project has already paid for
twice: it listed G5 as a live gate when G5 existed only in the retired v1
build, and it documented the `[60]`/`[100]` nomenclature guard while only one
of two consumers applied it.
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
from stages.editions import build_gate_report  # noqa: E402

HANDBOOK = ROOT / "MASTER_HANDBOOK.md"
TEXT = HANDBOOK.read_text(encoding="utf-8")


def test_handbook_exists_and_is_versioned():
    assert HANDBOOK.exists()
    m = re.search(r"\*\*Version (\d+\.\d+)", TEXT)
    assert m, "handbook must carry a version line"
    assert float(m.group(1)) >= 2.0


def _referenced_paths() -> set[str]:
    """Every scripts/... and config/... path the handbook names."""
    pats = [
        r"`(scripts/[\w/]+\.py)`",
        r"`(config/[\w]+\.yaml)`",
        r"^python (scripts/[\w/]+\.py)",
        r"python (scripts/[\w/]+\.py)",
    ]
    out: set[str] = set()
    for p in pats:
        out |= set(re.findall(p, TEXT, re.M))
    return out


def test_every_referenced_script_and_config_exists():
    """A handbook naming a file that does not exist sends the operator to a
    dead path mid-run."""
    missing = sorted(p for p in _referenced_paths() if not (ROOT / p).exists())
    assert not missing, f"handbook references non-existent paths: {missing}"


def test_no_reference_to_archived_stages_in_run_commands():
    """OLD/ holds superseded stages. The run commands must never name one."""
    runlines = [ln for ln in TEXT.splitlines()
                if "python scripts/stages/" in ln and not ln.lstrip().startswith("#")]
    joined = "\n".join(runlines)
    for retired in ("s13c_draft_v3", "s18c_build_v3", "s13b_draft_v2",
                    "s18b_build_v2", "s12_brief", "s13_draft.py",
                    "s18_build.py", "s11_figures.py"):
        assert retired not in joined, \
            f"run commands still call retired stage {retired}"


def _gate_report() -> dict | None:
    """Every gate report on disk, merged, newest month last.

    This used to try 2026-08 then 2026-07 in a fixed order. A gate added while
    building a different month then looked like a phantom: the handbook
    documented G3c, the build emitted it into June's report, and the test
    compared against August's, written before the gate existed.

    The §6 table is a claim about what THE BUILD emits, not about what one
    arbitrary run emitted, so the union across runs is the honest comparison.
    A gate absent from every report on disk is still a phantom and still
    fails.
    """
    merged: dict = {}
    for ptr in sorted((ROOT / "runs").glob("*.active")):
        rd = ROOT / "runs" / ptr.read_text(encoding="utf-8").strip()
        f = build_gate_report(ROOT, rd)
        if f.exists():
            merged.update(json.loads(f.read_text(encoding="utf-8")))
    return merged or None


def test_gate_table_matches_a_real_gate_report():
    """The §6 table is the operator's list of what must pass. If the build
    emits a gate the table omits, nobody checks it; if the table lists a gate
    the build never emits, the operator waits for a result that never comes.
    That second failure is exactly what happened with G5 in v3."""
    rep = _gate_report()
    if rep is None:
        pytest.skip("no v4 gate report on disk yet")

    emitted = {k for k in rep if not k.startswith("_")}   # _regate is info
    # Gate names appear in the §6 table as **G1-cite** etc. Match the prefix
    # up to the first dash so table prose can stay readable.
    documented = set()
    for m in re.finditer(r"\*\*(G\d+[a-z]?)(?:-[\w-]+)?\*\*", TEXT):
        documented.add(m.group(1))
    emitted_short = {re.match(r"(G\d+[a-z]?)", k).group(1) for k in emitted}

    undocumented = emitted_short - documented
    assert not undocumented, \
        f"build emits gates the handbook does not document: {sorted(undocumented)}"

    phantom = documented - emitted_short
    assert not phantom, \
        f"handbook documents gates the build never emits: {sorted(phantom)}"


def test_documented_thresholds_match_config():
    """Numbers in the handbook must be the numbers the code reads. A handbook
    threshold that disagrees with gates.yaml invites the operator to 'fix' the
    wrong one."""
    G = yaml.safe_load((ROOT / "config" / "gates.yaml").read_text(encoding="utf-8"))
    checks = [
        (str(G["novelty"]["body_max_ratio"]), "G8 body ratio"),
        (str(G["novelty"]["abstract_max_ratio"]), "G8 abstract ratio"),
        (str(G["novelty"]["shingle_words"]), "G8 shingle length"),
        (str(G["abstract"]["word_band"][0]), "abstract band floor"),
        (str(G["abstract"]["word_band"][1]), "abstract band ceiling"),
        (str(G["citations"]["total_band"][0]), "citation band floor"),
        (str(G["citations"]["total_band"][1]), "citation band ceiling"),
        (str(G["count_band"][0]), "corpus count band floor"),
        (str(G["count_band"][1]), "corpus count band ceiling"),
        (str(G["anchor_word_max"]), "anchor word cap"),
    ]
    missing = [label for val, label in checks if val not in TEXT]
    assert not missing, f"handbook omits or contradicts config values: {missing}"


def test_section_map_knobs_documented():
    """§4.1 tabulates the map knobs. If a knob changes in code and not in the
    handbook, the operator cannot predict the issue's shape."""
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from stages import section_map as sm

    for name, val in (("MIN_DEPTH", sm.MIN_DEPTH),
                      ("BODY_WORDS", sm.BODY_WORDS),
                      ("WORDS_PER_CITE", sm.WORDS_PER_CITE)):
        assert name in TEXT, f"{name} not documented"
        assert str(val) in TEXT, f"{name} value {val} not in handbook"


def test_model_assignment_matches_config():
    """The §2 table is how the operator knows which model to expect in a log."""
    M = yaml.safe_load((ROOT / "config" / "models.yaml").read_text(encoding="utf-8"))
    assert M["generator"]["model"] in TEXT, "writer model not documented"
    assert M["extractor"]["model"] in TEXT, "extractor model not documented"


def test_monthly_checklist_is_present_and_ordered():
    """The checklist is the thing a tired operator follows at 2am."""
    assert "## 11. The monthly checklist" in TEXT
    body = TEXT.split("## 11. The monthly checklist")[1].split("## 12.")[0]
    steps = re.findall(r"^\[ \] (\d+)\.", body, re.M)
    assert steps, "checklist has no numbered steps"
    assert [int(x) for x in steps] == sorted(int(x) for x in steps), \
        "checklist steps are out of order"
    # the two irreplaceable ones
    assert "verify_anchors" in body, "checklist omits the anchor verification"
    assert "READ THE PDF" in body, "checklist omits the human PDF read"


def test_handbook_records_the_narration_leak_incident():
    """The worst class of defect: a gate reporting pass on bad output. If this
    story ever leaves the handbook, the next author will re-derive the filter
    from remembered sentences and reopen the same hole."""
    assert "I have launched the search command" in TEXT
    assert "hygiene.py" in TEXT
    for phrase in ("worse than no gate", "grammar of the failure"):
        assert phrase in TEXT, f"handbook lost the lesson: {phrase!r}"
