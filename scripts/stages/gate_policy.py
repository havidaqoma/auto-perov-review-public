"""Which gate results let an issue ship. One rule, used by every consumer.

The build (s18d), the run driver (run_month), the ChemRxiv packager (s20) and
the public-tree builder all call `verdict`, so none of them can be more
lenient than the others. Before this module each one read the gate report its
own way and the build did not read it at all: a failed gate was recorded and
the PDF was still copied to manuscript/ (external review, 2026-10-09).

Policy:
  * "pass" always ships.
  * "fail" never ships.
  * "warn" means a gate could not measure (e.g. no PDF reader). An unmeasured
    gate is not a passed gate, so a warn blocks too, unless listed below.
  * "skip" is allowed only where the gate has nothing to compare against,
    and only for the gates listed below.
"""
from __future__ import annotations

# gate id -> statuses other than "pass" that may ship, with the reason.
ALLOWED_NON_PASS = {
    # The first issue on record has no prior issue to be novel against.
    "G8-novelty": {"skip": "no prior issue exists to compare against"},
}


def verdict(gate: dict) -> dict:
    """Return {"ok": bool, "blocking": {gate: status}, "allowed": {gate: reason}}."""
    blocking, allowed = {}, {}
    for k, v in (gate or {}).items():
        if k.startswith("_"):      # metadata block (e.g. "_regate"), not a gate
            continue
        st = (v or {}).get("status")
        if st == "pass":
            continue
        reason = ALLOWED_NON_PASS.get(k, {}).get(st)
        if reason:
            allowed[k] = f"{st}: {reason}"
        else:
            blocking[k] = st
    return {"ok": not blocking and bool(gate), "blocking": blocking, "allowed": allowed}
