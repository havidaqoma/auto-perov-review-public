"""Deterministic notation: units, ions and formulae as siunitx / mhchem.

Version 2 (2026-09-08). Havid asked for consistency of format, so notation is
now expressed with the packages the field actually uses -- \\qty{}{} from
siunitx and \\ce{} from mhchem -- instead of a hand-rolled $^2$ regex table.

Both packages were verified COMPILING under tectonic (it auto-downloads
mhchem.sty and chemgreek.sty from its bundle) and verified RENDERING at PDF
span level before this migration:

    \\qty{1.3e-3}{\\centi\\meter\\squared\\per\\volt\\per\\second}
        -> 1.3 x 10^-3 cm^2 V^-1 s^-1, every exponent AND every minus raised
    \\ce{[PbI4]^2-}
        -> subscript 4 BELOW the baseline, charge 2- ABOVE it, in one token

That second case is the argument for the migration in one line: a regex table
cannot put two scripts in opposite directions inside one formula.

Why version 1 failed, measured on the shipped August v4 PDF:

1. The writer emits Unicode minus (U+2212) in "V-1"; the rules matched ASCII
   hyphen. Same glyph to a reader, different codepoint, silent miss.
2. "1.3 x 10-3 cm2 V-1 s-1" is ONE quantity with a coefficient, a power of
   ten and a compound per-chain. Regex-per-token cannot express that.
   siunitx exists to express exactly that.
3. "[PbI4]2-", "Cs2AgInCl6" and "NH4SCN" were in no table. \\ce{} handles them
   by grammar rather than enumeration.
4. The v1 gate shared v1's ASCII blindness and reported PASS on the broken
   line. Ninth instance of handbook 7.3: a gate that cannot fail.

Per handbook 0.1 the writer still emits plain text and this module emits the
LaTeX. Nobody hand-writes \\qty or \\ce in prose, so nothing can drift.

Pass order inside format_notation():
  1 normalise  U+2212 -> '-', superscript digits -> ASCII, ' x 10' spacing
  2 mask       hyperlinks, URLs, DOIs, citation markers, existing math and
               existing \\qty/\\ce spans (idempotence), and defined terms
  3 convert    compound quantity -> bracket ion -> cation -> formula table
  4 unmask

Bare percentages are DELIBERATELY left alone. "27.12%" is already correct and
\\qty{27.12}{\\percent} would insert a thin space, changing hundreds of
already-accepted appearances. Consistency means the broken classes become
correct, not that every token is rewritten.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------- 1. masks
# Balanced-brace matcher for one or two argument groups, so an existing
# \qty{1.3e-3}{\centi\meter\squared} is protected whole and a second pass
# cannot nest it. This is what makes formatting idempotent.
_ARG = r"\{(?:[^{}]|\{[^{}]*\})*\}"
_PROTECT = [
    rf"\\(?:href|qty|qtyrange|ce|num|si|SI|unit){_ARG}(?:{_ARG})?",
    r"https?://\S+",
    r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+",     # DOIs
    r"\[@[^\]\s]+\]",                           # unresolved [@work_key]
    r"\$[^$]*\$",                               # existing inline math
    r"`[^`]*`",
]

# Domain vocabulary that LOOKS like notation but is not. Longest first so
# "C60-PA" masks before a bare "C60" rule could fire on its prefix.
KEEP_LITERAL = [
    r"\bC60-PA\b", r"\bC70-PA\b",
    r"\bISOS-[A-Z]-\d\b", r"\bISOS-[A-Z]\b", r"\bISOS\b",
    r"\bT\d{2}\b",                              # T80, T90
    r"\bp-i-n\b", r"\bn-i-p\b",
    r"\b[24]T\b", r"\bR2R\b",
    r"\bTOPCon\b", r"\bPERC\b", r"\bIBC\b",
    r"\bSC4A\b", r"\bm-FBC\b", r"\bMASCN\b", r"\bTTMB\b", r"\b2MAP\b",
    r"\bDMF\b", r"\bDMSO\b", r"\bDMF:DMSO\b",
    r"\bI-V\b", r"\bJ-V\b",
    r"\bSAMs?\b", r"\bPCEs?\b", r"\bPSCs?\b", r"\bETLs?\b", r"\bHTLs?\b",
    r"\bVoc\b", r"\bJsc\b", r"\bFF\b", r"\bMPPT\b", r"\bTRPL\b", r"\bPL\b",
    r"\bXRD\b", r"\bALD\b", r"\bDFT\b", r"\bTCO\b", r"\bWBG\b",
]

_SUP = str.maketrans("\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077"
                     "\u2078\u2079\u207b", "0123456789-")


def _normalise(text: str) -> str:
    """Fold the writer's typographic characters into one alphabet.

    THE fix for the v1 miss: the converter and the gate must both see the
    characters the writer actually types, not the ones the author of the
    regex imagined.
    """
    text = text.replace("\u2212", "-")                    # minus sign
    text = text.translate(_SUP)                            # 10^-3 written raw
    text = re.sub(r"(\d)\s*[\u00d7\u2715]\s*10", r"\1 x 10", text)
    return text


# ------------------------------------------------------------- 2. units
# Longest key first inside the alternation, or "m" would shadow "mA"/"mV".
_UNITS = {
    "cm": r"\centi\meter", "mm": r"\milli\meter", "nm": r"\nano\meter",
    "um": r"\micro\meter", "\u00b5m": r"\micro\meter", "km": r"\kilo\meter",
    "m": r"\meter",
    "mV": r"\milli\volt", "kV": r"\kilo\volt", "V": r"\volt",
    "mA": r"\milli\ampere", "uA": r"\micro\ampere", "A": r"\ampere",
    "mW": r"\milli\watt", "kW": r"\kilo\watt", "W": r"\watt",
    "meV": r"\milli\electronvolt", "eV": r"\electronvolt",
    "ms": r"\milli\second", "us": r"\micro\second", "ns": r"\nano\second",
    "ps": r"\pico\second", "min": r"\minute", "s": r"\second", "h": r"\hour",
    "K": r"\kelvin", "Hz": r"\hertz", "kHz": r"\kilo\hertz",
    "mg": r"\milli\gram", "kg": r"\kilo\gram", "g": r"\gram",
    "L": r"\liter", "mL": r"\milli\liter",
    "Pa": r"\pascal", "kPa": r"\kilo\pascal",
    # Energy in joules. Its absence shipped a flat "J m-2" in July 2026:
    # the writer reported an interfacial fracture energy of 0.94 J m-2, and
    # because "J" was unknown the whole unit RUN failed to match, so G9a
    # reported the trailing "m-2" as flat. A missing unit does not degrade
    # gracefully -- it silently drops every unit beside it in the run.
    "J": r"\joule", "mJ": r"\milli\joule", "kJ": r"\kilo\joule",
    "uJ": r"\micro\joule", "\u00b5J": r"\micro\joule",
    # Microwatts, added 2026-09-10. Same failure as "J" above, one literature
    # subfield later: an indoor-photovoltaics paper reported "127.94 uW cm-2"
    # for its absolute power output, "uW"/"\u00b5W" were unknown, so the unit RUN
    # failed to match and G9a reported the trailing "cm-2" as flat on the
    # rendered page. Indoor PV always quotes power in uW/cm2 because the
    # incident flux is ~1000x lower than one sun, so this unit arrives with the
    # subfield, not by accident.
    #
    # BOTH spellings are required: U+00B5 MICRO SIGN and U+03BC GREEK SMALL
    # LETTER MU are different codepoints that render identically, and the
    # writer emits whichever the source paper used. This is the 4.4 rule 1
    # lesson (normalise before matching) applied to a unit prefix.
    "uW": r"\micro\watt", "\u00b5W": r"\micro\watt", "\u03bcW": r"\micro\watt",
    "uV": r"\micro\volt", "\u00b5V": r"\micro\volt",
}
_UALT = "|".join(sorted((re.escape(u) for u in _UNITS), key=len, reverse=True))

# one unit token with an optional exponent: cm2, V-1, s-1, m-3
_UTOK = re.compile(rf"({_UALT})(-?[1-9])?")


def _unit_expr(tok: str, exp: str | None) -> str:
    """siunitx fragment for one unit token.

    Positive exponent:  cm2  -> \\centi\\meter\\squared
    Negative exponent:  V-1  -> \\per\\volt
                        cm-2 -> \\per\\centi\\meter\\squared
    \\squared follows the unit it modifies; \\per precedes the whole group.
    """
    base = _UNITS[tok]
    if not exp:
        return base
    neg = exp.startswith("-")
    d = exp.lstrip("-")
    suffix = {"1": "", "2": r"\squared", "3": r"\cubed"}.get(d, "")
    if not suffix and d != "1":
        suffix = rf"\tothe{{{d}}}"
    return (r"\per" if neg else "") + base + suffix


# value, optionally with a power of ten: 61.2 | 1.3 x 10-3 | 1 x 1015 | 1.6e17
#
# The e-notation alternative is not cosmetic. June 2026's writer emitted
# "1.6e17 cm-3" instead of "1.6 x 1017 cm-3", so _QTY never matched, the unit
# was left flat, and G9a reported "unit flat inverse: cm-3" on the rendered
# page. The converter had silently handled only one of the two ways a writer
# can spell a power of ten. Both are now accepted, so the unit is typeset
# either way.
_VAL = r"\d+(?:\.\d+)?(?:\s*x\s*10-?\d+|[eE][-\u2212+]?\d+)?"
_UNITRUN = (rf"(?:{_UALT})(?:-?[1-9])?"
            rf"(?:\s+(?:{_UALT})(?:-?[1-9])?)*")
_QTY = re.compile(rf"(?<![\w.\\]) ?({_VAL})\s+({_UNITRUN})(?![\w\-/])")


def _fmt_value(v: str) -> str:
    """Normalise a value to the single e-notation form siunitx expects.

    '1.3 x 10-3' -> '1.3e-3'   (siunitx renders the raised minus, which is
                                precisely what the flat-text version got wrong)
    '1.6E+17'    -> '1.6e17'   (already e-notation, only the spelling varies;
                                siunitx rejects a '+' exponent, so strip it)
    """
    v = v.strip()
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*x\s*10(-?)(\d+)", v)
    if m:
        return f"{m.group(1)}e{m.group(2) or ''}{m.group(3)}"
    m = re.fullmatch(r"(\d+(?:\.\d+)?)[eE]([-\u2212+]?)(\d+)", v)
    if m:
        sign = "-" if m.group(2) in ("-", "\u2212") else ""
        return f"{m.group(1)}e{sign}{m.group(3)}"
    return v


def _qty_sub(m: re.Match) -> str:
    val = _fmt_value(m.group(1))
    parts = [_unit_expr(t.group(1), t.group(2))
             for t in _UTOK.finditer(re.sub(r"\s+", " ", m.group(2)))
             if t.group(1)]
    if not parts:
        return m.group(0)
    lead = " " if m.group(0).startswith(" ") else ""
    return lead + r"\qty{" + val + "}{" + "".join(parts) + "}"


# ------------------------------------------------------------- 3. species
_METALS = ("Na|K|Cs|Rb|Li|Mg|Ca|Sr|Ba|Zn|Cd|Pb|Sn|Cu|Ag|Au|Ni|Co|Fe|Mn|"
           "Ti|Bi|Sb|In|Ga|Al|Ge|Eu|Yb")
_CATION = re.compile(rf"\b({_METALS})([2-9]?)\+(?![\w+])")
_BRACKET = re.compile(r"\[([A-Z][A-Za-z0-9]*)\]([2-9]?)([-+])(?![\w])")

_FORMULAE = {
    "PbI2": "PbI2", "PbBr2": "PbBr2", "PbCl2": "PbCl2", "SnI2": "SnI2",
    "SnF2": "SnF2", "SnO2": "SnO2", "TiO2": "TiO2", "SiO2": "SiO2",
    "ZnO": "ZnO", "Al2O3": "Al2O3", "In2S3": "In2S3",
    "NiOx": "NiO_x", "TiOx": "TiO_x", "MoOx": "MoO_x", "WOx": "WO_x",
    "H2O": "H2O", "CO2": "CO2", "O2": "O2", "N2": "N2", "H2": "H2",
    "NH4SCN": "NH4SCN", "NH4Cl": "NH4Cl", "NH4I": "NH4I", "NH4": "NH4",
    "CH3NH3PbI3": "CH3NH3PbI3", "CH3NH3": "CH3NH3", "CH3NH2": "CH3NH2",
    "Cs2AgInCl6": "Cs2AgInCl6", "Cs2AgBiBr6": "Cs2AgBiBr6",
    "Cs2CO3": "Cs2CO3", "CsPbI3": "CsPbI3", "CsPbBr3": "CsPbBr3",
    "FAPbI3": "FAPbI3", "MAPbI3": "MAPbI3", "MAPbBr3": "MAPbBr3",
    "C60": "C60", "C70": "C70", "PbSCN2": "Pb(SCN)2",
    "KSCN": "KSCN", "NaCl": "NaCl", "KI": "KI", "CsI": "CsI",
}
_FORM_RX = re.compile(r"(?<![\w\\])(" +
                      "|".join(sorted(map(re.escape, _FORMULAE),
                                      key=len, reverse=True)) +
                      r")(?![\w])")


def _mask(text: str) -> tuple[str, list[str]]:
    store: list[str] = []

    def sub(m: re.Match) -> str:
        store.append(m.group(0))
        return f"\x00{len(store) - 1}\x00"

    for pat in _PROTECT + KEEP_LITERAL:
        text = re.sub(pat, sub, text)
    return text, store


def _unmask(text: str, store: list[str]) -> str:
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r"\x00(\d+)\x00",
                      lambda m: store[int(m.group(1))], text)
    return text


def format_notation(text: str) -> tuple[str, dict]:
    """Convert plain-text notation to siunitx / mhchem. Returns (text, counts)."""
    counts: dict[str, int] = {}
    masked, store = _mask(_normalise(text))

    def run(label: str, rx, rep, s: str) -> str:
        s, n = rx.subn(rep, s)
        if n:
            counts[label] = counts.get(label, 0) + n
        return s

    # most specific first: a quantity may contain digits a formula rule would
    # otherwise claim
    masked = run("quantity", _QTY, _qty_sub, masked)
    masked = run("bracket-ion", _BRACKET,
                 lambda m: r"\ce{[" + m.group(1) + "]^"
                           + (m.group(2) or "") + m.group(3) + "}", masked)
    masked = run("cation", _CATION,
                 lambda m: r"\ce{" + m.group(1)
                           + ("^" + m.group(2) + "+" if m.group(2) else "+")
                           + "}", masked)
    masked = run("formula", _FORM_RX,
                 lambda m: r"\ce{" + _FORMULAE[m.group(1)] + "}", masked)

    return _unmask(masked, store), counts


# ------------------------------------------------------------------- gate
# Both alphabets are covered. v1's ASCII-only check is what reported PASS on
# the shipped Unicode-minus mobility line.
_DEFECTS = [
    ("unit flat exponent", r"\b(?:cm|mm|nm|um|\u00b5m|m|km)[23]\b"),
    ("unit flat inverse",
     r"\b(?:cm|mm|nm|m|s|h|V|A|K|W|eV|Hz|mA|mV)[-\u2212][1-9]\b"),
    # The minus is REQUIRED, not optional. With `[-\u2212]?` this matched
    # "100", "101", "102" ... as 10 followed by a digit, so the gate failed
    # the whole manuscript on ordinary numbers (page counts, paper counts,
    # temperatures). Tenth instance of 7.3: the artifact was right, the check
    # was wrong. A flat power of ten only exists when a sign is present.
    ("power of ten flat", r"\b10[-\u2212]\d\b"),
    ("flat cation", rf"\b(?:{_METALS})[2-9]?\+(?![\w+])"),
    ("flat bracket ion", r"\[[A-Z][A-Za-z0-9]*\][2-9]?[-\u2212+](?![\w])"),
    ("flat formula",
     r"(?<![\w\\])(?:PbI2|PbBr2|SnI2|SnO2|TiO2|SiO2|NiOx|TiOx|MoOx|H2O|CO2"
     r"|NH4SCN|NH4Cl|CH3NH3|Cs2AgInCl6|Cs2AgBiBr6|Cs2CO3|FAPbI3|MAPbI3"
     r"|CsPbI3|CsPbBr3|C60|C70)(?![\w])"),
    ("typographic times outside qty", r"\d\s*\u00d7\s*10"),
]

# Reported for human judgement, never auto-converted: "I-V curve" is a real
# term and so is the iodide ion. A silent wrong guess in a formula is worse
# than a flagged one. Inside [brackets] the ambiguity disappears, which is why
# bracket ions ARE converted.
_AMBIGUOUS = [
    ("bare anion", r"(?<=[\s(])(?:I|Br|Cl|F|OH)[-\u2212](?=[\s,.;)])"),
]


def check_notation(text: str) -> dict:
    masked, _ = _mask(_normalise(text))
    defects, ambiguous = {}, {}
    for label, pat in _DEFECTS:
        hits = re.findall(pat, masked)
        if hits:
            defects[label] = sorted({str(h) for h in hits})[:8]
    for label, pat in _AMBIGUOUS:
        hits = re.findall(pat, masked)
        if hits:
            ambiguous[label] = sorted({str(h) for h in hits})[:8]
    return {"defects": defects, "ambiguous": ambiguous}


# Every case below is a defect Havid found in a shipped PDF or a near-miss
# that shaped a rule. Tests assert each pair.
KNOWN_FIXES = [
    # the electron-mobility line, the defect that triggered the migration
    ("electron mobilities up to 1.3 \u00d7 10\u22123 cm2 V\u22121 s\u22121",
     r"electron mobilities up to \qty{1.3e-3}{\centi\meter\squared\per\volt\per\second}"),
    # the ASCII spelling must give the IDENTICAL result: one alphabet
    ("mobility of 12 cm2 V-1 s-1",
     r"mobility of \qty{12}{\centi\meter\squared\per\volt\per\second}"),
    ("aperture area of 61.2 cm2.",
     r"aperture area of \qty{61.2}{\centi\meter\squared}."),
    ("a 0.08 cm2 cell", r"a \qty{0.08}{\centi\meter\squared} cell"),
    ("current density of 24 mA cm-2",
     r"current density of \qty{24}{\milli\ampere\per\centi\meter\squared}"),
    ("tracked for 2125 h under one sun",
     r"tracked for \qty{2125}{\hour} under one sun"),
    ("Na+ migration", r"\ce{Na+} migration"),
    ("Pb2+ and Sn2+ oxidation", r"\ce{Pb^2+} and \ce{Sn^2+} oxidation"),
    ("inorganic [PbI4]2- slabs", r"inorganic \ce{[PbI4]^2-} slabs"),
    ("octahedral [SnI6]4- units", r"octahedral \ce{[SnI6]^4-} units"),
    ("residual PbI2 at the interface", r"residual \ce{PbI2} at the interface"),
    ("Cs2AgInCl6 double perovskite", r"\ce{Cs2AgInCl6} double perovskite"),
    ("NH4SCN treatment", r"\ce{NH4SCN} treatment"),
    ("SnO2 electron transport", r"\ce{SnO2} electron transport"),
    ("NiOx hole contact", r"\ce{NiO_x} hole contact"),
    ("anchoring C60 on the surface", r"anchoring \ce{C60} on the surface"),
]

KNOWN_UNTOUCHED = [
    "a T80 of 1400 h under ISOS-L-1" if False else "a T80 under ISOS-L-1",
    "the 2T tandem on TOPCon silicon",
    "p-i-n and n-i-p architectures",
    r"already correct: \qty{61.2}{\centi\meter\squared} aperture",
    r"already correct: \ce{[PbI4]^2-} slabs",
    "see https://doi.org/10.1002/adma.74461 for detail",
    "the DOI 10.1038/s41467-026-76266-0 resolves",
    r"\href{https://doi.org/10.1/x}{[12]}",
    "an I-V curve measured under bias",
    "C60-PA anchored on the oxide",
    "SC4A and m-FBC additives",
    "an efficiency of 27.12% certified",
    "Voc, Jsc and FF triplets",
]
