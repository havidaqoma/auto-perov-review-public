"""The preprint target must stay ChemRxiv, and must not creep back to arXiv.

Why this file exists
--------------------
The submission target was arXiv from IDEA.md onwards, and by the time Havid
changed it (2026-09-09) the string `arxiv` had spread into a stage filename,
an output directory, a tarball stem, a `.done` marker key, a metadata schema
and six documents. That is the exact shape of drift this project already pays
for elsewhere: a value with no single definition, copied until nobody knows
which copy is authoritative.

Per handbook 0.2 a defect becomes an assertion rather than a prompt reminder.
The pipeline is autonomous and the monthly cron prompt is regenerated from
these documents, so a stale "prepare the arXiv bundle" instruction would
quietly reintroduce the old target on the next run. Hence gates, not memory.

THE DISTINCTION THESE TESTS PROTECT
-----------------------------------
arXiv has two unrelated meanings in this repo and only one of them moved:
  * HARVEST SOURCE -- stage 01 queries the arXiv API, stage 05 dedupes on
    arXiv IDs, the ledger has an `arxiv_id` column, cited works carry arXiv
    DOIs. Legitimate, permanent, must NOT be renamed. A blind
    s/arxiv/chemrxiv/ would have broken the harvest.
  * SUBMISSION TARGET -- now ChemRxiv. Only this meaning is gated below.
"""
from __future__ import annotations

import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
PREPRINT = CONFIG / "preprint.yaml"


def _p() -> dict:
    return yaml.safe_load(PREPRINT.read_text(encoding="utf-8"))


def test_preprint_config_exists_and_names_chemrxiv():
    """ONE definition of the platform. Everything else reads this file."""
    assert PREPRINT.exists(), "config/preprint.yaml is the platform contract"
    P = _p()
    assert P["platform"] == "ChemRxiv"
    assert P["platform_slug"] == "chemrxiv"
    assert "chemrxiv.org" in P["platform_url"]


def test_chemrxiv_subject_categories_not_arxiv_archive_codes():
    """ChemRxiv has subject categories. `physics.app-ph` is an arXiv archive
    code and is meaningless on a chemistry preprint server, so a dotted code
    here means the old metadata schema survived the migration."""
    P = _p()
    cats = [P["subject_category_primary"], *P["subject_categories_secondary"]]
    for c in cats:
        assert not re.match(r"^[a-z-]+\.[a-z-]+$", c), \
            f"{c!r} looks like an arXiv archive code, not a ChemRxiv category"
    assert P["subject_category_primary"] == "Energy", \
        ("Havid chose Energy as primary on 2026-09-09: perovskite PV is "
         "energy-device work.")
    # "Materials Chemistry" and "Materials Science" are DIFFERENT ChemRxiv
    # categories. Havid picked Materials Chemistry, so assert the exact label
    # rather than a substring that both would satisfy.
    assert P["subject_categories_secondary"] == ["Materials Chemistry"], \
        f'secondary must be exactly ["Materials Chemistry"], got {P["subject_categories_secondary"]}'


def test_preprint_doi_is_never_invented_by_a_script():
    """ChemRxiv assigns the DOI on posting. A DOI written before the preprint
    exists is a fabricated identifier, which is the one thing this pipeline
    must never produce. It stays null until a human pastes the real one."""
    P = _p()
    assert P["doi_prefix"] == "10.26434"
    assert P["preprint_doi"] is None, \
        ("preprint_doi must stay null until ChemRxiv assigns it on posting; "
         "if the preprint is now live, paste the REAL DOI here and update "
         "this test's intent deliberately")


def test_no_automated_submission_path_exists():
    """The human gate at submission is the design (PLAN Q17=b). Assert both
    the declared route and the absence of code that could post."""
    P = _p()
    assert P["submission_route"] == "manual_portal"
    assert P["api_submission_supported"] is False
    stage = (ROOT / "scripts" / "stages" / "s20_chemrxiv.py").read_text(
        encoding="utf-8")
    for forbidden in ("requests.post", "urllib.request.urlopen",
                      "httpx.post", "session.post"):
        assert forbidden not in stage, \
            f"stage 20 must not be able to submit: found {forbidden}"


def test_submission_stage_is_chemrxiv_and_the_arxiv_stage_is_gone():
    """A renamed file with the old name still referenced somewhere is how a
    migration half-lands."""
    assert (ROOT / "scripts" / "stages" / "s20_chemrxiv.py").exists()
    assert not (ROOT / "scripts" / "stages" / "s20_arxiv.py").exists(), \
        "the arXiv submission stage must not linger beside its replacement"


def _live_text_files() -> list[pathlib.Path]:
    """Active docs, configs and code. Excludes OLD/, archive/, runs/,
    manuscript/ and .staging/: those hold history and generated evidence, and
    rewriting the past to say ChemRxiv would be dishonest about what ran."""
    out: list[pathlib.Path] = []
    for pat in ("*.md", "config/*.yaml", "config/*.txt",
                "scripts/**/*.py", "tests/*.py"):
        for f in ROOT.glob(pat):
            out.append(f)
    for f in (ROOT / "scripts").rglob("*.py"):
        out.append(f)
    skip = ("OLD", "archive", "runs", "manuscript", ".staging", ".git",
            "__pycache__", "example of review paper")
    return sorted({f for f in out
                   if f.is_file() and not any(s in f.parts for s in skip)})


# Sentences that describe WHERE WE SUBMIT. A harvest-source mention of arXiv is
# fine; these are not. Kept narrow and specific on purpose: a broad "any line
# containing arxiv" rule would fire on the legitimate harvest documentation and
# get switched off, which is worse than no gate (handbook 7.6).
SUBMISSION_PHRASES = [
    r"submit\s+(?:it\s+|anything\s+)?to\s+arxiv",
    r"arxiv\s+submission\s+bundle",
    r"arxiv_metadata\.json",
    r"prepare\s+the\s+arxiv",
    r"published\s+into\s+arxiv",
    r"arxiv\s+tarball",
    r"s20_arxiv",
    r"20_arxiv\b",
]


# A line may NAME the old target while explaining that it was replaced. The
# Q68 decision row and the stage docstring both say "s20_arxiv became
# s20_chemrxiv", which is the migration record and must survive: deleting the
# history would leave the next author to re-derive why the target moved.
#
# So the exemption is narrow and evidence-based -- the same line must also
# mention the CURRENT target. A line that says only "prepare the arXiv bundle"
# is still a live instruction and still fails. Widening this to "any line
# containing chemrxiv anywhere in the file" would defeat the gate.
HISTORICAL_CONTEXT = re.compile(r"chemrxiv", re.I)


def test_no_live_file_still_targets_arxiv_for_submission():
    """The autonomous failure mode: a stale instruction in a document the cron
    prompt is built from, sending next month's run back to arXiv."""
    offenders: list[str] = []
    for f in _live_text_files():
        if f.name == pathlib.Path(__file__).name:
            continue  # this file quotes the patterns it forbids
        txt = f.read_text(encoding="utf-8", errors="replace")
        lines = txt.splitlines()
        for pat in SUBMISSION_PHRASES:
            for m in re.finditer(pat, txt, re.I):
                ln = txt.count("\n", 0, m.start())
                if HISTORICAL_CONTEXT.search(lines[ln] if ln < len(lines) else ""):
                    continue  # narrating the migration, not instructing it
                offenders.append(
                    f"{f.relative_to(ROOT)}:{ln + 1}: {m.group(0)!r}")
    assert not offenders, ("live files still target arXiv for submission:\n"
                           + "\n".join(offenders))


def test_arxiv_survives_as_a_harvest_source():
    """The other half of the contract. If a future cleanup does a blind
    s/arxiv/chemrxiv/ the harvest silently loses a source, so assert the
    legitimate meaning is still present."""
    harvest = (ROOT / "scripts" / "stages" / "s01_harvest.py").read_text(
        encoding="utf-8")
    assert "arxiv" in harvest.lower(), \
        "stage 01 must still harvest arXiv; it is a literature source"
    ledger = (ROOT / "scripts" / "common" / "ledger.py").read_text(
        encoding="utf-8")
    assert "arxiv_id" in ledger, \
        "the ledger's arxiv_id column identifies harvested preprints"


def test_cron_prompt_names_the_current_target():
    """The monthly prompt drives an unattended run; it must not be ambiguous
    about the target or about the hard stop before submitting."""
    txt = (CONFIG / "cron_prompt_monthly.txt").read_text(encoding="utf-8")
    assert "ChemRxiv" in txt
    assert re.search(r"do not submit", txt, re.I), \
        "the cron prompt must keep the explicit no-submission instruction"


def test_handbook_documents_the_chemrxiv_package():
    """§8.1 is what the operator follows to actually submit."""
    txt = (ROOT / "MASTER_HANDBOOK.md").read_text(encoding="utf-8")
    assert "ChemRxiv package" in txt
    assert "config/preprint.yaml" in txt, \
        "the handbook must point at the single platform definition"
    assert "10.26434" in txt, "the DOI-on-posting rule must be documented"
