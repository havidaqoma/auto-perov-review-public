"""Repair a stored p-field that was destroyed by fixed-decimal rounding.

The 767-paper title-only run stored `fisher_exact_p: 0.0`. The arithmetic was
never wrong -- `round(p, 8)` in the summary block flattened a real
8.885779466077036e-15 to zero on the way to disk. A stored 0.0 asserts
impossible certainty, so the artifact cannot ship as it stands.

This recomputes p from the COUNTS ALREADY IN THE ARTIFACT. It calls no model,
re-extracts nothing, and touches no row. If the recomputed arm counts disagree
with the row-level records, it refuses to write -- a repair that silently
disagrees with its own evidence is worse than the defect.

Run: python -u scripts/studies/repair_p_field.py <artifact.json>
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from studies.baseline_scaled import fisher_exact, P_FLOOR  # noqa: E402


def repair(path: pathlib.Path) -> int:
    d = json.loads(path.read_text(encoding="utf-8"))
    meta, rows = d["meta"], d["rows"]
    arms = {a["arm"]: a for a in meta["arms"]}
    if len(arms) != 2:
        raise SystemExit(f"FAIL-CLOSED: expected 2 arms, got {list(arms)}")

    # Re-derive every count from the rows. The summary is the thing under
    # suspicion, so it may not be the thing that validates the repair.
    for name, a in arms.items():
        n = sum(1 for r in rows if r["arm"] == name)
        ung = sum(1 for r in rows if r["arm"] == name and not r["grounded"])
        if (n, ung) != (a["n_values"], a["n_ungrounded"]):
            raise SystemExit(
                f"FAIL-CLOSED: {name} summary says {a['n_ungrounded']}/{a['n_values']} "
                f"but rows say {ung}/{n}")
        print(f"[repair] {name:22s} {ung}/{n} confirmed against rows")

    ung_arm = [a for k, a in arms.items() if k != "guarded_pipeline"][0]
    g_arm = arms["guarded_pipeline"]
    p = fisher_exact(ung_arm["n_ungrounded"],
                     ung_arm["n_values"] - ung_arm["n_ungrounded"],
                     g_arm["n_ungrounded"],
                     g_arm["n_values"] - g_arm["n_ungrounded"])
    p_repr = f"< {P_FLOOR:.0e}" if p <= P_FLOOR else f"{p:.3e}"

    old = meta.get("fisher_exact_p")
    meta["fisher_exact_p"] = p
    meta["fisher_exact_p_repr"] = p_repr
    meta["p_floor"] = P_FLOOR
    meta["significant_at_0_05"] = bool(p < 0.05)
    meta["p_field_repaired"] = (
        "stored 0.0 came from round(p, 8) in the summary block, not from "
        "underflow; recomputed offline from the counts in this artifact")

    path.write_text(json.dumps(d, indent=2), encoding="utf-8")
    print(f"[repair] {old!r} -> {p!r}  (reported as {p_repr})")
    return 0


if __name__ == "__main__":
    sys.exit(repair(pathlib.Path(sys.argv[1])))
