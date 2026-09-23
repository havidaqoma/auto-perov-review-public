"""s11y_si_figures: the two SUPPLEMENTARY figures, and nothing else.

WHY THIS IS A SEPARATE STAGE FROM `s11y_figures_yearly`
------------------------------------------------------
The main-text figure gates count populations. `G9e-figures-present` asserts
F5 and F6 exist, and `G9c-figure-unique` asserts no figure is attached twice.
Adding supplementary plates to the main-text stage would put two different
populations behind one set of counts, and every future edit to either gate
would have to remember the distinction. Keeping the SI plates in their own
stage with an `S` prefix means the main-text gates keep counting exactly what
they were written to count.

SINGLE SOURCE OF TRUTH
----------------------
Both figures read `stats_yearly.json` and the same `01_meta.json` the SI prose
reads. Nothing here recomputes a quantity from the corpus: a figure that
derives its own numbers can disagree with the table beside it, and when a
figure and the prose disagree the figure is the one a reader believes.

NOTHING IS INVENTED
-------------------
Every value plotted is read from a run artifact. `S1` plots the selection
funnel, whose five stages are the counts the SI already states in prose; `S2`
plots the reporting-audit rates that Note S4 already tabulates. If a required
key is missing the stage FAILS rather than plotting a plausible shape --
an SI figure exists to let a reader check the text, so a guessed value here
is worse than no figure.
"""
from __future__ import annotations

import csv
import json
import pathlib
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                             # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from stages.util import ROOT, done, is_year, run_dir        # noqa: E402
from stages.yearly_corpus import yearly_dir                 # noqa: E402

AUDIT_KEYS = ["efficiency_stated", "certified", "stabilised",
              "area_stated", "isos_label", "hysteresis"]
AUDIT_SHORT = {"efficiency_stated": "an efficiency value",
               "certified": "independent certification",
               "stabilised": "stabilised or MPP output",
               "area_stated": "a device area",
               "isos_label": "a named ISOS protocol",
               "hysteresis": "hysteresis information"}

# Identical to the main-text figure stage. Two figure stages with different
# type sizes would ship an SI whose plates do not look like the paper's.
plt.rcParams.update({
    "font.size": 8, "axes.labelsize": 8, "axes.titlesize": 8.5,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 200, "savefig.bbox": "tight", "pdf.fonttype": 42,
})


def _csv(path: pathlib.Path, header: list, rows: list) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def _band(ax, text: str) -> None:
    ax.text(0.0, 1.02, text, transform=ax.transAxes, ha="left",
            va="bottom", fontsize=6.8, style="italic", color="#444444",
            clip_on=False)


# --------------------------------------------------------------------- S1
def fig_s1(meta: dict, S: dict, agg_unknown: int, n_measured: int,
           fd: pathlib.Path, dd: pathlib.Path) -> str:
    """The selection funnel, stage by stage.

    Each bar is a count the SI already states in prose. The figure exists
    because five numbers in a paragraph are five numbers; the same five as a
    funnel show at a glance that the depth tier is a small fraction of the
    corpus, which is the honest framing of what this review read.
    """
    retrieved = meta.get("openalex_count")
    corpus = S.get("corpus.n")
    with_abs = meta.get("with_abstract")
    audited = S.get("audit.year.certified.denominator")
    cards = S.get("cards.n")
    stages = [
        ("Retrieved from OpenAlex", retrieved),
        ("Passed the scope gate", corpus),
        ("Usable abstract (40+ words)", with_abs),
        ("Month-resolved and audited", audited),
        ("Read closely (depth tier)", cards),
        ("Measured device reports", n_measured),
    ]
    missing = [lab for lab, v in stages if v is None]
    if missing:
        raise SystemExit(f"FAIL-CLOSED: S1 funnel missing counts: {missing}")

    _csv(dd / "figureS1_corpus_funnel.csv",
         ["stage", "n_works"], [[lab, v] for lab, v in stages])

    labels = [s[0] for s in stages]
    vals = [s[1] for s in stages]
    fig, ax = plt.subplots(figsize=(6.6, 3.0))
    ys = list(range(len(stages)))
    ax.barh(ys, vals, color="#3E7CB1", height=0.62, edgecolor="none")
    ax.barh(ys[-1:], vals[-1:], color="#1A4E8A", height=0.62, edgecolor="none")
    for i, v in enumerate(vals):
        pct = 100.0 * v / vals[0]
        ax.text(v + vals[0] * 0.012, i, f"{v:,} ({pct:.1f}%)",
                va="center", ha="left", fontsize=6.8, color="#222222")
    ax.set_yticks(ys)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("Works")
    ax.set_xlim(0, vals[0] * 1.30)
    ax.set_xticks([])
    ax.spines["bottom"].set_visible(False)
    _band(ax, f"Percentages are of the {vals[0]:,} works retrieved. "
              f"{agg_unknown:,} works carry a year-only date and are absent "
              f"from every month-resolved count.")
    fig.savefig(fd / "S1_corpus_funnel.pdf")
    plt.close(fig)
    return "S1_corpus_funnel.pdf"


# --------------------------------------------------------------------- S2
def fig_s2(S: dict, fd: pathlib.Path, dd: pathlib.Path) -> str:
    """Reporting completeness: pooled annual rate with its monthly range.

    The main text's F6 plots the same quantities. This plate differs in one
    deliberate way: it prints the detected COUNT against the denominator on
    each row, because the SI is where a reader checks arithmetic rather than
    reads a trend.
    """
    present = [k for k in AUDIT_KEYS if S.get(f"audit.year.{k}.pct") is not None]
    if not present:
        raise SystemExit("FAIL-CLOSED: S2 has no audit keys to plot")

    rows = [[k, S.get(f"audit.year.{k}.n"),
             S.get(f"audit.year.{k}.denominator"),
             S.get(f"audit.year.{k}.pct"),
             S.get(f"audit.year.{k}.month_min_pct"),
             S.get(f"audit.year.{k}.month_max_pct")] for k in present]
    _csv(dd / "figureS2_reporting_audit.csv",
         ["quantity", "n_detected", "denominator", "pooled_pct",
          "month_min_pct", "month_max_pct"], rows)

    fig, ax = plt.subplots(figsize=(6.6, 3.1))
    for i, k in enumerate(present):
        lo = S.get(f"audit.year.{k}.month_min_pct")
        hi = S.get(f"audit.year.{k}.month_max_pct")
        pooled = S.get(f"audit.year.{k}.pct")
        if lo is not None and hi is not None:
            ax.hlines(i, lo, hi, color="#B9C9DC", lw=5, zorder=1)
            ax.scatter([lo, hi], [i, i], s=14, color="#3E7CB1",
                       edgecolors="none", zorder=2)
        ax.scatter([pooled], [i], s=42, color="#1A4E8A", marker="D",
                   edgecolors="white", linewidths=0.6, zorder=3)
        n = S.get(f"audit.year.{k}.n")
        den = S.get(f"audit.year.{k}.denominator")
        ax.text(0.995, i, f"{n:,}/{den:,}", transform=ax.get_yaxis_transform(),
                ha="right", va="center", fontsize=6.4, color="#555555")
    ax.set_yticks(range(len(present)))
    ax.set_yticklabels([AUDIT_SHORT[k] for k in present])
    ax.invert_yaxis()
    ax.set_xlabel("Abstracts in which the quantity was detected (%)")
    ax.set_xlim(0, max(60.0, max(S.get(f"audit.year.{k}.month_max_pct") or 0
                                 for k in present) * 1.35))
    _band(ax, "Diamonds: pooled annual rate. Bars: the monthly range. "
              "Counts at right are detected over denominator. Every rate is "
              "a LOWER BOUND: the detector reads abstracts only.")
    fig.savefig(fd / "S2_reporting_audit.pdf")
    plt.close(fig)
    return "S2_reporting_audit.pdf"


def _measured_total(year: str, rd: pathlib.Path) -> int:
    """Total measured device reports, READ from the shipped T3 rather than
    recounted. Recounting here would let S1 disagree with Table 2 in the main
    text, and when a figure and a table disagree the reader believes the
    figure (handbook 9.5)."""
    for cand in (ROOT / "manuscript" / f"{year}_yearly" / "data"
                 / "table3_evidence.csv",
                 rd / "tabledata" / "table3_evidence.csv"):
        if cand.exists():
            with cand.open(encoding="utf-8-sig") as fh:
                return sum(int(r["n_measured"]) for r in csv.DictReader(fh))
    raise SystemExit("FAIL-CLOSED: table3_evidence.csv not found; S1 cannot "
                     "state a measured-report count it did not read")


def figures(year: str) -> dict:
    if not is_year(year):
        raise SystemExit(f"expected a 4-digit year, got {year!r}")
    rd = run_dir(year, create=False)
    yd = yearly_dir(year)
    S = json.loads((yd / "stats_yearly.json").read_text(encoding="utf-8"))
    meta = json.loads((rd / "01_meta.json").read_text(encoding="utf-8"))

    n_measured = _measured_total(year, rd)
    n_year_only = meta.get("imprecise_dated", 0)

    fd = rd / "fig"
    dd = rd / "figdata"
    fd.mkdir(parents=True, exist_ok=True)
    dd.mkdir(parents=True, exist_ok=True)

    made = [fig_s1(meta, S, n_year_only, n_measured, fd, dd),
            fig_s2(S, fd, dd)]

    meta_out = {"year": year, "figures": made, "fig_dir": str(fd),
                "measured_reports": n_measured,
                "year_only_dated": n_year_only}
    done(rd, "11y_si_figures", **meta_out)
    print("[11yS]", json.dumps(meta_out)[:400])
    return meta_out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: s11y_si_figures.py <YYYY>\n"
                         "No default: the period must be stated.")
    figures(sys.argv[1])
