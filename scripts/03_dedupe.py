"""03_dedupe: records.jsonl -> csv/perovskite_<month>.csv (v2 4.1-4.3).

Deterministic, idempotent per (month, run_hash):
- in-batch dedupe collapses duplicate papers WITHIN the run (prefer journal-article over preprint)
- ledger match skips papers already canonical from previous months
- two-phase ledger: pending JSONL first; canonical merge only after the CSV is fully written
- a finalized run is short-circuited (never rewrites an existing CSV partially/empty)
"""
import csv
import json
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[0]))

from common import ledger
from common import titles as titlesmod

ROOT = pathlib.Path(__file__).resolve().parents[1]
PREPRINT_LABELS = {"preprint"}


def find_run_hash(ym: str) -> str:
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
    return best


def _keys_for(rec: dict) -> list[tuple[str, str]]:
    keys = []
    if rec.get("doi_norm"):
        keys.append(("doi", rec["doi_norm"]))
    if rec.get("oa_id"):
        keys.append(("oa", rec["oa_id"]))
    if rec.get("arxiv_id"):
        keys.append(("arxiv", rec["arxiv_id"]))
    tc = titlesmod.clean_title(rec.get("title_clean", "")).lower()
    keys.append(("title-hash", titlesmod.title_hash(tc)))
    return keys


def in_batch_dedupe(recs: list[dict]) -> tuple[list[dict], dict]:
    """Collapse duplicate papers inside one run. Prefer journal-article, earliest date."""
    recs = sorted(recs, key=lambda r: (
        1 if r.get("venue_type_label") in PREPRINT_LABELS else 0,
        r.get("date_published", ""), r.get("title_clean", "").lower(), r.get("doi_norm", "")))
    seen, keep, reasons = {}, [], {}
    for rec in recs:
        keys = _keys_for(rec)
        hit = next(((k, v) for k, v in keys if v and v in seen), None)
        if hit:
            reasons[hit[0]] = reasons.get(hit[0], 0) + 1
            continue
        for k, v in keys:
            if v:
                seen[v] = rec.get("oa_id") or rec.get("doi_norm")
        keep.append(rec)
    return keep, reasons


def dedupe(ym: str, run_hash: str | None = None) -> dict:
    run_hash = run_hash or find_run_hash(ym)
    db = ROOT / "data" / "ledger.sqlite3"
    conn = ledger.open_db(db)
    already = conn.execute(
        "SELECT status FROM runs WHERE month=? AND run_hash=?", (ym, run_hash)).fetchone()
    if already:
        conn.close()
        print(f"run {run_hash} already {already[0]}; CSV and ledger untouched")
        sp = ROOT / "runs" / run_hash / "dedupe_stats.json"
        if sp.exists():
            return json.loads(sp.read_text(encoding="utf-8"))
        return {"run_hash": run_hash, "csv_rows": None, "note": "already finalized"}

    recs = [json.loads(l) for l in
            open(ROOT / "runs" / run_hash / "records.jsonl", encoding="utf-8") if l.strip()]
    print(f"records loaded: {len(recs)} (run {run_hash})")

    in_batch, reasons_batch = in_batch_dedupe(recs)
    if reasons_batch:
        print("in-batch dup:", sum(reasons_batch.values()), reasons_batch)

    keep, reasons_ledger = [], {}
    for rec in in_batch:
        probe = {"title": rec["title_clean"], "doi_norm": rec["doi_norm"],
                 "openalex_id": rec["oa_id"], "arxiv_id": rec["arxiv_id"]}
        existing, rsn = ledger.match_existing(conn, probe)
        if existing is not None:
            for r_ in rsn:
                reasons_ledger[r_] = reasons_ledger.get(r_, 0) + 1
            continue
        keep.append(rec)
    conn.close()

    keep.sort(key=lambda r: (r["date_published"], r["title_clean"].lower(), r["doi_norm"]))
    print(f"new rows for CSV: {len(keep)} | in-batch dup: {sum(reasons_batch.values())} "
          f"| ledger dup: {sum(reasons_ledger.values())} {reasons_ledger}")

    header_cfg = yaml.safe_load(
        (ROOT / "config/csv_columns.yaml").read_text(encoding="utf-8"))["columns"]
    header = [str(c["label"]) for c in header_cfg]

    csv_path = ROOT / "csv" / f"perovskite_{ym}.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for i, rec in enumerate(keep, 1):
            w.writerow([
                i, rec["date_published"], rec["category"], rec["title_clean"],
                rec["journal"], rec["author_first"], rec["institution_first"],
                rec["doi_norm"], rec["summary"], rec["country_name"], "oa:Perovskite",
                rec["venue_type_label"], rec["cited_by"], rec["oa_status"],
                rec["arxiv_id"], rec["oa_id"], "", rec["axis_provisional"],
                ym, rec["first_seen"], rec["lang"], "",
            ])

    pending = [{"title": rec["title_clean"], "doi_norm": rec["doi_norm"],
                "openalex_id": rec["oa_id"], "arxiv_id": rec["arxiv_id"],
                "first_seen": rec["first_seen"], "payload_hash": rec["oa_id"]}
               for rec in keep]
    ledger.append_pending(ROOT / "runs" / run_hash, pending, run_hash, ym)
    counts = {"records": len(recs), "in_batch_dups": sum(reasons_batch.values()),
              "in_batch_reasons": reasons_batch, "csv_rows": len(keep),
              "ledger_dup_skipped": sum(reasons_ledger.values()), "ledger_reasons": reasons_ledger}
    res = ledger.finalize_run(db, ROOT / "runs" / run_hash, run_hash, ym, counts)

    out = {"run_hash": run_hash, "csv": str(csv_path), "csv_rows": len(keep),
           "in_batch": reasons_batch, "finalize": res}
    (ROOT / "runs" / run_hash / "dedupe_stats.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":
    ym = sys.argv[1] if len(sys.argv) > 1 else ""
    rh = sys.argv[2] if len(sys.argv) > 2 else None
    if len(ym) != 7:
        raise SystemExit("usage: python scripts/03_dedupe.py YYYY-MM [run_hash]")
    print(json.dumps(dedupe(ym, rh), indent=2))
