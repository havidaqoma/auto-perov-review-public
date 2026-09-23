"""v2 main-text TABLES, generated from anchor-verified numbers only.

A table earns main-text space on the same terms as a figure (handbook 5): it
must carry an argument the prose cannot make in a sentence. Five are emitted;
which reach the main text is decided by the section map, and the rest go to the
SI.

    T1  Device family state of the art      -- the spine of the whole issue
    T2  Certified champion per family       -- every number with its provenance
    T3  Efficiency vs aperture area         -- the cell-to-module gap, quantified
    T4  Reporting completeness by family    -- who verifies what
    T5  Family x month attention matrix     -- what moved over six months

Hard rules, all inherited:

- NO literal data in this file. Every value is read from stats.json's family.*
  keys, which h1_family_stats computed from cards. A hardcoded number in a
  table is handbook 7.2 with extra steps.
- A cell with no evidence prints an em-rule, never 0 and never a blank. "0"
  asserts a measurement of zero; "--" says nothing was reported.
- Every certified value passed anchor_contradicts_family, so no table can
  repeat the 32.95%-module defect.
- Markdown here, LaTeX by the build. The writer never sees a table and cannot
  alter one (handbook 0.1).
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from stages.util import RUNS                                    # noqa: E402
from stages.device_family import FAMILIES, LABEL, SHORT         # noqa: E402

EDITION = "2026-H1"
MONTH_LAB = {"2026-01": "Jan", "2026-02": "Feb", "2026-03": "Mar",
             "2026-04": "Apr", "2026-05": "May", "2026-06": "Jun"}
DASH = "--"          # md_esc turns this into an en-rule; never print 0


def _f(x, unit: str = "", nd: int | None = None) -> str:
    """Render a value, or an em-rule when there is no evidence."""
    if x is None:
        return DASH
    if isinstance(x, float) and nd is not None:
        return f"{x:.{nd}f}{unit}"
    if isinstance(x, float) and x == int(x):
        return f"{int(x)}{unit}"
    return f"{x}{unit}"


def table1_family_state(S: dict) -> dict:
    """T1: what each device family achieved, and on how much evidence."""
    head = ["Device family", "Papers", "Certified (n)", "Certified (%)",
            "Best certified PCE", "Best self-reported PCE",
            "Largest area", "Longest T80"]
    rows = []
    for f in FAMILIES:
        p = f"family.{f}."
        rows.append([
            # SHORT, not LABEL. LABEL["hyb"] is 43 characters
            # ("Perovskite/silicon and other hybrid tandems") with no break
            # point after the slash, so in an eight-column table it overflowed
            # the first column and printed ON TOP of the Papers value, making
            # that row's paper count unreadable. Havid found it by reading the
            # page. Tables 4 and 5 already used SHORT and rendered correctly,
            # which is the tell: the same quantity was formatted two ways and
            # only one of them fitted (handbook 7.6 #12, one guard applied in
            # one consumer). The full name is defined once in the table note.
            SHORT[f],
            _f(S.get(p + "n_cards")),
            _f(S.get(p + "n_certified")),
            _f(S.get(p + "pct_certified"), "%"),
            _f(S.get(p + "top_certified"), "%"),
            _f(S.get(p + "top_champion"), "%"),
            _f(S.get(p + "max_area_cm2"), " cm2"),
            _f(S.get(p + "max_t80_h"), " h"),
        ])
    unspec = S.get("family.unspecified_tandem_n")
    note = (
        "Device families are abbreviated in the first column: \"Hybrid "
        "tandem\" is a perovskite absorber paired with a non-perovskite "
        "partner, silicon in most cases and otherwise an organic, "
        "chalcopyrite, telluride or kesterite cell. "
        "Papers are depth-tier records assigned to exactly one family by the "
        "device named in the quotation carrying each number, not by the paper's "
        "title. Best-certified values exclude any value whose own quotation "
        "names a different device family, so a tandem-cell record reported "
        "inside a module study is not counted as a module result. Simulation "
        "and review papers are excluded from every measured value, as are "
        "efficiencies measured under indoor or low-light illumination, which "
        "are not comparable to one-sun values. "
        f"{unspec} tandem papers name no partner and are grouped with "
        "all-perovskite tandems; they are reported separately in the "
        "Supplementary Information. An em-rule means no value was reported, "
        "which is not the same as a reported zero.")
    return {"id": "T1", "title": "State of the art by device family, "
            "January-June 2026", "head": head, "rows": rows, "note": note}


def table2_champions(S: dict) -> dict:
    """T2: the single best certified device per family, fully traceable."""
    head = ["Device family", "Certified PCE", "Aperture area",
            "Architecture", "Month", "Venue"]
    rows = []
    keys = []
    for f in FAMILIES:
        ch = S.get(f"family.{f}.champion")
        if not ch:
            # SHORT here too, for the same reason as T1: LABEL["hyb"] is 43
            # characters and overflows into the next column.
            rows.append([SHORT[f], DASH, DASH, DASH, DASH, DASH])
            keys.append(None)
            continue
        rows.append([
            SHORT[f],
            _f(ch.get("value"), "%"),
            _f(ch.get("area_cm2"), " cm2"),
            _f(ch.get("architecture")),
            MONTH_LAB.get(ch.get("month"), _f(ch.get("month"))),
            _f(ch.get("venue")),
        ])
        keys.append(ch.get("work_key"))
    note = ("Each row resolves to exactly one extraction record, cited in the "
            "column at the end of the corresponding row in the Supplementary "
            "Information, and every value appears verbatim in the cited "
            "paper's own abstract. Aperture area is shown only where the same "
            "paper reported it; an em-rule means the area was not stated "
            "alongside the certified value.")
    return {"id": "T2", "title": "Best independently certified device in each "
            "family, with provenance", "head": head, "rows": rows,
            "note": note, "work_keys": keys}


def table3_area_ladder(S: dict) -> dict:
    """T3: the cell-to-module gap, as a ladder rather than a scatter."""
    ladder = S.get("family.area_ladder") or []
    head = ["Aperture area (cm2)", "Devices", "Best certified",
            "Best self-reported", "Median self-reported"]
    rows = []
    for r in ladder:
        rows.append([
            r.get("band_cm2", DASH),
            _f(r.get("n")) if r.get("n") else DASH,
            _f(r.get("best_certified"), "%"),
            _f(r.get("best_champion"), "%"),
            _f(r.get("median_champion"), "%"),
        ])
    note = ("Every device in the half year that reported an aperture or active "
            "area, binned by decade. The median column is the more informative "
            "one: a best value in a band can be a single outlier, while the "
            "median describes what the band routinely achieves. Devices "
            "reporting no area cannot appear here, which is itself a reporting "
            "limitation rather than an absence of large-area work.")
    return {"id": "T3", "title": "Reported efficiency against device area",
            "head": head, "rows": rows, "note": note}


def table4_reporting(S: dict) -> dict:
    """T4: reporting completeness, cut by family. Who verifies what."""
    head = ["Device family", "Papers", "States an efficiency",
            "Independently certified", "States an area",
            "Reports T80", "Names an ISOS protocol"]
    rows = []
    for f in FAMILIES:
        p = f"family.{f}."
        rows.append([
            SHORT[f],
            _f(S.get(p + "n_cards")),
            _f(S.get(p + "pct_champion"), "%"),
            _f(S.get(p + "pct_certified"), "%"),
            _f(S.get(p + "pct_area"), "%"),
            _f(S.get(p + "pct_t80"), "%"),
            _f(S.get(p + "pct_isos"), "%"),
        ])
    note = ("Percentages are of that family's depth-tier papers. These are "
            "detection rates over abstracts, not audits of experimental "
            "practice: a protocol that is not named in an abstract may still "
            "have been followed, so each figure is a lower bound. The ISOS "
            "column counts a specified protocol such as ISOS-L-1; a paper "
            "referring to ISOS protocols without naming one is not counted.")
    return {"id": "T4", "title": "Reporting completeness by device family",
            "head": head, "rows": rows, "note": note}


def table5_attention(S: dict) -> dict:
    """T5: family x month. Did attention move between device families?"""
    mm = S.get("family.month_matrix") or {}
    months = list(MONTH_LAB)
    head = ["Device family"] + [MONTH_LAB[m] for m in months] + ["Total"]
    rows = []
    for f in FAMILIES:
        per = mm.get(f, {})
        vals = [per.get(m, 0) for m in months]
        rows.append([SHORT[f]] + [_f(v) if v else DASH for v in vals]
                    + [_f(sum(vals))])
    tot = [sum((mm.get(f, {}) or {}).get(m, 0) for f in FAMILIES) for m in months]
    rows.append(["**All families**"] + [f"**{v}**" for v in tot]
                + [f"**{sum(tot)}**"])
    note = ("Depth-tier papers per family per month. Month-to-month movement "
            "of a few papers is not a trend: the corpus is assembled from "
            "indexed records, and indexing completeness itself varies across "
            "the window, with the earliest month the least complete. Read the "
            "column totals before reading any single row.")
    return {"id": "T5", "title": "Depth-tier papers by device family and month",
            "head": head, "rows": rows, "note": note}


BUILDERS = [table1_family_state, table2_champions, table3_area_ladder,
            table4_reporting, table5_attention]

# Which tables the MAIN text carries, and which are SI. T5 is a corpus
# statistic rather than a scientific argument, so it goes to the SI by the
# same rule that demoted the audit bars and the corpus funnel (handbook 5).
MAIN_TABLES = ["T1", "T2", "T3", "T4"]
SI_TABLES = ["T5"]


def build_all(S: dict) -> dict:
    out = {}
    for fn in BUILDERS:
        t = fn(S)
        out[t["id"]] = t
    return out


def to_markdown(t: dict) -> str:
    """Markdown table. The build converts to LaTeX; the writer never sees it."""
    lines = [f"**Table {t['id'][1:]}.** {t['title']}", ""]
    lines.append("| " + " | ".join(t["head"]) + " |")
    lines.append("|" + "|".join(["---"] * len(t["head"])) + "|")
    for r in t["rows"]:
        lines.append("| " + " | ".join(str(x) for x in r) + " |")
    if t.get("note"):
        lines += ["", t["note"]]
    return "\n".join(lines)


def main() -> int:
    d = RUNS / EDITION
    S = json.loads((d / "stats.json").read_text(encoding="utf-8"))
    tables = build_all(S)
    (d / "14_tables.json").write_text(json.dumps(tables, indent=2),
                                      encoding="utf-8")
    md = "\n\n".join(to_markdown(tables[k]) for k in
                     MAIN_TABLES + SI_TABLES if k in tables)
    (d / "14_tables.md").write_text(md, encoding="utf-8")

    # 7.1: a zero is a bug until proven otherwise.
    bad = []
    for k, t in tables.items():
        if not t["rows"]:
            bad.append(f"{k}: no rows")
        filled = sum(1 for r in t["rows"] for c in r if str(c) != DASH)
        if filled <= len(t["rows"]):
            bad.append(f"{k}: every data cell is an em-rule")
    for k in MAIN_TABLES:
        if k not in tables:
            bad.append(f"{k}: missing but declared main-text")
    if bad:
        print("FAIL:\n  " + "\n  ".join(bad))
        return 1

    print(f"[h1v6-tables] {len(tables)} tables -> 14_tables.json / .md")
    for k in MAIN_TABLES + SI_TABLES:
        t = tables[k]
        print(f"   {k}  {len(t['rows'])} rows x {len(t['head'])} cols  "
              f"{'MAIN' if k in MAIN_TABLES else 'SI  '}  {t['title'][:52]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
