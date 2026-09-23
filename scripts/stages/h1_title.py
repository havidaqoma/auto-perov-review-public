"""The H1 title, defined ONCE.

s18d.derive_title computes its rotation index as int(month[:4])*12 +
int(month[5:7]), which raises on "2026-H1". Three consumers need a working
title: the build (s18d), the SI (s19) and the ChemRxiv package (s20).

The first fix lived inside h1_build.py. That was already one copy too many:
the moment s19 asked for a title, a second copy would have been written, and
s20 would have made a third. Three copies of one guard is precisely the
divergence the handbook records twice (7.6 #10, the narration filter in three
copies with the build-side copy narrowest; 7.6 #12, the citation regex applied
in only one consumer).

So the title lives here, and every H1 stage imports it.

Nothing about the title CONTRACT is relaxed. Same frame, same axis phrases from
config/title_terms.yaml, same banned-term list, same one-colon rule, same word
cap, same no-publication-count rule. Only the rotation index is period-derived
instead of month-derived, because a half-year issue has no month number.
"""
from __future__ import annotations

import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

PERIOD_LABEL = "January-June 2026"
# Deterministic rotation for 2026-H1: same edition always yields the same
# title, or a rerun would rename the paper (the reproducibility rule that
# makes the section map deterministic too).
ROT = 2026 * 2 + 1


def derive_title_h1(month=None, smap=None) -> str:
    """Signature matches s18d.derive_title so it can be rebound in place."""
    from stages.s18d_build_v4 import TITLE_FRAME

    tt = yaml.safe_load(
        (ROOT / "config" / "title_terms.yaml").read_text(encoding="utf-8"))
    phrases = tt.get("axis_phrases", {})

    mech = [s for s in (smap or {}).get("sections", [])
            if s.get("role") == "mechanism"][:2]
    picked = []
    for s in mech:
        bank = phrases.get(s.get("axis")) or []
        if bank:
            picked.append(bank[ROT % len(bank)])
    if not picked:
        picked = ["a half-year mechanism and reporting audit"]

    # Comma-join when a phrase already contains "and", or the slot reads
    # "X and Y and Z": two conjunctions in one noun phrase is a defect a
    # reader sees immediately, in the most-read line of the PDF.
    if len(picked) == 2 and any(" and " in p for p in picked):
        slot = f"{picked[0]}, {picked[1]}"
    else:
        slot = " and ".join(picked)
    slot = slot[0].upper() + slot[1:] if slot else slot
    title = f"{TITLE_FRAME} in {PERIOD_LABEL}: {slot}"

    banned = [x.lower() for x in tt.get("banned_in_title", [])]
    hits = [x for x in banned if x in title.lower()]
    if hits:
        raise SystemExit(f"FAIL-CLOSED title contains banned term {hits}")
    if title.count(":") != 1:
        raise SystemExit(f"FAIL-CLOSED title needs exactly one colon: {title}")
    if len(title.split()) > tt.get("max_title_words", 16):
        title = f"{TITLE_FRAME} in {PERIOD_LABEL}: {picked[0].capitalize()}"
    # No publication count in the title: it goes stale as months backfill and
    # contradicts the indexing caveat the paper itself states. PERIOD_LABEL
    # legitimately carries the year, so remove it before checking for digits.
    if re.search(r"\b\d{2,}\b", title.replace(PERIOD_LABEL, "")):
        raise SystemExit("FAIL-CLOSED title carries a publication count")
    return title


if __name__ == "__main__":
    import json
    smap = json.loads(
        (ROOT / "runs" / "2026-H1" / "12_section_map.json").read_text(encoding="utf-8"))
    print(derive_title_h1(None, smap))
