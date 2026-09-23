"""Span-geometry legibility gate for figure PDFs (handbook 4.4b, level 2).

WHY THIS EXISTS. Figures were shipped after looking at file sizes. File size
cannot see a collision. `page.get_text()` cannot see one either: it
concatenates spans and discards geometry, so an axis label sitting on top of
a tick label reads as ordinary text. The same lesson as notation
verification, applied to figures instead of chemistry.

THE GATE. For every text span in the rendered figure PDF, read its bounding
box from `page.get_text("dict")` and assert that no two boxes overlap by more
than MAX_OVERLAP_PT in BOTH axes simultaneously. Overlap in one axis only is
normal and must not fail: a column of tick labels shares an x range, a row of
them shares a y range. A genuine collision overlaps in both.

WHAT IS DELIBERATELY NOT FAILED.
  - Spans on different pages (a figure is one page, but stay explicit).
  - Sub-threshold touching: antialiased glyph boxes routinely abut by a few
    hundredths of a point.
  - Empty and whitespace-only spans, which carry a box but no ink.

Run: python -u scripts/verify_figure_pdf.py papers/system/fig
     python -u scripts/verify_figure_pdf.py path/to/one.pdf
Exit code is non-zero on any collision, so a build cannot promote a figure
whose text overlaps.
"""
from __future__ import annotations

import pathlib
import sys

MAX_OVERLAP_PT = 0.6      # handbook 9.4 threshold
MIN_FONT_PT = 7.0         # print-legible floor
# Raised from 5.5. At 5.5 the gate passed Figure 2 with 6.0 pt defect
# labels while every other figure sat at 7.4 pt, so the operator caught
# by eye what the gate was built to catch. A threshold that only fails
# on the unreadable extreme does not enforce a legibility standard.


def _spans(pdf_path: pathlib.Path) -> list[dict]:
    import pymupdf

    doc = pymupdf.open(str(pdf_path))
    out: list[dict] = []
    for pno in range(doc.page_count):
        pg = doc[pno]
        for blk in pg.get_text("dict")["blocks"]:
            for ln in blk.get("lines", []):
                for sp in ln["spans"]:
                    if not sp["text"].strip():
                        continue
                    out.append({"page": pno, "text": sp["text"],
                                "size": sp["size"], "bbox": tuple(sp["bbox"])})
    doc.close()
    return out


def _overlap(a: tuple, b: tuple) -> tuple[float, float]:
    """Return (x_overlap, y_overlap) in points; zero when disjoint."""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    dx = min(ax1, bx1) - max(ax0, bx0)
    dy = min(ay1, by1) - max(ay0, by0)
    return (max(0.0, dx), max(0.0, dy))


def scan(pdf_path: pathlib.Path) -> dict:
    spans = _spans(pdf_path)
    collisions = []
    for i in range(len(spans)):
        for j in range(i + 1, len(spans)):
            a, b = spans[i], spans[j]
            if a["page"] != b["page"]:
                continue
            dx, dy = _overlap(a["bbox"], b["bbox"])
            # A real collision overlaps in BOTH axes. One axis alone is just
            # alignment: a column of tick labels shares an x range by design.
            if dx > MAX_OVERLAP_PT and dy > MAX_OVERLAP_PT:
                collisions.append({
                    "a": a["text"][:40], "b": b["text"][:40],
                    "dx": round(dx, 2), "dy": round(dy, 2),
                    "page": a["page"],
                    "a_bbox": [round(v, 1) for v in a["bbox"]],
                    "b_bbox": [round(v, 1) for v in b["bbox"]],
                })
    tiny = [{"text": s["text"][:40], "size": round(s["size"], 2)}
            for s in spans if s["size"] < MIN_FONT_PT]
    return {"file": pdf_path.name, "n_spans": len(spans),
            "collisions": collisions, "tiny": tiny,
            "min_size": round(min((s["size"] for s in spans), default=0.0), 2)}


def main(argv: list[str]) -> int:
    target = pathlib.Path(argv[0])
    if target.is_dir():
        pdfs = sorted(p for p in target.glob("*.pdf"))
    else:
        pdfs = [target]
    if not pdfs:
        print(f"FAIL-CLOSED: no figure PDFs at {target}")
        return 2

    bad = 0
    for p in pdfs:
        rep = scan(p)
        ok = not rep["collisions"] and not rep["tiny"]
        flag = "PASS" if ok else "FAIL"
        print(f"  {flag}  {rep['file']:<34} spans={rep['n_spans']:<4} "
              f"min_font={rep['min_size']}pt "
              f"collisions={len(rep['collisions'])}")
        for c in rep["collisions"]:
            print(f"         overlap dx={c['dx']}pt dy={c['dy']}pt  "
                  f"{c['a']!r} vs {c['b']!r}")
            print(f"           {c['a_bbox']}  {c['b_bbox']}")
        for t in rep["tiny"]:
            print(f"         font {t['size']}pt < {MIN_FONT_PT}pt: {t['text']!r}")
        if not ok:
            bad += 1

    print(f"\n{len(pdfs)} figures checked, {bad} failing "
          f"(threshold {MAX_OVERLAP_PT} pt both axes, min font {MIN_FONT_PT} pt)")
    return 1 if bad else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: verify_figure_pdf.py <fig_dir|pdf_path>")
        sys.exit(2)
    sys.exit(main(sys.argv[1:]))
