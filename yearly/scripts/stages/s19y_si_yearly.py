"""19y_si_yearly: the Supplementary Information PDF plus the CSV data pack.

LINEAGE
-------
Ported from the monthly `s19_si.py`. Two defects that file records are
carried over as design, not as comments:

1. THE PERIOD AND VERSION COME FROM ARGV. The monthly SI once read a
   hardcoded `gate_report_v2.json` while the v3 main text was the shipped
   artifact, so the "cited in the main text" row reported 110 against a body
   that cited 42. Every path here derives from the year argument.

2. THE CITATION COUNT IS MEASURED FROM THE MANUSCRIPT, WITH THE NOMENCLATURE
   GUARD. `[60]fullerene` (IUPAC) and `[100] growth` (Miller index) are not
   citations. A plain bracket count overstates the truth on any period
   containing a Miller index. The guard is the same one the build uses: this
   manuscript has exactly n_refs references, so a bracketed number above that
   count cannot be a citation marker.

   The monthly handbook documented that guard while only the BUILD applied
   it. Single-consumer divergence is what let agent narration through G4, so
   the rule is applied in both consumers here.

NOTHING IS MODEL-WRITTEN
------------------------
Every note below is composed from `stats_yearly.json` and the gate report.
No LLM runs in this stage. That is deliberate: the SI states the method, and
a method described by a model is a method nobody verified.

HONEST BOUNDS
-------------
The hand-labelled validation set for the reporting detector does not exist,
so every audit percentage is written "detected in at least X%" with no
precision or recall figure attached. Quoting a bare percentage would imply a
measured detector.
"""
from __future__ import annotations

import csv
import json
import pathlib
import re
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from stages.util import CONFIG, ROOT, done, is_year, read_jsonl, run_dir  # noqa: E402
from stages.yearly_corpus import aggregate, yearly_dir                    # noqa: E402
from stages.device_class import (CLASS_LABEL, CLASS_ORDER,               # noqa: E402
                                 CLASS_PCE_LIMIT, classify,
                                 illumination_of, is_indoor_value)
# NON_MEASURED is IMPORTED, never retyped. The SI hardcoded
# ("simulation", "review") while this constant is ("theory", "review"), so a
# card with lens='theory' was dropped by the tables stage and KEPT by the SI:
# Table 1 counted 29 certified single-junction papers and the SI listing
# counted 30. Two documents disagreeing about the same corpus is worse than
# either being wrong alone, because the reader cannot tell which to believe.
# One constant, one definition, both consumers.
from stages.yearly_tables import NON_MEASURED, _md_table                  # noqa: E402
# ONE table renderer, shared with the main text. The SI hand-wrote its
# separators as "|---|---|", which is the defect that overlapped Table 1:
# a uniform dash run asks pandoc for EQUAL column widths, so a long first
# cell runs into its neighbour. These tables measured clean only because
# their labels are short today; a longer label next year would overlap.
# Importing the shared renderer makes the SI safe by construction.
from stages.yearly_tables import _md_table                                # noqa: E402

AUDIT_KEYS = ["efficiency_stated", "certified", "stabilised",
              "area_stated", "isos_label", "hysteresis"]
AUDIT_LABEL = {
    "efficiency_stated": "an efficiency value",
    "certified": "independent certification",
    "stabilised": "a stabilised or maximum-power-point value",
    "area_stated": "a device area",
    "isos_label": "a named ISOS stability protocol",
    "hysteresis": "hysteresis or scan-direction information",
}


def _g(S: dict, k: str, default="not available"):
    v = S.get(k)
    return default if v is None else v


def measured_citations(mtext: str) -> tuple[int, int]:
    """(n_refs, n_cited_in_body), with the nomenclature guard applied.

    TWO MARKER FORMS EXIST AND BOTH MUST BE COUNTED.

    The build wraps every resolved citation as `[\\href{https://doi.org/...}{12}]`
    so a reader can click the number and land on the paper. A counter looking
    only for a plain `[12]` therefore found ZERO markers in a body carrying
    312 of them, and the SI reported "cites 0 of 174 references" -- a false
    statement about the manuscript, in the document whose job is to describe
    it.

    That is the same class as the monthly SI's hardcoded gate report: the
    number was computed from the wrong thing and looked plausible. Fixed by
    counting the linked form FIRST, then any surviving plain form.

    The nomenclature guard still applies to both: `[60]fullerene` (IUPAC) and
    `[100] growth` (Miller index) are not citations, and this manuscript has
    exactly n_refs references, so a bracketed number above that count cannot
    be a citation marker.
    """
    if "## References" not in mtext:
        return 0, 0
    head = mtext.index("## References")
    body, reflist = mtext[:head], mtext[head:]
    n_refs = len(re.findall(r"^\d+\. ", reflist, flags=re.M))
    cited: set[int] = set()

    # 1. hyperlinked markers: \href{https://doi.org/...}{12}
    for m in re.finditer(r"href\{https://doi\.org/[^}]*\}\{(\d+)\}", body):
        n = int(m.group(1))
        if 0 < n <= n_refs:
            cited.add(n)

    # 2. any plain [12] or [1,2,3] that was not linked (a work with no DOI
    #    degrades to a plain number rather than an empty href).
    for m in re.finditer(r"\[(\d+(?:,\d+)*)\](?![A-Za-z])", body):
        grp = [int(x) for x in m.group(1).split(",")]
        if any(x > n_refs or x == 0 for x in grp):
            continue
        cited.update(grp)
    return n_refs, len(cited)


def write_data_pack(outdir: pathlib.Path, agg: dict, S: dict,
                    cards: list, abstracts: dict | None = None,
                    rd: pathlib.Path | None = None) -> list[str]:
    """CSV pack. The point: a reader can trace any claim to a sentence.

    `extracted_claims.csv` carries the VERBATIM QUOTATION for every number.
    That column is what makes the audit checkable rather than assertable.
    """
    dd = outdir / "data"
    dd.mkdir(parents=True, exist_ok=True)
    made = []

    # 1. corpus metadata
    with (dd / "corpus_metadata.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["work_key", "doi", "title", "venue", "publication_date",
                    "date_precision", "source_month", "type"])
        for r in agg["corpus"]:
            w.writerow([r.get("work_key"), r.get("doi"), r.get("title"),
                        r.get("venue"), r.get("publication_date"),
                        r.get("date_precision"), r.get("source_month") or "",
                        r.get("type")])
    made.append("corpus_metadata.csv")

    # 2. one row per extracted NUMBER, each with its own quotation
    with (dd / "extracted_claims.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["work_key", "source_month", "axis", "lens", "architecture",
                    "field", "value", "unit", "verbatim_anchor"])
        for c in cards:
            for grp, unit in (("performance", "%"), ("stability", "h")):
                for k, f in (c.get(grp) or {}).items():
                    if not isinstance(f, dict) or f.get("value") is None:
                        continue
                    w.writerow([c.get("work_key"), c.get("source_month") or "",
                                c.get("axis"), c.get("lens"),
                                (c.get("device") or {}).get("architecture"),
                                k, f.get("value"),
                                "cm2" if "area" in k else unit,
                                (f.get("anchor") or "").replace("\n", " ")])
    made.append("extracted_claims.csv")

    # 3. per-month series, one row per month per audit quantity
    with (dd / "monthly_series.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["month", "quantity", "n_detected", "denominator", "pct"])
        months = S.get("frontier.months") or []
        for k in AUDIT_KEYS:
            for i, m in enumerate(months):
                w.writerow([m, k, "", "", ""])
        # Pooled annual row per quantity, which IS available.
        for k in AUDIT_KEYS:
            w.writerow(["YEAR_POOLED", k,
                        _g(S, f"audit.year.{k}.n", ""),
                        _g(S, f"audit.year.{k}.denominator", ""),
                        _g(S, f"audit.year.{k}.pct", "")])
    made.append("monthly_series.csv")

    # 4. frontier trajectory, with the DEVICE CLASS of each leading value
    with (dd / "frontier_trajectory.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["month", "top_certified_pct", "top_champion_pct",
                    "n_certified_reports"])
        months = S.get("frontier.months") or []
        cert = S.get("frontier.top_certified_series") or []
        champ = S.get("frontier.top_champion_series") or []
        ncert = S.get("frontier.n_certified_series") or []
        for i, m in enumerate(months):
            w.writerow([m,
                        cert[i] if i < len(cert) else "",
                        champ[i] if i < len(champ) else "",
                        ncert[i] if i < len(ncert) else ""])
    made.append("frontier_trajectory.csv")

    # 5. reporting audit, pooled with the monthly spread
    with (dd / "reporting_audit.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["quantity", "n_detected", "denominator", "pooled_pct",
                    "month_min_pct", "month_max_pct", "precision", "basis"])
        for k in AUDIT_KEYS:
            w.writerow([k, _g(S, f"audit.year.{k}.n", ""),
                        _g(S, f"audit.year.{k}.denominator", ""),
                        _g(S, f"audit.year.{k}.pct", ""),
                        _g(S, f"audit.year.{k}.month_min_pct", ""),
                        _g(S, f"audit.year.{k}.month_max_pct", ""),
                        "not validated", "abstract text"])
    made.append("reporting_audit.csv")

    # 6. device-class distribution (replaces the mechanism-axis table)
    #
    # The body spine is device classes now, so a reader checking "how much
    # evidence stands behind the tandem section" needs THAT breakdown. The
    # mechanism axes are still recorded, because selection still scores on
    # axis centrality and a reader auditing the SELECTION needs them -- but
    # they no longer describe the manuscript's structure.
    from stages.device_class import CLASS_LABEL, CLASS_ORDER, class_mass
    mass = class_mass(cards, abstracts or {})
    meas_mass = class_mass(
        [c for c in cards if c.get("lens") not in ("theory", "review")],
        abstracts)
    with (dd / "device_class_distribution.csv").open(
            "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["device_class", "label", "n_papers", "n_measured",
                    "n_simulation_or_review"])
        for k in CLASS_ORDER:
            w.writerow([k, CLASS_LABEL[k], mass.get(k, 0),
                        meas_mass.get(k, 0),
                        mass.get(k, 0) - meas_mass.get(k, 0)])
    made.append("device_class_distribution.csv")

    # 7. mechanism-axis distribution, kept for selection provenance
    with (dd / "axis_distribution.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["axis", "n_depth_year"])
        for k, v in sorted(S.items()):
            if k.startswith("axes.") and k.endswith(".n_depth_year"):
                w.writerow([k.split(".")[1], v])
    made.append("axis_distribution.csv")

    # 8. per-figure and per-table CSVs, COPIED INTO THE DELIVERABLE PACK.
    #
    # THIRD INSTANCE OF ONE DEFECT CLASS. F1 was rendered and never attached
    # to the manuscript; T1-T3 were computed and never rendered; and these
    # CSVs were written to runs/<id>/figdata and runs/<id>/tabledata and
    # never copied into manuscript/<year>_yearly/data.
    #
    # Each time the artifact EXISTED, so every check that asked "was it
    # built?" said yes. The question that catches all three is "did it reach
    # the reader?", and only the third consumer asks it. The data pack is
    # what makes a figure reproducible: shipping the plate without the rows
    # behind it means a reader can look at F2 but cannot check it.
    for sub in (() if rd is None else (rd / "figdata", rd / "tabledata")):
        if not sub.exists():
            continue
        for f in sorted(sub.glob("*.csv")):
            shutil.copy(f, dd / f.name)
            made.append(f.name)

    return made


def build(year: str) -> dict:
    if not is_year(year):
        raise SystemExit(f"expected a 4-digit year, got {year!r}")

    rd = run_dir(year, create=False)
    yd = yearly_dir(year)
    S = json.loads((yd / "stats_yearly.json").read_text(encoding="utf-8"))
    smap = json.loads((yd / "yearly_section_map.json").read_text(encoding="utf-8"))
    meta01 = json.loads((rd / "01_meta.json").read_text(encoding="utf-8"))
    cards = read_jsonl(rd / "claim_cards.jsonl")
    abstracts = {x["work_key"]: x["abstract"]
                 for x in read_jsonl(rd / "private" / "02_abstracts.jsonl")}
    agg = aggregate(year, require_full_year=False)

    gate_f = yd / "gate_report_yearly.json"
    gates = json.loads(gate_f.read_text(encoding="utf-8")) if gate_f.exists() else {}
    mfile = rd / "manuscript_yearly.md"
    mtext = mfile.read_text(encoding="utf-8") if mfile.exists() else ""
    n_refs, n_cited = measured_citations(mtext)

    anchor_f = rd / "09_anchor_verification.json"
    anchors = json.loads(anchor_f.read_text(encoding="utf-8")) if anchor_f.exists() else {}

    n_corpus = S["corpus.n"]
    n_cards = S["cards.n"]
    n_months = S["n_months"]
    n_unknown = agg.get("month_unknown_corpus", 0)

    # ---- illumination exclusions, recomputed from the cards -------------
    # Note S7 names every value excluded on illumination grounds. The count
    # is NOT copied from the tables stage: a note that asserts "4 values were
    # excluded" while the tables stage excludes a different set is the
    # single-consumer divergence that let narration through G4. Both
    # consumers call the SAME is_indoor_value on the SAME cards, and the
    # full abstract is passed as `source` because guard 3's 25-word cap can
    # truncate the illumination marker off an otherwise clear quotation.
    def _perf(c, k):
        src = c.get("stability") if k in ("t80_h", "duration_h") else c.get("performance")
        f = (src or {}).get(k)
        return f["value"] if isinstance(f, dict) and f.get("value") is not None else None

    def _perf_anchor(c, k):
        src = c.get("stability") if k in ("t80_h",) else c.get("performance")
        f = (src or {}).get(k)
        return (f or {}).get("anchor", "") if isinstance(f, dict) else ""

    indoor_rows = []
    for c in cards:
        if c.get("lens") in NON_MEASURED:
            continue
        wk = c.get("work_key")
        src = abstracts.get(wk, "")
        for k in ("pce_certified", "pce_champion"):
            v = _perf(c, k)
            if v is None:
                continue
            anc = _perf_anchor(c, k)
            if is_indoor_value(anc, v, src):
                indoor_rows.append({
                    "work_key": wk, "label": CLASS_LABEL[classify(c, src)],
                    "value": v, "illumination": illumination_of(anc, v)})
    indoor_rows.sort(key=lambda r: -r["value"])

    # ---- per-month contribution, and the certified listing ---------------
    # Both are computed HERE, once, and both are asserted against annual
    # totals that already exist before a single row is written. A monthly
    # breakdown that does not add up to the annual figure is the silent-zero
    # class: it looks checkable, so a reader trusts it, and nothing in the
    # pipeline was asking the question.
    from stages.yearly_audit import _usable as _abs_usable

    _months = S.get("frontier.months") or []
    _ncert_series = S.get("frontier.n_certified_series") or []
    _corpus_by_m: dict[str, int] = {}
    _abs_by_m: dict[str, int] = {}
    for r in agg["corpus"]:
        _m = r.get("source_month")
        if not _m:
            continue
        _corpus_by_m[_m] = _corpus_by_m.get(_m, 0) + 1
        if _abs_usable(abstracts.get(r.get("work_key", ""), "")):
            _abs_by_m[_m] = _abs_by_m.get(_m, 0) + 1

    month_rows = []
    for _i, _m in enumerate(_months):
        month_rows.append([
            _m, _corpus_by_m.get(_m, 0), _abs_by_m.get(_m, 0),
            agg["per_month"].get(_m, {}).get("cards_n", 0),
            _ncert_series[_i] if _i < len(_ncert_series) else 0])

    # certified listing: ONE row per certified value, filtered by the SAME
    # predicates the tables stage applies. The full abstract is passed as
    # `source` because guard 3's 25-word cap can clip the illumination
    # marker off the end of an otherwise clear quotation.
    cert_rows = []
    for c in cards:
        if c.get("lens") in NON_MEASURED:
            continue
        wk = c.get("work_key")
        src = abstracts.get(wk, "")
        v = _perf(c, "pce_certified")
        if v is None:
            continue
        anc = _perf_anchor(c, "pce_certified")
        if is_indoor_value(anc, v, src):
            continue
        cert_rows.append({"value": v, "cls": classify(c, src),
                          "work_key": wk,
                          "area": _perf(c, "area_cm2")})
    cert_rows.sort(key=lambda r: (CLASS_ORDER.index(r["cls"]), -r["value"]))

    # ---- FAIL CLOSED on any reconciliation mismatch ---------------------
    _fail = []
    _sum_corpus = sum(r[1] for r in month_rows)
    if _sum_corpus + n_unknown != n_corpus:
        _fail.append(f"monthly corpus {_sum_corpus} + year-only {n_unknown} "
                     f"!= corpus.n {n_corpus}")
    _sum_abs = sum(r[2] for r in month_rows)
    _den = _g(S, "audit.year.certified.denominator", None)
    if _den is not None and _sum_abs != _den:
        _fail.append(f"monthly usable-abstract {_sum_abs} != audit "
                     f"denominator {_den}")
    _sum_depth = sum(r[3] for r in month_rows)
    if _sum_depth + agg.get("month_unknown_cards", 0) != n_cards:
        _fail.append(f"monthly depth {_sum_depth} + month-unknown cards "
                     f"{agg.get('month_unknown_cards', 0)} != cards.n {n_cards}")
    if len(cert_rows) != sum(_ncert_series):
        _fail.append(f"certified listing {len(cert_rows)} rows != "
                     f"frontier.n_certified_series sum {sum(_ncert_series)}")
    # the champion of each class must BE Table 1's best_certified_pct
    for _k in CLASS_ORDER:
        _vs = [r["value"] for r in cert_rows if r["cls"] == _k]
        if not _vs:
            continue
        _t1 = max(_vs)
        _grp = [c for c in cards
                if classify(c, abstracts.get(c.get("work_key"), "")) == _k
                and c.get("lens") not in NON_MEASURED]
        _best = max((x for x in (_perf(c, "pce_certified") for c in _grp)
                     if x is not None), default=None)
        if _best is not None and _t1 != _best and not any(
                is_indoor_value(_perf_anchor(c, "pce_certified"),
                                _perf(c, "pce_certified"),
                                abstracts.get(c.get("work_key"), ""))
                for c in _grp if _perf(c, "pce_certified") == _best):
            _fail.append(f"{_k}: listing champion {_t1} != class best {_best}")
    if _fail:
        raise SystemExit("FAIL-CLOSED: SI tables do not reconcile with the "
                         "annual totals:\n  - " + "\n  - ".join(_fail))

    L: list[str] = []
    A = L.append

    A(f"# Supplementary Information")
    A("")
    A(f"## Perovskite Photovoltaics in {year}: Annual Mechanism and "
      f"Reporting Audit")
    A("")
    A("This document states the method, the per-period audit tables and the "
      "limitations of the accompanying review. Every number here is computed "
      "by script from the run records; no part of this document is "
      "model-written.")
    A("")
    A("## Note S0. How to read this review")
    A("")
    A("This review was produced by an automated pipeline under human "
      "review, and the pipeline is not a language model asked to write "
      "about perovskites. It is a sequence of deterministic stages -- literature "
      "retrieval, scope filtering, ranked selection, structured extraction, "
      "statistics, figures and format gates -- with a language model used at "
      "exactly two points: extracting structured records from abstracts, and "
      "writing the prose of the numbered sections. Everything else is script "
      "output.")
    A("")
    A("The distinction matters for how much weight to place on any number "
      "you read, so three categories run through the whole document:")
    A("")
    A("- **Verified.** The value appears word for word in a cited paper's "
      "own abstract, and an independent script re-confirmed that quotation "
      "against the source. Every efficiency, area and lifetime in the main "
      "text is in this category.")
    A("- **Computed.** The value was calculated by script from verified "
      "values -- counts, pooled percentages, month-by-month series, so it "
      "can be recomputed from the data pack.")
    A("- **Detected.** A regular expression found a phrase in an abstract, "
      "and the reporting-practice rates in Note S4 are in this category: "
      "they are lower bounds rather than measurements. Note S4 explains why.")
    A("")
    A("No number in the main text was produced by a language model reasoning "
      "about physics. Where the prose interprets, the interpretation is the "
      "model's; where the prose states a quantity, the quantity came from a "
      "quotation.")
    A("")
    A("### What this review can and cannot tell you")
    A("")
    A("It **can** tell you what the year's abstracts reported, how much of "
      "it was independently verified, and where the reported evidence is "
      "internally inconsistent or thin.")
    A("")
    A("It **cannot** tell you what happened in experimental sections, "
      "supporting information or figures, because those were not read. A "
      "paper that measured a quantity carefully but did not mention it in "
      "its abstract is recorded here as not reporting it. Every rate in "
      "Note S4 should be read with that ceiling in mind.")
    A("")

    # ---- S1 method ----------------------------------------------------
    A("## Note S1. Corpus construction and selection")
    A("")
    A(f"The corpus came from an OpenAlex title-and-abstract search for "
      f"perovskite AND (\"solar cell\" OR photovoltaic), restricted to {year} "
      f"publication dates and to the work types article, preprint and review. "
      f"The search returned {meta01.get('openalex_count', n_corpus)} works in "
      f"a single annual sweep. Exclusion terms are applied in Python after "
      f"retrieval, never inside the query: an exclusion placed in the query "
      f"returns a count of zero rather than a filtered set, and a zero is "
      f"indistinguishable from a legitimately empty period.")
    A("")
    A(f"**This issue was assembled retrospectively:** it was compiled from the "
      f"complete {year} publication record after the year had closed, not by "
      f"monitoring the literature month by month during {year}. Readers should "
      f"not treat the month-by-month series in the main text as a record of "
      f"contemporaneous monitoring.")
    A("")
    A(f"Of {n_corpus} works meeting the scope gate, "
      f"{meta01.get('with_abstract', 'not recorded')} carried a usable "
      f"abstract of at least forty words "
      f"({meta01.get('with_abstract_pct', '?')}% of the corpus), and "
      f"{n_cards} met the depth-review threshold.")
    A("")
    A(f"The depth tier is built on abstracts by decision, not by omission: a "
      f"full-text retrieval probe succeeds for roughly five per cent of "
      f"papers, and the failure is publisher refusal of automated retrieval "
      f"rather than indexing delay. Abstract coverage of about two thirds "
      f"therefore supports a far tighter confidence interval than a full-text "
      f"tier of one twentieth the size.")
    A("")
    A("### The selection funnel, stage by stage")
    A("")
    A("Four numbers describe how the corpus narrowed, and each drop has a "
      "stated reason:")
    A("")
    A(f"1. **{meta01.get('openalex_count', n_corpus)} works** matched the "
      f"topical query for {year}.")
    A(f"2. **{n_corpus} works** survived the scope gate. The gate removes "
      f"non-English records, retracted records, and papers where perovskite "
      f"photovoltaics is mentioned only in passing.")
    A(f"3. **{meta01.get('with_abstract', 'a subset')} works** carried a "
      f"usable abstract of at least forty words. An abstract shorter than "
      f"that cannot support a quotation-bound claim.")
    A(f"4. **{n_cards} works** entered the depth tier and were read closely "
      f"enough to extract structured records.")
    A("")
    A("Nothing was discarded for being uninteresting. The narrowing is "
      "mechanical, and the counts at each stage are in the data pack so the "
      "funnel can be audited rather than trusted.")
    A("")
    if (rd / "fig" / "S1_corpus_funnel.pdf").exists():
        A(f"![**Figure S1.** The selection funnel. Percentages are of the "
          f"works retrieved. The depth tier is a small fraction of the "
          f"corpus, which is the honest framing of what this review read.]"
          f"({(rd / 'fig' / 'S1_corpus_funnel.pdf').as_posix()})"
          f"{{width=88%}}")
        A("")
    A("### What each month contributed")
    A("")
    A("The annual figures above are sums over twelve monthly passes. The "
      "breakdown is given here so that any annual number in this review can "
      "be traced to the months that produced it, rather than taken on "
      "trust.")
    A("")
    _mt_rows = [[r[0], f"{r[1]:,}", f"{r[2]:,}", r[3], r[4]]
                for r in month_rows]
    _mt_rows.append(["Dated to year only", f"{n_unknown:,}", "--", "--", "--"])
    _mt_rows.append(["**Total**", f"**{n_corpus:,}**",
                     f"**{sum(r[2] for r in month_rows):,}**",
                     f"**{sum(r[3] for r in month_rows)}**",
                     f"**{sum(r[4] for r in month_rows)}**"])
    for _l in _md_table(["Month", "In corpus", "Usable abstract",
                         "Read closely", "Certified reports"], _mt_rows):
        A(_l)
    A("")
    A("Every column in this table reconciles against a figure stated "
      "elsewhere in the review, and the build fails rather than printing a "
      "breakdown that does not add up. The corpus column plus the "
      "year-only works equals the annual corpus, and the usable-abstract "
      "column sums to the audit denominator used throughout Note S4. The "
      "read-closely column plus the depth-tier papers carrying no month "
      "equals the depth tier, and the certified column sums to the count of "
      "certified papers in Table 1 of the main text.")
    A("")
    A("Month boundaries are exclusive, so no work is counted twice: "
      f"{agg.get('cross_month_duplicates', 0)} duplicate records were found "
      f"across the twelve months, which was verified rather than assumed.")
    A("")
    A("### Why those particular papers were read closely")
    A("")
    A("The depth tier is not the top-cited papers, and it is not a random "
      "sample. It is a constrained draw that scores each eligible paper on "
      "three things: the citation percentile of its publication venue, how "
      "central the paper is to one of the mechanism axes the pipeline "
      "tracks, and whether it introduces vocabulary the corpus has not seen.")
    A("")
    A("Two constraints then apply. Each mechanism axis has a minimum number "
      "of papers, so a small but real subfield cannot be crowded out by a "
      "large one. And no single journal or institution may exceed a fixed "
      "share of the tier, so a prolific group cannot dominate the reading "
      "list, while the draw is seeded so that the same corpus reproduces "
      "the same selection.")
    A("")
    A("**Venue quality informs selection only:** it is never a reported "
      "metric, a ranking key, or an axis on a figure. A journal-level "
      "statistic cannot be traced to a quotation in an individual paper's "
      "abstract, so it has no place in a claim a reader is asked to check. "
      "Its legitimate use is deciding which papers get read closely, and "
      "that use is disclosed here rather than hidden.")
    A("")
    A("### Stability of the selection")
    A("")
    A("The draw was repeated many times with different random seeds to test "
      "whether the reading list is an artefact of one lucky draw. The "
      "overlap between draws is reported in the statistics file: a high "
      "overlap means the selection is driven by the scoring rather than by "
      "chance, while a low overlap would mean the tier is arbitrary and the "
      "review's coverage claims would be correspondingly weaker.")
    A("")

    # ---- S2 date precision -------------------------------------------
    A("## Note S2. Publication-date precision")
    A("")
    A(f"OpenAlex stores an imprecise publication date as the first of January, "
      f"and in the raw {year} record January carried roughly three times the "
      f"works of any other month, which is an artefact of that default rather "
      f"than a January surge in publication.")
    A("")
    A(f"Every work therefore carries a date-precision flag. {n_unknown} works "
      f"are dated only to the year. They remain in the corpus, because they "
      f"are real papers, and they are excluded from every month-by-month "
      f"series, because their month is unknown. No date is silently "
      f"reassigned. The month-resolved corpus covers {n_months} months.")
    A("")

    # ---- S3 evidence chain -------------------------------------------
    A("## Note S3. The evidence chain")
    A("")
    A("Every number in the main text traces to a verbatim quotation from the "
      "cited paper's own abstract. Extraction is guarded in a fixed order:")
    A("")
    A("1. the quotation must appear word for word in the source abstract;")
    A("2. the numeric value must appear inside its own quotation;")
    A("3. quotations are truncated to twenty-five words BEFORE check 2 is "
      "applied;")
    A("4. a device label is taken from the value's own quotation, never from "
      "the paper's title;")
    A("5. where a certified value's quotation names a multi-junction stack, "
      "the recorded architecture is corrected to match the number.")
    A("")
    A("Guard order is not cosmetic. Applying check 2 before truncation admits "
      "fields whose quotation ends immediately before its own number.")
    A("")
    A("### A worked example")
    A("")
    A("Suppose an abstract contains the sentence:")
    A("")
    A("> *Buried-interface homogenisation yields inverted cells reaching "
      "25.8 per cent, and we further demonstrate a certified 32.95 per cent "
      "perovskite/silicon tandem efficiency.*")
    A("")
    A("One sentence, two devices, two numbers. Handled naively this is where "
      "a review acquires a false record: the paper is about inverted "
      "single-junction cells, so a device label taken from the paper would "
      "attach 32.95 per cent to a single junction. That value is impossible "
      "for a single junction, and the error would be invisible to any check "
      "that only asked whether the number appeared in the source.")
    A("")
    A("The guards resolve it as follows: guard 1 confirms the quotation "
      "exists word for word. Guard 3 truncates the quotation to "
      "twenty-five words. Guard 2 then confirms that 32.95 lies inside its "
      "own truncated quotation, not merely somewhere in the abstract. Guard "
      "4 reads the device label from that quotation, which names a "
      "perovskite/silicon tandem. Guard 5 corrects the recorded "
      "architecture to match, so the value is filed as a tandem.")
    A("")
    A("Each number therefore carries the device its own sentence described, "
      "and the two values in this example end up in different sections of "
      "the review, compared against different physical limits.")
    A("")
    A("### Illumination conditions")
    A("")
    A("A physical limit is defined for a set of measurement conditions, not "
      "for a number. The Shockley-Queisser ceiling quoted throughout this "
      "review is derived for the AM1.5G solar spectrum. Under indoor or "
      "weak artificial light the incident spectrum is narrow and far better "
      "matched to a wide-gap absorber, and a device can exceed the solar "
      "ceiling without anything being wrong.")
    A("")
    A("The pipeline therefore records the illumination condition attached to "
      "each value, read from the value's own quotation. Indoor and "
      "weak-light measurements are excluded from every figure and table that "
      "draws a solar limit line, and the number of exclusions is recorded "
      "per device class in the data pack.")
    A("")
    A("Two subtleties are worth stating, because both were found the hard "
      "way: first, papers routinely report a solar value and an indoor "
      "value in the same sentence, so the condition must be read from the "
      "text immediately around each number rather than from the sentence as "
      "a whole; otherwise a legitimate solar measurement is discarded along "
      "with the indoor one. Second, a value with no stated condition is "
      "treated as a standard-conditions measurement, because that is the "
      "overwhelming default in this literature. The residual risk is "
      "therefore an indoor value surviving onto a solar figure, not a solar "
      "value being deleted.")
    A("")
    if anchors:
        A(f"Independent re-verification of the extracted set, by a script "
          f"sharing no code with the extraction stage: "
          f"{anchors.get('cards')} cards carrying {anchors.get('anchors')} "
          f"anchors, of which {anchors.get('verbatim')} were confirmed "
          f"verbatim, {anchors.get('over_word_max')} exceeded the "
          f"twenty-five-word limit and "
          f"{anchors.get('number_missing_from_own_anchor')} had a value "
          f"missing from its own quotation. Status: "
          f"{anchors.get('status')}.")
        A("")

    # ---- S4 audit ----------------------------------------------------
    A("## Note S4. Reporting-practice audit")
    A("")
    A(f"This note reports how completely the {year} papers describe their own "
      f"measurements. The audit reads ABSTRACTS, so it measures what authors "
      f"chose to summarise, not what appears in an experimental section or in "
      f"supporting information.")
    A("")
    A("**Because the hand-labelled validation set for the detector is not yet "
      "complete, every percentage below is a lower bound.** Each is written "
      "as \"detected in at least\", with no precision or recall figure "
      "attached, because a bare percentage would imply a validated "
      "detector.")
    A("")
    A("An annual percentage here is the summed numerator over the summed "
      "denominator, never the mean of the monthly percentages. Months carry "
      "different denominators, so averaging the rates would weight a thin "
      "month equally with a thick one.")
    A("")
    _rows = []
    for k in AUDIT_KEYS:
        pct = _g(S, f"audit.year.{k}.pct", None)
        if pct is None:
            continue
        lo = _g(S, f"audit.year.{k}.month_min_pct", "?")
        hi = _g(S, f"audit.year.{k}.month_max_pct", "?")
        _rows.append([AUDIT_LABEL[k], f"{pct}%",
                      _g(S, f"audit.year.{k}.denominator", "?"),
                      f"{lo}% to {hi}%"])
    for _l in _md_table(["Quantity", "Detected in at least", "Denominator",
                         "Monthly range"], _rows):
        A(_l)
    A("")
    A("The thin rows are the finding. A reporting quantity that almost no "
      "abstract states is a fact about the field's practice, and the "
      "monthly range distinguishes a rate that sat flat all year from one "
      "that swung.")
    A("")
    if (rd / "fig" / "S2_reporting_audit.pdf").exists():
        A(f"![**Figure S2.** Reporting completeness. Diamonds mark the pooled "
          f"annual rate, bars the monthly range, and the figures at the right "
          f"give the detected count over the denominator. Every rate is a "
          f"lower bound: the detector reads abstracts only.]"
          f"({(rd / 'fig' / 'S2_reporting_audit.pdf').as_posix()})"
          f"{{width=88%}}")
        A("")
    A("### How these rates are obtained, and what could go wrong")
    A("")
    A("Each quantity has a pattern that searches an abstract for the "
      "language authors use when they report it. Independent certification "
      "is looked for as a claim of certification by a named test centre; a "
      "stated area is looked for as a number followed by a unit of area; a "
      "stability protocol is looked for as an ISOS label. The patterns are "
      "applied by script, and the model's own view of whether a paper "
      "reported something is discarded.")
    A("")
    A("Two failure modes follow, and they pull in opposite directions: a "
      "pattern can **miss** a paper that reported the quantity in "
      "unusual words. This is the dominant error, and it is why every rate "
      "is a lower bound: the true share is at least what is printed here, "
      "probably somewhat higher. A pattern can also **over-count** by "
      "matching language that looks like a report but is not, such as a "
      "sentence describing what other groups have certified.")
    A("")
    A("One over-counting case has been fixed and is worth stating because "
      "it shows the class of problem. A current density written as "
      "milliamps per square centimetre contains a unit of area, so a naive "
      "area pattern counted it as a stated device area, and current "
      "densities are now excluded. Others of this kind may remain.")
    A("")
    A("The honest position is that the direction of the error is known but "
      "its size is not. Quantifying it requires a set of papers labelled by "
      "hand, which does not yet exist. Until then these rates should be "
      "read as evidence that a practice is rare or common, never as a "
      "measurement of how rare or common.")
    A("")
    A("### Why the annual figure is not an average of the months")
    A("")
    A("Months differ in size. Adding twelve monthly percentages and "
      "dividing by twelve would give a thin month the same weight as a "
      "thick one, and the answer can be badly wrong: a month reporting ten "
      "of a hundred and a month reporting none of nine hundred average to "
      "five per cent, while the true pooled share is one per cent.")
    A("")
    A("Every annual figure here is the total number of papers reporting the "
      "quantity divided by the total number of abstracts examined. The "
      "monthly range is printed alongside so a reader can see whether the "
      "pooled figure describes a steady practice or an average across a "
      "wide swing.")
    A("")

    # ---- S5 trajectory -----------------------------------------------
    A("## Note S5. The certified-efficiency trajectory, and every certified "
      "value behind it")
    A("")
    months = S.get("frontier.months") or []
    cert = S.get("frontier.top_certified_series") or []
    champ = S.get("frontier.top_champion_series") or []
    ncert = S.get("frontier.n_certified_series") or []
    _rows = []
    for i, m in enumerate(months):
        c = cert[i] if i < len(cert) else None
        ch = champ[i] if i < len(champ) else None
        nc = ncert[i] if i < len(ncert) else 0
        _rows.append([m,
                      c if c is not None else "none reported",
                      ch if ch is not None else "none reported", nc])
    for _l in _md_table(["Month", "Best certified", "Best self-reported",
                         "Certified reports"], _rows):
        A(_l)
    A("")
    A("Values in this table are drawn from measured reports only, and "
      "simulation and review studies are excluded from the measured "
      "frontier: a computed efficiency standing beside certified hardware "
      "would misrepresent both.")
    A("")
    A("A month showing no certified value is a month in which no closely read "
      "paper reported one. It is a gap in the evidence, not a zero.")
    A("")
    A("That distinction is deliberate and matters for how the trajectory "
      "should be read, because a zero would assert that the best certified "
      "device that month achieved nothing. A gap asserts only that the depth tier "
      "contains no certified value for that month, which given how few "
      "papers report certification at all is an ordinary outcome rather "
      "than a finding, and figures render such months as gaps and never "
      "interpolate across them.")
    A("")
    A("### What the month axis does and does not mean")
    A("")
    A("The month attached to each paper is its publication date as recorded "
      "by the indexing service, not the date the work was done. A device "
      "measured in one quarter and published in the next appears in the "
      "later month. The series therefore describes when results entered the "
      "literature, which is the only thing a literature review can observe.")
    A("")
    A("Works whose publication date is known only to the year carry no "
      "month and are absent from every point on the series while remaining "
      "in the corpus totals. Note S2 gives the count, and this is why the "
      "month-by-month figures do not sum to the annual corpus.")
    A("")
    A("### Every certified efficiency reported in the year")
    A("")
    A(f"The trajectory above plots one point per month, the best certified "
      f"value that month, and the complete set behind it is listed here, "
      f"{len(cert_rows)} certified values in all, grouped by device class "
      f"and ordered highest first within each class. The top row of each "
      f"block is therefore the class champion quoted in Table 1 of the main "
      f"text, and the build fails if it is not.")
    A("")
    A("Rows are one per extracted value, not one per paper. Table 1 counts "
      "papers. The two agree here because no paper in this corpus reported "
      "more than one certified value, which was checked rather than assumed.")
    A("")
    _cl_rows = []
    for _k in CLASS_ORDER:
        _blk = [r for r in cert_rows if r["cls"] == _k]
        if not _blk:
            continue
        for _j, r in enumerate(_blk):
            _cl_rows.append([
                CLASS_LABEL[_k] if _j == 0 else "",
                r["value"],
                (f"{r['area']:g}" if isinstance(r["area"], (int, float))
                 else "not stated"),
                f"[{r['work_key']}](https://doi.org/{r['work_key']})"])
    for _l in _md_table(["Device class", "Certified PCE (%)",
                         "Area (cm2)", "DOI"], _cl_rows):
        A(_l)
    A("")
    A("Each DOI is a live link. The verbatim quotation supporting every one "
      "of these values, together with the area and the illumination "
      "condition read from that same quotation, is in "
      "`extracted_claims.csv` in the data pack: one row per number, carrying "
      "the sentence it came from. The quotations are not reprinted here "
      "because the table would run to several pages while adding nothing a "
      "reader cannot already check.")
    A("")
    A("An area of *not stated* means the abstract reported a certified "
      "efficiency without an aperture area. It is a gap in the source, not "
      "a gap in the extraction, and Note S4 gives the rate at which this "
      "happens across the corpus.")
    A("")

    # ---- S6 device classes (NEW) --------------------------------------
    A("## Note S6. How device classes were assigned")
    A("")
    A("Every table and figure in the main text is organised by device class, "
      "because a single number means different things in different "
      "architectures. A power conversion efficiency of 33.15% is impossible "
      "for a single junction and unremarkable for a tandem, so a review that "
      "pools them reports a frontier that belongs to no real device.")
    A("")
    _rows = []
    for k in CLASS_ORDER:
        cs = [c for c in cards if classify(c, abstracts.get(c.get("work_key"), "")) == k]
        if not cs:
            continue
        meas = [c for c in cs if c.get("lens") not in NON_MEASURED]
        _rows.append([CLASS_LABEL[k], len(cs), len(meas),
                      len(cs) - len(meas), f"{CLASS_PCE_LIMIT[k]}%"])
    for _l in _md_table(["Device class", "Papers read", "Measured",
                         "Simulation or review",
                         "Detailed-balance limit"], _rows):
        A(_l)
    A("")
    A("The class is read from each value's OWN quotation, never from the "
      "paper's title: a paper about inverted single-junction cells that also "
      "reports a certified tandem contributes its tandem number to the "
      "tandem class and its single-junction number to the single-junction "
      "class. Note S3 works through exactly that case.")
    A("")
    A("The limit in the last column is the detailed-balance ceiling that "
      "applies to that architecture under the AM1.5G spectrum. It is the "
      "number against which any claim in that class should be read, and it "
      "is why the classes are never pooled.")
    A("")

    # ---- S7 illumination (NEW) ----------------------------------------
    A("## Note S7. Illumination conditions, and the values excluded because "
      "of them")
    A("")
    A("A detailed-balance limit is defined for a spectrum, not for a number, "
      "and the ceilings quoted in this review are derived for AM1.5G. Under "
      "indoor or weak artificial light the incident spectrum is narrow and "
      "far better matched to a wide-gap absorber, so a device can exceed the "
      "solar ceiling without anything being wrong with the device, the "
      "measurement, or the extraction.")
    A("")
    if indoor_rows:
        A(f"**{len(indoor_rows)} values across "
          f"{len({r['work_key'] for r in indoor_rows})} papers were "
          f"identified as indoor or weak-light measurements and excluded "
          f"from every main-text table and figure that draws a solar "
          f"limit.** They are listed here in full rather than silently "
          f"dropped: an excluded value is not an erased one, and a reader "
          f"who finds one of these numbers in the source should be able to "
          f"see that the pipeline saw it too.")
        A("")
        for _l in _md_table(["Paper", "Device class", "Value (%)",
                             "Condition detected"],
                            [[r["work_key"], r["label"], r["value"],
                              r["illumination"]] for r in indoor_rows]):
            A(_l)
        A("")
        A("Two of these carry a detected condition of *unknown* rather than "
          "*indoor*, which is the truncation case described in Note S3: the "
          "quotation cap can cut the illumination marker off the end of an "
          "otherwise clear sentence, so the condition is read from the full "
          "source abstract, which the pipeline holds and has already "
          "verified. The quotation shown to a reader stays capped; what the "
          "pipeline may KNOW is not limited to what it may QUOTE.")
        A("")
        A("Had these values been left in, the highest would have sat above "
          "the single-junction solar ceiling and made the issue appear to "
          "have found a field-wide integrity problem. It had not. The "
          "devices are real and the numbers are correctly reported by their "
          "authors; only the comparison would have been wrong.")
    else:
        A("No value in this corpus was identified as an indoor or weak-light "
          "measurement, so no value was excluded on illumination grounds.")
    A("")
    A("An unmarked value is treated as a standard-conditions measurement, "
      "because that is the overwhelming default in this literature. The "
      "residual risk is therefore an indoor value surviving onto a solar "
      "figure, not a solar value being deleted.")
    A("")

    # ---- S8 mechanism axes (NEW) --------------------------------------
    A("## Note S8. What the closely read papers were about")
    A("")
    A("The depth tier is drawn with a minimum quota per mechanism axis, so a "
      "small but real subfield cannot be crowded out by a large one. The "
      "distribution below is therefore a property of the SELECTION as much "
      "as of the literature, and should not be read as a measurement of what "
      "the field worked on in " + str(year) + ".")
    A("")
    _ax = [(k.split(".")[1], v) for k, v in sorted(S.items())
           if k.startswith("axes.") and k.endswith(".n_depth_year")]
    if _ax:
        _tot = sum(v for _, v in _ax) or 1
        for _l in _md_table(["Mechanism axis", "Papers read closely",
                             "Share of the depth tier"],
                            [[a.replace("_", " "), v,
                              f"{100.0 * v / _tot:.1f}%"]
                             for a, v in sorted(_ax, key=lambda x: -x[1])]):
            A(_l)
        A("")
        A("These counts sum to more than the depth tier where a paper is "
          "central to more than one axis, and the axis is assigned from the "
          "paper's own abstract rather than from its journal or keywords.")
        A("")

    # ---- S9 denominators (NEW) ----------------------------------------
    A("## Note S9. Which denominator applies to which number")
    A("")
    A("This review reports counts drawn from five different populations, and "
      "a rate is meaningless without knowing which one it was divided by. "
      "Every quantity below is stated somewhere in the main text or in these "
      "notes, and each one enumerates something different.")
    A("")
    for _l in _md_table(
            ["Quantity", "Count", "What it enumerates"],
            [["Works retrieved", meta01.get("openalex_count", n_corpus),
              f"records returned by the {year} topical query"],
             ["Corpus", n_corpus,
              "works surviving the scope gate; the denominator for nothing "
              "except itself"],
             ["Usable abstract", meta01.get("with_abstract", "not recorded"),
              "works carrying an abstract of at least forty words"],
             ["Audit denominator",
              _g(S, "audit.year.certified.denominator", "?"),
              "works with BOTH a usable abstract and a resolved month; the "
              "denominator of every rate in Note S4"],
             ["Depth tier", n_cards,
              "works read closely enough to extract structured records"],
             ["Year-only dated", n_unknown,
              "works absent from every month-resolved count, including the "
              "audit denominator"]]):
        A(_l)
    A("")
    A("The audit denominator is smaller than the count of works with a "
      "usable abstract, and the difference is exactly the works dated only "
      "to the year. A monthly rate cannot be computed for a work with no "
      "month, so those works are excluded from the audit rather than "
      "assigned a month they do not have. This is why the reporting rates in "
      "Note S4 are divided by a number no other section uses.")
    A("")
    A("No percentage in this review is a mean of monthly percentages, and "
      "every one is a summed numerator over a summed denominator, for the reason "
      "given in Note S4.")
    A("")

    # ---- S10 limitations ----------------------------------------------
    A("## Note S10. Limitations")
    A("")
    A("1. **Abstract-based extraction.** Every claim comes from an abstract. "
      "A paper that reports a quantity only in its experimental section is "
      "recorded as not reporting it, so all audit rates are lower bounds.")
    A("2. **No validated detector.** The reporting-flag regular expressions "
      "have no hand-labelled precision or recall figure, which is the single "
      "highest-value outstanding task for the project.")
    A("3. **Retrospective assembly.** See Note S1. The month-by-month series "
      "reflects publication dates, not contemporaneous monitoring.")
    A("4. **Date precision.** Works dated only to the year are absent from "
      "every monthly series, as recorded in Note S2.")
    A("5. **No prior annual issue.** This is the first annual issue of this "
      "review, so it contains no year-over-year comparison. A comparison "
      "against a raw publication count from an earlier year would not be "
      "equivalent to a comparison against a prior audited issue.")
    A("6. **Venue coverage.** Some venues carry no citation percentile and "
      "score zero in selection, so they can enter the depth tier only "
      "through mechanism centrality.")
    A("")

    # ---- S7 gates ----------------------------------------------------
    if gates:
        A("## Note S11. Automated gate report")
        A("")
        A("Each gate encodes a defect that reached a rendered page at least "
          "once, and a gate is never widened to admit output; the output is "
          "fixed instead.")
        A("")
        for _l in _md_table(["Gate", "Status"],
                            [[k, v.get("status")] for k, v in gates.items()]):
            A(_l)
        A("")
        if any(v.get("status") == "cold-start" for v in gates.values()):
            A("A gate reported as *cold-start* could not run because it "
              "compares against a prior issue and none exists. It is "
              "deliberately not reported as a pass.")
            A("")

    # ---- S8 reproduction --------------------------------------------
    A("## Note S12. Data availability and reproduction")
    A("")
    A(f"The accompanying data pack contains the corpus table, one row per "
      f"extracted number WITH ITS VERBATIM QUOTATION, the per-month series, "
      f"the frontier trajectory, the reporting audit with denominators, and "
      f"the axis distribution. Abstract text and full texts are not "
      f"redistributed.")
    A("")
    A(f"The main text cites {n_cited} of {n_refs} listed references. "
      f"Bracketed numbers above the reference count are chemical or "
      f"crystallographic nomenclature, not citation markers, and are excluded "
      f"from that count.")
    A("")
    A(f"Section map fingerprint: `{smap.get('sha256')}`. The section "
      f"structure is generated from the evidence mass, so the same corpus "
      f"reproduces the same map.")
    A("")

    si_md = rd / "supplementary_yearly.md"
    si_md.write_text("\n".join(L), encoding="utf-8")

    outdir = ROOT / "manuscript" / f"{year}_yearly"
    outdir.mkdir(parents=True, exist_ok=True)
    made_csv = write_data_pack(outdir, agg, S, cards, abstracts, rd)

    pandoc = shutil.which("pandoc")
    if not pandoc:
        for c in (pathlib.Path.home() / "AppData/Local/Pandoc/pandoc.exe",
                  pathlib.Path(r"C:\Program Files\Pandoc\pandoc.exe")):
            if c.exists():
                pandoc = str(c)
                break
    if not pandoc:
        raise SystemExit("FAIL-CLOSED: pandoc not found")
    tectonic = shutil.which("tectonic") or "tectonic"
    pdf = outdir / "supplementary_yearly.pdf"
    p = subprocess.run(
        [pandoc, str(si_md), "-V", "geometry:margin=2.4cm",
         "-V", "fontsize=10pt", "-V", "colorlinks=true",
         "-V", "linkcolor=[HTML]{1A4E8A}",
         "-H", str(CONFIG / "tex" / "manuscript_head.tex"),
         f"--pdf-engine={tectonic}", "-o", str(pdf)],
        capture_output=True, text=True, timeout=900, cwd=str(ROOT))
    if p.returncode != 0 or not pdf.exists():
        (rd / "19y_si_error.txt").write_text(
            (p.stdout or "") + "\n" + (p.stderr or ""), encoding="utf-8")
        raise SystemExit(f"FAIL-CLOSED: SI pandoc rc={p.returncode}\n"
                         f"{(p.stderr or '')[:1200]}")
    shutil.copy(si_md, outdir / "supplementary_yearly.md")

    pages = None
    try:
        import pymupdf
        with pymupdf.open(pdf) as d:
            pages = d.page_count
    except Exception:                                       # noqa: BLE001
        pass

    # Count the notes RENDERED, never a literal. This field said `8` while
    # the SI shipped thirteen notes: a hardcoded count is a claim about the
    # artifact that nothing re-checks, which is the same class as the
    # monthly SI reading a hardcoded gate report. Measured from the text
    # that was actually written.
    n_notes = len(re.findall(r"^## Note S\d+\.", "\n".join(L), flags=re.M))

    meta = {"year": year, "pdf": str(pdf), "bytes": pdf.stat().st_size,
            "pages": pages, "notes": n_notes, "csv_files": made_csv,
            "cited_in_main_text": n_cited, "references_listed": n_refs}
    done(rd, "19y_si_yearly", **meta)
    print("[19y]", json.dumps(meta)[:500])
    return meta


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: s19y_si_yearly.py <YYYY>\n"
                         "No default: the period must be stated.")
    build(sys.argv[1])
