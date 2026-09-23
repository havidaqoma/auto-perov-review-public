"""Regression tests for 01_harvest exclusion rules (no network).

Rules under test were added v0.1.1 (bare-LED case fix) and v0.1.2 (Wiley
cover-caption and issue-suffix-title exclusions, QA 2026-09-05 caught
10.1002/smtd.70688 "Back Cover In article number e70654..." caption record).
"""
import importlib.util
import pathlib

import pytest
import yaml

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
SCRIPT = REPO / "scripts" / "01_harvest.py"

_spec = importlib.util.spec_from_file_location("harvest_rules_mod", SCRIPT)
harvest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(harvest)

_CFG = yaml.safe_load((REPO / "config" / "exclude.yaml").read_text(encoding="utf-8"))


def reason(title, abstract, journal=""):
    return harvest.exclusion_reason(title, journal, abstract, _CFG)


# ---------- v0.1.2: Wiley cover captions are not papers ----------

def test_cover_caption_wiley_back_cover():
    abs = ("Back Cover In article number e70654, Yu-Ching Huang and co-workers "
           "present a fully vacuum-processed perovskite platform tailored for "
           "indoor photovoltaics.")
    assert reason("A Defect Engineered Strategy (Small Methods 13/2026)", abs) == "cover-caption"


def test_cover_caption_front_cover():
    abs = ("Front Cover In article number e12345, the authors demonstrate a "
           "stabilization route for perovskite solar cells.")
    assert reason("Some Title", abs) == "cover-caption"


def test_issue_suffix_title_without_caption():
    # Some Wiley index records only carry the issue-suffix title, no cover abstract.
    assert reason("A Defect Engineered Strategy (Small Methods 13/2026)", "") == "issue-suffix-title"


def test_legit_cover_glasses_does_not_fire():
    # "cover glasses" (encapsulation) is a legit PV topic (ACS Energy Lett. 2026 case).
    abs = ("While encapsulation can reduce damage, cover glasses are incompatible "
           "with the desirable development of flexible solar cells.")
    assert reason("Energy-Independent Barrier Strategy Stabilizes Proton-Irradiated "
                  "Perovskite Solar Cells against Outgassing", abs) is None


def test_legit_no_suffix_no_caption():
    assert reason("Suppressing Morphological and Energetic Disorder in Hole-Transport "
                  "Layers", "Dopant-free inorganic hole-transport layers are promising.") is None


# ---------- v0.1.1 regression: bare-LED case handling ----------

def test_bare_led_still_excluded():
    assert reason("An LED-based illumination source for indoor perovskite modules",
                  "") == "bare-LED"


def test_led_verb_lowercase_safe():
    assert reason("Halide segregation led to reduced performance in mixed devices",
                  "") is None


def test_version_bumped():
    assert harvest.SCRIPT_VERSION == "0.1.2"
