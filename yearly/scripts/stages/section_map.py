"""Shared section map: the ONE place that decides what sections an issue has.

Why this file exists
--------------------
v3 hardcoded the same eight sections in four places (s13c SEC, s18c SEC, the
s19 SI title, the F1 caption). That guaranteed two problems:

1. Drift. The month literal "July 2026" lived in all four and was fixed in
   three of them before the August build; the fourth (figure caption) shipped
   into the PDF and was only caught by reading the rendered page.
2. A section map that ignored the month. August's depth tier was
   defects 42, interfaces 32, composition 25, architecture 17, stability 16,
   scale_up 12 -- composition was the third largest body of evidence and had
   no section of its own, while scale_up was the thinnest and got a full one.

So the map is computed once, from that month's own evidence, written to
runs/<m>/12_section_map.json, and every downstream stage READS it. No stage
may hardcode a section title, ceiling, or citation target again.

Design rules
------------
- SPINE is fixed: Introduction, Certified Frontier, Research Gaps and Outlook.
  Those three carry the issue's identity and always appear, in that order,
  with Research Gaps last.
- Mechanism sections are selected by depth-tier evidence mass, between
  MIN_MECH and MAX_MECH of them, and only if an axis clears MIN_DEPTH papers.
  An axis with too little evidence does not get a section; its papers still
  reach the reader through the axis it is folded into.
- Word ceilings and citation targets are ALLOCATED PROPORTIONALLY to evidence
  mass, not typed in. A month where composition dominates gets a long
  composition section automatically.
- Titles come from a per-axis bank so consecutive issues do not reuse one
  phrasing. Selection is seeded by month, so it is deterministic and
  reproducible, not random per run.

Fingerprinting
--------------
The map carries a sha256. s13d records it next to every drafted section and
refuses to reuse prose drafted under a different map, which is the failure
mode that would otherwise ship last month's section titles over this month's
text.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from stages.util import run_dir  # noqa: E402

# Selection knobs. Deliberately few and all explicit.
MIN_MECH = 4          # never fewer than 4 mechanism sections
MAX_MECH = 5          # never more than 5, or the issue loses its shape
MIN_DEPTH = 10        # an axis needs this many depth papers to earn a section
BODY_WORDS = 2400     # total words to distribute across mechanism sections
MECH_MIN_WORDS = 320  # floor so a thin section is still a section
MECH_MAX_WORDS = 620  # ceiling so one axis cannot eat the issue
# Citation target = ceiling / WORDS_PER_CITE, clamped by CITE_CLAMP.
#
# Was 34, which is wrong at the ISSUE level even though it looks right per
# section: the per-section minimums summed to 78 against a G2c band whose top
# is 85. A writer that merely MEETS every minimum lands 7 citations below the
# ceiling, so the August v4 build hit 87 and failed G2c while every individual
# section had done exactly what it was told.
#
# The gate band is the agreed contract, so the GENERATOR moves, not the gate.
# At 42 the minimums sum to ~63, leaving real headroom inside [60,85] for a
# writer that cites generously, which the rules explicitly ask it to do.
WORDS_PER_CITE = 42
CITE_CLAMP = (5, 15)
# Sanity band for the sum of per-section minimums. Asserted in build_map so a
# future tuning change cannot silently recreate the same inconsistency.
CITE_SUM_BAND = (55, 72)

# Spine ceilings. These three are fixed because their job does not change
# with the month: frame it, state what was verified, say what is missing.
SPINE_WORDS = {"intro": 300, "frontier": 290, "gaps": 400}

# Per-axis title bank. Rotated by month so successive issues differ in
# phrasing even when the same axis leads two months running. Every phrase
# must be a plain description of the physics, never a claim.
TITLE_BANK = {
    "interfaces": [
        "Buried Interfaces and Contact Chemistry",
        "Contact Chemistry at the Buried Interface",
        "Interfacial Energetics and Contact Design",
        "Self-Assembled Contacts and Interfacial Dipoles",
    ],
    "defects": [
        "Defect Tolerance, Passivation and Ion Migration",
        "Trap States, Passivation and Ionic Motion",
        "Non-Radiative Recombination and Defect Control",
        "Passivation Chemistry and Ion Migration Under Bias",
    ],
    "composition": [
        "Composition, Phase Control and Crystallisation",
        "A-Site and Halide Composition Engineering",
        "Crystallisation Pathways and Phase Stability",
        "Precursor Chemistry and Phase Purity",
    ],
    "architecture": [
        "Wide-Bandgap Absorbers and Tandem Integration",
        "Tandem Architecture and Current Matching",
        "Subcell Design and Tandem Interconnection",
        "Wide-Bandgap Subcells and Recombination Layers",
    ],
    "stability": [
        "Operational Stability and Degradation Pathways",
        "Degradation Mechanisms Under Operation",
        "Operational Lifetime and Failure Pathways",
        "Stability Under Load, Heat and Illumination",
    ],
    "scale_up": [
        "Scale-Up and the Area Penalty",
        "Large-Area Coating and the Area Penalty",
        "From Cell to Module: Coating and Uniformity",
        "Module Fabrication and Area-Dependent Losses",
    ],
}

# Axes that may be folded into another section when they miss the cut, so
# their evidence still reaches the writer instead of being dropped.
FOLD_INTO = {
    "composition": "defects",
    "scale_up": "architecture",
    "stability": "defects",
    "architecture": "interfaces",
    "defects": "interfaces",
    "interfaces": "defects",
}


def month_name(month: str) -> str:
    """'2026-08' -> 'August 2026'."""
    y, m = month.split("-")
    return f"{datetime.date(int(y), int(m), 1):%B} {y}"


def _month_index(month: str) -> int:
    """Stable integer for title rotation. Deterministic across reruns."""
    y, m = month.split("-")
    return int(y) * 12 + int(m)


def build_map(month: str, stats: dict) -> dict:
    """Compute this issue's section map from its own depth-tier evidence."""
    mon = month_name(month)

    depth = {}
    for axis in TITLE_BANK:
        k = f"axes.{axis}.n_depth"
        if k in stats and stats[k]:
            depth[axis] = int(stats[k])
    if not depth:
        raise SystemExit("FAIL-CLOSED: no axes.*.n_depth in stats; cannot "
                         "build a section map without evidence mass")

    ranked = sorted(depth.items(), key=lambda kv: (-kv[1], kv[0]))
    eligible = [(a, n) for a, n in ranked if n >= MIN_DEPTH]

    # Take the top MAX_MECH eligible axes; if too few clear MIN_DEPTH, back
    # off to the ranking so the issue always has at least MIN_MECH sections.
    chosen = eligible[:MAX_MECH]
    if len(chosen) < MIN_MECH:
        chosen = ranked[:MIN_MECH]
    chosen_axes = [a for a, _ in chosen]

    # Everything not given its own section is folded into one that exists, so
    # no depth-tier paper becomes invisible to the writer.
    folded: dict[str, list[str]] = {a: [a] for a in chosen_axes}
    for axis in depth:
        if axis in chosen_axes:
            continue
        target = FOLD_INTO.get(axis)
        while target and target not in chosen_axes:
            target = FOLD_INTO.get(target)
        folded[target or chosen_axes[0]].append(axis)

    # Proportional word allocation over the CHOSEN axes' own depth counts.
    total = sum(depth[a] for a in chosen_axes) or 1
    raw = {a: BODY_WORDS * depth[a] / total for a in chosen_axes}
    ceilings = {a: int(min(MECH_MAX_WORDS, max(MECH_MIN_WORDS, round(raw[a] / 10) * 10)))
                for a in chosen_axes}

    rot = _month_index(month)
    sections, n = [], 0

    n += 1
    sections.append({
        "id": str(n), "role": "intro", "axis": None, "axes": [],
        "title": "Introduction",
        "ceiling": SPINE_WORDS["intro"], "cite_target": 0})

    n += 1
    sections.append({
        "id": str(n), "role": "frontier", "axis": None, "axes": [],
        "title": f"The Certified Frontier in {mon}",
        "ceiling": SPINE_WORDS["frontier"], "cite_target": 8})

    for axis in chosen_axes:
        n += 1
        bank = TITLE_BANK[axis]
        ceil = ceilings[axis]
        sections.append({
            "id": str(n), "role": "mechanism", "axis": axis,
            "axes": folded[axis],
            "title": bank[rot % len(bank)],
            "ceiling": ceil,
            "cite_target": max(CITE_CLAMP[0], min(CITE_CLAMP[1],
                                                  round(ceil / WORDS_PER_CITE))),
            "n_depth": depth[axis]})

    n += 1
    sections.append({
        "id": str(n), "role": "gaps", "axis": None, "axes": [],
        "title": "Research Gaps and Outlook",
        "ceiling": SPINE_WORDS["gaps"], "cite_target": 4})

    m = {
        "month": month,
        "month_name": mon,
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
    # The per-section minimums must leave headroom inside the issue-level G2c
    # band, or a writer that obeys every section fails the manuscript. The v4
    # August build hit exactly that: minimums summed to 78 against a [60,85]
    # band, the writer cited 87, and G2c failed while every section had done
    # what it was told. Assert the invariant here so tuning cannot silently
    # recreate it.
    cite_sum = sum(s["cite_target"] for s in sections)
    lo, hi = CITE_SUM_BAND
    if not (lo <= cite_sum <= hi):
        raise SystemExit(
            f"FAIL-CLOSED section map: per-section citation minimums sum to "
            f"{cite_sum}, outside {CITE_SUM_BAND}. They must leave room under "
            f"the issue-level G2c ceiling. Retune WORDS_PER_CITE/CITE_CLAMP, "
            f"never the gate.")
    m["cite_target_sum"] = cite_sum
    m["sha256"] = hashlib.sha256(
        json.dumps(m["sections"], sort_keys=True).encode()).hexdigest()[:16]
    return m


def write_map(month: str, stats: dict) -> dict:
    rd = run_dir(month)
    m = build_map(month, stats)
    (rd / "12_section_map.json").write_text(json.dumps(m, indent=2),
                                            encoding="utf-8")
    return m


def load_map(month: str) -> dict:
    rd = run_dir(month)
    f = rd / "12_section_map.json"
    if not f.exists():
        raise SystemExit(f"FAIL-CLOSED: {f} missing; run s13d first")
    return json.loads(f.read_text(encoding="utf-8"))


def gaps_id(m: dict) -> str:
    for s in m["sections"]:
        if s["role"] == "gaps":
            return s["id"]
    raise SystemExit("FAIL-CLOSED: section map has no gaps section")


if __name__ == "__main__":
    mo = sys.argv[1] if len(sys.argv) > 1 else "2026-08"
    st = json.loads((run_dir(mo) / "stats.json").read_text(encoding="utf-8"))
    mp = build_map(mo, st)
    print(json.dumps({k: v for k, v in mp.items() if k != "folded"}, indent=2))
    print("\nfolded:", json.dumps(mp["folded"]))
