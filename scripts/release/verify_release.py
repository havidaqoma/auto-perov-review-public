"""verify_release.py: the full release gate, end to end, in one command.

The step that matters here is the CLONE TEST, and it exists because of a real
defect that every other check passed.

The first release commit shipped the private repo's .gitignore. That file
carries `runs/*` with a `!runs/*/` re-include, a rule written to keep per-run
raw payloads out of the private history. In the release tree it silently
excluded the `runs/<period>.active` pointers from `git add -A`. The built
directory verified perfectly: reproduce.py returned 0, ten of ten checks
passed. A `git clone` of that same commit failed, because the pointers that
tell every stage which run directory shipped had never been committed.

The lesson is narrow and worth encoding: verifying the directory you built is
not the same as verifying what a stranger receives. Only a clone proves the
second one. So this script verifies both, and the clone is not optional.

Usage:
    python scripts/release/verify_release.py --tree auto-perov-review-public

Exit code 0 means the tree is safe to push and a clone of it reproduces.
"""
from __future__ import annotations

import argparse
import pathlib
import shutil
import stat
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]


def run(cmd: list[str], cwd: pathlib.Path) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def rmtree_retry(path: pathlib.Path, attempts: int = 6) -> None:
    """Windows holds handles briefly after writes; retry before giving up."""
    def on_error(func, p, _exc):
        try:
            pathlib.Path(p).chmod(stat.S_IWRITE)
            func(p)
        except OSError:
            pass
    for i in range(attempts):
        if not path.exists():
            return
        shutil.rmtree(path, onerror=on_error)
        if not path.exists():
            return
        time.sleep(0.5 * (i + 1))


def step(name: str, ok: bool, detail: str = "") -> bool:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    if not ok and detail:
        for line in detail.strip().splitlines()[-25:]:
            print(f"        {line}")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", required=True,
                    help="the built public tree to verify")
    ap.add_argument("--skip-clone", action="store_true",
                    help="skip the clone test (NOT recommended: the clone is "
                         "the only check that sees what a stranger receives)")
    a = ap.parse_args()

    tree = pathlib.Path(a.tree).resolve()
    if not tree.is_dir():
        print(f"verify_release: no such tree: {tree}", file=sys.stderr)
        return 2

    print(f"verify_release: {tree}\n")
    results: list[bool] = []

    # 1. The tree verifies itself, offline.
    rc, out = run([sys.executable, "reproduce.py", "--tier", "0"], tree)
    results.append(step("built tree: reproduce.py --tier 0", rc == 0, out))

    # 2. Nothing secret, nothing host-specific, nothing forbidden.
    rc, out = run([sys.executable, "tools/ship_audit.py"], tree)
    results.append(step("built tree: ship_audit.py", rc == 0, out))

    # 3. Everything the builder wrote is actually committed. This is the check
    #    the .gitignore defect defeated: files present on disk, absent from
    #    the commit, and no other check could see the difference.
    if (tree / ".git").is_dir():
        rc, out = run(["git", "status", "--porcelain", "--ignored"], tree)
        ignored = [ln[3:] for ln in out.splitlines() if ln.startswith("!!")]
        untracked = [ln[3:] for ln in out.splitlines() if ln.startswith("??")]
        # Caches are legitimately ignored; anything else is a silent drop.
        benign = ("__pycache__", ".pytest_cache", "scratch/", "repro.txt",
                  "audit.txt", ".venv", "private/01_abstracts.jsonl",
                  "private/02_abstracts.jsonl")
        dropped = [p for p in ignored + untracked
                   if not any(b in p for b in benign)]
        results.append(step(
            "built tree: no shipped file left uncommitted",
            not dropped,
            "these files are on disk but not in the commit:\n" +
            "\n".join(dropped[:25])))
    else:
        results.append(step("built tree: git repository initialised", False,
                            "no .git directory: run `git init && git add -A "
                            "&& git commit` in the tree first"))

    # 4. The clone test. Not optional, and deliberately noisy about why.
    if not a.skip_clone:
        tmp = pathlib.Path(tempfile.gettempdir()) / "release_clone_test"
        rmtree_retry(tmp)
        rc, out = run(["git", "clone", "-q", str(tree), str(tmp)], ROOT)
        cloned = step("clone: git clone succeeds", rc == 0, out)
        results.append(cloned)
        if cloned:
            rc, out = run([sys.executable, "reproduce.py", "--tier", "0"], tmp)
            results.append(step(
                "CLONE: reproduce.py --tier 0 (what a stranger receives)",
                rc == 0, out))
            rc, out = run([sys.executable, "tools/ship_audit.py"], tmp)
            results.append(step("clone: ship_audit.py", rc == 0, out))
        rmtree_retry(tmp)
    else:
        print("  [SKIP] clone test (--skip-clone)")

    passed = sum(1 for r in results if r)
    print(f"\n{passed} passed, {len(results) - passed} failed")
    if all(results):
        print("\nThe tree verifies AND a clone of it verifies. Safe to push.")
        return 0
    print("\nNOT safe to push. Fix the failures above and rebuild.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
