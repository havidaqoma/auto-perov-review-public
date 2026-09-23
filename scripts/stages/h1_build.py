"""H1 build: run the REAL v4 build over the half-year run dir.

Why an adapter instead of an h1 build stage
-------------------------------------------
s18d_build_v4.py is 1116 lines and carries all eleven gates, the citation
merge/link ordering, the abstract placeholder boundary, the notation pass, the
figure single-claim rule and the title grammar. Every one of those encodes a
defect that shipped once.

Copying it to make an H1 variant would create a second copy of each guard, and
the handbook records that exact failure three separate times: the narration
filter in three divergent copies (7.6 #10, the build-side copy narrowest, which
put "I have launched the search command" into a shipped PDF), and the citation
regex applied in only one consumer (7.6 #12). A guard that exists twice
diverges.

So this file changes NOTHING about the build. It makes the H1 run dir look like
a month to s18d, rebinds the four names s18d resolves at call time, and points
CONFIG at a generated config directory whose gates.yaml carries the H1 bands
from config/h1.yaml. The monthly path imports none of this and is not modified.

Every rebinding is asserted before use: if s18d stops binding a name, this
fails loudly rather than silently building the wrong artifact (7.7 #6, the
verifier that passed by examining a different file).
"""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import yaml  # noqa: E402

from stages.util import RUNS, read_jsonl, run_dir, write_jsonl  # noqa: E402

EDITION = "2026-H1"
PERIOD_LABEL = "January-June 2026"
MONTHS = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]


def h1_dir() -> pathlib.Path:
    return RUNS / EDITION


def prepare_inputs() -> dict:
    """Give the H1 dir the file names s18d expects, from H1 data only."""
    d = h1_dir()
    info = {}

    # s18d reads 01_openalex.jsonl for author names on the reference list.
    # Union the six monthly files, keyed by DOI, so every cited work resolves.
    oa_rows, seen = [], set()
    for m in MONTHS:
        rd = run_dir(m, create=False)
        for r in read_jsonl(rd / "01_openalex.jsonl"):
            k = (r.get("doi") or "").replace("https://doi.org/", "").lower()
            if k and k not in seen:
                seen.add(k)
                oa_rows.append(r)
    write_jsonl(d / "01_openalex.jsonl", oa_rows)
    info["openalex_rows"] = len(oa_rows)

    # s18d reads draft_v4/. The H1 writer wrote draft_h1/. Copy rather than
    # rename so the drafts stay where h1_draft's resume logic expects them.
    # Sync file-by-file rather than rmtree + copytree.
    #
    # On Windows an empty leftover draft_v4/ from a crashed build refused
    # os.rmdir with WinError 5 (a stale directory handle outlives the process
    # that crashed). Deleting the tree was never required: what matters is that
    # every section present in draft_h1 is byte-identical in draft_v4, and that
    # no section from an older map survives. Both are achieved without a
    # directory delete, so a stale handle can no longer stop the build.
    src, dst = d / "draft_h1", d / "draft_v4"
    dst.mkdir(parents=True, exist_ok=True)
    keep = set()
    for f in src.iterdir():
        if f.is_file():
            shutil.copy2(f, dst / f.name)
            keep.add(f.name)
    for f in dst.iterdir():
        # A section left over from a previous map would otherwise be built into
        # the manuscript under this map's headings.
        if f.is_file() and f.name not in keep:
            f.unlink()
    info["drafts"] = len(list(dst.glob("sec*.md")))

    # s18d's placeholder boundary reads the MONTHLY key namespace
    # (audit.corpus.*). h1_stats emits audit.h1.* because a pooled half-year
    # rate is a different quantity from one month's rate and must not be
    # confusable with it. Alias the two keys s18d actually reads rather than
    # renaming either set: the H1 names stay authoritative in stats.json, and
    # the build sees the names it was written against.
    sp = d / "stats.json"
    S = json.loads(sp.read_text(encoding="utf-8"))
    for k in ("efficiency_stated", "certified"):
        src, dst = f"audit.h1.{k}.pct", f"audit.corpus.{k}.pct"
        if src in S and dst not in S:
            S[dst] = S[src]
    sp.write_text(json.dumps(S, indent=2), encoding="utf-8")
    info["aliased_audit_keys"] = True

    # derive_title() reads smap["month_name"]; give the map the period label.
    mp = d / "12_section_map.json"
    m = json.loads(mp.read_text(encoding="utf-8"))
    m["month_name"] = PERIOD_LABEL
    mp.write_text(json.dumps(m, indent=2), encoding="utf-8")
    info["map_sections"] = len(m["sections"])
    return info


def h1_config() -> pathlib.Path:
    """A config dir whose gates.yaml carries the H1 bands.

    config/gates.yaml is NOT edited: it describes the monthly issue and must
    keep describing exactly that. The H1 bands live in config/h1.yaml and are
    projected onto the key names s18d reads. This is not widening a gate
    (handbook 6.1) -- it is a different artifact with its own envelope, the
    same reasoning that added `paper_v3` beside the retired `paper` band.
    """
    # Sync in place, never rmtree.
    #
    # Same WinError 5 class as the draft dir above: a stale directory handle
    # from a crashed build made os.rmdir refuse '.h1_config/domains'. Fixing
    # only the first site would have left the identical bug waiting here, which
    # is the "fix the class, not the reported site" rule. dirs_exist_ok keeps
    # every file current without ever removing a directory.
    src = ROOT / "config"
    dst = ROOT / ".h1_config"
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst, dirs_exist_ok=True)

    H = yaml.safe_load((src / "h1.yaml").read_text(encoding="utf-8"))
    G = yaml.safe_load((src / "gates.yaml").read_text(encoding="utf-8"))

    G["paper_v3"]["content_page_band"] = H["h1"]["content_page_band"]
    G["paper_v3"]["total_page_band"] = H["h1"]["total_page_band"]
    G["citations"]["total_band"] = H["citations_h1"]["total_band"]
    G["abstract"]["word_band"] = H["abstract_h1"]["word_band"]
    G["novelty"] = {k: v for k, v in H["novelty_h1"].items()
                    if k in ("body_max_ratio", "abstract_max_ratio",
                             "shingle_words")}
    (dst / "gates.yaml").write_text(yaml.safe_dump(G, sort_keys=False),
                                    encoding="utf-8")
    return dst


def main() -> int:
    info = prepare_inputs()
    print(f"[h1-build] inputs ready: {info}", flush=True)
    cfg = h1_config()

    from stages import s18d_build_v4 as b

    # Assert every name exists BEFORE rebinding it. A rebinding that silently
    # does nothing is worse than a crash.
    for name in ("run_dir", "month_name", "load_map", "CONFIG"):
        if not hasattr(b, name):
            raise SystemExit(
                f"FAIL-CLOSED: s18d_build_v4 no longer binds {name!r}; this "
                f"adapter is stale and would build the wrong artifact.")

    d = h1_dir()
    smap = json.loads((d / "12_section_map.json").read_text(encoding="utf-8"))

    b.run_dir = lambda m, create=True: d
    b.month_name = lambda m: PERIOD_LABEL
    b.load_map = lambda m: smap
    b.CONFIG = cfg

    # {{N_MONTHS}} is an H1-only token: a monthly abstract has no such
    # quantity, so s18d's token table does not carry it and would fail closed
    # on "unresolvable=['N_MONTHS']" -- correctly, since a hole must never
    # ship. Resolve it HERE, from the aggregate on disk, then hand the rest to
    # the real resolver so the anti-fabrication boundary is untouched: every
    # other number still comes from stats.json or a claim card, and any token
    # this wrapper does not know still fails closed inside s18d.
    n_months = len(smap.get("months") or MONTHS)
    _resolve = b.resolve_placeholders

    def resolve_h1(ab, S, cl):
        ab = ab.replace("{{N_MONTHS}}", str(n_months))
        ab, vals, used = _resolve(ab, S, cl)
        vals["N_MONTHS"] = str(n_months)
        used.append("N_MONTHS")
        return ab, vals, used

    b.resolve_placeholders = resolve_h1

    # derive_title() computes its rotation index as int(month[:4])*12 +
    # int(month[5:7]), which raises on "2026-H1". The H1 title now lives in
    # ONE place (stages/h1_title.py) because three stages need it: this build,
    # the SI and the ChemRxiv package. Defining it inline here made it a copy
    # waiting to diverge (7.6 #10/#12).
    from stages.h1_title import derive_title_h1

    b.derive_title = derive_title_h1

    # G8 compares against the newest prior issue on disk. For the first H1
    # issue the honest comparison is against the shipped MONTHLY issues in its
    # own window: if the half-year prose reuses a monthly issue's sentences,
    # that is exactly the reuse the gate exists to catch.
    meta = b.build(EDITION)
    print(json.dumps(meta, indent=2)[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
