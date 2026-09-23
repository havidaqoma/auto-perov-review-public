"""yearly_tables: main-text tables, generated from evidence. No prose.

WHY TABLES AND NOT MORE FIGURES
-------------------------------
Havid asked for "meaningful tables we can show in the main manuscript"
(2026-09-10). A table earns main-text space where a figure cannot: when a
reader needs to READ a specific value and its provenance rather than see a
shape. Three cases in this issue qualify:

  T1  the champion table -- the year's best verified device in each class,
      with its own physical bound beside it. A reader checking "is 33.15%
      plausible?" needs the number, the class and the limit on one line.
  T2  reporting completeness per device class -- which classes report their
      own measurements and which do not. A figure would show the shape; the
      table lets a reader cite the denominator.
  T3  the evidence ledger -- how many papers, values and verified quotations
      stand behind each section. This is the table that makes the review
      auditable rather than assertable.

EVERY CELL IS COMPUTED
----------------------
Nothing here is typed in. Values come from claim cards and stats_yearly.json,
and the tables are emitted as BOTH markdown (for the manuscript) and CSV (for
the data pack), from one computation, so the two can never disagree.

CERTIFIED AND SELF-REPORTED ARE NEVER MIXED IN ONE CELL
-------------------------------------------------------
T1 carries them in separate columns. Merging them would reproduce the defect
the whole project exists to prevent: a champion value measured on a 0.05 cm2
laboratory cell and an independently certified value are not the same kind of
evidence, and a single "best PCE" column silently equates them.

SIMULATION IS EXCLUDED FROM EVERY PERFORMANCE CELL
--------------------------------------------------
`lens in ("theory", "review")` never contributes a number to T1. It DOES
contribute to T3's paper counts, because a theory paper is genuinely part of
the section's evidence base -- it simply cannot supply a measured value.
"""
from __future__ import annotations

import csv
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from stages.device_class import (CLASS_LABEL, CLASS_ORDER,  # noqa: E402
                                 CLASS_PCE_LIMIT, classify,
                                 illumination_of, is_indoor_value)

NON_MEASURED = ("theory", "review")

# Set by build_tables(). The illumination fallback needs the full
# abstract, and threading it through every helper signature would
# touch code that has nothing to do with illumination.
_ABSTRACTS: dict = {}


def _v(c: dict, k: str):
    src = c.get("stability") if k in ("t80_h", "duration_h") else c.get("performance")
    f = (src or {}).get(k)
    return f["value"] if isinstance(f, dict) and f.get("value") is not None else None


def _anchor(c: dict, k: str) -> str:
    src = c.get("stability") if k in ("t80_h",) else c.get("performance")
    f = (src or {}).get(k)
    return (f or {}).get("anchor", "") if isinstance(f, dict) else ""


def _v_am15(c: dict, k: str, source: str = ""):
    """A performance value ONLY when it was measured under solar conditions.

    Returns None for an indoor or weak-light measurement. Every AM1.5G
    detailed-balance bound in this file -- 29.4% single junction, 47.6%
    two-junction -- is derived for the solar spectrum, so an indoor value
    compared against one is a category error even though the number, the
    extraction and the device class are all correct.

    Measured on 2025: two single-junction cards report 33.2% and 30.3%
    under weak light. Plotted against the 29.4% line they made the review
    appear to show a field-wide integrity problem. They show nothing of the
    kind; they are indoor photovoltaics, where exceeding the solar SQ limit
    is ordinary physics.

    An UNMARKED value is kept. Standard conditions are the overwhelming
    default in this literature, and assuming otherwise would silently drop
    most of the corpus.
    """
    val = _v(c, k)
    if val is None:
        return None
    return None if is_indoor_value(_anchor(c, k), val, source) else val


def _fmt(x) -> str:
    if x is None:
        return "not reported"
    if isinstance(x, float) and x == int(x):
        return str(int(x))
    return str(x)


def _md_table(header: list, rows: list) -> list:
    """Pipe table whose SEPARATOR WIDTHS carry the column proportions.

    Why the dashes are not all "---"
    --------------------------------
    Pandoc sets pipe-table column widths from the width of each dash run in
    the separator line, normalised to a fraction of \\linewidth. A uniform
    `|---|---|` therefore asks for SIX EQUAL columns and pandoc emits
    `p{... * real{0.1667}}` for every one of them -- 81.3 pt at this
    geometry.

    That is too narrow for column 1. Measured on the shipped v1 PDF (page 5):
    "Perovskite/silicon" is a single unbreakable token -- LaTeX will not break
    at "/" -- and renders to x=152.6 while column 2 starts at x=149.4. A
    `p{}` column does not clip, so the label RAN INTO "Best certified".
    That is the overlap Havid read off the page (2026-09-13).

    Allocate on the LONGEST TOKEN, not the longest cell
    ---------------------------------------------------
    The first attempt sized each dash run by the longest whole CELL. That
    fixed column 1 and broke column 3: "Device class" has a 43-character cell
    and only an 18-character longest token, so it took 43/117 of the width
    while needing far less, starving "Measured" (8 characters, and its own
    header is one unbreakable 8-character word) down to 28.4 pt when the word
    renders 45.8 pt wide. Measured on that build: "Measured" overlapped
    "review" by 5.42 pt. Trading one overlap for another is not a fix.

    What actually sets a column's MINIMUM width is its longest unbreakable
    token, because a multi-word cell may wrap but a single word may not.
    Allocating in proportion to the longest token therefore satisfies every
    column's hard floor by construction, and wrapping absorbs the rest.
    Verified by measurement on the rendered page, not by argument: every
    device-class label and every header word clears its neighbour.

    MIN_DASH keeps a one-character column above pandoc's 3-character minimum
    separator.
    """
    MIN_DASH = 3
    cols = len(header)
    widths = []
    for ci in range(cols):
        cells = [str(header[ci])] + [str(r[ci]) for r in rows if ci < len(r)]
        # longest unbreakable token: the hard floor for this column
        tok = max((max((len(t) for t in c.split()), default=1) for c in cells),
                  default=MIN_DASH)
        widths.append(tok)
    out = ["| " + " | ".join(str(h) for h in header) + " |",
           "|" + "|".join("-" * max(MIN_DASH, w) for w in widths) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(x) for x in r) + " |")
    return out


def _by_class(cards: list, abstracts: dict) -> dict:
    g = {k: [] for k in CLASS_ORDER}
    for c in cards:
        g[classify(c, abstracts.get(c.get("work_key"), ""))].append(c)
    return g


# ---------------------------------------------------------------- T1
def table1(groups: dict) -> tuple[list, list, list]:
    """Best verified and best self-reported device in each class.

    The physical bound sits in its own column so a reader can check any
    value against the ceiling that actually applies to it. That is the
    whole point of a device-class spine: 33.15% is impossible for a single
    junction and unremarkable for a tandem, and only the class tells you
    which sentence is true.
    """
    header = ["Device class", "Best certified (%)", "Best self-reported (%)",
              "Detailed-balance limit (%)", "Papers with a certified value",
              "Papers read"]
    rows, csv_rows = [], []
    for k in CLASS_ORDER:
        cards = groups[k]
        if not cards:
            continue
        meas = [c for c in cards if c.get("lens") not in NON_MEASURED]
        # _v_am15, NOT _v. Every limit in the right-hand column is an AM1.5G
        # detailed-balance bound, so an indoor value in the same row would be
        # compared against a ceiling derived for a different spectrum.
        # `src` is the FULL abstract. Guard 3 caps an anchor at 25 words and
        # can cut the illumination marker off the end ("...under 1000" with
        # "lux" one word beyond), so the source is the fallback. Guard 3
        # governs what may be QUOTED, not what the pipeline may KNOW.
        def _src(c):
            return _ABSTRACTS.get(c.get("work_key"), "")
        cert = [(_v_am15(c, "pce_certified", _src(c)), c) for c in meas
                if _v_am15(c, "pce_certified", _src(c)) is not None]
        champ = [(_v_am15(c, "pce_champion", _src(c)), c) for c in meas
                 if _v_am15(c, "pce_champion", _src(c)) is not None]
        n_indoor = sum(
            1 for c in meas for kk in ("pce_certified", "pce_champion")
            if _v(c, kk) is not None and _v_am15(c, kk, _src(c)) is None)
        best_cert = max(cert, key=lambda x: x[0]) if cert else None
        best_champ = max(champ, key=lambda x: x[0]) if champ else None
        limit = CLASS_PCE_LIMIT[k]
        rows.append([
            CLASS_LABEL[k],
            _fmt(best_cert[0]) if best_cert else "none reported",
            _fmt(best_champ[0]) if best_champ else "none reported",
            _fmt(limit), len(cert), len(cards)])
        csv_rows.append([
            k, CLASS_LABEL[k],
            best_cert[0] if best_cert else "",
            best_cert[1]["work_key"] if best_cert else "",
            (_anchor(best_cert[1], "pce_certified") if best_cert else
             "").replace("\n", " "),
            best_champ[0] if best_champ else "",
            best_champ[1]["work_key"] if best_champ else "",
            limit, len(cert), len(meas), len(cards), n_indoor])
    csv_header = ["device_class", "label", "best_certified_pct",
                  "best_certified_work_key", "best_certified_anchor",
                  "best_self_reported_pct", "best_self_reported_work_key",
                  "detailed_balance_limit_pct", "n_certified",
                  "n_measured_papers", "n_papers",
                  "n_values_excluded_indoor"]
    return header, rows, [csv_header] + csv_rows


# ---------------------------------------------------------------- T2
def table2(groups: dict) -> tuple[list, list, list]:
    """Reporting completeness per device class.

    Computed from the reporting_flags each card carries, which are
    RECOMPUTED BY SCRIPT during extraction rather than taken from the
    model's own assessment.

    Every rate is a lower bound: the flags read abstracts, and the
    hand-labelled validation set does not exist yet. The caption says so.
    """
    header = ["Device class", "Certification stated", "Area stated",
              "Stabilised output", "ISOS protocol named", "Papers read"]
    rows, csv_rows = [], []
    flags = [("states_certification", "certification"),
             ("states_area", "area"),
             ("states_stabilised", "stabilised"),
             ("isos_labelled", "isos")]
    for k in CLASS_ORDER:
        cards = groups[k]
        if not cards:
            continue
        n = len(cards)
        vals = []
        for fk, _ in flags:
            hit = sum(1 for c in cards
                      if (c.get("reporting_flags") or {}).get(fk))
            vals.append((hit, round(100.0 * hit / n, 1) if n else 0.0))
        rows.append([CLASS_LABEL[k]]
                    + [f"{p}% ({h})" for h, p in vals] + [n])
        csv_rows.append([k, CLASS_LABEL[k]]
                        + [x for h, p in vals for x in (h, p)] + [n])
    csv_header = ["device_class", "label",
                  "n_certification", "pct_certification",
                  "n_area", "pct_area",
                  "n_stabilised", "pct_stabilised",
                  "n_isos", "pct_isos", "n_papers"]
    return header, rows, [csv_header] + csv_rows


# ---------------------------------------------------------------- T3
def table3(groups: dict) -> tuple[list, list, list]:
    """The evidence ledger: what stands behind each section.

    This is the table that makes the issue auditable. A reader can see that
    a section arguing about tandems rests on N papers, M extracted values
    and K verified quotations, rather than taking the argument on trust.

    `Simulation or review` is reported explicitly rather than folded away,
    because a section whose evidence is largely computational is a different
    claim from one resting on measured hardware.
    """
    header = ["Device class", "Papers read", "Measured", "Simulation or review",
              "Extracted values", "Verified quotations"]
    rows, csv_rows = [], []
    for k in CLASS_ORDER:
        cards = groups[k]
        if not cards:
            continue
        meas = [c for c in cards if c.get("lens") not in NON_MEASURED]
        nonmeas = len(cards) - len(meas)
        n_val = 0
        n_anchor = 0
        for c in cards:
            for grp in ("performance", "stability"):
                for f in (c.get(grp) or {}).values():
                    if isinstance(f, dict) and f.get("value") is not None:
                        n_val += 1
                    if isinstance(f, dict) and f.get("anchor"):
                        n_anchor += 1
            for cl in (c.get("claims") or []):
                if isinstance(cl, dict) and cl.get("anchor"):
                    n_anchor += 1
        rows.append([CLASS_LABEL[k], len(cards), len(meas), nonmeas,
                     n_val, n_anchor])
        csv_rows.append([k, CLASS_LABEL[k], len(cards), len(meas), nonmeas,
                         n_val, n_anchor])
    csv_header = ["device_class", "label", "n_papers", "n_measured",
                  "n_simulation_or_review", "n_extracted_values",
                  "n_verified_quotations"]
    return header, rows, [csv_header] + csv_rows


CAPTIONS = {
    "T1": ("Best independently certified and best self-reported power "
           "conversion efficiency in each device class, with the "
           "detailed-balance limit that applies to that class. Certified "
           "and self-reported values are kept in separate columns because "
           "they are not the same kind of evidence. Simulation and review "
           "studies contribute no value to this table."),
    "T2": ("Reporting completeness by device class. Each cell gives the "
           "percentage of papers whose abstract states the quantity, with "
           "the paper count in brackets. Flags are recomputed by script "
           "from abstract text, so every figure is a lower bound: a paper "
           "reporting a quantity only in its experimental section is "
           "counted as not reporting it. No validated precision figure is "
           "available."),
    "T3": ("The evidence base behind each section. Extracted values are "
           "individual numbers bound to a source quotation; verified "
           "quotations are anchors confirmed word for word against the "
           "source abstract by a script sharing no code with the "
           "extraction stage."),
}


def build_tables(cards: list, abstracts: dict) -> dict:
    global _ABSTRACTS
    _ABSTRACTS = abstracts or {}
    groups = _by_class(cards, abstracts)
    out = {}
    for tid, fn in (("T1", table1), ("T2", table2), ("T3", table3)):
        header, rows, csv_block = fn(groups)
        out[tid] = {"header": header, "rows": rows, "csv": csv_block,
                    "caption": CAPTIONS[tid],
                    "markdown": _md_table(header, rows)}
    return out


def write_tables(year: str, cards: list, abstracts: dict,
                 outdir: pathlib.Path) -> dict:
    tables = build_tables(cards, abstracts)
    outdir.mkdir(parents=True, exist_ok=True)
    made = []
    for tid, t in tables.items():
        p = outdir / f"table{tid[1]}_{'champions' if tid == 'T1' else 'reporting' if tid == 'T2' else 'evidence'}.csv"
        with p.open("w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerows(t["csv"])
        made.append(p.name)
    return {"tables": list(tables), "csv": made, "detail": tables}


if __name__ == "__main__":
    from stages.util import read_jsonl, run_dir
    from stages.yearly_corpus import aggregate

    if len(sys.argv) < 2:
        raise SystemExit("usage: yearly_tables.py <YYYY> [--partial]")
    yr = sys.argv[1]
    agg = aggregate(yr, require_full_year="--partial" not in sys.argv)
    rd = run_dir(yr, create=False)
    ab = {x["work_key"]: x["abstract"]
          for x in read_jsonl(rd / "private" / "02_abstracts.jsonl")}
    res = write_tables(yr, agg["cards"], ab, rd / "tabledata")
    for tid, t in res["detail"].items():
        print(f"\n=== {tid} ===")
        for line in t["markdown"]:
            print(" ", line)
    print("\ncsv:", res["csv"])
