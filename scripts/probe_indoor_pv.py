"""Verify EXACTLY which cards produce the table numbers, and why.

Havid flagged >30% for a single junction. The probe found two populations and
they need different fixes, so this separates them rather than lumping them:

  A. lens='theory' simulation values (SCAPS-1D etc.), 29.41-32.41%
  B. INDOOR / low-light values, 35.54-44.36%, reported under LED or TL84
     illumination at 300-900 lux

Population A should already be excluded from every table number by
family_block()'s measured() filter. This asserts that rather than assuming it.

Population B is a NEW defect class with no guard anywhere: an indoor PCE above
the 1-sun Shockley-Queisser limit is PHYSICALLY CORRECT, because the indoor
spectrum is not AM1.5G. It is simply not comparable to a 1-sun record, and the
review prints it in a column headed "Best self-reported PCE" beside 1-sun
values.
"""
import pathlib
import re
import sys

sys.path.insert(0, "scripts")
from stages.util import read_jsonl                                # noqa: E402
from stages.device_family import family_or_fold                   # noqa: E402
from stages.h1_family_stats import (_anchor, _v,                  # noqa: E402
                                    anchor_contradicts_family, measured)

cards = read_jsonl(pathlib.Path("runs/2026-H1/claim_cards.jsonl"))

# Words that mark a measurement as NOT one-sun AM1.5G.
INDOOR = re.compile(
    r"\bindoor\b|\blux\b|\bled\b|TL84|TL-84|fluorescen|low[- ]light|"
    r"artificial light|\bPCE\(i\)|dim light|ambient light|"
    r"\bµW\s*cm|\buW\s*cm|microwatt", re.I)


def reason(c, field):
    a = _anchor(c, field)
    hits = sorted(set(m.group(0).lower() for m in INDOOR.finditer(a)))
    return hits


print("=== A. does measured() actually exclude the theory cards? ===")
for fam in ("sj", "ap", "hyb", "mod"):
    pool = [c for c in cards if family_or_fold(c) == fam]
    meas = [c for c in pool if measured(c)]
    theory = [c for c in pool if not measured(c)]
    th_champ = [v for v in (_v(c, "pce_champion") for c in theory)
                if isinstance(v, (int, float))]
    print(f"   {fam:4} pool={len(pool):4} measured={len(meas):4} "
          f"theory/review={len(theory):3}  max theory champion="
          f"{max(th_champ) if th_champ else None}")

print("\n=== B. the number that ACTUALLY reaches family.<fam>.top_champion ===")
for fam in ("sj", "ap", "hyb", "mod"):
    vals = []
    for c in cards:
        if family_or_fold(c) != fam or not measured(c):
            continue
        v = _v(c, "pce_champion")
        if not isinstance(v, (int, float)):
            continue
        if anchor_contradicts_family(c, "pce_champion", fam):
            continue
        vals.append((v, c))
    vals.sort(key=lambda r: -r[0])
    print(f"\n   {fam}: top_champion = {vals[0][0] if vals else None}")
    for v, c in vals[:3]:
        ind = reason(c, "pce_champion")
        print(f"      {v:>7}% lens={c.get('lens'):12} "
              f"indoor_markers={ind or 'NONE'}")
        print(f"              {(c.get('title') or '')[:88]}")

print("\n=== C. every card whose champion or certified anchor is INDOOR ===")
n = 0
for c in cards:
    for field in ("pce_champion", "pce_certified"):
        v = _v(c, field)
        if not isinstance(v, (int, float)):
            continue
        hits = reason(c, field)
        if hits:
            n += 1
            print(f"\n   {v:>7}% {field:14} fam={family_or_fold(c):4} "
                  f"lens={c.get('lens')} markers={hits}")
            print(f"      title : {(c.get('title') or '')[:98]}")
            print(f"      anchor: {_anchor(c, field)[:150]}")
print(f"\n   -> {n} indoor/low-light value(s) currently treated as 1-sun")
