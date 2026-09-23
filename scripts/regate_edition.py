"""regate_edition: run the build gates on a FINISHED edition, without rebuilding.

WHY THIS EXISTS
The v5 July and August editions are hand-revised prose on top of the shipped
v4 builds (manuscript/<month>_v5/V5_NOTE.md). Their gates never ran: the gate
report is an output of s18d_build_v4.build(), which rebuilds the manuscript
from the draft caches and would DISCARD the revised text. So v5 shipped with no
gate_report_v5.json, which also meant verify_pdf and the ChemRxiv stage could
not run on it.

This reads the finished markdown and PDF, reconstructs the inputs the build's
gate code takes, and calls the SAME functions the build calls
(s18d_build_v4.text_gates, novelty_gate, page_gate, and the G10 layout
measure). Nothing is re-typed, so a gate cannot pass here that would fail in a
build.

What is reconstructed differently from a build, and recorded in the report
under "_regate" so no reader mistakes this for a build log:
  - body_words / G2 input_freeze are taken from the finished sections with
    citation markup removed. A build counts the raw drafts, whose [@doi]
    markers each count as one word, so the two word counts differ slightly.
  - expanded / notation_counts are informational build logs, not inputs to
    any verdict. They are left empty rather than invented.
  - abs_vals / abs_tokens come from resolve_placeholders on the draft abstract
    template. V5 froze every number as a multiset against v4, so the canonical
    computed values are unchanged by the revision.

CALIBRATION: `--check-against <gate_report.json>` runs the regate on an edition
that DOES have a build report and fails unless every verdict matches. Run it on
the v4 edition before trusting a v5 regate.

    python scripts/regate_edition.py 2026-07 v4 --check-against runs/2026-07_197abe83/gate_report_v4.json
    python scripts/regate_edition.py 2026-07 v5 --prior manuscript/2026-06_v4/manuscript_v4.md --write
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import shutil
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from stages.util import CONFIG, read_jsonl, run_dir  # noqa: E402
from stages.section_map import load_map  # noqa: E402
from stages import s18d_build_v4 as b  # noqa: E402
from stages import editions  # noqa: E402

canon_work_key = b.canon_work_key

SEC_RX = re.compile(r"^## (\d+)\. (.+?)\s*$")
FIG_RX = re.compile(r"\\begin\{figure\}.*?\\includegraphics\[[^\]]*\]\{([^}]+)\}"
                    r".*?\\caption\{(.*?)\}\s*\\end\{figure\}", re.S)
REF_RX = re.compile(r"^(\d+)\. .*?\(https://doi\.org/([^)\s]+)\)\s*$")


CAL_DETAIL = {"G1": ["resolved"], "G2": ["prose_words"],
              "G2b-cite-order": ["first_appearance_sequence"],
              "G2c-cite-count": ["cited"], "G3-abstract": ["words"],
              "G8-novelty": ["prior_issue", "worst_section_ratio"],
              "G9b-cite-links": ["hyperlinked_markers"],
              "G5": ["total_pages", "content_pages"]}


def split_manuscript(md: str) -> dict:
    """Pull abstract, numbered sections, figures and references back out."""
    lines = md.replace("\r\n", "\n").split("\n")
    out = {"ab": None, "secs": {}, "figs": {}, "refs": [], "date": None}
    i_abs = lines.index("## Abstract")
    j = i_abs + 1
    buf = []
    while not lines[j].startswith("**Keywords:**"):
        buf.append(lines[j])
        j += 1
    out["ab"] = "\n".join(buf).strip()

    head = "\n".join(lines[:i_abs])
    m = re.search(r"\\\\\[2\.0em\]\s*\n(.+?)\n\\end\{minipage\}", head)
    out["date"] = m.group(1).strip() if m else None

    cur, buf = None, []

    def flush():
        if cur is None:
            return
        body = "\n".join(buf)
        fm = FIG_RX.search(body)
        if fm:
            out["figs"][cur] = (pathlib.Path(fm.group(1)).name, fm.group(2))
            body = body[:fm.start()] + body[fm.end():]
        out["secs"][cur] = body.strip()

    in_refs = False
    for ln in lines[j:]:
        sm = SEC_RX.match(ln)
        if sm:
            flush()
            cur, buf = sm.group(1), []
            continue
        if ln.startswith("## "):
            flush()
            cur, buf = None, []
            in_refs = ln.strip() == "## References"
            continue
        if in_refs:
            rm = REF_RX.match(ln)
            if rm:
                out["refs"].append((int(rm.group(1)), rm.group(2)))
            continue
        if cur is not None:
            buf.append(ln)
    flush()
    return out


def strip_cites(t: str) -> str:
    t = re.sub(r"\\href\{[^}]*\}\{(\d+)\}", r"\1", t)
    return t


def regate(month: str, ver: str, prior: pathlib.Path | None) -> tuple[dict, dict]:
    rd = run_dir(month)
    if editions.is_release_tree(ROOT):
        # Public release: final edition only, unversioned names.
        md_p = editions.edition_file(ROOT, month, "manuscript", ".md")
    else:
        md_p = ROOT / "manuscript" / f"{month}_{ver}" / f"manuscript_{ver}.md"
    pdf = md_p.with_suffix(".pdf")
    for p in (md_p, pdf):
        if not p.exists():
            raise SystemExit(f"FAIL-CLOSED: {p} missing")
    smap = load_map(month)
    S = json.loads((rd / "stats.json").read_text(encoding="utf-8"))
    G = yaml.safe_load((CONFIG / "gates.yaml").read_text(encoding="utf-8"))
    cards = {c["work_key"]: c for c in read_jsonl(rd / "claim_cards.jsonl")}
    corpus = {r["work_key"]: r for r in read_jsonl(rd / "05_corpus.jsonl")}
    cl = list(cards.values())

    md = md_p.read_text(encoding="utf-8")
    parts = split_manuscript(md)
    ids = [s["id"] for s in smap["sections"]]
    if sorted(parts["secs"], key=int) != ids:
        raise SystemExit(f"FAIL-CLOSED: sections {sorted(parts['secs'])} "
                         f"do not match the section map {ids}")
    secs = {sid: parts["secs"][sid] for sid in ids}
    ab = parts["ab"]

    # reference list -> card keys, in numbered order
    by_canon = {}
    for wk in cards:
        by_canon.setdefault(canon_work_key(wk), []).append(wk)
    for wk, r in corpus.items():
        if r.get("doi"):
            by_canon.setdefault(canon_work_key(r["doi"]), []).append(wk)
    order, unmapped = [], []
    for n, doi in sorted(parts["refs"]):
        cand = sorted(set(by_canon.get(canon_work_key(doi), [])))
        if len(cand) == 1:
            order.append(cand[0])
        else:
            unmapped.append(doi)
    if [n for n, _ in sorted(parts["refs"])] != list(range(1, len(parts["refs"]) + 1)):
        raise SystemExit("FAIL-CLOSED: reference numbers are not 1..N")
    unresolved = re.findall(r"\[@([^\]\s]+)\]", "\n".join(secs.values())) + unmapped
    doi_of = {wk: (corpus.get(wk, {}).get("doi") or "") for wk in order}

    # G2b input, computed exactly as the build computes it (on linked text)
    CITE_RX = r"\[(\d+(?:,\d+)*)\](?![A-Za-z])"
    seq, seen = [], set()
    for m in re.finditer(CITE_RX, "\n".join(strip_cites(secs[s]) for s in ids)):
        grp = [int(x) for x in m.group(1).split(",")]
        if any(x > len(order) or x == 0 for x in grp):
            continue
        for g in grp:
            if g not in seen:
                seen.add(g)
                seq.append(g)

    plain = {s: strip_cites(v) for s, v in secs.items()}
    frozen = {s: {"words": len(v.split()),
                  "sha256": hashlib.sha256(v.encode()).hexdigest()[:16]}
              for s, v in plain.items()}
    body_words = sum(len(v.split()) for v in plain.values())

    ab_raw = (editions.draft_dir(ROOT, rd) / "abstract.md").read_text(
        encoding="utf-8").strip()
    _, abs_vals, abs_tokens = b.resolve_placeholders(ab_raw, S, cl)

    fig_for = parts["figs"]
    md_blocks = [blk for blk in md.replace("\r\n", "\n").split("\n\n")]

    gate = b.text_gates(month=month, ab=ab, secs=secs, order=order,
                        unresolved=unresolved, aliased={},
                        body_words=body_words, smap=smap, frozen=frozen,
                        seq=seq, S=S, cl=cl, abs_vals=abs_vals,
                        abs_tokens=abs_tokens, expanded=[], G=G,
                        notation_counts={}, doi_of=doi_of, fig_for=fig_for,
                        md=md_blocks, prior_path=prior)
    pages, g5 = b.page_gate(pdf, G)
    try:
        g10 = b.measure_title_block(pdf, date_str=parts["date"])
        gate["G10-title-block"] = {"status": g10["status"], "detail": g10}
        if g10.get("title_block_fraction_measured") is not None:
            g5["detail"]["title_block_fraction_measured"] = \
                g10["title_block_fraction_measured"]
    except Exception as e:
        gate["G10-title-block"] = {"status": "warn",
                                   "detail": {"error": str(e)[:160]}}
    gate["G5"] = g5
    info = {"edition": f"{month}_{ver}", "source_markdown": md_p.name,
            "source_pdf": pdf.name, "pages": pages,
            "references": len(order), "date_on_title_block": parts["date"],
            "prior_issue_file": (str(prior.relative_to(ROOT)).replace("\\", "/")
                                 if prior else "build default"),
            "method": ("regate of finished text via scripts/regate_edition.py; "
                       "gate code is s18d_build_v4.text_gates/page_gate. "
                       "body_words counted on finished sections with citation "
                       "markup removed; expanded/notation_counts not re-derived.")}
    return gate, info


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("month")
    ap.add_argument("ver")
    ap.add_argument("--prior", type=pathlib.Path, default=None,
                    help="prior issue markdown for G8 (default: build rule)")
    ap.add_argument("--check-against", type=pathlib.Path, default=None)
    ap.add_argument("--write", action="store_true",
                    help="write gate_report_<ver>.json to run + edition dirs")
    a = ap.parse_args()
    prior = (ROOT / a.prior).resolve() if a.prior else None
    gate, info = regate(a.month, a.ver, prior)
    for k, v in gate.items():
        print(f"  {v['status']:<10} {k:<22} {json.dumps(v['detail'])[:110]}")
    rc = 0
    if a.check_against:
        ref = json.loads((ROOT / a.check_against).read_text(encoding="utf-8"))
        # A gate added after the reference build has no verdict to match;
        # it is listed, not counted as a mismatch.
        newer = sorted(set(gate) - set(ref))
        # "_regate" is the info record a regate writes, not a gate verdict.
        diff = {k: (ref[k].get("status"), gate.get(k, {}).get("status"))
                for k in sorted(ref) if not k.startswith("_")
                if ref[k].get("status") != gate.get(k, {}).get("status")}
        for k, keys in CAL_DETAIL.items():
            for dk in keys:
                rv = ref.get(k, {}).get("detail", {}).get(dk)
                gv = gate.get(k, {}).get("detail", {}).get(dk)
                print(f"    detail {k}.{dk}: build={json.dumps(rv)[:70]} "
                      f"regate={json.dumps(gv)[:70]}")
        print("CALIBRATION", "MATCH" if not diff else f"MISMATCH {diff}",
              f"(gates newer than the build report: {newer or 'none'})")
        rc = 0 if not diff else 1
    if a.write:
        if a.check_against and rc:
            raise SystemExit("refusing to write: calibration failed")
        report = dict(gate)
        report["_regate"] = {"status": "info", "detail": info}
        rd = run_dir(a.month)
        name = f"gate_report_{a.ver}.json"
        (rd / name).write_text(json.dumps(report, indent=2), encoding="utf-8")
        edir = ROOT / "manuscript" / f"{a.month}_{a.ver}"
        shutil.copy(rd / name, edir / name)
        print(f"wrote {rd.name}/{name} and {edir.name}/{name}")
    fails = [k for k, v in gate.items() if v["status"] == "fail"]
    print("FAILING GATES:", fails or "none")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
