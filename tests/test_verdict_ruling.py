"""The hand-verdict error rule is an operator ruling, never a scorer default.

Both evaluation scorers must read `counts_as_error` from the review file and
fail closed if it is absent or names an unknown class. A disagreement on the
verdict page is accepted only when verdict_rulings.json resolves it.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
ST = ROOT / "papers" / "studies"


def test_review_files_carry_a_ruled_error_rule():
    rl = json.loads((ST / "verdict_rulings.json").read_text(encoding="utf-8"))
    assert rl["ruled_by"]
    for f in ("r3_ungrounded_review.json", "r5_ungrounded_review.json"):
        rv = json.loads((ST / f).read_text(encoding="utf-8"))
        assert rv["counts_as_error"] == ["wrong"], f
        assert set(rv["counts_as_error"]) <= set(rv["classes"]), f
    # the ruling changes the error rule, not the verdicts it applies to
    have = set()
    for f, tag in (("r3_ungrounded_review.json", "R3"), ("r5_ungrounded_review.json", "R5")):
        for r in json.loads((ST / f).read_text(encoding="utf-8"))["rows"]:
            if r["verdict"] == "footprint_as_area":
                have.add(f"{tag}|{r['work_key']}|{r['field']}|{r['value']}")
    assert have == set(rl["applies_to"])


def test_scorers_have_no_hardcoded_error_class():
    for f in ("rescore_metric.py", "ablation_gate.py"):
        src = (ROOT / "papers" / "scripts" / "studies" / f).read_text(encoding="utf-8")
        assert 'rv.get("counts_as_error")' in src, f
        assert "FAIL-CLOSED: review file lacks a valid counts_as_error ruling" in src, f


def test_confirmation_has_no_unresolved_disagreement():
    c = json.loads((ST / "verdict_confirmation.json").read_text(encoding="utf-8"))
    assert c["n_unresolved"] == 0
    assert all(d["resolved_by"] for d in c["disagreements"])


def test_second_labeller_result_is_a_real_file():
    k = json.loads((ST / "interrater_kappa.json").read_text(encoding="utf-8"))["meta"]
    assert (ST / "label_sheet" / "r1_second_filled.csv").exists()
    assert k["n_judgements"] == 100 and k["n_papers"] == 20
