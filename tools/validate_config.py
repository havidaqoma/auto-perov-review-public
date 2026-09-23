"""validate_config.py: schema-check the YAML that drives every gate.

The one real gap Gemini's Executable Skill Contract spec identified in this
pipeline. Every gate threshold lives in `config/gates.yaml`, and until now a
typo in a KEY was silent: `body_max_ratio` misspelled as `body_max_ration`
makes `G["novelty"]["body_max_ratio"]` raise KeyError at best, and at worst a
`.get(key, default)` somewhere swallows it and the gate runs against a default
nobody chose. That is the same failure shape as `abstract_word_max: 250`
sitting in config with no gate reading it while a 326-word abstract shipped.

So the config gets a schema with `extra='forbid'`: an unknown key is an error,
not a note. Physical and editorial bounds are validators, not comments.

Exit codes
----------
0  every config file validates
1  at least one violation (the message names file, key, expectation, value)
2  pydantic missing, or a config file is absent or unparseable

Usage
-----
    python tools/validate_config.py
    python tools/validate_config.py --tree yearly
"""
from __future__ import annotations

import argparse
import pathlib
import sys

try:
    import yaml
except ImportError:
    print("FAIL: pyyaml missing. pip install -r requirements.txt",
          file=sys.stderr)
    raise SystemExit(2) from None

try:
    from pydantic import BaseModel, ConfigDict, Field, field_validator
except ImportError:
    print("FAIL: pydantic missing. pip install -r requirements.txt",
          file=sys.stderr)
    raise SystemExit(2) from None

ROOT = pathlib.Path(__file__).resolve().parents[1]

# The Shockley-Queisser limit for a single junction under AM1.5G. The build's
# G3c gate uses the same number; it is stated once here and once there rather
# than being passed around, because a shared constant that drifts is worse
# than two that are each checked.
SQ_SINGLE_JUNCTION_PCT = 29.4


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _band(v: list[int] | list[float], name: str):
    if len(v) != 2:
        raise ValueError(f"{name} must be [low, high], got {v!r}")
    lo, hi = v
    if lo > hi:
        raise ValueError(f"{name} is inverted: low {lo} > high {hi}")
    if lo < 0:
        raise ValueError(f"{name} low bound is negative: {lo}")
    return v


class ModeBand(Strict):
    prose_word_ceiling: int = Field(gt=0, lt=100_000)
    content_page_band: list[int]
    total_page_band: list[int]
    max_body_citations: int = Field(gt=0, lt=1000)

    @field_validator("content_page_band", "total_page_band")
    @classmethod
    def bands(cls, v, info):
        return _band(v, info.field_name)


class PageBandOnly(Strict):
    content_page_band: list[int]
    total_page_band: list[int]

    @field_validator("content_page_band", "total_page_band")
    @classmethod
    def bands(cls, v, info):
        return _band(v, info.field_name)


class Novelty(Strict):
    # Ratios are similarity fractions. A value above 1 cannot be a ratio, and
    # a value of 1 means "identical text passes", which would make the gate
    # ornamental. Both are rejected.
    body_max_ratio: float = Field(gt=0, lt=1)
    abstract_max_ratio: float = Field(gt=0, lt=1)
    shingle_words: int = Field(ge=5, le=50)


class AbstractCfg(Strict):
    word_band: list[int]

    @field_validator("word_band")
    @classmethod
    def band(cls, v):
        _band(v, "word_band")
        if v[0] < 100:
            raise ValueError(
                f"abstract.word_band low bound {v[0]} is under 100 words; a "
                "review abstract that short cannot carry the audit numerals "
                "G3 requires")
        return v


class Citations(Strict):
    total_band: list[int]

    @field_validator("total_band")
    @classmethod
    def band(cls, v):
        return _band(v, "total_band")


class Gates(Strict):
    mode: str
    paper: ModeBand
    bulletin: ModeBand
    paper_v3: PageBandOnly
    novelty: Novelty
    abstract: AbstractCfg
    citations: Citations

    count_band: list[int]
    max_pages: int = Field(gt=0, lt=200)
    depth_target: int = Field(gt=0)
    depth_band: list[int]
    axis_min_depth: int = Field(gt=0)
    venue_share_max_pct: float = Field(gt=0, le=100)
    institution_share_max_pct: float = Field(gt=0, le=100)
    preprint_share_min_pct: float = Field(ge=0, le=100)
    preprint_share_max_pct: float = Field(ge=0, le=100)
    sensitivity_draws: int = Field(gt=0)
    seed: int
    printable_precision_min: float = Field(gt=0, le=1)
    g1b_partial_max_pct: float = Field(ge=0, le=100)
    g1b_partial_pause_pct: float = Field(ge=0, le=100)
    max_title_words: int = Field(gt=0, lt=100)
    title_colons: int = Field(ge=0, le=3)
    abstract_word_max: int = Field(gt=0)
    abstract_audit_numerals_min: int = Field(ge=0)
    anchor_word_max: int = Field(gt=0, lt=200)
    summary_word_max: int = Field(gt=0, lt=500)
    max_review_rounds: int = Field(gt=0, le=10)
    accept_red_max: int = Field(ge=0)
    accept_orange_max: int = Field(ge=0)
    cron_day: int = Field(ge=1, le=28)

    @field_validator("mode")
    @classmethod
    def known_mode(cls, v):
        if v not in ("paper", "bulletin"):
            raise ValueError(f"mode must be paper or bulletin, got {v!r}")
        return v

    @field_validator("count_band", "depth_band")
    @classmethod
    def bands(cls, v, info):
        return _band(v, info.field_name)

    @field_validator("preprint_share_max_pct")
    @classmethod
    def preprint_order(cls, v, info):
        lo = info.data.get("preprint_share_min_pct")
        if lo is not None and lo > v:
            raise ValueError(
                f"preprint_share_min_pct {lo} exceeds max {v}; no corpus can "
                "satisfy both")
        return v

    @field_validator("g1b_partial_pause_pct")
    @classmethod
    def pause_above_max(cls, v, info):
        mx = info.data.get("g1b_partial_max_pct")
        if mx is not None and v < mx:
            raise ValueError(
                f"g1b_partial_pause_pct {v} is below g1b_partial_max_pct "
                f"{mx}; the pause threshold must sit at or above the fail "
                "threshold or the run pauses before it can fail")
        return v


class Axis(Strict):
    name: str
    keywords: list[str]

    @field_validator("keywords")
    @classmethod
    def nonempty(cls, v, info):
        if not v:
            raise ValueError("axis has no keywords, so it can never score")
        dupes = {k for k in v if v.count(k) > 1}
        if dupes:
            raise ValueError(f"duplicate keywords double-count a hit: "
                             f"{sorted(dupes)}")
        return v


class Axes(Strict):
    axes: dict[str, Axis]

    @field_validator("axes")
    @classmethod
    def enough(cls, v):
        if len(v) < 2:
            raise ValueError(f"{len(v)} axes defined; the section map needs at "
                             "least two to build a body")
        return v


class Preprint(Strict):
    platform: str
    platform_slug: str
    platform_url: str
    submission_route: str
    main_content: str
    main_content_alternatives: list[str]
    subject_category_primary: str
    subject_categories_secondary: list[str]
    license: str
    doi_prefix: str
    preprint_doi: str | None
    api_submission_supported: bool

    @field_validator("preprint_doi")
    @classmethod
    def no_invented_doi(cls, v, info):
        # A DOI is assigned on posting. A non-null value here that does not
        # start with the platform's prefix is a fabricated citation, which is
        # the exact failure class this whole project exists to prevent.
        if v is None:
            return v
        pref = info.data.get("doi_prefix")
        if pref and not v.startswith(pref):
            raise ValueError(
                f"preprint_doi {v!r} does not start with the platform prefix "
                f"{pref!r}. A DOI that the platform did not assign is a "
                "fabricated identifier; leave it null until posting.")
        return v

    @field_validator("api_submission_supported")
    @classmethod
    def manual_only(cls, v, info):
        if v and info.data.get("submission_route") == "manual_portal":
            raise ValueError(
                "api_submission_supported is true while submission_route is "
                "manual_portal; there is no automated submission code path "
                "in this repository")
        return v


SCHEMAS: dict[str, type[BaseModel]] = {
    "gates.yaml": Gates,
    "axes.yaml": Axes,
    "preprint.yaml": Preprint,
}

# Which config files each cadence MUST have. Declared per tree rather than
# treating every absence as acceptable: "optional if missing" is how
# abstract_word_max ended up sitting in config with no gate reading it. A file
# is either required here, or listed as deliberately absent with a reason.
REQUIRED: dict[str, set[str]] = {
    ".": {"gates.yaml", "axes.yaml", "preprint.yaml"},
    # The yearly cadence assembles a retrospective from the monthly runs and
    # is not posted as a preprint, so it carries no preprint.yaml. That is a
    # design decision, not a missing file.
    "yearly": {"gates.yaml", "axes.yaml"},
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", default=".",
                    help="subtree holding config/ ('.' for monthly+half-year, "
                         "'yearly' for the yearly cadence)")
    a = ap.parse_args()
    cfg = ROOT / a.tree / "config"
    if not cfg.is_dir():
        print(f"FAIL: {cfg} missing", file=sys.stderr)
        return 2

    bad = 0
    required = REQUIRED.get(a.tree, set(SCHEMAS))
    for fname, model in SCHEMAS.items():
        p = cfg / fname
        if not p.exists():
            if fname in required:
                print(f"FAIL {fname}: required for tree {a.tree!r} but not "
                      f"found in {cfg}", file=sys.stderr)
                bad += 1
            else:
                print(f"--   {fname}  (not used by this cadence)")
            continue
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            print(f"FAIL {fname}: unparseable YAML: {e}", file=sys.stderr)
            bad += 1
            continue
        try:
            model(**data)
        except Exception as e:                        # noqa: BLE001
            print(f"FAIL {fname}:", file=sys.stderr)
            for line in str(e).splitlines():
                print(f"  {line}", file=sys.stderr)
            bad += 1
            continue
        nkeys = len(data) if isinstance(data, dict) else 0
        print(f"ok   {fname}  ({nkeys} top-level keys, extra keys forbidden)")

    if bad:
        print(f"\n{bad} config file(s) failed validation", file=sys.stderr)
        return 1
    print(f"\nall {len(SCHEMAS)} schema-checked config files valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
