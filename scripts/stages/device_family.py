"""Canonical DEVICE FAMILY classification. ONE definition.

Havid's v2 structure (2026-09-09): the main text is organised by four device
families instead of six mechanism axes.

    sj      single junction
    ap      all-perovskite tandem (perovskite + perovskite)
    hyb     perovskite + NON-perovskite partner: silicon leads, plus
            perovskite/organic, perovskite/CIGS, perovskite/CdTe, kesterite
    mod     module (a form factor, not a junction count -- see PRECEDENCE)

Why s11b's cls() could not be reused
------------------------------------
cls() has four buckets (sj / ap / psi / mod) and NO bucket for a non-silicon,
non-perovskite partner. Measured on the 872 H1 cards: 19 tandems with an
organic, CIGS, CdTe or kesterite partner were classified `ap`, i.e. reported as
ALL-PEROVSKITE tandems. Examples:

    "Perovskite/Organic Tandem Solar Cells with 26.49% Efficiency ..."   -> ap
    "Efficient Perovskite-Cu(In,Ga)Se2 Tandem Solar Cells ..."           -> ap
    "Thermally Stable Halide-Tuned CsPbX3/CdTe Four-Terminal Tandem ..." -> ap
    "... kesterite/perovskite tandem solar cells ..."                    -> ap

That is a device label contradicting the paper, which is monthly handbook 7.8:
a real number attached to the wrong device. It shipped invisibly because no
gate compares a device label against its own title or anchor.

PRECEDENCE, and why it is explicit
----------------------------------
A module can be single-junction OR tandem, so `mod` overlaps every other
family. Order is therefore declared, not incidental:

    mod  >  hyb  >  ap  >  sj

`mod` wins because the FINDING for a module-scale measurement is the area
penalty, not the junction count -- that is why the family exists as a section.
`hyb` beats `ap` because a paper naming BOTH silicon and a wide-bandgap
perovskite is a perovskite/Si tandem, not an all-perovskite one.

ANCHOR-FIRST, and why
---------------------
Where a certified value carries an anchor, the anchor is the only text verified
verbatim against the source, so it classifies the DEVICE THE NUMBER WAS
MEASURED ON. The title describes the paper. Handbook 7.8 exists because one
abstract reported two devices and the label followed the paper while the number
came from the other one.

So: anchor first, then architecture, then title. And `unspecified tandem` is a
real answer -- a tandem naming no partner is NOT silently assigned to a family.
"""
from __future__ import annotations

import re
import unicodedata

FAMILIES = ("sj", "ap", "hyb", "mod")

# A module is a SIZE, and sizes have a floor. Below this, a device is a
# laboratory cell no matter what words surround it.
#
# This exists because five cards survived the anchor rule with areas of 0.049,
# 0.067, 0.096, 0.108 and 0.108 cm2. Their area anchors name TWO devices in one
# sentence and the card's area value is the SMALL one:
#
#   "21.46% (small-area, 0.108 cm2) and 19.38% (large-area module, 15.52 cm2)"
#   "26.41% (0.096 cm2) and 22.18% (10.04 cm2 module)"
#   "certified 26.61% for small-area PSCs (0.06734 cm2) and 22.83% for
#    large-area modules (62.37 cm2)"
#
# One of them even carries architecture 'module' while its own anchor says
# "flexible all-perovskite tandem CELLS (active area of 0.049 cm 2)" -- the
# architecture describes the paper, the anchor describes the number.
#
# This is handbook 7.8 exactly: an abstract reporting two devices lends the
# wrong one its label. Word adjacency would be fragile here, so the guard is
# the handbook's own corollary instead -- add a plausibility gate wherever
# physics bounds a quantity. 1 cm2 is conservative: the smallest genuine
# mini-module in this corpus is 3.9 cm2, and typical lab cells are 0.04-0.12.
MODULE_MIN_AREA_CM2 = 1.0

LABEL = {
    "sj": "Single junction",
    "ap": "All-perovskite tandem",
    "hyb": "Perovskite/silicon and other hybrid tandems",
    "mod": "Module",
    "tandem_unspecified": "Tandem, partner not specified",
}
SHORT = {
    "sj": "Single junction",
    "ap": "All-perovskite tandem",
    "hyb": "Hybrid tandem",
    "mod": "Module",
    "tandem_unspecified": "Tandem (unspecified)",
}

# --- partner detection -------------------------------------------------------
_SI = re.compile(
    r"perovskite\s*[/\u2013\u2014-]\s*si\b|/si\b|\bc-si\b|crystalline silicon|"
    r"\bsilicon\b|\bshj\b|silicon heterojunction|\btopcon\b|textured silicon",
    re.I)
# Non-silicon, non-perovskite partners. Kept explicit rather than "anything not
# perovskite": a guessed partner is worse than an unspecified one.
_OTHER_PARTNER = re.compile(
    r"perovskite\s*[/\u2013\u2014-]\s*organic|organic\s*[/\u2013\u2014-]\s*perovskite|"
    r"\bopv\b|organic photovolta|organic solar cell|bulk[- ]heterojunction|"
    r"\bcigs\b|cu\s*\(\s*in\s*,?\s*ga\s*\)\s*se|cuin|\bcis\b|"
    r"kesterite|\bczts\b|cu2znsn|"
    r"\bcdte\b|cspbx\s*3\s*/\s*cdte|"
    r"\bs?bs?e\b|antimony selenide|selenium solar|"
    r"quantum dot photovolta|\bpbs\b quantum",
    re.I)
_ALL_PEROV = re.compile(
    r"all[- ]perovskite|perovskite\s*[/\u2013\u2014-]\s*perovskite|"
    r"(?:sn[- ]?pb|tin[- ]lead|pb[- ]?sn)\b.{0,40}(?:tandem|narrow)|"
    r"narrow[- ]bandgap.{0,40}tandem|tandem.{0,40}narrow[- ]bandgap",
    re.I)
_TANDEM = re.compile(r"\btandem\b|\b[24][- ]?t\b|two[- ]terminal|four[- ]terminal|"
                     r"monolithic.{0,20}(?:stack|integrat)", re.I)
# Module / large-area form factor.
_MODULE = re.compile(
    r"\bmodule\b|\bmini[- ]?module\b|submodule|\bpanel\b|"
    r"blade[- ]coat|slot[- ]die|scalable fabrication|large[- ]area", re.I)


def _norm(s) -> str:
    if not s:
        return ""
    return unicodedata.normalize("NFKC", str(s))


def _anchor_of(card: dict, field: str) -> str:
    """Verbatim quotation bound to one numeric field, if present."""
    for sub in ("performance", "stability", "device"):
        d = card.get(sub) or {}
        f = d.get(field)
        if isinstance(f, dict):
            return _norm(f.get("anchor") or f.get("quote") or "")
    return ""


def evidence_text(card: dict) -> str:
    """The text that classifies the NUMBER: certified anchor, then champion."""
    return " ".join(x for x in (_anchor_of(card, "pce_certified"),
                                _anchor_of(card, "pce_champion")) if x)


def module_text(card: dict) -> str:
    """Every anchor that could name a module, INCLUDING the area anchor.

    The area anchor is where "module" actually appears, and omitting it shipped
    the defect this function exists to prevent. Measured on the H1 cards, two
    cards classified `sj` carried a module in their own area quotation:

        651 cm2  "...scalable fabrication of large-area perovskite modules..."
        100 cm2  "...large-area flexible modules obtain ... (100 square cent..."

    family.sj.max_area_cm2 therefore reported 651 cm2 for a SINGLE-JUNCTION
    CELL, which is module-scale hardware. The efficiency-vs-area argument is
    the whole point of the module section, so a module counted as a cell
    corrupts precisely the comparison the section is built on.

    Same class as handbook 7.8 and 7.6 #12: the guard existed, but it was
    applied to one field and not to the field carrying the evidence.
    """
    return " ".join(x for x in (_anchor_of(card, "pce_certified"),
                                _anchor_of(card, "pce_champion"),
                                _anchor_of(card, "active_area_cm2")) if x)


def _below_module_floor(card: dict) -> bool:
    """True when the card's OWN area value is a lab-cell area.

    See MODULE_MIN_AREA_CM2. Used by every module branch, including the
    `architecture == "module"` branch: the architecture field describes the
    paper, so it is not exempt from a physics floor.
    """
    af = (card.get("performance") or {}).get("active_area_cm2")
    av = af.get("value") if isinstance(af, dict) else None
    return isinstance(av, (int, float)) and av < MODULE_MIN_AREA_CM2


def family(card: dict) -> str:
    """Canonical family for one card. Never guesses a partner.

    Returns one of FAMILIES, or 'tandem_unspecified' when a card is clearly a
    tandem but names no partner anywhere. A caller that needs exactly four
    buckets must decide what to do with that -- it is not silently folded.
    """
    arch = _norm((card.get("device") or {}).get("architecture")).lower()
    title = _norm(card.get("title"))
    anchor = evidence_text(card)

    # 1. MODULE takes precedence: the finding is the area penalty.
    #    The module test reads module_text(), which INCLUDES the area anchor --
    #    that is where the word "module" actually appears. Using evidence_text()
    #    here classified two module papers as single junction and reported
    #    family.sj.max_area_cm2 = 651 cm2 for a cell.
    # The architecture field describes the PAPER; the anchor describes the
    # NUMBER. So even `architecture: module` is subject to the plausibility
    # floor -- two cards carried arch='module' with areas of 0.049 and
    # 0.06734 cm2, and one of them says in its own anchor "flexible
    # all-perovskite tandem CELLS (active area of 0.049 cm 2)". Returning
    # early here bypassed the floor entirely, which is why they survived.
    if arch == "module" and not _below_module_floor(card):
        return "mod"
    # A MODULE CLAIM MUST LIVE IN THE AREA ANCHOR.
    #
    # Two failures, in both directions, before this rule settled:
    #
    # 1. Searching only the efficiency anchors + title MISSED two real modules,
    #    because `\bmodule\b` cannot match "modules" -- the trailing \b fails
    #    against the following "s". Both defect cards said "modules":
    #      "...scalable fabrication of large-area perovskite modules..."  651 cm2
    #      "...large-area flexible modules obtain ... (100 square cent..." 100 cm2
    #    Identical to handbook 7.3 bug 6, where `gate checks?` missed
    #    "gate checking" for want of a word boundary.
    #
    # 2. Fixing the plural and searching ALL anchors + title OVER-captured:
    #    mod went 30 -> 68, including ten cards under 1 cm2 (one at
    #    0.045 cm2). A 0.045 cm2 device is not a module. 27 of those matched on
    #    an anchor while their title never says module, and 14 matched a title
    #    like "Perovskite Solar Cells and Modules" -- a paper that covers BOTH
    #    form factors, whose cited number may be either one.
    #
    # A module is a SIZE, so the claim belongs in the sentence that carries the
    # size. This is handbook 7.8's rule applied to the form factor: bind the
    # label to the number's own quotation, not to the paper.
    if re.search(r"\bmodules?\b|\bmini[- ]?modules?\b|submodules?",
                 _anchor_of(card, "active_area_cm2"), re.I):
        # PLAUSIBILITY FLOOR. The anchor names a module, but if the card's own
        # area value is a lab-cell area then the module in that sentence is a
        # DIFFERENT device (see MODULE_MIN_AREA_CM2). Fail toward `not a
        # module`: mislabelling a 0.049 cm2 cell as a module corrupts the
        # efficiency-vs-area comparison the module section exists to make.
        af = (card.get("performance") or {}).get("active_area_cm2")
        av = af.get("value") if isinstance(af, dict) else None
        if not (isinstance(av, (int, float)) and av < MODULE_MIN_AREA_CM2):
            return "mod"

    # 2. Anchor first, then title, for the partner.
    for blob in (anchor, title):
        if not blob:
            continue
        if _OTHER_PARTNER.search(blob):
            return "hyb"
        if _SI.search(blob):
            return "hyb"
        if _ALL_PEROV.search(blob):
            return "ap"

    # 3. Architecture is weaker evidence than a named partner: tandem_2T says
    #    "two junctions", not "which partner".
    if arch.startswith("tandem"):
        return "tandem_unspecified"
    if _TANDEM.search(title) or _TANDEM.search(anchor):
        return "tandem_unspecified"

    return "sj"


def family_or_fold(card: dict) -> str:
    """Four buckets. An unspecified tandem folds to `ap` ONLY as a last resort.

    Rationale, stated so it can be argued with: an unspecified tandem in this
    corpus is overwhelmingly a perovskite-perovskite stack reported by a group
    working on wide-bandgap absorbers, because a silicon or CIGS partner is
    essentially always named in the title (it is the selling point). Folding is
    still a GUESS, so `family()` keeps the honest label and every count that
    reaches the manuscript reports the unspecified bucket separately.
    """
    f = family(card)
    return "ap" if f == "tandem_unspecified" else f


def counts(cards: list, fold: bool = False) -> dict:
    fn = family_or_fold if fold else family
    out: dict[str, int] = {}
    for c in cards:
        out[fn(c)] = out.get(fn(c), 0) + 1
    order = list(FAMILIES) + ["tandem_unspecified"]
    return {k: out[k] for k in order if k in out}
