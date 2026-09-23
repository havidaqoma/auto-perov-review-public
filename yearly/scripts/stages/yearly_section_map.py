"""Yearly section map: what sections a YEARLY issue has, computed from a year.

Relationship to section_map.py
------------------------------
Same contract, different shape. The monthly map is not reused because a
yearly issue has two jobs a monthly issue does not:

- a TRAJECTORY (what changed across the twelve months), which no monthly
  issue can carry because it only ever sees one month
- a SYNTHESIS across axes (what the year's separate mechanism literatures,
  read together, now say), which is the reason to write a yearly review at
  all rather than stapling twelve monthlies together

So the spine gains two roles, `trajectory` and `synthesis`, and the mechanism
band widens from 4-5 to 5-6 because annual mass supports it.

What is deliberately IDENTICAL to monthly
-----------------------------------------
- titles from a bank, rotated deterministically, so reruns are reproducible
- ceilings allocated proportionally to evidence mass, never typed in
- cite_target = ceiling / WORDS_PER_CITE, clamped
- CITE_SUM_BAND asserted, so a writer obeying every section minimum cannot
  fail the issue-level ceiling (handbook 6.5 -- the generator moves, never
  the gate)
- a sha256 over the sections, so cached prose drafted under a different map
  is deleted rather than reused
- axes that miss the cut are FOLDED, never dropped

Why MAX_MECH is 6 and not 12
-----------------------------
There are exactly six mechanism axes in config/axes.yaml. A yearly issue can
afford to give every axis its own section, which is the honest thing to do
when annual mass clears the floor for all six. It cannot afford one section
per month: that is twelve narrations of the same physics, which is precisely
the repetition Havid found in the August monthly issue (handbook 4.1b).
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from stages.section_map import TITLE_BANK, FOLD_INTO  # noqa: E402

# ---- knobs. Scaled from the monthly values, each with its reason. ----
MIN_MECH = 5           # monthly 4; annual mass supports one more
MAX_MECH = 6           # there are only six axes; a yearly issue may use all
MIN_DEPTH = 25         # monthly 10; scaled to annual mass (config/yearly.yaml)
BODY_WORDS = 7000      # monthly 2400; 2.9x, inside Havid's 2-3x ask
MECH_MIN_WORDS = 700   # floor keeps a thin section real
MECH_MAX_WORDS = 1500  # ceiling stops one axis eating the year

# Monthly uses 42. This was FIRST SET TO 40, and the CITE_SUM_BAND assertion
# below rejected the resulting map: over the real annual mass of the three
# shipped 2026 issues the minimums summed to 214 against a band top of 200,
# which is exactly the August v4 failure of handbook 6.5 reproduced at annual
# scale -- a writer meeting every section minimum would overshoot the
# issue-level ceiling and G2c would fail while every section obeyed.
#
# Fixed by moving the GENERATOR, never the gate: 40 -> 45, and the spine cite
# targets trimmed (22/12/8/10 -> 18/10/7/9). Measured result on the same mass:
# mechanism 151 + spine 44 = 195, inside (150, 200), leaving 25 citations of
# headroom under the citations_yearly ceiling of 220.
WORDS_PER_CITE = 45
CITE_CLAMP = (8, 34)
# Asserted in build_map. Must leave headroom under citations_yearly.total_band
# [160, 220], or a writer that merely meets every section minimum overshoots
# the issue ceiling and G2c fails while every section obeyed its instructions.
CITE_SUM_BAND = (150, 200)

# Spine ceilings. Fixed because their job does not change with the year.
SPINE_WORDS = {
    "intro": 700,
    "trajectory": 900,   # the month-by-month frontier, unique to yearly
    "synthesis": 900,    # what the axes say when read together
    "audit": 700,        # twelve months of reporting practice
    "gaps": 900,         # always last
}

# Rotated by YEAR, not month, so consecutive yearly issues differ in phrasing.
TRAJECTORY_BANK = [
    "The Certified Frontier Across {year}",
    "What {year} Verified: The Frontier Month by Month",
    "The {year} Certified Record and Its Trajectory",
]
SYNTHESIS_BANK = [
    "Cross-Cutting Synthesis: What the Mechanisms Say Together",
    "Reading the Mechanisms Together",
    "Convergent Evidence Across Mechanism Axes",
]
AUDIT_BANK = [
    "Reporting Practice Over Twelve Months",
    "Twelve Months of Reporting and Characterisation Practice",
    "How the Field Reported Itself in {year}",
]


def _year_index(year: str) -> int:
    return int(year)


def build_map(year: str, axis_mass: dict[str, int],
              n_months: int = 12) -> dict:
    """Compute a yearly issue's section map from its own annual evidence mass.

    `axis_mass` is the annual depth-tier count per axis, as produced by
    yearly_aggregate.axis_mass(). It is passed in rather than read from disk
    so this function stays pure and testable.
    """
    depth = {a: int(n) for a, n in axis_mass.items() if a in TITLE_BANK and n}
    if not depth:
        raise SystemExit(
            "FAIL-CLOSED: no per-axis annual mass; cannot build a yearly "
            "section map without evidence mass")

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

    rot = _year_index(year)
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
        TRAJECTORY_BANK[rot % len(TRAJECTORY_BANK)].format(year=year),
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
    add("audit", AUDIT_BANK[rot % len(AUDIT_BANK)].format(year=year),
        SPINE_WORDS["audit"], 7)
    add("gaps", "Research Gaps and Outlook", SPINE_WORDS["gaps"], 9)

    m = {
        "year": year,
        "n_months": n_months,
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
            f"FAIL-CLOSED yearly section map: per-section citation minimums "
            f"sum to {cite_sum}, outside {CITE_SUM_BAND}. They must leave "
            f"room under the issue-level ceiling. Retune WORDS_PER_CITE / "
            f"CITE_CLAMP, never the gate.")
    m["cite_target_sum"] = cite_sum

    # Gaps must be last, as in monthly. Asserted rather than assumed: the
    # role order above is easy to edit and hard to eyeball.
    if sections[-1]["role"] != "gaps":
        raise SystemExit("FAIL-CLOSED: gaps must be the final section")

    m["sha256"] = hashlib.sha256(
        json.dumps(m["sections"], sort_keys=True).encode()).hexdigest()[:16]
    return m


def gaps_id(m: dict) -> str:
    for s in m["sections"]:
        if s["role"] == "gaps":
            return s["id"]
    raise SystemExit("FAIL-CLOSED: yearly section map has no gaps section")


if __name__ == "__main__":
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from stages.yearly_corpus import aggregate, axis_mass, yearly_dir

    if len(sys.argv) < 2:
        raise SystemExit("usage: yearly_section_map.py <YYYY> [--partial]  "
                         "No default: the period must be stated.")
    yr = sys.argv[1]
    partial = "--partial" in sys.argv
    agg = aggregate(yr, require_full_year=not partial)
    mp = build_map(yr, axis_mass(agg), n_months=agg["n_months"])

    # PERSIST IT. The draft stage regenerates the map (same inputs, same
    # sha256, because the map is deterministic) but the BUILD stage only
    # reads this file. Printing to stdout leaves the build with nothing to
    # open, and a build that cannot find its map cannot check that every
    # mapped section is present in the manuscript.
    out = yearly_dir(yr) / "yearly_section_map.json"
    out.write_text(json.dumps(mp, indent=2), encoding="utf-8")
    print(f"[map] sha {mp['sha256']}  cite_sum {mp['cite_target_sum']}  "
          f"ceiling {mp['total_ceiling']} -> {out}")
    for s in mp["sections"]:
        print(f"  {s['id']:>2} {s['role']:<11} ceil={s['ceiling']:<5} "
              f"cite={s['cite_target']:<3} {s['title'][:54]}")
