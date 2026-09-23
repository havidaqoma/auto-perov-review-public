"""Freeze the content contract across a prose rewrite, then verify it held.

The scientific-writing skill is blunt about this being the highest-risk edit
class in a verified pipeline: the build's gates protect tokens and citations,
but nothing in the pipeline can see a SOFTENED BOUND. "0 of 1084, at most
0.35% by Wilson" degrading to "eliminated fabrication" passes every gate and
is a fabrication.

So before rewriting, snapshot every contract-bearing item per file. After
rewriting, verify the sets are unchanged. Only SENTENCES may change.

    python scripts/check_content_contract.py snapshot LABEL glob [glob ...]
    python scripts/check_content_contract.py verify   LABEL glob [glob ...]

Exit code is non-zero when the contract broke, so this can gate a commit.
"""
from __future__ import annotations

import glob as _glob
import json
import pathlib
import re
import sys
from collections import Counter

SNAP = pathlib.Path(__file__).resolve().parents[1] / "runs" / "_style_contract"

# A bare integer inside a word (sec3, S12, H1) is not a datum. Require the
# number to stand alone, and keep any trailing percent sign because "5" and
# "5%" are different claims.
NUM = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?\s*%?")
CITE = re.compile(r"\[@([^\]\s,;]+)")
# The ASSEMBLED manuscript carries no [@doi] markers at all: the build has
# already resolved them into \href{https://doi.org/...}{N} links against a
# numbered reference list. Measured on manuscript/2026-07_v5/manuscript_v5.md:
# 0 [@ markers, 79 numbered references. Tracking only [@...] there would
# silently verify NOTHING, so the href form is a first-class citation.
HREF = re.compile(r"\\href\{(?:https?://doi\.org/)?([^}]+)\}\{(\d+)\}")
TOKEN = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
QTY = re.compile(r"\\qty\{([^}]*)\}\{([^}]*)\}")
# Words that carry calibration. Losing one usually means a bound got stronger.
HEDGE = re.compile(
    r"\b(?:may|might|could|suggests?|suggesting|appears?|seems?|likely|"
    r"approximately|about|roughly|at most|at least|no more than|lower bound|"
    r"upper bound|only|merely|not|never|cannot|unverified|uncertain|"
    r"limitation|caveat|assumed|estimated)\b", re.I)


def items(text: str) -> dict:
    return {
        "numbers": sorted(Counter(n.strip() for n in NUM.findall(text)).items()),
        # Counter, not set. A rewrite that emits the same [@doi] twice passes a
        # set comparison but moves the citation total, which config/gates.yaml
        # gates to [60, 85]. The guard has to see duplication.
        # Both citation dialects, merged into one ledger: [@doi] in the draft
        # caches, \href{doi}{N} in the assembled build output. A file uses one
        # or the other, never both, so the union is unambiguous.
        "cites": sorted(Counter(
            CITE.findall(text) + [d for d, _ in HREF.findall(text)]).items()),
        # The rendered citation NUMBERS are a separate contract: renumbering
        # breaks every cross-reference to the bibliography even when the DOI
        # set is untouched.
        "cite_nums": sorted(Counter(n for _, n in HREF.findall(text)).items()),
        "tokens": sorted(Counter(TOKEN.findall(text)).items()),
        "qty": sorted(Counter(f"{a}|{b}" for a, b in QTY.findall(text)).items()),
        "hedges": len(HEDGE.findall(text)),
        "words": len(text.split()),
    }


def as_counts(v) -> dict:
    """Read either snapshot shape.

    Older snapshots stored cites/tokens as a bare sorted list; the current
    format stores [item, count] pairs. Verifying a rewrite against a snapshot
    taken before that change must not crash, and must not silently compare
    nothing, so normalise both shapes to {item: count}.
    """
    if not v:
        return {}
    if isinstance(v[0], str):
        return {x: 1 for x in v}
    return {k: c for k, c in (tuple(p) for p in v)}


def collect(patterns: list[str]) -> dict:
    out = {}
    for pat in patterns:
        for p in sorted(_glob.glob(pat)):
            f = pathlib.Path(p)
            out[f.as_posix()] = items(f.read_text(encoding="utf-8", errors="replace"))
    return out


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    mode, label, patterns = argv[0], argv[1], argv[2:]
    SNAP.mkdir(parents=True, exist_ok=True)
    store = SNAP / f"{label}.json"
    cur = collect(patterns)
    if not cur:
        print(f"!! no files matched {patterns}")
        return 2

    if mode == "snapshot":
        store.write_text(json.dumps(cur, indent=1), encoding="utf-8")
        tot = sum(v["words"] for v in cur.values())
        print(f"snapshot {label}: {len(cur)} files, {tot} words")
        for f, v in cur.items():
            print(f"  {pathlib.Path(f).name:16s} {v['words']:5d}w  "
                  f"{len(v['numbers']):3d} num  {len(v['cites']):3d} cite  "
                  f"{v['hedges']:3d} hedge")
        return 0

    if mode != "verify":
        print(f"unknown mode {mode!r}")
        return 2

    if not store.exists():
        print(f"!! no snapshot for {label}; run snapshot first")
        return 2
    old = json.loads(store.read_text(encoding="utf-8"))
    bad = 0
    for f, ov in old.items():
        nv = cur.get(f)
        if nv is None:
            print(f"FAIL {f}: file disappeared")
            bad += 1
            continue
        o_num, n_num = as_counts(ov["numbers"]), as_counts(nv["numbers"])
        lost = {k: c for k, c in o_num.items() if n_num.get(k, 0) < c}
        gained = {k: c for k, c in n_num.items() if o_num.get(k, 0) < c}
        o_q, n_q = dict(map(tuple, ov["qty"])), dict(map(tuple, nv["qty"]))
        name = pathlib.Path(f).name
        if lost or gained:
            print(f"FAIL {name}: numbers changed")
            if lost:
                print(f"     lost   {lost}")
            if gained:
                print(f"     gained {gained}")
            bad += 1
        o_c, n_c = as_counts(ov["cites"]), as_counts(nv["cites"])
        if o_c != n_c:
            lost_c = {k: c for k, c in o_c.items() if n_c.get(k, 0) < c}
            gain_c = {k: c for k, c in n_c.items() if o_c.get(k, 0) < c}
            print(f"FAIL {name}: citations changed -{lost_c} +{gain_c}")
            bad += 1
        if as_counts(ov["tokens"]) != as_counts(nv["tokens"]):
            print(f"FAIL {name}: tokens changed")
            bad += 1
        o_cn, n_cn = as_counts(ov.get("cite_nums", [])), as_counts(nv.get("cite_nums", []))
        if o_cn != n_cn:
            lost_n = {k: c for k, c in o_cn.items() if n_cn.get(k, 0) < c}
            gain_n = {k: c for k, c in n_cn.items() if o_cn.get(k, 0) < c}
            print(f"FAIL {name}: citation NUMBERS changed -{lost_n} +{gain_n}")
            bad += 1
        if o_q != n_q:
            print(f"FAIL {name}: \\qty units changed -{o_q} +{n_q}")
            bad += 1
        dh = nv["hedges"] - ov["hedges"]
        dw = nv["words"] - ov["words"]
        # Both directions matter. Dropping a hedge strengthens a claim, which
        # is the classic silent defect. But ADDING one demotes a result the
        # authors stated plainly ("demonstrates" -> "suggests"), which is the
        # over-correction failure mode. Neither is auto-failed, because both
        # can be legitimate; both are surfaced for a human to read.
        mark = ""
        if dh < 0:
            mark = "  <-- REVIEW: hedges dropped, claim may be stronger"
        elif dh > 0:
            mark = "  <-- REVIEW: hedges added, claim may be weakened"
        print(f"{'ok  ' if not mark else 'WARN'} {name:16s} "
              f"words {ov['words']:5d}->{nv['words']:<5d} ({dw:+d})  "
              f"hedges {ov['hedges']:3d}->{nv['hedges']:<3d} ({dh:+d}){mark}")
    print("\nCONTRACT HELD" if not bad else f"\nCONTRACT BROKEN: {bad} defect(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
