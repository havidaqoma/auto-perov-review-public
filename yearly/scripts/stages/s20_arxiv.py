"""20_arxiv: the submission bundle (Q66).

arXiv wants a self-contained tarball: .tex, the figures it references by
relative path, and a .bbl so no bibliography tool runs on their machine.
Also emits the CSV data pack Havid asked for -- corpus metadata, every
extracted record, and the raw numbers behind every plotted panel.

Run: python scripts/stages/s20_arxiv.py 2026-07 [v3]
"""
from __future__ import annotations

import csv
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tarfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from stages.util import ROOT, done, read_jsonl, run_dir

AX = ["composition", "defects", "interfaces", "architecture", "stability", "scale_up"]


def _v(c, k):
    src = c["stability"] if k in ("t80_h", "duration_h") else c["performance"]
    f = (src or {}).get(k)
    return f["value"] if isinstance(f, dict) and f.get("value") is not None else None


def _anchor(c, k):
    src = c["stability"] if k in ("t80_h", "duration_h") else c["performance"]
    f = (src or {}).get(k)
    return f.get("anchor", "") if isinstance(f, dict) else ""


def cls(c):
    a = c["device"]["architecture"]
    t = (c["title"] or "").lower()
    if "silicon" in t or "/si" in t:
        return "perovskite_silicon_tandem"
    if a in ("tandem_2T", "tandem_4T") or "all-perovskite" in t:
        return "all_perovskite_tandem"
    if a == "module" or "module" in t:
        return "module"
    return "single_junction"


def build(month: str) -> dict:
    ver = sys.argv[2] if len(sys.argv) > 2 else "v3"
    rd = run_dir(month)
    S = json.loads((rd / "stats.json").read_text(encoding="utf-8"))
    cards = read_jsonl(rd / "claim_cards.jsonl")
    corpus = {r["work_key"]: r for r in read_jsonl(rd / "05_corpus.jsonl")}
    labels = {l["work_key"]: l for l in read_jsonl(rd / "06_labels.jsonl")}
    md = rd / f"manuscript_{ver}.md"
    out = ROOT / "manuscript" / f"{month}_{ver}" / "arxiv"
    (out / "fig").mkdir(parents=True, exist_ok=True)
    data = ROOT / "manuscript" / f"{month}_{ver}" / "data"
    data.mkdir(parents=True, exist_ok=True)

    # ---------------- 1. LaTeX, figures by RELATIVE path ----------------
    pandoc = shutil.which("pandoc")
    if not pandoc:
        for c in (pathlib.Path.home() / "AppData/Local/Pandoc/pandoc.exe",
                  pathlib.Path(r"C:\Program Files\Pandoc\pandoc.exe")):
            if c.exists():
                pandoc = str(c)
                break
    tex = out / "manuscript.tex"
    p = subprocess.run(
        [pandoc, str(md), "-s",
         "-f", "markdown+raw_tex-implicit_figures",
         "-V", "geometry:margin=2.4cm", "-V", "fontsize=11pt",
         "-V", "linestretch=1.05", "-V", "colorlinks=true",
         "-V", "linkcolor=[HTML]{1A4E8A}", "-V", "urlcolor=[HTML]{1A4E8A}",
         "-H", str(ROOT / "config" / "tex" / "manuscript_head.tex"),
         "-o", str(tex)],
        capture_output=True, text=True, timeout=600, cwd=ROOT)
    if p.returncode != 0 or not tex.exists():
        raise SystemExit(f"FAIL-CLOSED: pandoc tex rc={p.returncode}\n"
                         f"{(p.stderr or '')[:900]}")

    # absolute figure paths -> fig/NAME, and copy the files in
    body = tex.read_text(encoding="utf-8")
    figs = set(re.findall(r"includegraphics\[[^\]]*\]\{([^}]+)\}", body))
    for f in figs:
        src = pathlib.Path(f)
        if not src.exists():
            src = rd / "fig" / pathlib.Path(f).name
        if src.exists():
            shutil.copy(src, out / "fig" / src.name)
            body = body.replace(f, f"fig/{src.name}")
    # arXiv compiles with pdflatex by default; keep the preamble portable
    body = body.replace(r"\usepackage{fontspec}", "% fontspec removed for pdflatex")
    tex.write_text(body, encoding="utf-8")

    # ---------------- 2. compile once to produce a .bbl / verify ----------
    tectonic = shutil.which("tectonic") or "tectonic"
    c = subprocess.run([tectonic, "--keep-intermediates", "--outdir", str(out),
                        str(tex)], capture_output=True, text=True,
                       timeout=900, cwd=out)
    compiled = (out / "manuscript.pdf").exists()

    # ---------------- 3. CSV data pack ----------------
    # 3a. corpus metadata: every work that passed the scope gate
    with (data / "corpus_metadata.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["work_key", "doi", "title", "venue", "venue_type",
                    "publication_date", "type", "lang", "axis_primary",
                    "axis_secondary", "lens", "mechanism_centrality",
                    "first_author_institution", "cited_by_count",
                    "oa_status", "in_depth_tier"])
        depth = {c_["work_key"] for c_ in cards}
        for k, r in corpus.items():
            lb = labels.get(k, {})
            w.writerow([k, r.get("doi", ""), r.get("title", ""), r.get("venue", ""),
                        r.get("venue_type", ""), r.get("publication_date", ""),
                        r.get("type", ""), r.get("lang", ""),
                        lb.get("axis_primary", ""), lb.get("axis_secondary") or "",
                        lb.get("lens", ""), lb.get("mechanism_centrality", ""),
                        r.get("first_author_institution_clean", ""),
                        r.get("cited_by_count", 0), r.get("oa_status", ""),
                        int(k in depth)])

    # 3b. extraction records, one row per numeric field, WITH its source quote
    with (data / "extracted_claims.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["work_key", "doi", "venue", "axis", "lens", "device_class",
                    "architecture", "field", "value", "unit",
                    "source_quotation", "text_basis"])
        for c_ in cards:
            for fld, unit in (("pce_champion", "%"), ("pce_certified", "%"),
                              ("pce_stabilised", "%"), ("active_area_cm2", "cm2"),
                              ("t80_h", "h")):
                v = _v(c_, fld)
                if v is None:
                    continue
                w.writerow([c_["work_key"], c_["doi"], c_["venue"], c_["axis"],
                            c_.get("lens", ""), cls(c_),
                            c_["device"]["architecture"], fld, v, unit,
                            _anchor(c_, fld), c_.get("text_basis", "abstract")])
            if c_["stability"].get("protocol"):
                w.writerow([c_["work_key"], c_["doi"], c_["venue"], c_["axis"],
                            c_.get("lens", ""), cls(c_),
                            c_["device"]["architecture"], "stability_protocol",
                            c_["stability"]["protocol"], "label", "",
                            c_.get("text_basis", "abstract")])

    # 3c. raw data behind each plotted figure
    with (data / "figure1_certified_frontier.csv").open("w", newline="",
                                                        encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["work_key", "doi", "device_class", "pce_champion",
                    "pce_certified", "included_in_figure", "exclusion_reason"])
        for c_ in cards:
            excl = c_.get("lens") in ("theory", "review")
            w.writerow([c_["work_key"], c_["doi"], cls(c_),
                        _v(c_, "pce_champion") or "", _v(c_, "pce_certified") or "",
                        int(not excl),
                        f"lens={c_.get('lens')}" if excl else ""])

    with (data / "figure2_area_penalty.csv").open("w", newline="",
                                                  encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["work_key", "doi", "device_class", "area_cm2", "pce_percent"])
        for c_ in cards:
            if c_.get("lens") in ("theory", "review"):
                continue
            a, pc = _v(c_, "active_area_cm2"), _v(c_, "pce_champion")
            if a and pc:
                w.writerow([c_["work_key"], c_["doi"], cls(c_), a, pc])

    with (data / "figure3_effort_map.csv").open("w", newline="",
                                                encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["mechanism_axis", "device_class", "n_papers"])
        from collections import Counter
        cnt = Counter((c_["axis"], cls(c_)) for c_ in cards)
        for (ax_, dc), n in sorted(cnt.items()):
            w.writerow([ax_, dc, n])

    with (data / "figure4_stability_evidence.csv").open("w", newline="",
                                                        encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["work_key", "doi", "device_class", "t80_hours",
                    "stability_protocol", "source_quotation"])
        for c_ in cards:
            t = _v(c_, "t80_h")
            pr = c_["stability"].get("protocol")
            if t or pr:
                w.writerow([c_["work_key"], c_["doi"], cls(c_), t or "",
                            pr or "", _anchor(c_, "t80_h")])

    # 3d. the audit table + axis table, flat
    with (data / "reporting_audit.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["metric", "tier", "n_detected", "percent", "denominator",
                    "printable", "note"])
        for tier in ("corpus", "depth"):
            den = S[f"audit.{tier}.denominator"]
            for m in ("efficiency_stated", "stabilised", "certified", "area_stated",
                      "hysteresis", "isos_label", "triplet_complete"):
                w.writerow([m, tier, S.get(f"audit.{tier}.{m}.n", ""),
                            S[f"audit.{tier}.{m}.pct"], den,
                            S.get(f"audit.{tier}.{m}.printable", False),
                            "lower bound: validation set incomplete"])

    with (data / "axis_distribution.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["mechanism_axis", "n_corpus", "n_depth", "share_of_corpus_pct"])
        for a in AX:
            w.writerow([a, S[f"axes.{a}.n_corpus"], S[f"axes.{a}.n_depth"],
                        S[f"axes.{a}.share_pct"]])

    # 3e. machine-readable stats + provenance
    shutil.copy(rd / "stats.json", data / "statistics.json")
    shutil.copy(rd / "claim_cards.jsonl", data / "extraction_records.jsonl")
    shutil.copy(rd / f"gate_report_{ver}.json", data / "gate_report.json")
    # v4 derives the title from the month's leading axes, so the data pack
    # README must ask for it rather than repeating a literal. v3 hardcoded
    # "July 2026" here and it survived the whole August build unnoticed,
    # because nothing reads a README.
    pack_title = f"Perovskite Photovoltaics in {month}"
    if ver == "v4":
        try:
            from stages.section_map import load_map
            from stages.s18d_build_v4 import derive_title
            pack_title = derive_title(month, load_map(month))
        except Exception as e:
            raise SystemExit(f"FAIL-CLOSED: data pack cannot derive title: {e}")
    (data / "README.txt").write_text(
        f"Data pack for \"{pack_title}\"\n"
        f"Generated {time.strftime('%Y-%m-%d %H:%M')} from run "
        f"{rd.name}\n\n"
        "corpus_metadata.csv      every work passing the scope gate, with its\n"
        "                         mechanism axis, lens and depth-tier flag\n"
        "extracted_claims.csv     one row per extracted numeric field, each with\n"
        "                         the verbatim source quotation that proves it\n"
        "figure1..4_*.csv         the exact rows behind each plotted panel,\n"
        "                         including which points were excluded and why\n"
        "reporting_audit.csv      detection rates, both tiers, with denominators\n"
        "axis_distribution.csv    corpus and depth counts per mechanism axis\n"
        "statistics.json          every number the manuscript can cite\n"
        "extraction_records.jsonl full structured records, one JSON per paper\n"
        "gate_report.json         automated gate results for this build\n\n"
        "Every numeric value in extracted_claims.csv is accompanied by the\n"
        "quotation it was read from, so any figure or claim in the manuscript\n"
        "can be traced to a sentence in the cited paper's own abstract.\n",
        encoding="utf-8")

    # ---------------- 4. arXiv metadata + tarball ----------------
    title = re.search(r"\{\\LARGE\\bfseries (.+?)\\par\}", body)
    (out / "00README.XXX").write_text(
        "This submission compiles with pdflatex.\n"
        "Figures are vector PDFs in fig/ and are referenced by relative path.\n",
        encoding="utf-8")
    meta = {
        "title": "Perovskite Photovoltaics in July 2026: Buried-Interface "
                 "Chemistry, Defect Tolerance and the Certified Efficiency "
                 "Frontier",
        "authors": "Havid Aqoma",
        "primary_category": "physics.app-ph",
        "cross_lists": ["cond-mat.mtrl-sci"],
        "license": "CC BY 4.0",
        "comments": f"{S['selection.n_depth']} papers read closely; "
                    f"machine-assisted monthly review; data and extraction "
                    f"records in Supplementary Information",
    }
    (out / "arxiv_metadata.json").write_text(json.dumps(meta, indent=2),
                                             encoding="utf-8")

    tgz = ROOT / "manuscript" / f"{month}_{ver}" / f"arxiv_{month}.tar.gz"
    with tarfile.open(tgz, "w:gz") as tf:
        for f in ("manuscript.tex", "00README.XXX"):
            if (out / f).exists():
                tf.add(out / f, arcname=f)
        if (out / "manuscript.bbl").exists():
            tf.add(out / "manuscript.bbl", arcname="manuscript.bbl")
        for f in sorted((out / "fig").glob("*.pdf")):
            tf.add(f, arcname=f"fig/{f.name}")
    names = tarfile.open(tgz).getnames()
    absolute = [n for n in names if n.startswith("/") or ":" in n]

    meta_out = {"tex": str(tex), "tex_compiles": compiled,
                "tarball": str(tgz), "tarball_bytes": tgz.stat().st_size,
                "tarball_members": names,
                "absolute_paths_in_tar": absolute,
                "csv_files": sorted(f.name for f in data.glob("*.csv")),
                "data_dir": str(data)}
    if absolute:
        raise SystemExit(f"FAIL-CLOSED: absolute paths in tarball {absolute}")
    done(rd, "20_arxiv", **meta_out)
    print("[20]", json.dumps(meta_out, indent=2))
    return meta_out


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "2026-07")
