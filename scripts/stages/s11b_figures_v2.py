"""v2 figures: built around the REVIEW STORY, not the corpus statistics.
Old F1-F4 (axis shares, audit bars, funnel) move to the SI; the main text gets
figures a perovskite reader would actually stop on.
Run: python scripts/stages/s11b_figures_v2.py 2026-07
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
from stages.util import done, read_jsonl, run_dir

plt.rcParams.update({"font.size": 8.5, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 220,
                     "font.family": "serif"})
C = {"sj": "#4C72B0", "psi": "#C44E52", "ap": "#DD8452",
     "mod": "#55A868", "grey": "#8C8C8C"}


def _v(c, k):
    """Read a guarded numeric field. t80_h lives under `stability`, everything
    else under `performance` -- reading the wrong dict silently returned None
    for every T80 and printed n_t80=0 while 4 real values (9800, 6785, 720,
    200 h) sat in the cards. Silent-zero class again: the figure rendered
    empty rather than raising."""
    src = c["stability"] if k in ("t80_h", "duration_h") else c["performance"]
    f = (src or {}).get(k)
    return f["value"] if isinstance(f, dict) and f.get("value") is not None else None


def cls(c):
    """Device class from architecture + title, for the frontier figure."""
    a = c["device"]["architecture"]
    t = (c["title"] or "").lower()
    if "silicon" in t or "/si" in t or "si tandem" in t:
        return "psi"
    if a in ("tandem_2T", "tandem_4T") or "all-perovskite" in t:
        return "ap"
    if a == "module" or "module" in t:
        return "mod"
    return "sj"


LAB = {"sj": "Single junction", "psi": "Perovskite/silicon tandem",
       "ap": "All-perovskite tandem", "mod": "Module"}


def figures(month: str) -> dict:
    rd = run_dir(month)
    S = json.loads((rd / "stats.json").read_text(encoding="utf-8"))
    cards = read_jsonl(rd / "claim_cards.jsonl")
    fd = rd / "fig"
    fd.mkdir(exist_ok=True)
    made = []

    # ---------- F1: the certified frontier ----------
    # Certified vs self-reported, by device class. This is the month's headline:
    # where the verified ceiling actually sits, and how thin the certified layer is.
    fig, ax = plt.subplots(figsize=(6.6, 3.0))
    order = ["sj", "ap", "psi", "mod"]
    xoff = {k: i for i, k in enumerate(order)}
    rng = np.random.default_rng(0)
    n_self = n_cert = n_excl = 0
    for c in cards:
        # Q63: an efficiency frontier must show MEASURED devices only.
        # Havid spotted a ~30.8% "single junction" that is a
        # drift-diffusion study (Temperature-Dependent Performance
        # Analysis ... A Theoretical Study), i.e. a simulated ceiling
        # standing beside certified hardware. lens comes from stage 06.
        # `scale_up` is KEPT deliberately: those are real modules.
        if c.get("lens") in ("theory", "review"):
            n_excl += 1
            continue
        k = cls(c)
        ch, ce = _v(c, "pce_champion"), _v(c, "pce_certified")
        x = xoff[k] + rng.uniform(-0.16, 0.16)
        if ch and 8 < ch < 36:
            ax.scatter(x, ch, s=16, facecolor="none", edgecolor=C["grey"],
                       linewidth=0.7, zorder=2)
            n_self += 1
        if ce and 8 < ce < 36:
            ax.scatter(x, ce, s=34, color=C[k], edgecolor="k", linewidth=0.4,
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
    ax.scatter([], [], s=16, facecolor="none", edgecolor=C["grey"],
               label=f"Self-reported champion (n={n_self})")
    ax.scatter([], [], s=34, color="k", label=f"Independently certified (n={n_cert})")
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
    # Efficiency against aperture area: the single most useful scale-up plot,
    # because it exposes the cell-to-module gap the month actually reported.
    pts = [(a, p, cls(c)) for c in cards
           if c.get("lens") not in ("theory", "review")
           if (a := _v(c, "active_area_cm2")) and (p := _v(c, "pce_champion"))
           and 8 < p < 36]
    if pts:
        fig, ax = plt.subplots(figsize=(6.6, 2.9))
        for a, p, k in pts:
            ax.scatter(a, p, s=40, color=C[k], edgecolor="k", linewidth=0.4,
                       label=LAB[k], zorder=3)
        ax.set_xscale("log")
        ax.set_xlabel("Reported active or aperture area (cm$^2$, log scale)")
        ax.set_ylabel("Efficiency (%)")
        h, l = ax.get_legend_handles_labels()
        seen = dict(zip(l, h))
        ax.legend(seen.values(), seen.keys(), frameon=False, fontsize=7.5,
                  loc="lower left")
        ax.axvspan(0.04, 0.3, color=C["grey"], alpha=0.10)
        # Band label sits ABOVE the axes frame, not inside it.
        #
        # History: first pinned to ylim bottom (collided with the data and the
        # lower-left legend), then moved to axis-fraction y=0.97 with
        # va="top" -- which is still INSIDE the plot area, and Havid found it
        # overlapping the data in the August v4 PDF. Two failed attempts to
        # place a label inside a data region is enough: y=1.02 in axis
        # coordinates puts it in the margin above the frame, where no data
        # point can ever reach it regardless of the y-range.
        ax.text(0.09, 1.02, "lab-cell regime", fontsize=6.5,
                ha="center", va="bottom", color=C["grey"],
                transform=ax.get_xaxis_transform(), clip_on=False)
        ax.grid(alpha=0.25, lw=0.5)
        fig.tight_layout()
        fig.savefig(fd / "F2_area_penalty.pdf")
        plt.close(fig)
        made.append("F2_area_penalty.pdf")

    # ---------- F3: where the month's effort went ----------
    # Mechanism axis vs device class: shows WHICH physics each device family is
    # being pushed on, which the flat axis-share bar chart could not.
    axes = ["composition", "defects", "interfaces", "architecture",
            "stability", "scale_up"]
    nice = ["Composition", "Defects", "Interfaces", "Architecture",
            "Stability", "Scale-up"]
    M = np.zeros((len(axes), len(order)))
    for c in cards:
        if c["axis"] in axes:
            M[axes.index(c["axis"]), order.index(cls(c))] += 1
    fig, ax = plt.subplots(figsize=(6.6, 2.8))
    bottom = np.zeros(len(axes))
    for j, k in enumerate(order):
        ax.bar(range(len(axes)), M[:, j], 0.6, bottom=bottom, color=C[k],
               label=LAB[k], edgecolor="white", linewidth=0.5)
        bottom += M[:, j]
    ax.set_xticks(range(len(axes)))
    ax.set_xticklabels(nice, fontsize=8)
    ax.set_ylabel("Depth-tier papers")
    ax.legend(frameon=False, fontsize=7.5, ncol=2)
    fig.tight_layout()
    fig.savefig(fd / "F3_effort_map.pdf")
    plt.close(fig)
    made.append("F3_effort_map.pdf")

    # ---------- F4: stability evidence, and how thin it is ----------
    t80 = sorted((_v(c, "t80_h"), c) for c in cards if _v(c, "t80_h"))
    protos = Counter(c["stability"]["protocol"].split()[0]
                     for c in cards if c["stability"].get("protocol"))
    fig, axs = plt.subplots(1, 2, figsize=(6.6, 2.6))
    if t80:
        vals = [v for v, _ in t80]
        axs[0].barh(range(len(vals)), vals, color=C["mod"], edgecolor="k",
                    linewidth=0.4)
        axs[0].set_yticks(range(len(vals)))
        axs[0].set_yticklabels([f"{cls(c)[:3]}" for _, c in t80], fontsize=6.5)
        for i, v in enumerate(vals):
            axs[0].text(v * 1.03, i, f"{int(v)} h", va="center", fontsize=6.5)
        axs[0].set_xscale("log")
        axs[0].set_xlabel("Reported T$_{80}$ (h, log)")
        axs[0].set_title(f"Every T$_{{80}}$ in the month (n={len(vals)})",
                         fontsize=8)
    if protos:
        ks = list(protos)
        axs[1].bar(range(len(ks)), [protos[k] for k in ks], 0.55,
                   color=C["psi"], edgecolor="k", linewidth=0.4)
        axs[1].set_xticks(range(len(ks)))
        axs[1].set_xticklabels(ks, fontsize=7, rotation=20, ha="right")
        axs[1].set_ylabel("papers")
        axs[1].set_title(f"ISOS protocol labels (n={sum(protos.values())} of "
                         f"{len(cards)})", fontsize=8)
    fig.tight_layout()
    fig.savefig(fd / "F4_stability_evidence.pdf")
    plt.close(fig)
    made.append("F4_stability_evidence.pdf")

    # ---------- SI figures: the audit + funnel ----------
    METRICS = ["efficiency_stated", "stabilised", "certified", "area_stated",
               "hysteresis", "isos_label", "triplet_complete"]
    ML = ["Efficiency", "Stabilised/MPPT", "Certified", "Device area",
          "Hysteresis/scan", "ISOS label", "Full V$_{oc}$/J$_{sc}$/FF"]
    fig, ax = plt.subplots(figsize=(6.2, 2.6))
    ys = np.arange(len(METRICS))
    ax.barh(ys + 0.2, [S[f"audit.corpus.{m}.pct"] for m in METRICS], 0.4,
            color=C["sj"], label=f"corpus (n={S['audit.corpus.denominator']})")
    ax.barh(ys - 0.2, [S[f"audit.depth.{m}.pct"] for m in METRICS], 0.4,
            color=C["ap"], label=f"depth (n={S['audit.depth.denominator']})")
    ax.set_yticks(ys)
    ax.set_yticklabels(ML, fontsize=7.5)
    ax.invert_yaxis()
    ax.set_xlabel("Abstracts in which the item was detected (%)")
    ax.legend(frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(fd / "S1_reporting_audit.pdf")
    plt.close(fig)
    made.append("S1_reporting_audit.pdf")

    fig, ax = plt.subplots(figsize=(6.2, 2.0))
    stages = ["Scope gate", "Usable abstract", "Depth tier", "Cited in body"]
    counts = [S["corpus.n"], S["selection.n_eligible"],
              S["selection.n_depth"], S["selection.n_cited"]]
    ax.barh(range(4), counts, 0.55, color=C["sj"], edgecolor="k", linewidth=0.4)
    for i, c_ in enumerate(counts):
        ax.text(c_ + max(counts) * 0.015, i, str(c_), va="center", fontsize=7.5)
    ax.set_yticks(range(4))
    ax.set_yticklabels(stages, fontsize=7.5)
    ax.invert_yaxis()
    ax.set_xlim(0, max(counts) * 1.16)
    ax.set_xlabel("Works")
    fig.tight_layout()
    fig.savefig(fd / "S2_corpus_funnel.pdf")
    plt.close(fig)
    made.append("S2_corpus_funnel.pdf")

    meta = {"figures": made, "n": len(made),
            "n_certified": n_cert, "n_self": n_self,
            "n_area": len(pts), "n_t80": len(t80)}
    done(rd, "11_figures", **meta)
    print("[11b]", json.dumps(meta, indent=2))
    return meta


if __name__ == "__main__":
    figures(sys.argv[1] if len(sys.argv) > 1 else "2026-07")
