"""Read-only audit: values above the physical limit, by family.

Havid flagged a >30% PCE reported for a single junction and asked whether it is
a tandem or a simulation. Table 1 prints single-junction best SELF-REPORTED as
44.36% and module best self-reported as 41.6% -- both above even the ~33.7%
theoretical Shockley-Queisser single-junction limit, so the concern is well
founded and the defect is larger than flagged.

Note what was already guarded and what was not. G3c and
anchor_contradicts_family both police CERTIFIED values. `pce_champion` had NO
plausibility check at all, on the reasoning that a self-reported number is the
paper's own claim. That reasoning is wrong: an impossible self-reported number
is either an extraction error or a different device, and either way the review
must not print it as a single-junction champion.

Prints the verbatim anchor so the device can be judged from the sentence the
number came from, never from the title.
"""
import pathlib
import sys

sys.path.insert(0, "scripts")
from stages.util import read_jsonl                              # noqa: E402
from stages.device_family import family, family_or_fold         # noqa: E402

SJ_MAX = 29.4        # practical perovskite single-junction limit (G3c)
SJ_SQ = 33.7         # theoretical single-junction Shockley-Queisser limit
TANDEM_MAX = 47.6    # 2-junction detailed-balance limit

cards = read_jsonl(pathlib.Path("runs/2026-H1/claim_cards.jsonl"))


def v(c, k):
    src = c.get("stability") if k in ("t80_h",) else c.get("performance")
    f = (src or {}).get(k)
    return f["value"] if isinstance(f, dict) and f.get("value") is not None else None


def an(c, k):
    src = c.get("stability") if k in ("t80_h",) else c.get("performance")
    f = (src or {}).get(k)
    return (f.get("anchor") or "") if isinstance(f, dict) else ""


def show(c, field, val, why):
    print(f"\n  {val:>7}%  {why}")
    print(f"     family={family_or_fold(c):4} honest={family(c):20} "
          f"lens={c.get('lens')!r} arch={(c.get('device') or {}).get('architecture')!r}")
    print(f"     month={c.get('source_month')} venue={c.get('venue')!r}")
    print(f"     doi={c.get('work_key')}")
    print(f"     title : {(c.get('title') or '')[:112]}")
    print(f"     anchor: {an(c, field)[:160]}")


print("=== SJ cards, self-reported champion above the practical limit ===")
n = 0
for c in cards:
    if family_or_fold(c) != "sj":
        continue
    val = v(c, "pce_champion")
    if isinstance(val, (int, float)) and val > SJ_MAX:
        n += 1
        show(c, "pce_champion", val,
             "ABOVE SQ LIMIT - impossible for one junction" if val > SJ_SQ
             else "above practical perovskite limit")
print(f"\n  -> {n} SJ champion value(s) above {SJ_MAX}%")

print("\n=== SJ cards, CERTIFIED above 29.4% ===")
m = 0
for c in cards:
    if family_or_fold(c) != "sj":
        continue
    val = v(c, "pce_certified")
    if isinstance(val, (int, float)) and val > SJ_MAX:
        m += 1
        show(c, "pce_certified", val, "certified > SJ limit")
print(f"\n  -> {m} SJ certified value(s) above {SJ_MAX}%")

print("\n=== TOP 12 self-reported champions, any family ===")
rows = sorted(((v(c, "pce_champion"), c) for c in cards
               if isinstance(v(c, "pce_champion"), (int, float))),
              key=lambda r: r[0])
for val, c in rows[-12:][::-1]:
    print(f"   {val:>7}%  fam={family_or_fold(c):4} "
          f"arch={str((c.get('device') or {}).get('architecture')):16} "
          f"lens={str(c.get('lens')):12} {(c.get('title') or '')[:58]}")

print("\n=== anything above the 2-junction limit (>47.6%) ===")
for val, c in rows:
    if val > TANDEM_MAX:
        show(c, "pce_champion", val, "above 2-junction detailed-balance limit")

print("\n=== MODULE champions above 30% ===")
for c in cards:
    if family_or_fold(c) != "mod":
        continue
    val = v(c, "pce_champion")
    if isinstance(val, (int, float)) and val > 30:
        show(c, "pce_champion", val, "module champion > 30%")
