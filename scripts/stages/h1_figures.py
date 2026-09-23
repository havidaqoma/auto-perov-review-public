"""H1 figures: the four monthly panels over six months, plus a trajectory.

Reuses s11b_figures_v2's helpers BY IMPORT (_v, cls, LAB, C), never by copy.
Those helpers carry paid-for guards -- `t80_h` lives under `stability` not
`performance`, theory/review lenses are excluded from measured-performance
figures, `scale_up` is KEPT because those are real modules. A forked copy of a
guard diverges, and the handbook records that exact failure three times
(narration filter in three copies, the citation regex in two consumers).

Adds T1, which no monthly issue can carry: the certified frontier month by
month. A single month has one point; six months have a shape, and that shape is
the reason to write a half-year review instead of stapling six monthlies
together.
"""
from __future__ import annotations

import json
import pathlib
import sys
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from matplotlib.ticker import (LogFormatterSciNotation, LogLocator,  # noqa: E402
                               NullLocator)

from stages.util import read_jsonl  # noqa: E402
from stages.s11b_figures_v2 import C, LAB, _v, cls  # noqa: E402
from stages.h1_aggregate import edition_dir  # noqa: E402
from stages.protocol import is_isos, protocol_counts  # noqa: E402
from stages.illumination import comparable_to_one_sun  # noqa: E402


def _illum_anchor(c: dict) -> str:
    """The anchors that decide whether a card's numbers are one-sun.

    Certified first, then champion: those are the two fields the
    measured-performance figures plot. If either quotation names an indoor or
    low-light condition, the card's efficiency points are not comparable to
    one-sun data and the whole card is dropped from those panels. Dropping the
    card rather than the single field is deliberate: F1 plots certified and
    champion side by side for the SAME device, so keeping one and dropping the
    other would draw a half-device.
    """
    out = []
    perf = c.get("performance") or {}
    for f in ("pce_certified", "pce_champion"):
        fd = perf.get(f)
        if isinstance(fd, dict):
            out.append(fd.get("anchor") or "")
    return " ".join(x for x in out if x)

plt.rcParams.update({"font.size": 8.5, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 220,
                     "font.family": "serif"})

MONTH_LAB = {"2026-01": "Jan", "2026-02": "Feb", "2026-03": "Mar",
             "2026-04": "Apr", "2026-05": "May", "2026-06": "Jun"}
SQ_SJ = 29.4  # 1.55 eV Shockley-Queisser single-junction limit


def figures() -> dict:
    d = edition_dir()
    S = json.loads((d / "stats.json").read_text(encoding="utf-8"))
    cards = read_jsonl(d / "claim_cards.jsonl")
    fd = d / "fig"
    fd.mkdir(exist_ok=True)
    made = []
    order = ["sj", "ap", "psi", "mod"]

    # ---------- T1: the certified frontier, month by month ----------
    # THE half-year figure. Every value is read from stats.json, which derived
    # it from anchor-verified cards; nothing is typed in (handbook 5.2).
    months = S["frontier.months"]
    certs = S["frontier.top_certified_series"]
    champs = S["frontier.top_champion_series"]
    ncert = S["frontier.n_certified_series"]

    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(6.6, 4.0), sharex=True,
                                  gridspec_kw={"height_ratios": [3, 1]})
    x = range(len(months))
    ax.plot(x, champs, "o--", color=C["grey"], lw=1.2, ms=5,
            markerfacecolor="none", label="Best self-reported champion")
    ax.plot(x, certs, "o-", color=C["psi"], lw=1.8, ms=6,
            label="Best independently certified")
    for i, v in enumerate(certs):
        if isinstance(v, (int, float)):
            ax.annotate(f"{v:.2f}", (i, v), textcoords="offset points",
                        xytext=(0, 7), ha="center", fontsize=6.8,
                        color=C["psi"], fontweight="bold")
    # The single-junction limit, drawn because most of these records are
    # tandems and a reader must be able to see that at a glance.
    ax.axhline(SQ_SJ, color=C["sj"], lw=1.0, ls=":", zorder=1)
    ax.annotate("single-junction limit (29.4%)", xy=(0.995, 1.02),
                xycoords="axes fraction", ha="right", va="bottom",
                fontsize=6.5, color=C["sj"], clip_on=False)
    ax.set_ylabel("Power conversion efficiency (%)")
    ax.legend(frameon=False, fontsize=7.5, loc="lower right")
    ax.grid(axis="y", alpha=0.25, lw=0.5)

    ax2.bar(x, ncert, 0.55, color=C["mod"], edgecolor="k", linewidth=0.4)
    for i, v in enumerate(ncert):
        ax2.text(i, v + 0.15, str(v), ha="center", fontsize=6.5)
    ax2.set_ylabel("certified\npapers", fontsize=7.5)
    ax2.set_xticks(list(x))
    ax2.set_xticklabels([MONTH_LAB.get(m, m) for m in months], fontsize=8)
    ax2.grid(axis="y", alpha=0.25, lw=0.5)
    fig.tight_layout()
    fig.savefig(fd / "T1_frontier_trajectory.pdf")
    plt.close(fig)
    made.append("T1_frontier_trajectory.pdf")

    # ---------- F1: certified vs self-reported, by device class ----------
    fig, ax = plt.subplots(figsize=(6.6, 3.0))
    xoff = {k: i for i, k in enumerate(order)}
    rng = np.random.default_rng(0)
    n_self = n_cert = n_excl = n_indoor = 0
    for c in cards:
        if c.get("lens") in ("theory", "review"):
            n_excl += 1
            continue
        # Indoor / low-light values are EXCLUDED from every measured-performance
        # figure, exactly as they are from the tables.
        #
        # Havid flagged a >30% single junction in Table 1; it was a real
        # experimental 44.36% measured at 1000 lx LED ("PCE(i)"), and a module
        # 41.6% at TL84 900 lux. Correct numbers, wrong axis: an indoor PCE is
        # not comparable to a one-sun PCE because the SQ limit is defined for
        # AM1.5G. Plotting them beside one-sun points would draw the reader to
        # exactly the wrong conclusion, and a figure is harder to caveat than a
        # sentence. They are discussed in the prose instead (stats indoor.*).
        if not comparable_to_one_sun(_illum_anchor(c)):
            n_indoor += 1
            continue
        k = cls(c)
        ch, ce = _v(c, "pce_champion"), _v(c, "pce_certified")
        xx = xoff[k] + rng.uniform(-0.16, 0.16)
        if ch and 8 < ch < 36:
            ax.scatter(xx, ch, s=14, facecolor="none", edgecolor=C["grey"],
                       linewidth=0.6, zorder=2)
            n_self += 1
        if ce and 8 < ce < 36:
            ax.scatter(xx, ce, s=30, color=C[k], edgecolor="k", linewidth=0.4,
                       zorder=3)
            n_cert += 1
    for k in order:
        ce = [_v(c, "pce_certified") for c in cards
              if cls(c) == k and _v(c, "pce_certified")]
        if ce:
            m = max(ce)
            ax.hlines(m, xoff[k] - 0.3, xoff[k] + 0.3, color=C[k], lw=1.6)
            ax.text(xoff[k], m + 0.55, f"{m:.2f}%", ha="center", fontsize=8,
                    color=C[k], fontweight="bold")
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([LAB[k] for k in order], fontsize=8)
    ax.set_ylabel("Power conversion efficiency (%)")
    ax.scatter([], [], s=14, facecolor="none", edgecolor=C["grey"],
               label=f"Self-reported champion (n={n_self})")
    ax.scatter([], [], s=30, color="k",
               label=f"Independently certified (n={n_cert})")
    ax.legend(frameon=False, fontsize=7.5, loc="lower right")
    ax.grid(axis="y", alpha=0.25, lw=0.5)
    if n_excl:
        ax.annotate(f"{n_excl} simulation and review papers excluded",
                    xy=(0.995, 1.015), xycoords="axes fraction",
                    ha="right", fontsize=6.5, color=C["grey"])
    fig.tight_layout()
    fig.savefig(fd / "F1_certified_frontier.pdf")
    plt.close(fig)
    made.append("F1_certified_frontier.pdf")

    # ---------- F2: the area penalty ----------
    pts = [(a, p, cls(c)) for c in cards
           if c.get("lens") not in ("theory", "review")
           if (a := _v(c, "active_area_cm2")) and (p := _v(c, "pce_champion"))
           and 8 < p < 36]
    if pts:
        fig, ax = plt.subplots(figsize=(6.6, 2.9))
        for a, p, k in pts:
            ax.scatter(a, p, s=34, color=C[k], edgecolor="k", linewidth=0.4,
                       label=LAB[k], zorder=3)
        ax.set_xscale("log")
        ax.set_xlabel("Reported active or aperture area (cm$^2$, log scale)")
        ax.set_ylabel("Efficiency (%)")
        h, l = ax.get_legend_handles_labels()
        seen = dict(zip(l, h))
        ax.legend(seen.values(), seen.keys(), frameon=False, fontsize=7.5,
                  loc="lower left")
        ax.axvspan(0.04, 0.3, color=C["grey"], alpha=0.10)
        # Margin, not inside the data region (two failed attempts, handbook 5.1b).
        ax.text(0.09, 1.02, "lab-cell regime", fontsize=6.5,
                ha="center", va="bottom", color=C["grey"],
                transform=ax.get_xaxis_transform(), clip_on=False)
        ax.grid(alpha=0.25, lw=0.5)
        fig.tight_layout()
        fig.savefig(fd / "F2_area_penalty.pdf")
        plt.close(fig)
        made.append("F2_area_penalty.pdf")

    # ---------- F3: where the effort went, per axis per month ----------
    # The monthly F3 is axis x device class. Over six months the more
    # informative cut is axis x MONTH: it shows which physics gained and lost
    # attention, which is a half-year finding a single month cannot state.
    axes_l = ["composition", "defects", "interfaces", "architecture",
              "stability", "scale_up"]
    nice = ["Composition", "Defects", "Interfaces", "Architecture",
            "Stability", "Scale-up"]
    M = np.zeros((len(axes_l), len(months)))
    for c in cards:
        a, m = c.get("axis"), c.get("source_month")
        if a in axes_l and m in months:
            M[axes_l.index(a), months.index(m)] += 1
    fig, ax = plt.subplots(figsize=(6.6, 3.0))
    bottom = np.zeros(len(months))
    cmap = plt.get_cmap("viridis")
    for i, a in enumerate(axes_l):
        ax.bar(range(len(months)), M[i], 0.6, bottom=bottom,
               color=cmap(i / max(1, len(axes_l) - 1)), label=nice[i],
               edgecolor="white", linewidth=0.5)
        bottom += M[i]
    ax.set_xticks(range(len(months)))
    ax.set_xticklabels([MONTH_LAB.get(m, m) for m in months], fontsize=8)
    ax.set_ylabel("Depth-tier papers")
    ax.legend(frameon=False, fontsize=7, ncol=3)
    fig.tight_layout()
    fig.savefig(fd / "F3_effort_map.pdf")
    plt.close(fig)
    made.append("F3_effort_map.pdf")

    # ---------- F4: stability evidence, and how thin it is ----------
    # key=itemgetter(0): without it, two cards sharing a T80 value make Python
    # fall through to comparing the card dicts, which raises. The monthly stage
    # never hit this because one month rarely carries a duplicate T80; six
    # months do. Tuple sorting on (number, dict) is a latent crash, not a
    # style issue.
    t80 = sorted(((_v(c, "t80_h"), c) for c in cards if _v(c, "t80_h")),
                 key=lambda t: t[0])

    # Canonical labels, not raw first tokens.
    #
    # Splitting on whitespace and plotting the raw token produced NINETEEN
    # categories for THIRTEEN real protocols, because papers spell the same
    # protocol several ways: "ISOS-L-1" and "ISOS\u2010L\u20101" (U+2010 hyphen,
    # visually identical), "ISOS-L-2" and "ISOS-L2", "ISOS-D-1" and "ISOS-D1".
    # Handbook 4.4 rule 1 says normalise Unicode BEFORE matching; this stage
    # never did. The effect was not only a crowded axis: each protocol's count
    # was split across its spellings, understating every bar and overstating
    # how many distinct protocols the field uses.
    protos = Counter(protocol_counts(cards))

    fig, axs = plt.subplots(1, 2, figsize=(6.6, 3.2))
    if t80:
        vals = [v for v, _ in t80]
        axs[0].barh(range(len(vals)), vals, color=C["mod"], edgecolor="k",
                    linewidth=0.3)
        axs[0].set_yticks([])
        axs[0].set_xscale("log")
        # Decade ticks only. The default log locator added minor ticks
        # (2x10^3, 4x10^3, 8x10^3) that collided with each other at this panel
        # width. Decades are also the honest resolution for a quantity spanning
        # two orders of magnitude.
        axs[0].xaxis.set_major_locator(LogLocator(base=10))
        axs[0].xaxis.set_minor_locator(NullLocator())
        axs[0].xaxis.set_major_formatter(LogFormatterSciNotation(base=10))
        axs[0].tick_params(axis="x", labelsize=7)
        axs[0].set_xlabel("Reported T$_{80}$ (h, log)")
        axs[0].set_title(f"Every T$_{{80}}$ in six months (n={len(vals)})",
                         fontsize=8)
    if protos:
        # HORIZONTAL bars, sorted by count.
        #
        # Third attempt at this panel, and the first that cannot regress. The
        # labels are long ("ISOS-L-2I"), there are thirteen of them, and the
        # panel is ~3 in wide: rotating vertical tick labels only trades
        # overlap for truncation, which is why the shipped figure was
        # unreadable. Rotation is a workaround for a horizontal-space problem;
        # transposing the bars removes the problem, because a horizontal bar
        # chart gives every label its own full-width row.
        #
        # Same principle as 5.1b: when a label cannot fit where it is, move it
        # somewhere it fits rather than shrinking it further.
        ks = list(protos)[::-1]          # largest at the top after barh
        vals_p = [protos[k] for k in ks]
        colors = [C["psi"] if is_isos(k) else C["grey"] for k in ks]
        axs[1].barh(range(len(ks)), vals_p, 0.68, color=colors,
                    edgecolor="k", linewidth=0.4)
        axs[1].set_yticks(range(len(ks)))
        axs[1].set_yticklabels(ks, fontsize=6.8)
        for i, v in enumerate(vals_p):
            axs[1].text(v + 0.12, i, str(v), va="center", fontsize=6.5)
        axs[1].set_xlabel("papers", fontsize=8)
        axs[1].set_xlim(0, max(vals_p) * 1.18)
        # Havid's decision (2026-09-09): keep the prose's 39 and relabel the
        # figure, rather than switch {{N_PROTO}} to 31 and redraft.
        #
        # So the HEADLINE count is "any stability protocol named" = 39, which
        # is what the abstract and the two body sentences say. The 31-vs-8
        # split is carried by the COLOUR and the LEGEND instead of by the title
        # number. Do NOT put 31 back in the title: it would disagree with the
        # abstract, and a figure that contradicts the prose is worse than a
        # figure that says less.
        n_isos = sum(v for k, v in protos.items() if is_isos(k))
        n_any = sum(protos.values())
        # ONE line; a two-line title measured as a collision on the rendered
        # page, the same defect class being fixed here (4.5).
        axs[1].set_title(f"Any stability protocol named: {n_any} of "
                         f"{len(cards)}", fontsize=7.4)
        # Grey bars are labels that are NOT a specified ISOS protocol (IEC,
        # MPP, bare "ISOS"). Distinguishing them is the finding, not decoration.
        axs[1].scatter([], [], marker="s", color=C["psi"], label="ISOS-specified")
        axs[1].scatter([], [], marker="s", color=C["grey"], label="other / unspecified")
        axs[1].legend(frameon=False, fontsize=6.2, loc="lower right")
    fig.tight_layout()
    fig.savefig(fd / "F4_stability_evidence.pdf")
    plt.close(fig)
    made.append("F4_stability_evidence.pdf")

    # ---------- SI: reporting audit trajectory ----------
    METRICS = ["efficiency_stated", "certified", "stabilised", "area_stated",
               "isos_label", "hysteresis"]
    fig, ax = plt.subplots(figsize=(6.6, 3.0))
    for k in METRICS:
        ser = S.get(f"series.{k}.pct") or []
        if any(isinstance(v, (int, float)) for v in ser):
            ax.plot(range(len(ser)), ser, "o-", lw=1.2, ms=4,
                    label=k.replace("_", " "))
    ax.set_xticks(range(len(months)))
    ax.set_xticklabels([MONTH_LAB.get(m, m) for m in months], fontsize=8)
    ax.set_ylabel("% of corpus")
    ax.legend(frameon=False, fontsize=7, ncol=2)
    ax.grid(alpha=0.25, lw=0.5)
    fig.tight_layout()
    fig.savefig(fd / "S1_reporting_audit.pdf")
    plt.close(fig)
    made.append("S1_reporting_audit.pdf")

    # ---------- SI: corpus construction funnel ----------
    # The SI references this file but the period layer never built it, so
    # Figure S1 rendered as an empty float with its caption stranded above
    # blank space. Only the MONTHLY figure stage produced a funnel, and the
    # period SI inherited a reference to a file that does not exist here.
    # Nothing caught it: no gate asserts that a referenced figure is on disk,
    # and pandoc emits a missing image silently rather than failing.
    #
    # The period funnel differs from the monthly one in its last bar. A monthly
    # issue cites most of what it reads; a half-year issue reads 884 papers and
    # cites 184, so "cited in body" is a real and much larger narrowing that a
    # reader should see rather than infer.
    n_cited = 0
    try:
        gp = d / "gate_report_v6.json"
        if gp.exists():
            g = json.loads(gp.read_text(encoding="utf-8"))
            n_cited = int(((g.get("G2c-cite-count") or {}).get("detail")
                           or {}).get("cited") or 0)
    except Exception:
        n_cited = 0

    stages_lab = ["Indexed works in scope", "With a usable abstract",
                  "Read closely (depth tier)", "Yielding a verified record"]
    counts = [S.get("corpus.n") or 0, S.get("corpus.n_with_abstract") or 0,
              S.get("selection.n_depth") or 0, S.get("cards.n") or 0]
    if n_cited:
        stages_lab.append("Cited in the main text")
        counts.append(n_cited)

    fig, ax = plt.subplots(figsize=(6.2, 2.4))
    ax.barh(range(len(counts)), counts, 0.58, color=C["sj"],
            edgecolor="k", linewidth=0.4)
    for i, c_ in enumerate(counts):
        ax.text(c_ + max(counts) * 0.015, i, f"{c_:,}", va="center", fontsize=7.5)
    ax.set_yticks(range(len(counts)))
    ax.set_yticklabels(stages_lab, fontsize=7.5)
    ax.invert_yaxis()
    ax.set_xlim(0, max(counts) * 1.18)
    ax.set_xlabel("Works")
    fig.tight_layout()
    fig.savefig(fd / "S2_corpus_funnel.pdf")
    plt.close(fig)
    made.append("S2_corpus_funnel.pdf")

    meta = {"edition": S["edition"], "n_figures": len(made), "files": made,
            "n_cards": len(cards), "n_t80": len(t80),
            "n_certified_points": n_cert}
    (d / "11_figures.json").write_text(json.dumps(meta, indent=2),
                                       encoding="utf-8")
    return meta


def main() -> int:
    m = figures()
    print(json.dumps(m, indent=2))
    # A zero is a bug until proven otherwise (7.1).
    if not m["n_t80"]:
        print("FAIL: n_t80=0 -- check field locations before trusting this")
        return 1
    if not m["n_certified_points"]:
        print("FAIL: no certified points plotted")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
