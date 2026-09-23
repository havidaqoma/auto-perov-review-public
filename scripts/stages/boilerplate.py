"""Manuscript boilerplate and typography helpers. Version-independent.

Extracted from s18c_build_v3.py on 2026-09-08 so the v3 build could be
archived to OLD/ without breaking v4. s18d imported AFFIL/ACK/AI_DECL/tex_esc/
md_esc/expand_abbrev directly from the v3 module, which meant a superseded
build stage had to stay on the live path purely to hold shared constants.

Everything here was tuned against real rendered-PDF defects and must not be
paraphrased:
  - the affiliation block is the author's, verified against config/author_manifest
  - ABBREV is ordered LONGEST-KEY-FIRST so a match on TRPL is not consumed by PL
  - tex_esc/md_esc escape sets were fixed by inspecting broken LaTeX output
"""
from __future__ import annotations

import re

AFFIL = [
    "School of Energy and Chemical Engineering, Xiamen University Malaysia, "
    "Selangor Darul Ehsan 43900, Malaysia",
    "Kelip-kelip! Center of Excellence for Light Enabling Technologies, School "
    "of Energy and Chemical Engineering, Xiamen University Malaysia, Selangor "
    "Darul Ehsan 43900, Malaysia",
    "Centre of Excellence for Green and Advanced Technologies in Efficient "
    "Separations (GATES), School of Energy and Chemical Engineering, Xiamen "
    "University Malaysia, Selangor Darul Ehsan 43900, Malaysia",
    "Gulei Innovation Institute, Xiamen University, Zhangzhou 363200, China",
]

# Corresponding-author note. Havid asked (2026-09-09) for an asterisk on his
# name in the author line and the marker explained just below the affiliation
# list. The asterisk is NOT an affiliation number, so it is appended after the
# numeric superscripts and explained by its own line inside the same centred
# minipage -- putting it in a page footnote would separate the marker from the
# block a reader scans, and putting it after the date would read as a caption.
CORRESP_EMAIL = "havidaqoma.khoiruddin@xmu.edu.my"
CORRESP_NOTE = "*Corresponding author. Email: " + CORRESP_EMAIL

ACK = ("The authors would like to acknowledge the financial support from Xiamen "
       "University Malaysia through the Xiamen University Malaysia Research Fund "
       "(XMUMRF/2022-C10/IENG/0046), and from National Natural Science Foundation "
       "of China (Ref. No.: 52503390). The authors would also like to thank "
       "Anthropic for support through the Anthropic AI for Science program.")

AI_DECL = (
    "This manuscript was prepared as part of our Research Project for making a "
    "reliable Autonomous Researcher Agent. The agent executed the monthly review "
    "pipeline without human intervention: it harvested the indexed literature for "
    "the month through the OpenAlex, Semantic Scholar, Crossref and arXiv "
    "interfaces, applied a deterministic topical filter, ranked and selected the "
    "papers read closely, extracted every quantitative claim into a structured "
    "record binding each number to a verbatim quotation from that paper's own "
    "abstract, computed the statistics and figures from those records, and drafted "
    "this text from the resulting evidence briefs. Literature harvesting, "
    "selection, statistics, figures and gate checking are deterministic scripts "
    "rather than model output. Structured extraction used {extractor}; the prose "
    "was written by {writer}; independent review used {reviewer}. No figure is a "
    "model-generated image: every panel is plotted directly from the extracted "
    "records. Every quantitative statement in the main text resolves to the "
    "machine-generated statistics file shipped as Supplementary Information, and "
    "every citation resolves to a record carrying its source quotation. The author "
    "reviewed and edited the content, verified the selection, and takes full "
    "responsibility for the content of the published article."
)

# Q62: expand at first use. Order matters -- longer keys first so that a match
# on "TRPL" is not consumed by "PL".
ABBREV = [
    ("TRPL", "time-resolved photoluminescence"),
    ("ISOS", "International Summit on Organic Photovoltaic Stability"),
    ("MPPT", "maximum power point tracking"),
    ("PSCs", "perovskite solar cells"),
    ("SAMs", "self-assembled monolayers"),
    ("PCE", "power conversion efficiency"),
    ("PSC", "perovskite solar cell"),
    ("SAM", "self-assembled monolayer"),
    ("ETL", "electron-transport layer"),
    ("HTL", "hole-transport layer"),
    ("TCO", "transparent conducting oxide"),
    ("ALD", "atomic layer deposition"),
    ("DFT", "density functional theory"),
    ("XRD", "X-ray diffraction"),
    ("WBG", "wide-bandgap"),
    ("R2R", "roll-to-roll"),
    ("Voc", "open-circuit voltage"),
    ("Jsc", "short-circuit current density"),
    ("PL", "photoluminescence"),
    ("FF", "fill factor"),
]


def tex_esc(t: str) -> str:
    t = re.sub(r"<[^>]+>", "", t or "")
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"),
                 ("$", r"\$"), ("#", r"\#"), ("_", r"\_"),
                 ("{", r"\{"), ("}", r"\}"), ("~", r"\textasciitilde{}"),
                 ("^", r"\textasciicircum{}")):
        t = t.replace(a, b)
    return t.strip()


def md_esc(t: str) -> str:
    t = re.sub(r"<[^>]+>", "", t or "")
    return t.replace("&", r"\&").replace("%", r"\%").replace("#", r"\#").strip()


def expand_abbrev(text: str) -> tuple[str, list]:
    """Deterministic first-use expansion (Q62).

    A bare abbreviation on first mention is replaced by
    "expansion (ABBREV)". Later mentions are untouched. Skips any occurrence
    already inside an expansion, and skips citation markers.
    """
    done_list = []
    for ab, full in ABBREV:
        # already expanded somewhere by the writer?
        if re.search(rf"{re.escape(full)}\s*\({re.escape(ab)}s?\)", text, re.I):
            continue
        m = re.search(rf"(?<![A-Za-z0-9\-]){re.escape(ab)}(?![A-Za-z0-9])", text)
        if not m:
            continue
        # do not touch an occurrence that is already preceded by its expansion
        pre = text[max(0, m.start() - 90):m.start()].lower()
        if full.lower() in pre:
            continue
        text = text[:m.start()] + f"{full} ({ab})" + text[m.end():]
        done_list.append(ab)
    return text, done_list


