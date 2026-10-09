"""Export the machine side of the R1 label join, one row per labelled paper.

The R1 analysis computes the regex flags, card presence and sampling weight
of each labelled paper from the run folders, which hold the source abstracts
and so do not ship publicly. Without this file the precision/recall figure
cannot be rebuilt from the public tree (external review, 2026-10-09).

Only derived booleans, the card's headline value and the weight leave here;
no abstract text.

Run: python papers/scripts/studies/export_machine_side.py
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "papers" / "scripts"))
sys.path.insert(0, str(ROOT / "papers" / "scripts" / "studies"))
sys.path.insert(0, str(ROOT / "scripts"))
from label_sheet_analyze import machine_side  # noqa: E402

OUT = ROOT / "papers" / "studies" / "label_sheet" / "machine_side_rows.json"


def main() -> int:
    m = machine_side()
    rows = [{"work_key": k, **v} for k, v in sorted(m.items())]
    OUT.write_text(json.dumps({"_what": __doc__.split("\n")[0], "n": len(rows),
                               "rows": rows}, indent=2), encoding="utf-8")
    print(f"[machine_side] {len(rows)} rows -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
