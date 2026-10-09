"""Fail-closed shipping and the body-number gate (G3e).

An external review (2026-10-09) showed three ways a failed issue could still
ship: s18d rendered the PDF into manuscript/ before reading its own gates,
run_month looked for a PDF name the build never writes, and the packagers
copied whatever gate report they found. Body prose numbers were also never
read back. Each test here pins one of those fixes.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from stages.gate_policy import verdict  # noqa: E402
from stages.body_numbers import check_body_numbers, numbers_in  # noqa: E402
import run_month  # noqa: E402

DOI = "10.1000/x.1"
OTHER = "10.1000/y.2"


def _card(doi, pce=None, t80=None, protocol=None, anchor=""):
    perf = {}
    if pce is not None:
        perf["pce_champion"] = {"value": pce, "anchor": anchor}
    stab = {"protocol": protocol}
    if t80 is not None:
        stab["t80_h"] = {"value": t80, "anchor": ""}
    return {"work_key": doi, "doi": doi, "performance": perf, "stability": stab, "claims": []}


def _cite(doi, n=1):
    return rf"[\href{{https://doi.org/{doi}}}{{{n}}}]"


CARDS = [_card(DOI, pce=26.13, anchor="a fill factor of 83.8% and 1.18 V"),
         _card(OTHER, pce=24.4, t80=1000, protocol="ISOS-L-1")]


def _gate(text, cards=CARDS, agg=(), abstracts=None):
    return check_body_numbers({"3": text}, cards, set(agg), abstracts)


# ---------------------------------------------------------------- gate policy
def test_policy_pass_ships():
    assert verdict({"G1": {"status": "pass"}, "G4": {"status": "pass"}})["ok"]


def test_policy_fail_and_warn_block():
    v = verdict({"G1": {"status": "pass"}, "G4": {"status": "fail"},
                 "G5": {"status": "warn"}})
    assert not v["ok"] and v["blocking"] == {"G4": "fail", "G5": "warn"}


def test_policy_only_listed_skip_allowed():
    assert verdict({"G8-novelty": {"status": "skip"}})["ok"]
    assert not verdict({"G8-novelty": {"status": "warn"}})["ok"]
    assert not verdict({"G3-abstract": {"status": "skip"}})["ok"]


def test_policy_ignores_metadata_blocks():
    assert verdict({"G1": {"status": "pass"}, "_regate": {"status": "info"}})["ok"]


def test_policy_empty_report_is_not_a_pass():
    assert not verdict({})["ok"]


# ---------------------------------------------------------------- G3e
def test_bound_number_passes():
    g = _gate(f"The device reached 26.13% PCE {_cite(DOI)}.")
    assert g["status"] == "pass" and g["detail"]["bound"] == 1


def test_number_from_verified_anchor_passes():
    g = _gate(f"Fill factor reached 83.8% {_cite(DOI)}.")
    assert g["status"] == "pass"


def test_number_of_another_paper_is_misbound():
    g = _gate(f"The device reached 24.4% PCE {_cite(DOI)}.")
    assert g["status"] == "fail"
    assert g["detail"]["failures"][0]["kind"] == "misbound"


def test_invented_number_is_untraced():
    g = _gate(f"The device reached 27.9% PCE {_cite(DOI)}.")
    assert g["status"] == "fail" and g["detail"]["untraced"] == 1


def test_number_in_cited_abstract_is_its_own_tier():
    g = _gate(f"The film formed at 450 nm thickness {_cite(DOI)}.",
              abstracts={DOI: "films beyond 450 nm thick"})
    assert g["status"] == "pass" and g["detail"]["in_cited_abstract"] == 1


def test_build_aggregate_passes_only_when_computed():
    s = "The certified reporting share was 8.3% this month."
    assert _gate(s)["status"] == "fail"
    assert _gate(s, agg={8.3})["status"] == "pass"


def test_conventions_years_and_small_integers_are_exempt():
    g = _gate(f"Since 2024, two-terminal devices on sub-0.1 cm2 cells under air mass "
              f"1.5 global light used 3 layers {_cite(DOI)}.")
    assert g["status"] == "pass", g["detail"]["failures"]


def test_t80_definition_is_not_a_datum():
    g = _gate(f"The time to 80% of initial efficiency (T80) was 1000 h {_cite(OTHER)}.")
    assert g["status"] == "pass", g["detail"]["failures"]


def test_wrong_isos_count_is_caught_even_though_the_digit_is_small():
    # The June 2026 issue said "only 5 papers named an ISOS protocol" while
    # 3 named a specified one: small integers are exempt from tracing, so the
    # count check is what catches it.
    cards = CARDS + [_card(f"10.1/z{i}", protocol="ISOS") for i in range(3)]
    bad = _gate("Only 1 paper reported a T80 and only 4 papers named an ISOS protocol.",
                cards=cards)
    assert bad["status"] == "fail" and bad["detail"]["count_mismatch"] == 1
    assert bad["detail"]["failures"][0]["expected"] == {"ISOS": 1}
    ok = _gate("Only 1 paper reported a T80 and only 1 paper named an ISOS protocol.",
               cards=cards)
    assert ok["status"] == "pass", ok["detail"]["failures"]


def test_digit_grouping_is_read_as_one_number():
    assert numbers_in("over 1,000 h and 1 000 h") == {1000.0}


# ---------------------------------------------------------------- run_month
def _fake_run(tmp_path, monkeypatch, gates, pdf_bytes=60_000, failed_marker=False):
    rd = tmp_path / "runs" / "2026-09_abc"
    rd.mkdir(parents=True)
    (rd / "gate_report_v4.json").write_text(json.dumps(gates), encoding="utf-8")
    md = tmp_path / "manuscript" / "2026-09_v4"
    md.mkdir(parents=True)
    (md / "manuscript_v4.pdf").write_bytes(b"%PDF" + b"0" * pdf_bytes)
    if failed_marker:
        (md / "BUILD_FAILED.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(run_month, "ROOT", tmp_path)
    monkeypatch.setattr(run_month, "resolve_run_dir", lambda m: rd)


def test_run_month_accepts_a_passing_issue(tmp_path, monkeypatch):
    # Before the fix it looked for manuscript.pdf, so this could never pass.
    _fake_run(tmp_path, monkeypatch, {"G1": {"status": "pass"},
                                      "G8-novelty": {"status": "skip"}})
    ok, problems = run_month.verify_artifacts("2026-09")
    assert ok, problems


def test_run_month_rejects_warn_fail_and_failed_marker(tmp_path, monkeypatch):
    _fake_run(tmp_path, monkeypatch, {"G1": {"status": "pass"}, "G5": {"status": "warn"}})
    ok, problems = run_month.verify_artifacts("2026-09")
    assert not ok and "G5=warn" in " ".join(problems)


def test_run_month_rejects_build_failed_marker(tmp_path, monkeypatch):
    _fake_run(tmp_path, monkeypatch, {"G1": {"status": "pass"}}, failed_marker=True)
    ok, problems = run_month.verify_artifacts("2026-09")
    assert not ok and "BUILD_FAILED" in " ".join(problems)


# ---------------------------------------------------------------- s18d order
def test_s18d_gates_before_publishing():
    src = (ROOT / "scripts" / "stages" / "s18d_build_v4.py").read_text(encoding="utf-8")
    body = src[src.index("def build("):]
    assert 'pdf = rd / "manuscript_v4.pdf"' in body, "PDF must be staged in the run dir"
    i_verdict = body.index("v = verdict(gate)")
    i_raise = body.index("raise SystemExit(f\"FAIL-CLOSED: gates failed")
    i_copy = body.index('"12_section_map.json", "manuscript_v4.pdf"')
    assert i_verdict < i_raise < i_copy
    assert "G3e-body-numbers" in src


def test_packagers_use_the_shared_policy():
    for rel in ("scripts/stages/s20_chemrxiv.py", "scripts/release/build_public_tree.py",
                "scripts/run_month.py"):
        src = (ROOT / rel).read_text(encoding="utf-8")
        assert re.search(r"from stages\.gate_policy import verdict", src), rel
