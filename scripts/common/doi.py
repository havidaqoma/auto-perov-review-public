"""DOI normalisation: bare, lowercased, no URL prefix or trailing punctuation."""
from __future__ import annotations

import re

_URL = re.compile(r"^(?:https?://)?(?:dx\.)?doi\.org/", re.I)
_TRAIL = re.compile(r"[.\s]+$")


def norm_doi(d: str) -> str:
    if not d:
        return ""
    d = _URL.sub("", d.strip())
    d = _TRAIL.sub("", d)
    return d.lower()
