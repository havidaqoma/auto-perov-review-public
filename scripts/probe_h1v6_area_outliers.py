"""Audit the large-area outliers inside each family.

Trigger: h1_family_stats reported family.sj.max_area_cm2 = 651 cm2. A
single-junction CELL at 651 cm2 is module-scale hardware, so either the area
belongs to a module (the 7.8 mislabel class) or the family label is wrong.

Read-only. Prints the anchor so the DEVICE can be judged from the sentence the
number came from, not from the paper's title.
"""
import pathlib
import sys

sys.path.insert(0, "scripts")
from stages.util import read_jsonl                              # noqa: E402
from stages.device_family import family, family_or_fold         # noqa: E402

cards = read_jsonl(pathlib.Path("runs/2026-H1/claim_cards.jsonl"))


def v(c, k):
    src = c.get("stability") if k in ("t80_h",) else c.get("performance")
    f = (src or {}).get(k)
    return f["value"] if isinstance(f, dict) and f.get("value") is not None else None


def anchor(c, k):
    src = c.get("stability") if k in ("t80_h",) else c.get("performance")
    f = (src or {}).get(k)
    return (f.get("anchor") or "") if isinstance(f, dict) else ""


print("=== every card with area >= 100 cm2, by family ===")
rows = []
for c in cards:
    a = v(c, "active_area_cm2")
    if isinstance(a, (int, float)) and a >= 100:
        rows.append((a, family(c), family_or_fold(c), c))
rows.sort(key=lambda r: -r[0])
for a, fam, folded, c in rows:
    print(f"\n  {a:>8} cm2  family={fam:20} arch={(c.get('device') or {}).get('architecture')!r}")
    print(f"      title : {(c.get('title') or '')[:95]}")
    print(f"      anchor: {anchor(c,'active_area_cm2')[:120]}")
    print(f"      cert={v(c,'pce_certified')} champ={v(c,'pce_champion')}")
print(f"\n  total cards >= 100 cm2: {len(rows)}")

print("\n=== does any 'sj' card name a module in its own area anchor? ===")
bad = 0
for c in cards:
    if family_or_fold(c) != "sj":
        continue
    a = v(c, "active_area_cm2")
    an = anchor(c, "active_area_cm2").lower()
    if isinstance(a, (int, float)) and a >= 100:
        flag = "MODULE-WORD" if ("module" in an or "submodule" in an) else "no module word"
        print(f"   {a:>8} cm2  {flag}  {(c.get('title') or '')[:70]}")
        bad += 1
print(f"   -> sj cards >= 100 cm2: {bad}")
