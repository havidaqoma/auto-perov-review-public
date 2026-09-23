"""yearly_device_map: an 11-section map with a DEVICE-CLASS body spine.

WHY THIS REPLACES THE MECHANISM SPINE
-------------------------------------
`yearly_section_map.py` builds the body from mechanism axes (defects,
interfaces, composition...). That is the right spine for a monthly issue,
where one month rarely holds enough of any device class to argue about.

Over a year it is the wrong spine, and the reason is a reader's question. Ask
"what happened in tandems in 2025" and a mechanism-organised review cannot
answer: every section mixes single cells, stacks and modules, so the tandem
evidence is scattered across six places and compared against the wrong
physical bound in each. Havid asked for a device spine (2026-09-10) and the
measured mass supports it.

THE FOUR SECTIONS, AND WHY NOT FIVE
-----------------------------------
Measured on the 2025 corpus, all 450 cards:

    single_junction       332
    hybrid_tandem          47   (perovskite/Si, /CIGS, /organic)
    module                 43
    all_perovskite_tandem  28

Havid's original request listed perovskite/silicon and "other" (CIGS, OPV) as
one topic, and that is what the evidence supports: only 17 cards are
explicitly Si-partnered and 10 name CIGS or organic. Split into two sections
they would sit at 17 and 10, far below the 25-card floor, and each would make
a thin claim. Merged they are a solid 47.

SECTION MASS COUNTS ALL CARDS, NOT MEASURED-ONLY
------------------------------------------------
`all_perovskite_tandem` has 28 cards but only 24 with `lens == experimental`.
The lens filter exists to keep simulation off MEASURED FIGURES (a computed
efficiency must never sit beside certified hardware). It is not a membership
rule: a drift-diffusion study of an all-perovskite stack is legitimately
DISCUSSED in the all-perovskite section, it simply cannot have its computed
value plotted on a measured frontier.

So section mass counts every card and the figures stay filtered. Conflating
the two would drop a real section below its floor for the wrong reason.

THE CITATION-FLOOR COLLISION, AND WHICH SIDE MOVED
--------------------------------------------------
Four body sections produce fewer per-section citation minimums than six.
With the mechanism spine's knobs (`MECH_MAX_WORDS` 1500, `WORDS_PER_CITE` 45)
the sum came to roughly 132, BELOW G2c's floor of 160. A writer meeting every
section minimum would have produced an issue that failed the gate.

This is the generator/gate invariant firing for the third time in this
project, and as always the GENERATOR moved: `DEVICE_MAX_WORDS` rises to 2200
because a yearly device-class section genuinely carries more than a monthly
mechanism section. The G2c band was not touched.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from stages.device_class import (CLASS_LABEL, CLASS_ORDER,  # noqa: E402
                                 CLASS_PCE_LIMIT, class_mass)

# ------------------------------------------------------------------ knobs
DEVICE_MIN_WORDS = 900       # a device section below this cannot argue
DEVICE_MAX_WORDS = 2200      # see the docstring: raised from 1500
WORDS_PER_CITE = 45          # unchanged from the mechanism map
CITE_CLAMP = (10, 50)
# Ceiling on cite_target as a share of the class's own card pool. See the
# comment at the call site: a section asked for 30 citations from 28 papers
# failed closed three times on the 2025 draft. 0.60 leaves the writer room
# to SELECT rather than transcribe the whole class.
POOL_CITE_FRACTION = 0.60
CITE_SUM_BAND = (150, 210)   # must leave headroom under G2c's 220 ceiling
MIN_CLASS_CARDS = 25         # below this a class is folded, never shipped thin

SPINE_WORDS = {"intro": 700, "trajectory": 900, "synthesis": 900,
               "audit": 700, "gaps": 900}
SPINE_CITES = {"intro": 0, "trajectory": 18, "synthesis": 10,
               "audit": 7, "gaps": 9}

# Rotated by YEAR so consecutive issues differ in phrasing with no per-run
# randomness. Never dictate a sentence to the writer; these are TITLES, which
# the build renders, not prose the model is asked to echo.
TRAJECTORY_TITLES = [
    "The Certified Frontier Across {year}",
    "What {year} Verified: The Frontier Month by Month",
    "Twelve Months of Certified Performance in {year}",
]
SYNTHESIS_TITLES = [
    "Reading the Device Classes Together",
    "Cross-Cutting Synthesis: What the Architectures Share",
    "Common Mechanisms Across Device Classes",
]
AUDIT_TITLES = [
    "Reporting Practice Across {year}",
    "How Completely {year} Reported Its Own Measurements",
    "Twelve Months of Reporting and Characterisation Practice",
]

DEVICE_TITLES = {
    "single_junction": [
        "Single-Junction Cells: Passivation, Contacts and the "
        "Shockley-Queisser Ceiling",
        "Single-Junction Devices: Where the Remaining Losses Sit",
    ],
    "all_perovskite_tandem": [
        "All-Perovskite Tandems: Narrow-Gap Absorbers and Recombination "
        "Layers",
        "All-Perovskite Tandems: Sn-Pb Stability and Subcell Matching",
    ],
    "hybrid_tandem": [
        "Perovskite/Silicon and Other Hybrid Tandems: Texture, Current "
        "Matching and Interconnection",
        "Hybrid Tandems: Coupling Perovskite to Silicon, CIGS and Organic "
        "Subcells",
    ],
    "module": [
        "From Cell to Module: Coating Uniformity and the Area Penalty",
        "Modules and Large-Area Devices: Scaling the Deposited Film",
    ],
}


def _allocate(mass: dict[str, int], budget: int) -> dict[str, int]:
    """Word ceilings proportional to card mass, clamped, then rebalanced.

    Single junction carries roughly three quarters of the corpus. Pure
    proportional allocation would hand it the entire budget and starve the
    other three, so every section is clamped to [MIN, MAX] and the remainder
    is redistributed to whichever sections still have headroom.
    """
    live = {k: v for k, v in mass.items() if v > 0}
    total = sum(live.values()) or 1
    raw = {k: budget * v / total for k, v in live.items()}
    out = {k: int(max(DEVICE_MIN_WORDS, min(DEVICE_MAX_WORDS, r)))
           for k, r in raw.items()}

    # Rebalance in fixed key order so the result is deterministic: the same
    # mass must always produce the same map, or a resume redrafts forever.
    slack = budget - sum(out.values())
    for _ in range(4):
        if abs(slack) < 25:
            break
        room = [k for k in CLASS_ORDER if k in out
                and (out[k] < DEVICE_MAX_WORDS if slack > 0
                     else out[k] > DEVICE_MIN_WORDS)]
        if not room:
            break
        step = slack // len(room)
        if step == 0:
            break
        for k in room:
            out[k] = int(max(DEVICE_MIN_WORDS,
                             min(DEVICE_MAX_WORDS, out[k] + step)))
        slack = budget - sum(out.values())
    return {k: int(round(v / 10) * 10) for k, v in out.items()}


def build_map(year: str, cards: list, abstracts: dict | None = None,
              n_months: int = 12) -> dict:
    """The full 11-section map. Nothing is typed in.

    Titles, ceilings and citation targets all fall out of the measured card
    mass per device class.
    """
    mass = class_mass(cards, abstracts or {})
    rot = int(year)

    # A class below the floor is FOLDED into the nearest larger class rather
    # than shipped as a thin section. Folding keeps its papers reachable by
    # the writer; dropping would delete evidence.
    folded: dict[str, str] = {}
    live = dict(mass)
    for k in CLASS_ORDER:
        if 0 < live.get(k, 0) < MIN_CLASS_CARDS:
            target = ("hybrid_tandem" if k == "all_perovskite_tandem"
                      else "single_junction")
            if live.get(target, 0) >= MIN_CLASS_CARDS:
                folded[k] = target
                live[target] += live[k]
                live[k] = 0

    body_budget = 6200          # device sections only; spine is fixed
    ceilings = _allocate({k: v for k, v in live.items() if v > 0},
                         body_budget)

    sections: list[dict] = []
    sid = 0

    def add(role: str, title: str, ceiling: int, cite: int,
            device: str | None = None, n: int = 0) -> None:
        nonlocal sid
        sid += 1
        s = {"id": str(sid), "role": role, "title": title,
             "ceiling": int(ceiling), "cite_target": int(cite),
             "n_depth": int(n)}
        if device:
            s["device_class"] = device
            s["pce_limit_pct"] = CLASS_PCE_LIMIT[device]
            s["folded_in"] = [k for k, v in folded.items() if v == device]
        # `axis`/`axes` are kept for contract compatibility with the build
        # and figure stages, which key attachment on them.
        s["axis"] = device or role
        s["axes"] = [device] if device else [role]
        sections.append(s)

    add("intro", "Introduction", SPINE_WORDS["intro"], SPINE_CITES["intro"])
    add("trajectory",
        TRAJECTORY_TITLES[rot % len(TRAJECTORY_TITLES)].format(year=year),
        SPINE_WORDS["trajectory"], SPINE_CITES["trajectory"])

    for k in CLASS_ORDER:
        if live.get(k, 0) <= 0:
            continue
        ceil = ceilings[k]
        cite = max(CITE_CLAMP[0], min(CITE_CLAMP[1], round(ceil / WORDS_PER_CITE)))
        # A SECTION CANNOT CITE MORE PAPERS THAN ITS CLASS CONTAINS.
        #
        # Measured failure, 2025 first device-spine draft: all-perovskite
        # tandems hold 28 cards and the map asked for 30 distinct citations.
        # The writer reached 28, was rejected three times, and the stage
        # failed closed after burning three full LLM calls on a section no
        # model could have passed.
        #
        # The bug is that cite_target was derived from the WORD CEILING
        # alone (ceiling / WORDS_PER_CITE) and never consulted the pool.
        # Word budget and evidence supply are independent quantities, and a
        # thin class gets a generous ceiling precisely because the floor
        # protects it -- which is exactly when the two diverge.
        #
        # POOL_CITE_FRACTION caps the target at a share of the class. It is
        # below 1.0 on purpose: the evidence block is "a pool to select
        # from, not a checklist" (RULES), so demanding every paper in a
        # class would force the writer to cite work that does not bear on
        # the problems it chose to develop -- padding, dressed as rigour.
        cite = min(cite, int(live[k] * POOL_CITE_FRACTION))
        cite = max(CITE_CLAMP[0], cite)
        bank = DEVICE_TITLES[k]
        add("device", bank[rot % len(bank)], ceil, cite, device=k,
            n=live[k])

    add("synthesis", SYNTHESIS_TITLES[rot % len(SYNTHESIS_TITLES)],
        SPINE_WORDS["synthesis"], SPINE_CITES["synthesis"])
    add("audit", AUDIT_TITLES[rot % len(AUDIT_TITLES)].format(year=year),
        SPINE_WORDS["audit"], SPINE_CITES["audit"])
    add("gaps", "Research Gaps and Outlook", SPINE_WORDS["gaps"],
        SPINE_CITES["gaps"])

    if sections[-1]["role"] != "gaps":
        raise SystemExit("FAIL-CLOSED: gaps must be the last section")

    cite_sum = sum(s["cite_target"] for s in sections)
    lo, hi = CITE_SUM_BAND
    if not (lo <= cite_sum <= hi):
        raise SystemExit(
            f"FAIL-CLOSED device map: per-section citation minimums sum to "
            f"{cite_sum}, outside ({lo}, {hi}). A writer meeting every "
            f"minimum would miss the issue-level band. Retune "
            f"WORDS_PER_CITE / DEVICE_MAX_WORDS, NEVER the gate.")

    total_ceiling = sum(s["ceiling"] for s in sections)
    payload = json.dumps({"year": year, "mass": mass, "live": live,
                          "sections": [(s["role"], s["title"], s["ceiling"],
                                        s["cite_target"]) for s in sections]},
                         sort_keys=True)
    return {
        "year": year, "n_months": n_months, "spine": "device_class",
        "class_mass": mass, "class_mass_after_fold": live, "folded": folded,
        "sections": sections, "total_ceiling": total_ceiling,
        "cite_target_sum": cite_sum,
        "params": {"DEVICE_MIN_WORDS": DEVICE_MIN_WORDS,
                   "DEVICE_MAX_WORDS": DEVICE_MAX_WORDS,
                   "WORDS_PER_CITE": WORDS_PER_CITE,
                   "MIN_CLASS_CARDS": MIN_CLASS_CARDS,
                   "body_budget": body_budget},
        "sha256": hashlib.sha256(payload.encode()).hexdigest()[:16],
    }


if __name__ == "__main__":
    from stages.util import read_jsonl, run_dir
    from stages.yearly_corpus import aggregate, yearly_dir

    if len(sys.argv) < 2:
        raise SystemExit("usage: yearly_device_map.py <YYYY> [--partial]")
    yr = sys.argv[1]
    agg = aggregate(yr, require_full_year="--partial" not in sys.argv)
    rd = run_dir(yr, create=False)
    ab = {x["work_key"]: x["abstract"]
          for x in read_jsonl(rd / "private" / "02_abstracts.jsonl")}
    mp = build_map(yr, agg["cards"], ab, n_months=agg["n_months"])
    out = yearly_dir(yr) / "yearly_section_map.json"
    out.write_text(json.dumps(mp, indent=2), encoding="utf-8")
    print(f"[map] spine=device_class sha {mp['sha256']}  "
          f"cite_sum {mp['cite_target_sum']}  ceiling {mp['total_ceiling']}")
    print(f"[map] class mass {mp['class_mass']}")
    if mp["folded"]:
        print(f"[map] folded {mp['folded']}")
    for s in mp["sections"]:
        tag = f" [{s.get('device_class')}]" if s.get("device_class") else ""
        print(f"  {s['id']:>2} {s['role']:<11} ceil={s['ceiling']:<5} "
              f"cite={s['cite_target']:<3} {s['title'][:52]}{tag}")
    print(f"[map] -> {out}")
