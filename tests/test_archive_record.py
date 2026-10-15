"""The Zenodo archive DOI is recorded once (docs/archive.json); every other
place that repeats it must agree, and a malformed record must fail closed."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARCH = ROOT / "docs" / "archive.json"
sys.path.insert(0, str(ROOT / "scripts"))

pytestmark = pytest.mark.skipif(not ARCH.exists(), reason="no archive record")


def _rec():
    return json.loads(ARCH.read_text(encoding="utf-8"))


def test_boilerplate_reads_the_record():
    from stages import boilerplate
    assert boilerplate.ARCHIVE_DOI == _rec()["concept_doi"]


@pytest.mark.parametrize("rel", ["scripts/release/overlay/README.md",
                                 "scripts/release/overlay/CITATION.cff",
                                 "README.md", "CITATION.cff"])
def test_repeated_dois_agree(rel):
    p = ROOT / rel
    if not p.exists():
        pytest.skip(f"{rel} not in this tree")
    text = p.read_text(encoding="utf-8")
    if "zenodo" not in text.lower():
        pytest.skip(f"{rel} does not cite the archive")
    rec = _rec()
    assert rec["concept_doi"] in text
    for v in rec["versions"]:
        assert v["doi"] in text, (rel, v["doi"])


def test_malformed_record_fails_closed(tmp_path, monkeypatch):
    from stages import boilerplate
    bad = dict(_rec(), concept_doi="10.5281/zenodo.")
    f = tmp_path / "archive.json"
    f.write_text(json.dumps(bad), encoding="utf-8")
    monkeypatch.setattr(boilerplate, "_ARCHIVE_FILE", f)
    with pytest.raises(ValueError):
        boilerplate._load_archive_doi()
