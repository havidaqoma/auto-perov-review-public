"""Archive superseded H1 artifacts into OLD/ before the v6 commit lands.

Havid (2026-09-12): "I forgot to tell you to archive the old version of files
also".

WHAT NEEDS ARCHIVING, AND WHAT EMPHATICALLY DOES NOT
-----------------------------------------------------
Handbook 1.3 says superseded files are MOVED into OLD/ with an index. Applying
that rule to this working tree means separating three classes that look alike
in `git status` but are not alike at all:

1. PURE RENAMES (the `R` entries: v5 -> v6 stages, probes, run-dir files).
   Content is byte-identical and git records the rename. Copying these into
   OLD/ would put two identical gate reports on disk differing only by suffix,
   which is the exact ambiguity rename_v5_to_v6.py was written to remove.
   NOT ARCHIVED.

2. DELETED-WITH-REPLACEMENT (manuscript/2026-H1_v5/, 51 `D` entries).
   Recoverable with `git show HEAD:<path>`, but OLD/ exists so that a reader
   does not need git archaeology to see what a prior reader might be holding.
   The READER-FACING artifacts are archived: the two PDFs a person could have
   downloaded, their markdown sources, and the gate report that certifies them.
   The regenerable bulk (figures, CSV data pack, claim_cards.jsonl at 1.6 MB)
   is NOT copied: it is reproducible from runs/2026-H1/ and duplicating it
   would add megabytes of binary to the repo for no recovery value.

3. STALE FILES INSIDE THE SHIPPING v6 DIRECTORY.  <- the dangerous one
   manuscript/2026-H1_v6/chemrxiv/ still holds manuscript_v4.pdf,
   manuscript_v5.pdf, supplementary_v4.pdf and supplementary_v5.pdf, dated
   2026-09-11 01:40/01:43, carried along when the directory was renamed
   wholesale. These are UNTRACKED, and their bytes differ from the v5 blobs at
   HEAD, so git history does NOT contain them. If they are deleted without
   being archived first they are gone for good. They are archived and then
   removed from the shipping tree, because a submission directory that
   contains three manuscript PDFs invites uploading the wrong one.

The tarball was verified separately: chemrxiv_2026-H1.tar.gz contains only
manuscript_v6.pdf and supplementary_v6.pdf, so it does NOT ship the stale
files and does not need rebuilding.
"""
from __future__ import annotations

import hashlib
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEST = ROOT / "OLD" / "2026-H1_v5_artifacts"

# Class 2: reader-facing v5 artifacts, pulled from HEAD (they are deleted on disk).
FROM_HEAD = [
    "manuscript/2026-H1_v5/manuscript_v5.pdf",
    "manuscript/2026-H1_v5/supplementary_v5.pdf",
    "manuscript/2026-H1_v5/supplementary_v5.md",
    "manuscript/2026-H1_v5/gate_report_v4.json",
    "manuscript/2026-H1_v5/chemrxiv/SUBMISSION_CHECKLIST.md",
    "manuscript/2026-H1_v5/chemrxiv/submission_metadata.json",
]

# Class 3: stale PDFs sitting in the SHIPPING v6 directory. Untracked, so these
# exist nowhere else. Archived, then deleted from the v6 tree.
STALE_IN_V6 = [
    "manuscript/2026-H1_v6/chemrxiv/manuscript_v4.pdf",
    "manuscript/2026-H1_v6/chemrxiv/manuscript_v5.pdf",
    "manuscript/2026-H1_v6/chemrxiv/supplementary_v4.pdf",
    "manuscript/2026-H1_v6/chemrxiv/supplementary_v5.pdf",
]


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:16]


def main() -> int:
    (DEST / "from_v5_dir").mkdir(parents=True, exist_ok=True)
    (DEST / "stale_in_v6_chemrxiv").mkdir(parents=True, exist_ok=True)

    manifest: list[str] = []
    failures: list[str] = []

    for rel in FROM_HEAD:
        out = DEST / "from_v5_dir" / pathlib.Path(rel).name
        try:
            blob = subprocess.run(
                ["git", "show", f"HEAD:{rel}"],
                cwd=ROOT, capture_output=True, check=True).stdout
        except subprocess.CalledProcessError as exc:
            failures.append(f"{rel}: git show failed ({exc.returncode})")
            continue
        out.write_bytes(blob)
        manifest.append(f"| `{out.name}` | from-HEAD | {len(blob):,} | `{sha(blob)}` |")
        print(f"archived (HEAD)  {rel} -> {out.relative_to(ROOT)} [{len(blob):,} B]")

    for rel in STALE_IN_V6:
        src = ROOT / rel
        if not src.exists():
            failures.append(f"{rel}: not on disk")
            continue
        data = src.read_bytes()
        out = DEST / "stale_in_v6_chemrxiv" / src.name
        shutil.copy2(src, out)
        # Verify the copy landed byte-for-byte BEFORE deleting the only copy.
        if sha(out.read_bytes()) != sha(data):
            failures.append(f"{rel}: copy hash mismatch, NOT deleting")
            continue
        src.unlink()
        manifest.append(f"| `{out.name}` | stale-in-v6 | {len(data):,} | `{sha(data)}` |")
        print(f"archived (disk)  {rel} -> {out.relative_to(ROOT)} [{len(data):,} B], removed from v6")

    (DEST / "MANIFEST.md").write_text(
        "# 2026-H1 v5 archive\n\n"
        "Written by `scripts/archive_h1_v5.py` on 2026-09-12.\n\n"
        "`from-HEAD` files were recovered from the last commit before the v5\n"
        "directory was replaced by v6. `stale-in-v6` files were UNTRACKED\n"
        "copies left inside `manuscript/2026-H1_v6/chemrxiv/` by the wholesale\n"
        "directory rename; they existed nowhere else and are the reason this\n"
        "script runs before the commit rather than after.\n\n"
        "| File | Source | Bytes | sha256[:16] |\n|---|---|---|---|\n"
        + "\n".join(sorted(manifest)) + "\n",
        encoding="utf-8")

    print(f"\nmanifest rows: {len(manifest)}")
    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
