"""Repo-local .env loader. Values are never printed, never committed."""
from __future__ import annotations

import os
import pathlib

SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
ROOT = SCRIPTS.parent

# parents[1] is scripts/, NOT the repo root, so the original
#     ROOT = pathlib.Path(__file__).resolve().parents[1]
#     p = ROOT / ".env"
# looked for scripts/.env, which does not exist in either repo. `.env` lives
# at the repo root, so load_env() found nothing and returned silently --
# every OpenAlex call has always been ANONYMOUS, in this project and in the
# monthly one, despite a populated .env sitting on disk.
#
# It failed silently because the loader treats "no file" as "nothing to do",
# which is correct behaviour for an absent .env and indistinguishable from
# looking in the wrong place. Nothing downstream complains: net.py appends
# the key only `if key`, so an empty key degrades to an anonymous request
# that still returns 200. The only symptom is a lower rate limit.
#
# Root is checked FIRST so the real file wins; scripts/ is kept as a
# fallback so any environment that did place one there is not broken.
_CANDIDATES = (ROOT / ".env", SCRIPTS / ".env")


def load_env() -> None:
    p = next((c for c in _CANDIDATES if c.exists()), None)
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
