"""v2 section map: the main text organised by DEVICE FAMILY.

Havid's structure (2026-09-09): four device-family sections instead of six
mechanism-axis sections.

    Single junction | All-perovskite tandem | Perovskite/silicon and other
    hybrid tandems | Module

v1 (`h1_section_map.py`) is untouched and still produces the mechanism map, so
the shipped v1 artifact stays reproducible.

The allocation problem, and why proportional is WRONG here
----------------------------------------------------------
Measured family mass (872 cards, folded):

    sj 692 (79%) | hyb 77 (9%) | ap 60 (7%) | mod 43 (5%)

The v1 map allocates ceilings proportionally to evidence mass. Applied to these
counts that gives single junction ~5700 of 7200 body words and modules ~355 --
arithmetically faithful, editorially indefensible. A device family earns a
section because it poses a distinct device-physics question, not because many
groups publish on it. The module section carries the area penalty, which is the
single most consequential open problem in the field, on 5% of the papers.

So v2 allocates from a DECLARED editorial weight, damped toward mass:

    ceiling_f = BODY_WORDS * (W_DECLARED[f] * (1 - DAMP) + share_f * DAMP)

DAMP = 0.30 lets a genuinely thin family shrink a little without letting the
biggest family eat the issue. Both bounds are still enforced, and the declared
weights are visible, arguable and recorded in the map JSON -- unlike a
proportional rule whose output looks objective while encoding a judgement
nobody made.

Mechanism is NOT abandoned
--------------------------
Each family section is told which mechanism axes dominate ITS OWN papers, so
buried-interface chemistry still gets written about -- inside the family where
it matters, rather than as a section competing with device physics. The
cross-cutting synthesis then reads all four and says what they share.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from stages.device_family import FAMILIES, LABEL  # noqa: E402

# ---- knobs ----
BODY_WORDS = 7200          # Havid's 3x spec, same as v1
FAM_MIN_WORDS = 900        # a family section must be able to make an argument
FAM_MAX_WORDS = 2100       # and must not eat the issue
DAMP = 0.30                # how much measured mass moves the declared weight

# Declared editorial weight per family. Sums to 1.0, asserted below.
#
# sj leads because it is where the physics is contested and where 79% of the
# literature lives. hyb is second: it holds the certified record and the
# tandem-specific problems (current matching, interconnection). ap and mod are
# equal thirds -- ap because the Sn-Pb stability problem is unsolved, mod
# because the area penalty is the field's translation bottleneck.
W_DECLARED = {"sj": 0.34, "hyb": 0.24, "ap": 0.21, "mod": 0.21}

SPINE_WORDS = {
    "intro": 700,
    "frontier": 900,     # the cross-family certified frontier + trajectory
    "synthesis": 900,    # what the four families say together
    "audit": 700,        # reporting practice, cut by family
    "gaps": 900,         # always last
}

WORDS_PER_CITE = 45
CITE_CLAMP = (8, 34)
CITE_SUM_BAND = (140, 210)   # headroom under citations_h1 [150, 250]

TITLE_BANK = {
    "sj": ["Single-Junction Cells: Where the Voltage Deficit Now Sits",
           "The Single-Junction Frontier and Its Remaining Losses"],
    "ap": ["All-Perovskite Tandems and the Tin-Lead Problem",
           "All-Perovskite Tandems: Narrow-Bandgap Stability as the Limit"],
    "hyb": ["Perovskite/Silicon and Other Hybrid Tandems",
            "Hybrid Tandems: Silicon, CIGS and Organic Partners"],
    "mod": ["From Cell to Module: The Area Penalty",
            "Modules and the Cost of Area"],
}
FRONTIER_BANK = [
    "The Certified Frontier Across January-June 2026",
    "What January-June 2026 Verified, by Device Family",
]
SYNTHESIS_BANK = [
    "Cross-Cutting Synthesis: What the Device Families Share",
    "Reading the Device Families Together",
]
AUDIT_BANK = [
    "Reporting Practice Across Device Families",
    "How Each Device Family Reports Itself",
]

ROT = 2026 * 2 + 1     # deterministic for 2026-H1


def build_map(stats: dict, period_label: str = "January-June 2026") -> dict:
    """Compute the v2 map from measured family mass + declared weights."""
    assert abs(sum(W_DECLARED.values()) - 1.0) < 1e-9, (
        f"W_DECLARED must sum to 1.0, got {sum(W_DECLARED.values())}")

    mass = {f: int(stats.get(f"family.{f}.n_cards") or 0) for f in FAMILIES}
    total_mass = sum(mass.values())
    if not total_mass:
        raise SystemExit("FAIL-CLOSED: no family mass; run h1_family_stats first")
    # 7.1: a family with no papers cannot carry a section.
    empty = [f for f, n in mass.items() if n == 0]
    if empty:
        raise SystemExit(f"FAIL-CLOSED: families with zero cards: {empty}")

    share = {f: mass[f] / total_mass for f in FAMILIES}
    weight = {f: W_DECLARED[f] * (1 - DAMP) + share[f] * DAMP for f in FAMILIES}
    wsum = sum(weight.values())
    ceilings = {}
    for f in FAMILIES:
        raw = BODY_WORDS * weight[f] / wsum
        ceilings[f] = int(min(FAM_MAX_WORDS,
                              max(FAM_MIN_WORDS, round(raw / 10) * 10)))

    sections: list[dict] = []
    n = 0

    def add(role, title, ceiling, cite, family=None, extra=None):
        nonlocal n
        n += 1
        s = {"id": str(n), "role": role, "family": family, "title": title,
             "ceiling": ceiling, "cite_target": cite}
        if extra:
            s.update(extra)
        sections.append(s)

    add("intro", "Introduction", SPINE_WORDS["intro"], 0)
    add("frontier", FRONTIER_BANK[ROT % len(FRONTIER_BANK)],
        SPINE_WORDS["frontier"], 18)

    # Family sections in DECLARED order, not mass order: the issue reads
    # cell -> tandem -> tandem -> module, which is the physical progression a
    # reader expects. Mass order would put modules last by accident and
    # single junction first for the wrong reason.
    for f in ("sj", "ap", "hyb", "mod"):
        bank = TITLE_BANK[f]
        ceil = ceilings[f]
        add("family", bank[ROT % len(bank)], ceil,
            max(CITE_CLAMP[0], min(CITE_CLAMP[1], round(ceil / WORDS_PER_CITE))),
            family=f,
            extra={"n_cards": mass[f], "label": LABEL[f],
                   "share_pct": round(100 * share[f], 1),
                   "declared_weight": W_DECLARED[f]})

    add("synthesis", SYNTHESIS_BANK[ROT % len(SYNTHESIS_BANK)],
        SPINE_WORDS["synthesis"], 10)
    add("audit", AUDIT_BANK[ROT % len(AUDIT_BANK)], SPINE_WORDS["audit"], 7)
    add("gaps", "Research Gaps and Outlook", SPINE_WORDS["gaps"], 9)

    m = {
        "edition": "2026-H1",
        "version": "v6",
        "structure": "device_family",
        "period_label": period_label,
        "month_name": period_label,     # s18d/derive_title read this key
        "months": stats.get("months", []),
        "n_months": stats.get("n_months"),
        "sections": sections,
        "family_mass": mass,
        "family_share_pct": {f: round(100 * share[f], 1) for f in FAMILIES},
        "declared_weights": W_DECLARED,
        "damp": DAMP,
        "total_ceiling": sum(s["ceiling"] for s in sections),
        "params": {"BODY_WORDS": BODY_WORDS, "FAM_MIN_WORDS": FAM_MIN_WORDS,
                   "FAM_MAX_WORDS": FAM_MAX_WORDS,
                   "WORDS_PER_CITE": WORDS_PER_CITE,
                   "CITE_CLAMP": list(CITE_CLAMP)},
    }

    cite_sum = sum(s["cite_target"] for s in sections)
    lo, hi = CITE_SUM_BAND
    if not (lo <= cite_sum <= hi):
        raise SystemExit(
            f"FAIL-CLOSED v2 map: per-section citation minimums sum to "
            f"{cite_sum}, outside {CITE_SUM_BAND}. A writer meeting every "
            f"minimum must not overshoot the issue ceiling. Retune "
            f"WORDS_PER_CITE / CITE_CLAMP, never the gate (handbook 6.5).")
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
    raise SystemExit("FAIL-CLOSED: v2 map has no gaps section")


def main() -> int:
    from stages.util import RUNS
    d = RUNS / "2026-H1"
    S = json.loads((d / "stats.json").read_text(encoding="utf-8"))
    m = build_map(S)
    (d / "12_section_map_v6.json").write_text(json.dumps(m, indent=2),
                                              encoding="utf-8")
    print(f"[h1v6-map] {len(m['sections'])} sections  sha={m['sha256']}  "
          f"ceiling={m['total_ceiling']}  cite_sum={m['cite_target_sum']}")
    for s in m["sections"]:
        fam = f"[{s['family']}]" if s.get("family") else ""
        print(f"  {s['id']:>2}  {s['role']:<10} {s['ceiling']:>5}w "
              f"cite>={s['cite_target']:<3} {fam:<6} {s['title']}")
    print(f"[h1v6-map] mass={m['family_mass']}  share={m['family_share_pct']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
