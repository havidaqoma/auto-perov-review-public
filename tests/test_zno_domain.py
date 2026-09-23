"""Regression tests for the ZnO nanoparticle / quantum-dot domain.

Every assertion here pins a decision that a future edit could silently
reverse. The ZnO instance is the SECOND Type-D domain, and Type-D is the
field GENERAL 3.3 calls the highest-stakes in the registry: choosing P for a
discovery topic produces a paper that ranks materials by a number nobody
ranks them by, and every gate passes.

These tests do not re-test domain_lint.py itself (test_yearly_and_domains.py
covers that). They assert the ZnO domain's own content.
"""
from __future__ import annotations

import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.stages.domain_lint import (  # noqa: E402
    UNIVERSAL_BANNED,
    VENUE_PRESTIGE_KEYS,
    lint,
)

ZNO_PATH = ROOT / "config" / "domains" / "zno_qd.yaml"


@pytest.fixture(scope="module")
def zno() -> dict:
    return yaml.safe_load(ZNO_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def metrics(zno) -> dict:
    return {m["key"]: m for m in zno["metrics"]}


def test_zno_domain_file_exists_and_lints_clean():
    assert ZNO_PATH.exists(), "the ZnO domain registry is missing"
    errs = lint(ZNO_PATH)
    assert errs == [], f"zno_qd.yaml fails domain_lint: {errs}"


def test_slug_matches_filename_stem(zno):
    # A mismatch splits one domain's artifacts across two run-dir names.
    assert zno["domain"]["slug"] == ZNO_PATH.stem == "zno_qd"


# --------------------------------------------------------------- Type-D
def test_zno_is_type_d(zno):
    """The load-bearing decision.

    ZnO nanoparticle/QD work spans synthesis, optics, defect chemistry,
    photocatalysis, sensing and electronics. No scalar figure of merit ranks
    across those literatures, so Type-P would be a category error.
    """
    assert zno["domain"]["topic_type"] == "D"


def test_no_metric_claims_the_frontier_role(zno):
    roles = [m.get("role") for m in zno["metrics"]]
    assert "frontier" not in roles, (
        "a frontier role would license a champion curve over ZnO "
        "nanomaterials, which is the Type-D category error"
    )


def test_lead_role_is_significance(zno):
    assert zno["section_spine"]["lead_role"] == "significance"


def test_advance_taxonomy_is_present_and_closed(zno):
    tax = zno["advance_taxonomy"]
    assert tax["values"], "Type-D classifies contributions; it needs classes"
    assert "unknown" in tax["values"], (
        "an unlisted class must land in 'unknown', never be coerced silently"
    )


def test_comparative_advance_classes_require_a_comparator(zno):
    """Comparative claims by construction need the prior art's number.

    'improved', 'more stable' and 'now practical' are all claims ABOUT prior
    art. Without the comparator in the same anchor there is nothing to check.
    """
    tax = zno["advance_taxonomy"]
    need = tax["requires_comparator"]
    for cls in ("improved_optical_quality", "improved_stability"):
        assert cls in need, f"{cls} is comparative and needs a comparator"
    assert set(need) <= set(tax["values"]), (
        "requires_comparator names a class that does not exist"
    )


def test_yield_direction_is_none(metrics):
    """Yield is a property of a run, not of a method.

    Also enforced generically by domain_lint for any key starting 'yield',
    but ZnO's key is `synthesis_yield_pct`, which that prefix check does NOT
    match. So it is pinned explicitly here.
    """
    m = metrics["synthesis_yield_pct"]
    assert m["direction"] == "none"
    assert m["role"] != "frontier"


# ------------------------------------------------ the PLQY binding trap
def test_plqy_is_quality_not_frontier(metrics):
    """PLQY is the most tempting wrong frontier in this domain.

    A 94% colloid PLQY is not comparable to a 12% film PLQY, and the film is
    usually the harder result.
    """
    m = metrics["plqy_pct"]
    assert m["role"] == "quality"
    assert m["plausibility"]["max"] <= 100.0


def test_plqy_is_device_bound_to_its_sample_class(metrics):
    """GENERAL 2.4 in its ZnO form.

    One abstract routinely reports the authors' colloid PLQY and a film or
    device value in adjacent sentences. A label taken from the PAPER attaches
    to the wrong number; the label must come from the value's own anchor.
    """
    m = metrics["plqy_pct"]
    assert m["device_binding"] is True
    assert m["requires_condition"] == "sample_class"


def test_stability_requires_its_stress_condition(metrics):
    """Retention without its stress is not a fact about a material."""
    m = metrics["photostability_retention_pct"]
    assert m["device_binding"] is True
    assert m["requires_condition"] == "stress_condition"


def test_sample_taxonomy_separates_colloid_film_and_device(zno):
    vals = set(zno["sample_taxonomy"]["values"])
    for v in ("colloid", "thin_film", "device", "powder", "unknown"):
        assert v in vals, f"sample class {v!r} missing; PLQY binding needs it"


# ------------------------------------------------------- physics bounds
def test_every_metric_declares_plausibility_bounds(zno):
    for m in zno["metrics"]:
        p = m.get("plausibility") or {}
        assert "min" in p and "max" in p, f"{m['key']} has no bounds"
        assert p["min"] < p["max"], f"{m['key']} bounds inverted"


def test_percentage_metrics_cannot_exceed_one_hundred(zno):
    for m in zno["metrics"]:
        if m.get("unit") == "%":
            assert m["plausibility"]["max"] <= 100.0, (
                f"{m['key']} is a percentage with max > 100"
            )


def test_bandgap_bound_brackets_bulk_zno(metrics):
    """Bulk ZnO is 3.37 eV; confinement raises it. A bound that excludes
    3.37 would reject correct data, and one that admits 1.5 would accept a
    different material entirely."""
    p = metrics["bandgap_ev"]["plausibility"]
    assert p["min"] < 3.37 < p["max"]
    assert p["min"] >= 2.5, "a gap below 2.5 eV is not ZnO"


def test_emission_peak_bound_brackets_band_edge_and_defect_emission(metrics):
    """ZnO band-edge PL sits near 370 nm, defect PL near 500-600 nm."""
    p = metrics["emission_peak_nm"]["plausibility"]
    assert p["min"] <= 370 <= p["max"]
    assert p["min"] <= 600 <= p["max"]


def test_particle_size_floor_is_above_a_unit_cell(metrics):
    p = metrics["particle_size_nm"]["plausibility"]
    assert p["min"] >= 0.5, "below a ZnO unit cell the value is not a size"


# ------------------------------------------------------ venue prestige
def test_no_venue_prestige_metric_anywhere(zno):
    """GENERAL 3.4: refused as a metric in EVERY domain.

    An impact factor has no anchor in the cited paper's abstract, so it
    cannot pass the evidence guards, and in a Type-D domain it reinstates
    the scalar ranking the significance section exists to replace.
    """
    for m in zno["metrics"]:
        norm = str(m["key"]).lower().replace("-", "_").replace(" ", "_")
        assert norm not in VENUE_PRESTIGE_KEYS
        assert not norm.endswith("_impact_factor")


# -------------------------------------------------------------- figures
def test_no_champion_abstract_token(zno):
    """A Type-D abstract has no champion value to state.

    Adding one would invite exactly the ranking error the type split exists
    to prevent.
    """
    toks = {t["token"] for t in zno["abstract_tokens"]}
    for bad in ("P_TOP_CERT", "P_TOP_CHAMP", "P_TOP_CERT_YEAR"):
        assert bad not in toks, f"{bad} is a PV champion token"


def test_abstract_tokens_resolve_to_declared_metrics_or_classes(zno, metrics):
    classes = set(zno["advance_taxonomy"]["values"])
    for t in zno["abstract_tokens"]:
        src = str(t["source"])
        if not src.startswith("cards:"):
            continue
        bits = src.split(":")
        if len(bits) >= 3:
            named = bits[2]
            assert named in metrics or named in classes, (
                f"token {t['token']} names {named!r}, which is neither a "
                f"declared metric nor an advance class"
            )


def test_figures_attach_by_role_or_axis_never_section_number(zno):
    axes = set(zno["axes"])
    for f in zno["figure_roles"]:
        tgt = f.get("attach_role") or f.get("attach_axis")
        assert tgt, f"figure {f['id']} has no role/axis attachment"
        ax = f.get("attach_axis")
        for a in ([ax] if isinstance(ax, str) else (ax or [])):
            assert a in axes, f"figure {f['id']} attaches to unknown axis {a}"


def test_each_figure_file_attaches_to_at_most_one_target(zno):
    """G9c. The August v4 PDF showed one plate as Figure 2 AND Figure 3."""
    ids = [f["id"] for f in zno["figure_roles"]]
    assert len(ids) == len(set(ids)), "duplicate figure id"


def test_measured_figures_exclude_computational_work(zno):
    """GENERAL 5.2, and ZnO defect chemistry has a large DFT literature."""
    lens = zno["lens"]
    assert "computational" in lens["exclude_from_measured_figures"]
    assert "review" in lens["exclude_from_measured_figures"]
    assert not set(lens["measured_lenses"]) & set(
        lens["exclude_from_measured_figures"]
    )
    for f in zno["figure_roles"]:
        if f.get("y_metric") in ("plqy_pct", "photostability_retention_pct"):
            assert f["lens_filter"] == "measured", (
                f"figure {f['id']} plots a measured quantity and must not "
                f"admit computational values"
            )


# ------------------------------------------------------------- harvest
def test_harvest_query_has_no_exclusions_or_wildcards(zno):
    """A '-term' in an OpenAlex query returns count 0, not a filtered set,
    and zero is indistinguishable from a legitimately empty month."""
    for grp in zno["harvest"]["query_terms"]:
        for term in grp:
            assert not str(term).strip().startswith("-")
            assert "*" not in str(term)


def test_exclusions_are_declared_in_python_side_block(zno):
    ex = zno["exclude"]
    assert ex["substring"] or ex["word_bound"]
    assert "perovskite" in ex["word_bound"], (
        "the PV corpus overlaps ZnO heavily via electron-transport layers"
    )


def test_count_band_is_ordered(zno):
    lo, hi = zno["harvest"]["count_band"]
    assert 0 < lo < hi


# ---------------------------------------------------------------- axes
def test_enough_axes_to_fill_the_section_map(zno):
    assert len(zno["axes"]) >= 4


def test_every_axis_folds_somewhere_real(zno):
    axes = zno["axes"]
    for name, ax in axes.items():
        assert ax["keywords"], f"axis {name} can never score"
        fi = ax.get("fold_into")
        assert fi in axes, f"axis {name} folds into unknown {fi!r}"
        assert fi != name, f"axis {name} folds into itself"


def test_every_axis_has_title_phrases(zno):
    ap = zno["title_terms"]["axis_phrases"]
    for name in zno["axes"]:
        assert ap.get(name), f"a month led by {name} could not build a title"


# --------------------------------------------------------------- title
def test_banned_list_is_additive_over_the_universal_set(zno):
    banned = {str(b).lower() for b in zno["title_terms"]["banned"]}
    assert UNIVERSAL_BANNED <= banned, (
        f"a domain may add to the banned list, never remove: missing "
        f"{sorted(UNIVERSAL_BANNED - banned)}"
    )


def test_lead_title_template_is_not_a_hardcoded_period(zno):
    tpl = zno["section_spine"]["lead_title_template"]
    assert "{month}" in tpl or "{year}" in tpl, (
        "a hardcoded period ships a stale month into a later issue"
    )


# ------------------------------------------------------------ notation
def test_domain_units_are_declared(zno):
    """A MISSING unit does not degrade gracefully: one unknown token in a
    unit run leaves every unit beside it flat, and the gate reports the
    neighbour instead (GENERAL 5.3, the missing `J`)."""
    units = zno["notation"]["extra_units"]
    for u in ("nm", "eV", "ns"):
        assert u in units, f"unit {u!r} is used by a declared metric"


def test_every_metric_unit_is_resolvable(zno):
    """Any non-empty, non-% metric unit must appear in the unit table."""
    units = set(zno["notation"]["extra_units"])
    for m in zno["metrics"]:
        u = str(m.get("unit") or "")
        if u and u != "%":
            assert u in units, (
                f"metric {m['key']} uses unit {u!r}, which is not in "
                f"notation.extra_units; it would render flat"
            )


def test_acronyms_are_masked_before_substitution(zno):
    terms = set(zno["notation"]["defined_terms"])
    for t in ("PLQY", "FWHM", "TRPL", "ZnO"):
        assert t in terms, f"{t} must be masked or a formula rule chews it"
