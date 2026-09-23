"""P-07: measure how long OpenAlex keeps ingesting a finished month (Q39).

Papers published in August keep being added to OpenAlex for weeks afterwards.
The monthly cron must not fire before the month has finished arriving, or it
harvests a partial corpus, passes every gate, and misstates its own scope.

Method: re-run the stage-01 count for one already-finished month at weekly
points, then find the first point whose count is at least 95% of the final
point. That day of the month becomes `cron_day`.

The count query is IMPORTED from s01_harvest rather than retyped. A probe that
measures a slightly different filter than the harvester measures nothing about
the harvester (handbook 0.3 corollary: the check is as likely to be wrong as
the thing it checks).

Usage
-----
    python scripts/probe_p07_indexing_lag.py 2026-08 --record
    python scripts/probe_p07_indexing_lag.py --report
    python scripts/probe_p07_indexing_lag.py --report --apply

--record  takes one reading and appends it to docs/p07_indexing_lag.jsonl
--report  reads the ledger and computes the day; exits non-zero if it cannot
--apply   additionally writes the measured day into config/gates.yaml

Read-only against the network. --record never edits config; only --apply does.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from common.net import oa, redact  # noqa: E402
from stages.s01_harvest import FILTER  # noqa: E402  -- one definition, not two
from stages.util import month_bounds  # noqa: E402

LEDGER = ROOT / "docs" / "p07_indexing_lag.jsonl"
GATES = ROOT / "config" / "gates.yaml"
RATIO = 0.95


def count_for(month: str) -> tuple[int, str]:
    """The stage-01 count for `month`, as of right now."""
    a, b = month_bounds(month)
    url = (f"https://api.openalex.org/works?filter={FILTER},"
           f"from_publication_date:{a},to_publication_date:{b},"
           f"type:article|preprint|review&per-page=1")
    j = oa(url, stage="p07_indexing_lag")
    return int(j["meta"]["count"]), url


def record(month: str) -> dict:
    now = dt.datetime.now().astimezone()
    n, url = count_for(month)
    rec = {
        "probe": "P-07",
        "month": month,
        "as_of": now.isoformat(timespec="seconds"),
        "point_day": now.day,
        "openalex_count": n,
        "filter_sha256": hashlib.sha256(FILTER.encode()).hexdigest()[:12],
    }
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[P-07] {month} as of {rec['as_of']} (day {rec['point_day']}): "
          f"{n} works")
    print(f"[P-07] query: {redact(url)}")
    print(f"[P-07] appended to {LEDGER.relative_to(ROOT)}")
    return rec


def load(month: str | None = None) -> list[dict]:
    if not LEDGER.exists():
        return []
    out = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if month is None or r.get("month") == month:
            out.append(r)
    out.sort(key=lambda r: r.get("as_of", ""))
    return out


def _dedupe_by_day(recs: list[dict]) -> list[dict]:
    """One reading per day: a re-run must not create a second point."""
    by_day: dict[int, dict] = {}
    for r in recs:
        by_day[int(r["point_day"])] = r  # later reading wins
    return [by_day[d] for d in sorted(by_day)]


def report(apply: bool = False) -> int:
    recs = load()
    if not recs:
        print("FAIL: no P-07 readings in docs/p07_indexing_lag.jsonl.")
        print("Take one with: python scripts/probe_p07_indexing_lag.py <YYYY-MM> --record")
        return 1

    month = recs[-1]["month"]
    pts = _dedupe_by_day([r for r in recs if r["month"] == month])

    print(f"P-07 indexing lag for {month} ({len(pts)} readings)\n")
    for r in pts:
        print(f"  day {r['point_day']:>2}  {r['as_of'][:10]}  {r['openalex_count']:>6} works")

    final = pts[-1]
    # The series is only meaningful once it has stopped moving. With fewer than
    # three points, or with the last two still climbing, the "final" count is
    # not final and any day derived from it is a guess wearing a number.
    if len(pts) < 3:
        print(f"\nINCOMPLETE: {len(pts)} of 3+ readings. No day can be derived yet.")
        return 2

    threshold = RATIO * final["openalex_count"]
    print(f"\n  final point : day {final['point_day']} = {final['openalex_count']} works")
    print(f"  95% threshold: {threshold:.1f}")

    still_climbing = (len(pts) >= 2
                      and pts[-2]["openalex_count"] < threshold)
    day = next((r["point_day"] for r in pts
                if r["openalex_count"] >= threshold), final["point_day"])
    print(f"  first point >= threshold: day {day}")

    if still_climbing:
        print("\nWARNING: the second-to-last reading is still below the 95% "
              "threshold, so the series has not flattened. The measured day is "
              "a lower bound; take another reading before trusting it.")

    print(f"\nMEASURED cron_day = {day}")
    if not apply:
        print("(report only; pass --apply to write it into config/gates.yaml)")
        return 0

    txt = GATES.read_text(encoding="utf-8")
    new, n = re.subn(r"(?m)^cron_day:\s*\d+\s*$", f"cron_day: {day}", txt)
    if n != 1:
        print(f"FAIL: expected exactly one 'cron_day:' line in gates.yaml, found {n}")
        return 1
    if new == txt:
        print(f"config/gates.yaml already at cron_day: {day} — unchanged.")
        return 0
    GATES.write_text(new, encoding="utf-8")
    print(f"config/gates.yaml updated -> cron_day: {day}")
    print("The cron job's schedule is NOT changed by this script. Edit it "
          "deliberately once Havid has seen the number.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("month", nargs="?", help="YYYY-MM to re-count (with --record)")
    ap.add_argument("--record", action="store_true", help="take one reading")
    ap.add_argument("--report", action="store_true", help="compute the day")
    ap.add_argument("--apply", action="store_true",
                    help="with --report: write cron_day into config/gates.yaml")
    a = ap.parse_args()

    if a.record:
        if not a.month:
            ap.error("--record needs a month, e.g. 2026-08")
        record(a.month)
        if not a.report:
            return 0
    if a.report:
        return report(apply=a.apply)
    ap.error("give --record and/or --report")


if __name__ == "__main__":
    raise SystemExit(main())
