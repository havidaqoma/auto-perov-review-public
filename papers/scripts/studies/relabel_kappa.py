"""R1b: intra-rater reliability (kappa) between the primary labels and the re-label.

WHY KAPPA ALONE WOULD MISLEAD HERE. These questions are heavily skewed --
states_certified is ~74% N, isos_protocol ~84% N. Under skew, Cohen's kappa
collapses even when raw agreement is near-perfect: the "kappa paradox". A flag
with 95% agreement can score kappa ~0.0 purely because one answer dominates, and
a reader seeing only kappa concludes the labeller is unreliable when the data
says the opposite.

So four numbers are reported together, never kappa alone:
  raw agreement   what actually happened
  Cohen's kappa   chance-corrected, with its bootstrap CI
  PABAK           prevalence-and-bias-adjusted (2*po - 1), the skew-robust read
  prevalence      so the reader can see WHY kappa and PABAK diverge

FAIL-CLOSED ON THE ARTIFACT. If every judgement matches, that is far more
likely to be localStorage restoring the first pass than a human reproducing
100 judgements exactly. The run refuses to report kappa in that case.

Run: python -u scripts/studies/relabel_kappa.py
"""
from __future__ import annotations

import csv
import json
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from studies.study_common import write_report  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[3]
SHEET = ROOT / "papers" / "studies" / "label_sheet"
COLS = ["states_pce", "states_certified", "states_area", "states_t80",
        "isos_protocol"]


def load(p: pathlib.Path) -> dict[str, dict]:
    return {r["work_key"].strip(): r
            for r in csv.DictReader(p.open(encoding="utf-8-sig"))}


def cohen_kappa(pairs: list[tuple[str, str]]) -> tuple[float, float, dict]:
    """Cohen's kappa, raw agreement, and the marginal counts behind them."""
    n = len(pairs)
    if n == 0:
        return float("nan"), float("nan"), {}
    cats = sorted({v for pr in pairs for v in pr})
    po = sum(1 for a, b in pairs if a == b) / n
    pe = 0.0
    for c in cats:
        pa = sum(1 for a, _ in pairs if a == c) / n
        pb = sum(1 for _, b in pairs if b == c) / n
        pe += pa * pb
    k = (po - pe) / (1 - pe) if pe < 1 else float("nan")
    return k, po, {c: sum(1 for a, _ in pairs if a == c) for c in cats}


def boot_ci(pairs: list[tuple[str, str]], n_boot: int = 4000) -> tuple:
    """Percentile bootstrap. At n=20 the asymptotic SE is not trustworthy."""
    if len(pairs) < 2:
        return (float("nan"), float("nan"))
    rng = random.Random(20260913)
    ks = []
    for _ in range(n_boot):
        s = [pairs[rng.randrange(len(pairs))] for _ in range(len(pairs))]
        k, _, _ = cohen_kappa(s)
        if k == k:                      # drop NaN (degenerate resample)
            ks.append(k)
    if not ks:
        return (float("nan"), float("nan"))
    ks.sort()
    return (round(ks[int(0.025 * len(ks))], 4), round(ks[int(0.975 * len(ks))], 4))


def main() -> int:
    P = load(SHEET / "r1_labels_filled.csv")
    R = load(SHEET / "r1_relabel_filled.csv")
    fr = json.loads((SHEET / "relabel_frame.json").read_text(encoding="utf-8"))
    want = set(fr["work_keys"])

    if set(R) != want:
        raise SystemExit(f"FAIL-CLOSED: re-label keys differ from the "
                         f"pre-registered draw (missing {sorted(want-set(R))[:3]}, "
                         f"extra {sorted(set(R)-want)[:3]})")
    missing = want - set(P)
    if missing:
        raise SystemExit(f"FAIL-CLOSED: {len(missing)} re-labelled papers are "
                         f"absent from the primary sheet")

    rows, all_pairs = [], []
    for c in COLS:
        pairs = [(P[k][c].strip().upper(), R[k][c].strip().upper())
                 for k in sorted(want)]
        pairs = [(a, b) for a, b in pairs if a and b]
        all_pairs += pairs
        k, po, marg = cohen_kappa(pairs)
        lo, hi = boot_ci(pairs)
        n = len(pairs)
        y = sum(1 for a, _ in pairs if a == "Y")
        rows.append(dict(
            flag=c, n=n, agree=sum(1 for a, b in pairs if a == b),
            raw_agreement=round(po, 4),
            kappa=None if k != k else round(k, 4),
            kappa_ci95=[lo, hi],
            pabak=round(2 * po - 1, 4),
            prevalence_Y=round(y / n, 4) if n else None,
            degenerate=bool(k != k),
        ))

    k_all, po_all, _ = cohen_kappa(all_pairs)
    lo, hi = boot_ci(all_pairs)
    n_all = len(all_pairs)
    n_agree = sum(1 for a, b in all_pairs if a == b)

    # A perfect match across every judgement is the localStorage artifact
    # signature, not a reliability result. Refuse rather than report it.
    if n_agree == n_all and n_all > 0:
        raise SystemExit(
            "FAIL-CLOSED: every judgement is identical. That is the "
            "localStorage-restore artifact, not intra-rater reliability. "
            "Re-run the re-label in a private window.")

    disagreements = [
        dict(work_key=k, flag=c, first=P[k][c].strip().upper(),
             second=R[k][c].strip().upper())
        for c in COLS for k in sorted(want)
        if P[k][c].strip().upper() != R[k][c].strip().upper()
    ]

    meta = dict(
        study="R1b intra-rater reliability",
        design="same labeller, same instrument, 20 papers re-labelled",
        measures="kappa is reported WITH PABAK and prevalence: under skew the "
                 "kappa paradox drives kappa down while agreement stays high",
        limitation="intra-rater reliability shows labels are STABLE, not "
                   "CORRECT. A consistently mistaken labeller scores 1.0.",
        n_papers=len(want), n_judgements=n_all, n_agree=n_agree,
        overall_raw_agreement=round(po_all, 4),
        overall_kappa=None if k_all != k_all else round(k_all, 4),
        overall_kappa_ci95=[lo, hi],
        overall_pabak=round(2 * po_all - 1, 4),
        n_disagreements=len(disagreements),
        disagreements=disagreements,
        per_flag=rows,
    )
    write_report("relabel_kappa", rows, meta)
    print(json.dumps({k: v for k, v in meta.items() if k != "per_flag"}, indent=2))
    print("\nper flag:")
    for r in rows:
        print(f"  {r['flag']:18s} n={r['n']:2d} agree={r['agree']:2d} "
              f"po={r['raw_agreement']:.3f} kappa={r['kappa']} "
              f"PABAK={r['pabak']:.3f} prevY={r['prevalence_Y']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
