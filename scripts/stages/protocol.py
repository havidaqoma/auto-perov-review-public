"""Canonical stability-protocol labels. ONE definition.

Why this exists
---------------
The extractor records the protocol string as the paper wrote it, and papers
write the same protocol several ways:

    ISOS-L-1   and   ISOS-L-1   (U+2010 hyphen, not ASCII)
    ISOS-L-2   and   ISOS-L2
    ISOS-D-1   and   ISOS-D1

Handbook 4.4 rule 1 is explicit that Unicode must be normalised BEFORE
matching, and it was written after exactly this class of bug: the writer emits
U+2212 where the rule expects ASCII, the glyphs are identical, and an
ASCII-only comparison silently reports the wrong answer.

The protocol labels were never normalised anywhere, so the H1 stability figure
plotted 19 categories for 13 real protocols, splitting each protocol's count
across its spellings and overstating the diversity of stability practice.

This module is imported by the figure and by the count used in prose. It is
NOT copied into either, because a guard that exists twice diverges (7.6 #10,
#12).
"""
from __future__ import annotations

import re
import unicodedata

# Every Unicode dash that a publisher may substitute for ASCII '-'.
# U+2010 HYPHEN, U+2011 NB HYPHEN, U+2012 FIGURE DASH, U+2013 EN DASH,
# U+2014 EM DASH, U+2015 HORIZONTAL BAR, U+2212 MINUS SIGN.
_DASHES = r"[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]"

# ISOS-<family><n>[I]: family is D (dark), L (light), O (outdoor),
# T (thermal cycling), V (voltage), LC/LT (combined). The optional trailing
# 'I' marks the ISOS "I" variant and is preserved: ISOS-L-2I is a different
# protocol from ISOS-L-2 and must not be merged into it.
_ISOS = re.compile(r"^ISOS-?(D|L|O|T|V|LC|LT)-?(\d)(I?)$")


def canon_protocol(raw: str) -> str:
    """Canonical label for one protocol string.

    Returns the ISOS form when the string names an ISOS protocol, otherwise the
    upper-cased first token. Never guesses: a string that does not match the
    ISOS grammar is returned as itself, not coerced into the nearest protocol.
    """
    if not raw:
        return ""
    s = unicodedata.normalize("NFKC", raw)
    s = re.sub(_DASHES, "-", s)
    tok = s.split()[0].upper().rstrip(".,;:)")
    m = _ISOS.match(tok)
    if m:
        return f"ISOS-{m.group(1)}-{m.group(2)}{m.group(3)}"
    return tok


def normalize_text(raw: str) -> str:
    """NFKC + dash unification for scanning FREE TEXT (not a single label).

    canon_protocol() normalises ONE label. The corpus audit scans whole
    abstracts, and it was doing so with a raw ASCII-hyphen regex, so every
    publisher that types U+2010 was invisible to it. Handbook 4.4 rule 1 --
    normalise Unicode BEFORE matching -- applies to the scanner exactly as it
    applies to the label.
    """
    return re.sub(_DASHES, "-", unicodedata.normalize("NFKC", raw or ""))


# Free-text scanner, sharing the family vocabulary of _ISOS above so the two
# cannot disagree about what an ISOS protocol is.
#
# Alternation is LONGEST-FIRST (LC|LT before L): Python alternation is
# first-match, so "L" placed first would consume the L of "ISOS-LC-1" and
# leave "C-1" unmatched. Same trap as ABBREV's longest-key-first ordering,
# where "PL" would otherwise swallow "TRPL".
#
# A family letter AND a digit are both required, so "ISOS protocols" with no
# code does NOT count -- consistent with is_isos(), because a paper naming no
# protocol has not tested to a defined standard.
ISOS_IN_TEXT = re.compile(r"\bISOS-?(?:LC|LT|D|L|O|T|V)-?\d I?\b".replace(" ", ""),
                          re.I)


def isos_in_text(raw: str) -> bool:
    """True if free text names a SPECIFIED ISOS protocol, dash-agnostic."""
    return bool(ISOS_IN_TEXT.search(normalize_text(raw)))


# --- operational lifetime -------------------------------------------------
#
# SPECIFIED FROM FIRST PRINCIPLES, BEFORE BEING MEASURED. The R1 sheet asked
# "does the abstract give an operational lifetime (T80 or equivalent)?" and the
# only machine answer available was a CARD field, which exists for the depth
# tier alone -- so 49 of 100 sampled papers had no comparable value and the
# apparent recall of 0.077 was a population artifact, not a miss.
#
# Writing this pattern by looking at which of the 100 labelled abstracts it
# happens to catch would be HARKing: the labels are the test set, and a rule
# fitted to its own test set measures nothing. So the grammar is enumerated
# from how the perovskite stability literature actually reports lifetime, then
# evaluated ONCE and reported whatever it says.
#
# Three ways a lifetime is stated:
#   1. a T-metric with a number of hours   "T80 of 1200 h", "T80 > 1000 hours"
#   2. retention of a percentage over time "retained 92% after 1000 h"
#   3. operation/storage for a duration    "stable for 1500 h under 1 sun"
#
# Deliberately NOT counted: a duration with no performance claim attached
# ("annealed for 30 min"), and a bare "long-term stability" with no number.
# A lifetime claim needs BOTH a quantity and a time.
_HOURS = r"(?:h|hr|hrs|hours?)"
_T_METRIC = r"\bT-?\s?(?:80|85|90|95|98)\b"

T80_IN_TEXT = re.compile(
    # 1. T-metric anywhere near a number of hours (either order)
    rf"{_T_METRIC}[^.]{{0,60}}?\d[\d,.]*\s*{_HOURS}\b"
    rf"|\d[\d,.]*\s*{_HOURS}\b[^.]{{0,40}}?{_T_METRIC}"
    # a T-metric alone still names the metric, e.g. "T80 lifetime was reached"
    rf"|{_T_METRIC}\s*(?:lifetime|stability)"
    # 2. retention of a percentage after / over / within a duration
    rf"|\b(?:retain|retaining|retained|maintain|maintaining|maintained|"
    rf"preserv\w+|keep|kept)\b[^.]{{0,80}}?\d[\d,.]*\s*%[^.]{{0,60}}?"
    rf"\d[\d,.]*\s*{_HOURS}\b"
    rf"|\d[\d,.]*\s*%[^.]{{0,40}}?(?:of (?:its |the )?initial|of the original)"
    rf"[^.]{{0,60}}?\d[\d,.]*\s*{_HOURS}\b"
    # 3. operational/storage stability FOR a stated duration
    rf"|\b(?:stab\w+|operat\w+|degrad\w+|lifetime|durability|continuous)\b"
    rf"[^.]{{0,60}}?\b(?:for|after|over|exceeding|beyond|up to|within)\b\s*"
    rf"[~>]?\s*\d[\d,.]*\s*{_HOURS}\b",
    re.I)


def t80_in_text(raw: str) -> bool:
    """True if free text states an operational lifetime with a duration."""
    return bool(T80_IN_TEXT.search(normalize_text(raw)))


def is_isos(label: str) -> bool:
    """True only for a SPECIFIED ISOS protocol.

    Bare 'ISOS' is deliberately False: a paper that says "ISOS protocols" with
    no family or number has not named a protocol, and counting it as one
    overstates how much of the literature is testing to a defined standard.
    IEC, MPP, UV and bare thermal conditions are not ISOS at all.
    """
    return bool(re.match(r"^ISOS-(D|L|O|T|V|LC|LT)-\d I?$".replace(" ", ""),
                         label or ""))


def protocol_counts(cards: list) -> dict:
    """Canonical label -> paper count, over cards carrying a protocol string."""
    out: dict[str, int] = {}
    for c in cards:
        p = (c.get("stability") or {}).get("protocol")
        if not p:
            continue
        k = canon_protocol(p)
        if k:
            out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


def n_isos_specified(cards: list) -> int:
    """Papers naming a SPECIFIED ISOS protocol (the honest N_PROTO)."""
    return sum(n for k, n in protocol_counts(cards).items() if is_isos(k))


def n_any_protocol(cards: list) -> int:
    """Papers naming any stability protocol at all, ISOS or not."""
    return sum(protocol_counts(cards).values())
