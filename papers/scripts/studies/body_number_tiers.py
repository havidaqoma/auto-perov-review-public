"""How the body-number gate (G3e) admitted each numeral, and what the older
fault-injection rule let through.

Two disclosures asked for by the round-2 external review (agy, 2026-10-09):

1. G3e admits a numeral by one of several tiers, some looser than the anchor
   contract (a number found anywhere in a cited abstract, a number inherited
   from a paragraph citation, a month-wide card number, small integers and
   years exempt). This reads the tier counts each monthly issue's gate report
   recorded, so the paper can say how much traffic each tier carried.
2. Under the older fault-injection rule (a mutation is caught once its
   declared gate fires) some caught builds still exited cleanly. This counts
   them from the stored second-run record.

Read-only; no model calls. Run: python papers/scripts/studies/body_number_tiers.py
"""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
ISSUES = ("2026-06", "2026-07", "2026-08")
TIERS = ("bound", "para_bound", "in_cited_abstract", "para_in_cited_abstract",
         "aggregate", "month_bound", "exempt")
OLD_FI = ROOT / "papers/studies/superseded/fault_injection.oracle_definition_dac5f79.json"
NEW_FI = ROOT / "papers/studies/fault_injection.json"
OUT = ROOT / "papers/studies/body_number_tiers.json"


def main() -> int:
    rows = []
    for m in ISSUES:
        rep = json.loads((ROOT / f"manuscript/{m}_v4/gate_report_v4.json").read_text(encoding="utf-8"))
        g = rep["G3e-body-numbers"]
        if g["status"] != "pass":
            raise SystemExit(f"FAIL-CLOSED: {m} G3e status {g['status']!r}")
        d = g["detail"]
        missing = [t for t in TIERS if t not in d]
        if missing:
            raise SystemExit(f"FAIL-CLOSED: {m} gate report lacks tiers {missing}")
        rows.append({"issue": m, **{t: d[t] for t in TIERS},
                     "count_claims_checked": d["count_claims_checked"],
                     "n_failed": d["n_failed"]})
    total = {t: sum(r[t] for r in rows) for t in TIERS}
    n_num = sum(total.values())
    loose = total["in_cited_abstract"] + total["para_in_cited_abstract"] + total["month_bound"]

    old = json.loads(OLD_FI.read_text(encoding="utf-8"))["rows"]
    old_caught = [r for r in old if r["verdict"] == "caught_by_oracle"]
    old_clean = [r["id"] for r in old_caught if r["rc"] == 0]
    new = json.loads(NEW_FI.read_text(encoding="utf-8"))["rows"]
    old_ids = {r["id"] for r in old_caught}
    orig_strict = [r["id"] for r in new if r["id"] in old_ids
                   and r["verdict"] == "caught_by_oracle" and r["rc"] != 0]
    added = sorted({r["id"] for r in new} - {r["id"] for r in old})

    out = {
        "meta": {
            "source": "manuscript/<issue>_v4/gate_report_v4.json, G3e-body-numbers.detail",
            "issues": list(ISSUES),
            "n_numerals": n_num,
            "total": total,
            "n_card_bound": total["bound"] + total["para_bound"],
            "n_loose_tiers": loose,
            "exempt_rule": "a whole number from 0 to 10 not followed by a count noun "
                           "(papers, works, ...), or a whole number from 1900 to 2100",
            "not_scanned": "figure environments and markdown table lines; in an issue the "
                           "figures and SI tables are emitted by build code from the cards",
            "fi_old_rule_caught": len(old_caught),
            "fi_old_rule_caught_clean_exit": len(old_clean),
            "fi_old_rule_clean_exit_ids": old_clean,
            "fi_original_caught_strict": len(orig_strict),
            "fi_added_after_g3e": added,
        },
        "rows": rows,
    }
    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out["meta"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
