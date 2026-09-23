"""CSV writer: utf-8-sig so Excel on Windows renders UTF-8 (eyeball gate)."""
from __future__ import annotations

import csv
from pathlib import Path


def write_rows(path: str | Path, header: list[str], rows: list[list]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def read_rows(path: str | Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))
