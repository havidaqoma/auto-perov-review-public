"""Contract tests for the yearly BACKFILL path.

These tests exist because this project inverts the monthly project's central
rule. There, a yearly issue is the union of twelve monthly runs. Here, a year
is harvested in one sweep and sliced into months afterwards.

That means two verified modules (`yearly_stats`, `yearly_section_map`) are
being fed from a NEW source. If the new source's output shape drifts from the
old aggregator's by even one key, those modules fail -- or worse, silently
compute against a missing key.

So every test below pins a contract, not an implementation. All of them run
on synthetic data: no network, no API key, no live harvest.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from stages import yearly_audit as ya                       # noqa: E402
from stages import yearly_corpus as yc                      # noqa: E402
from stages import yearly_stats as ys                       # noqa: E402
from stages import yearly_section_map as ysm                # noqa: E402
from stages.s01_harvest_yearly import date_precision        # noqa: E402
from stages.util import is_year, period_bounds, year_months  # noqa: E402


# ------------------------------------------------------- period plumbing
def test_is_year_distinguishes_year_from_month():
    """A stage that guessed would harvest one month and label it a year."""
    assert is_year("2025") is True
    assert is_year("2025-06") is False
    assert is_year("25") is False
    assert is_year("abcd") is False


def test_period_bounds_handles_both_shapes():
    assert period_bounds("2025") == ("2025-01-01", "2025-12-31")
    assert period_bounds("2025-06") == ("2025-06-01", "2025-06-30")
    # February, because a hardcoded 30 or 31 would silently drop or invent a day
    assert period_bounds("2025-02") == ("2025-02-01", "2025-02-28")
    assert period_bounds("2024-02") == ("2024-02-01", "2024-02-29")


def test_year_months_returns_twelve_ordered_months():
    ms = year_months("2025")
    assert len(ms) == 12
    assert ms[0] == "2025-01" and ms[-1] == "2025-12"
    assert ms == sorted(ms)


def test_year_months_rejects_a_month():
    with pytest.raises(ValueError):
        year_months("2025-06")


# ------------------------------------------- the January lumping artefact
def test_jan_first_is_treated_as_imprecise():
    """OpenAlex stores an imprecise date as Jan 1.

    Measured: 2025-01 carries 1,569 works against ~550 for every other
    month. Untreated that is a fabricated January spike on F5.
    """
    assert date_precision("2025-01-01", "2025") == "year"


def test_a_real_january_date_is_kept():
    """The fix must not throw away genuine January papers."""
    assert date_precision("2025-01-15", "2025") == "day"
    assert date_precision("2025-01-31", "2025") == "day"


def test_other_months_are_day_precision():
    for d in ("2025-06-03", "2025-12-31", "2025-02-28"):
        assert date_precision(d, "2025") == "day"


def test_jan_first_of_another_year_is_not_this_years_artefact():
    """The rule is anchored to the harvested year, not to any Jan 1."""
    assert date_precision("2024-01-01", "2025") == "day"


def test_empty_date_is_unknown_not_day():
    assert date_precision("", "2025") == "unknown"


# --------------------------------------------------- duplicate collapse
def test_canon_work_key_collapses_elsevier_j_prefix():
    """A writer once transcribed '10.1016/joule...' for a card keyed
    '10.1016/j.joule...' and the citation silently failed to resolve."""
    a = yc.canon_work_key("10.1016/j.joule.2025.102538")
    b = yc.canon_work_key("10.1016/joule.2025.102538")
    assert a == b


def test_canon_work_key_is_case_and_punctuation_insensitive():
    assert yc.canon_work_key("10.1038/S41586-025-1") == \
           yc.canon_work_key("10.1038/s41586.025.1")


def test_canon_work_key_of_empty_is_empty():
    assert yc.canon_work_key("") == ""
    assert yc.canon_work_key(None) == ""


# ------------------------------------------------------ synthetic fixture
def _card(wk: str, month: str, axis: str, *, cert=None, champ=None,
          lens="experimental", model="test-extractor") -> dict:
    perf: dict = {}
    if cert is not None:
        perf["pce_certified"] = {"value": cert}
    if champ is not None:
        perf["pce_champion"] = {"value": champ}
    return {
        "work_key": wk,
        "publication_date": f"{month}-15",
        "date_precision": "day",
        "axis": axis,
        "lens": lens,
        "performance": perf,
        "extractor": {"model": model},
    }


def _work(wk: str, month: str, *, precision="day", depth=False) -> dict:
    day = "01" if precision == "year" else "15"
    date = f"{month}-{day}" if precision == "day" else f"{month[:4]}-01-01"
    return {"work_key": wk, "publication_date": date,
            "date_precision": precision, "depth": depth}


@pytest.fixture
def synthetic_year(tmp_path, monkeypatch):
    """A full twelve-month synthetic year on disk, in the annual layout."""
    runs = tmp_path / "runs"
    rd = runs / "2025_a1b2c3d4"
    (rd / "private").mkdir(parents=True)
    (runs / "2025.active").write_text("2025_a1b2c3d4", encoding="utf-8")

    axes = ["defects", "interfaces", "composition",
            "stability", "architecture", "scale_up"]
    # Keys are ZERO-PADDED deliberately. canon_work_key strips every
    # non-alphanumeric character, so unpadded 'w1-11' and 'w11-1' both
    # canonicalise to '101w111' and collide. Real DOIs rarely collide this
    # way, but a fixture that collides silently under-counts and makes the
    # duplicate assertion measure the wrong thing.
    corpus, cards = [], []
    for i, m in enumerate(year_months("2025")):
        for j in range(30):
            corpus.append(_work(f"10.1/w{i:02d}x{j:02d}", m, depth=(j < 12)))
        for j in range(12):
            corpus_key = f"10.1/w{i:02d}x{j:02d}"
            cards.append(_card(corpus_key, m, axes[(i + j) % len(axes)],
                               cert=30.0 + i * 0.1 if j == 0 else None,
                               champ=31.0 + i * 0.1 if j == 1 else None))
    # two imprecise works: real papers, unknown month
    corpus.append(_work("10.1/impreciseA", "2025-01", precision="year"))
    corpus.append(_work("10.1/impreciseB", "2025-01", precision="year"))
    # one duplicate inside the sweep
    corpus.append(_work("10.1/w00x00", "2025-01"))

    def _w(p, rows):
        p.write_text("\n".join(json.dumps(r) for r in rows) + "\n",
                     encoding="utf-8")

    _w(rd / "05_corpus.jsonl", corpus)
    _w(rd / "claim_cards.jsonl", cards)

    monkeypatch.setattr(yc, "RUNS", runs)
    monkeypatch.setattr(ys, "RUNS", runs)
    import stages.util as u
    monkeypatch.setattr(u, "RUNS", runs)
    return runs


# -------------------------------------------- the aggregator's contract
def test_aggregate_produces_every_key_the_old_aggregator_did(synthetic_year):
    """The whole point of yearly_corpus: same contract, new source.

    If any key here disappears, yearly_stats and yearly_section_map break --
    or compute against a missing key, which is worse.
    """
    agg = yc.aggregate("2025")
    for k in ("year", "months", "n_months", "corpus_n", "cards_n",
              "cross_month_duplicates", "per_month", "extractors",
              "corpus", "cards"):
        assert k in agg, f"contract key {k!r} missing"


def test_aggregate_finds_twelve_months(synthetic_year):
    agg = yc.aggregate("2025")
    assert agg["n_months"] == 12
    assert agg["months"] == year_months("2025")


def test_per_month_blocks_have_the_expected_shape(synthetic_year):
    agg = yc.aggregate("2025")
    for m, blk in agg["per_month"].items():
        for k in ("corpus_n", "depth_n", "cards_n", "axis_depth"):
            assert k in blk, f"{m} missing {k}"
        assert isinstance(blk["axis_depth"], dict)


def test_imprecise_works_stay_in_corpus_but_get_no_month(synthetic_year):
    """They are real papers. Only their MONTH is unknown."""
    agg = yc.aggregate("2025")
    assert agg["month_unknown_corpus"] == 2
    unknown = [c for c in agg["corpus"] if c["source_month"] is None]
    assert len(unknown) == 2


def test_within_sweep_duplicate_is_collapsed(synthetic_year):
    agg = yc.aggregate("2025")
    assert agg["cross_month_duplicates"] == 1


def test_duplicate_semantics_are_stated_not_inferred(synthetic_year):
    """A 0 here is a design property, not the suspicious zero the handbook
    warns about. The distinction must be machine-readable."""
    agg = yc.aggregate("2025")
    assert "duplicate_semantics" in agg
    assert "backfill" in agg["duplicate_semantics"]


def test_extractor_provenance_comes_from_card_records(synthetic_year):
    """A back-matter fact about which model did what is prose reaching a
    reader. It must come from records, never from live config."""
    agg = yc.aggregate("2025")
    assert agg["extractors"] == {"test-extractor": 144}


def test_aggregate_fails_closed_without_a_harvest(tmp_path, monkeypatch):
    runs = tmp_path / "runs"
    runs.mkdir()
    monkeypatch.setattr(yc, "RUNS", runs)
    with pytest.raises(SystemExit) as e:
        yc.aggregate("2025")
    assert "no harvest" in str(e.value).lower()


def test_aggregate_fails_closed_on_a_partial_year(synthetic_year):
    """A partial year passes every other gate and misstates its own scope."""
    rd = synthetic_year / "2025_a1b2c3d4"
    rows = [json.loads(l) for l in
            (rd / "05_corpus.jsonl").read_text(encoding="utf-8").splitlines() if l]
    keep = [r for r in rows if not r["publication_date"].startswith("2025-12")]
    (rd / "05_corpus.jsonl").write_text(
        "\n".join(json.dumps(r) for r in keep) + "\n", encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        yc.aggregate("2025")
    assert "2025-12" in str(e.value)


def test_partial_year_is_allowed_only_explicitly(synthetic_year):
    rd = synthetic_year / "2025_a1b2c3d4"
    rows = [json.loads(l) for l in
            (rd / "05_corpus.jsonl").read_text(encoding="utf-8").splitlines() if l]
    keep = [r for r in rows if not r["publication_date"].startswith("2025-12")]
    (rd / "05_corpus.jsonl").write_text(
        "\n".join(json.dumps(r) for r in keep) + "\n", encoding="utf-8")
    agg = yc.aggregate("2025", require_full_year=False)
    assert agg["n_months"] == 11


def test_zero_cards_is_a_bug_not_an_empty_year(synthetic_year):
    rd = synthetic_year / "2025_a1b2c3d4"
    (rd / "claim_cards.jsonl").write_text("", encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        yc.aggregate("2025")
    assert "silent-zero" in str(e.value)


# --------------------------------------------------- downstream still work
def test_axis_mass_is_sorted_by_descending_mass(synthetic_year):
    agg = yc.aggregate("2025")
    mass = yc.axis_mass(agg)
    vals = list(mass.values())
    assert vals == sorted(vals, reverse=True)
    assert sum(vals) == agg["cards_n"]


def test_section_map_builds_from_the_new_source(synthetic_year):
    """The verified section map must work unchanged on backfill data."""
    agg = yc.aggregate("2025")
    mp = ysm.build_map("2025", yc.axis_mass(agg), n_months=agg["n_months"])
    assert mp["sections"], "no sections generated"
    assert mp["sections"][-1]["role"] == "gaps", "gaps must be last"


def test_section_map_is_deterministic(synthetic_year):
    """A map that changed per run would make resumes redraft forever."""
    agg = yc.aggregate("2025")
    m1 = ysm.build_map("2025", yc.axis_mass(agg), n_months=12)
    m2 = ysm.build_map("2025", yc.axis_mass(agg), n_months=12)
    assert m1["sha256"] == m2["sha256"]


def test_frontier_series_excludes_simulation(synthetic_year):
    """A drift-diffusion study reporting ~30.8% once sat beside certified
    hardware until a human noticed."""
    agg = yc.aggregate("2025")
    agg["cards"].append(_card("10.1/theory", "2025-06", "defects",
                              cert=40.0, lens="theory"))
    fs = ys.frontier_series(agg)
    certs = [c for c in fs["top_certified"] if c is not None]
    assert 40.0 not in certs, "a theory value reached the measured frontier"


# ------------------------------------------------- pooled-rate arithmetic
def test_annual_rate_is_pooled_not_the_mean_of_monthly_rates():
    """The single easiest way to ship a wrong number, and it looks correct.

    month 1: 10/100 = 10.0%     month 2: 0/900 = 0.0%
    pooled  = 10/1000 = 1.0%    mean of rates = 5.0%
    A five-fold error.
    """
    series = {
        "months": ["2025-01", "2025-02"],
        "efficiency_stated.n": [10, 0],
        "efficiency_stated.denominator": [100, 900],
        "efficiency_stated.pct": [10.0, 0.0],
    }
    for k in ys.AUDIT_KEYS:
        series.setdefault(f"{k}.n", [0, 0])
        series.setdefault(f"{k}.denominator", [100, 900])
        series.setdefault(f"{k}.pct", [0.0, 0.0])
    out = ys.annual_rates(series)
    assert out["audit.year.efficiency_stated.pct"] == 1.0
    assert out["audit.year.efficiency_stated.pct"] != 5.0


def test_annual_rates_report_the_monthly_spread():
    """A pooled rate hides whether a value sat flat or swung wildly."""
    series = {"months": ["2025-01", "2025-02"]}
    for k in ys.AUDIT_KEYS:
        series[f"{k}.n"] = [3, 15]
        series[f"{k}.denominator"] = [100, 100]
        series[f"{k}.pct"] = [3.0, 15.0]
    out = ys.annual_rates(series)
    assert out["audit.year.certified.month_min_pct"] == 3.0
    assert out["audit.year.certified.month_max_pct"] == 15.0


# ------------------------------------------------------- the audit series
def test_audit_keys_agree_with_yearly_stats():
    """Two lists of audit quantities would be two definitions of what the
    paper measures."""
    assert ya.AUDIT_KEYS == ys.AUDIT_KEYS


def test_audit_regexes_are_imported_not_retyped():
    """A second copy of a detection regex is a second definition."""
    from stages.s04_10 import AUDIT_RX as source_rx
    assert ya.AUDIT_RX is source_rx


def test_audit_detects_a_stated_efficiency():
    fired = ya.audit_one(
        "We report a power conversion efficiency of 25.4% for the device.")
    assert fired["efficiency_stated"] is True


def test_audit_does_not_count_a_current_density_as_an_area():
    """'24.1 mA cm-2' is a current density, not a stated device area."""
    fired = ya.audit_one(
        "The device delivered a short-circuit current of 24.1 mA cm-2 "
        "under one sun illumination with no other geometry reported.")
    assert fired["area_stated"] is False


def test_audit_detects_a_real_device_area():
    fired = ya.audit_one(
        "Devices with an aperture area of 1.02 cm2 were measured "
        "under simulated sunlight to confirm the reported performance.")
    assert fired["area_stated"] is True


def test_uncertified_is_not_counted_as_certified():
    fired = ya.audit_one(
        "These uncertified results were obtained in our own laboratory "
        "without any independent verification of the stated efficiency.")
    assert fired["certified"] is False


def test_monthly_series_shape_matches_what_annual_rates_consumes():
    """The seam most likely to break: series -> annual_rates.

    The abstract below is deliberately over 40 words. An abstract under the
    floor is dropped from the denominator, so a short fixture would make this
    test pass for the wrong reason -- it would assert on an empty pool.
    """
    months = year_months("2025")
    corpus, abstracts = [], {}
    text = (
        "We report a certified power conversion efficiency of 25.1% for a "
        "device measured under standard test conditions, with a stabilised "
        "maximum power point output confirmed over an extended period in "
        "ambient air, alongside reverse scan and forward scan data and an "
        "aperture area of 1.02 cm2 for the champion cell described "
        "throughout this present study report.")
    assert len(text.split()) >= ya.MIN_ABSTRACT_WORDS
    for i, m in enumerate(months):
        for j in range(5):
            wk = f"10.1/x{i:02d}y{j:02d}"
            corpus.append({"work_key": wk, "source_month": m, "depth": j < 2})
            abstracts[wk] = text
    series = ya.monthly_series("2025", months, corpus, abstracts)
    out = ys.annual_rates(series)
    assert out["audit.year.efficiency_stated.pct"] == 100.0
    assert out["audit.year.efficiency_stated.denominator"] == 60


def test_short_abstracts_are_excluded_from_the_denominator():
    """Counting works without usable abstracts would depress every rate,
    and the depression would look like a finding about the field."""
    months = year_months("2025")
    corpus, abstracts = [], {}
    for m in months:
        corpus.append({"work_key": f"a-{m}", "source_month": m})
        abstracts[f"a-{m}"] = "Too short."
    series = ya.monthly_series("2025", months, corpus, abstracts)
    assert all(d == 0 for d in series["efficiency_stated.denominator"])
    assert all(p is None for p in series["efficiency_stated.pct"])


def test_month_unknown_works_are_counted_separately():
    months = year_months("2025")
    corpus = [{"work_key": "u1", "source_month": None},
              {"work_key": "u2", "source_month": None}]
    for m in months:
        corpus.append({"work_key": f"k-{m}", "source_month": m})
    series = ya.monthly_series("2025", months, corpus, {})
    assert series["month_unknown"] == 2


def test_assert_month_coverage_rejects_a_hole():
    months = year_months("2025")
    series = {"months": months, "corpus_n": [5] * 11 + [0]}
    with pytest.raises(SystemExit) as e:
        ya.assert_month_coverage("2025", series)
    assert "2025-12" in str(e.value)


def test_assert_month_coverage_passes_a_full_year():
    months = year_months("2025")
    ya.assert_month_coverage("2025", {"months": months,
                                      "corpus_n": [5] * 12})


# ------------------------------------------------------ never widen a gate
def test_monthly_bands_are_untouched_by_the_yearly_config():
    """The yearly bands must be NEW keys, never widened monthly ones."""
    import yaml
    g = yaml.safe_load((ROOT / "config" / "gates.yaml").read_text(
        encoding="utf-8"))
    y = yaml.safe_load((ROOT / "config" / "yearly.yaml").read_text(
        encoding="utf-8"))
    assert g["paper_v3"]["total_page_band"] == [12, 17]
    assert g["paper_v3"]["content_page_band"] == [8, 11]
    # and the yearly floors sit ABOVE the monthly ceilings
    assert y["yearly"]["total_page_band"][0] > g["paper_v3"]["total_page_band"][1]
    assert y["yearly"]["content_page_band"][0] > g["paper_v3"]["content_page_band"][1]
