"""Two-phase dedup ledger. Nothing touches the canonical sqlite3 until
finalize_run(); the fail-closed guarantee (Q26=b) is structural, not a convention."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from common.titles import clean_title, containment, title_hash

SCHEMA = """
CREATE TABLE IF NOT EXISTS papers(
  id INTEGER PRIMARY KEY,
  doi_norm TEXT UNIQUE,
  openalex_id TEXT, arxiv_id TEXT, s2_id TEXT,
  title_hash TEXT, title_clean TEXT,
  month_tag TEXT, first_seen TEXT, payload_hash TEXT
);
CREATE INDEX IF NOT EXISTS idx_oa  ON papers(openalex_id);
CREATE INDEX IF NOT EXISTS idx_arx ON papers(arxiv_id);
CREATE INDEX IF NOT EXISTS idx_th  ON papers(title_hash);
CREATE TABLE IF NOT EXISTS runs(
  month TEXT, run_hash TEXT, status TEXT, counts_json TEXT,
  PRIMARY KEY(month, run_hash)
);
"""


def _nn(x) -> str | None:
    x = (x or "").strip()
    return x or None


def open_db(path: str | Path) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.executescript(SCHEMA)
    return conn


def match_existing(conn: sqlite3.Connection, rec: dict) -> tuple[int | None, list[str]]:
    """Return (existing paper id, reasons) when rec duplicates a stored paper.
    Duplicate iff any of: doi, openalex id, arxiv id, 80-char title hash,
    >30-char title containment (v2 §4.3.2). First match wins."""
    f = {k: _nn(rec.get(k)) for k in ("doi_norm", "openalex_id", "arxiv_id", "s2_id")}
    if f["doi_norm"]:
        row = conn.execute("SELECT id FROM papers WHERE doi_norm=?", (f["doi_norm"],)).fetchone()
        if row:
            return row[0], ["doi"]
    for kind, val in (("openalex_id", f["openalex_id"]), ("arxiv_id", f["arxiv_id"])):
        if val:
            row = conn.execute(f"SELECT id FROM papers WHERE {kind}=?", (val,)).fetchone()
            if row:
                return row[0], [kind]
    tc = clean_title(rec.get("title", "")).lower()
    th = title_hash(tc)
    row = conn.execute("SELECT id FROM papers WHERE title_hash=?", (th,)).fetchone()
    if row:
        return row[0], ["title-hash"]
    if len(tc) > 30:
        for pid, stored in conn.execute("SELECT id, title_clean FROM papers"):
            if containment(tc, stored):
                return pid, ["title-containment"]
    return None, []


def append_pending(run_dir: str | Path, recs: list[dict], run_hash: str, month: str) -> Path:
    p = Path(run_dir) / "ledger_pending.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:  # overwrite: pending derived per run
        for rec in recs:
            fh.write(json.dumps({"run": run_hash, "month": month, "rec": rec},
                                ensure_ascii=False) + "\n")
    return p


def finalize_run(db_path: str | Path, run_dir: str | Path, run_hash: str, month: str,
                 counts: dict) -> dict:
    """Merge pending records into the canonical db. Idempotent per (month, run_hash);
    the runs row is written only after a fully successful merge (Q26=b)."""
    conn = open_db(db_path)
    if conn.execute("SELECT 1 FROM runs WHERE month=? AND run_hash=?",
                    (month, run_hash)).fetchone():
        conn.close()
        return {"finalized": False, "reason": "already-finalized"}
    pending = Path(run_dir) / "ledger_pending.jsonl"
    added = dup = 0
    if pending.exists():
        with open(pending, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                rec = json.loads(line)["rec"]
                existing, _reasons = match_existing(conn, rec)
                if existing is not None:
                    dup += 1
                    continue
                tc = clean_title(rec.get("title", "")).lower()
                cur = conn.execute(
                    "INSERT INTO papers(doi_norm, openalex_id, arxiv_id, s2_id, "
                    "title_hash, title_clean, month_tag, first_seen, payload_hash) "
                    "VALUES(?,?,?,?,?,?,?,?,?)",
                    (_nn(rec.get("doi_norm")), _nn(rec.get("openalex_id")),
                     _nn(rec.get("arxiv_id")), _nn(rec.get("s2_id")),
                     title_hash(tc), tc, month, rec.get("first_seen") or "",
                     rec.get("payload_hash") or "")).lastrowid
                added += int(cur is not None)
    conn.execute("INSERT INTO runs(month, run_hash, status, counts_json) VALUES(?,?,?,?)",
                 (month, run_hash, "finalized", json.dumps(counts)))
    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    conn.close()
    return {"finalized": True, "added": added, "dup": dup, "total": total}
