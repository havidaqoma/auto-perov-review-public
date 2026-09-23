"""Read-only dry-run: per-month OpenAlex work counts for 2026-01..2026-06.

Writes runs/2026-H1_dryrun.json. Touches NO monthly run dir and NO monthly stage.

Two things this deliberately does NOT do:
  * paraphrase the query -- FILTER is imported verbatim from s01_harvest, because
    every trap in handbook 9.1 (a `-term` returning count 0, rejected wildcards)
    comes from a retyped query.
  * roll its own HTTP -- oa() carries the key, the UA and the 429 backoff. A raw
    requests.get() got rate-limited here on the first try.
"""
import datetime
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from common.net import oa
from stages.s01_harvest import FILTER

MONTHS = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]
BAND = (250, 1200)  # config/gates.yaml count_band, read-only reference
TYPES = "type:article|preprint|review"  # same conjunction s01 paginates with


def month_bounds(m):
    y, mm = (int(x) for x in m.split("-"))
    a = f"{y:04d}-{mm:02d}-01"
    ny, nm = (y + 1, 1) if mm == 12 else (y, mm + 1)
    b = (datetime.date(ny, nm, 1) - datetime.timedelta(days=1)).isoformat()
    return a, b


def count(m):
    a, b = month_bounds(m)
    url = (
        f"https://api.openalex.org/works?filter={FILTER},"
        f"from_publication_date:{a},to_publication_date:{b},"
        f"{TYPES}&per-page=1"
    )
    return oa(url, stage="h1_dryrun_count")["meta"]["count"]


def main():
    rows = []
    for m in MONTHS:
        n = count(m)
        status = "OK" if BAND[0] <= n <= BAND[1] else ("ZERO" if n == 0 else "OUT_OF_BAND")
        rows.append({"month": m, "count": n, "status": status})
        print(f"{m}  {n:6d}  {status}", flush=True)
        time.sleep(2)

    total = sum(r["count"] for r in rows)
    shares = {r["month"]: round(100.0 * r["count"] / total, 1) for r in rows} if total else {}
    out = {
        "edition": "2026-H1",
        "filter": FILTER,
        "types": TYPES,
        "count_band_monthly": list(BAND),
        "months": rows,
        "total_raw": total,
        "share_pct": shares,
        "min_share_pct": min(shares.values()) if shares else None,
        "max_share_pct": max(shares.values()) if shares else None,
        "note": "raw pre-dedupe counts; the cross-month union will be smaller",
    }
    p = ROOT / "runs" / "2026-H1_dryrun.json"
    p.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\ntotal_raw={total}")
    print(f"shares={shares}")
    print(f"wrote {p}")
    if any(r["status"] == "ZERO" for r in rows):
        print("ABORT-WORTHY: a zero is a bug until proven otherwise")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
