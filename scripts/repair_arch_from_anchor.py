"""Apply the s09 guard-5 architecture correction to ALREADY-EXTRACTED cards.

Guard 5 fixes a card whose certified value came from a different device than
the paper's own: June 2026 labelled a "certified 32.95% perovskite/Si tandem"
value as a single-junction p-i-n cell, because the architecture described the
PAPER while the number came from a tandem sentence in the same abstract.

The guard now lives in s09_cards.py, but re-extracting a shipped month would
spend ~35 minutes of model time and could perturb every other card in it. This
script applies the identical rule to cards already on disk. It is deterministic
and idempotent: no model runs, only the recorded anchors are read.

    python scripts/repair_arch_from_anchor.py 2026-06 [--apply]

Without --apply it reports and changes nothing.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from stages.util import run_dir  # noqa: E402

MULTI = ("tandem", "/si ", "/silicon", "perovskite/si",
         "perovskite/perovskite", "all-perovskite")


def needs_fix(card: dict) -> str | None:
    """Return the corrected architecture, or None when the card is fine."""
    arch = str((card.get("device") or {}).get("architecture") or "unknown")
    if arch.startswith("tandem"):
        return None
    anchor = ((card.get("performance", {}).get("pce_certified") or {})
              .get("anchor") or "").lower()
    if not anchor:
        return None
    return "tandem_2T" if any(t in anchor for t in MULTI) else None


def main(month: str, apply: bool) -> int:
    rd = run_dir(month, create=False)
    f = rd / "claim_cards.jsonl"
    if not f.exists():
        print(f"no claim_cards.jsonl for {month}")
        return 1
    rows = [json.loads(ln) for ln in
            f.read_text(encoding="utf-8").splitlines() if ln.strip()]
    hits = []
    for c in rows:
        new = needs_fix(c)
        if new:
            old = (c.get("device") or {}).get("architecture")
            hits.append((c["work_key"], old, new,
                         (c["performance"]["pce_certified"] or {})))
            if apply:
                c["device"]["architecture"] = new
    print(f"{month}: {len(rows)} cards, {len(hits)} mislabelled")
    for wk, old, new, perf in hits:
        print(f"  {wk}")
        print(f"    {old} -> {new}   value={perf.get('value')}")
        print(f"    anchor: {perf.get('anchor')}")
    if not hits:
        return 0
    if not apply:
        print("\ndry run; re-run with --apply to write")
        return 0
    shutil.copy2(f, f.with_suffix(".jsonl.pre_arch_fix"))
    f.write_text("".join(json.dumps(c, ensure_ascii=False) + "\n"
                         for c in rows), encoding="utf-8")
    print(f"\nwrote {f} (backup: {f.name}.pre_arch_fix)")
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("usage: repair_arch_from_anchor.py <month> [--apply]")
        sys.exit(2)
    sys.exit(main(args[0], "--apply" in sys.argv))
