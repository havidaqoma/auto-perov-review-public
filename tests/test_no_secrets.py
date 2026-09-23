"""R20 leak class as a permanent gate: run on every commit, not by memory."""
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
KEY_LIKE = re.compile(r"""(?:api_key|apikey|token|secret)\s*=\s*["'][A-Za-z0-9_\-]{16,}["']""", re.I)
SK_PREFIX = re.compile(r"\b(?:sk-|s2k-|eyJ)[A-Za-z0-9_\-]{16,}")

SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "node_modules", "OLD",
             "archive"}


def _walk() -> list[str]:
    """Filesystem fallback for a tree that is not a git checkout.

    The public release tree is built by copying files, so it has no .git until
    the operator initialises one. Asserting on `git ls-files` there fails for a
    reason that has nothing to do with secrets, which would train a reader to
    ignore this gate. So it falls back to walking instead of erroring.
    """
    out = []
    for p in ROOT.rglob("*"):
        if not p.is_file() or any(d in SKIP_DIRS for d in p.parts):
            continue
        out.append(p.relative_to(ROOT).as_posix())
    return out


def _tracked() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
    if out.returncode != 0:
        return _walk()
    files = [p for p in out.stdout.splitlines() if p]
    return files or _walk()


def test_no_env_file_tracked():
    tracked = _tracked()
    assert not any(p == ".env" or p.endswith("/.env") for p in tracked)
    assert ".env.example" in tracked  # the template is committed


def test_no_key_shaped_literals_in_tracked():
    bad = []
    for p in _tracked():
        if not p.endswith((".py", ".yaml", ".yml", ".md", ".txt", ".example", ".json")):
            continue
        fp = ROOT / p
        if not fp.exists():
            continue
        body = fp.read_text(encoding="utf-8", errors="replace")
        if KEY_LIKE.search(body) or SK_PREFIX.search(body):
            bad.append(p)
    assert bad == [], f"key-shaped literals found in: {bad}"
