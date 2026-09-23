"""Meaning-level review of the July/August v5 style pass.

The drift audit already proved numbers, citations, citation numbers, tokens
and \qty units are byte-stable. That is necessary and NOT sufficient: a style
pass can hold every one of those and still move what the paper CLAIMS, or
wreck the document skeleton the build depends on. This checks the things the
token ledger cannot see.

Written as a file because a trailing backslash cannot end a Python raw string,
so the %LOCALAPPDATA%\Temp\ path kept failing when inlined into `python -c`.
"""
from __future__ import annotations

import collections
import os
import pathlib
import re

TEMP = pathlib.Path(os.environ["LOCALAPPDATA"]) / "Temp"
EDITIONS = [("2026-07", TEMP / "v4base_jul"), ("2026-08", TEMP / "v4base_aug")]
FILES = ["manuscript_v5.md", "supplementary_v5.md"]

# Verbs that assert vs verbs that hedge. Moving a result between these
# registers is invisible to every number and citation check.
ASSERT_V = re.compile(r"\b(?:demonstrat\w+|reveal\w+|show\w+|prov\w+|"
                      r"establish\w+|confirm\w+)\b", re.I)
HEDGE_V = re.compile(r"\b(?:suggest\w+|indicat\w+|imply|implies|appear\w+)\b", re.I)
CALIB = re.compile(r"\b(?:only|merely|remains?|at most|at least|approximately|"
                   r"may|might|could|unverified|uncertified|cannot|never|"
                   r"lower bound)\b", re.I)
HEADING = re.compile(r"^#{1,6} .*$", re.M)


def report(label, o, c):
    ao, ac = len(ASSERT_V.findall(o)), len(ASSERT_V.findall(c))
    ho, hc = len(HEDGE_V.findall(o)), len(HEDGE_V.findall(c))
    co, cc = len(CALIB.findall(o)), len(CALIB.findall(c))
    flag = ""
    if ac < ao and hc > ho:
        flag = "   <-- ASSERTION DEMOTED TO HEDGE"
    elif ac > ao and hc < ho:
        flag = "   <-- HEDGE PROMOTED TO ASSERTION"
    print(f"  {label:34s} assert {ao:3d}->{ac:<3d} hedgeverb {ho:3d}->{hc:<3d} "
          f"calib {co:3d}->{cc:<3d}{flag}")
    return bool(flag)


def main() -> int:
    problems = 0
    print("=== CLAIM STRENGTH (verbs + calibration vocabulary) ===")
    for mon, base in EDITIONS:
        for f in FILES:
            o = (base / f).read_text(encoding="utf-8")
            c = (pathlib.Path(f"manuscript/{mon}_v5") / f).read_text(encoding="utf-8")
            problems += report(f"{mon} {f}", o, c)

    print("\n=== DOCUMENT SKELETON (build depends on these) ===")
    for mon, base in EDITIONS:
        for f in FILES:
            o = (base / f).read_text(encoding="utf-8")
            c = (pathlib.Path(f"manuscript/{mon}_v5") / f).read_text(encoding="utf-8")
            ho, hc = HEADING.findall(o), HEADING.findall(c)
            fo, fc = o.count(r"\begin{figure}"), c.count(r"\begin{figure}")
            to = [l for l in o.splitlines() if "|" in l]
            tc = [l for l in c.splitlines() if "|" in l]
            i_o, i_c = o.rfind("## References"), c.rfind("## References")
            refs_same = (o[i_o:] == c[i_c:]) if i_o > 0 and i_c > 0 else "n/a"
            ok = (ho == hc) and (fo == fc) and (to == tc) and refs_same in (True, "n/a")
            if not ok:
                problems += 1
            print(f"  {mon} {f:22s} headings {len(ho)}->{len(hc)} same={ho == hc} | "
                  f"figures {fo}->{fc} | tablelines {len(to)}->{len(tc)} "
                  f"same={to == tc} | refs_identical={refs_same}")

    print("\n=== PUNCTUATION the brief constrained ===")
    for mon, base in EDITIONS:
        for f in FILES:
            o = (base / f).read_text(encoding="utf-8")
            c = (pathlib.Path(f"manuscript/{mon}_v5") / f).read_text(encoding="utf-8")
            print(f"  {mon} {f:22s} semicolons {o.count(';'):3d}->{c.count(';'):<3d} "
                  f"emdash {o.count(chr(8212))}->{c.count(chr(8212))} "
                  f"endash {o.count(chr(8211))}->{c.count(chr(8211))}")

    print(f"\nMEANING-LEVEL PROBLEMS: {problems}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
