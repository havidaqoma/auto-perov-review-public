"""Tests for the extraction stage's coverage guarantees.

These exist because of a MEASURED hole in the 2025-06 dry run:

    [09]  96/152 -> 96 cards
    [09] 108/152 -> 96 cards      <- 12 papers in, 0 cards out

Papers 96-107 were exactly one contiguous batch. Their abstracts were
148-342 words, median 197 -- good input. The batch's response failed to
parse, `parse_array` returned [] by design, every paper got `o = {}`, and the
loop produced no card WITHOUT RAISING. The summary reported
`dropped_papers: 12` as if that were normal.

`call_opencode` already fails loudly on rc!=0 or empty stdout. The silent
zero lived on the OTHER side of that seam.

No network: `retry` is injected.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from stages import s09_cards as s9                          # noqa: E402


def _obj(i: int) -> str:
    return '{"i": %d, "pce_champion": null, "claims": []}' % i


def _array(n: int) -> str:
    return "[" + ",".join(_obj(i) for i in range(n)) + "]"


# --------------------------------------------------- parse_array unchanged
class TestParseArray:
    """parse_array keeps returning [] -- it is a pure decoder.

    The fix belongs in the CALLER, not here. A decoder that raised would
    break every other use and would conflate "cannot decode" with "decoded
    an empty list", which are different facts.
    """

    def test_garbage_returns_empty_list(self):
        assert s9.parse_array("not json at all") == []

    def test_prose_wrapper_returns_empty(self):
        assert s9.parse_array("I could not complete that request.") == []

    def test_fenced_json_is_decoded(self):
        got = s9.parse_array("```json\n" + _array(2) + "\n```")
        assert len(got) == 2

    def test_leading_prose_before_array_is_tolerated(self):
        got = s9.parse_array("Here you go:\n" + _array(3))
        assert len(got) == 3


# ------------------------------------------- retry, then fail LOUDLY
class TestParseBatchOrRaise:

    def test_unparseable_batch_raises_instead_of_returning_empty(self):
        """The core fix. An empty mapping must never reach the card loop."""
        with pytest.raises(s9.BatchParseFailure):
            s9.parse_batch_or_raise(
                "garbage", 12, 8, retry=lambda: ("still garbage", {}))

    def test_it_retries_exactly_once_before_raising(self):
        calls = []

        def retry():
            calls.append(1)
            return ("garbage again", {})

        with pytest.raises(s9.BatchParseFailure):
            s9.parse_batch_or_raise("garbage", 12, 8, retry=retry)
        assert len(calls) == 1, "must retry once, not zero and not forever"

    def test_a_retry_that_succeeds_recovers_the_batch(self):
        """The 2025-06 failure was almost certainly transient, so the retry
        is what actually saves the 12 papers."""
        got = s9.parse_batch_or_raise(
            "garbage", 12, 8, retry=lambda: (_array(12), {}))
        assert len(got) == 12

    def test_a_good_first_response_does_not_retry(self):
        """Retrying on success would double the bill for the only stage that
        spends money."""
        calls = []

        def retry():
            calls.append(1)
            return ("unused", {})

        got = s9.parse_batch_or_raise(_array(12), 12, 0, retry=retry)
        assert len(got) == 12
        assert calls == []

    def test_it_indexes_objects_by_their_own_i_field(self):
        got = s9.parse_batch_or_raise(_array(4), 4, 0,
                                      retry=lambda: ("", {}))
        assert sorted(got) == [0, 1, 2, 3]

    def test_objects_without_a_usable_index_are_discarded(self):
        """An object with no `i` cannot be attached to a paper. Attaching it
        to the wrong paper would put a number on a device it never described,
        which is the misattribution class."""
        raw = '[{"i": 0}, {"no_index": true}, {"i": "x"}, {"i": 2}]'
        got = s9.parse_batch_or_raise(raw, 3, 0, retry=lambda: ("", {}))
        assert sorted(got) == [0, 2]

    def test_a_partial_batch_is_accepted_not_raised(self):
        """3 of 12 answered is a SHORT batch, not a dead one. It must pass
        through so the coverage assertion can judge it in aggregate."""
        got = s9.parse_batch_or_raise(_array(3), 12, 5,
                                      retry=lambda: ("", {}))
        assert len(got) == 3

    def test_the_error_names_the_batch_and_the_failure_class(self):
        """An operator reading the traceback must know WHICH batch and WHY,
        without reading the source."""
        with pytest.raises(s9.BatchParseFailure) as e:
            s9.parse_batch_or_raise("x", 12, 8, retry=lambda: ("y", {}))
        msg = str(e.value)
        assert "batch 8" in msg
        assert "12 papers" in msg
        assert "silent-zero" in msg


# ------------------------------------------------- the coverage floor
class TestCoverageFloor:

    def test_floor_is_high_enough_to_catch_one_dead_batch(self):
        """The measured failure was 140/152 = 92.1%. The floor must reject
        it, or the fix does not close the hole it was written for."""
        assert 140 / 152 < s9.MIN_COVERAGE

    def test_floor_admits_a_single_genuine_per_paper_skip(self):
        """The floor must not be so tight that one legitimately unanswerable
        paper fails a whole year's extraction."""
        assert 449 / 450 >= s9.MIN_COVERAGE

    def test_floor_is_not_a_hundred_percent(self):
        """A 100% floor would make the stage unrunnable on any real corpus
        and would invite someone to lower it under pressure."""
        assert s9.MIN_COVERAGE < 1.0


# ------------------------------------------------------ token honesty
def test_token_input_is_marked_not_credible():
    """Measured 2025-06: tokens_in = 78 across 13 batches each carrying ~12
    abstracts of ~180 words. That is not a prompt-token count.

    An implausible number is the same class as a zero: surfaced, never
    substituted with an estimate that merely looks better.
    """
    src = (ROOT / "scripts" / "stages" / "s09_cards.py").read_text(
        encoding="utf-8")
    assert '"tokens_in_credible": False' in src


def test_batch_coverage_is_written_for_audit():
    """`dropped_papers` as a bare total cannot distinguish 'the model skipped
    these' from 'a batch died'. The per-batch record can."""
    src = (ROOT / "scripts" / "stages" / "s09_cards.py").read_text(
        encoding="utf-8")
    assert "09_batch_coverage.json" in src
    assert "n_answered" in src


def test_the_card_loop_no_longer_decodes_inline():
    """Regression guard: the old inline dict-comprehension is what made the
    silent zero possible. If it comes back, this test fails."""
    src = (ROOT / "scripts" / "stages" / "s09_cards.py").read_text(
        encoding="utf-8")
    body = src.split("def cards(")[-1]
    assert "parse_batch_or_raise" in body
    assert 'for o in parse_array(raw)' not in body, \
        "inline parse_array decoding is back in the card loop"
