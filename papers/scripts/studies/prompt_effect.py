"""Prompt effect and clustering of ungrounded values, computed, not typed.

Two numbers the manuscript needs that no other artifact holds (external
review, 2026-10-09):

  * The prompt effect. Both ungated arms ran the same extractor with every
    tool off and no gate; they differ only in the prompt (generic in R3, the
    production anchor prompt in R5 gate-off). Fisher's exact test on their
    ungrounded counts is the one comparison here that is not against a zero
    the gate guarantees by construction.
  * Clustering. Values come in groups from one paper, so the number of
    distinct papers behind the ungrounded values is reported beside the count.

Run: python papers/scripts/studies/prompt_effect.py
"""
from __future__ import annotations

import json
import math
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
S = ROOT / "papers" / "studies"


def fisher_two_sided(a: int, b: int, c: int, d: int) -> float:
    """Exact two-sided P for the 2x2 table [[a, b], [c, d]]."""
    r1, c1, n = a + b, a + c, a + b + c + d

    def p(x: int) -> float:
        return math.comb(c1, x) * math.comb(n - c1, r1 - x) / math.comb(n, r1)

    obs = p(a)
    lo, hi = max(0, r1 - (n - c1)), min(r1, c1)
    return min(1.0, sum(p(x) for x in range(lo, hi + 1) if p(x) <= obs * (1 + 1e-9)))


def main() -> int:
    r3 = json.loads((S / "baseline_scaled.json").read_text(encoding="utf-8"))
    r5 = json.loads((S / "ablation_gate.json").read_text(encoding="utf-8"))
    g = [r for r in r3["rows"] if r["arm"] == "ungated_baseline"]
    o = r5["rows"]
    gb = [r for r in g if not r["grounded"]]
    ob = [r for r in o if not r["grounded"]]
    a3 = r3["meta"]["arms"][0]
    a5 = r5["meta"]["arms"][0]
    assert (len(g), len(gb)) == (a3["n_values"], a3["n_ungrounded"]), "R3 rows disagree with meta"
    assert (len(o), len(ob)) == (a5["n_values"], a5["n_ungrounded"]), "R5 rows disagree with meta"
    pval = fisher_two_sided(len(gb), len(g) - len(gb), len(ob), len(o) - len(ob))
    out = {"meta": {
        "comparison": "generic prompt (R3 ungated) vs production prompt (R5 gate off); "
                      "same extractor, tools off, no gate",
        "generic_n": len(g), "generic_bad": len(gb),
        "generic_bad_papers": len({r["work_key"] for r in gb}),
        "production_n": len(o), "production_bad": len(ob),
        "production_bad_papers": len({r["work_key"] for r in ob}),
        "fisher_p": round(pval, 4), "fisher_p_repr": f"{pval:.3e}",
        "test": "Fisher exact, two-sided, values treated as independent; "
                "the paper counts are given so clustering is visible"}}
    (S / "prompt_effect.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out["meta"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
