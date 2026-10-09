"""Record the transfer evidence: the anchor contract run on two non-perovskite schemas.

The General_topic_monthly fork (General_topic_monthly) re-implements
the extraction schema from a domain registry and ships its own independent
verifier (scripts/verify_cards.py, which shares no code with its extractor).
Two August 2026 periods were run there:

  cqd_led  colloidal quantum-dot light-emitting diodes (performance-type schema)
  zno_pv   ZnO in solar-cell devices (discovery-type schema)

This script re-runs that verifier on COPIES of the two runs' card and
selection files, so the fork is never written to, compares the fresh result
with the stored verify_cards.json byte for byte, hashes the inputs, and
records the fork's commit and the dirtiness of its working tree. It fails
closed if the fresh verification disagrees with the stored one.

What this evidence can and cannot support is written into the artifact:
it shows the contract ports to other extraction schemas and holds there. It
does not show a fabrication reduction in those domains, because no ungated
arm was run for them.

  python papers/scripts/studies/transfer_evidence.py
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
FORK = pathlib.Path("General_topic_monthly")
OUT = ROOT / "papers" / "studies" / "transfer_domains.json"
RUNS = [("cqd_led", "2026-08", "Colloidal quantum-dot light-emitting diodes", "P"),
        ("zno_pv", "2026-08", "ZnO in solar-cell devices", "D")]
FILES = ("04_selected.jsonl", "09_claim_cards.jsonl")


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git(*a: str) -> str:
    return subprocess.run(["git", "-C", str(FORK), *a], capture_output=True,
                          text=True, timeout=30).stdout.strip()


def main() -> int:
    if not (FORK / "scripts" / "verify_cards.py").exists():
        raise SystemExit(f"FAIL-CLOSED: verifier not found in {FORK}")
    sys.path.insert(0, str(FORK / "scripts"))
    import verify_cards as v  # the fork's own, independent verifier

    rows = []
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        v.RUNS = tmp  # verify copies; never write into the fork
        for dom, per, name, ttype in RUNS:
            rid = f"{dom}_{per}"
            src = FORK / "runs" / rid
            (tmp / rid).mkdir()
            for f in FILES:
                shutil.copy2(src / f, tmp / rid / f)
            shutil.copy2(FORK / "runs" / f"{rid}.active", tmp / f"{rid}.active")
            rc = v.main([per, "--domain", dom])
            fresh = json.loads((tmp / rid / "verify_cards.json").read_text(encoding="utf-8"))
            stored = json.loads((src / "verify_cards.json").read_text(encoding="utf-8"))
            if rc != 0 or fresh != stored:
                raise SystemExit(f"FAIL-CLOSED: {rid} re-verification rc={rc}, "
                                 f"matches stored={fresh == stored}")
            cards = [json.loads(l) for l in (src / "09_claim_cards.jsonl")
                     .read_text(encoding="utf-8").splitlines() if l.strip()]
            models = sorted({(c.get("extractor") or {}).get("model", "?") for c in cards})
            n_ok = fresh["counts"].get("ok", 0)
            rows.append({
                "domain": dom, "name": name, "schema_type": ttype, "period": per,
                "n_papers_selected": sum(1 for l in (src / "04_selected.jsonl")
                                         .read_text(encoding="utf-8").splitlines() if l.strip()),
                "n_cards": fresh["n_cards"], "n_fields": fresh["n_fields"],
                "n_fields_verified": n_ok,
                "n_fields_failed": fresh["n_fields"] - n_ok,
                "n_metrics": len(fresh["per_metric"]),
                "per_metric": fresh["per_metric"],
                "extractor_models": models,
                "reverified_equals_stored": True,
                "sha256": {f: sha(src / f) for f in FILES},
            })

    status = [l for l in git("status", "--porcelain").splitlines() if l.strip()]
    meta = {
        "study": "T1 transfer of the anchor contract to non-perovskite schemas",
        "source_repo": str(FORK), "source_commit": git("rev-parse", "HEAD"),
        "source_tree_clean": not status,
        "source_uncommitted": status,
        "verifier": "General_topic_monthly/scripts/verify_cards.py (independent of its extractor)",
        "n_domains": len(rows),
        "n_fields_total": sum(r["n_fields"] for r in rows),
        "n_fields_verified_total": sum(r["n_fields_verified"] for r in rows),
        "n_cards_total": sum(r["n_cards"] for r in rows),
        "supports": "the verbatim-anchor contract can be re-declared for another "
                    "extraction schema and every extracted field then verifies",
        "does_not_support": "a fabrication reduction in these domains: no ungated arm "
                            "was run, and n is small",
        "caveats": [
            "same extractor model and same operator as the perovskite deployment",
            "both periods ran before the extractor tool-access fix, with default "
            "tool access; every value still had to appear verbatim in its abstract",
            "the source working tree carries uncommitted edits, listed in "
            "source_uncommitted; the verified card files are hashed here",
        ],
    }
    OUT.write_text(json.dumps({"meta": meta, "rows": rows}, indent=1) + "\n",
                   encoding="utf-8")
    for r in rows:
        print(f"{r['domain']}: {r['n_fields_verified']}/{r['n_fields']} fields verified, "
              f"{r['n_cards']} cards, {r['n_metrics']} metrics, models {r['extractor_models']}")
    print(f"source {meta['source_commit'][:7]} clean={meta['source_tree_clean']} -> {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
