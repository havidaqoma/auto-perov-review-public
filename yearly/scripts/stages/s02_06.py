"""02_normalize: canonical records + language detect + institution cleanup (5.2).
05_dedupe:     work_key merge across sources, canonical month (5.5).
06_mechanism:  axis/lens keyword scoring + 4.4 post-filter precedence (5.6).
Run as: python scripts/stages/s02_06.py 2026-07
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from stages.util import (CONFIG, done, is_year, read_jsonl, run_dir,
                         write_jsonl)

PV = ("solar cell", "solar cells", "photovoltaic", "photovoltaics", "psc", "pscs",
      "tandem", "power conversion efficiency", "pce")

INST_STRIP = (
    r"key laboratory of[^,;]*", r"state key laboratory[^,;]*",
    r"ministry of education", r"chinese academy of sciences",
    r"school of[^,;]*", r"department of[^,;]*", r"faculty of[^,;]*",
    r"college of[^,;]*", r"institute of[^,;]*",
)


def title_norm(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def clean_inst(name: str) -> str:
    if not name:
        return ""
    s = name.lower()
    for pat in INST_STRIP:
        s = re.sub(pat, "", s)
    s = re.sub(r"\s+", " ", s.replace(",", " ")).strip(" ,;-")
    return " ".join(w.capitalize() for w in s.split())[:80]


def detect_lang(text: str, declared: str | None) -> str:
    if declared:
        return declared
    try:
        from langdetect import detect
        return detect(text) if len(text) > 40 else "en"
    except Exception:
        return "en"


def normalize(month: str) -> dict:
    rd = run_dir(month)
    oa_rows = read_jsonl(rd / "01_openalex.jsonl")
    abstracts = {a["work_key"]: a["abstract"]
                 for a in read_jsonl(rd / "private" / "01_abstracts.jsonl")}
    s2 = {r["doi"]: r for r in read_jsonl(rd / "01_s2.jsonl") if r.get("doi")}
    cr = {r["doi"]: r for r in read_jsonl(rd / "01_crossref.jsonl") if r.get("doi")}
    ax = read_jsonl(rd / "01_arxiv.jsonl")

    recs, priv = [], []
    for r in oa_rows:
        doi = (r.get("doi") or "").replace("https://doi.org/", "").lower()
        wk = doi or f"{title_norm(r.get('title'))}|"
        auths = r.get("authorships") or []
        first_inst = ""
        first_sur = ""
        if auths:
            a0 = auths[0]
            first_sur = ((a0.get("author") or {}).get("display_name") or "").split()[-1:]
            first_sur = first_sur[0].lower() if first_sur else ""
            insts = a0.get("institutions") or []
            if insts:
                first_inst = insts[0].get("display_name") or ""
        if not doi:
            wk = f"{title_norm(r.get('title'))}|{first_sur}"
        loc = r.get("primary_location") or {}
        src = loc.get("source") or {}
        abstract = abstracts.get(wk, "") or abstracts.get(doi, "")
        # backfill abstract from S2 when OpenAlex has none (40% gap, P-04b)
        if not abstract and doi in s2:
            abstract = s2[doi].get("abstract") or ""
        title = r.get("title") or r.get("display_name") or ""
        lang = detect_lang(f"{title} {abstract}", r.get("language"))
        sources = ["openalex"]
        if doi in s2:
            sources.append("s2")
        if doi in cr:
            sources.append("crossref")

        recs.append({
            "work_key": wk, "doi": doi, "openalex_id": r.get("id"),
            "title": title, "title_norm": title_norm(title),
            "publication_date": r.get("publication_date") or "",
            "canonical_month": (r.get("publication_date") or "")[:7],
            # CARRIED THROUGH, not recomputed. s01_harvest_yearly stamps this
            # and normalize() rebuilds each record field-by-field, so anything
            # not named here is SILENTLY DROPPED. Losing it made every work
            # month-unknown, which would have emptied the trajectory series,
            # F5, F6, and the trajectory/synthesis spine roles -- while the
            # run still reported success. Recomputing it here instead would
            # be a second definition of the Jan-1 rule.
            "date_precision": r.get("date_precision") or "unknown",
            "type": r.get("type") or "article",
            "lang": lang, "translated": bool(lang != "en"),
            "source_primary": "openalex", "sources_seen": ",".join(sources),
            "venue": src.get("display_name") or "",
            "venue_source_id": src.get("id") or "",
            "venue_type": src.get("type") or "",
            "issn_l": src.get("issn_l") or "",
            "first_author_surname": first_sur,
            "first_author_institution_clean": clean_inst(first_inst),
            "cited_by_count": r.get("cited_by_count") or 0,
            "is_retracted": bool(r.get("is_retracted")),
            "oa_status": (r.get("open_access") or {}).get("oa_status") or "",
            "pdf_url": (r.get("best_oa_location") or {}).get("pdf_url") or "",
            "related_works": r.get("related_works") or [],
        })
        priv.append({"work_key": wk, "abstract": abstract})

    # arXiv-only preprints not matched by DOI
    seen_titles = {r["title_norm"] for r in recs}
    for a in ax:
        tn = title_norm(a.get("title"))
        if tn in seen_titles:
            continue
        wk = f"arxiv:{a.get('arxiv_id')}"
        recs.append({
            "work_key": wk, "doi": "", "openalex_id": "",
            "title": a.get("title") or "", "title_norm": tn,
            "publication_date": a.get("publication_date") or "",
            "canonical_month": (a.get("publication_date") or "")[:7],
            "type": "preprint", "lang": "en", "translated": False,
            "source_primary": "arxiv", "sources_seen": "arxiv",
            "venue": "arXiv", "venue_source_id": "", "venue_type": "repository",
            "issn_l": "", "first_author_surname": "",
            "first_author_institution_clean": "",
            "cited_by_count": 0, "is_retracted": False, "oa_status": "green",
            "pdf_url": "", "related_works": [],
        })
        priv.append({"work_key": wk, "abstract": a.get("abstract") or ""})

    write_jsonl(rd / "02_records.jsonl", recs)
    write_jsonl(rd / "private" / "02_abstracts.jsonl", priv)
    nlang = sum(1 for r in recs if r["lang"] != "en")
    meta = {"n": len(recs), "non_english": nlang,
            "with_abstract": sum(1 for p in priv if p["abstract"])}
    done(rd, "02_normalize", **meta)
    print("[02]", json.dumps(meta))
    return meta


def in_period(canonical_month: str, period: str) -> bool:
    """Does a record's canonical month belong to the requested period?

    THE BUG THIS FIXES WOULD HAVE EMPTIED THE WHOLE YEAR.

    The monthly original was:

        if r["canonical_month"] != month:   # '2025-06' != '2025'  -> DROP

    `canonical_month` is always 'YYYY-MM'. Compared against a bare year it
    never matches, so every one of ~7,900 works would have been dropped as
    "wrong month" and the stage would have written an EMPTY corpus while
    reporting a large, healthy-looking `dropped_wrong_month` count. Nothing
    downstream would crash; the year would simply be gone. That is the
    silent-zero class exactly.

    A prefix test is deliberately NOT used ('2025' is a prefix of '2025-06'
    but also of nothing else useful, and a prefix test on a month period
    would let '2025-06' match '2025-06' only by luck of equal length). The
    period shape is resolved explicitly instead.
    """
    if is_year(period):
        return (canonical_month or "")[:4] == period
    return canonical_month == period


def dedupe(period: str) -> dict:
    rd = run_dir(period)
    recs = read_jsonl(rd / "02_records.jsonl")
    by_key: dict[str, dict] = {}
    dropped_month = 0
    for r in recs:
        if not in_period(r["canonical_month"], period):
            dropped_month += 1
            continue
        k = r["work_key"]
        if k in by_key:
            old = by_key[k]
            # prefer journal article over preprint (in-batch rule carried from v2)
            if old["type"] == "preprint" and r["type"] != "preprint":
                r["sources_seen"] = ",".join(
                    sorted(set(old["sources_seen"].split(",") + r["sources_seen"].split(","))))
                by_key[k] = r
        else:
            by_key[k] = r
    corpus = list(by_key.values())
    write_jsonl(rd / "05_corpus.jsonl", corpus)
    meta = {"n_corpus": len(corpus), "dropped_wrong_month": dropped_month,
            "n_preprint": sum(1 for r in corpus if r["type"] == "preprint"),
            "n_review": sum(1 for r in corpus if r["type"] == "review"),
            "n_retracted": sum(1 for r in corpus if r["is_retracted"])}
    done(rd, "05_dedupe", **meta)
    print("[05]", json.dumps(meta))
    return meta


DEFAULT_LENS = {
    "theory": ["DFT", "first-principles", "simulation", "machine learning",
               "drift-diffusion", "SCAPS", "ab initio", "molecular dynamics"],
    "review": ["review", "perspective", "roadmap"],
    "scale_up": ["module", "roll-to-roll", "slot-die", "techno-economic"],
}

# High-signal terms get weight 3, mid 2, everything else 1. axes.yaml ships
# keywords as a flat LIST (no weights), so 5.6's weighted scoring is recovered
# here rather than by rewriting a config whose term choices are already good.
W3 = {"halide segregation", "phase stability", "ion migration", "passivation",
      "trap", "grain boundary", "SAM", "self-assembled monolayer",
      "buried interface", "tandem", "all-perovskite", "perovskite-silicon",
      "perovskite-on-silicon", "2-terminal", "4-terminal", "current matching",
      "recombination layer", "ISOS", "damp heat", "T80", "T90",
      "operational stability", "module", "mini-module", "slot-die",
      "roll-to-roll", "blade coating", "techno-economic", "lead-free",
      "tin perovskite", "maximum power point", "MPPT"}
W2 = {"cation", "A-site", "2D perovskite", "3D perovskite", "mixed-halide",
      "defect", "vacancy", "interstitial", "passivate", "antisite",
      "interface", "ETL", "electron transport", "HTL", "hole transport",
      "band alignment", "surface modification", "contact layer", "p-i-n",
      "n-i-p", "device architecture", "light soaking", "thermal stability",
      "encapsulation", "reverse bias", "moisture", "TEA", "LCA",
      "life cycle", "scalable", "area scaling", "Ruddlesden-Popper"}


def _weighted(kw_spec) -> dict:
    """Accept 5.6's {term: weight} dict OR axes.yaml's flat list."""
    if isinstance(kw_spec, dict):
        return {str(k): int(v) for k, v in kw_spec.items()}
    out = {}
    for term in (kw_spec or []):
        t = str(term)
        out[t] = 3 if t in W3 else (2 if t in W2 else 1)
    return out


def mechanism(month: str) -> dict:
    rd = run_dir(month)
    axes_cfg = yaml.safe_load((CONFIG / "axes.yaml").read_text(encoding="utf-8"))
    axes = {k: {"keywords": _weighted((v or {}).get("keywords"))}
            for k, v in axes_cfg["axes"].items()}
    lenses = axes_cfg.get("lens") or DEFAULT_LENS
    exc = yaml.safe_load((CONFIG / "exclude.yaml").read_text(encoding="utf-8"))
    EXCLUDE = [e.lower() for e in (exc.get("exclude") or [])]

    corpus = read_jsonl(rd / "05_corpus.jsonl")
    abstracts = {a["work_key"]: a["abstract"]
                 for a in read_jsonl(rd / "private" / "02_abstracts.jsonl")}

    labels, dropped = [], []
    for r in corpus:
        title = (r["title"] or "").lower()
        abst = (abstracts.get(r["work_key"], "") or "").lower()
        blob = f"{title} {abst}"

        # --- 4.4 post-filter precedence, in order, first match wins ---
        pv_title = any(p in title for p in PV)
        pv_abst = any(p in abst for p in PV)
        hit_exc_title = next((e for e in EXCLUDE if e in title), None)
        hit_exc_any = next((e for e in EXCLUDE if e in blob), None)
        if pv_title:
            keep, reason = True, "pv_in_title"
        elif hit_exc_title:
            keep, reason = False, f"postfilter:{hit_exc_title}"
        elif hit_exc_any and not pv_abst:
            keep, reason = False, f"postfilter_abstract:{hit_exc_any}"
        else:
            keep, reason = True, "kept"
        if not keep:
            dropped.append({"work_key": r["work_key"], "title": r["title"],
                            "reason": reason})
            continue

        # --- axis scoring: weight x (2 if in title else 1), word-bounded ---
        scores, matched = {}, {}
        for ax, spec in axes.items():
            tot, hits = 0, []
            for kw, w in (spec.get("keywords") or {}).items():
                k = kw.lower()
                pat = r"\b" + re.escape(k) + r"\b"
                if re.search(pat, title):
                    tot += w * 2
                    hits.append(kw)
                elif re.search(pat, abst):
                    tot += w
                    hits.append(kw)
            scores[ax] = tot
            matched[ax] = hits
        ranked = sorted(scores.items(), key=lambda kv: -kv[1])
        top, top_s = ranked[0]
        second, second_s = ranked[1] if len(ranked) > 1 else (None, 0)
        maxposs = sum(w * 2 for w in (axes[top].get("keywords") or {}).values()) or 1
        centrality = min(1.0, round(top_s / maxposs, 4)) if top_s else 0.0
        secondary = second if (second_s and top_s and second_s >= 0.8 * top_s) else None

        lens = "experimental"
        for ln, kws in lenses.items():
            if any(re.search(r"\b" + re.escape(k.lower()) + r"\b", blob) for k in kws):
                lens = ln
                break

        labels.append({
            "work_key": r["work_key"],
            "axis_primary": top if top_s else "composition",
            "axis_secondary": secondary,
            "axis_scores": scores,
            "mechanism_centrality": centrality,
            "lens": lens,
            "matched_keywords": matched.get(top, [])[:8],
            "offtopic_risk": 1 if hit_exc_any else 0,
            "selection_reason": reason,
            "has_abstract": bool(abstracts.get(r["work_key"])),
        })

    write_jsonl(rd / "06_labels.jsonl", labels)
    write_jsonl(rd / "06_postfilter_dropped.jsonl", dropped)
    # unvalidated mode (5.6): no labels_v1.csv yet -> printable forced false
    lv = pathlib.Path(__file__).resolve().parents[2] / "data/validation/labels_v1.csv"
    vm = {"status": "unvalidated"} if not lv.exists() else {"status": "validated"}
    (rd / "06_validation_metrics.json").write_text(json.dumps(vm, indent=2),
                                                  encoding="utf-8")
    from collections import Counter
    dist = Counter(l["axis_primary"] for l in labels)
    meta = {"n_kept": len(labels), "n_dropped": len(dropped),
            "axis_distribution": dict(dist),
            "validation": vm["status"],
            "n_with_abstract": sum(1 for l in labels if l["has_abstract"])}
    done(rd, "06_mechanism", **meta)
    print("[06]", json.dumps(meta, indent=2))
    return meta


if __name__ == "__main__":
    # No default period. A verifier that defaulted to a hardcoded August
    # manuscript once ran during the June cycle, verified the wrong file, and
    # reported PASS. A stage that defaults to a period is the same defect with
    # write access: run it in this repo without an argument and it would
    # harvest-shape a 2026-07 run dir that nothing here owns.
    if len(sys.argv) < 2:
        raise SystemExit(
            "usage: s02_06.py <period>   e.g. 2025  or  2025-06\n"
            "No default: the period must be stated, never inferred.")
    m = sys.argv[1]
    normalize(m)
    dedupe(m)
    mechanism(m)
