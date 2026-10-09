"""Digit grouping in every number matcher that decides groundedness.

"1,080 h" is one thousand and eighty hours. Three matchers (the s09 guard, the
independent verify_anchors check, and the study metric) all once read the
comma as a decimal point, so a correct value of 1080 was nulled by the guard
and scored as fabricated by the study. These tests pin the fixed behaviour in
all three, and pin that a real decimal comma still reads as a decimal.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "papers" / "scripts"))

import verify_anchors  # noqa: E402
from stages import s09_cards  # noqa: E402
from studies import study_common as sc  # noqa: E402

CASES_TRUE = [
    ("1080", "retained 80% of its initial PCE after 1,080 h"),
    ("20000", "a projected T80 of 20,000 h"),
    ("1000000", "over 1,000,000 cycles"),
    ("26.13", "a PCE of 26.13%"),
    ("0.148", "an area of 0,148 cm2"),         # European decimal comma
    ("1.08", "after 1,08 h"),                   # two digits after comma: decimal
]
CASES_FALSE = [
    ("1080", "a PCE of 10.80%"),
    ("148", "an area of 0,148 cm2"),            # leading zero: never grouping
    ("1080", "after 1,0800 h"),
]


def _all(want, text):
    return (s09_cards._num_in(want, text), verify_anchors.num_in(want, text),
            sc.number_present(want, text))


def test_grouping_is_read_as_grouping():
    for want, text in CASES_TRUE:
        assert _all(want, text) == (True, True, True), (want, text, _all(want, text))


def test_no_false_matches():
    for want, text in CASES_FALSE:
        assert _all(want, text) == (False, False, False), (want, text, _all(want, text))


def test_legacy_metric_reproduces_the_defect():
    # kept only so a study can report what published numbers were computed with
    assert sc.number_present_legacy("1080", "after 1,080 h") is False


def test_explain_ungrounded_classes():
    assert sc.explain_ungrounded(900, "active_area_cm2", "a 30 x 30 cm2 module") == "unit_conversion"
    assert sc.explain_ungrounded(0.0405, "active_area_cm2", "area 4.05 mm 2") == "unit_conversion"
    assert sc.explain_ungrounded(1080, "t80_h", "stable for 45 days") == "unit_conversion"
    assert sc.explain_ungrounded(26, "pce_champion", "a PCE of 26.13%") == "rounding"
    assert sc.explain_ungrounded(0.0148, "active_area_cm2", "0.148 cm 2") == "decimal_shift"
    assert sc.explain_ungrounded(33.3, "pce_champion", "a PCE of 26.1%") == "absent"
