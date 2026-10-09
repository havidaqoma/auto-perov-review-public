"""Shared infrastructure for the evaluation studies (items 2 and 3).

ONE definition of the sandbox, the number normaliser and the report writer,
imported by both studies. Two copies of a normalisation rule diverge exactly
the way the narration filter did (handbook 7.6 #10), and here the consequence
would be a fault-injection study and a baseline study that disagree about what
counts as a fabricated number.

Nothing in this module mutates the live repository. Every study runs against a
sandbox copy, because a mutation study that edits runs/ in place would corrupt
the artifacts the papers were built from.
"""
from __future__ import annotations

import csv
import json
import os
import pathlib
import re
import shutil
import subprocess
import time
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parents[3]
RUNS = ROOT / "runs"
SANDBOX_ROOT = ROOT / "sandbox"
STUDY_OUT = ROOT / "runs" / "studies"

# ---------------------------------------------------------------------------
# Number normalisation
# ---------------------------------------------------------------------------
# A fabrication metric that has not normalised its input does not measure
# fabrication, it measures encoding. The pipeline already paid for this twice:
# U+2212 vs ASCII hyphen shipped units flat while an ASCII-only gate reported
# pass (7.6 #13), and `_VAL` matched "1.6 x 1017" but not "1.6e17" (7.7 #2).
# Declaring a number "absent from the abstract" without these rules would
# falsely accuse correct output.

_DASHES = dict.fromkeys(map(ord, "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"), "-")
_SPACES = dict.fromkeys(map(ord, "\u00a0\u2007\u202f\u2009\u200a\u2002\u2003"), " ")


def norm_text(s: str) -> str:
    """NFKC + dash/space unification + whitespace collapse."""
    s = unicodedata.normalize("NFKC", s or "")
    s = s.translate(_DASHES).translate(_SPACES)
    return re.sub(r"\s+", " ", s).strip()


_NUM = re.compile(r"\d+(?:[.,]\d+)?(?:\s*[eE]\s*[-+]?\d+)?")
_SCI = re.compile(r"(\d+(?:[.,]\d+)?)\s*[x\u00d7]\s*10\s*[-+]?\s*(\d+)")
# Digit grouping: "1,080", "20,000", "1 000 000". A group of exactly three
# digits after a separator, with 1-3 leading digits, and no further digit.
_GROUPED = re.compile(r"(?<![\d.,])(\d{1,3}(?:[, ]\d{3})+)(?![\d]|[.,]\d)")


def numbers_in(text: str) -> set[float]:
    """Every number in `text` as a float, with e-notation and x10^n folded in.

    A writer may spell one quantity three ways (1.6e17, 1.6 x 1017,
    1.6 * 10^17). All three must compare equal or the metric reports
    fabrication where the literature merely changed notation.

    Digit grouping is the fourth spelling. The first version of this function
    read every comma as a decimal point, so "1,080 h" became 1.08 and a
    correct extraction of 1080 was scored as fabricated: five of the fifteen
    ungrounded values in the first R3 run were this defect. A grouped
    spelling is ambiguous in principle (European "1,500" = 1.5), so BOTH
    readings are added; a leading zero ("0,148") is only ever a decimal.
    """
    t = norm_text(text)
    out: set[float] = set()
    for m in _SCI.finditer(t):
        try:
            out.add(float(m.group(1).replace(",", ".")) * (10 ** float(m.group(2))))
        except Exception:
            pass
    for m in _GROUPED.finditer(t):
        g = m.group(1)
        if not g.startswith("0"):
            out.add(float(re.sub(r"[, ]", "", g)))
    for m in _NUM.finditer(t):
        g = m.group(0).replace(",", ".").replace(" ", "")
        try:
            out.add(float(g))
        except Exception:
            pass
    return out


def _close(w: float, v: float, tol: float = 1e-6) -> bool:
    return abs(w - v) < tol or (v != 0 and abs(w - v) / abs(v) < 1e-9)


def number_present(want, text: str, tol: float = 1e-6) -> bool:
    """True if `want` occurs as a number in `text` under any spelling."""
    try:
        w = float(str(want).replace(",", "."))
    except Exception:
        return False
    return any(_close(w, v, tol) for v in numbers_in(text))


def number_present_legacy(want, text: str) -> bool:
    """The pre-fix metric (comma always a decimal point), kept ONLY so that a
    study can report what the published numbers were computed with. Never use
    it to decide anything."""
    try:
        w = float(str(want).replace(",", "."))
    except Exception:
        return False
    t = norm_text(text)
    vals = set()
    for m in _SCI.finditer(t):
        try:
            vals.add(float(m.group(1).replace(",", ".")) * (10 ** float(m.group(2))))
        except Exception:
            pass
    for m in _NUM.finditer(t):
        try:
            vals.add(float(m.group(0).replace(",", ".").replace(" ", "")))
        except Exception:
            pass
    return any(_close(w, v) for v in vals)


# ---------------------------------------------------------------------------
# Why is an ungrounded value ungrounded? (deterministic, lexical only)
# ---------------------------------------------------------------------------
# "Not verbatim in the source" is a union of very different events: a model
# that converted 4 mm2 to 0.04 cm2 correctly, a model that rounded 26.13 to 26,
# a slipped decimal, and a number with no source at all. Reporting them as one
# "fabrication" rate overstates the harm. This classifier only says which
# ARITHMETIC relation links the value to a number in the text. It cannot say
# whether the converted quantity was the right one (a 10-year extrapolated
# lifetime converted to hours is arithmetically exact and still not a T80);
# that needs a reader, and the paper must say so.

_AREA_PRODUCT = re.compile(
    r"(\d+(?:\.\d+)?)\s*[x\u00d7*]\s*(\d+(?:\.\d+)?)\s*(mm|cm|m)\s*(?:2|\u00b2|\^2)?")
_UNIT_AFTER = re.compile(
    r"(\d+(?:[.,]\d{3})*(?:\.\d+)?)\s*(mm|cm|m)\s*(?:2|\u00b2|\^2)|"
    r"(\d+(?:[.,]\d{3})*(?:\.\d+)?)\s*(square\s+(?:milli|centi)?met(?:er|re)s?)|"
    r"(\d+(?:[.,]\d{3})*(?:\.\d+)?)\s*(days?|weeks?|months?|years?|yrs?|min(?:utes)?)\b",
    re.I)
_AREA_F = {"mm": 0.01, "cm": 1.0, "m": 1e4}
_TIME_F = {"day": 24.0, "week": 168.0, "month": 730.0, "year": 8760.0,
           "yr": 8760.0, "min": 1 / 60}


def _decimals(v: float) -> int:
    s = repr(float(v))
    return 0 if s.endswith(".0") else len(s.split(".")[1]) if "." in s else 0


def explain_ungrounded(value, field: str, text: str) -> str:
    """One of: unit_conversion, rounding, decimal_shift, absent."""
    try:
        w = float(value)
    except Exception:
        return "absent"
    t = norm_text(text)
    rel = lambda a, b: b != 0 and abs(a - b) / abs(b) < 0.01  # noqa: E731
    conv = []
    if field == "active_area_cm2":
        for m in _AREA_PRODUCT.finditer(t):
            a, b, u = float(m.group(1)), float(m.group(2)), m.group(3).lower()
            conv.append(a * b * _AREA_F[u])
    for m in _UNIT_AFTER.finditer(t):
        num = m.group(1) or m.group(3) or m.group(5)
        unit = (m.group(2) or m.group(4) or m.group(6) or "").lower()
        try:
            x = float(num.replace(",", ""))
        except Exception:
            continue
        if field == "active_area_cm2":
            if unit in _AREA_F:
                conv.append(x * _AREA_F[unit])
            elif unit.startswith("square"):
                conv.append(x * (0.01 if "milli" in unit else 1.0 if "centi" in unit else 1e4))
        elif field == "t80_h":
            for k, f in _TIME_F.items():
                if unit.startswith(k):
                    conv.append(x * f)
    if any(rel(w, c) for c in conv):
        return "unit_conversion"
    src = numbers_in(t)
    d = _decimals(w)
    for s in src:
        if s != w and round(s, d) == round(w, d) and abs(s - w) < 1.0:
            return "rounding"
    for s in src:
        for k in (-3, -2, -1, 1, 2, 3):
            if s != 0 and _close(w, s * 10 ** k):
                return "decimal_shift"
    return "absent"


# ---------------------------------------------------------------------------
# Sandbox
# ---------------------------------------------------------------------------

def active_run(month: str, root: pathlib.Path = ROOT) -> pathlib.Path:
    ptr = root / "runs" / f"{month}.active"
    return root / "runs" / ptr.read_text(encoding="utf-8").strip()


def _ignore(_dir, names):
    return [n for n in names if n in ("__pycache__", ".git", ".pytest_cache")]


def make_sandbox(month: str, tag: str, quiet: bool = True) -> pathlib.Path:
    """A minimal but COMPLETE repo copy that can run the real build stage.

    Copies scripts/, config/, this month's whole run dir (including private/,
    which is gitignored but is what verify_anchors re-derives from), and every
    PRIOR issue's rendered markdown so G8-novelty still has something to
    compare against. Skipping the priors would make G8 report `skip` and the
    study would silently stop testing it.
    """
    sb = SANDBOX_ROOT / tag
    # Handbook 2.3: never rmtree a directory you are about to recreate. On
    # Windows a stale handle outlives the process, so rmtree "succeeds" via
    # ignore_errors while the directory survives, and the next copytree dies
    # with WinError 183. Seen on the second fault-injection pass. Sync
    # file-by-file instead and let dirs_exist_ok absorb the remains.
    shutil.rmtree(sb, ignore_errors=True)
    (sb / "runs").mkdir(parents=True, exist_ok=True)

    shutil.copytree(ROOT / "scripts", sb / "scripts", ignore=_ignore,
                    dirs_exist_ok=True)
    shutil.copytree(ROOT / "config", sb / "config", ignore=_ignore,
                    dirs_exist_ok=True)

    rd = active_run(month)
    shutil.copytree(rd, sb / "runs" / rd.name, ignore=_ignore,
                    dirs_exist_ok=True)
    shutil.copy(RUNS / f"{month}.active", sb / "runs" / f"{month}.active")

    # prior-month trend figures: G3e accepts a numeral from the previous
    # month's stats (s18d._g3e_aggregates reads stats_history/). Without them
    # the clean control failed G3e on "5.9% in 2026-06" and the study scored a
    # correct build as a broken control (2026-10-09).
    if (ROOT / "stats_history").exists():
        shutil.copytree(ROOT / "stats_history", sb / "stats_history",
                        ignore=_ignore, dirs_exist_ok=True)

    # prior issues: only the rendered markdown G8 reads
    for p in sorted(RUNS.glob("*/manuscript_v*.md")):
        if p.parent.name.split("_")[0] < month:
            d = sb / "runs" / p.parent.name
            d.mkdir(parents=True, exist_ok=True)
            shutil.copy(p, d / p.name)

    if not quiet:
        print(f"[sandbox] {sb}")
    return sb


def unfreeze_drafts(sb: pathlib.Path, month: str, age_s: int = 120) -> None:
    """Backdate draft mtimes.

    s18d refuses to build if any draft changed in the last 20 s (the orphan
    writer guard, 7.4). Every injection touches a draft, so without this the
    harness would measure that guard over and over instead of the gate under
    test.
    """
    rd = active_run(month, sb)
    old = time.time() - age_s
    for p in list((rd / "draft_v4").glob("*.md")):
        os.utime(p, (old, old))


def run(cmd: list[str], cwd: pathlib.Path, timeout: int = 900) -> dict:
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                           timeout=timeout, errors="replace")
        return {"rc": p.returncode, "out": p.stdout or "", "err": p.stderr or "",
                "sec": round(time.time() - t0, 1)}
    except subprocess.TimeoutExpired:
        return {"rc": 124, "out": "", "err": f"TIMEOUT after {timeout}s",
                "sec": round(time.time() - t0, 1)}


def gate_status(sb: pathlib.Path, month: str, ver: str = "v4") -> dict:
    rd = active_run(month, sb)
    p = rd / f"gate_report_{ver}.json"
    if not p.exists():
        return {}
    g = json.loads(p.read_text(encoding="utf-8"))
    return {k: v.get("status") for k, v in g.items() if isinstance(v, dict)}


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def write_report(name: str, rows: list[dict], meta: dict) -> tuple[pathlib.Path, pathlib.Path]:
    """CSV + JSON with the same schema, so a figure never reads literal data."""
    STUDY_OUT.mkdir(parents=True, exist_ok=True)
    cols: list[str] = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    csv_p = STUDY_OUT / f"{name}.csv"
    with csv_p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    json_p = STUDY_OUT / f"{name}.json"
    json_p.write_text(json.dumps({"meta": meta, "rows": rows}, indent=2),
                      encoding="utf-8")
    return csv_p, json_p


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson 95% interval. Normal approximation breaks at k=0 and k=n, which
    is precisely where a detection-rate study lives."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (round(max(0.0, c - h), 4), round(min(1.0, c + h), 4))
