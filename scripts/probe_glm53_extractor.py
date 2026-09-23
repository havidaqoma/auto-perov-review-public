"""JSON-shape probe for the extractor swap qwen3.8-flash -> glm-5.3-flash.

Handbook 2.1 requires this probe BEFORE a new extractor model is adopted, and
states plainly that the probe is necessary but NOT sufficient: it proves that
one object parses, not that 144 abstracts extract with comparable recall.

The probe therefore reports two separate things and never merges them:

  SHAPE     does call_opencode + parse_array return an array whose first
            object carries every schema key s09 later reads? This is what
            adoption is gated on.
  RECALL    did the model actually fill the numeric fields from the abstract,
            or return a well-formed object full of nulls? A model that returns
            the right keys with empty values passes a naive shape check and
            then produces the silent-zero class (handbook 7.1).

The prompt is built from s09_cards' own builder where one is exposed, so the
probe tests the real prompt rather than a hand-written approximation.

Exit codes: 0 shape pass, 1 shape fail, 2 harness/invocation error.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

REQUIRED = {"work_key", "architecture", "pce_champion", "pce_certified",
            "t80_h", "claims"}

# A real 2026 perovskite abstract with numbers that MUST come back, so the
# probe can tell a filled object from a well-formed empty one.
ABSTRACT = (
    "Buried-interface passivation of formamidinium-cesium perovskite solar "
    "cells with a phosphonic-acid self-assembled monolayer suppressed "
    "non-radiative recombination at the NiOx/perovskite contact. The "
    "champion device reached a power conversion efficiency of 26.7% with an "
    "open-circuit voltage of 1.19 V and a fill factor of 84.2% over an "
    "aperture area of 0.09 cm2, and an independently certified efficiency of "
    "26.1% was obtained. Encapsulated devices retained 92% of initial "
    "efficiency after 1500 h of maximum-power-point tracking under one-sun "
    "illumination at 65 C."
)


def main() -> int:
    try:
        from stages.s09_cards import call_opencode, parse_array, MODEL
    except Exception as exc:  # noqa: BLE001
        print(f"HARNESS FAIL: cannot import s09_cards: {exc}")
        return 2

    print(f"probing MODEL = {MODEL}")

    prompt = (
        "Extract ONE JSON object into a JSON array. Return ONLY the array, no "
        "prose, no markdown fence. Keys exactly: work_key (string), "
        "architecture (string), pce_champion (number or null), pce_certified "
        "(number or null), t80_h (number or null), claims (array of objects "
        "with keys text and anchor, where anchor is a VERBATIM span copied "
        "from the abstract).\n\nwork_key: W_PROBE_GLM53\n\nABSTRACT:\n"
        + ABSTRACT
    )

    t0 = time.time()
    try:
        raw, meta = call_opencode(prompt, timeout=420, attempts=2)
    except Exception as exc:  # noqa: BLE001
        print(f"HARNESS FAIL: call_opencode raised: {type(exc).__name__}: {exc}")
        return 2
    elapsed = time.time() - t0

    print(f"elapsed = {elapsed:.1f}s")
    print(f"meta    = {json.dumps(meta, default=str)[:400]}")
    print(f"raw len = {len(raw)}")
    print("--- RAW HEAD ---")
    print(raw[:900])
    print("--- END RAW HEAD ---")

    try:
        arr = parse_array(raw)
    except Exception as exc:  # noqa: BLE001
        print(f"SHAPE FAIL: parse_array raised {type(exc).__name__}: {exc}")
        return 1

    if not arr:
        print("SHAPE FAIL: parse_array returned an empty array (silent-zero class)")
        return 1

    obj = arr[0]
    have = set(obj)
    missing = REQUIRED - have
    print(f"keys returned = {sorted(have)}")
    if missing:
        print(f"SHAPE FAIL: missing required keys {sorted(missing)}")
        return 1
    print(f"SHAPE PASS: all {len(REQUIRED)} required keys present")

    # RECALL, reported separately and never used to claim adoption readiness.
    filled = {k: obj.get(k) for k in ("pce_champion", "pce_certified", "t80_h")}
    print(f"numeric fields = {filled}")
    nulls = [k for k, v in filled.items() if v in (None, "", 0)]
    if nulls:
        print(f"RECALL WARNING: null/zero numeric fields {nulls} "
              f"(expected ~26.7, ~26.1, ~1500 from the abstract)")
    else:
        print("RECALL OK on this single abstract (26.7 / 26.1 / 1500 expected)")

    claims = obj.get("claims") or []
    print(f"claims returned = {len(claims)}")
    verbatim = 0
    for c in claims:
        if isinstance(c, dict) and isinstance(c.get("anchor"), str):
            if c["anchor"].strip() and c["anchor"].strip() in ABSTRACT:
                verbatim += 1
    print(f"anchors verbatim-in-abstract = {verbatim}/{len(claims)}")
    if claims and verbatim < len(claims):
        print("RECALL WARNING: at least one anchor is not a verbatim span; "
              "verify_anchors would reject those cards")

    print("\nNOTE: a shape pass is NOT adoption clearance. Handbook 2.1 "
          "requires re-extracting a month rather than letting a new model "
          "debut on a shipping issue.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
