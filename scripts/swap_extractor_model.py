"""Swap the extraction model pin: qwen3.8-flash -> glm-5.3-flash.

Havid (2026-09-11): "change the opencode cli execution model in the process
from opencode-go/qwen3.8-flash to opencode-go/glm-5.3-flash (change all related
files)".

THE DISTINCTION THAT GOVERNS THIS SCRIPT
-----------------------------------------
"All related files" cannot mean every file containing the string, because two
different kinds of statement use it:

  CONFIG  -- what the pipeline WILL run next time. This must change.
  RECORD  -- what actually DID run on a shipped issue. This must NOT change.

Handbook 8.4 is explicit: provenance comes from records, never from live config,
and it exists because the August v4 PDF once declared an extractor that never
touched it. Rewriting a historical sentence to say glm-5.3-flash would create
exactly that false statement in reverse -- claiming a model extracted cards it
never saw. The 872 cards of 2026-H1 record `opencode-go/qwen3.8-flash` and that
is permanently true of them.

So:
  CHANGED   config/models.yaml          the forward-looking role assignment
            scripts/stages/s09_cards.py the live MODEL pin
            scripts/stages/s18d_build_v4.py  the product-name map for the
                                        AI declaration (needs the NEW name to
                                        render, or G9d fails on a bare slug)
  UNCHANGED OLD/, archive/, runs/, manuscript/   shipped artifacts
            every sentence describing what a past issue used

Handbook 2.1 requires a JSON-shape probe before adopting a new extractor, and
warns that a probe is necessary but NOT sufficient: it proves one object parses,
not that 144 abstracts extract with comparable recall. That warning is recorded
in the handbook alongside this swap rather than being silently skipped.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OLD = "qwen3.8-flash"
NEW = "glm-5.3-flash"

# Files carrying FORWARD-LOOKING configuration only.
CONFIG_FILES = [
    "config/models.yaml",
    "scripts/stages/s09_cards.py",
]

# Historical statements inside otherwise-config files that must NOT be rewritten.
# Matched as substrings; a line containing any of these is left alone.
KEEP_HISTORICAL = [
    "reverted from",
    "actually extracted July and August",
    "every card on record says",
    "313 verified anchors",
    "has 313 verified",
]


def swap(path: pathlib.Path) -> tuple[int, int]:
    """Replace OLD with NEW, skipping lines that state a historical fact."""
    txt = path.read_text(encoding="utf-8")
    out, changed, kept = [], 0, 0
    for line in txt.splitlines(keepends=True):
        if OLD in line:
            if any(k in line for k in KEEP_HISTORICAL):
                kept += 1
                out.append(line)
                continue
            out.append(line.replace(OLD, NEW))
            changed += 1
        else:
            out.append(line)
    path.write_text("".join(out), encoding="utf-8")
    return changed, kept


def main() -> int:
    print(f"=== {OLD} -> {NEW} ===")
    total = 0
    for rel in CONFIG_FILES:
        p = ROOT / rel
        if not p.exists():
            print(f"  MISSING {rel}")
            return 1
        c, k = swap(p)
        total += c
        print(f"  {rel:36} changed={c} kept_historical={k}")

    # s18d maps a CLI slug to a product name for the AI declaration. G9d fails
    # the build on a bare slug, so the new model needs an entry or the
    # declaration would name a slug instead of a product.
    s18 = ROOT / "scripts/stages/s18d_build_v4.py"
    t = s18.read_text(encoding="utf-8")
    if NEW not in t:
        # Find the product-name mapping and add the new model beside the old.
        m = re.search(r'(["\']){}\1\s*:\s*(["\'])([^"\']+)\2'.format(re.escape(OLD)), t)
        if m:
            entry = m.group(0)
            newentry = entry.replace(OLD, NEW).replace(m.group(3), "GLM 5.3 Flash")
            t = t.replace(entry, entry + ",\n        " + newentry, 1)
            s18.write_text(t, encoding="utf-8")
            print(f"  s18d product-name map: added {NEW} -> 'GLM 5.3 Flash'")
        else:
            print(f"  NOTE: no product-name map entry found for {OLD} in s18d; "
                  f"check G9d manually")

    print(f"\n=== VERIFY: live config now pins {NEW} ===")
    for rel in CONFIG_FILES:
        for i, line in enumerate((ROOT / rel).read_text(encoding="utf-8").splitlines(), 1):
            if NEW in line or (OLD in line and "MODEL" in line.upper()):
                print(f"  {rel}:{i}: {line.strip()[:92]}")

    print(f"\n=== UNCHANGED (provenance of shipped issues) ===")
    for d in ("runs", "manuscript", "OLD", "archive"):
        n = sum(1 for _ in (ROOT / d).rglob("*") if _.is_file()) if (ROOT / d).exists() else 0
        print(f"  {d}/ untouched ({n} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
