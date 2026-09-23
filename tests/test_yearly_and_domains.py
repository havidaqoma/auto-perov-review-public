"""Yearly + general-domain machinery must not drift from what it documents.

Same reasoning as tests/test_handbook.py: a handbook that disagrees with its
code sends the operator down a dead path mid-run, and this project has paid
for that twice already.
"""
from __future__ import annotations

import pathlib
import re
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from stages import domain_lint                      # noqa: E402
from stages import yearly_section_map as ysm         # noqa: E402
from stages.section_map import TITLE_BANK            # noqa: E402

YEARLY_HB = ROOT / "MASTER_HANDBOOK_YEARLY.md"
GENERAL_HB = ROOT / "MASTER_HANDBOOK_GENERAL.md"
DOMAINS = sorted((ROOT / "config" / "domains").glob("*.yaml"))

# Real annual mass of the three shipped 2026 issues, measured from disk
# 2026-09-08. Pinned as a literal so this test asserts a HISTORICAL fact
# with every input named (handbook 7.7: a fixture resolving "the latest"
# describes a moving target and stops testing what it was written to test).
MASS_2026 = {"defects": 132, "interfaces": 99, "composition": 98,
             "stability": 62, "architecture": 54, "scale_up": 35}


# --------------------------------------------------------------- domains
def test_every_domain_passes_the_linter():
    """A shipped domain instance must satisfy its own contract."""
    assert DOMAINS, "no domain instances found"
    for p in DOMAINS:
        errs = domain_lint.lint(p)
        assert not errs, f"{p.name} fails domain_lint:\n" + "\n".join(errs)


@pytest.mark.parametrize("path", DOMAINS, ids=lambda p: p.stem)
def test_domain_slug_matches_filename(path):
    D = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert D["domain"]["slug"] == path.stem


def test_linter_rejects_type_d_with_a_frontier_metric(tmp_path):
    """THE Type-D trap, and the most valuable assertion in the linter.

    Yield, ee and dr are all numbers, so a carelessly configured discovery
    domain will declare one a frontier and the pipeline will build a champion
    curve over chemistry that no chemist ranks that way. Every gate would
    pass. If this test ever goes green-by-accident, that hole reopens.
    """
    base = yaml.safe_load(
        (ROOT / "config" / "domains" / "molecular_synthesis.yaml")
        .read_text(encoding="utf-8"))
    # Promote yield to a frontier metric: the exact category error.
    for m in base["metrics"]:
        if m["key"] == "yield_pct":
            m["role"] = "frontier"
            m["direction"] = "higher_better"
    f = tmp_path / "molecular_synthesis.yaml"
    f.write_text(yaml.safe_dump(base), encoding="utf-8")

    errs = domain_lint.lint(f)
    assert any("must NOT declare a 'frontier'" in e for e in errs), \
        "linter failed to catch a Type-D domain declaring a frontier metric"
    assert any("yield" in e.lower() and "direction" in e.lower()
               for e in errs), \
        "linter failed to catch yield declared higher_better in a Type-D domain"


def test_linter_requires_plausibility_bounds(tmp_path):
    """7.8's corollary: traceability proves provenance, not meaning."""
    base = yaml.safe_load(
        (ROOT / "config" / "domains" / "perovskite_pv.yaml")
        .read_text(encoding="utf-8"))
    base["metrics"][0].pop("plausibility", None)
    f = tmp_path / "perovskite_pv.yaml"
    f.write_text(yaml.safe_dump(base), encoding="utf-8")
    errs = domain_lint.lint(f)
    assert any("plausibility" in e and "REQUIRED" in e for e in errs)


def test_linter_rejects_query_side_exclusions(tmp_path):
    """A '-term' in an OpenAlex query returns count 0, not a filtered set."""
    base = yaml.safe_load(
        (ROOT / "config" / "domains" / "perovskite_pv.yaml")
        .read_text(encoding="utf-8"))
    base["harvest"]["query_terms"].append(["-tandem"])
    f = tmp_path / "perovskite_pv.yaml"
    f.write_text(yaml.safe_dump(base), encoding="utf-8")
    errs = domain_lint.lint(f)
    assert any("returns count 0" in e for e in errs)


def test_universal_banned_terms_cannot_be_removed(tmp_path):
    base = yaml.safe_load(
        (ROOT / "config" / "domains" / "perovskite_pv.yaml")
        .read_text(encoding="utf-8"))
    base["title_terms"]["banned"] = ["novel"]
    f = tmp_path / "perovskite_pv.yaml"
    f.write_text(yaml.safe_dump(base), encoding="utf-8")
    errs = domain_lint.lint(f)
    assert any("universal entries" in e for e in errs)


def test_linter_refuses_venue_prestige_as_a_metric(tmp_path):
    """Journal IF as a ranking metric, refused in EVERY domain.

    Havid asked directly whether Type-D could rank by journal impact factor.
    The answer is no, and it is gated rather than merely documented, because
    IF is numeric and available -- which is exactly what makes it dangerous.

    Three independent reasons, any one sufficient:
      - it has no anchor in the cited paper's abstract, so it cannot pass
        guards 1-3 and G3 cannot trace it (monthly 0.4)
      - it judges an article by its journal (DORA / Leiden)
      - in a Type-D domain it reinstates the scalar ranking that the
        significance section exists to replace
    """
    for slug in ("molecular_synthesis", "perovskite_pv"):
        base = yaml.safe_load(
            (ROOT / "config" / "domains" / f"{slug}.yaml")
            .read_text(encoding="utf-8"))
        base["metrics"].append({
            "key": "journal_if", "label": "journal impact factor",
            "unit": "", "direction": "higher_better", "role": "quality",
            "plausibility": {"min": 0.0, "max": 200.0},
            "device_binding": False})
        f = tmp_path / f"{slug}.yaml"
        f.write_text(yaml.safe_dump(base), encoding="utf-8")
        errs = domain_lint.lint(f)
        assert any("VENUE-PRESTIGE PROXY" in e for e in errs), \
            f"{slug}: linter admitted a journal impact factor as a metric"


@pytest.mark.parametrize("key", ["impact_factor", "sjr", "citescore",
                                 "jcr_quartile", "h_index"])
def test_linter_refuses_every_prestige_alias(tmp_path, key):
    """The refusal must not be defeated by renaming the field."""
    base = yaml.safe_load(
        (ROOT / "config" / "domains" / "perovskite_pv.yaml")
        .read_text(encoding="utf-8"))
    base["metrics"].append({
        "key": key, "label": "venue prestige", "unit": "",
        "direction": "higher_better", "role": "quality",
        "plausibility": {"min": 0.0, "max": 100.0},
        "device_binding": False})
    f = tmp_path / "perovskite_pv.yaml"
    f.write_text(yaml.safe_dump(base), encoding="utf-8")
    assert any("VENUE-PRESTIGE PROXY" in e for e in domain_lint.lint(f)), \
        f"alias {key!r} slipped past the venue-prestige refusal"


def test_no_shipped_domain_declares_a_prestige_metric():
    """Belt and braces: the live instances must be clean."""
    for p in DOMAINS:
        D = yaml.safe_load(p.read_text(encoding="utf-8"))
        for m in (D.get("metrics") or []):
            k = str(m.get("key", "")).lower()
            assert k not in domain_lint.VENUE_PRESTIGE_KEYS, \
                f"{p.name} declares prestige metric {k!r}"


# ------------------------------------------------------------ token ledger
def test_yearly_token_ledger_reads_real_runs():
    from stages.yearly_tokens import aggregate_year
    a = aggregate_year("2026")
    assert a["n_months_measured"] >= 3
    # The extractor genuinely reports usage.
    assert a["extractor"]["tokens_out"] > 0
    # The writer genuinely does not: agy -p prints prose and reports nothing.
    assert a["writer"]["tokens_out_reported"] == 0
    assert a["writer"]["est_tokens_out"] > 0


def test_yearly_token_ledger_flags_incredible_input_counts():
    """The measured ledger reports ~6 input tokens per extractor call while
    each call carries twelve abstracts. That is not a credible prompt-token
    count, and the module must SAY so rather than quoting it as fact."""
    from stages.yearly_tokens import aggregate_year
    a = aggregate_year("2026")
    assert any("NOT CREDIBLE" in f for f in a["flags"]), \
        "an implausible input-token total was not flagged"


def test_aggregation_saves_the_whole_extraction_budget():
    """The cost argument for aggregating rather than re-running, computed."""
    from stages.yearly_tokens import aggregate_year
    p = aggregate_year("2026")["projection"]
    assert p["aggregate_extractor_tokens_out"] == 0
    assert p["naive_reextract_12mo_tokens_out"] > 1_000_000
    # v1.0 claimed ~7h. That was extraction only; end-to-end is ~12h.
    assert p["naive_reextract_minutes"] == 420
    assert p["naive_end_to_end_minutes"] == 720
    assert p["minutes_saved_vs_naive"] > 500


def test_pv_domain_reproduces_the_live_axes():
    """Backward compatibility: the PV instance must match the live config,
    or a domain-driven run would not reproduce the shipped issues."""
    live = yaml.safe_load(
        (ROOT / "config" / "axes.yaml").read_text(encoding="utf-8"))["axes"]
    inst = yaml.safe_load(
        (ROOT / "config" / "domains" / "perovskite_pv.yaml")
        .read_text(encoding="utf-8"))["axes"]
    assert set(inst) == set(live), \
        "PV domain instance and config/axes.yaml disagree on the axis set"


def test_pv_single_junction_bound_matches_the_g3c_gate():
    """G3c hardcodes 29.4 in s18d. The registry must agree with it."""
    inst = yaml.safe_load(
        (ROOT / "config" / "domains" / "perovskite_pv.yaml")
        .read_text(encoding="utf-8"))
    cert = [m for m in inst["metrics"] if m["key"] == "pce_certified"][0]
    assert cert["plausibility"]["max"] == 29.4
    src = (ROOT / "scripts" / "stages" / "s18d_build_v4.py").read_text(
        encoding="utf-8")
    assert "29.4" in src, "G3c's SQ limit vanished from the build"


# ---------------------------------------------------------------- yearly
def test_yearly_map_builds_on_real_annual_mass():
    m = ysm.build_map("2026", MASS_2026, n_months=3)
    assert m["sections"], "no sections"
    assert m["sections"][-1]["role"] == "gaps", "gaps must be last"
    roles = [s["role"] for s in m["sections"]]
    for required in ("intro", "trajectory", "synthesis", "audit", "gaps"):
        assert required in roles, f"yearly spine lost the {required} role"
    n_mech = roles.count("mechanism")
    assert ysm.MIN_MECH <= n_mech <= ysm.MAX_MECH


def test_yearly_cite_sum_leaves_headroom_under_the_issue_ceiling():
    """Handbook 6.5, at annual scale. This assertion already fired once
    during development: at WORDS_PER_CITE=40 the minimums summed to 214
    against a band top of 200, and the GENERATOR was moved to 45 rather than
    the gate being widened."""
    m = ysm.build_map("2026", MASS_2026, n_months=3)
    lo, hi = ysm.CITE_SUM_BAND
    assert lo <= m["cite_target_sum"] <= hi

    Y = yaml.safe_load(
        (ROOT / "config" / "yearly.yaml").read_text(encoding="utf-8"))
    ceiling = Y["citations_yearly"]["total_band"][1]
    assert m["cite_target_sum"] < ceiling, (
        "per-section minimums must sit BELOW the issue ceiling, or a writer "
        "obeying every section fails the manuscript")
    assert ceiling - m["cite_target_sum"] >= 15, (
        "less than 15 citations of headroom; a generously citing writer "
        "will overshoot G2c while every section obeyed its instructions")


def test_yearly_map_is_deterministic():
    """A map that changed per run would make resumes redraft forever."""
    a = ysm.build_map("2026", MASS_2026)
    b = ysm.build_map("2026", MASS_2026)
    assert a["sha256"] == b["sha256"]


def test_yearly_map_rotates_titles_by_year():
    a = ysm.build_map("2026", MASS_2026)
    b = ysm.build_map("2027", MASS_2026)
    ta = [s["title"] for s in a["sections"] if s["role"] == "trajectory"][0]
    tb = [s["title"] for s in b["sections"] if s["role"] == "trajectory"][0]
    assert ta != tb, "consecutive yearly issues reuse one trajectory title"


def test_yearly_map_never_drops_an_axis():
    """An axis that misses the cut must FOLD, so its papers still reach the
    writer rather than vanishing from the issue."""
    thin = dict(MASS_2026, scale_up=3)
    m = ysm.build_map("2026", thin)
    reachable = set()
    for s in m["sections"]:
        reachable.update(s.get("axes") or [])
    assert set(thin) <= reachable, \
        f"axes vanished from the issue: {set(thin) - reachable}"


def test_yearly_map_word_ceilings_are_bounded():
    m = ysm.build_map("2026", MASS_2026)
    for s in m["sections"]:
        if s["role"] == "mechanism":
            assert ysm.MECH_MIN_WORDS <= s["ceiling"] <= ysm.MECH_MAX_WORDS


def test_yearly_body_is_two_to_three_times_monthly():
    """Havid's brief: a yearly issue carries 2-3x the monthly content."""
    from stages.section_map import BODY_WORDS as MONTHLY_BODY
    ratio = ysm.BODY_WORDS / MONTHLY_BODY
    assert 2.0 <= ratio <= 3.2, f"yearly/monthly body ratio {ratio:.2f}"


def test_yearly_bands_are_new_keys_not_widened_monthly_ones():
    """Handbook 6.1: never widen a gate to make output pass. The monthly
    bands must still describe the monthly artifact."""
    G = yaml.safe_load(
        (ROOT / "config" / "gates.yaml").read_text(encoding="utf-8"))
    assert G["citations"]["total_band"] == [60, 85]
    assert G["abstract"]["word_band"] == [260, 340]
    assert G["paper_v3"]["total_page_band"] == [12, 17]

    Y = yaml.safe_load(
        (ROOT / "config" / "yearly.yaml").read_text(encoding="utf-8"))
    assert Y["citations_yearly"]["total_band"][0] > G["citations"]["total_band"][1]
    assert Y["yearly"]["total_page_band"][0] > G["paper_v3"]["total_page_band"][1]


def test_yearly_aggregate_fails_closed_on_a_partial_year():
    from stages.yearly_aggregate import aggregate
    with pytest.raises(SystemExit) as ei:
        aggregate("2026", require_full_year=True)
    assert "months built" in str(ei.value)


def test_yearly_aggregate_reports_extractor_provenance():
    """8.4: provenance comes from records, never from live config. A yearly
    issue spanning an extractor swap must say so."""
    from stages.yearly_aggregate import aggregate
    agg = aggregate("2026", require_full_year=False)
    assert agg["extractors"], "no extractor provenance recorded"
    assert sum(agg["extractors"].values()) == agg["cards_n"]


def test_yearly_annual_rate_is_pooled_not_averaged():
    """An annual percentage is NOT the mean of twelve monthly percentages:
    months have different denominators, so averaging weights a thin month
    equally with a thick one."""
    from stages.yearly_stats import annual_rates
    series = {
        "certified.n": [10, 0],
        "certified.denominator": [100, 900],
        "certified.pct": [10.0, 0.0],
    }
    for k in ("efficiency_stated", "stabilised", "area_stated",
              "isos_label", "hysteresis"):
        series[f"{k}.n"] = []
        series[f"{k}.denominator"] = []
        series[f"{k}.pct"] = []
    out = annual_rates(series)
    assert out["audit.year.certified.pct"] == 1.0, \
        "pooled rate must be 10/1000 = 1.0%, not mean(10%, 0%) = 5%"
    assert out["audit.year.certified.month_min_pct"] == 0.0
    assert out["audit.year.certified.month_max_pct"] == 10.0


def test_yearly_frontier_excludes_simulation():
    """5.1: a drift-diffusion study reporting ~30.8% sat beside certified
    hardware on the efficiency frontier until a human noticed."""
    from stages.yearly_stats import frontier_series
    agg = {"cards": [
        {"source_month": "2026-01", "lens": "experimental",
         "performance": {"pce_certified": {"value": 25.0}}},
        {"source_month": "2026-01", "lens": "theory",
         "performance": {"pce_certified": {"value": 40.0}}},
    ]}
    fs = frontier_series(agg)
    assert fs["top_certified"] == [25.0], \
        "a theory value reached the measured frontier series"


# -------------------------------------------------------------- handbooks
# The yearly + general HANDBOOK tests were removed on 2026-09-09.
#
# Havid moved MASTER_HANDBOOK_YEARLY.md and MASTER_HANDBOOK_GENERAL.md into a
# separate project, so those two documents no longer live in this repo and
# there is nothing here for them to drift against. A permanently-skipped test
# would just be dead code asserting nothing.
#
# WHAT THIS DELIBERATELY GIVES UP, so it is a visible decision and not a
# silent hole: the yearly and domain CODE is still here
# (config/yearly.yaml, config/domains/*.yaml, stages/yearly_section_map.py,
# stages/yearly_stats.py, stages/domain_lint.py) and every test above still
# guards its BEHAVIOUR. What is no longer checked is that a handbook
# DESCRIBES that behaviour correctly, because the describing document is now
# maintained elsewhere. If the companion handbooks ever return to this repo,
# restore these tests from git history (they were last present in the commit
# that removed the two files) rather than writing weaker ones.
#
# The monthly handbook is unaffected: MASTER_HANDBOOK.md is still gated by
# tests/test_handbook.py, which is the contract this repo actually runs on.
