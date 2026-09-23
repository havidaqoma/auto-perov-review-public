"""11y_figures_yearly: the yearly figure set. Six plates, all data-driven.

DESIGN, AND WHY EACH PLATE EARNS ITS SPACE
------------------------------------------
A figure earns main-text space by carrying an argument the prose cannot make
in a sentence. Learned from the monthly project's F1-F4 plus the H1 issue's
T1/S1, and sized to what the 2025 corpus ACTUALLY contains (measured, not
assumed):

  pce_certified    66 values     active_area_cm2  60 values
  pce_champion    330 values     t80_h            15 values
  pce_stabilised    8 values     ISOS protocols   24 cards
  cert+champ both  61 cards      area+PCE pairs   58 pairs

  F1  certified vs self-reported, by device family
      ARGUMENT: how thin the independently verified layer is. 66 certified
      against 330 self-reported is the single most important ratio in the
      issue.
  F2  area penalty, log x
      ARGUMENT: the frontier does not survive scale. 58 pairs spanning
      0.04-764 cm2 is nearly four decades.
  F3  effort map: where the year's reading went, by axis and device family
      ARGUMENT: the field's attention is not distributed like its evidence.
  F4  stability evidence in full
      ARGUMENT: its THINNESS is the finding. 15 T80 values and 24 protocol
      labels out of 450 closely read papers.
  F5  frontier trajectory, twelve points, DEVICE CLASS ON EVERY POINT
      ARGUMENT: whether the frontier moved at all, and on how much evidence.
      Only a yearly issue can plot this.
  F6  audit trajectory, six rates x twelve months
      ARGUMENT: whether reporting practice improved across the year.
      Only a yearly issue can plot this.

RULES CARRIED OVER, EACH FROM A REAL DEFECT
-------------------------------------------
1. NEVER HARD-CODE A PLOTTED NUMBER. Every value is read from stats or cards.
   A test asserts no literal data appears in this file.
2. SIMULATION NEVER SITS ON A MEASURED FIGURE. A drift-diffusion study
   reporting ~30.8% once sat beside certified hardware until a human noticed.
   `lens in ("theory", "review")` is excluded from every measured plate.
   `scale_up` is KEPT: those are real module measurements, and filtering to
   `experimental` alone silently dropped 11 real papers.
3. BAND LABELS GO OUTSIDE THE AXES FRAME (y=1.02, va="bottom",
   clip_on=False). Two cleverer positions inside the data region both
   collided with data.
4. F5 LABELS EVERY POINT WITH ITS DEVICE CLASS. The highest values here are
   tandems; an unlabelled trajectory of mixed device classes is the
   misattribution defect rendered as a line chart.
5. A FIGURE WITH NO DATA IS NOT WRITTEN. An empty axes frame published as a
   figure is worse than an absent figure, because it looks like a finding.
   Skipped plates are reported, never silent.
6. EVERY PLATE EMITS ITS OWN CSV. A reader must be able to reproduce any
   panel, including the exclusions and why they were excluded.
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

from stages.util import done, is_year, run_dir              # noqa: E402
from stages.yearly_corpus import aggregate, yearly_dir      # noqa: E402

# Excluded from every MEASURED plate. A computed efficiency standing beside
# certified hardware misrepresents both. Measured on 2025: 63 of 450 cards
# are theory or review, so this filter removes 14% of the corpus from every
# performance plate.
NON_MEASURED = ("theory", "review")

# Set by figures(). See yearly_tables for why this is module level.
_ABSTRACTS: dict = {}

# Multi-junction markers, checked against the value's own ANCHOR first and
# the title second. Duplicated from s18y_build_yearly deliberately? NO --
# imported below. A second copy would be a second definition of what counts
# as a tandem, and the two would drift.
from stages.s18y_build_yearly import _is_single_junction  # noqa: E402
from stages.device_class import is_indoor_value            # noqa: E402

ARCH_ORDER = ["p-i-n", "n-i-p", "tandem_2T", "tandem_4T", "module"]
ARCH_LABEL = {"p-i-n": "p-i-n", "n-i-p": "n-i-p", "tandem_2T": "tandem (2T)",
              "tandem_4T": "tandem (4T)", "module": "module",
              "unknown": "unspecified", "none": "unspecified"}
AXIS_LABEL = {"defects": "Defects", "interfaces": "Interfaces",
              "composition": "Composition", "stability": "Stability",
              "architecture": "Architecture", "scale_up": "Scale-up"}
AUDIT_KEYS = ["efficiency_stated", "certified", "stabilised",
              "area_stated", "isos_label", "hysteresis"]
AUDIT_SHORT = {"efficiency_stated": "efficiency stated",
               "certified": "certified", "stabilised": "stabilised",
               "area_stated": "area stated", "isos_label": "ISOS label",
               "hysteresis": "hysteresis"}

plt.rcParams.update({
    "font.size": 8, "axes.labelsize": 8, "axes.titlesize": 8.5,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 200, "savefig.bbox": "tight", "pdf.fonttype": 42,
})


def _v(c: dict, k: str):
    src = c.get("stability") if k in ("t80_h", "duration_h") else c.get("performance")
    f = (src or {}).get(k)
    return f["value"] if isinstance(f, dict) and f.get("value") is not None else None


def _anchor_of(c: dict, k: str) -> str:
    src = c.get("stability") if k in ("t80_h",) else c.get("performance")
    f = (src or {}).get(k)
    return (f or {}).get("anchor", "") if isinstance(f, dict) else ""


def _v_am15(c: dict, k: str, source: str = ""):
    """A value ONLY when measured under solar conditions; else None.

    F1a and F1b draw an AM1.5G detailed-balance line (29.4% single
    junction, 47.6% two-junction). An INDOOR measurement plotted against
    that line is a category error even though the number, the extraction
    and the device class are all correct: the SQ limit is derived for the
    solar spectrum, and under narrow indoor light a wide-gap perovskite
    legitimately exceeds it.

    Measured on 2025: two single-junction cards report 33.2% and 30.3%
    under weak light. On the first build they sat above the 29.4% line and
    made the issue look like it had found a field-wide integrity problem.
    It had not.

    An UNMARKED value is KEPT: standard conditions are the default in this
    literature, and assuming otherwise would drop most of the corpus.
    """
    val = _v(c, k)
    if val is None:
        return None
    return None if is_indoor_value(_anchor_of(c, k), val, source) else val


def _measured(cards: list) -> list:
    return [c for c in cards if c.get("lens") not in NON_MEASURED]


def _csv(path: pathlib.Path, header: list, rows: list) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def _band(ax, text: str) -> None:
    """Annotate ABOVE the axes frame. A label that must never touch data does
    not belong inside the data region."""
    ax.text(0.0, 1.02, text, transform=ax.transAxes, ha="left",
            va="bottom", fontsize=6.8, style="italic", color="#444444",
            clip_on=False)


# --------------------------------------------------------------------- F1
def _fig1_panel(rows: list, fd: pathlib.Path, fname: str, subtitle: str,
                sq_line: float | None) -> str:
    """One certified-vs-self-reported panel for ONE junction class.

    Row layout is [work_key, month, device_class, cert, champ, lens], so
    cert is index 3 and champ index 4. Reading 4/5 picked up the LENS string
    and float() raised on 'experimental' -- caught on first run.
    """
    fams = [a for a in ARCH_ORDER
            if any(r[2] == ARCH_LABEL[a] for r in rows)]
    if not fams:
        fams = sorted({r[2] for r in rows})
        lab_of = {f: f for f in fams}
    else:
        lab_of = {a: ARCH_LABEL.get(a, a) for a in fams}

    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    for i, a in enumerate(fams):
        lab = lab_of[a]
        cert = [float(r[3]) for r in rows if r[2] == lab and r[3] != ""]
        champ = [float(r[4]) for r in rows if r[2] == lab and r[4] != ""]
        if champ:
            ax.scatter([i - 0.14] * len(champ), champ, s=14, alpha=0.5,
                       color="#9aa5b1", edgecolors="none",
                       label="self-reported" if i == 0 else None)
        if cert:
            ax.scatter([i + 0.14] * len(cert), cert, s=24, alpha=0.9,
                       color="#1A4E8A", marker="D", edgecolors="none",
                       label="independently certified" if i == 0 else None)
            ax.hlines(max(cert), i - 0.02, i + 0.30, color="#1A4E8A", lw=1.4)

    # The detailed-balance bound for THIS junction class. Drawing it is only
    # meaningful once the classes are separated: a single axis carrying both
    # single junctions and tandems has two different ceilings and can show
    # neither honestly.
    if sq_line is not None:
        ax.axhline(sq_line, color="#B03A2E", lw=0.9, ls="--", zorder=1)
        ax.text(0.995, sq_line, f" {sq_line:g}% limit", transform=
                ax.get_yaxis_transform(), ha="right", va="bottom",
                fontsize=6.2, color="#B03A2E")

    ax.set_xticks(range(len(fams)))
    ax.set_xticklabels([lab_of[a] for a in fams])
    ax.set_ylabel("Power conversion efficiency (%)")
    n_cert = sum(1 for r in rows if r[3] != "")
    n_champ = sum(1 for r in rows if r[4] != "")
    _band(ax, f"{subtitle}: {n_cert} certified against {n_champ} "
              f"self-reported. Bars mark the certified maximum.")
    ax.legend(loc="lower right", frameon=False)
    fig.savefig(fd / fname)
    plt.close(fig)
    return fname


def fig1(cards: list, fd: pathlib.Path, dd: pathlib.Path) -> list:
    """Certified against self-reported, SPLIT BY JUNCTION CLASS.

    WHY THIS IS TWO FIGURES AND NOT ONE (Havid, 2026-09-09)
    ------------------------------------------------------
    Measured on 2025: single junctions carry 41 certified values topping out
    at 27.3%; tandems and modules carry 24 topping out at 33.15%. Those are
    two different populations with two different physical ceilings -- 29.4%
    for a 1.55 eV single junction, 47.6% for a two-junction stack.

    Plotting them on one axis actively HID that: the tandem points sat above
    every single-junction point and a reader could not tell whether the
    frontier was a single-junction achievement or a stack. It is the
    misattribution defect in chart form, and separating the panels is what
    lets each carry its own limit line.

    Classification uses the value's own ANCHOR first and the title second,
    imported from the build so the figure and the gate agree on what a
    tandem is.

    INDOOR VALUES ARE EXCLUDED (Havid, 2026-09-10). Each panel draws an
    AM1.5G detailed-balance line, so a value measured under weak or indoor
    light cannot appear beside it: the SQ limit is derived for the solar
    spectrum. Two single-junction cards (33.2% and 30.3%) sat above the
    29.4% line on the first build and made the issue appear to show a
    field-wide integrity problem. They are indoor photovoltaics, where
    exceeding the solar limit is ordinary physics.
    """
    m = _measured(cards)
    sj_rows, tan_rows = [], []
    n_indoor = 0
    for c in m:
        src = _ABSTRACTS.get(c.get("work_key"), "")
        cert, champ = (_v_am15(c, "pce_certified", src),
                       _v_am15(c, "pce_champion", src))
        # Count what the illumination filter removed, so the exclusion is
        # reported rather than silent.
        for kk in ("pce_certified", "pce_champion"):
            if _v(c, kk) is not None and _v_am15(c, kk, src) is None:
                n_indoor += 1
        if cert is None and champ is None:
            continue
        arch = ((c.get("device") or {}).get("architecture") or "unknown")
        row = [c["work_key"], c.get("source_month") or "",
               ARCH_LABEL.get(arch, arch), cert or "", champ or "",
               c.get("lens"), "AM1.5G"]
        (sj_rows if _is_single_junction(c) else tan_rows).append(row)

    hdr = ["work_key", "month", "device_class", "pce_certified_pct",
           "pce_champion_pct", "lens", "illumination"]
    made = []
    if n_indoor:
        print(f"[11y] F1: excluded {n_indoor} indoor/weak-light value(s); "
              f"panels compare against AM1.5G limits only")
    if sj_rows:
        _csv(dd / "figure1a_frontier_single_junction.csv", hdr, sj_rows)
        made.append(_fig1_panel(sj_rows, fd,
                                "F1a_frontier_single_junction.pdf",
                                "Single-junction devices", 29.4))
    if tan_rows:
        _csv(dd / "figure1b_frontier_tandem.csv", hdr, tan_rows)
        made.append(_fig1_panel(tan_rows, fd, "F1b_frontier_tandem.pdf",
                                "Tandem and module devices", 47.6))
    return made


# --------------------------------------------------------------------- F2
def fig2(cards: list, fd: pathlib.Path, dd: pathlib.Path) -> str | None:
    """Efficiency against reported area, log x. The scale penalty."""
    m = _measured(cards)
    rows = []
    for c in m:
        a = _v(c, "active_area_cm2")
        p = _v(c, "pce_certified") or _v(c, "pce_champion")
        if a is None or p is None:
            continue
        arch = ((c.get("device") or {}).get("architecture") or "unknown")
        rows.append([c["work_key"], c.get("source_month") or "", a, p,
                     "certified" if _v(c, "pce_certified") else "self-reported",
                     ARCH_LABEL.get(arch, arch)])
    if len(rows) < 4:
        return None
    _csv(dd / "figure2_area_penalty.csv",
         ["work_key", "month", "area_cm2", "pce_pct", "verification",
          "device_class"], rows)

    fig, ax = plt.subplots(figsize=(6.6, 3.3))
    ax.axvspan(0.001, 0.3, color="#f0f0f0", zorder=0)
    for kind, col, mk, sz in (("self-reported", "#9aa5b1", "o", 16),
                              ("certified", "#1A4E8A", "D", 26)):
        xs = [float(r[2]) for r in rows if r[4] == kind]
        ys = [float(r[3]) for r in rows if r[4] == kind]
        if xs:
            ax.scatter(xs, ys, s=sz, alpha=0.8, color=col, marker=mk,
                       edgecolors="none", label=kind, zorder=3)
    ax.set_xscale("log")
    ax.set_xlabel("Reported active or aperture area (cm$^2$)")
    ax.set_ylabel("Power conversion efficiency (%)")
    areas = [float(r[2]) for r in rows]
    _band(ax, f"{len(rows)} papers reporting both an area and an efficiency, "
              f"spanning {min(areas):g} to {max(areas):g} cm$^2$. Shading "
              f"marks the sub-0.3 cm$^2$ laboratory-cell regime.")
    ax.legend(loc="lower left", frameon=False)
    fig.savefig(fd / "F2_area_penalty.pdf")
    plt.close(fig)
    return "F2_area_penalty.pdf"


# --------------------------------------------------------------------- F3
def _fig3_panel(grid: dict, order: list, fams: list, fd: pathlib.Path,
                fname: str, subtitle: str) -> str:
    fig, ax = plt.subplots(figsize=(5.2, 3.1))
    colors = ["#1A4E8A", "#3E7CB1", "#81A4CD", "#B9C9DC", "#5C7A5C", "#c9c9c9"]
    bottom = [0.0] * len(order)
    for i, f in enumerate(fams):
        vals = [grid[a][f] for a in order]
        if not any(vals):
            continue
        ax.bar([AXIS_LABEL[a] for a in order], vals, bottom=bottom,
               color=colors[i % len(colors)], label=ARCH_LABEL.get(f, f),
               width=0.62, edgecolor="white", linewidth=0.4)
        bottom = [b + v for b, v in zip(bottom, vals)]
    ax.set_ylabel("Closely read papers")
    # Axis names are long; rotate rather than let them collide.
    ax.tick_params(axis="x", rotation=30)
    for t in ax.get_xticklabels():
        t.set_ha("right")
    total = sum(sum(grid[a].values()) for a in order)
    _band(ax, f"{subtitle}: {total} depth-tier papers by mechanism axis.")
    if len([f for f in fams if any(grid[a][f] for a in order)]) > 1:
        ax.legend(loc="upper right", frameon=False, ncol=2)
    fig.savefig(fd / fname)
    plt.close(fig)
    return fname


def fig3(cards: list, fd: pathlib.Path, dd: pathlib.Path) -> list:
    """Where the year's close reading went, SPLIT BY JUNCTION CLASS.

    Same reasoning as F1 (Havid, 2026-09-09). A single stacked bar mixing
    single junctions and tandems answers "how much was read on defects"
    but not "how much was read on defects IN A TANDEM", and the second
    question is the one a reader of a tandem section needs.

    Simulation and review papers are excluded here too. The effort map is a
    map of what was closely read for its MEASURED content; including theory
    papers would inflate axes with large computational literatures, and
    defects is exactly such an axis.
    """
    m = _measured(cards)
    fams = ARCH_ORDER + ["unknown"]

    def build(subset: list) -> tuple[dict, list]:
        axes_present = [a for a in AXIS_LABEL
                        if any(c.get("axis") == a for c in subset)]
        grid = {a: {f: 0 for f in fams} for a in axes_present}
        for c in subset:
            a = c.get("axis")
            if a not in grid:
                continue
            arch = ((c.get("device") or {}).get("architecture") or "unknown")
            if arch in ("none", "") or arch not in fams:
                arch = "unknown"
            grid[a][arch] += 1
        order = sorted(axes_present, key=lambda a: -sum(grid[a].values()))
        return grid, order

    sj = [c for c in m if _is_single_junction(c)]
    tan = [c for c in m if not _is_single_junction(c)]

    made = []
    rows = []
    for label, subset, fname, sub in (
        ("single_junction", sj, "F3a_effort_single_junction.pdf",
         "Single-junction devices"),
        ("tandem", tan, "F3b_effort_tandem.pdf", "Tandem and module devices"),
    ):
        grid, order = build(subset)
        if not order:
            continue
        rows += [[label, a, ARCH_LABEL.get(f, f), grid[a][f]]
                 for a in order for f in fams]
        made.append(_fig3_panel(grid, order, fams, fd, fname, sub))
    if rows:
        _csv(dd / "figure3_effort_map.csv",
             ["junction_class", "axis", "device_class", "n_depth_papers"],
             rows)
    return made


# --------------------------------------------------------------------- F4
def fig4(cards: list, fd: pathlib.Path, dd: pathlib.Path) -> str | None:
    """The year's operational-stability evidence in full.

    Its THINNESS is the finding, so the plate shows every value there is
    rather than a distribution.
    """
    m = _measured(cards)
    t80 = [(c["work_key"], c.get("source_month") or "", _v(c, "t80_h"),
            ((c.get("stability") or {}).get("protocol") or ""))
           for c in m if _v(c, "t80_h") is not None]
    protos: dict[str, int] = {}
    for c in m:
        p = (c.get("stability") or {}).get("protocol")
        if p:
            protos[p] = protos.get(p, 0) + 1
    if not t80 and not protos:
        return None
    _csv(dd / "figure4_stability_evidence.csv",
         ["work_key", "month", "t80_hours", "protocol"],
         [[a, b, c, d] for a, b, c, d in t80])

    fig, (axl, axr) = plt.subplots(1, 2, figsize=(6.8, 3.0),
                                   gridspec_kw={"width_ratios": [1.5, 1]})
    if t80:
        vals = sorted((float(x[2]) for x in t80))
        axl.scatter(vals, range(len(vals)), s=20, color="#1A4E8A",
                    edgecolors="none")
        axl.set_xscale("log")
        axl.set_xlabel("Reported T$_{80}$ (hours)")
        axl.set_yticks([])
        axl.set_ylabel("Individual reports")
        # OVERLAPPING X LABELS (Havid, 2026-09-09). A log axis over 144-3200 h
        # gets matplotlib's dense default decade+minor ticks, and the minor
        # labels collided into an unreadable smear. Fix: place a SMALL number
        # of explicit ticks at round hour values inside the real data range,
        # and suppress minor labels entirely. Ticks are derived from the data,
        # never hardcoded, so a different year re-derives them.
        from matplotlib.ticker import NullFormatter, FixedLocator, FixedFormatter
        candidates = [100, 200, 500, 1000, 2000, 5000, 10000]
        lo, hi = min(vals), max(vals)
        ticks = [t for t in candidates if lo * 0.7 <= t <= hi * 1.4]
        if len(ticks) < 2:
            ticks = [lo, hi]
        axl.xaxis.set_major_locator(FixedLocator(ticks))
        axl.xaxis.set_major_formatter(FixedFormatter(
            [f"{int(t):,}" for t in ticks]))
        axl.xaxis.set_minor_formatter(NullFormatter())
        _band(axl, f"Every T$_{{80}}$ reported: {len(vals)} of {len(m)} "
                   f"measured papers.")
    else:
        axl.axis("off")
    if protos:
        ks = sorted(protos, key=lambda k: -protos[k])[:6]
        axr.barh(range(len(ks)), [protos[k] for k in ks], color="#3E7CB1",
                 height=0.6)
        axr.set_yticks(range(len(ks)))
        axr.set_yticklabels(ks, fontsize=6.4)
        axr.invert_yaxis()
        axr.set_xlabel("Papers")
        # Integer ticks only: a count axis showing 0.5 papers is nonsense and
        # doubles the label density.
        from matplotlib.ticker import MaxNLocator
        axr.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=4))
        _band(axr, f"Protocol labels used ({sum(protos.values())} papers).")
    else:
        axr.axis("off")
    fig.subplots_adjust(wspace=0.32)
    fig.savefig(fd / "F4_stability_evidence.pdf")
    plt.close(fig)
    return "F4_stability_evidence.pdf"


# --------------------------------------------------------------------- F5
def fig5(cards: list, S: dict, fd: pathlib.Path, dd: pathlib.Path) -> str | None:
    """The frontier month by month, with DEVICE CLASS on every point.

    Only a yearly issue can plot this. The device class travels with the
    number because the highest values here are tandems.
    """
    months = S.get("frontier.months") or []
    cert = S.get("frontier.top_certified_series") or []
    champ = S.get("frontier.top_champion_series") or []
    ncert = S.get("frontier.n_certified_series") or []
    if not months:
        return None

    # Which device class produced each month's leading certified value?
    # Read from the cards, never assumed.
    m = _measured(cards)
    lead_class = {}
    for mo in months:
        best, cls = None, ""
        for c in m:
            if c.get("source_month") != mo:
                continue
            v = _v(c, "pce_certified")
            if v is not None and (best is None or v > best):
                best = v
                cls = ((c.get("device") or {}).get("architecture") or "unknown")
        lead_class[mo] = ARCH_LABEL.get(cls, cls) if best is not None else ""

    _csv(dd / "figure5_frontier_trajectory.csv",
         ["month", "top_certified_pct", "leading_device_class",
          "top_self_reported_pct", "n_certified_reports"],
         [[months[i],
           cert[i] if i < len(cert) and cert[i] is not None else "",
           lead_class.get(months[i], ""),
           champ[i] if i < len(champ) and champ[i] is not None else "",
           ncert[i] if i < len(ncert) else ""] for i in range(len(months))])

    xs = list(range(len(months)))
    fig, ax = plt.subplots(figsize=(6.6, 3.4))
    cx = [i for i in xs if i < len(champ) and champ[i] is not None]
    if cx:
        ax.plot(cx, [champ[i] for i in cx], "-o", ms=3.5, lw=1.0,
                color="#9aa5b1", label="best self-reported")
    kx = [i for i in xs if i < len(cert) and cert[i] is not None]
    if kx:
        sizes = [18 + 5 * (ncert[i] if i < len(ncert) else 0) for i in kx]
        ax.plot(kx, [cert[i] for i in kx], "-", lw=1.3, color="#1A4E8A")
        ax.scatter(kx, [cert[i] for i in kx], s=sizes, color="#1A4E8A",
                   marker="D", edgecolors="white", linewidths=0.5, zorder=4,
                   label="best certified")
        # Device class on EVERY point. This is the misattribution guard.
        for i in kx:
            cls = lead_class.get(months[i], "")
            if cls:
                ax.annotate(cls, (i, cert[i]), textcoords="offset points",
                            xytext=(0, 8), ha="center", fontsize=5.6,
                            color="#1A4E8A")
    gaps = [i for i in xs if i >= len(cert) or cert[i] is None]
    for i in gaps:
        ax.axvline(i, color="#dddddd", lw=6, zorder=0)
    ax.set_xticks(xs)
    ax.set_xticklabels([m[5:] for m in months])
    ax.set_xlabel(f"Month of {S.get('year')}")
    ax.set_ylabel("Power conversion efficiency (%)")
    note = (f"Point size scales with the number of certified reports that "
            f"month. Grey columns mark months with no certified value "
            f"reported.") if gaps else \
           "Point size scales with the number of certified reports."
    _band(ax, note)
    ax.legend(loc="lower right", frameon=False)
    fig.savefig(fd / "F5_frontier_trajectory.pdf")
    plt.close(fig)
    return "F5_frontier_trajectory.pdf"


# --------------------------------------------------------------------- F6
def fig6(S: dict, fd: pathlib.Path, dd: pathlib.Path) -> str | None:
    """Reporting practice month by month. Only a yearly issue has this."""
    months = S.get("frontier.months") or []
    present = [k for k in AUDIT_KEYS
               if S.get(f"audit.year.{k}.pct") is not None]
    if not months or not present:
        return None

    rows = [[k, S.get(f"audit.year.{k}.pct"),
             S.get(f"audit.year.{k}.month_min_pct"),
             S.get(f"audit.year.{k}.month_max_pct"),
             S.get(f"audit.year.{k}.n"),
             S.get(f"audit.year.{k}.denominator")] for k in present]
    _csv(dd / "figure6_audit_trajectory.csv",
         ["quantity", "pooled_pct", "month_min_pct", "month_max_pct",
          "n_detected", "denominator"], rows)

    fig, ax = plt.subplots(figsize=(6.6, 3.2))
    ys = list(range(len(present)))
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
    ax.set_yticks(ys)
    ax.set_yticklabels([AUDIT_SHORT[k] for k in present])
    ax.invert_yaxis()
    ax.set_xlabel("Abstracts in which the quantity was detected (%)")
    ax.set_xlim(left=0)
    den = S.get(f"audit.year.{present[0]}.denominator")
    _band(ax, f"Diamonds: pooled annual rate over {den} abstracts. Bars: the "
              f"monthly range. Detection in abstracts is a lower bound.")
    fig.savefig(fd / "F6_audit_trajectory.pdf")
    plt.close(fig)
    return "F6_audit_trajectory.pdf"


def figures(year: str) -> dict:
    if not is_year(year):
        raise SystemExit(f"expected a 4-digit year, got {year!r}")
    rd = run_dir(year, create=False)
    yd = yearly_dir(year)
    S = json.loads((yd / "stats_yearly.json").read_text(encoding="utf-8"))
    agg = aggregate(year, require_full_year=False)
    cards = agg["cards"]

    # Populate the abstract pool BEFORE any panel runs. Without this the
    # illumination fallback silently does nothing: `_ABSTRACTS` stays empty,
    # every `src` is "", and a truncated anchor whose "lux" fell outside
    # guard 3's 25-word cap resolves to "unknown" and reaches an AM1.5G
    # figure. The fix would look installed and change no output.
    global _ABSTRACTS
    _ABSTRACTS = {x["work_key"]: x["abstract"]
                  for x in read_jsonl(rd / "private" / "02_abstracts.jsonl")}

    fd = rd / "fig"
    fd.mkdir(exist_ok=True)
    dd = rd / "figdata"
    dd.mkdir(exist_ok=True)

    made, skipped = [], []
    for name, fn in (("F1", lambda: fig1(cards, fd, dd)),
                     ("F2", lambda: fig2(cards, fd, dd)),
                     ("F3", lambda: fig3(cards, fd, dd)),
                     ("F4", lambda: fig4(cards, fd, dd)),
                     ("F5", lambda: fig5(cards, S, fd, dd)),
                     ("F6", lambda: fig6(S, fd, dd))):
        out = fn()
        if out:
            made.append(out)
            print(f"[11y] {out}")
        else:
            # A figure with no data is NOT written. An empty axes frame
            # published as a figure looks like a finding.
            skipped.append(name)
            print(f"[11y] {name} SKIPPED: insufficient data")

    meta = {"year": year, "made": made, "skipped": skipped,
            "n_figures": len(made),
            "csv": sorted(p.name for p in dd.glob("*.csv"))}
    done(rd, "11y_figures_yearly", **meta)
    print("[11y]", json.dumps(meta)[:400])
    return meta


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: s11y_figures_yearly.py <YYYY>\n"
                         "No default: the period must be stated.")
    figures(sys.argv[1])
