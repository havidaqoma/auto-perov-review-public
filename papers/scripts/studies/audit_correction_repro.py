"""Reproduce papers/studies/audit_correction.json from the shipped runs.

The artifact was committed in c4695e0 without the script that made it. This
recomputes every count from the recorded run files and FAILS if any month
differs, so the numbers the paper cites (T80_PCT, ISOS_OLD/NEW) trace to code.

Denominator: papers in 06_labels.jsonl with has_abstract true.
Old ISOS:    the original raw pattern, AUDIT_RX["isos_label"] before the fix,
             matched case-insensitively on the unnormalised abstract.
New ISOS:    stages.protocol.isos_in_text (Unicode-normalised, all families).
T80:         stages.protocol.t80_in_text.

Read-only: writes nothing unless --write is passed.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "papers" / "scripts"))
from stages.protocol import isos_in_text, t80_in_text  # noqa: E402
from studies.study_common import active_run  # noqa: E402

ART = ROOT / "papers" / "studies" / "audit_correction.json"
OLD_ISOS = re.compile(r"\bISOS-[LVDTP]+(-\d)?\b", re.I)


def jl(p: pathlib.Path) -> list:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()
            if x.strip()]


def month_counts(month: str) -> dict:
    rd = active_run(month)
    ab = {r["work_key"].lower(): r.get("abstract") or ""
          for r in jl(rd / "private" / "02_abstracts.jsonl")}
    keys = [r["work_key"].lower() for r in jl(rd / "06_labels.jsonl")
            if r.get("has_abstract")]
    txt = [ab.get(k, "") for k in keys]
    return {"denominator": len(keys),
            "isos_old_n": sum(bool(OLD_ISOS.search(t)) for t in txt),
            "isos_new_n": sum(isos_in_text(t) for t in txt),
            "t80_n": sum(t80_in_text(t) for t in txt)}


def main() -> int:
    art = json.loads(ART.read_text(encoding="utf-8"))
    bad, tot = [], {"denominator": 0, "isos_old_n": 0, "isos_new_n": 0, "t80_n": 0}
    for month, rec in sorted(art["per_month"].items()):
        got = month_counts(month)
        for k in tot:
            tot[k] += got[k]
            if got[k] != rec[k]:
                bad.append(f"{month} {k}: recorded {rec[k]}, recomputed {got[k]}")
        print(month, got)
    for k in tot:
        if tot[k] != art["pooled"][k]:
            bad.append(f"pooled {k}: recorded {art['pooled'][k]}, recomputed {tot[k]}")
    print("pooled", tot)
    if bad:
        print("FAIL: audit_correction.json does not reproduce:")
        for b in bad:
            print("  " + b)
        return 1
    print("OK: every count in audit_correction.json reproduces from the runs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
