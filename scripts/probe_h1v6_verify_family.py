"""Verify device_family against the real H1 cards.

The point is NOT that it runs. The point is that the 19 mislabelled tandems
found by probe_h1v6_families.py are no longer called all-perovskite, and that
every family has enough mass to carry a section.
"""
import pathlib
import sys

sys.path.insert(0, "scripts")
from stages.util import read_jsonl                    # noqa: E402
from stages.s11b_figures_v2 import cls                # noqa: E402
from stages.device_family import (LABEL, counts,      # noqa: E402
                                  evidence_text, family, family_or_fold)

cards = read_jsonl(pathlib.Path("runs/2026-H1/claim_cards.jsonl"))

print("=== honest counts (unspecified kept separate) ===")
for k, v in counts(cards).items():
    print(f"   {v:4d}  {k:20} {LABEL.get(k,'')}")

print("\n=== folded to four buckets ===")
for k, v in counts(cards, fold=True).items():
    print(f"   {v:4d}  {k:20} {LABEL.get(k,'')}")

print("\n=== REGRESSION: the 19 mislabelled tandems ===")
KNOWN = ["Perovskite/Organic Tandem", "Cu(In,Ga)Se", "CdTe Four-Terminal",
         "kesterite/perovskite", "Perovskite/CIGS", "perovskite-organic tandem"]
bad = 0
for c in cards:
    t = c.get("title") or ""
    if any(k.lower() in t.lower() for k in KNOWN):
        f, old = family(c), cls(c)
        flag = "OK " if f in ("hyb", "mod") else "STILL WRONG"
        if f not in ("hyb", "mod"):
            bad += 1
        print(f"   {flag} old={old:4} new={f:20} {t[:66]}")
print(f"   -> still mislabelled: {bad}")

print("\n=== certified frontier per family (measured only) ===")
for fam in ("sj", "ap", "hyb", "mod"):
    vals = []
    for c in cards:
        if family_or_fold(c) != fam or c.get("lens") in ("theory", "review"):
            continue
        f = (c.get("performance") or {}).get("pce_certified")
        v = f.get("value") if isinstance(f, dict) else None
        if isinstance(v, (int, float)):
            vals.append(v)
    print(f"   {fam:4} n_cert={len(vals):3}  max={max(vals) if vals else None}")

print("\n=== SANITY: any single-junction above the SQ limit? (must be none) ===")
viol = []
for c in cards:
    if family_or_fold(c) != "sj":
        continue
    f = (c.get("performance") or {}).get("pce_certified")
    v = f.get("value") if isinstance(f, dict) else None
    if isinstance(v, (int, float)) and v > 29.4:
        viol.append((v, (c.get("title") or "")[:70], evidence_text(c)[:90]))
for v, t, a in viol:
    print(f"   {v}  {t}\n        anchor: {a}")
print(f"   -> violations: {len(viol)}")
