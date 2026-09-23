"""02_normalize: oa_raw.jsonl -> canonical flat records (v2 §4.2). Deterministic, no LLM.

Emits runs/<hash>/records.jsonl (one canonical record per kept work; abstract kept for
the later 02b_translate / abstracts.jsonl stage). Summary is Q14=a extractive, script-only.
Provisional axis label (v3 §E.4) written here; 04_mechanism refines it before monthly commit.
"""
import json
import pathlib
import re
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[0]))

from common import doi as doimod
from common import titles as titlesmod

ROOT = pathlib.Path(__file__).resolve().parents[1]

_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_ARXIV_RE = re.compile(r"arxiv\.org/abs/([A-Za-z0-9._\-/]+)")
_SHORT_RE = re.compile(r"v\d+$")
_SUMMARY_CAP = 700
_SHORT_KEYWORDS = {"fa", "ma", "cs", "tea", "lca", "led", "isos", "mppt", "t80", "t90",
                   "2d", "3d", "p-i-n", "n-i-p", "4t", "2t", "e.g"}


def _short_re(kw: str) -> re.Pattern:
    # token match allowing immediately-following digits/dots: fa / FA0.83 / CsPb (cs at word start)
    return re.compile(r"\b" + re.escape(kw) + r"(?=[\d.]*[\s,;:)\]]|$)", re.I)


def lang_detect(lang: str | None) -> str:
    lang = (lang or "").strip().lower()
    if len(lang) == 2 and lang.isalpha():
        return lang
    return "en" if lang in ("eng", "en") else ("und" if not lang else lang)


def venue_type_label(wtype: str, source_type: str | None) -> str:
    if wtype == "preprint":
        return "preprint"
    if wtype == "review":
        return "review"
    if wtype == "letter":
        return "letter"
    if source_type == "journal":
        return "journal-article"
    return wtype or "article"


def arxiv_id(work: dict) -> str:
    cands = []
    pl = work.get("primary_location") or {}
    for loc in [pl] + (work.get("locations") or []):
        for url in (loc.get("pdf_url"), loc.get("landing_page_url")):
            m = _ARXIV_RE.search(url or "")
            if m:
                cands.append(_SHORT_RE.sub("", m.group(1)))
        src = (loc.get("source") or {}).get("display_name") or ""
        if "arxiv" in src.lower():
            for u in (loc.get("pdf_url"), loc.get("landing_page_url")):
                m = _ARXIV_RE.search(u or "")
                if m:
                    cands.append(_SHORT_RE.sub("", m.group(1)))
    return cands[0] if cands else ""


def sentences_split(txt: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", txt.strip()) if s.strip()]


def extractive_summary(abstract: str) -> str:
    if not abstract:
        return "(no abstract available)"
    sents = sentences_split(abstract)
    if len(sents) >= 3:
        text = " ".join([sents[0], sents[1], sents[-1]])
    else:
        text = " ".join(sents)
    if len(text) > _SUMMARY_CAP:
        text = text[:_SUMMARY_CAP - 1].rsplit(" ", 1)[0] + "…"
    return text


def axis_provisional(title: str, abstract: str, axes_cfg: dict) -> tuple[str, int]:
    """Best axis by keyword hits; deterministic. Provisional (04 refines)."""
    t = (f"{title or ''} {abstract or ''}").lower()
    best, best_score = "unassigned", 0
    for axis, cfg in axes_cfg.items():
        score = 0
        for kw in cfg["keywords"]:
            k = kw.lower()
            if len(k) >= 5:
                score += t.count(k)
            else:
                score += len(_short_re(k).findall(t))
        if score > best_score:
            best, best_score = axis, score
    return best, best_score


def assign_category(title: str, abstract: str, rules: list[dict]) -> str:
    t = (f"{title or ''} {abstract or ''}").lower()
    for rule in rules:
        for kw in rule["keywords"]:
            if kw in t:
                return rule["name"]
    return "Solar Cells"


def normalize(ym: str, run_hash: str | None = None) -> dict:
    if not run_hash:
        best = None
        for m in (ROOT / "runs").glob("*/manifest.json"):
            try:
                j = json.loads(m.read_text(encoding="utf-8"))
            except Exception:
                continue
            if j.get("month") == ym and (best is None or j["run_hash"] >= best):
                best = j["run_hash"]
        if not best:
            raise SystemExit(f"no manifest for month {ym}; run 01 first")
        run_hash = best
    cfg_root = ROOT / "config"
    axes_cfg = yaml.safe_load((cfg_root / "axes.yaml").read_text(encoding="utf-8"))["axes"]
    cat_rules = yaml.safe_load((cfg_root / "category_rules.yaml").read_text(encoding="utf-8"))["rules"]
    cc_map = yaml.safe_load((cfg_root / "countries.yaml").read_text(encoding="utf-8"))["cc_map"]

    raw = ROOT / "runs" / run_hash / "oa_raw.jsonl"
    recs = []
    stats = {"rows": 0, "no_full_date": 0, "no_doi": 0, "non_english": 0,
             "no_abstract": 0, "unassigned_axis": 0}
    first_seen = "2026-09-05"

    with open(raw, encoding="utf-8") as fh:
        for line in fh:
            w = json.loads(line)
            date = w.get("publication_date") or ""
            if not _DATE_RE.fullmatch(date):
                stats["no_full_date"] += 1
                continue
            title_raw = w.get("title") or ""
            title_clean = titlesmod.clean_title(title_raw)
            doi_norm = doimod.norm_doi(w.get("doi") or "")
            abst = ""
            inv = w.get("abstract_inverted_index")
            if inv:
                pos = {}
                for word, idxs in inv.items():
                    for i in idxs:
                        pos[i] = word
                abst = " ".join(pos[i] for i in sorted(pos))
            if not abst:
                stats["no_abstract"] += 1

            auths = w.get("authorships") or []
            a0 = auths[0] if auths else {}
            author_first = (a0.get("author") or {}).get("display_name") or ""
            inst0 = (a0.get("institutions") or [{}])[0]
            institution = inst0.get("display_name") or ""
            cc_raw = (inst0.get("country_code") or "").strip().lower()
            cc_name = cc_map.get(cc_raw, cc_raw.upper() if cc_raw else "")
            pos0 = (a0.get("author_position") or "first")
            if pos0 != "first" and author_first:
                author_first = f"{author_first} (First Author)"

            src = (w.get("primary_location") or {}).get("source") or {}
            journal = src.get("display_name") or ""
            source_type = src.get("type")
            oa_status = (w.get("open_access") or {}).get("oa_status") or "missing"
            lang = lang_detect(w.get("language"))
            axis, axis_score = axis_provisional(title_clean, abst, axes_cfg)
            if axis == "unassigned":
                stats["unassigned_axis"] += 1
            if lang not in ("en", "eng", ""):
                stats["non_english"] += 1

            rec = {
                "month": ym, "run_hash": run_hash,
                "oa_id": (w.get("id") or "").rsplit("/", 1)[-1],
                "doi_norm": doi_norm, "title_raw": title_raw, "title_clean": title_clean,
                "date_published": date, "type_work": w.get("type") or "",
                "lang": lang, "journal": journal, "venue_source_type": source_type,
                "venue_type_label": venue_type_label(w.get("type") or "", source_type),
                "author_first": author_first, "institution_first": institution,
                "country_iso2": cc_raw or "", "country_name": cc_name,
                "cited_by": w.get("cited_by_count") or 0,
                "oa_status": oa_status if oa_status in ("gold", "green", "hybrid", "closed") else
                             ("bronze" if oa_status == "bronze" else "missing"),
                "arxiv_id": arxiv_id(w),
                "category": assign_category(title_clean, abst, cat_rules),
                "axis_provisional": axis, "axis_score": axis_score,
                "abstract_orig": abst, "summary": extractive_summary(abst),
                "first_seen": first_seen,
            }
            recs.append(rec)
            stats["rows"] += 1

    out = ROOT / "runs" / run_hash / "records.jsonl"
    with open(out, "w", encoding="utf-8") as fh:
        for rec in recs:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    stats["run_hash"] = run_hash
    return stats


if __name__ == "__main__":
    ym = sys.argv[1] if len(sys.argv) > 1 else ""
    rh = sys.argv[2] if len(sys.argv) > 2 else None
    if len(ym) != 7 or (rh and len(rh) != 12):
        raise SystemExit("usage: python scripts/02_normalize.py YYYY-MM [run_hash]")
    print(json.dumps(normalize(ym, rh), indent=2))
