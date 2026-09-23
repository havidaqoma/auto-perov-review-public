"""device_class: assign every card to ONE device-class topic.

WHY THIS MODULE EXISTS
----------------------
Version 3 of the review organised its body by MECHANISM axis (defects,
interfaces, composition...). Havid asked for a device-class spine instead:
single junction, all-perovskite tandem, perovskite/silicon and other hybrid
tandems, and modules. That is a better spine for this field, because a reader
asking "what happened in tandems this year" cannot answer it from a defects
section that mixes single cells and stacks.

But a device spine only works if a card can be assigned to exactly one class,
and the obvious way to do that is WRONG.

THE TANDEM-KEYWORD TRAP -- MEASURED, NOT SUSPECTED
--------------------------------------------------
A first classifier keyed on the word "tandem" anywhere in the title, abstract
or anchors. It produced 28 "tandem" cards whose titles read:

    Efficient and Moisture Resistant Wide-Bandgap Perovskite Solar Cells...
    Grain Boundary Engineering Enables 22.2%-Efficient Inverted Wide-Bandgap
      Perovskite Solar Cells...
    Multifunctional Passivator Enables High-Efficient Gas-Quenching Sn-Pb
      Perovskite Solar Cells

None of those is a tandem. They are SINGLE-JUNCTION wide-bandgap or Sn-Pb
cells whose abstracts mention tandems as the motivation -- "a promising
top-cell candidate for tandem application". Wide-bandgap and Sn-Pb chemistry
exists largely to serve tandems, so the word appears constantly in papers
that never built a stack.

Counted as tandems, those 28 cards would have inflated the tandem sections by
roughly a third and put single-junction efficiencies under a tandem heading,
where a reader would compare them against the 47.6 percent two-junction bound
instead of the 29.4 percent single-junction one. That is the misattribution
defect (a real number describing the wrong device) applied to a whole
section rather than one value.

THE RULE
--------
A device class is claimed only by evidence that the DEVICE was built:

  - an explicit stack ("perovskite/silicon tandem", "all-perovskite tandem")
  - a terminal count ("two-terminal", "monolithic")
  - a partner absorber named as a subcell (Si, CIGS, organic)
  - the extracted architecture field, which guard 5 already corrected against
    the value's own anchor

The bare word "tandem" NEVER claims a card on its own. Neither does
"wide-bandgap" or "Sn-Pb": both describe a perovskite composition, not a
device. A paper that says "suitable for tandems" is a single-junction paper.

Classification order is fixed and documented in `classify()`, because the
classes overlap in reality: an all-perovskite tandem module is both a module
and a tandem, and it must land in exactly one section.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------- classes
SINGLE = "single_junction"
ALLPK = "all_perovskite_tandem"
HYBRID = "hybrid_tandem"          # perovskite/Si, /CIGS, /organic, /DSSC
MODULE = "module"

CLASS_ORDER = [SINGLE, ALLPK, HYBRID, MODULE]

CLASS_LABEL = {
    SINGLE: "Single-junction cells",
    ALLPK: "All-perovskite tandems",
    HYBRID: "Perovskite/silicon and other hybrid tandems",
    MODULE: "Modules and large-area devices",
}

CLASS_SHORT = {
    SINGLE: "single junction",
    ALLPK: "all-perovskite tandem",
    HYBRID: "hybrid tandem",
    MODULE: "module",
}

# Detailed-balance ceiling per class. A single global bound would reject the
# tandems that top this frontier; the tandem bound applied globally would
# readmit the 32.95%-as-single-junction defect G3c exists to catch.
CLASS_PCE_LIMIT = {
    SINGLE: 29.4,     # 1.55 eV Shockley-Queisser
    ALLPK: 47.6,      # two-junction detailed balance
    HYBRID: 47.6,     # two-junction detailed balance
    MODULE: 47.6,     # a module may be a tandem module
}

# ------------------------------------------------------------- detectors
#
# Each of these asserts a DEVICE WAS BUILT. Motivation language is excluded
# by construction: see the module docstring.

# A module is a device fact, not a composition, so it is safe to key on.
_MODULE = re.compile(
    r"\b(?:mini[\-\s]?module|sub[\-\s]?module|module|panel)\b", re.I)

# An all-perovskite stack names both perovskite subcells, or says so.
_ALLPK = re.compile(
    r"all[\-\s]?perovskite[\-\s]?(?:tandem|multijunction|stack)?"
    r"|perovskite\s*/\s*perovskite"
    r"|(?:wide|narrow)[\-\s]?bandgap\s+(?:top|bottom)\s+(?:sub)?cell"
    r"|sn[\-\s]?pb\s+(?:bottom|narrow)[\-\s]?(?:bandgap\s+)?(?:sub)?cell",
    re.I)

# A hybrid stack names a NON-perovskite partner absorber.
_HYBRID = re.compile(
    r"perovskite\s*[/\-]\s*(?:si|silicon|c[\-\s]?si|cigs|cis|czts|"
    r"organic|opv|dye|cdte|gaas)\b"
    r"|(?:si|silicon|c[\-\s]?si|cigs|czts|organic|opv|cdte|gaas)"
    r"\s*[/\-]\s*perovskite"
    r"|(?:silicon|cigs|organic|cdte)\s+bottom\s+(?:sub)?cell"
    r"|textured\s+silicon\s+(?:bottom|subcell|tandem)"
    r"|monolithic\s+perovskite[\-\s/]*(?:si|silicon|cigs|organic)",
    re.I)

# A tandem device WITHOUT a named partner. Requires a terminal count or an
# explicit monolithic/stacked construction -- never the bare word "tandem".
_TANDEM_DEVICE = re.compile(
    r"\b(?:two|2|four|4)[\-\s]?terminal\b"
    r"|\b2[\-\s]?t\b|\b4[\-\s]?t\b"
    r"|monolithic(?:ally)?\s+integrated"
    r"|tandem\s+(?:device|cell|solar\s+cell|module)\s+(?:with|achiev|deliver|"
    r"reach|exhibit|show)",
    re.I)

# Language that mentions tandems as MOTIVATION. Presence of this alone must
# never claim a card. Kept explicit so the exclusion is auditable rather
# than implied by the absence of a match.
_MOTIVATION = re.compile(
    r"(?:candidate|promising|suitable|potential|application|prospect|"
    r"toward|towards|for use|paves?\s+the\s+way|opens?\s+(?:up\s+)?)"
    r"[^.]{0,60}\btandem",
    re.I)


def _haystack(card: dict, abstract: str = "") -> str:
    """Title + abstract + every verbatim anchor + claim text.

    Anchors are included because guard 1 verified them word-for-word against
    the source, so they are the most trustworthy text available about what
    the measured device actually was.
    """
    parts = [card.get("title") or "", abstract or ""]
    for group in ("performance", "stability"):
        for f in (card.get(group) or {}).values():
            if isinstance(f, dict) and f.get("anchor"):
                parts.append(f["anchor"])
    for cl in (card.get("claims") or []):
        if isinstance(cl, dict) and cl.get("text"):
            parts.append(cl["text"])
    return " ".join(parts)


def classify(card: dict, abstract: str = "") -> str:
    """Assign ONE device class. Order is fixed and load-bearing.

    The classes overlap in reality, so precedence decides ownership:

    1. MODULE first. An all-perovskite tandem mini-module belongs in the
       module section, because its argument is area and uniformity, not
       junction physics. The architecture field is authoritative here since
       guard 5 already reconciled it against the value's own anchor.
    2. HYBRID before ALLPK. "Perovskite/silicon" is unambiguous; a paper
       naming a silicon subcell is a hybrid tandem even if it also discusses
       perovskite/perovskite work.
    3. ALLPK next.
    4. Generic tandem DEVICE language falls to HYBRID, because an
       unspecified two-terminal stack is far more often silicon-partnered
       than all-perovskite in this corpus, and the hybrid section explicitly
       covers "and other".
    5. SINGLE is the default. Motivation language about tandems lands here,
       which is the correct home for a wide-bandgap top-cell study.
    """
    arch = ((card.get("device") or {}).get("architecture") or "").lower()
    text = _haystack(card, abstract)

    if arch == "module" or _MODULE.search(text):
        return MODULE
    if _HYBRID.search(text):
        return HYBRID
    if _ALLPK.search(text):
        return ALLPK
    if arch in ("tandem_2t", "tandem_4t") or _TANDEM_DEVICE.search(text):
        return HYBRID
    return SINGLE


def mentions_tandem_only_as_motivation(card: dict, abstract: str = "") -> bool:
    """True when a card talks about tandems but built a single junction.

    Reported in the SI so the exclusion is visible rather than silent: a
    reader should be able to see how many single-junction papers were framed
    as tandem enablers.
    """
    if classify(card, abstract) != SINGLE:
        return False
    return bool(_MOTIVATION.search(_haystack(card, abstract))
                or re.search(r"\btandem", _haystack(card, abstract), re.I))


def class_mass(cards: list, abstracts: dict | None = None) -> dict:
    """Cards per device class, in CLASS_ORDER, zero-filled.

    Zero-filling matters: a class with no cards must appear as 0 rather than
    vanish, or the section map cannot tell "no evidence" from "not computed".
    """
    abstracts = abstracts or {}
    out = {k: 0 for k in CLASS_ORDER}
    for c in cards:
        out[classify(c, abstracts.get(c.get("work_key"), ""))] += 1
    return out


# =====================================================================
# ILLUMINATION CONDITION
# =====================================================================
#
# WHY THIS EXISTS -- MEASURED, AND IT NEARLY WENT THE OTHER WAY
# -------------------------------------------------------------
# Havid asked why a single-junction card reported 33.2%, above the 29.4%
# Shockley-Queisser ceiling, and guessed a tandem or a simulation. Neither.
# The anchor reads:
#
#   "a record-high PCE of 33.2% is achieved for Li2CO3-modified C-PSCs
#    under WEAK LIGHT ILLUMINATION conditions, demonstrating excellent
#    INDOOR PHOTOVOLTAIC performance"
#
# It is an INDOOR photovoltaic measurement. Shockley-Queisser's 29.4% is
# derived for the AM1.5G solar spectrum; under narrow indoor light a
# wide-gap perovskite legitimately exceeds it. The number is real, the
# extraction is correct, the device class is correct -- and plotting it
# against an AM1.5G limit line is still wrong, because it is not the same
# quantity.
#
# This is the misattribution defect in a THIRD form. The first was a tandem
# value on a single-junction label; the second was tandem-motivation papers
# classed as tandems; this one is a different ILLUMINATION CONDITION. G3c
# cannot see it: G3c selects its bound by device class, and the device class
# is right. The missing dimension is the measurement condition.
#
# THE TRAP IN THE FIX, WHICH IS WORSE THAN THE ORIGINAL BUG
# ----------------------------------------------------------
# A first detector asked "does the anchor mention indoor light anywhere?".
# On the real corpus that tagged SIX values, of which THREE were false
# positives:
#
#   "a 23.7% PCE (22.9% certified) under AM 1.5 G illumination
#    and a 42.46% PCE under 1000 lux"          <- 22.9 is the AM1.5G value
#   "achieved a PCE of 21.9% under 1-sun equivalent illumination
#    and 42.6% under indoor light"             <- 21.9 is the 1-sun value
#   "Under standard sunlight conditions, the devices reach 20.1%"
#                                              <- title says indoor, value is not
#
# Papers routinely report BOTH conditions in one sentence. A whole-anchor
# test would have deleted three legitimate outdoor values while fixing two
# indoor ones: a misattribution introduced while repairing a
# misattribution.
#
# THE RULE
# --------
# The illumination condition belongs to THE NUMBER'S OWN LOCAL CONTEXT, not
# to the anchor as a whole. This is guard 4 -- "the label comes from the
# value's own quotation" -- taken one level finer: within the quotation, the
# marker nearest the value wins, and a marker AFTER the value is preferred
# because "X% under Y" is how the language works.
#
# Titles are advisory only. A title may say "Indoor Photovoltaics" while the
# extracted number is the paper's AM1.5G control, which is exactly case
# three above.

AM15 = "am15"
INDOOR = "indoor"
UNKNOWN_ILLUM = "unknown"

_INDOOR_MARK = re.compile(
    r"\bindoor\b|\bweak[\s\-]?light\b|\blow[\s\-]?light\b|\bdim[\s\-]?light\b"
    r"|\bambient\s+light\b|\bartificial\s+light\b|\bfluorescent\b"
    r"|\b\d{2,5}\s*lux\b|\bLED\s+illumination\b", re.I)

_AM15_MARK = re.compile(
    r"AM\s?1\.?5|\bone[\s\-]?sun\b|\b1[\s\-]?sun\b"
    r"|standard\s+(?:test|sunlight|illumination|conditions)"
    r"|\b100\s*mW\s*(?:/|per\s+)?\s*cm", re.I)

# How far from the value to look. Forward 90 covers "of 33.2% is achieved
# for X under weak light". Backward 130 covers "Under standard sunlight
# conditions, the devices reach a Power Conversion Efficiency (PCE) of
# 20.1%", where the marker sits at position 6 and the value at 93 -- a
# 60-character window truncated it and returned "unknown". That failure was
# benign (an unmarked value is treated as standard conditions, so nothing
# was dropped) but it would have understated the SI's condition counts.
_FWD, _BACK = 90, 130


def illumination_of(anchor: str, value) -> str:
    """Illumination condition for ONE value inside its own quotation.

    Returns "am15", "indoor" or "unknown". Nearest marker to the value
    wins; a marker following the value is preferred over one preceding it,
    because the reporting convention is "<value> under <condition>".
    """
    if not anchor or value is None:
        return UNKNOWN_ILLUM
    txt = str(anchor)

    # Locate the value as it appears. Try the literal form first, then the
    # integer form, so 30.30 matches "30.30%" and 33.0 matches "33%".
    cands = [f"{value}"]
    if isinstance(value, float):
        if value == int(value):
            cands.append(str(int(value)))
        cands.append(f"{value:.2f}".rstrip("0").rstrip("."))
    pos = -1
    for cand in cands:
        pos = txt.find(cand)
        if pos >= 0:
            break
    if pos < 0:
        # The value is not in its own anchor. Guard 2 should have caught
        # that upstream, so do not guess a condition here.
        return UNKNOWN_ILLUM

    end = pos + len(cands[0])
    after = txt[end:end + _FWD]
    before = txt[max(0, pos - _BACK):pos]

    # Forward window first, nearest marker wins.
    ai, aa = _INDOOR_MARK.search(after), _AM15_MARK.search(after)
    if ai and aa:
        return INDOOR if ai.start() < aa.start() else AM15
    if ai:
        return INDOOR
    if aa:
        return AM15

    # Backward window, nearest to the value means LAST match.
    bi = list(_INDOOR_MARK.finditer(before))
    ba = list(_AM15_MARK.finditer(before))
    if bi and ba:
        return INDOOR if bi[-1].end() > ba[-1].end() else AM15
    if bi:
        return INDOOR
    if ba:
        return AM15
    return UNKNOWN_ILLUM


def is_indoor_value(anchor: str, value, source: str = "") -> bool:
    """True only when the value's OWN context names indoor illumination.

    Deliberately not `!= AM15`: an unmarked value is assumed to be a
    standard-conditions measurement, because that is the overwhelming
    default in this literature. Assuming otherwise would silently drop the
    majority of the corpus from every performance figure.

    THE TRUNCATION PROBLEM, AND WHY `source` EXISTS
    -----------------------------------------------
    Guard 3 truncates every anchor to 25 words BEFORE the value check, and
    that cap is not negotiable: checking the value before truncating once
    shipped five fields whose quotations ended immediately before their own
    number. But truncation can cut the illumination marker off the end of
    an otherwise clear quotation. Measured on 2025:

        anchor : "...PCE of 30.30% and an open-circuit voltage (VOC) of
                  936 mV under 1000"                  <- 25 words exactly
        source : "...936 mV under 1000 lux (3000 K LED)"

    The anchor stops one word before "lux", so an anchor-only test returns
    "unknown" and a genuine indoor value reaches an AM1.5G figure.

    The resolution is NOT to widen guard 3. Guard 3 governs what may be
    QUOTED to a reader; it does not govern what the pipeline may KNOW. The
    full abstract is on disk and already verified, so the illumination
    condition is read from the source when the anchor is inconclusive.

    Order matters: the anchor is consulted FIRST, because it is the text
    verified word-for-word against the source and the text nearest the
    value. The source is a fallback for "unknown", never an override of a
    definite anchor reading. Letting the source override would reintroduce
    the whole-abstract false positives this module was written to prevent
    (a paper reporting BOTH conditions in one sentence).
    """
    verdict = illumination_of(anchor, value)
    if verdict != UNKNOWN_ILLUM:
        return verdict == INDOOR
    if source:
        return illumination_of(source, value) == INDOOR
    return False
