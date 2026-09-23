"""H1 section map: what sections a HALF-YEAR issue has, computed from its mass.

Relationship to section_map.py and yearly_section_map.py
--------------------------------------------------------
Same contract, third shape. An H1 issue has the two jobs a monthly issue
cannot do -- a TRAJECTORY across its months, and a SYNTHESIS across axes --
but over six months rather than twelve, so the spine is the yearly spine with
period-appropriate titles and ceilings.

What is deliberately IDENTICAL to monthly and yearly
----------------------------------------------------
- titles from a bank, rotated deterministically, so reruns are reproducible
- ceilings allocated proportionally to evidence mass, never typed in
- cite_target = ceiling / WORDS_PER_CITE, clamped
- CITE_SUM_BAND asserted, so a writer obeying every section minimum cannot
  fail the issue-level ceiling (handbook 6.5: the generator moves, never the gate)
- a sha256 over the sections, so cached prose drafted under a different map is
  deleted rather than reused
- axes that miss the cut are FOLDED, never dropped
- gaps is always last, asserted rather than eyeballed

Scale: Havid specified 3x the monthly issue (2026-09-09). Monthly BODY_WORDS is
2400, so this is 7200. That is close to the yearly 7000 on purpose -- a
half-year at 3x and a full year at 2.9x land in the same envelope, because both
are bounded by what a reader will actually read, not by how much evidence
exists. The difference between them is depth of selection, not length.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from stages.section_map import TITLE_BANK, FOLD_INTO  # noqa: E402

# ---- knobs. Scaled from monthly, each with its reason. ----
MIN_MECH = 5           # monthly 4; six months of mass supports one more
MAX_MECH = 6           # there are only six axes in config/axes.yaml
MIN_DEPTH = 20         # monthly 10, yearly 25; config/h1.yaml axis_min_depth
BODY_WORDS = 7200      # monthly 2400 x 3, Havid's spec
MECH_MIN_WORDS = 700   # floor keeps a thin section real
MECH_MAX_WORDS = 1500  # ceiling stops one axis eating the issue

# Monthly uses 42, yearly 45. Set to 45 here and VERIFIED against the real H1
# axis mass below rather than assumed: the yearly file records that 40 produced
# minimums summing to 214 against a band top of 200, reproducing the August v4
# G2c failure of handbook 6.5 at period scale. The assertion at the end of
# build_map is what actually enforces this, on the real mass, every run.
WORDS_PER_CITE = 45
CITE_CLAMP = (8, 34)
# Must leave headroom under citations_h1.total_band [150, 250].
CITE_SUM_BAND = (140, 210)

# Spine ceilings. Fixed because their job does not change with the period.
SPINE_WORDS = {
    "intro": 700,
    "trajectory": 900,   # the month-by-month frontier
    "synthesis": 900,    # what the axes say when read together
    "audit": 700,        # six months of reporting practice
    "gaps": 900,         # always last
}

# Rotated by PERIOD so a later H2/H1 issue differs in phrasing.
TRAJECTORY_BANK = [
    "The Certified Frontier Across {period}",
    "What {period} Verified: The Frontier Month by Month",
    "The {period} Certified Record and Its Trajectory",
]
SYNTHESIS_BANK = [
    "Cross-Cutting Synthesis: What the Mechanisms Say Together",
    "Reading the Mechanisms Together",
    "Convergent Evidence Across Mechanism Axes",
]
AUDIT_BANK = [
    "Reporting Practice Over Six Months",
    "Six Months of Reporting and Characterisation Practice",
    "How the Field Reported Itself in {period}",
]


def _period_index(edition: str) -> int:
    """Deterministic rotation index: 2026-H1 -> 2026*2 + 1."""
    year, half = edition.split("-H")
    return int(year) * 2 + int(half)


def build_map(edition: str, axis_mass: dict[str, int],
              months: list[str] | None = None,
              period_label: str = "January-June 2026") -> dict:
    """Compute the H1 section map from its own evidence mass.

    `axis_mass` is the half-year depth-tier count per axis from
    h1_aggregate.axis_mass(). Passed in rather than read from disk so this
    function stays pure and testable.
    """
    depth = {a: int(n) for a, n in axis_mass.items() if a in TITLE_BANK and n}
    if not depth:
        raise SystemExit(
            "FAIL-CLOSED: no per-axis mass; cannot build an H1 section map "
            "without evidence mass")

    ranked = sorted(depth.items(), key=lambda kv: (-kv[1], kv[0]))
    eligible = [(a, n) for a, n in ranked if n >= MIN_DEPTH]
    chosen = eligible[:MAX_MECH]
    if len(chosen) < MIN_MECH:
        chosen = ranked[:MIN_MECH]
    chosen_axes = [a for a, _ in chosen]

    folded: dict[str, list[str]] = {a: [a] for a in chosen_axes}
    for axis in depth:
        if axis in chosen_axes:
            continue
        target = FOLD_INTO.get(axis)
        while target and target not in chosen_axes:
            target = FOLD_INTO.get(target)
        folded[target or chosen_axes[0]].append(axis)

    total = sum(depth[a] for a in chosen_axes) or 1
    raw = {a: BODY_WORDS * depth[a] / total for a in chosen_axes}
    ceilings = {
        a: int(min(MECH_MAX_WORDS,
                   max(MECH_MIN_WORDS, round(raw[a] / 10) * 10)))
        for a in chosen_axes}

    rot = _period_index(edition)
    sections: list[dict] = []
    n = 0

    def add(role: str, title: str, ceiling: int, cite: int,
            axis: str | None = None, axes: list[str] | None = None,
            n_depth: int | None = None) -> None:
        nonlocal n
        n += 1
        s = {"id": str(n), "role": role, "axis": axis, "axes": axes or [],
             "title": title, "ceiling": ceiling, "cite_target": cite}
        if n_depth is not None:
            s["n_depth"] = n_depth
        sections.append(s)

    add("intro", "Introduction", SPINE_WORDS["intro"], 0)
    add("trajectory",
        TRAJECTORY_BANK[rot % len(TRAJECTORY_BANK)].format(period=period_label),
        SPINE_WORDS["trajectory"], 18)

    for axis in chosen_axes:
        bank = TITLE_BANK[axis]
        ceil = ceilings[axis]
        add("mechanism", bank[rot % len(bank)], ceil,
            max(CITE_CLAMP[0], min(CITE_CLAMP[1],
                                   round(ceil / WORDS_PER_CITE))),
            axis=axis, axes=folded[axis], n_depth=depth[axis])

    add("synthesis", SYNTHESIS_BANK[rot % len(SYNTHESIS_BANK)],
        SPINE_WORDS["synthesis"], 10)
    add("audit", AUDIT_BANK[rot % len(AUDIT_BANK)].format(period=period_label),
        SPINE_WORDS["audit"], 7)
    add("gaps", "Research Gaps and Outlook", SPINE_WORDS["gaps"], 9)

    m = {
        "edition": edition,
        "period_label": period_label,
        "months": months or [],
        "n_months": len(months or []),
        "sections": sections,
        "depth_distribution": depth,
        "chosen_axes": chosen_axes,
        "folded": folded,
        "total_ceiling": sum(s["ceiling"] for s in sections),
        "params": {"MIN_MECH": MIN_MECH, "MAX_MECH": MAX_MECH,
                   "MIN_DEPTH": MIN_DEPTH, "BODY_WORDS": BODY_WORDS,
                   "WORDS_PER_CITE": WORDS_PER_CITE,
                   "CITE_CLAMP": list(CITE_CLAMP)},
    }

    cite_sum = sum(s["cite_target"] for s in sections)
    lo, hi = CITE_SUM_BAND
    if not (lo <= cite_sum <= hi):
        raise SystemExit(
            f"FAIL-CLOSED H1 section map: per-section citation minimums sum "
            f"to {cite_sum}, outside {CITE_SUM_BAND}. They must leave room "
            f"under the issue-level ceiling. Retune WORDS_PER_CITE / "
            f"CITE_CLAMP, never the gate.")
    m["cite_target_sum"] = cite_sum

    if sections[-1]["role"] != "gaps":
        raise SystemExit("FAIL-CLOSED: gaps must be the final section")

    m["sha256"] = hashlib.sha256(
        json.dumps(m["sections"], sort_keys=True).encode()).hexdigest()[:16]
    return m


def gaps_id(m: dict) -> str:
    for s in m["sections"]:
        if s["role"] == "gaps":
            return s["id"]
    raise SystemExit("FAIL-CLOSED: H1 section map has no gaps section")


def main() -> int:
    from stages.h1_aggregate import EDITION, aggregate, axis_mass, edition_dir
    agg = aggregate()
    m = build_map(EDITION, axis_mass(agg), months=agg["months"])
    d = edition_dir()
    (d / "12_section_map.json").write_text(json.dumps(m, indent=2),
                                           encoding="utf-8")
    print(f"[h1-map] {len(m['sections'])} sections, sha={m['sha256']}, "
          f"total_ceiling={m['total_ceiling']}, cite_sum={m['cite_target_sum']}")
    for s in m["sections"]:
        print(f"  {s['id']:>2}  {s['role']:<10} {s['ceiling']:>5}w "
              f"cite>={s['cite_target']:<3} {s['title']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
