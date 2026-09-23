"""v2 build: run the REAL v4 build over the device-family structure.

Same adapter technique as h1_build.py, extended for v2. Nothing about s18d
changes: it keeps all seventeen gates, the citation merge/link ordering, the
abstract placeholder boundary, the notation pass and the title grammar.

v1 (`h1_build.py`) is untouched and still builds manuscript/2026-H1_v4/.
This writes manuscript/2026-H1_v6/, so both artifacts coexist and the shipped
v1 issue stays reproducible.

What v2 must additionally do
----------------------------
- read draft_h1_v6/ instead of draft_h1/
- read 12_section_map_v6.json instead of 12_section_map.json
- inject the four generated main-text TABLES, which the writer never saw
- land in manuscript/2026-H1_v6/

Every rebinding is asserted before use: a stage that stops binding a name fails
loudly rather than silently building the wrong artifact (handbook 7.7 #6).
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
# The version suffix, defined ONCE. Every path that carries a version derives
# it from here rather than embedding "_v6" as a literal, because a literal
# joined by an f-string at run time is invisible to a rename pass: the v5->v6
# rename substituted the full string "2026-H1_v5" and never saw f"{EDITION}_v5",
# so the build resurrected a _v5 directory the rename had just moved away.
VERSION = "v6"
PERIOD_LABEL = "January-June 2026"
MONTHS = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]


def h1_dir() -> pathlib.Path:
    return RUNS / EDITION


def prepare_inputs() -> dict:
    """Make the H1 dir look like a month to s18d, using v2 inputs."""
    d = h1_dir()
    info = {}

    # Reference-list author names, unioned across the six months.
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

    # s18d reads draft_v4/. Sync from draft_h1_v6/ file-by-file: never rmtree,
    # because a stale Windows directory handle refuses os.rmdir (WinError 5).
    src, dst = d / "draft_h1_v6", d / "draft_v4"
    if not src.exists():
        raise SystemExit(f"FAIL-CLOSED: {src} missing; run h1_draft_v6 first")
    dst.mkdir(parents=True, exist_ok=True)
    keep = set()
    for f in src.iterdir():
        if f.is_file():
            shutil.copy2(f, dst / f.name)
            keep.add(f.name)
    for f in dst.iterdir():
        # A section from the v1 map would otherwise be built under v2 headings.
        if f.is_file() and f.name not in keep:
            f.unlink()
    info["drafts"] = len(list(dst.glob("sec*.md")))

    # s18d reads 12_section_map.json. That file is ALSO v1's input, so pointing
    # it at the v2 map overwrote v1's map in place -- the v1 manuscript
    # directory ended up holding a device_family map with the v2 sha, and the
    # mechanism map (sha ef27cc7244d6f5de) was gone from disk.
    #
    # Havid's instruction was explicit: do not overlap, make a v2 file. So back
    # v1's map up before swapping and restore it afterwards, and assert the
    # restore. The v1 map is also deterministically rebuildable from stats by
    # h1_section_map.py, but "recoverable in principle" is not the same as
    # "still on disk", and a caller should not have to know that.
    v1_map = d / "12_section_map.json"
    backup = d / "12_section_map_v1.json"
    if v1_map.exists() and not backup.exists():
        cur = json.loads(v1_map.read_text(encoding="utf-8"))
        if cur.get("structure") != "device_family":
            backup.write_text(json.dumps(cur, indent=2), encoding="utf-8")
            print(f"[h1v6-build] backed up v1 map (sha {cur.get('sha256')}) "
                  f"-> {backup.name}")

    v2 = json.loads((d / "12_section_map_v6.json").read_text(encoding="utf-8"))
    v1_map.write_text(json.dumps(v2, indent=2), encoding="utf-8")
    info["map_sections"] = len(v2["sections"])
    info["map_sha"] = v2["sha256"]

    # Monthly-namespace aliases for the pooled rates (see h1_stats).
    sp = d / "stats.json"
    S = json.loads(sp.read_text(encoding="utf-8"))
    for k in ("efficiency_stated", "certified"):
        src_k, dst_k = f"audit.h1.{k}.pct", f"audit.corpus.{k}.pct"
        if src_k in S and dst_k not in S:
            S[dst_k] = S[src_k]
    sp.write_text(json.dumps(S, indent=2), encoding="utf-8")
    return info


def h1_config() -> pathlib.Path:
    """Config dir carrying the H1 bands. config/gates.yaml is NEVER edited."""
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


def tables_markdown() -> str:
    """The generated main-text tables, as markdown for the manuscript body.

    The writer never sees these (handbook 0.1: format is generated, never
    model-written). A writer shown a table transcribes its numbers into prose,
    which would put the same value in two places with no gate comparing them.
    """
    from stages.h1_tables import MAIN_TABLES, to_markdown
    d = h1_dir()
    tabs = json.loads((d / "14_tables.json").read_text(encoding="utf-8"))
    out = []
    for k in MAIN_TABLES:
        if k in tabs:
            out.append(to_markdown(tabs[k]))
    return "\n\n".join(out)


# The v2 title names DEVICE FAMILIES, not mechanism axes, because that is what
# the issue is organised around. Same grammar checks as every other title: one
# colon, <=16 words, no banned term, no publication count.
#
# MODULE LEVEL, not a closure inside main(). It started as a closure and the v2
# finalize adapter could not import it, which would have meant a second copy
# for s19/s20 -- the same three-divergent-copies failure that the v1 title was
# extracted to stages/h1_title.py to prevent (handbook 7.6 #10/#12).
def derive_title_v6_standalone(month=None, sm=None) -> str:
    """Signature matches s18d.derive_title so it can be rebound in place.

    The slot names the ARGUMENT, not the section list. Havid rejected "Single
    Junctions, Tandems and Modules" (2026-09-10): it enumerates the table of
    contents and argues nothing.

    What this half year actually established, from the issue's own measured
    numbers: the certified ceiling moves with architecture (27.6% single
    junction, 30.3% all-perovskite, 33.6% hybrid tandem) and collapses with
    area (33.6% at 1 cm2 against 26.8% at 655 cm2), while only 9.1% of
    single-junction papers reported any independent certification at all. The
    frontier is therefore not a number, it is a number qualified by
    architecture, by area and by verification -- and the title says that.

    Same grammar checks as every other title: one colon, <=16 words, no banned
    term, no publication count beyond the period label itself.
    """
    from stages.s18d_build_v4 import TITLE_FRAME
    title = (f"{TITLE_FRAME} in {PERIOD_LABEL}: "
             f"The Certified Frontier From Cell to Module")
    tt = yaml.safe_load(
        (ROOT / "config" / "title_terms.yaml").read_text(encoding="utf-8"))
    banned = [x.lower() for x in tt.get("banned_in_title", [])]
    hits = [x for x in banned if x in title.lower()]
    if hits:
        raise SystemExit(f"FAIL-CLOSED title contains banned term {hits}")
    if title.count(":") != 1:
        raise SystemExit(f"FAIL-CLOSED title needs one colon: {title}")
    if len(title.split()) > tt.get("max_title_words", 16):
        raise SystemExit(f"FAIL-CLOSED title too long: {title}")
    if re.search(r"\b\d{2,}\b", title.replace(PERIOD_LABEL, "")):
        raise SystemExit("FAIL-CLOSED title carries a publication count")
    return title


def tables_for_sections(smap: dict) -> dict:
    """section id -> markdown table block.

    Assignment is by ARGUMENT, not by order: each table goes to the section
    whose claim it supports, so a reader meets the numbers where they are being
    argued about.

        T1 state of the art       -> frontier   (the cross-family comparison)
        T2 certified champions    -> frontier   (same argument, provenance)
        T3 efficiency vs area     -> mod        (the area penalty IS that section)
        T4 reporting completeness -> audit      (that section's whole subject)

    T5 (family x month) stays in the SI: it is a corpus statistic, not a
    scientific argument, by the same rule that demoted the audit bars and the
    corpus funnel (handbook 5).
    """
    from stages.h1_tables import to_markdown
    d = h1_dir()
    tabs = json.loads((d / "14_tables.json").read_text(encoding="utf-8"))

    want = {"frontier": ["T1", "T2"], "audit": ["T4"]}
    fam_want = {"mod": ["T3"]}
    out: dict[str, str] = {}
    for s in smap["sections"]:
        ids = []
        if s["role"] in want:
            ids = want[s["role"]]
        elif s["role"] == "family" and s.get("family") in fam_want:
            ids = fam_want[s["family"]]
        blocks = [to_markdown(tabs[t]) for t in ids if t in tabs]
        if blocks:
            out[s["id"]] = "\n\n".join(blocks)

    # 7.1: a zero is a bug until proven otherwise. Four tables are declared
    # main-text, so four must be placed.
    placed = sum(len(v.split("**Table ")) - 1 for v in out.values())
    if placed != 4:
        raise SystemExit(
            f"FAIL-CLOSED: {placed} tables placed, expected 4. A table that is "
            f"generated but never injected reaches no reader, and nothing else "
            f"would have caught it.")
    return out


def main() -> int:
    info = prepare_inputs()
    print(f"[h1v6-build] inputs ready: {info}", flush=True)
    cfg = h1_config()

    from stages import s18d_build_v4 as b

    for name in ("run_dir", "month_name", "load_map", "CONFIG",
                 "resolve_placeholders", "derive_title"):
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

    # {{N_MONTHS}} is H1-only; s18d's token table would fail closed on it.
    n_months = len(smap.get("months") or MONTHS)
    _resolve = b.resolve_placeholders

    def resolve_h1(ab, S, cl):
        ab = ab.replace("{{N_MONTHS}}", str(n_months))
        ab, vals, used = _resolve(ab, S, cl)
        vals["N_MONTHS"] = str(n_months)
        used.append("N_MONTHS")
        return ab, vals, used

    b.resolve_placeholders = resolve_h1

    # The v2 title lives at module level (derive_title_v6_standalone) so the
    # finalize adapter can import the SAME function for s19/s20 instead of
    # holding a second copy.
    b.derive_title = derive_title_v6_standalone

    # Inject the generated tables. Bound on the s18d MODULE, because s18d reads
    # it via globals() at assembly time -- the same rebinding technique every
    # other v2 override uses, and it leaves v1 and the monthly path with an
    # empty dict and therefore no tables at all.
    b.TABLE_FOR = tables_for_sections(smap)
    print(f"[h1v6-build] tables placed in sections: "
          f"{sorted(b.TABLE_FOR)}", flush=True)

    # Write straight into the v6 home instead of through v1's directory.
    #
    # s18d used to derive its output path from the period string, so this call
    # wrote manuscript/2026-H1_v4/ -- the SHIPPED v1 edition -- and then copied
    # the files out. v1 was left holding v6 prose until someone noticed the
    # printed NOTE and re-ran h1_build.py. That is a stale artifact created by
    # a successful build, which is the worst kind: every gate passes.
    out_dir = ROOT / "manuscript" / f"{EDITION}_{VERSION}"
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = b.build(EDITION, out_dir_override=out_dir)

    # ---- inject the generated tables + relocate to manuscript/2026-H1_v6 ----
    #
    # src_dir is where s18d WRITES (it hardcodes <edition>_v4); out_dir is the
    # v5 home. The rename pass rewrote out_dir to _v2 -> _v5 correctly, but the
    # first run after the rename still had out_dir = _v2, so the build wrote
    # _v4/ then copied to _v2/ and left STALE PDFs in _v5/ from the previous
    # build. The stale PDF carried the OLD title while the freshly generated
    # markdown carried the new one, and every gate passed because the gates
    # read the run dir, not this copy.
    #
    # That is handbook 7.6 #6 exactly: a stage that passed by examining a
    # different artifact. So out_dir is asserted against VERSION below rather
    # than trusted.
    # VERSION, never a literal suffix.
    #
    # This read f"{EDITION}_v5" and the v5->v6 rename did not catch it: the
    # rename substituted the full string "2026-H1_v5", but here the suffix is a
    # SEPARATE literal joined by an f-string at run time, so no full-string
    # search could ever see it. The build then resurrected a _v5 directory that
    # the rename had just moved away, and finalize failed looking for a file in
    # _v6 that had been written to _v5.
    #
    # Deriving the path from VERSION means the next renumbering is one constant,
    # and a literal that a rename cannot find cannot come back.
    # The copy-out from manuscript/<edition>_v4 is GONE, and must stay gone.
    # s18d now writes into out_dir directly, so copying from the v4 directory
    # would drag v1's older files ON TOP of the render that was just made:
    # the same "stage passed by examining a different artifact" defect this
    # comment block was written about, only with the arrow reversed.
    src_dir = ROOT / "manuscript" / f"{EDITION}_v4"    # v1's home, read-only here
    (out_dir / "tables.md").write_text(tables_markdown(), encoding="utf-8")
    shutil.copy2(h1_dir() / "14_tables.json", out_dir / "14_tables.json")

    # RESTORE v1's inputs and artifacts.
    #
    # s18d hardcodes outdir = manuscript/<edition>_v4, so this build writes
    # THROUGH v1's directory on its way to _v2. Havid's instruction was "don't
    # overlap, make a v2 file", so v1 is put back exactly as it was and the
    # restore is asserted rather than assumed.
    d = h1_dir()
    backup = d / "12_section_map_v1.json"
    if backup.exists():
        v1m = json.loads(backup.read_text(encoding="utf-8"))
        (d / "12_section_map.json").write_text(json.dumps(v1m, indent=2),
                                               encoding="utf-8")
        # v1's manuscript dir must carry the MECHANISM map, not this one.
        shutil.copy2(backup, src_dir / "12_section_map.json")
        back = json.loads((d / "12_section_map.json").read_text(encoding="utf-8"))
        if back.get("structure") == "device_family":
            raise SystemExit(
                "FAIL-CLOSED: v1 section map was not restored; v1 and v2 "
                "would share one map file.")
        print(f"[h1v6-build] restored v1 map (sha {back.get('sha256')})")

    # v1's PDF is rebuilt by h1_build.py, which is deterministic given its own
    # drafts and map. Say so plainly rather than leaving a stale v2 PDF sitting
    # in the v1 directory pretending to be v1.
    print(f"[h1v6-build] NOTE: manuscript/{EDITION}_v4/ currently holds this "
          f"v2 render because s18d writes there. Run "
          f"`python scripts/stages/h1_build.py` to restore the v1 artifact.")
    print(f"[h1v6-build] v2 artifacts -> {out_dir}")
    print(json.dumps(meta, indent=2)[:2500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
