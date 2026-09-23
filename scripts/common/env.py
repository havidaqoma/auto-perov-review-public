"""Repo-local .env loader. Values are never printed, never committed."""
from __future__ import annotations

import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _find_env() -> pathlib.Path | None:
    """First .env at or above scripts/.

    ROOT is scripts/, but the repo's .env lives one level up at the repo root,
    so the original `ROOT / ".env"` silently found nothing and every keyed
    request fell back to the anonymous pool. That failure is invisible: the
    OpenAlex call still succeeds until the shared anonymous pool throttles,
    and then a harvest stalls in 429 backoff with an empty log. Searching
    upward keeps the old location working and adds the real one.
    """
    for base in (ROOT, *ROOT.parents):
        p = base / ".env"
        if p.exists():
            return p
    return None


def load_env() -> None:
    p = _find_env()
    if p is None:
        return
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())


load_env()


def get(key: str, default: str | None = None, required: bool = False) -> str | None:
    v = os.environ.get(key)
    if v is None and required:
        raise RuntimeError(f"required env var missing: {key}")
    return v if v is not None else default
