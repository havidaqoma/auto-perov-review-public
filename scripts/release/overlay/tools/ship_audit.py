"""ship_audit.py: last check before the tree becomes public.

Run inside the BUILT public tree, not the private repo. It answers the only
questions that matter irreversibly: does this tree contain a credential, does
it contain someone else's copyrighted PDF, does it contain a path that leaks
the private machine, and does it contain the unpublished manuscript.

A push is irreversible in practice. GitHub caches forks and third parties
mirror within minutes, so a secret pushed once must be treated as burned
regardless of how fast the commit is deleted. That asymmetry is why this runs
before the first commit rather than in CI afterwards.

Exit codes
----------
0  nothing found
1  at least one finding (each is printed with file and line)
2  the tree does not look like a built public tree

Usage
-----
    python tools/ship_audit.py
    python tools/ship_audit.py --json audit.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

SKIP_DIR = {".git", "__pycache__", ".pytest_cache", "node_modules"}
BINARY_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".gz", ".zip", ".woff",
              ".woff2", ".ttf", ".otf", ".ico", ".xlsx", ".docx", ".db"}

# Credential shapes. Deliberately specific: a pattern like [A-Za-z0-9]{32}
# matches every sha256 in the run directories and buries the real finding in
# thousands of false ones, which is how a scan gets ignored.
SECRET_PATTERNS: list[tuple[str, str]] = [
    ("openai-style key",      r"sk-[A-Za-z0-9_\-]{20,}"),
    ("anthropic key",         r"sk-ant-[A-Za-z0-9_\-]{20,}"),
    ("github token",          r"gh[pousr]_[A-Za-z0-9]{20,}"),
    ("google api key",        r"AIza[A-Za-z0-9_\-]{30,}"),
    ("huggingface token",     r"hf_[A-Za-z0-9]{30,}"),
    ("openrouter key",        r"sk-or-v1-[A-Za-z0-9]{20,}"),
    ("slack token",           r"xox[abprs]-[A-Za-z0-9\-]{10,}"),
    ("aws access key id",     r"AKIA[0-9A-Z]{16}"),
    ("private key block",     r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
    ("bearer literal",        r"Bearer\s+[A-Za-z0-9_\-]{30,}"),
    ("assigned env secret",   r"(?i)(api[_-]?key|secret|token|password)\s*"
                              r"[=:]\s*['\"][A-Za-z0-9_\-]{24,}['\"]"),
]

# Absolute paths from the authoring machine. Harmless technically, but they
# tell a reader the operator's username and drive layout, and they make the
# repo look like a dump rather than a release.
PATH_PATTERNS: list[tuple[str, str]] = [
    ("windows user path", r"[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s\"']+"),
    ("private repo drive", r"F:[\\/]+GITHUB"),
    ("hermes profile path", r"AppData[\\/]+Local[\\/]+hermes"),
]

# Things that must not be in a public tree at all.
FORBIDDEN_PATHS: list[tuple[str, str]] = [
    ("third-party copyrighted PDF", r"(?i)example of (review )?paper"),
    ("unpublished system manuscript", r"papers/system/"),
    ("superseded stage code", r"(?:^|/)OLD/"),
    ("real dotenv", r"(?:^|/)\.env$"),
    ("agent bookkeeping", r"BRAIN_PENDING"),
]

# .env.example is the template and MUST ship; it holds names, never values.
ALLOW_FILE = {".env.example"}


def text_files() -> list[pathlib.Path]:
    out = []
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_DIR for part in p.parts):
            continue
        if p.suffix.lower() in BINARY_EXT:
            continue
        if p.resolve() == pathlib.Path(__file__).resolve():
            continue          # this file contains the patterns themselves
        out.append(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", metavar="PATH")
    a = ap.parse_args()

    if not (ROOT / "reproduce.py").exists():
        print(f"FAIL: {ROOT} has no reproduce.py, so it is not a built public "
              "tree. Run this inside the tree, not the private repo.",
              file=sys.stderr)
        return 2

    findings: list[dict] = []

    # 1. forbidden paths
    for p in ROOT.rglob("*"):
        if not p.is_file() or any(part in SKIP_DIR for part in p.parts):
            continue
        rel = p.relative_to(ROOT).as_posix()
        if p.name in ALLOW_FILE:
            continue
        for label, pat in FORBIDDEN_PATHS:
            if re.search(pat, rel):
                findings.append({"kind": "forbidden-path", "what": label,
                                 "file": rel})

    # 2. content scan
    files = text_files()
    for p in files:
        rel = p.relative_to(ROOT).as_posix()
        try:
            txt = p.read_text(encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, OSError):
            continue
        for i, line in enumerate(txt.splitlines(), 1):
            if len(line) > 4000:
                line = line[:4000]
            for label, pat in SECRET_PATTERNS:
                if re.search(pat, line):
                    findings.append({
                        "kind": "secret", "what": label, "file": rel,
                        "line": i,
                        # Never echo the match itself into a report that may
                        # get pasted into a chat or an issue.
                        "excerpt": "[REDACTED]"})
            for label, pat in PATH_PATTERNS:
                m = re.search(pat, line)
                if m:
                    findings.append({"kind": "host-path", "what": label,
                                     "file": rel, "line": i,
                                     "excerpt": m.group(0)[:120]})

    secrets = [f for f in findings if f["kind"] == "secret"]
    paths = [f for f in findings if f["kind"] == "host-path"]
    forbidden = [f for f in findings if f["kind"] == "forbidden-path"]

    print(f"ship_audit: {len(files)} text files scanned in {ROOT}")
    print(f"  credential patterns : {len(secrets)}")
    print(f"  host absolute paths : {len(paths)}")
    print(f"  forbidden paths     : {len(forbidden)}")

    for group, title in ((secrets, "CREDENTIALS"),
                         (forbidden, "FORBIDDEN PATHS"),
                         (paths, "HOST PATHS")):
        if not group:
            continue
        print(f"\n{title}:")
        # Collapse by file so one noisy file does not produce 400 lines.
        byfile: dict[str, list[dict]] = {}
        for f in group:
            byfile.setdefault(f["file"], []).append(f)
        for fn, items in sorted(byfile.items()):
            lines = ", ".join(str(i.get("line", "-")) for i in items[:8])
            more = f" (+{len(items) - 8} more)" if len(items) > 8 else ""
            print(f"  {fn}: {items[0]['what']} at line {lines}{more}")
            if items[0]["kind"] == "host-path":
                print(f"      e.g. {items[0]['excerpt']}")

    if a.json:
        pathlib.Path(a.json).write_text(
            json.dumps({"ok": not findings, "files_scanned": len(files),
                        "findings": findings}, indent=1), encoding="utf-8")
        print(f"\nreport written to {a.json}")

    if secrets or forbidden:
        print("\nDO NOT PUSH. Credentials or forbidden files are present.\n"
              "A secret pushed once is burned even if the commit is deleted: "
              "forks and mirrors cache within minutes. Rotate anything that "
              "appeared here.")
        return 1
    if paths:
        print("\nNo credentials and no forbidden files. Host absolute paths "
              "are present; they leak the authoring machine's layout but no "
              "secret. Clean them or accept them deliberately.")
        return 1
    print("\nClean. Safe to initialise git and push.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
