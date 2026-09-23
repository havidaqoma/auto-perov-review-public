"""Shared helpers for v5 stages: run dirs, jsonl, .done markers, abstracts."""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
RUNS = ROOT / "runs"
CONFIG = ROOT / "config"
DATA = ROOT / "data"


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              cwd=ROOT, capture_output=True, text=True,
                              timeout=15).stdout.strip() or "nogit"
    except Exception:
        return "nogit"


def config_hash() -> str:
    h = hashlib.sha256()
    for f in sorted(CONFIG.glob("*.yaml")):
        h.update(f.read_bytes())
    return h.hexdigest()[:8]


def run_dir(month: str, create: bool = True) -> pathlib.Path:
    """Resolve THIS month's run dir, pinned once and then stable.

    The identifier includes the config hash (5: run = sha of month+commit+config),
    which is right for provenance and wrong as a live lookup: editing any config
    mid-run silently relocates the directory, so a later stage reads an empty
    dir instead of the harvested one. Real failure seen 2026-09-07 -- adding
    gates.yaml between stage 06 and stage 04 moved 197abe83 -> 51e6c170 and
    04_venues found 0 venues in a 655-work corpus.

    Fix: the FIRST stage to run pins the id into runs/<month>.active, and every
    later stage follows that pointer. Provenance is preserved (the pinned id
    still encodes the config at harvest time) and the run stops being able to
    wander. Delete the pointer to force a fresh run.
    """
    ptr = RUNS / f"{month}.active"
    if ptr.exists():
        d = RUNS / ptr.read_text(encoding="utf-8").strip()
        if create:
            (d / "private").mkdir(parents=True, exist_ok=True)
        return d
    tag = hashlib.sha256(f"{month}|{git_commit()}|{config_hash()}".encode()).hexdigest()[:8]
    d = RUNS / f"{month}_{tag}"
    if create:
        (d / "private").mkdir(parents=True, exist_ok=True)
        RUNS.mkdir(parents=True, exist_ok=True)
        ptr.write_text(d.name, encoding="utf-8")
    return d


def write_jsonl(path: pathlib.Path, rows) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n


def read_jsonl(path: pathlib.Path) -> list:
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def done(rd: pathlib.Path, stage: str, **info) -> None:
    (rd / f"{stage}.done").write_text(
        json.dumps({"stage": stage, "at": time.strftime("%Y-%m-%dT%H:%M:%S"), **info},
                   indent=2), encoding="utf-8")


#: stage -> the payload key that must be non-zero for the stage to count as done
_NONZERO = {
    "01_harvest": "openalex_count",
    "02_normalize": "n",
    "05_dedupe": "n_corpus",
    "06_mechanism": "n_kept",
    "08_subset": "n_depth",
    "09_cards": "n_cards",
    "10_stats": "n_keys",
}


def is_done(rd: pathlib.Path, stage: str) -> bool:
    """True only if the stage finished AND produced output.

    File existence alone is not enough. On 2026-09-07 the failed stage-09 run
    (every opencode call rc=1, see s09_cards._opencode_exe) still wrote a
    09_cards.done recording n_cards=0 / dropped_papers=181. A resume would
    have trusted that marker and skipped extraction entirely, shipping a paper
    with no cards at all -- section 0 rule 4 ("no stage proceeds on partial or
    guessed inputs") defeated by a file that merely exists.

    So a marker whose own payload says it produced nothing is treated as NOT
    done. Third instance of the silent-zero class this run, after the run_dir
    relocation and the ignored subprocess return code.
    """
    f = rd / f"{stage}.done"
    if not f.exists():
        return False
    key = _NONZERO.get(stage)
    if not key:
        return True
    try:
        payload = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return False
    return bool(payload.get(key))


def reconstruct_abstract(inv: dict | None) -> str:
    """OpenAlex abstract_inverted_index -> plain text."""
    if not inv:
        return ""
    pos: dict[int, str] = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    if not pos:
        return ""
    return " ".join(pos[k] for k in sorted(pos))


def month_bounds(month: str) -> tuple[str, str]:
    import calendar
    y, m = (int(x) for x in month.split("-"))
    return f"{month}-01", f"{month}-{calendar.monthrange(y, m)[1]:02d}"


def is_year(period: str) -> bool:
    """True for '2025', False for '2025-06'.

    The yearly-backfill project runs stages over a YEAR as well as a month,
    so every stage must be able to tell which it was handed. A stage that
    guesses would silently harvest one month and label it a year.
    """
    return len(period) == 4 and period.isdigit()


def period_bounds(period: str) -> tuple[str, str]:
    """Inclusive ISO date bounds for either a month or a whole year.

    This project harvests a year directly (no monthly runs exist here), so
    month_bounds alone is insufficient. month_bounds is KEPT unchanged and
    still used for per-month slicing, because the trajectory series needs
    twelve real month boundaries.
    """
    if is_year(period):
        return f"{period}-01-01", f"{period}-12-31"
    return month_bounds(period)


def year_months(year: str) -> list[str]:
    """The twelve 'YYYY-MM' slices of a year, in order.

    The trajectory section and F5 need per-month values even though the
    harvest is annual, so the slicing happens on publication_date AFTER the
    harvest rather than by twelve separate API sweeps.
    """
    if not is_year(year):
        raise ValueError(f"expected a 4-digit year, got {year!r}")
    return [f"{year}-{m:02d}" for m in range(1, 13)]
