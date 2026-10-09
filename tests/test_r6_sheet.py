"""R6 numeric sheet: blind, frozen, and hash-bound to its analysis."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
D = ROOT / "papers" / "studies" / "r6_numeric"
# The HTML sheet embeds publisher abstracts and is not released; its sha256 is
# in preregistration.json, so the binding is checked where the sheet exists.
pytestmark = pytest.mark.skipif(not (D / "r6_sheet.html").exists(),
                                reason="blind sheet not shipped (embeds abstracts)")


def test_prereg_binds_sheet_and_analysis():
    pre = json.loads((D / "preregistration.json").read_text(encoding="utf-8"))
    sheet = (D / "r6_sheet.html").read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(sheet).hexdigest() == pre["sheet_sha256"]
    ana = (ROOT / pre["analysis_script"]).read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(ana).hexdigest() == pre["analysis_script_sha256"], \
        "r6_analyze.py changed after pre-registration: list it as a deviation"
    assert pre["analysis_frozen_before_labelling"] is True
    assert pre["labeller"].startswith("Havid Aqoma (human). No model may label")


def test_sheet_has_no_machine_side_and_no_prefill():
    page = (D / "r6_sheet.html").read_text(encoding="utf-8")
    frame = json.loads((D / "sampling_frame.json").read_text(encoding="utf-8"))
    assert page.count('<section class="card"') == len(frame)
    assert 'value="' not in page
    attrs = set(re.findall(r"\sdata-([a-z-]+)=", page))
    assert attrs <= {"wk", "k"}, attrs
    for bad in ("extractor", "qwen", "glm", "opencode", "card_pce", "has_card"):
        assert bad not in page.lower(), bad
