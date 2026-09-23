"""Tests for the three monthly stages adapted to accept a YEAR.

Each test here pins a defect that would NOT have crashed. That is the whole
point: a stage handed a year instead of a month mostly keeps working, writes
plausible files, and produces a monthly-shaped review wearing a yearly title.
Nothing raises. Every gate passes. Only a domain expert reading the PDF would
notice, and by then the tokens are spent.

No network. No API key. No live harvest.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from stages.s02_06 import in_period                        # noqa: E402
from stages.s04_10 import gates                            # noqa: E402


# ------------------------------------------------ the year-emptying bug
class TestInPeriod:
    """The bug that would have dropped all ~7,900 works of 2025.

    The monthly original read:

        if r["canonical_month"] != month:   # '2025-06' != '2025' -> DROP

    `canonical_month` is always 'YYYY-MM'. Against a bare year it NEVER
    matches, so every work is dropped as "wrong month", the stage writes an
    empty corpus, and `dropped_wrong_month` reports a large healthy-looking
    number. Nothing downstream crashes. The year is simply gone.
    """

    def test_a_month_belongs_to_its_year(self):
        assert in_period("2025-06", "2025") is True

    def test_every_month_of_the_year_is_kept(self):
        for m in range(1, 13):
            assert in_period(f"2025-{m:02d}", "2025") is True, \
                f"2025-{m:02d} was dropped from its own year"

    def test_another_years_month_is_rejected(self):
        assert in_period("2024-12", "2025") is False
        assert in_period("2026-01", "2025") is False

    def test_month_mode_still_matches_exactly(self):
        """The monthly behaviour must be preserved bit for bit."""
        assert in_period("2025-06", "2025-06") is True
        assert in_period("2025-07", "2025-06") is False
        assert in_period("2024-06", "2025-06") is False

    def test_empty_or_missing_month_is_rejected_not_admitted(self):
        """A blank canonical_month must not silently pass a year filter."""
        assert in_period("", "2025") is False
        assert in_period(None, "2025") is False

    def test_a_year_string_is_not_admitted_as_a_month(self):
        """Guards against a prefix-test implementation: '2025' must not
        satisfy the month filter '2025-06'."""
        assert in_period("2025", "2025-06") is False


# ------------------------------------------------------- the gates overlay
class TestGatesOverlay:
    """A year must select on YEARLY depth knobs, not monthly ones.

    With the monthly numbers, a year of ~7,900 works would cap its depth tier
    at 200 papers and let an axis carry a 1500-word section on twelve papers.
    Nothing crashes; the issue is just thin in a way its title denies.
    """

    def test_yearly_depth_target_replaces_the_monthly_one(self):
        assert gates("2025-06")["depth_target"] == 200
        assert gates("2025")["depth_target"] == 450

    def test_yearly_depth_band_replaces_the_monthly_one(self):
        assert gates("2025-06")["depth_band"] == [100, 300]
        assert gates("2025")["depth_band"] == [350, 550]

    def test_yearly_axis_floor_is_raised(self):
        """12 papers cannot support a 700-1500 word yearly section."""
        assert gates("2025-06")["axis_min_depth"] == 12
        assert gates("2025")["axis_min_depth"] == 25

    def test_yearly_citation_ceiling_is_carried_across(self):
        """selection.n_cited must be bounded by the YEARLY ceiling."""
        assert gates("2025-06")["paper"]["max_body_citations"] == 180
        assert gates("2025")["paper"]["max_body_citations"] == 220

    def test_period_mode_is_recorded_for_downstream_prose(self):
        """stats.json's delta_basis branches on this, so it must be set."""
        assert gates("2025").get("_period_mode") == "yearly"
        assert gates("2025-06").get("_period_mode") is None

    def test_fairness_caps_fall_through_and_are_not_zeroed(self):
        """yearly.yaml deliberately does NOT declare these.

        They are PROPORTIONS of n_target, so they scale with the pool by
        themselves. The risk being tested is the opposite of widening: an
        overlay that copied every key would set them to None and disable the
        venue/institution concentration limits entirely.
        """
        y = gates("2025")
        assert y["venue_share_max_pct"] == 8
        assert y["institution_share_max_pct"] == 10
        assert y["preprint_share_min_pct"] == 10

    def test_no_yearly_key_is_ever_none_in_the_overlay(self):
        """A None from yearly.yaml must not overwrite a real monthly value."""
        y = gates("2025")
        for k in ("depth_target", "depth_band", "axis_min_depth",
                  "venue_share_max_pct", "institution_share_max_pct",
                  "sensitivity_draws", "seed"):
            assert y.get(k) is not None, f"{k} was zeroed by the overlay"

    def test_monthly_gates_file_is_not_mutated_by_a_yearly_read(self):
        """gates() must not leave the monthly config altered on disk."""
        gates("2025")
        raw = yaml.safe_load((ROOT / "config" / "gates.yaml").read_text(
            encoding="utf-8"))
        assert raw["depth_target"] == 200
        assert raw["depth_band"] == [100, 300]
        assert raw["paper"]["max_body_citations"] == 180

    def test_calling_gates_twice_is_stable(self):
        """No accumulating mutation across calls."""
        assert gates("2025")["depth_target"] == gates("2025")["depth_target"]
        assert gates("2025-06")["depth_target"] == 200


# ------------------------------------------------- no silent default period
@pytest.mark.parametrize("stage", ["s02_06", "s04_10", "s09_cards"])
def test_stage_refuses_to_run_without_a_period(stage):
    """A verifier that defaulted to a hardcoded August manuscript once ran
    during the June cycle, verified the wrong file, and reported PASS.

    A STAGE that defaults is the same defect with write access: run bare in
    this repo and it would touch a 2026-07 run dir this project does not own.
    s09_cards is the worst case, being the only stage that spends money.
    """
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "stages" / f"{stage}.py")],
        capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode != 0, f"{stage} ran without a period argument"
    combined = (r.stdout + r.stderr).lower()
    assert "usage" in combined
    assert "never inferred" in combined


@pytest.mark.parametrize("stage", ["s02_06", "s04_10", "s09_cards"])
def test_no_stage_carries_a_hardcoded_monthly_default(stage):
    """The literal that caused the defect must be gone from the entrypoint."""
    src = (ROOT / "scripts" / "stages" / f"{stage}.py").read_text(
        encoding="utf-8")
    tail = src.split('if __name__ == "__main__":')[-1]
    assert '"2026-07"' not in tail, f"{stage} still defaults to 2026-07"
    assert '"2026-08"' not in tail, f"{stage} still defaults to 2026-08"


# ------------------------------------- prose that reaches a reader as fact
def test_force_include_reason_does_not_claim_month_one():
    """This string is written to disk and read as a statement of fact.

    'month 1: empty card history' in a YEARLY run is simply false. The
    condition is a cold start, which is what it now says.
    """
    src = (ROOT / "scripts" / "stages" / "s04_10.py").read_text(
        encoding="utf-8")
    assert '"reason": "cold start: empty card history' in src
    assert '"month 1: empty card history' not in src


def test_axis_delta_basis_branches_on_period_mode():
    """A yearly cold start has no prior ISSUE, not merely no prior month.

    delta_basis lands in stats.json, which the manuscript may cite, so a
    stale 'no prior month' would be an unfalsifiable false statement in a
    yearly issue.
    """
    src = (ROOT / "scripts" / "stages" / "s04_10.py").read_text(
        encoding="utf-8")
    assert 'cold start: no prior issue' in src
    assert '_period_mode' in src
