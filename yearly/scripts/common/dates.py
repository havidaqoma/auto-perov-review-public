"""Canonical calendar-month helpers (Q16=c)."""
from __future__ import annotations

import calendar


BAND = (250, 1200)  # v3 §B2.3 measured band for the canonical PV gate


def month_window(ym: str) -> tuple[str, str]:
    """'2026-08' -> ('2026-08-01', '2026-08-31') inclusive."""
    year, month = (int(x) for x in ym.split("-"))
    last = calendar.monthrange(year, month)[1]
    return f"{ym}-01", f"{ym}-{last:02d}"


def in_band(n: int) -> bool:
    return BAND[0] <= n <= BAND[1]
