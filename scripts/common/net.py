"""Keyed vs plain HTTP. R20 structural fix: the OpenAlex key is appended ONLY
to api.openalex.org requests and ONLY through oa(); plain() can never see it."""
from __future__ import annotations

import re
import time
import urllib.parse

import requests

from common.env import get as env_get

OA_HOST = "api.openalex.org"
UA = "auto-perov-review/0.1 (mailto:%s)" % (env_get("CROSSREF_MAILTO", "noreply@example.com"))

# R34: anything that may be written to a log, a probe note, or an exception must
# pass through redact() first. api_key is the obvious one; email= is NOT a secret
# but Unpaywall carries it in the query string, and a probe note pasted into
# docs/PROBES_v5.md would publish Havid's address into a repo whose whole history
# T-47 scans before release. Redaction is mechanical, never left to the writer.
_REDACT_PARAMS = ("api_key", "email", "mailto", "token", "key", "api-key")


def redact(text: str) -> str:
    """Mask secret-shaped and PII-shaped query params in any string."""
    if not text:
        return text
    out = str(text)
    for p in _REDACT_PARAMS:
        out = re.sub(
            r"(?i)\b%s=([^&\s'\"]+)" % re.escape(p), r"%s=<redacted>" % p, out)
    return out


class SourceFailure(Exception):
    """Fail-closed carrier: stage name + offending URL for the operator alert (Q26=b)."""

    def __init__(self, stage: str, url: str, attempts: int, last: str):
        super().__init__(f"{stage}: {url!r} failed after {attempts} attempts: {last}")
        self.stage, self.url, self.attempts = stage, url, attempts


def _fetch(url: str, *, authed: bool, attempts: int = 4, timeout: int = 30, stage: str = "http") -> dict:
    if authed:
        p = urllib.parse.urlparse(url)
        if p.hostname != OA_HOST:
            raise AssertionError(
                f"keyed request to non-OpenAlex host '{p.hostname}' (R20); use plain()")
        key = env_get("OPENALEX_API_KEY", "")
        if key:  # anonymous (no key in .env) = same host guard, key simply absent
            q = urllib.parse.parse_qsl(p.query)
            q.append(("api_key", key))
            url = urllib.parse.urlunparse(p._replace(query=urllib.parse.urlencode(q)))
    last = ""
    for i in range(attempts):
        try:
            resp = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
            if resp.status_code == 429:
                wait = float(resp.headers.get("Retry-After", 2)) + 1
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as exc:
            if i == attempts - 1:
                raise SourceFailure(stage, url, attempts, str(exc)) from exc
            time.sleep(2 ** i)
        except requests.RequestException as exc:
            last = str(exc)
            if i == attempts - 1:
                raise SourceFailure(stage, url, attempts, last) from exc
            time.sleep(2 ** i + 0.5)
    raise SourceFailure(stage, url, attempts, last or "all attempts consumed")


def oa(url: str, **kw) -> dict:
    """OpenAlex-authenticated GET (key appended + host asserted)."""
    return _fetch(url, authed=True, **kw)


def plain(url: str, **kw) -> dict:
    """Unauthenticated GET - key structurally unreachable here."""
    return _fetch(url, authed=False, **kw)
