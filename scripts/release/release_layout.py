"""release_layout: the public tree ships the FINAL edition of each period, unversioned.

Why this exists
---------------
The private repo keeps every edition an issue went through (2026-07 has v2,
v3, v4 and v5) because the audit trail is the point of a private record. A
reader of the public repository needs the opposite: one paper per period, the
one that is final, with no guessing which of four folders to open. Shipping
all of them also let a superseded file sit next to its replacement under a
confusable name: 2026-H1's final edition held a stale `supplementary_v4.md`
beside `supplementary_v6.md`, and a count read from the wrong one looked like
a real defect.

So the release is declared here as data:

* FINAL names the edition that ships per period. Every other edition folder
  is dropped.
* Output files and folders lose their version token (`manuscript_v5.md` ->
  `manuscript.md`, `manuscript/2026-07_v5/` -> `manuscript/2026-07/`,
  `draft_v4/` -> `draft/`).
* Pipeline STEP names keep theirs (`s18d_build_v4.py`, `18d_build_v4.done`,
  the `18c_build_v3` rows of a token ledger). They name code, not an edition,
  and the public code has to stay line-for-line comparable with the private
  repo that produced the artifacts.

The rename is applied to paths AND to the text that points at them, and the
full map is written into the tree (verification/release_renames.json) so a
reader who wants to re-run a step can put the step's own input names back
with tools/stage_inputs.py.
"""
from __future__ import annotations

import gzip
import io
import json
import pathlib
import re
import tarfile

# period -> (private edition folder, private run folder, final version)
FINAL: dict[str, tuple[str, str, str]] = {
    "2026-06": ("2026-06_v4", "2026-06_cf764cbb", "v4"),
    "2026-07": ("2026-07_v5", "2026-07_197abe83", "v5"),
    "2026-08": ("2026-08_v5", "2026-08_b086357d", "v5"),
    "2026-H1": ("2026-H1_v6", "2026-H1", "v6"),
}

# The final draft cache per run. The v5 monthly editions revised the ASSEMBLED
# markdown only, so their drafts are still the v4 build's.
FINAL_DRAFT = {"2026-06_cf764cbb": "draft_v4", "2026-07_197abe83": "draft_v4",
               "2026-08_b086357d": "draft_v4", "2026-H1": "draft_h1_v6"}

# Run folders dropped whole. 2026-07_51e6c170 is an abandoned July run left
# when a gates.yaml edit changed the run hash between stage 06 and stage 04
# (scripts/stages/util.py); no edition was ever built from it.
DROP_RUNS = {"2026-07_51e6c170"}

# Explicit per-file decisions that the general rules below cannot make.
# None = drop. Paths are relative to the private repo root.
EXPLICIT: dict[str, str | None] = {
    # H1: s18d always writes *_v4 names, so the final v6 edition carries the
    # v6 paper under v4 names. manuscript_v4.md IS the v6 text (same bytes as
    # runs/2026-H1/manuscript_v6.md) and gate_report_v4.json IS its report.
    "manuscript/2026-H1_v6/manuscript_v4.md": "manuscript/2026-H1/manuscript.md",
    "manuscript/2026-H1_v6/gate_report_v4.json": "manuscript/2026-H1/gate_report.json",
    # Byte-identical duplicate of manuscript_v6.pdf.
    "manuscript/2026-H1_v6/manuscript_v4.pdf": None,
    # The superseded v1 SI and the v1 package copies.
    "manuscript/2026-H1_v6/supplementary_v4.md": None,
    "manuscript/2026-H1_v6/supplementary_v4.pdf": None,
    "manuscript/2026-H1_v6/chemrxiv/manuscript_v4.pdf": None,
    "manuscript/2026-H1_v6/chemrxiv/supplementary_v4.pdf": None,
    # H1 run: the v6 map and draft index replace the v1 ones of the same stem.
    "runs/2026-H1/12_section_map.json": None,
    "runs/2026-H1/12_section_map_v1.json": None,
    "runs/2026-H1/12_section_map_v6.json": "runs/2026-H1/12_section_map.json",
    "runs/2026-H1/13_draft_h1.json": None,
    "runs/2026-H1/13_draft_h1_v6.json": "runs/2026-H1/13_draft_h1.json",
    "runs/2026-H1/stats_v1_backup.json": None,
    # The format exemplar is a different paper, not an edition of this one.
    "manuscript/example_manuscript_v2.md": "manuscript/example_manuscript.md",
    "manuscript/example_manuscript_v2.pdf": "manuscript/example_manuscript.pdf",
    # Style-contract snapshots of the final July and August prose.
    "runs/_style_contract/julv5.json": "runs/_style_contract/jul.json",
    "runs/_style_contract/augv5.json": "runs/_style_contract/aug.json",
    # The planning document that the handbooks superseded.
    "PLAN_monthly_perovskite_review_v5.md": "PLAN_monthly_perovskite_review.md",
    # The per-edition revision notes.
    "manuscript/2026-07_v5/V5_NOTE.md": "manuscript/2026-07/REVISION_NOTE.md",
    "manuscript/2026-08_v5/V5_NOTE.md": "manuscript/2026-08/REVISION_NOTE.md",
}

# Stamps of retired stage versions (their code is not shipped: OLD/ is
# excluded). The current step stamps (13d_draft_v4.done, 18d_build_v4.done)
# are step names and stay. The last entry is the stamp of the retired
# preprint stage (replaced by s20_chemrxiv); it points at a package that does
# not ship.
RETIRED_STAMPS = {"13b_draft_v2.done", "13c_draft_v3.done",
                  "18b_build_v2.done", "18c_build_v3.done",
                  "13_draft.done", "18_build.done", "12_brief.done",
                  "20_arxiv.done"}  # superseded by 20_chemrxiv.done

# Unversioned outputs that belong to a retired edition, not to the final one.
# July's first (v1) build wrote them without a version token, so the name
# rules cannot tell them from final outputs. None of them is read by shipped
# code: the final edition's figures are F1_certified_frontier..F4_stability_
# evidence and its manuscript/gate report are the renamed v5 ones.
RETIRED_OUTPUTS = {
    "runs/2026-07_197abe83/" + n for n in (
        "12_brief.json", "18_input_freeze.json", "references.bib",
        "gate_report.json", "manuscript.md", "supplementary.md",
        "fig/F1_axis_shares.pdf", "fig/F2_reporting_audit.pdf",
        "fig/F3_claim_vs_check.pdf", "fig/F4_corpus_funnel.pdf")
} | {"runs/2026-07_197abe83/draft/" + f"sec{i}.md" for i in range(1, 9)}
# manuscript/2026-07/ (no version) is the v1 July edition folder, and
# runs/2026-H1/draft_h1/ is the v1 H1 draft cache that draft_h1_v6/ replaced.
RETIRED_EDITION_DIRS = ("manuscript/2026-07/", "runs/2026-H1/draft_h1/")

_EDITION_DIR = re.compile(r"^manuscript/(\d{4}-(?:\d{2}|H1))_v\d+/")
_OUTPUT = re.compile(
    r"^(?P<stem>manuscript|supplementary|gate_report)_(?P<ver>v\d+)(?P<ext>\.\w+)$")
_DRAFT_DIR = re.compile(r"^(draft(?:_h1)?)_v\d+$")

# A versioned OUTPUT name, used to prove nothing slipped through. Step names
# (sNN_*_vN.py, NN*_vN.done) are matched separately and allowed.
VERSIONED = re.compile(r"(^|[_./-])v\d+([_./-]|$)")
STEP_NAME = re.compile(
    r"(^|/)(s\d+[a-z]?_[a-z0-9_]+_v\d+\.py|\d+[a-z]?_[a-z0-9_]+_v\d+\.done|"
    r"h1_[a-z0-9_]+_v\d+\.py|test_[a-z0-9_]+_v\d+\.py|"
    r"render_v\d+\.py|_v\d+_clobber_audit\.py|archive_h1_v\d+\.py|"
    r"rename_v\d+_to_v\d+\.py|probe_h1v\d+_[a-z_]+\.py|"
    r"MASTER_HANDBOOK_YEARLY_v\d+\.md)$")

_final_editions = {e: (p, v) for p, (e, _, v) in FINAL.items()}
_final_runs = {r: (p, v) for p, (_, r, v) in FINAL.items()}


def is_step_name(rel: str) -> bool:
    return bool(STEP_NAME.search(rel))


def public_path(rel: str) -> str | None:
    """Map a private path to its public path, or None to drop it."""
    if rel in EXPLICIT:
        return EXPLICIT[rel]
    if rel in RETIRED_OUTPUTS or rel.startswith(RETIRED_EDITION_DIRS):
        return None

    m = _EDITION_DIR.match(rel)
    if m:
        edition = rel.split("/")[1]
        if edition not in _final_editions:
            return None                       # a superseded edition
        period, ver = _final_editions[edition]
        rest = rel[len(f"manuscript/{edition}/"):]
        if rest == "chemrxiv/manuscript.pdf":
            # s20's LaTeX compile check, not the paper: the upload is the
            # built manuscript_vN.pdf, which takes this name once unversioned.
            # tex_compiles is recorded in submission_metadata and the stamp.
            return None
        parts = rest.split("/")
        o = _OUTPUT.match(parts[-1])
        if o:
            if o["ver"] != ver:
                return None                   # a superseded output
            parts[-1] = o["stem"] + o["ext"]
        return "/".join(["manuscript", period] + parts)

    if rel.startswith("runs/"):
        parts = rel.split("/")
        run = parts[1] if len(parts) > 2 else None
        if run in DROP_RUNS:
            return None
        if run in _final_runs:
            _, ver = _final_runs[run]
            name = parts[-1]
            if len(parts) == 3 and name in RETIRED_STAMPS:
                return None
            if len(parts) >= 4 and _DRAFT_DIR.match(parts[2]):
                if parts[2] != FINAL_DRAFT[run]:
                    return None               # a superseded draft cache
                parts[2] = _DRAFT_DIR.match(parts[2])[1]
            elif len(parts) == 3:
                o = _OUTPUT.match(name)
                if o:
                    if o["ver"] != ver:
                        return None
                    parts[-1] = o["stem"] + o["ext"]
            return "/".join(parts)
    return rel


def text_rewrites(rel_public: str) -> list[tuple[re.Pattern, str]]:
    """Substitutions that make a shipped file point at the renamed paths.

    Scoped per file: inside the final July edition, `manuscript_v5.pdf` means
    July's final paper and becomes `manuscript.pdf`; a July run stamp that
    names the retired `2026-07_v4` folder is history and is left alone.
    """
    subs: list[tuple[re.Pattern, str]] = []
    sep = r"(?<![A-Za-z0-9_-])"
    end = r"(?![A-Za-z0-9_])"
    for period, (edition, run, ver) in FINAL.items():
        subs.append((re.compile(sep + re.escape(edition) + end), period))
    owner = None
    for period, (edition, run, ver) in FINAL.items():
        if (rel_public.startswith(f"manuscript/{period}/")
                or rel_public.startswith(f"runs/{run}/")):
            owner = (period, edition, run, ver)
    if owner:
        _, _, run, ver = owner
        for stem in ("manuscript", "supplementary", "gate_report"):
            subs.append((re.compile(sep + stem + "_" + ver + r"(?=\.\w)"), stem))
        if run == "2026-H1":
            # See EXPLICIT: s18d's *_v4 names carry the v6 paper here.
            for stem in ("manuscript", "gate_report"):
                subs.append((re.compile(sep + stem + r"_v4(?=\.\w)"), stem))
        draft = FINAL_DRAFT[run]
        subs.append((re.compile(sep + re.escape(draft) + end),
                     _DRAFT_DIR.match(draft)[1]))
    return subs


def rewrite_text(rel_public: str, text: str) -> tuple[str, int]:
    """Rewrite references to renamed paths inside one shipped DATA/DOC file.

    Python source is never rewritten: a regex edit to code is an unreviewed
    code change, and it made public tests diverge from the private ones in
    ways neither tree tested. Code finds editions through
    scripts/stages/editions.py, which reads either layout.
    """
    if rel_public.endswith(".py"):
        return text, 0
    n = 0
    for pat, repl in text_rewrites(rel_public):
        text, k = pat.subn(repl, text)
        n += k
    return text, n


def repack_tarball(data: bytes, rel_public: str) -> bytes:
    """Rename the members of a ChemRxiv tarball and rewrite its text members.

    Member order, modes and mtimes are kept so the archive differs from the
    private one only in the names this module changes.
    """
    src = tarfile.open(fileobj=io.BytesIO(gzip.decompress(data)), mode="r:")
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w:", format=tarfile.PAX_FORMAT) as dst:
        for m in src.getmembers():
            f = src.extractfile(m) if m.isfile() else None
            body = f.read() if f else None
            name, _ = rewrite_text(rel_public, m.name)
            if body is not None and pathlib.PurePosixPath(m.name).suffix in (
                    ".md", ".tex", ".json", ".txt", ".bib"):
                t, _ = rewrite_text(rel_public, body.decode("utf-8"))
                body = t.encode("utf-8")
            m2 = tarfile.TarInfo(name)
            m2.mode, m2.mtime, m2.type = m.mode, m.mtime, m.type
            if body is not None:
                m2.size = len(body)
                dst.addfile(m2, io.BytesIO(body))
            else:
                dst.addfile(m2)
    return gzip.compress(out.getvalue(), compresslevel=9, mtime=0)


def rename_manifest(pairs: list[tuple[str, str | None]]) -> dict:
    """The record shipped as verification/release_renames.json."""
    renamed = {a: b for a, b in pairs if b is not None and a != b}
    return {
        "note": ("The public tree ships the final edition of each period "
                 "with version tokens removed from output names. Step names "
                 "(s18d_build_v4.py, 18d_build_v4.done) are unchanged. "
                 "`renamed` maps each private path to its public path; "
                 "tools/stage_inputs.py uses it to restore the input names "
                 "a pipeline step reads before that step is re-run."),
        "final_editions": {p: {"private_edition": e, "run": r, "version": v}
                           for p, (e, r, v) in FINAL.items()},
        "renamed": dict(sorted(renamed.items())),
        "dropped_count": sum(1 for _, b in pairs if b is None),
    }


def unversioned_violations(paths: list[str]) -> list[str]:
    """Public paths that still carry a version token and are not step names."""
    return [p for p in paths if VERSIONED.search(p) and not is_step_name(p)]


if __name__ == "__main__":       # quick look at the plan without building
    import subprocess
    root = pathlib.Path(__file__).resolve().parents[2]
    files = subprocess.run(["git", "ls-files"], cwd=root, check=True,
                           capture_output=True, text=True).stdout.split()
    pairs = [(f, public_path(f)) for f in files]
    print(json.dumps({"dropped": sum(1 for _, b in pairs if b is None),
                      "renamed": sum(1 for a, b in pairs if b and a != b)}))
