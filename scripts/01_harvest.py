"""01_harvest: canonical perovskite-PV gate, OpenAlex leg (v3 §C/§F).

Deterministic. Fail-closed (Q26=b): any SourceFailure aborts with stage+url.
Post-filters run in Python per §B2.1-2 (never in the query string).
Idempotent per run hash: an existing runs/<hash>/oa_raw.jsonl is never re-fetched.
"""
import hashlib
import json
import pathlib
import re
import sys
import time
import urllib.parse

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[0]))

from common.dates import in_band, month_window
from common.net import SourceFailure, oa

SCRIPT_VERSION = "0.1.2"
EXCLUDE_BARE_LED = re.compile(r"\bLED\b")          # case-sensitive: verb 'led' is safe
# 0.1.2: publisher issue-metadata captions are not papers. Wiley/Elsevier index
# "Back Cover In article number e70654, ..." caption records and title suffixes
# "(Journal 13/2026)". Excluded systematically (QA 2026-09-05 caught 10.1002/smtd.70688).
COVER_CAPTION = re.compile(
    r"^\s*(?:back\s*cover|front\s*cover|inside(?:\s*back)?\s*cover|"
    r"outside(?:\s*back)?\s*cover|cover\s+(?:image|picture|art|caption|profile|feature))"
    r".{0,160}?\barticle\s+number\b",
    re.I | re.S)
ISSUE_SUFFIX = re.compile(
    r"\(\s*[A-Za-z][A-Za-z0-9&.'\- ]{0,60}?\d{1,2}\s*/\s*\d{4}\s*\)\s*$")


def build_filter(ym: str) -> str:
    lo, hi = month_window(ym)
    return (f'title_and_abstract.search:perovskite AND ("solar cell" OR photovoltaic),'
            f"from_publication_date:{lo},to_publication_date:{hi},"
            f"type:article|preprint|review")


def exclusion_reason(title: str, journal: str, abstract: str, cfg: dict) -> str | None:
    """Return the first exclusion rule that fires, else None.

    NOTE: the bare-LED acronym check runs on the RAW (case-preserving) text --
    the rest lowercases, which would turn 'LED' into 'led' (never matches \bLED\b)
    or false-hit the verb 'led'. Fixed in 0.1.1."""
    if COVER_CAPTION.search(abstract or ""):
        return "cover-caption"
    if ISSUE_SUFFIX.search((title or "").strip()):
        return "issue-suffix-title"
    raw = f"{title or ''} {journal or ''} {abstract or ''}"
    if EXCLUDE_BARE_LED.search(raw):
        return "bare-LED"
    t = raw.lower()
    for kw in cfg["exclude"]:
        if kw in t:
            return f"exclude:{kw}"
    for kw in cfg["exclude_bound"]:
        if re.search(r"\b" + re.escape(kw) + r"\b", t):
            return f"exclude_bound:{kw}"
    for kw in cfg["pv_exclude_bound"]:
        if re.search(r"\b" + re.escape(kw) + r"\b", t):
            return f"pv_exclude_bound:{kw}"
    return None


def abstract_text(inv: dict | None) -> str:
    if not inv:
        return ""
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return " ".join(pos[i] for i in sorted(pos))


def harvest(ym: str) -> dict:
    cfg = yaml.safe_load(
        (pathlib.Path(__file__).resolve().parents[1] / "config/exclude.yaml").read_text(encoding="utf-8"))
    flt = build_filter(ym)
    run_hash = hashlib.sha256((flt + "|" + SCRIPT_VERSION).encode()).hexdigest()[:12]
    outdir = pathlib.Path(__file__).resolve().parents[1] / "runs" / run_hash
    outdir.mkdir(parents=True, exist_ok=True)
    raw = outdir / "oa_raw.jsonl"

    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(
        {"filter": flt, "per-page": "1"})
    meta_count = oa(url)["meta"]["count"]
    if not in_band(meta_count):
        raise SystemExit(f"FAIL-CLOSED: canonical count {meta_count} outside band - aborting")
    print(f"canonical count {meta_count} (in-band)")

    if raw.exists():
        n = sum(1 for _ in open(raw, encoding="utf-8"))
        print(f"harvest already exists for {run_hash}: {n} records - skipping fetch")
        return {"run_hash": run_hash, "meta_count": meta_count, "records": n}

    kept = 0
    drop_reasons = {}
    cursor = "*"
    page = 0
    with open(raw, "w", encoding="utf-8") as fh:
        while cursor:
            page += 1
            url = "https://api.openalex.org/works?" + urllib.parse.urlencode({
                "filter": flt, "per-page": "100", "cursor": cursor,
                "select": ("id,doi,title,publication_date,type,language,"
                           "abstract_inverted_index,authorships,cited_by_count,"
                           "primary_location,locations,ids,open_access"),
            })
            try:
                j = oa(url)
            except SourceFailure as exc:
                raise SystemExit(f"FAIL-CLOSED at page {page}: {exc}")
            for w in j.get("results", []):
                title = w.get("title") or ""
                venue = ((w.get("primary_location") or {}).get("source") or {}).get("display_name") or ""
                abst = abstract_text(w.get("abstract_inverted_index"))
                reason = exclusion_reason(title, venue, abst, cfg)
                if reason:
                    drop_reasons[reason] = drop_reasons.get(reason, 0) + 1
                    continue
                fh.write(json.dumps(w, ensure_ascii=False) + "\n")
                kept += 1
            cursor = j.get("meta", {}).get("next_cursor")
            time.sleep(0.25)
    print(f"pages={page} kept={kept} dropped={sum(drop_reasons.values())}")
    (outdir / "manifest.json").write_text(json.dumps({
        "month": ym, "run_hash": run_hash, "script_version": SCRIPT_VERSION,
        "filter": flt, "meta_count": meta_count, "kept": kept, "pages": page,
        "dropped": sum(drop_reasons.values()),
        "drop_reasons": dict(sorted(drop_reasons.items(), key=lambda kv: -kv[1])),
    }, indent=2), encoding="utf-8")
    return {"run_hash": run_hash, "meta_count": meta_count, "kept": kept, "pages": page}


if __name__ == "__main__":
    ym = sys.argv[1] if len(sys.argv) > 1 else None
    if not ym or len(ym) != 7 or ym[4] != "-":
        raise SystemExit("usage: python scripts/01_harvest.py YYYY-MM")
    print(json.dumps(harvest(ym), indent=2))
