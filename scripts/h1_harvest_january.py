"""January 2026 harvest with a corrected date window.

WHY THIS FILE EXISTS
--------------------
OpenAlex stamps 2026-01-01 on works indexed with year-only precision. For the
scope filter, January 2026 returns:

    2026-01-01 .. 2026-01-01   ->  823
    2026-01-02 .. 2026-01-31   ->  488
    -------------------------------------
    full month                    1311   <- fails the [250,1200] count band

The 823 are real papers in real venues (EES, Nature Photonics, Science), so
they are not junk to be filtered on relevance. But their true publication month
cannot be established from the record, and an issue titled "January-June 2026"
may not assert a month it cannot verify. Full reasoning and the SI limitation
text: docs/H1_JANUARY_DATE_DECISION.md

HOW IT AVOIDS TOUCHING THE MONTHLY PATH
---------------------------------------
Havid's constraint (2026-09-09): do not disturb the monthly workflow.

s01_harvest.py does `from stages.util import month_bounds`, which binds the
name into the s01 module namespace. Rebinding it HERE, in this script's
process only, changes the window for this one run without editing a single
byte of s01_harvest.py or util.py. The monthly chain imports neither this file
nor anything it defines.

The override is asserted, not assumed: if s01 ever stops using month_bounds,
the assertion below fails loudly rather than silently harvesting the wrong
window (the handbook's 7.6 #6 class -- a verifier that passed by examining a
different artifact).
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from stages import s01_harvest as s01  # noqa: E402

MONTH = "2026-01"
WINDOW = ("2026-01-02", "2026-01-31")


def main() -> int:
    # Fail loudly if the assumption behind the monkeypatch ever breaks.
    assert hasattr(s01, "month_bounds"), (
        "s01_harvest no longer binds month_bounds; this override is dead code "
        "and January would silently harvest the wrong window.")
    original = s01.month_bounds(MONTH)
    assert original == ("2026-01-01", "2026-01-31"), (
        f"unexpected default window for {MONTH}: {original}")

    s01.month_bounds = lambda m: WINDOW if m == MONTH else original
    print(f"[h1-jan] window overridden: {original} -> {WINDOW}", flush=True)
    print("[h1-jan] 823 works dated exactly 2026-01-01 are EXCLUDED "
          "(year-only indexing placeholder); see "
          "docs/H1_JANUARY_DATE_DECISION.md", flush=True)

    meta = s01.harvest(MONTH)
    n = (meta or {}).get("openalex_count")
    print(f"[h1-jan] openalex_count={n}", flush=True)
    if not n:
        print("[h1-jan] FAIL: zero is a bug until proven otherwise (7.1)")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
