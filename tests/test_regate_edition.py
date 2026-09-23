"""The regate must reach the same verdicts the build reached.

scripts/regate_edition.py gates a finished edition without rebuilding it (the
hand-revised July and August editions were never built by s18d). It is only
trustworthy while it agrees with the build on an edition the build DID gate.

Private tree: July v4 was built and gated by s18d; replay it and compare every
verdict with the build's own report. Public tree (final editions only): replay
each shipped final edition and compare with the gate report that ships beside
it, so a reader can check that the shipped verdicts are reproducible.
"""
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from stages import editions  # noqa: E402

if editions.is_release_tree(ROOT):
    CASES = [(p, v, editions.edition_file(ROOT, p, "gate_report", ".json"),
              editions.edition_file(ROOT, p, "manuscript", ".pdf"))
             for p, v in editions.FINAL.items() if p != "2026-H1"]
else:
    CASES = [("2026-07", "v4",
              ROOT / "runs" / "2026-07_197abe83" / "gate_report_v4.json",
              ROOT / "manuscript" / "2026-07_v4" / "manuscript_v4.pdf")]


def _prior(ref: dict) -> pathlib.Path | None:
    """The prior issue G8 compared against, as the shipped report records."""
    info = ref.get("_regate", {}).get("detail", {})
    rel = info.get("prior_issue_file")
    if not rel or rel == "build default":
        return None
    if editions.is_release_tree(ROOT):
        period = rel.split("/")[1].split("_")[0]
        return editions.edition_file(ROOT, period, "manuscript", ".md")
    return ROOT / rel


@pytest.mark.parametrize("period,ver,ref_p,pdf", CASES,
                         ids=[c[0] for c in CASES])
def test_regate_matches_recorded_verdicts(period, ver, ref_p, pdf):
    assert ref_p.exists() and pdf.exists(), (ref_p, pdf)
    import regate_edition
    ref = json.loads(ref_p.read_text(encoding="utf-8"))
    gate, _ = regate_edition.regate(period, ver, _prior(ref))
    gates = {k: v for k, v in ref.items() if not k.startswith("_")}
    mismatch = {k: (gates[k]["status"], gate.get(k, {}).get("status"))
                for k in gates if gates[k]["status"] != gate.get(k, {}).get("status")}
    assert not mismatch, f"regate disagrees with the recorded report: {mismatch}"
