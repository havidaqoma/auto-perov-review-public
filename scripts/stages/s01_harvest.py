"""01_harvest: OpenAlex (keyed) + arXiv/Crossref/S2 (plain) -> run dir.
Abstracts go to private/ immediately, never into the public JSONL (5.1).
"""
from __future__ import annotations

import json
import pathlib
import sys
import time
import xml.etree.ElementTree as ET

import requests
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from common.net import SourceFailure, oa, redact
from stages.util import (CONFIG, done, month_bounds, reconstruct_abstract,
                         run_dir, write_jsonl)

UA = {"User-Agent": "auto-perov-review/0.1"}
SELECT = ("id,doi,title,display_name,publication_date,type,language,authorships,"
          "primary_location,best_oa_location,open_access,abstract_inverted_index,"
          "cited_by_count,related_works,is_retracted")
FILTER = 'title_and_abstract.search:perovskite AND ("solar cell" OR photovoltaic)'


def harvest(month: str) -> dict:
    g = yaml.safe_load((CONFIG / "gates.yaml").read_text(encoding="utf-8"))
    lo, hi = g["count_band"]
    a, b = month_bounds(month)
    rd = run_dir(month)
    meta: dict = {"month": month, "sources": {}}

    # --- count-band assertion FIRST (4.2): abort before paginating ---
    base = (f"https://api.openalex.org/works?filter={FILTER},"
            f"from_publication_date:{a},to_publication_date:{b},"
            f"type:article|preprint|review")
    j = oa(base + "&per-page=1", stage="01_harvest_count")
    n = j["meta"]["count"]
    meta["openalex_count"] = n
    if n == 0 or not (lo <= n <= hi):
        raise SystemExit(
            f"FAIL-CLOSED (4.2): count {n} outside [{lo},{hi}] for {month}")
    print(f"[01] count band OK: {n} in [{lo},{hi}]")

    # --- cursor pagination ---
    rows, abstracts = [], []
    cursor, pages = "*", 0
    while cursor and pages < g["max_pages"]:
        u = f"{base}&sort=publication_date&per-page=100&cursor={cursor}&select={SELECT}"
        page = oa(u, stage="01_harvest")
        got = page.get("results", [])
        for r in got:
            inv = r.pop("abstract_inverted_index", None)
            wk = (r.get("doi") or r.get("id") or "").replace("https://doi.org/", "")
            abstracts.append({"work_key": wk.lower(),
                              "abstract": reconstruct_abstract(inv)})
            rows.append(r)
        pages += 1
        cursor = (page.get("meta") or {}).get("next_cursor")
        print(f"[01] page {pages}: +{len(got)} (total {len(rows)})")
        if not got:
            break
    meta["sources"]["openalex"] = len(rows)
    meta["pages"] = pages
    write_jsonl(rd / "01_openalex.jsonl", rows)
    write_jsonl(rd / "private" / "01_abstracts.jsonl", abstracts)

    # --- arXiv (plain; no server-side month filter, per P-02) ---
    ax = []
    try:
        au = ("http://export.arxiv.org/api/query?search_query="
              "all:perovskite+AND+%28all:%22solar+cell%22+OR+all:photovoltaic%29"
              "&start=0&max_results=300&sortBy=submittedDate&sortOrder=descending")
        r = requests.get(au, headers=UA, timeout=60)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for e in ET.fromstring(r.text).findall("a:entry", ns):
            pub = (e.find("a:published", ns).text or "")
            if pub.startswith(month):
                ax.append({
                    "arxiv_id": (e.find("a:id", ns).text or "").rsplit("/", 1)[-1],
                    "title": " ".join((e.find("a:title", ns).text or "").split()),
                    "publication_date": pub[:10],
                    "type": "preprint",
                    "abstract": " ".join((e.find("a:summary", ns).text or "").split()),
                    "authors": [x.find("a:name", ns).text
                                for x in e.findall("a:author", ns)],
                })
    except Exception as e:
        print("[01] arXiv soft-fail:", redact(str(e)))
    meta["sources"]["arxiv"] = len(ax)
    write_jsonl(rd / "01_arxiv.jsonl", ax)

    # --- Crossref (plain) ---
    cr = []
    try:
        cu = ("https://api.crossref.org/works?query.bibliographic="
              "perovskite+solar+cell+photovoltaic"
              f"&filter=from-pub-date:{a},until-pub-date:{b},type:journal-article"
              "&rows=200&select=DOI,title,issued,container-title,author,type")
        r = requests.get(cu, headers=UA, timeout=60)
        for it in (r.json().get("message", {}) or {}).get("items", []):
            cr.append({
                "doi": (it.get("DOI") or "").lower(),
                "title": (it.get("title") or [""])[0],
                "venue": (it.get("container-title") or [""])[0],
                "type": "article",
            })
    except Exception as e:
        print("[01] Crossref soft-fail:", redact(str(e)))
    meta["sources"]["crossref"] = len(cr)
    write_jsonl(rd / "01_crossref.jsonl", cr)

    # --- Semantic Scholar (plain, anonymous per P-02) ---
    s2 = []
    try:
        su = ("https://api.semanticscholar.org/graph/v1/paper/search/bulk"
              "?query=perovskite+%28%22solar+cell%22+%7C+photovoltaic%29"
              f"&publicationDateOrYear={a}:{b}"
              "&fields=externalIds,title,abstract,publicationDate,venue,openAccessPdf")
        r = requests.get(su, headers=UA, timeout=90)
        if r.status_code == 200:
            for it in (r.json() or {}).get("data", []) or []:
                ex = it.get("externalIds") or {}
                s2.append({
                    "doi": (ex.get("DOI") or "").lower(),
                    "title": it.get("title") or "",
                    "publication_date": it.get("publicationDate") or "",
                    "venue": it.get("venue") or "",
                    "type": "article",
                    "abstract": it.get("abstract") or "",
                    "oa_pdf": (it.get("openAccessPdf") or {}).get("url"),
                })
        else:
            print(f"[01] S2 HTTP {r.status_code} (soft-fail, OpenAlex is primary)")
        time.sleep(1)
    except Exception as e:
        print("[01] S2 soft-fail:", redact(str(e)))
    meta["sources"]["s2"] = len(s2)
    write_jsonl(rd / "01_s2.jsonl", s2)

    (rd / "01_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    done(rd, "01_harvest", **meta)
    print("[01]", json.dumps(meta["sources"]))
    return meta


if __name__ == "__main__":
    harvest(sys.argv[1] if len(sys.argv) > 1 else "2026-07")
