"""Splice re-drafted sections of a rebuilt v4 issue into its v5 edition.

WHY THIS EXISTS
The v5 editions are register revisions of v4 (manuscript/<month>_v5/V5_NOTE.md):
same numbers, same citations, shorter sentences. After the external review of
2026-10-09, some v4 sections were re-drafted to pass new gates (G3e body
numbers, G8 novelty) and the v4 issues were rebuilt. Rebuilding v5 from v4
would throw away the register revision of every untouched section, so this
script replaces only the named sections and keeps the rest of v5.

Citation numbers are first-appearance order over the whole body, so replacing
a section can renumber everything after it. Every citation in these editions
is a DOI link, \\href{https://doi.org/<doi>}{<n>}, so the script renumbers by
DOI and rebuilds the reference list from the DOI -> entry map of both
editions. It fails closed on a cited DOI with no reference entry.

It also collapses repeated first-use expansions (each section was drafted on
its own, so the writer spelled ISOS out in several sections).

    python scripts/splice_v5.py 2026-07 --sections 6 7 8 --abstract
    python scripts/splice_v5.py 2026-08 --sections 1
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stages.boilerplate import expand_abbrev  # noqa: E402
from stages.util import run_dir  # noqa: E402

CITE = re.compile(r"\\href\{https://doi\.org/([^}]+)\}\{(\d+)\}")
REF_LINE = re.compile(r"^(\d+)\. (.*)$")
REF_DOI = re.compile(r"https://doi\.org/([^\s\])]+)")


def split_blocks(md: str) -> tuple[str, list[tuple[str, str]]]:
    """Header text, then (heading line, block text) in document order."""
    parts = re.split(r"(?m)^(?=## )", md)
    head, blocks = parts[0], []
    for p in parts[1:]:
        line, _, rest = p.partition("\n")
        blocks.append((line, rest))
    return head, blocks


def key_of(heading: str) -> str:
    m = re.match(r"## (\d+)\. ", heading)
    return m.group(1) if m else heading[3:].strip()


def ref_map(blocks) -> dict[str, str]:
    body = dict((key_of(h), t) for h, t in blocks).get("References", "")
    out = {}
    for line in body.splitlines():
        m = REF_LINE.match(line.strip())
        if not m:
            continue
        d = REF_DOI.search(m.group(2))
        if d:
            out[d.group(1).lower()] = m.group(2)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("month")
    ap.add_argument("--sections", nargs="+", required=True)
    ap.add_argument("--abstract", action="store_true",
                    help="also take the v4 abstract")
    a = ap.parse_args()

    v4p = ROOT / "manuscript" / f"{a.month}_v4" / "manuscript_v4.md"
    v5p = ROOT / "manuscript" / f"{a.month}_v5" / "manuscript_v5.md"
    for p in (v4p, v5p):
        if not p.exists():
            raise SystemExit(f"FAIL-CLOSED: {p} missing")
    h4, b4 = split_blocks(v4p.read_text(encoding="utf-8"))
    h5, b5 = split_blocks(v5p.read_text(encoding="utf-8"))
    new4 = {key_of(h): (h, t) for h, t in b4}
    take = set(a.sections) | ({"Abstract"} if a.abstract else set())
    missing = [k for k in take if k not in new4]
    if missing:
        raise SystemExit(f"FAIL-CLOSED: v4 has no section {missing}")

    out = []
    for h, t in b5:
        k = key_of(h)
        out.append(new4[k] if k in take else (h, t))
    keys = [key_of(h) for h, _ in out]
    if [key_of(h) for h, _ in b4 if key_of(h).isdigit()] != [k for k in keys if k.isdigit()]:
        raise SystemExit("FAIL-CLOSED: v4 and v5 section lists differ")

    # one expansion per document: abstract alone, body as one text
    done: list = []
    for i, (h, t) in enumerate(out):
        if key_of(h).isdigit():
            t2, e = expand_abbrev(t, skip=done)
            done += e
            out[i] = (h, t2)

    # renumber citations by DOI, first appearance over the body
    order: dict[str, int] = {}

    def renum(m):
        d = m.group(1).lower()
        if d not in order:
            order[d] = len(order) + 1
        return f"\\href{{https://doi.org/{m.group(1)}}}{{{order[d]}}}"

    for i, (h, t) in enumerate(out):
        if key_of(h).isdigit():
            out[i] = (h, CITE.sub(renum, t))

    refs = ref_map(b5)
    refs.update(ref_map(b4))         # rebuilt v4 entries win
    lost = [d for d in order if d not in refs]
    if lost:
        raise SystemExit(f"FAIL-CLOSED: cited DOIs with no reference entry: {lost[:5]}")
    ref_body = "\n" + "\n".join(f"{n}. {refs[d]}" for d, n in
                                 sorted(order.items(), key=lambda x: x[1])) + "\n"
    out = [(h, ref_body) if key_of(h) == "References" else (h, t) for h, t in out]

    md = h5 + "".join(f"{h}\n{t}" for h, t in out)
    # No backup file beside the edition: the pre-splice text is in git, and a
    # stray copy in manuscript/ could be picked up by the release tree.
    v5p.write_text(md, encoding="utf-8")
    rd = run_dir(a.month)
    shutil.copy(v5p, rd / "manuscript_v5.md")
    print(json.dumps({"month": a.month, "replaced": sorted(take),
                      "cited": len(order)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
