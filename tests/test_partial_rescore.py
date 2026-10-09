"""Rescoring from a public clone when some abstracts no longer match.

The public tree ships a sha256 per abstract, and the rehydrator keeps only
re-fetched texts that match. A publisher revision therefore removes a text
from disk. These tests pin that (1) pool membership still comes from the
digest, (2) unverified text is never scored, (3) works with no abstract at
harvest are not counted as unrecovered, and (4) the partial check passes only
on identical rows and writes nothing.
"""
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "papers" / "scripts"))

from studies import study_common as sc  # noqa: E402


def sha(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def make_run(tmp: pathlib.Path, on_disk: dict, digest: dict) -> pathlib.Path:
    priv = tmp / "private"
    priv.mkdir(parents=True)
    (priv / "02_abstracts.jsonl").write_text(
        "".join(json.dumps({"work_key": k, "abstract": v}) + "\n" for k, v in on_disk.items()),
        encoding="utf-8")
    (priv / "ABSTRACTS_DIGEST_02_abstracts.json").write_text(json.dumps(
        {"digest": [{"work_key": k, "abstract_sha256": h} for k, h in digest.items()]}),
        encoding="utf-8")
    return tmp


def test_private_tree_without_digest_reads_everything(tmp_path):
    priv = tmp_path / "private"
    priv.mkdir()
    (priv / "02_abstracts.jsonl").write_text(
        json.dumps({"work_key": "W1", "abstract": "PCE 21.3%"}) + "\n", encoding="utf-8")
    abst, unrec = sc.read_abstracts(tmp_path)
    assert abst == {"w1": "PCE 21.3%"} and unrec == set()


def test_revised_lost_and_empty_abstracts(tmp_path):
    rd = make_run(
        tmp_path,
        on_disk={"W1": "kept text", "W2": "revised text"},
        digest={"W1": sha("kept text"), "W2": sha("original text"),
                "W3": sha("never re-fetched"), "W4": sc.EMPTY_SHA256})
    abst, unrec = sc.read_abstracts(rd)
    assert abst == {"w1": "kept text"}          # revised text is never scored
    assert unrec == {"w2", "w3"}                # empty-at-harvest W4 is not lost


def test_compare_partial_passes_only_on_identical_rows(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sc, "ROOT", tmp_path)
    stored = [{"work_key": "W1", "value": 1.0}, {"work_key": "W2", "value": 2.0},
              {"work_key": "W3", "value": 3.0}]
    out = tmp_path / "study.json"
    out.write_text(json.dumps({"meta": {}, "rows": stored}), encoding="utf-8")
    before = out.read_bytes()
    keep = lambda r: r["work_key"] != "W2"  # noqa: E731
    assert sc.compare_partial(out, [stored[0], stored[2]], keep, 1) == 0
    assert "PARTIAL CHECK PASSED: 2 of 3" in capsys.readouterr().out
    tampered = [stored[0], {"work_key": "W3", "value": 3.1}]
    assert sc.compare_partial(out, tampered, keep, 1) == 1
    assert "first difference at row 1" in capsys.readouterr().out
    assert sc.compare_partial(out, [stored[0]], keep, 1) == 1   # a dropped row fails too
    assert out.read_bytes() == before                            # nothing written
