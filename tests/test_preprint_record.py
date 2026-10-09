"""The cover letter's preprint sentence comes from preprint.json and fails closed.

ACS asks the cover letter to name any preprint. The arXiv identifier exists
only after announcement, so an empty identifier must render a visible [CHECK],
never a guessed number, and a malformed one must stop the build.
"""
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if not (ROOT / "papers" / "scripts" / "build_cover_letter.py").exists():
    pytest.skip("the system-paper submission files are not part of the public release",
                allow_module_level=True)
SPEC = importlib.util.spec_from_file_location(
    "build_cover_letter", ROOT / "papers" / "scripts" / "build_cover_letter.py")


@pytest.fixture
def cl(tmp_path, monkeypatch):
    mod = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(mod)
    monkeypatch.setattr(mod, "PREPRINT", tmp_path / "preprint.json")
    return mod


def write(cl, **rec):
    base = {"server": "arXiv", "arxiv_id": None,
            "version_submitted_to_journal": "identical to the arXiv version"}
    base.update(rec)
    cl.PREPRINT.write_text(json.dumps(base), encoding="utf-8")


def test_missing_record_fails_closed(cl):
    with pytest.raises(SystemExit):
        cl.preprint_sentence()


def test_empty_identifier_renders_a_visible_check(cl):
    write(cl)
    s = cl.preprint_sentence()
    assert s.startswith("[CHECK:") and "arXiv" in s


def test_real_identifier_is_stated(cl):
    write(cl, arxiv_id="2610.01234")
    s = cl.preprint_sentence()
    assert "arXiv:2610.01234" in s and "[CHECK" not in s


@pytest.mark.parametrize("bad", ["2610.1", "arXiv:2610.01234", "10.48550/arXiv.2610.01234"])
def test_malformed_identifier_fails_closed(cl, bad):
    write(cl, arxiv_id=bad)
    with pytest.raises(SystemExit):
        cl.preprint_sentence()


def test_other_server_fails_closed(cl):
    write(cl, server="ChemRxiv")
    with pytest.raises(SystemExit):
        cl.preprint_sentence()


def test_repo_record_is_arxiv():
    rec = json.loads((ROOT / "papers/system/submission/preprint.json").read_text(encoding="utf-8"))
    assert rec["server"] == "arXiv"
