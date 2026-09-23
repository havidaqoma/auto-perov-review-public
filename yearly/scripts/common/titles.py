"""Title cleaning + normalisation (mirrors the daily cron's proven logic, v2 §4.2)."""
from __future__ import annotations

import hashlib
import html
import re

_SUB = re.compile(r"</?(?:sub|sup|i|b|em|strong)[^>]*>", re.I)
_LATEX = re.compile(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^{}]*\})?|\$[^$]*\$")


def clean_title(t: str) -> str:
    if not t:
        return ""
    t = html.unescape(t)
    t = _SUB.sub("", t)          # keep the content: Cs<sub>0.05</sub> -> Cs0.05
    t = _LATEX.sub(" ", t)       # drop LaTeX markup tokens
    return re.sub(r"\s+", " ", t).strip()


def norm(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (t or "").lower())


def title_hash(t: str, chars: int = 80) -> str:
    return hashlib.sha256(norm(t).encode("utf-8")).hexdigest()[:chars]


def containment(a: str, b: str) -> bool:
    """v2 §4.3.2: duplicate iff one clean title contains the other at >30 chars."""
    a, b = (a or "").lower(), (b or "").lower()
    return (len(a) > 30 and a in b) or (len(b) > 30 and b in a)
