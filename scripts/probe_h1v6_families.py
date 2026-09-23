"""Read-only probe: can four DEVICE FAMILIES each carry a section?

Havid asked (2026-09-09) to restructure the H1 main text around four device
families instead of six mechanism axes:
    single junction | all-perovskite tandem | perovskite/Si tandem (+ other
    tandem partners: OPV, CIGS) | module

Before writing any code this must be measured. A family below MIN_DEPTH cannot
support a section, and s11b's cls() has NO bucket for a perovskite/organic or
perovskite/CIGS tandem -- those currently land in 'ap' (all-perovskite), which
would be a mislabel, not a rounding error.
"""
import pathlib
import re
import sys
from collections import Counter

sys.path.insert(0, "scripts")
from stages.util import read_jsonl              # noqa: E402
from stages.s11b_figures_v2 import cls          # noqa: E402

cards = read_jsonl(pathlib.Path("runs/2026-H1/claim_cards.jsonl"))
print("n_cards:", len(cards))

print("\n=== cls() current 4 buckets ===")
for k, v in Counter(cls(c) for c in cards).most_common():
    print(f"   {v:4d}  {k}")

print("\n=== device.architecture raw ===")
for k, v in Counter((c.get("device") or {}).get("architecture")
                    for c in cards).most_common():
    print(f"   {v:4d}  {k!r}")

# Which tandems are NOT silicon and NOT all-perovskite?
OTHER = re.compile(
    r"cigs|cu\(in|cuin|kesterite|czts|organic photovolt|perovskite/organic|"
    r"perovskite-organic|\bopv\b|polymer solar|pm6|y6|ptb7|dye-sensit|"
    r"quantum dot|cdte|seleni", re.I)
SI = re.compile(r"silicon|/si\b|si\s*tandem|c-si|textured|heterojunction|shj|topcon", re.I)
ALLP = re.compile(r"all-perovskite|perovskite/perovskite|wide-bandgap|narrow-bandgap|"
                  r"sn-pb|tin-lead|pb-sn", re.I)


def is_tandem(c):
    a = str((c.get("device") or {}).get("architecture") or "")
    t = (c.get("title") or "").lower()
    return a.startswith("tandem") or "tandem" in t


tan = [c for c in cards if is_tandem(c)]
print(f"\n=== tandem-ish cards: {len(tan)} ===")
buck = Counter()
other_hits = []
for c in tan:
    blob = (c.get("title") or "")
    if OTHER.search(blob):
        buck["other-partner (OPV/CIGS/...)"] += 1
        other_hits.append(c)
    elif SI.search(blob):
        buck["perovskite/Si"] += 1
    elif ALLP.search(blob):
        buck["all-perovskite"] += 1
    else:
        buck["unclassified-tandem"] += 1
for k, v in buck.most_common():
    print(f"   {v:4d}  {k}")

print("\n=== the 'other partner' tandems (would be mislabelled 'ap' today) ===")
for c in other_hits[:20]:
    print(f"   cls={cls(c):4}  {(c.get('title') or '')[:88]}")

print("\n=== module-ish evidence ===")
mod = [c for c in cards if cls(c) == "mod"]
areas = []
for c in cards:
    f = (c.get("performance") or {}).get("active_area_cm2")
    v = f.get("value") if isinstance(f, dict) else None
    if isinstance(v, (int, float)):
        areas.append(v)
print(f"   cls=='mod': {len(mod)}")
print(f"   cards with an area value: {len(areas)}")
for lo, hi in ((0, 1), (1, 10), (10, 100), (100, 1e9)):
    print(f"   area {lo:>4}-{hi:<6}: {sum(1 for a in areas if lo <= a < hi)}")

print("\n=== certified values per family (measured performance only) ===")
for fam in ("sj", "ap", "psi", "mod"):
    vals = []
    for c in cards:
        if cls(c) != fam or c.get("lens") in ("theory", "review"):
            continue
        f = (c.get("performance") or {}).get("pce_certified")
        v = f.get("value") if isinstance(f, dict) else None
        if isinstance(v, (int, float)):
            vals.append(v)
    print(f"   {fam:4} n_certified={len(vals):3}  max={max(vals) if vals else None}")
