"""build_public_tree: assemble the public reproducibility repo from this one.

Why a script and not a one-off copy
-----------------------------------
The public tree must be rebuildable. If it is assembled by hand once, the
next person to ship a monthly issue has no way to refresh it without
re-deciding every include/exclude question, and the answers drift. So the
include list, the exclude list and the transforms are declared here as data
and the tree is a pure function of the private repo plus this file.

What it does NOT do
-------------------
No `git init`, no commit, no push. The skill's iron rule is that `.git` never
crosses into a spin-off, because history is the leak. The operator creates
the remote and pushes.

Gate on the INDEX, not the filesystem: run `python reproduce.py --tier 0`
and `scripts/ship_audit.py` in the built tree before pushing.

Usage
-----
    python scripts/release/build_public_tree.py                # default dest
    python scripts/release/build_public_tree.py --dest D:/tmp/pub
    python scripts/release/build_public_tree.py --dry-run
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import pathlib
import re
import shutil
import stat
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_DEST = ROOT.parent / "auto-perov-review-public"

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import release_layout  # noqa: E402

# Files above this size are shipped gzipped; tools/unpack_payloads.py restores
# them. Only two tracked files exceed it, and one is 81 MB, which GitHub warns
# on at 50 MB and blocks at 100 MB.
GZIP_OVER_BYTES = 20 * 1024 * 1024

# ---------------------------------------------------------------------------
# What ships. Keys are destination subtrees, values are source prefixes taken
# from `git ls-files` in the private repo.
# ---------------------------------------------------------------------------
SUBTREES: dict[str, list[str]] = {
    # The public tree MIRRORS the private layout: monthly and half-year code
    # at the root, yearly under yearly/. An earlier version of this script
    # nested the monthly tree under monthly_halfyear/ for tidiness, which
    # broke every path in the pipeline: scripts/stages/yearly_aggregate.py
    # resolves the monthly runs through parents[1], and the yearly stages read
    # ../runs/<month>/ relative to themselves. Seven tests failed with
    # "FAIL-CLOSED: no monthly runs on disk". Tidiness is not worth a tree
    # where nothing runs, so the layout is now identical to the repo that
    # produced the artifacts.
    "": [
        "scripts/",
        "config/",
        "tests/",
        "runs/",
        "manuscript/",
        "stats_history/",
        "papers/studies/",
        "papers/scripts/studies/",
        "docs/decisions/",
        "MASTER_HANDBOOK.md",
        "MASTER_HANDBOOK_H1.md",
        "PLAN_monthly_perovskite_review_v5.md",
        "data/",
        # The credential TEMPLATE ships (names only, never values) and
        # tests/test_no_secrets.py asserts its presence, so a tree without it
        # fails its own secret gate.
        #
        # .gitignore is NOT copied from the private repo: the overlay supplies
        # a release-specific one. The private file's `runs/*` rule silently
        # dropped the runs/<period>.active pointers from the first release
        # commit, which broke run resolution in a fresh clone.
        ".env.example",
    ],
    "yearly": [
        "yearly/",
    ],
}

# Dropped even when a prefix above would otherwise pull them in.
EXCLUDE_SUBSTR: tuple[str, ...] = (
    # Copyrighted third-party PDFs used as writing exemplars. Not ours to
    # redistribute; the pipeline never reads them.
    "example of review paper/",
    "Example of paper about automonous AI researcher/",
    # Superseded stage code and legacy payloads. Kept privately for audit
    # trail; shipping them invites someone to run a v1 stage.
    "OLD/",
    "archive/",
    "/scratch/",
    "/sandbox/",
    # Internal agent bookkeeping, not research artifacts.
    "docs/BRAIN_PENDING.md",
    # The unpublished system-paper manuscript. Its EVIDENCE ships
    # (papers/studies + papers/scripts/studies); its prose does not, and the
    # paper-building scripts are excluded with it so nothing dangles.
    "papers/system/",
    "papers/archive/",
    # Editor/CI noise.
    "__pycache__/",
    ".pytest_cache/",
)

EXCLUDE_EXACT: tuple[str, ...] = (
    "QUESTIONS.md",   # internal open-question log, superseded by the handbooks
    "IDEA.md",        # earliest scoping notes, contradicts the shipped design
    # Reads scratch/exemplars/, which holds the copyrighted third-party PDFs
    # excluded above. Shipping it would hand a reader a script that cannot run.
    "scripts/measure_style_any.py",
    # A format exemplar from another project, not a manuscript of this
    # pipeline. Havid removed it from the public repository (6b96c8a,
    # "remove unverified manuscript"); a rebuild must not bring it back.
    "manuscript/example_manuscript_v2.md",
    "manuscript/example_manuscript_v2.pdf",
)

# Abstract payloads are replaced by a digest. See _abstract_digest.
ABSTRACT_SUFFIXES = ("private/01_abstracts.jsonl", "private/02_abstracts.jsonl")

# ---------------------------------------------------------------------------
# Host-path sanitisation
# ---------------------------------------------------------------------------
# The shipped manuscripts carry \includegraphics{
# runs/<id>/fig/F1.pdf}. That is an absolute path on the authoring machine, so
# a third party who rebuilds the PDF gets a missing-figure error on every
# figure. Rewriting the prefix to a repo-root-relative path is the whole fix
# and it changes no number and no sentence.
#
# The username is also stripped from prose and docstrings. It leaks no secret,
# but "<HOME>" in a public repository is the authoring machine's
# layout, and a release should not read like a copied working directory.
HOST_REWRITES: tuple[tuple[str, str], ...] = (
    (r"F:[\\/]+GITHUB[\\/]+auto-perov-review[\\/]+", ""),
    (r"", ""),
    (r"F:[\\/]+GITHUB[\\/]+", ""),
    (r"", ""),
    (r"C:[\\/]+Users[\\/]+havid[\\/ ]+aqoma", "<HOME>"),
    (r"<HOME>", "<HOME>"),
    (r"[A-Za-z]:[\\/]+Users[\\/]+havid[^\\/\s\"'}]*", "<HOME>"),
)

SANITISE_EXT = {".md", ".py", ".txt", ".json", ".yaml", ".yml", ".tex",
                ".done", ".bib", ".csv"}


def sanitise(text: str) -> tuple[str, int]:
    """Strip authoring-machine paths. Returns (text, substitutions)."""
    n = 0
    for pat, repl in HOST_REWRITES:
        text, k = re.subn(pat, repl, text)
        n += k
    return text, n


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, check=True,
                         capture_output=True, text=True).stdout
    return [ln for ln in out.splitlines() if ln.strip()]


def is_excluded(rel: str) -> bool:
    if rel in EXCLUDE_EXACT:
        return True
    # No .gitignore is ever copied from the private repo. The overlay supplies
    # one release-specific file at the root. Both the root and the yearly
    # private .gitignore carry a `runs/*` rule that keeps per-run payloads out
    # of the private history; in the release tree that rule silently excluded
    # the runs/<period>.active pointers from `git add -A`, so a clone had run
    # directories that no stage could resolve while the built tree verified
    # perfectly.
    if rel == ".gitignore" or rel.endswith("/.gitignore"):
        return True
    return any(s in rel for s in EXCLUDE_SUBSTR)


def destination(rel: str) -> pathlib.Path | None:
    """Map a private-repo path to its public-tree path, or None to drop."""
    if is_excluded(rel):
        return None
    for sub, prefixes in SUBTREES.items():
        for p in prefixes:
            if rel == p or rel.startswith(p):
                # Both subtrees are identity mappings now: the public tree
                # mirrors the private layout so every relative path inside the
                # pipeline still resolves.
                return pathlib.Path(rel) if not sub else pathlib.Path(rel)
    return None


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _abstract_digest(src: pathlib.Path) -> bytes:
    """Per-work sha256 of the abstract text, without the text itself.

    OpenAlex serves abstracts as an inverted index and the pipeline
    reconstructs plain text from it (scripts/stages/util.py). Redistributing
    the reconstructed text would be republishing publisher abstracts, which
    we have no licence to do. The digest lets a third party re-fetch from
    OpenAlex and prove byte-for-byte that they hold the same corpus we held,
    which is what reproduction actually needs.
    """
    rows = []
    with src.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            ab = d.get("abstract") or ""
            rows.append({
                "work_key": d.get("work_key"),
                "abstract_sha256": _sha256(ab.encode("utf-8")),
                "abstract_chars": len(ab),
            })
    payload = {
        "note": ("Abstract TEXT is not redistributed (publisher copyright). "
                 "Re-fetch with tools/rehydrate_abstracts.py, which rebuilds "
                 "it from the OpenAlex inverted index and checks every row "
                 "against abstract_sha256 below."),
        "source_file": src.name,
        "rows": len(rows),
        "total_chars": sum(r["abstract_chars"] for r in rows),
        "digest": rows,
    }
    return (json.dumps(payload, indent=1, ensure_ascii=False) + "\n").encode("utf-8")


def robust_rmtree(path: pathlib.Path, attempts: int = 6) -> None:
    """Delete a tree, tolerating transient Windows file locks.

    On Windows an antivirus scanner or the search indexer can hold a handle on
    a file for a second or two after it is written, and shutil.rmtree then
    fails with WinError 5 on a directory that is genuinely empty. Retrying
    with a short backoff clears it. Read-only bits are also cleared, because
    copy2 preserves them and rmtree refuses read-only files on Windows.
    """
    def on_error(func, p, exc_info):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except OSError:
            pass

    last: Exception | None = None
    for i in range(attempts):
        try:
            shutil.rmtree(path, onerror=on_error)
            if not path.exists():
                return
        except OSError as exc:
            last = exc
        time.sleep(0.5 * (i + 1))
    if path.exists():
        raise RuntimeError(
            f"could not remove {path} after {attempts} attempts: {last}. "
            "Close any editor, shell, or file browser open inside it.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default=str(DEFAULT_DEST))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    dest = pathlib.Path(a.dest).resolve()

    if dest.exists() and (dest / ".git").exists():
        print(f"REFUSING: {dest} already has a .git; delete or pick another "
              "--dest. This script never writes into an initialised repo.",
              file=sys.stderr)
        return 2

    files = tracked_files()
    copied = skipped = digested = gzipped = n_sanitised = 0
    n_relinked = n_repacked = 0
    plan: list[tuple[str, str, str]] = []
    renames: list[tuple[str, str | None]] = []

    for rel in files:
        d = destination(rel)
        if d is None:
            skipped += 1
            continue
        src = ROOT / rel
        if not src.exists():          # tracked but deleted on disk
            skipped += 1
            continue
        # Latest edition only, version tokens off output names. See
        # release_layout.py for the rules and why step names keep theirs.
        pub = release_layout.public_path(rel)
        renames.append((rel, pub))
        if pub is None:
            skipped += 1
            continue
        d = pathlib.Path(pub)

        if rel.endswith(ABSTRACT_SUFFIXES):
            plan.append((rel, str(d.parent / "ABSTRACTS_DIGEST_"
                                   f"{pathlib.Path(rel).stem}.json"), "digest"))
            continue
        if src.stat().st_size > GZIP_OVER_BYTES:
            plan.append((rel, str(d) + ".gz", "gzip"))
            continue
        plan.append((rel, str(d), "copy"))

    if a.dry_run:
        by_kind: dict[str, int] = {}
        for _, _, k in plan:
            by_kind[k] = by_kind.get(k, 0) + 1
        print(f"tracked={len(files)} ship={len(plan)} drop={skipped}")
        print("by kind:", by_kind)
        for rel, out, kind in plan:
            if kind != "copy":
                print(f"  [{kind}] {rel} -> {out}")
        return 0

    # Fail before writing anything if the layout rules left a versioned
    # output name or mapped two private files onto one public path.
    outs = [pathlib.PurePath(o).as_posix() for _, o, _ in plan]
    bad = release_layout.unversioned_violations(outs)
    dup = sorted({o for o in outs if outs.count(o) > 1})
    if bad or dup:
        print(f"FAIL-CLOSED layout: versioned={bad[:10]} collisions={dup[:10]}",
              file=sys.stderr)
        return 2

    if dest.exists():
        robust_rmtree(dest)
    dest.mkdir(parents=True)

    for rel, out, kind in plan:
        src = ROOT / rel
        dst = dest / out
        pub = pathlib.PurePath(out).as_posix()
        dst.parent.mkdir(parents=True, exist_ok=True)
        if kind == "copy":
            if src.suffix.lower() in SANITISE_EXT:
                try:
                    txt = src.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    shutil.copy2(src, dst)
                    copied += 1
                    continue
                clean, k = sanitise(txt)
                # Point shipped text at the renamed files (scoped per file).
                clean, r = release_layout.rewrite_text(pub, clean)
                n_relinked += r
                # Write with newline="" so the original line endings survive:
                # a gate report's sha256 is computed over bytes, and silently
                # converting CRLF to LF here would change hashes the
                # verification manifests then record as drift.
                dst.write_text(clean, encoding="utf-8", newline="")
                n_sanitised += k
                copied += 1
                continue
            if rel.endswith(".tar.gz") and rel.startswith("manuscript/"):
                # The ChemRxiv tarball names its PDFs manuscript_vN.pdf.
                dst.write_bytes(release_layout.repack_tarball(
                    src.read_bytes(), pub))
                n_repacked += 1
                copied += 1
                continue
            shutil.copy2(src, dst)
            copied += 1
        elif kind == "digest":
            dst.write_bytes(_abstract_digest(src))
            digested += 1
        elif kind == "gzip":
            # mtime=0 and no stored file name: a gzip header otherwise records
            # the build time, so every rebuild rewrote an 80 MB payload whose
            # content had not changed and grew the public history by it.
            with src.open("rb") as fi, open(dst, "wb") as raw, \
                    gzip.GzipFile(filename="", mode="wb", fileobj=raw,
                                  compresslevel=9, mtime=0) as fo:
                shutil.copyfileobj(fi, fo)
            gzipped += 1

    # The overlay holds everything that exists ONLY in the public tree:
    # reproduce.py, the environment manifests, the Dockerfile, the tools, the
    # top-level README/LICENSE/CITATION. It is versioned in the private repo
    # under scripts/release/overlay/ so it is reviewable and diffable rather
    # than being generated as a string literal inside this script.
    overlay = ROOT / "scripts" / "release" / "overlay"
    n_overlay = 0
    if not overlay.is_dir():
        print(f"FAIL: overlay missing at {overlay}", file=sys.stderr)
        return 2
    for src in sorted(overlay.rglob("*")):
        if src.is_dir() or "__pycache__" in src.parts:
            continue
        dst = dest / src.relative_to(overlay)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        n_overlay += 1

    # Run pointers. The FIRST stage of a run writes runs/<period>.active with
    # the run id, and every later stage reads it to find the directory. Those
    # pointers are gitignored in the private repo (they are per-machine
    # working state), so a tree built from `git ls-files` alone has runs on
    # disk that no stage can find.
    #
    # The private repo's own pointers are the ground truth for which run
    # SHIPPED, so they are copied when present. Deriving them instead is a
    # guess: the first attempt derived them by splitting the directory name on
    # "_", which silently skipped the 2026-H1 run (no underscore in its name)
    # and that is the only run carrying G3d-illumination, so the handbook gate
    # test then reported G3d as a phantom gate. Derivation survives only as a
    # fallback for a period whose pointer is absent.
    n_ptr = n_derived = 0
    for src_runs, dst_runs in ((ROOT / "runs", dest / "runs"),
                               (ROOT / "yearly" / "runs",
                                dest / "yearly" / "runs")):
        if not dst_runs.is_dir():
            continue
        have: set[str] = set()
        for ptr in sorted(src_runs.glob("*.active")):
            target = ptr.read_text(encoding="utf-8").strip()
            if (dst_runs / target).is_dir():
                shutil.copy2(ptr, dst_runs / ptr.name)
                have.add(ptr.name[: -len(".active")])
                n_ptr += 1
        # Fallback for any shipped run directory with no pointer of its own.
        for d in sorted(dst_runs.iterdir()):
            if not d.is_dir():
                continue
            period = d.name.rpartition("_")[0] or d.name
            if period in have:
                continue
            if not any(d.glob("gate_report*.json")):
                continue
            (dst_runs / f"{period}.active").write_text(d.name + "\n",
                                                       encoding="utf-8")
            have.add(period)
            n_derived += 1

    # The yearly subtree has no conftest.py of its own; the monthly one holds
    # the autouse socket block. reproduce.py asserts both suites are offline,
    # so the guard is installed here rather than being claimed and not checked.
    ycf = dest / "yearly" / "tests" / "conftest.py"
    if ycf.parent.is_dir() and not ycf.exists():
        shutil.copy2(dest / "tests" / "conftest.py", ycf)

    # The rename record, so a reader can map every public name back to the
    # name the pipeline step wrote (tools/stage_inputs.py uses it).
    vdir = dest / "verification"
    vdir.mkdir(parents=True, exist_ok=True)
    (vdir / "release_renames.json").write_text(
        json.dumps(release_layout.rename_manifest(renames), indent=1) + "\n",
        encoding="utf-8")

    print(f"[build] dest={dest}")
    print(f"[build] copied={copied} gzipped={gzipped} "
          f"abstract-digests={digested} dropped={skipped} "
          f"overlay={n_overlay} pointers={n_ptr}+{n_derived}derived "
          f"host-paths-rewritten={n_sanitised} "
          f"renamed-refs-rewritten={n_relinked} tarballs-repacked={n_repacked}")
    print("[build] next:")
    print("  python scripts/release/make_verification_manifests.py "
          f"--tree {dest}")
    print(f"  cd {dest} && python tools/ship_audit.py")
    print(f"  cd {dest} && python reproduce.py --tier 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
