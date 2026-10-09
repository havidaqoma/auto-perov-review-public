"""N_PROTO correction: what each issue printed vs what it should have printed.

Until 2026-10-09 the build filled "N papers named an ISOS protocol" with the
number of cards carrying ANY protocol string (non-ISOS labels such as
"damp heat" included). The corrected count is papers naming a specified ISOS
protocol (stages.protocol.n_isos_specified). This file records both for each
monthly issue, so the manuscript can disclose the overcount with its size.

Run: python papers/scripts/studies/nproto_correction.py
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from stages.protocol import n_isos_specified  # noqa: E402
from stages.util import read_jsonl, run_dir  # noqa: E402

ISSUES = ("2026-06", "2026-07", "2026-08")


def main() -> int:
    rows = []
    for m in ISSUES:
        cl = read_jsonl(run_dir(m) / "claim_cards.jsonl")
        old = len([c for c in cl if (c.get("stability") or {}).get("protocol")])
        rows.append({"issue": m, "printed": old, "correct": n_isos_specified(cl),
                     "n_cards": len(cl)})
    over = [r for r in rows if r["printed"] != r["correct"]]
    out = {"meta": {"rule_old": "cards with any stability.protocol string",
                    "rule_new": "cards naming a specified ISOS protocol",
                    "n_issues": len(rows), "n_issues_overcounted": len(over),
                    "max_overcount": max(r["printed"] - r["correct"] for r in rows),
                    "fixed_in": "s18d_build_v4.py and s13d_draft_v4.py, 2026-10-09"},
           "rows": rows}
    (ROOT / "papers" / "studies" / "nproto_correction.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
