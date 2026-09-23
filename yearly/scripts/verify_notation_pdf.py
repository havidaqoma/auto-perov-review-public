"""Span-level notation verification. Flat PDF text CANNOT see a superscript.

Eighth instance of handbook 7.3. After the notation fix landed, an ad-hoc
scan of `page.get_text()` still reported flat "cm2", "Na+", "PbI2" and
"Pb2+" -- so it looked like the fix had not worked. It had. Inspecting the
same line at SPAN level showed:

    size=10.91  y=490.21  text='cm'
    size= 7.64  y=488.89  text='2'      <- smaller font, raised baseline

That is a correct superscript. `get_text()` concatenates spans into one
string and discards font size and baseline, so "cm" + "2" reads as "cm2"
whether or not the 2 is raised. **A flat-text check can never verify
typography.**

This module compares each candidate token against its neighbours:
  - a superscript/subscript span is SMALLER than the body font
  - a superscript sits HIGHER than the baseline, a subscript LOWER

Both conditions must hold, because a smaller span at the same baseline is
just small text (a caption), and a raised span at body size is a rendering
artefact, not notation.
"""
from __future__ import annotations

import pathlib
import re
import sys

# Tokens that must render with a raised or lowered digit. Each entry is
# (label, base, script, kind) where `script` is what must be raised/lowered.
SUPERSCRIPT_CASES = [
    ("area unit", "cm", "2", "super"),
    ("volume unit", "cm", "3", "super"),
    ("cation Na", "Na", "+", "super"),
    ("cation Pb", "Pb", "2+", "super"),
    ("cation Sn", "Sn", "2+", "super"),
    ("inverse unit", "V", "-1", "super"),
]
SUBSCRIPT_CASES = [
    ("lead iodide", "PbI", "2", "sub"),
    ("tin oxide", "SnO", "2", "sub"),
    ("titanium oxide", "TiO", "2", "sub"),
    ("nickel oxide", "NiO", "x", "sub"),
    ("fullerene", "C", "60", "sub"),
]

SIZE_RATIO_MAX = 0.85     # script span must be <=85% of the body size
BASELINE_EPS = 0.30       # minimum baseline offset in points


def _body_size(pages) -> float:
    """Modal span size across the document = the body font size."""
    from collections import Counter
    c: Counter = Counter()
    for pg in pages:
        for blk in pg.get_text("dict")["blocks"]:
            for ln in blk.get("lines", []):
                for sp in ln["spans"]:
                    if sp["text"].strip():
                        c[round(sp["size"], 2)] += len(sp["text"])
    return c.most_common(1)[0][0] if c else 11.0


def scan(pdf_path: str | pathlib.Path) -> dict:
    """Return per-case evidence of correct scripting, plus any flat hits."""
    import pymupdf

    doc = pymupdf.open(str(pdf_path))
    pages = [doc[i] for i in range(doc.page_count)]
    body = _body_size(pages)

    # Collect every line as an ordered span list once.
    lines: list[list[dict]] = []
    for pg in pages:
        for blk in pg.get_text("dict")["blocks"]:
            for ln in blk.get("lines", []):
                spans = [s for s in ln["spans"] if s["text"] != ""]
                if spans:
                    lines.append(spans)

    results: dict[str, dict] = {}
    for label, base, script, kind in SUPERSCRIPT_CASES + SUBSCRIPT_CASES:
        good, flat = 0, 0
        for spans in lines:
            for i, sp in enumerate(spans):
                if not sp["text"].rstrip().endswith(base):
                    continue
                nxt = spans[i + 1] if i + 1 < len(spans) else None
                if nxt is None or not nxt["text"].lstrip().startswith(script):
                    # base and script may share one span => flat
                    joined = sp["text"] + (nxt["text"] if nxt else "")
                    if re.search(re.escape(base) + re.escape(script),
                                 sp["text"]):
                        flat += 1
                    continue
                smaller = nxt["size"] <= body * SIZE_RATIO_MAX
                dy = sp["bbox"][1] - nxt["bbox"][1]     # +ve => script higher
                if kind == "super":
                    placed = smaller and dy > BASELINE_EPS
                else:
                    placed = smaller and dy < -BASELINE_EPS
                if placed:
                    good += 1
                else:
                    flat += 1
        if good or flat:
            results[label] = {"token": base + script, "kind": kind,
                              "correct": good, "flat": flat}

    doc.close()
    return {"body_font_size": body, "cases": results,
            "flat_total": sum(v["flat"] for v in results.values()),
            "correct_total": sum(v["correct"] for v in results.values())}


def main(arg: str, version: str = "v4") -> int:
    """Accept either a month ("2026-06") or a direct PDF path.

    It used to take a path only, and defaulted to a HARDCODED
    "manuscript/2026-08_v4/manuscript_v4.pdf". That is the same defect class
    as the month hardcoded in five sites (handbook 7.6 #2): running it during
    the June cycle silently re-verified August's PDF and reported PASS for a
    file the operator was not building. Every verifier now takes <month> [v4]
    like verify_pdf.py, so the month can only come from argv.
    """
    if re.fullmatch(r"\d{4}-\d{2}", arg):
        pdf_path = (pathlib.Path(__file__).resolve().parents[1]
                    / "manuscript" / f"{arg}_{version}"
                    / f"manuscript_{version}.pdf")
        if not pdf_path.exists():
            print(f"no such manuscript: {pdf_path}")
            return 1
    else:
        pdf_path = pathlib.Path(arg)
    print(f"pdf: {pdf_path}")
    rep = scan(pdf_path)
    print(f"body font size: {rep['body_font_size']} pt")
    if not rep["cases"]:
        print("no notation tokens found (nothing to verify)")
        return 0
    width = max(len(k) for k in rep["cases"])
    for label, v in sorted(rep["cases"].items()):
        flag = "PASS" if v["flat"] == 0 else "FAIL"
        print(f"  {flag}  {label:<{width}}  {v['token']:<6} "
              f"{v['kind']:<5} correct={v['correct']} flat={v['flat']}")
    ok = rep["flat_total"] == 0
    print(f"\n{'ALL NOTATION CORRECTLY SCRIPTED' if ok else 'FLAT NOTATION FOUND'}"
          f"  ({rep['correct_total']} correct, {rep['flat_total']} flat)")
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: verify_notation_pdf.py <month|pdf_path> [version]")
        sys.exit(2)
    sys.exit(main(sys.argv[1],
                  sys.argv[2] if len(sys.argv) > 2 else "v4"))
