"""Text hygiene before BibTeX/CSV output (v2 §4.2 BibTeX pass)."""
from __future__ import annotations

import html


def entity_collapse(s: str) -> str:
    return html.unescape(s or "")


def bibtex_escape(s: str) -> str:
    """Escape & % # for .bib title/author fields. Idempotent-ish and safe for
    composition strings like Cs0.05FA0.85MA0.10Pb(I0.6Br0.4)3 (braces untouched)."""
    s = entity_collapse(s or "")
    s = s.replace("\\&", "&").replace("\\%", "%").replace("\\#", "#")  # de-escape first
    s = s.replace("&", "\\&").replace("%", "\\%").replace("#", "\\#")
    return s
