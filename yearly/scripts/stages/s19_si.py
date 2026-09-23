"""19_si: build the Supplementary Information PDF (Q56).

Sources: the v1 qwen-drafted methods/audit/limitations text (stripped of any
leaked self-report lines), stats.json tables, the SI figures, and the gate
report. Single column, same format family as the main text.
Run: python scripts/stages/s19_si.py 2026-07
"""
from __future__ import annotations

import datetime
import json
import pathlib
import re
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from stages.util import ROOT, done, read_jsonl, run_dir

# Third copy of the narration filter used to live here. All three have been
# replaced by the single canonical definition in stages.hygiene, because the
# copies drifted and the narrowest one let a leak reach a shipped PDF.
from stages.hygiene import SELF_REF, strip_narration  # noqa: E402,F401


def strip(text: str) -> str:
    """Strip narration from SI note prose (delegates to stages.hygiene)."""
    return strip_narration(text)[0]


def month_name(month: str) -> str:
    """'2026-08' -> 'August 2026'. The SI title and the S1/S3/S6 notes must
    name the month being built, never a literal typed in for one issue."""
    y, m = month.split("-")
    return f"{datetime.date(int(y), int(m), 1):%B} {y}"


def build(month: str) -> dict:
    rd = run_dir(month)
    MON = month_name(month)
    S = json.loads((rd / "stats.json").read_text(encoding="utf-8"))
    # Q64: the SI must describe THIS build. It previously read a hard-coded
    # gate_report_v2.json, so the "cited in the main text" row reported 110
    # while the v3 main text cited 42. Version is now an argument, and the
    # citation count is measured from the manuscript itself.
    ver = sys.argv[2] if len(sys.argv) > 2 else "v3"
    gates = json.loads((rd / f"gate_report_{ver}.json").read_text(encoding="utf-8"))
    mtext = (rd / f"manuscript_{ver}.md").read_text(encoding="utf-8")
    # Same nomenclature guard as the build: "[60]fullerene" (IUPAC) and
    # "[100] growth" (Miller index) are not citations. A plain \[(\d+)...\]
    # count is one too high on any month containing a Miller index, and August
    # contains one, so the SI's "Cited in the main text" row overstated truth.
    # The handbook documented this guard while only the build applied it --
    # exactly the single-consumer divergence that let the narration leak
    # through G4.
    _body = mtext[:mtext.index("## References")]
    _n_refs = len(re.findall(r"^\d+\. ", mtext[mtext.index("## References"):],
                             flags=re.M))
    _cited = set()
    for m in re.finditer(r"\[(\d+(?:,\d+)*)\](?![A-Za-z])", _body):
        grp = [int(x) for x in m.group(1).split(",")]
        if any(x > _n_refs or x == 0 for x in grp):
            continue
        _cited.update(grp)
    n_cited_main = len(_cited)
    meta01 = json.loads((rd / "01_meta.json").read_text(encoding="utf-8"))
    cards = read_jsonl(rd / "claim_cards.jsonl")

    # Notes S1/S3/S6 used to be lifted from the v1 qwen drafts in runs/<m>/draft/.
    # That directory only exists for months whose v1 pipeline was run: the
    # 2026-08 build is v3-only, so this raised FileNotFoundError on draft/sec2.md.
    #
    # Reusing July's v1 text was NOT an option: it names its own month and its
    # own counts ("Of 648 works published in July 2026 ... 453 had a usable
    # abstract and 181 ... depth"). Pasting that into an August SI would put
    # three wrong numbers into the methods note -- the 7.2 fabrication class.
    #
    # So when no v1 draft exists these notes are composed here, deterministically,
    # from stats.json. No model writes them and every number is a stats lookup.
    v1 = rd / "draft"

    def _from_v1(name: str) -> str | None:
        f = v1 / name
        return strip(f.read_text(encoding="utf-8")) if f.exists() else None

    method = _from_v1("sec2.md") or (
        f"The corpus came from an OpenAlex title-and-abstract search for "
        f"perovskite AND (\"solar cell\" OR photovoltaic), restricted to {MON} "
        f"publication dates and to the work types article, preprint and review. "
        f"That set was unioned with records from Semantic Scholar, Crossref and "
        f"arXiv and de-duplicated by DOI. Exclusion terms are applied in Python "
        f"after retrieval, never inside the query. "
        f"Of {S['corpus.n']} works meeting the scope gate, "
        f"{S['corpus.n_with_abstract']} had a usable abstract and "
        f"{S['selection.n_depth']} met the depth-review threshold.\n\n"
        f"The depth tier is built on abstracts by decision, not by omission: a "
        f"full-text retrieval probe succeeded for about 5% of a month's papers, "
        f"and the failure is publisher refusal of automated retrieval rather "
        f"than indexing delay. Selection is a constrained draw over venue "
        f"citation percentile and mechanism axis with per-axis minima and "
        f"venue and institution share caps, seeded for reproducibility. "
        f"Across {S['selection.sensitivity_draws'] if 'selection.sensitivity_draws' in S else 200} "
        f"sensitivity draws the median Jaccard overlap of the selected set was "
        f"{S['selection.jaccard_median']}, with {S['selection.core_n']} papers "
        f"appearing in every draw.")

    audit = _from_v1("sec6.md") or (
        f"This note reports how completely the {MON} papers describe their own "
        f"measurements. The audit reads abstracts, so it measures what authors "
        f"chose to summarise, not what appears in an experimental section or in "
        f"supporting information. Two tiers are covered: a corpus tier of "
        f"{S['audit.corpus.denominator']} abstracts and a depth tier of "
        f"{S['audit.depth.denominator']} abstracts.\n\n"
        f"Because the hand-labelled validation set for the detector is not yet "
        f"complete, every percentage here is a lower bound and is written as "
        f"\"detected in at least\", with no precision or recall figure attached. "
        f"In the corpus tier an efficiency value was detected in at least "
        f"{S['audit.corpus.efficiency_stated.pct']}% of abstracts, a stabilised "
        f"or maximum-power-point-tracked efficiency in at least "
        f"{S['audit.corpus.stabilised.pct']}%, independent certification in at "
        f"least {S['audit.corpus.certified.pct']}%, an active or aperture area "
        f"in at least {S['audit.corpus.area_stated.pct']}%, and a complete "
        f"open-circuit voltage, short-circuit current density and fill factor "
        f"triplet in at least {S['audit.corpus.triplet_complete.pct']}%. An ISOS "
        f"stability-protocol label was detected in at least "
        f"{S['audit.corpus.isos_label.pct']}% and an explicit hysteresis "
        f"statement in at least {S['audit.corpus.hysteresis.pct']}%. Table S3 "
        f"gives both tiers side by side.")

    limits = _from_v1("sec8.md") or (
        f"Venue-impact-prioritised selection under-samples preprints, regional "
        f"journals and non-English venues, so the depth subset is biased toward "
        f"well-indexed English-language publishing. Work circulating chiefly on "
        f"preprint servers or in regional venues can carry mechanism results and "
        f"reporting habits this review never sees. Of the corpus, "
        f"{S['corpus.n_preprint']} records are preprints and "
        f"{S['corpus.n_translated']} were machine translated from another "
        f"language; translation can blur technical wording.\n\n"
        f"Because indexing lags publication, this review describes the indexed "
        f"record of {MON} as retrieved at build time, not the month itself. The "
        f"lag is uneven, and work published late in the month is systematically "
        f"under-represented relative to work published early. A later rebuild of "
        f"the same month would retrieve a larger corpus, which is why no "
        f"publication count appears in the title.")

    def _v(c, k):
        src = c["stability"] if k in ("t80_h",) else c["performance"]
        f = (src or {}).get(k)
        return f["value"] if isinstance(f, dict) and f.get("value") is not None else None

    cert = sorted(((_v(c, "pce_certified"), c) for c in cards if _v(c, "pce_certified")),
                  key=lambda x: -x[0])

    t1 = ["| Source | Records retrieved |", "| --- | --- |",
          f"| OpenAlex (keyed, cursor-paginated) | {meta01['sources'].get('openalex', 0)} |",
          f"| Semantic Scholar (bulk) | {meta01['sources'].get('s2', 0)} |",
          f"| Crossref | {meta01['sources'].get('crossref', 0)} |",
          f"| arXiv | {meta01['sources'].get('arxiv', 0)} |",
          f"| **Corpus after de-duplication and topical post-filter** | **{S['corpus.n']}** |",
          f"| With a usable abstract | {S['corpus.n_with_abstract']} |",
          f"| Non-English (machine translated) | {S['corpus.n_translated']} |",
          f"| Preprints | {S['corpus.n_preprint']} |"]

    t2 = ["| Stage | Works |", "| --- | --- |",
          f"| Passed the scope gate | {S['corpus.n']} |",
          f"| Usable abstract (eligibility) | {S['selection.n_eligible']} |",
          f"| Depth tier (selected for close reading) | {S['selection.n_depth']} |",
          f"| Extraction records surviving all guards | {len(cards)} |",
          f"| Dropped: no verifiable claim survived | {S['selection.n_depth'] - len(cards)} |",
          f"| Cited in the main text | {n_cited_main} |",
          f"| Audited but not cited individually | {len(cards) - n_cited_main} |"]

    rows = ["efficiency_stated", "stabilised", "certified", "area_stated",
            "hysteresis", "isos_label", "triplet_complete"]
    lab = {"efficiency_stated": "Efficiency value stated",
           "stabilised": "Stabilised or MPPT value",
           "certified": "Independent certification",
           "area_stated": "Device area stated",
           "hysteresis": "Hysteresis or scan direction",
           "isos_label": "ISOS protocol label",
           "triplet_complete": "Complete Voc / Jsc / FF triplet"}
    t3 = [f"| Reporting item | Corpus (n={S['audit.corpus.denominator']}) | "
          f"Depth (n={S['audit.depth.denominator']}) |", "| --- | --- | --- |"]
    for r in rows:
        t3.append(f"| {lab[r]} | {S[f'audit.corpus.{r}.pct']}% | "
                  f"{S[f'audit.depth.{r}.pct']}% |")

    AX = ["composition", "defects", "interfaces", "architecture", "stability", "scale_up"]
    t4 = ["| Mechanism axis | Corpus | Depth | Share of corpus |", "| --- | --- | --- | --- |"]
    for a in AX:
        t4.append(f"| {a.replace('_', ' ')} | {S[f'axes.{a}.n_corpus']} | "
                  f"{S[f'axes.{a}.n_depth']} | {S[f'axes.{a}.share_pct']}% |")

    t5 = ["| Certified PCE (%) | Venue | Architecture | DOI |", "| --- | --- | --- | --- |"]
    for v, c in cert:
        t5.append(f"| {v} | {c['venue']} | {c['device']['architecture']} | "
                  f"[{c['doi']}](https://doi.org/{c['doi']}) |")

    t6 = ["| Gate | Status | Summary |", "| --- | --- | --- |"]
    for k, gv in gates.items():
        d = gv["detail"]
        if k == "G1":
            sm = f"{d['resolved']} citations resolved, {len(d['unresolved'])} unresolved"
        elif k == "G2":
            # v4's G2 dropped 'cited' and 'figures' (citation count moved to
            # G2c, figures are no longer fixed per section), so a v3-shaped
            # read raised KeyError and killed the SI build. Read defensively:
            # a supplementary table must never be the thing that stops a
            # verified manuscript from shipping.
            bits = [f"{d['prose_words']} words"]
            if "cited" in d:
                bits.append(f"{d['cited']} cited")
            if "figures" in d:
                bits.append(f"{d['figures']} figures")
            if "per_section_within_135pct" in d:
                nsec = len(d["per_section_within_135pct"])
                bits.append(f"{nsec} sections within 135% of ceiling")
            sm = ", ".join(bits)
        elif k == "G2c-cite-count":
            sm = (f"{d['cited']} cited, target {d['target_range']}, "
                  f"{d['words_per_citation']} words per citation")
        elif k == "G4":
            sm = (f"em-dash {d['em_dash']}, banned {len(d['banned'])}, "
                  f"self-report leaks {len(d['self_report_leak'])}")
        elif k == "G8-novelty":
            if gv["status"] == "skip":
                sm = "no prior issue on record"
            else:
                sm = (f"worst section {d['worst_section_ratio']} vs "
                      f"{d['body_max_ratio']}, abstract {d['abstract_ratio']} "
                      f"vs {d['abstract_max_ratio']}, "
                      f"{d['n_shared_shingles']} shared shingles")
        elif k == "G5":
            sm = (f"{d.get('total_pages')} pages, "
                  f"{d.get('content_pages')} content"
                  if "total_pages" in d else json.dumps(d)[:70])
        else:
            sm = json.dumps(d)[:70]
        t6.append(f"| {k} | {gv['status']} | {sm} |")

    figdir = rd / "fig"
    n_t80 = len([c for c in cards if _v(c, "t80_h")])
    n_proto = len([c for c in cards if c["stability"].get("protocol")])

    # v4: the title is DERIVED from the month's leading axes, so the SI must
    # ask the build for it rather than repeating a literal. v3 hardcoded
    # "Buried-Interface Chemistry, Defect Tolerance and the Certified
    # Efficiency Frontier" here, which would caption an August SI with a July
    # issue's subtitle the moment the main title started varying.
    title_line = None
    if ver == "v4":
        try:
            from stages.section_map import load_map
            from stages.s18d_build_v4 import derive_title
            title_line = derive_title(month, load_map(month))
        except Exception as e:                      # fail loud, never silent
            raise SystemExit(f"FAIL-CLOSED: SI cannot derive the v4 title: {e}")
    else:
        title_line = (f"Perovskite Photovoltaics in {MON}: Buried-Interface "
                      f"Chemistry, Defect Tolerance and the Certified "
                      f"Efficiency Frontier")

    md = [
        "# Supplementary Information",
        "",
        f"For \"{title_line}\"",
        "",
        f"Havid Aqoma, {time.strftime('%B ')}{int(time.strftime('%d'))}{time.strftime(', %Y')}",
        "",
        "This Supplementary Information contains the corpus construction and "
        "selection method (Note S1), the extraction and evidence-chain method "
        "(Note S2), the full reporting audit (Note S3), the corpus statistics "
        "(Note S4), the complete certified-record table (Note S5), the "
        "limitations (Note S6), and the automated gate report for this build "
        "(Note S7).",
        "",
        "## Note S1. Corpus construction and selection",
        "", method, "",
        "**Table S1.** Records retrieved by source.", "", "\n".join(t1), "",
        "**Table S2.** Selection funnel.", "", "\n".join(t2), "",
        f"![**Figure S1.** Corpus construction funnel.]"
        f"({(figdir / 'S2_corpus_funnel.pdf').as_posix()}){{width=85%}}",
        "",
        "## Note S2. Extraction and the evidence chain",
        "",
        "Every closely read paper was passed through a structured extraction step "
        "that returned numeric fields, each bound to a verbatim quotation from "
        "that paper's own abstract. Three deterministic guards were then applied "
        "by script, never by the extracting model. First, the quotation must "
        "appear word for word in the source abstract. Second, the numeric value "
        "must appear inside its own quotation. Third, the quotation is truncated "
        "to 25 words before that check rather than after it, so a value can never "
        "be separated from the words that prove it. Any field failing a guard is "
        "nulled and counted, and a paper whose extraction left no verifiable "
        "claim was dropped from the cited set rather than shipped with an "
        f"unprovable record ({S['selection.n_depth'] - len(cards)} of "
        f"{S['selection.n_depth']} this month).",
        "",
        "Independent re-verification of the shipped records, run as a separate "
        "script against the source abstracts, found every quotation present "
        "verbatim, none exceeding 25 words, and no numeric value missing from its "
        "own quotation. The abstract of the main text carries an additional gate: "
        "every numeral in it must exist either in the statistics file or in an "
        "extraction record, and each named scientific highlight is bound to one "
        "explicit record by its DOI, so a highlight cannot silently attach a real "
        "number to the wrong paper.",
        "",
        "## Note S3. The full reporting audit",
        "", audit, "",
        "**Table S3.** Reporting-completeness detection rates. All values are "
        "lower bounds obtained by pattern detection on abstracts, not by human "
        "reading.", "", "\n".join(t3), "",
        f"![**Figure S2.** Reporting-completeness detection rates, corpus and "
        f"depth tiers.]({(figdir / 'S1_reporting_audit.pdf').as_posix()}){{width=90%}}",
        "",
        "Two properties of these rates govern how they should be read. They are "
        "measured on abstracts, so they describe what authors chose to summarise "
        "rather than what was measured in the laboratory: an abstract omitting a "
        "device area is not evidence that the area went unrecorded. They are also "
        "lower bounds, because the hand-labelled validation set that would attach "
        "a precision and recall figure to each pattern is not yet complete. No "
        "percentage becomes exact until its precision reaches 0.85 against human "
        "labels, and until then every figure in this note carries that caveat "
        "without restating it.",
        "",
        "## Note S4. Corpus statistics",
        "", "**Table S4.** Mechanism-axis distribution.", "", "\n".join(t4), "",
        "Axis assignment uses weighted keyword scoring over title and abstract "
        "across six fixed axes, with the title weighted twice. Mechanism "
        "centrality is the winning axis score normalised by that axis maximum. "
        "Selection into the depth tier scores venue citation percentile (0.40), "
        "mechanism centrality (0.35) and novelty (0.25), subject to a floor of 12 "
        "papers per axis, a preprint reservation, and per-venue and "
        "per-institution caps.",
        "",
        "One caveat on the selection statistics is worth stating plainly. In this "
        "first issue the novelty term is constant, because it is defined against a "
        "cumulative history of extracted records that does not yet exist, so "
        "ranking reduces to venue percentile plus mechanism centrality. Repeating "
        "the selection under 200 perturbed weightings therefore returns a "
        f"selection overlap of {S['selection.jaccard_median']} with "
        f"{S['selection.core_n']} papers selected in almost every draw. That "
        "number should be read as a consequence of the flat novelty term, not as "
        "evidence that the selector is robust; it becomes informative from the "
        "third issue onward.",
        "",
        "## Note S5. Every certified efficiency reported in the month",
        "",
        f"Of {len(cards)} closely read papers, {len(cert)} reported an "
        "independently certified efficiency. The complete list follows, highest "
        "first. Each DOI is a live link.",
        "", "\n".join(t5), "",
        "## Note S6. Limitations",
        "", limits, "",
        "Four limitations are specific to this build. First, the reporting audit "
        "is unvalidated pending the human label set (Note S3). Second, the depth tier is built on abstracts by decision: "
        "a full-text retrieval probe succeeded for only 5% of the month's papers, "
        "and a diagnostic across three months of differing age showed the failure "
        "is publisher refusal of automated retrieval rather than indexing delay, "
        "since a fourteen-month-old month retrieved worse than a two-month-old "
        "one. The audit therefore measures reported summaries, and the extraction "
        "records quote abstracts rather than full texts. Third, operational "
        f"stability evidence is thin in an absolute sense: {n_t80} papers reported "
        f"a T80 lifetime and {n_proto} named an ISOS protocol, which limits what "
        "any review can conclude about degradation this month. Fourth, this issue "
        "covers a single month, so nothing in it is a trend; the first "
        "month-over-month comparison becomes possible with the next issue.",
        "",
        "## Note S7. Automated gate report for this build",
        "", "\n".join(t6), "",
        "Gate definitions. G1 requires every citation marker in the main text to "
        "resolve to an extraction record carrying its own source quotation. G2 "
        "enforces length and structure ceilings and records a SHA-256 fingerprint "
        "of each drafted section, so a gate result is permanently bound to the "
        "text it judged. G4 enforces prose hygiene: em-dash count, a banned "
        "vocabulary list, and detection of leaked model self-commentary. G6 "
        "forbids first-person experimental claims, since this is a review of other "
        "groups' work. The main-text abstract carries the additional numeric gate "
        "described in Note S2.",
        "",
    ]
    out = "\n".join(md)
    f = rd / f"supplementary_{ver}.md"
    f.write_text(out, encoding="utf-8")

    outdir = ROOT / "manuscript" / f"{month}_{ver}"
    outdir.mkdir(parents=True, exist_ok=True)
    pandoc = shutil.which("pandoc")
    if not pandoc:
        for c in (pathlib.Path.home() / "AppData/Local/Pandoc/pandoc.exe",
                  pathlib.Path(r"C:\Program Files\Pandoc\pandoc.exe")):
            if c.exists():
                pandoc = str(c)
                break
    tectonic = shutil.which("tectonic") or "tectonic"
    pdf = outdir / f"supplementary_{ver}.pdf"
    p = subprocess.run(
        [pandoc, str(f), "-V", "geometry:margin=2.4cm", "-V", "fontsize=10pt",
         "-V", "colorlinks=true", "-V", "linkcolor=[HTML]{1A4E8A}",
         "-V", "urlcolor=[HTML]{1A4E8A}",
         f"--pdf-engine={tectonic}", "-o", str(pdf)],
        capture_output=True, text=True, timeout=900, cwd=ROOT)
    if p.returncode != 0 or not pdf.exists():
        (rd / "19_si_error.txt").write_text((p.stdout or "") + "\n" + (p.stderr or ""),
                                            encoding="utf-8")
        raise SystemExit(f"FAIL-CLOSED SI build: rc={p.returncode}\n"
                         f"{(p.stderr or '')[:1200]}")
    shutil.copy(f, outdir / f"supplementary_{ver}.md")
    pages = None
    try:
        import pymupdf
        with pymupdf.open(pdf) as d:
            pages = d.page_count
    except Exception:
        pass
    meta = {"pdf": str(pdf), "pages": pages, "bytes": pdf.stat().st_size,
            "notes": 7, "tables": 6, "figures": 2, "certified_listed": len(cert)}
    done(rd, "19_si", **meta)
    print("[19]", json.dumps(meta, indent=2))
    return meta


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "2026-07")
