"""Drift audit: compare a baseline snapshot of prose files against the live ones.

Generalised from the hardcoded `basecheck` version. A baseline is just a
directory of same-named .md files, so it works for any edition: git-extracted
originals, a v4 directory being compared against its v5 copy, or a manual
backup.

    python scripts/drift_audit.py BASELINE_DIR LIVE_DIR [name ...]

With no explicit names every .md present in BOTH directories is compared.

Counter semantics throughout. A rewrite that duplicates a citation or a number
must not pass: the citation total is gated, and a duplicated number is a
changed claim.

Both citation dialects are tracked, because the pipeline uses different ones at
different stages:
    [@10.1038/xxxx]                          in the draft caches
    \\href{https://doi.org/10.1038/xxxx}{7}   in assembled build output
Measured on manuscript/2026-07_v5/manuscript_v5.md: 0 of the first form, 79 of
the second. An auditor that knew only the [@...] form would verify NOTHING
there and report success.
"""
from __future__ import annotations

import collections
import pathlib
import re
import sys

CITE = re.compile(r"\[@([^\]\s,;]+)")
HREF = re.compile(r"\\href\{(?:https?://doi\.org/)?([^}]+)\}\{(\d+)\}")
NUM = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?\s*%?")
TOK = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
QTY = re.compile(r"\\qty\{([^}]*)\}\{([^}]*)\}")
HEDGE = re.compile(
    r"\b(?:may|might|could|suggests?|suggesting|appears?|seems?|likely|"
    r"approximately|about|roughly|at most|at least|no more than|lower bound|"
    r"upper bound|only|merely|not|never|cannot|unverified|uncertain|"
    r"limitation|caveat|assumed|estimated)\b", re.I)
DASH = re.compile(r"[\u2013\u2014]")
# Claim-strength verbs. Moving a result between these registers is invisible to
# every other check: the numbers, citations and units all survive untouched.
ASSERT_V = re.compile(r"\b(?:demonstrat\w+|reveal\w+|show\w+|prov\w+|"
                      r"establish\w+|confirm\w+)\b", re.I)
HEDGE_V = re.compile(r"\b(?:suggest\w+|indicat\w+|imply|implies|appear\w+)\b", re.I)


def cites_of(text: str) -> collections.Counter:
    return collections.Counter(CITE.findall(text)
                               + [d for d, _ in HREF.findall(text)])


def counts(rx, text, strip=False) -> collections.Counter:
    found = rx.findall(text)
    if found and isinstance(found[0], tuple):
        found = ["|".join(t) for t in found]
    if strip:
        found = [x.strip() for x in found]
    return collections.Counter(found)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    base, live = pathlib.Path(argv[0]), pathlib.Path(argv[1])
    names = argv[2:]
    if not names:
        names = sorted(p.name for p in base.glob("*.md")
                       if (live / p.name).exists())
    if not names:
        print(f"!! no common .md files between {base} and {live}")
        return 2

    defects = 0
    for n in names:
        b, l = base / n, live / n
        if not b.exists() or not l.exists():
            print(f"FAIL {n}: missing in {'baseline' if not b.exists() else 'live'}")
            defects += 1
            continue
        o = b.read_text(encoding="utf-8", errors="replace")
        c = l.read_text(encoding="utf-8", errors="replace")

        checks = [("num", counts(NUM, o, True), counts(NUM, c, True)),
                  ("cite", cites_of(o), cites_of(c)),
                  ("citenum", counts(HREF, o), counts(HREF, c)),
                  ("tok", counts(TOK, o), counts(TOK, c)),
                  ("qty", counts(QTY, o), counts(QTY, c))]
        for lab, co, cc in checks:
            if co != cc:
                lost = {k: co[k] - cc.get(k, 0) for k in co if cc.get(k, 0) < co[k]}
                gain = {k: cc[k] - co.get(k, 0) for k in cc if co.get(k, 0) < cc[k]}
                print(f"  DRIFT {n:22s} {lab:8s} lost={lost} gain={gain}")
                defects += 1

        notes = []
        dh = len(HEDGE.findall(c)) - len(HEDGE.findall(o))
        if dh:
            notes.append(f"hedge {dh:+d}"
                         + (" (claim may be STRONGER)" if dh < 0
                            else " (claim may be WEAKER)"))
        da = len(ASSERT_V.findall(c)) - len(ASSERT_V.findall(o))
        dv = len(HEDGE_V.findall(c)) - len(HEDGE_V.findall(o))
        if da or dv:
            notes.append(f"assert-verbs {da:+d}, hedge-verbs {dv:+d}")
        # Dashes must be counted as a DELTA, not as absolute presence. The
        # shipped 2026-07 v4 manuscript already contains 10 en-dashes: 4 in
        # body numeric ranges ("2-8% Cs") and 6 inside reference titles
        # ("Sn-Pb", "perovskite-organic"). Flagging those as defects of a
        # rewrite blamed the editor for text they never touched, and a check
        # that fires on untouched input is a check that gets ignored.
        nd = len(DASH.findall(c)) - len(DASH.findall(o))
        if nd > 0:
            notes.append(f"EN/EM DASH introduced x{nd}")
            defects += 1
        elif nd < 0:
            notes.append(f"en/em dashes removed x{-nd}")
        dw = len(c.split()) - len(o.split())
        pct = 100.0 * dw / max(len(o.split()), 1)
        if abs(pct) > 8:
            notes.append(f"WORDS {dw:+d} ({pct:+.1f}%) OUTSIDE +/-8%")
            defects += 1
        status = "ok  " if not any("DRIFT" in x for x in notes) else "note"
        print(f"  {status} {n:22s} words {len(o.split()):5d}->{len(c.split()):<5d} "
              f"({pct:+.1f}%)" + ("  | " + "; ".join(notes) if notes else ""))

    print(f"\nTRUE DEFECTS: {defects}")
    return 1 if defects else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
