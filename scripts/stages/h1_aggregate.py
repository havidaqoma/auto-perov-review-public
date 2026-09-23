"""H1 aggregation: union six monthly runs into one half-year corpus.

Reuses yearly_aggregate's proven primitives (canon_work_key, the silent-zero
refusal, the union semantics) but takes an EXPLICIT month list instead of a
year, because a half-year is a window, not a calendar unit.

Nothing is re-extracted. Cards on disk are anchor-verified already; re-running
extraction would perturb every card in a shipped month (handbook 7.8) and cost
~6 hours to re-derive what exists.

Writes runs/2026-H1/ -- a sibling of the monthly run dirs, never inside one.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from stages.util import RUNS, read_jsonl, run_dir  # noqa: E402
from stages.yearly_aggregate import canon_work_key  # noqa: E402

EDITION = "2026-H1"
MONTHS = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]


def edition_dir(create: bool = True) -> pathlib.Path:
    d = RUNS / EDITION
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def available_months(months: list[str]) -> list[str]:
    out = []
    for m in months:
        if not (RUNS / f"{m}.active").exists():
            continue
        rd = run_dir(m, create=False)
        if (rd / "claim_cards.jsonl").exists() and (rd / "stats.json").exists():
            out.append(m)
    return out


def aggregate(months: list[str] = None, require_all: bool = True) -> dict:
    months = months or MONTHS
    avail = available_months(months)
    if require_all and len(avail) != len(months):
        missing = [m for m in months if m not in avail]
        raise SystemExit(
            f"FAIL-CLOSED: {len(avail)}/{len(months)} months built for "
            f"{EDITION}. Missing: {missing}. An H1 issue is assembled from its "
            f"monthly runs; a missing month is not an empty month (7.1).")

    corpus: dict[str, dict] = {}
    cards: dict[str, dict] = {}
    per_month: dict[str, dict] = {}
    dupes = 0

    for m in avail:
        rd = run_dir(m, create=False)
        # MEMBERSHIP from 06_labels, BIBLIOGRAPHY from 05_corpus.
        #
        # Two different facts live in two different files and both are needed:
        #
        # - 05_corpus.jsonl is the deduped corpus BEFORE the 4.4 scope
        #   post-filter. It carries doi, title, venue, publication_date -- the
        #   fields the reference list is built from.
        # - 06_labels.jsonl is what SURVIVES the post-filter, and its `n_kept`
        #   is exactly what each monthly issue reports as `corpus.n`. It
        #   carries axis/lens labels and NO bibliographic fields at all.
        #
        # Reading 05 alone summed to 3414 against the monthly issues' 3328, an
        # 86-work inflation that would have silently enlarged the denominator
        # under every audit percentage while each monthly issue used the
        # smaller one. Reading 06 alone gave the right denominator but left
        # every reference without a DOI, and G9b caught it: 207 works without
        # DOI, zero hyperlinked citation markers.
        #
        # Neither file alone is the corpus. Join them: 06 decides WHICH works
        # are in, 05 says WHAT they are.
        lab = read_jsonl(rd / "06_labels.jsonl")
        bib = {r.get("work_key"): r for r in read_jsonl(rd / "05_corpus.jsonl")}
        c_rows = []
        for r in lab:
            wk = r.get("work_key")
            base = bib.get(wk)
            if base is None:
                # A labelled work with no bibliographic record cannot be cited
                # or listed. Fail closed rather than emit a reference with an
                # empty title (7.1: a hole never ships).
                raise SystemExit(
                    f"FAIL-CLOSED: {m} work_key {wk!r} is in 06_labels but "
                    f"absent from 05_corpus; the reference list would carry an "
                    f"entry with no title or DOI.")
            c_rows.append({**base, **r})
        k_rows = read_jsonl(rd / "claim_cards.jsonl")
        stats = json.loads((rd / "stats.json").read_text(encoding="utf-8"))

        if not k_rows:
            raise SystemExit(
                f"FAIL-CLOSED: {m} resolves but has zero claim cards (7.1).")

        # Anchor verification is a PRECONDITION, not a nicety: the H1 issue
        # inherits every number these cards carry.
        av = rd / "09_anchor_verification.json"
        if not av.exists():
            raise SystemExit(
                f"FAIL-CLOSED: {m} has no anchor verification report. Run "
                f"scripts/verify_anchors.py {m} before aggregating.")
        rep = json.loads(av.read_text(encoding="utf-8"))
        if rep.get("status") != "pass":
            raise SystemExit(
                f"FAIL-CLOSED: {m} anchor verification status="
                f"{rep.get('status')!r}, not 'pass'.")

        for r in c_rows:
            ck = canon_work_key(r.get("work_key", ""))
            if not ck:
                continue
            if ck in corpus:
                dupes += 1
                continue
            corpus[ck] = {**r, "source_month": m}
        for r in k_rows:
            ck = canon_work_key(r.get("work_key", ""))
            if not ck:
                continue
            if ck in cards:
                continue
            cards[ck] = {**r, "source_month": m}

        per_month[m] = {
            "corpus_n": stats.get("corpus.n"),
            "depth_n": stats.get("selection.n_depth"),
            "cards_n": len(k_rows),
            "anchors_n": rep.get("anchors"),
            "axis_depth": {k.split(".")[1]: v for k, v in stats.items()
                           if k.startswith("axes.") and k.endswith(".n_depth")},
        }

    extractors: dict[str, int] = {}
    for c in cards.values():
        mdl = ((c.get("extractor") or {}).get("model")) or "unknown"
        extractors[mdl] = extractors.get(mdl, 0) + 1

    return {
        "edition": EDITION,
        "months": avail,
        "n_months": len(avail),
        "corpus_n": len(corpus),
        "cards_n": len(cards),
        "cross_month_duplicates": dupes,
        "per_month": per_month,
        "extractors": extractors,
        "corpus": list(corpus.values()),
        "cards": list(cards.values()),
    }


def axis_mass(agg: dict) -> dict[str, int]:
    out: dict[str, int] = {}
    for c in agg["cards"]:
        a = c.get("axis")
        if a:
            out[a] = out.get(a, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


def main() -> int:
    agg = aggregate()
    d = edition_dir()
    from stages.util import write_jsonl
    write_jsonl(d / "05_corpus.jsonl", agg["corpus"])
    write_jsonl(d / "claim_cards.jsonl", agg["cards"])
    summary = {k: v for k, v in agg.items() if k not in ("corpus", "cards")}
    summary["axis_mass"] = axis_mass(agg)
    (d / "aggregate.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
