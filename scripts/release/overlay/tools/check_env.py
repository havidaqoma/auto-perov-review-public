"""check_env.py: compare the live environment against the pinned manifest.

Exists because the Supplementary Information claims "package version pins and
a container manifest specify the execution environment". That sentence was in
the manuscript before any manifest existed on disk. This script is what makes
the claim checkable instead of decorative: it reads requirements.txt and
env.lock.json, inspects the running interpreter and the external binaries,
and names every mismatch.

Exit codes
----------
0  every pin matches
1  at least one mismatch or missing package
2  the manifest itself is missing or unreadable

A mismatch is NOT automatically an error in the science sense. Tier 0
re-verification is pure Python over stored JSON and tolerates patch drift.
The script therefore separates HARD requirements (needed to re-verify) from
SOFT ones (needed only to regenerate figures or re-harvest), and reports
which tier a given mismatch actually blocks.

Usage
-----
    python tools/check_env.py             # human report, exit code gates
    python tools/check_env.py --json      # machine-readable
"""
from __future__ import annotations

import argparse
import importlib.metadata as md
import json
import pathlib
import platform
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
REQ = ROOT / "requirements.txt"
LOCK = ROOT / "env.lock.json"

#: which tier stops working when this package is wrong or absent
TIER_OF = {
    "pyyaml": 0,      # every stage reads config/*.yaml
    "pytest": 0,      # the unit suite IS the tier-0 check
    "pymupdf": 0,     # rendered-PDF verification
    "numpy": 1,       # figure regeneration
    "matplotlib": 1,  # figure regeneration
    "requests": 2,    # live API harvest
    "pydantic": 0,    # config schema validation
}

#: import name when it differs from the distribution name
IMPORT_NAME = {"pyyaml": "yaml", "pymupdf": "pymupdf"}


def parse_requirements() -> dict[str, str]:
    if not REQ.exists():
        print(f"FAIL: {REQ} missing", file=sys.stderr)
        raise SystemExit(2)
    out: dict[str, str] = {}
    for ln in REQ.read_text(encoding="utf-8").splitlines():
        ln = ln.split("#", 1)[0].strip()
        if not ln:
            continue
        m = re.match(r"^([A-Za-z0-9_.-]+)==([^\s]+)$", ln)
        if not m:
            print(f"FAIL: cannot parse requirement {ln!r}; only NAME==VERSION "
                  "is accepted so the pin cannot be a range",
                  file=sys.stderr)
            raise SystemExit(2)
        out[m.group(1).lower()] = m.group(2)
    return out


def installed_version(dist: str) -> str | None:
    try:
        return md.version(dist)
    except md.PackageNotFoundError:
        return None


def binary_version(cmd: str, args: list[str]) -> str | None:
    exe = shutil.which(cmd)
    if not exe:
        # Windows installs pandoc outside PATH often enough to be worth
        # looking, and the build stage already does exactly this.
        for c in (pathlib.Path.home() / "AppData/Local/Pandoc/pandoc.exe",
                  pathlib.Path(r"C:\Program Files\Pandoc\pandoc.exe")):
            if c.exists():
                exe = str(c)
                break
    if not exe:
        return None
    try:
        p = subprocess.run([exe] + args, capture_output=True, text=True,
                           timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    txt = (p.stdout or "") + (p.stderr or "")
    m = re.search(r"(\d+\.\d+(?:\.\d+)?)", txt)
    return m.group(1) if m else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    want = parse_requirements()
    lock = json.loads(LOCK.read_text(encoding="utf-8")) if LOCK.exists() else {}

    rows = []
    for dist, pin in sorted(want.items()):
        have = installed_version(dist)
        rows.append({
            "kind": "python-package",
            "name": dist,
            "expected": pin,
            "found": have,
            "ok": have == pin,
            "blocks_tier": TIER_OF.get(dist, 2),
        })

    py_want = lock.get("python")
    py_have = platform.python_version()
    if py_want:
        # Patch level of CPython does not change JSON arithmetic; minor does
        # (3.11 raised on mid-pattern inline regex flags, which killed a stage
        # once already). So compare on MAJOR.MINOR and report the full string.
        rows.append({
            "kind": "interpreter",
            "name": "python",
            "expected": py_want,
            "found": py_have,
            "ok": py_have.split(".")[:2] == py_want.split(".")[:2],
            "blocks_tier": 0,
        })

    for name, spec in (lock.get("external") or {}).items():
        have = binary_version(name, spec.get("version_args") or ["--version"])
        rows.append({
            "kind": "external-binary",
            "name": name,
            "expected": spec.get("version"),
            "found": have,
            # A PDF renders identically enough across pandoc patch releases
            # that we compare MAJOR.MINOR; a missing binary is a hard fail for
            # tier 1 because nothing can be rebuilt without it.
            "ok": bool(have) and (have.split(".")[:2]
                                  == str(spec.get("version")).split(".")[:2]),
            "blocks_tier": spec.get("blocks_tier", 1),
        })

    bad = [r for r in rows if not r["ok"]]
    if a.json:
        print(json.dumps({"ok": not bad, "rows": rows}, indent=1))
        return 1 if bad else 0

    print(f"{'component':<22}{'expected':<12}{'found':<12}tier  ok")
    for r in rows:
        print(f"{r['name']:<22}{str(r['expected']):<12}"
              f"{str(r['found']):<12}{r['blocks_tier']:<6}"
              f"{'yes' if r['ok'] else 'NO'}")

    if not bad:
        print("\nenvironment matches the manifest")
        return 0

    print(f"\n{len(bad)} mismatch(es):")
    for r in bad:
        what = ("not installed" if r["found"] is None
                else f"{r['found']} instead of {r['expected']}")
        print(f"  {r['name']}: {what}  -> blocks tier {r['blocks_tier']} "
              "and above")
    t0 = [r["name"] for r in bad if r["blocks_tier"] == 0]
    if t0:
        print("\nTier 0 (offline re-verification) is affected by: "
              + ", ".join(t0))
    else:
        print("\nTier 0 (offline re-verification) is UNAFFECTED; "
              "`python reproduce.py --tier 0` should still pass.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
