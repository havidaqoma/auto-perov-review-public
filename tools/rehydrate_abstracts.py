"""rehydrate_abstracts.py: rebuild the abstract payloads we cannot redistribute.

Why this exists
---------------
Claim-card verification compares an extracted value against the exact quoted
span in the source abstract. That needs the abstract text. We do not hold a
licence to republish publisher abstracts, so this repository ships a per-work
sha256 digest instead of the text (`private/ABSTRACTS_DIGEST_*.json`).

This script fetches the abstracts again from OpenAlex, rebuilds the plain text
by the same inversion the pipeline uses, and checks every row against the
shipped digest. When it finishes clean, you hold a byte-identical copy of the
corpus the results were computed from, and the full-text anchor verification
becomes available:

    python scripts/verify_anchors.py 2026-08

Any row whose hash does not match is reported, not silently accepted. A
mismatch usually means the publisher revised the abstract after our harvest,
which is a real finding about the corpus rather than a bug here.

Network and courtesy
--------------------
OpenAlex asks for a mailto so they can contact heavy users. Set
OPENALEX_MAILTO or CROSSREF_MAILTO in .env. Requests are batched 50 works at
a time with a pause between pages.

Usage
-----
    python tools/rehydrate_abstracts.py --all
    python tools/rehydrate_abstracts.py --period 2026-08
    python tools/rehydrate_abstracts.py --all --dry-run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import sys
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
# The tree mirrors the private repo: monthly + half-year at the root, yearly
# under yearly/. Both hold their own runs/ directory.
BASES = [ROOT, ROOT / "yearly"]
API = "https://api.openalex.org/works"
PAGE = 50


def mailto() -> str:
    for k in ("OPENALEX_MAILTO", "CROSSREF_MAILTO", "UNPAYWALL_EMAIL"):
        v = os.environ.get(k)
        if v and "@" in v:
            return v
    env = ROOT / ".env"
    if env.exists():
        for ln in env.read_text(encoding="utf-8").splitlines():
            if "=" in ln and not ln.strip().startswith("#"):
                k, _, v = ln.partition("=")
                if k.strip() in ("OPENALEX_MAILTO", "CROSSREF_MAILTO",
                                 "UNPAYWALL_EMAIL") and "@" in v:
                    return v.strip()
    print("FAIL: no mailto found. OpenAlex asks every client to identify "
          "itself. Set OPENALEX_MAILTO in .env (see .env.example).",
          file=sys.stderr)
    raise SystemExit(2)


def invert(inv: dict | None) -> str:
    """OpenAlex abstract_inverted_index -> plain text.

    Identical to scripts/stages/util.py. Duplicated on
    purpose: this tool must work in a tree where the stage package has not
    been put on sys.path, and a wrong import here would produce text that
    fails the hash check for a reason unrelated to the corpus.
    """
    if not inv:
        return ""
    pos: list[tuple[int, str]] = []
    for word, idxs in inv.items():
        for i in idxs:
            pos.append((i, word))
    pos.sort()
    return " ".join(w for _, w in pos)


def fetch(ids: list[str], mt: str) -> dict[str, str]:
    """work_id -> reconstructed abstract text."""
    out: dict[str, str] = {}
    for i in range(0, len(ids), PAGE):
        chunk = ids[i:i + PAGE]
        q = urllib.parse.urlencode({
            "filter": "openalex_id:" + "|".join(chunk),
            "select": "id,abstract_inverted_index",
            "per-page": str(PAGE),
            "mailto": mt,
        })
        req = urllib.request.Request(
            f"{API}?{q}", headers={"User-Agent": f"auto-perov-review ({mt})"})
        with urllib.request.urlopen(req, timeout=90) as fh:
            data = json.loads(fh.read().decode("utf-8"))
        for r in data.get("results", []):
            out[r["id"]] = invert(r.get("abstract_inverted_index"))
        print(f"    fetched {min(i + PAGE, len(ids))}/{len(ids)}")
        time.sleep(1.0)
    return out


def digests(base: pathlib.Path) -> list[pathlib.Path]:
    return sorted((base / "runs").rglob("ABSTRACTS_DIGEST_*.json"))


def work_ids_for(rd: pathlib.Path) -> dict[str, str]:
    """work_key -> OpenAlex id, read from the shipped corpus records."""
    m: dict[str, str] = {}
    for name in ("05_corpus.jsonl", "02_records.jsonl"):
        p = rd / name
        if not p.exists():
            continue
        with p.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                wk, oid = d.get("work_key"), d.get("openalex_id")
                if wk and oid and wk not in m:
                    m[wk] = oid
        if m:
            break
    return m


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--period")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not (a.all or a.period):
        ap.error("pass --all or --period")

    mt = "dry-run@example.org" if a.dry_run else mailto()
    total_rows = total_ok = total_bad = total_unresolved = 0

    for base in BASES:
        if not base.is_dir():
            continue
        for dig_p in digests(base):
            rd = dig_p.parent.parent
            if a.period and a.period not in rd.name:
                continue
            dig = json.loads(dig_p.read_text(encoding="utf-8"))
            want = {r["work_key"]: r["abstract_sha256"] for r in dig["digest"]}
            print(f"[{base.name}/{rd.name}] {dig_p.name}: {len(want)} rows")
            if a.dry_run:
                total_rows += len(want)
                continue

            idmap = work_ids_for(rd)
            ids = [idmap[k] for k in want if k in idmap]
            unresolved = [k for k in want if k not in idmap]
            if unresolved:
                print(f"    {len(unresolved)} work_keys have no openalex_id "
                      "in the shipped records and cannot be refetched")
            got = fetch(ids, mt) if ids else {}

            rows, ok, bad = [], 0, []
            rev = {v: k for k, v in idmap.items()}
            for oid, text in got.items():
                wk = rev.get(oid)
                if not wk:
                    continue
                h = hashlib.sha256(text.encode("utf-8")).hexdigest()
                if h == want.get(wk):
                    ok += 1
                    rows.append({"work_key": wk, "abstract": text})
                else:
                    bad.append({"work_key": wk, "expected": want.get(wk),
                                "got": h, "chars": len(text)})

            stem = dig_p.name.replace("ABSTRACTS_DIGEST_", "").replace(
                ".json", ".jsonl")
            out_p = dig_p.parent / stem
            with out_p.open("w", encoding="utf-8", newline="\n") as fh:
                for r in rows:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"    wrote {out_p.name}: {ok} verified, {len(bad)} hash "
                  f"mismatches, {len(unresolved)} unresolved")
            if bad:
                (dig_p.parent / f"MISMATCH_{stem}.json").write_text(
                    json.dumps(bad, indent=1), encoding="utf-8")
                print("    mismatches written to "
                      f"MISMATCH_{stem}.json -- the publisher most likely "
                      "revised these abstracts after our harvest")
            total_rows += len(want)
            total_ok += ok
            total_bad += len(bad)
            total_unresolved += len(unresolved)

    if a.dry_run:
        print(f"\ndry run: {total_rows} abstract rows would be refetched")
        return 0
    print(f"\n{total_ok}/{total_rows} abstracts verified against the shipped "
          f"digest; {total_bad} mismatched; {total_unresolved} unresolvable")
    return 1 if (total_bad or not total_ok) else 0


if __name__ == "__main__":
    raise SystemExit(main())
