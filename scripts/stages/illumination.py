"""Illumination condition. ONE definition.

Why this exists
---------------
Havid read Table 1 and flagged a >30% single-junction PCE, expecting a tandem
or a simulation. Both guesses were reasonable and both were wrong, which is
why this module exists rather than a tweak to an existing guard.

The measured facts, from `scripts/probe_indoor_pv.py`:

    sj  top self-reported = 44.36%   lens=experimental
        anchor: "wide-band gap (WBG)-PIPVs achieve a PCE(i) of 44.36%
                 (a power output of 127.94 uW cm-2) ..."
        -> INDOOR photovoltaic, 1000 lx LED. PIPV = perovskite indoor PV.

    mod top self-reported = 41.6%    lens=scale_up
        anchor: "record indoor power conversion efficiencies of 41.60% at
                 900 lux and 41.22% at 300 lux under TL84 illumination"
        -> INDOOR mini-module, TL84 fluorescent.

Neither is an error, a tandem, or a simulation. Both are CORRECT numbers for a
different measurement. An indoor PCE above the one-sun Shockley-Queisser limit
is physically ordinary: the limit is defined for the AM1.5G spectrum, and a
1000 lx LED spectrum is narrow, low-flux and much better matched to a
wide-bandgap absorber, so conversion efficiency is legitimately higher while
the absolute power output is ~128 uW/cm2 instead of ~25 mW/cm2.

The defect is COMPARABILITY, not correctness. The review printed 44.36% in a
column headed "Best self-reported PCE" beside one-sun values, inviting a reader
to conclude that single junctions outperform perovskite/silicon tandems.

Why the existing guards all missed it
-------------------------------------
- `measured()` excludes lens in (theory, review). The 44.36% card is
  lens=experimental. It IS a measurement.
- `anchor_contradicts_family()` checks the DEVICE named in the anchor. The
  device is right: it is a single-junction wide-bandgap cell.
- G3c bounds SINGLE-JUNCTION CERTIFIED values at 29.4%. This is a
  self-reported value, and `pce_champion` had no plausibility check at all --
  on the reasoning that a self-reported number is the paper's own claim to
  make. That reasoning is wrong for exactly this case.

So this is a genuinely new axis: every previous guard asked *what device* or
*how verified*. None asked *under what illumination*.

Handbook 5 for figures and 4.4 for notation both say the same thing in
different words: a value only means something alongside the conditions it was
measured under. Illumination is one of those conditions, and it now travels
with the number.
"""
from __future__ import annotations

import re
import unicodedata

# Markers that a value was NOT measured under one-sun AM1.5G.
#
# Deliberately explicit rather than clever. Each alternative was taken from a
# real anchor in the 2026-H1 corpus, so a future reader can see what the rule
# was built from:
#
#   "PCE(i) of 44.36%"                          -> pce(i)
#   "power output of 127.94 uW cm-2"            -> uW cm  (indoor power scale)
#   "41.60% at 900 lux ... under TL84"          -> lux, tl84
#   "35.54% under indoor LED illumination"      -> indoor, led
#   "12.53% under 1,000 lux"                    -> lux
_INDOOR = re.compile(
    r"\bindoor\b|\blux\b|\blx\b|\bled\b|TL[- ]?84|fluorescen|"
    r"low[- ]light|dim light|artificial light|ambient light|"
    r"\bPCE\s*\(\s*i\s*\)|\bPIPVs?\b|"
    r"[\u00b5u]W\s*[/ ]?\s*cm|microwatt",
    re.I)

# Markers of a one-sun measurement. Used only to REPORT a conflict, never to
# override: an anchor naming both conditions is ambiguous and must fail toward
# excluding, because the number could be either one.
_ONE_SUN = re.compile(
    r"AM\s*1\.5|one[- ]sun|1[- ]sun|standard illumination|"
    r"100\s*mW\s*[/ ]?\s*cm|simulated sunlight|solar simulator",
    re.I)


def _norm(s) -> str:
    return unicodedata.normalize("NFKC", str(s or ""))


def indoor_markers(text: str) -> list[str]:
    """Every non-one-sun marker found, lowercased and deduplicated."""
    t = _norm(text)
    return sorted({m.group(0).lower() for m in _INDOOR.finditer(t)})


def one_sun_markers(text: str) -> list[str]:
    t = _norm(text)
    return sorted({m.group(0).lower() for m in _ONE_SUN.finditer(t)})


def is_one_sun(anchor: str) -> bool:
    """True when the quotation gives no reason to think it is not one-sun.

    Absence of evidence is treated as one-sun, because the overwhelming default
    in this literature is AM1.5G and papers state indoor conditions explicitly
    (it is their selling point). The asymmetry is deliberate and stated here so
    it can be argued with rather than discovered.
    """
    return not indoor_markers(anchor)


def classify(anchor: str) -> str:
    """'indoor' | 'one_sun' | 'ambiguous'."""
    ind = indoor_markers(anchor)
    sun = one_sun_markers(anchor)
    if ind and sun:
        # "35.54% under indoor LED illumination and 20.28% under standard one
        # sun conditions" is one anchor holding TWO measurements. The value
        # bound to this anchor could be either, so it is not comparable.
        return "ambiguous"
    if ind:
        return "indoor"
    return "one_sun"


def comparable_to_one_sun(anchor: str) -> bool:
    """The gate a measured-performance number must pass.

    Fails on 'ambiguous' as well as 'indoor': an anchor reporting both
    conditions cannot tell us which one this value is, and a wrong condition
    on a headline number is the misattribution class of handbook 7.8.
    """
    return classify(anchor) == "one_sun"
