"""Establish exactly what the v6 rebuild did to the shipped v4 edition.

s18d_build_v4.py line 1124 hardcodes

    outdir = ROOT / "manuscript" / f"{month}_v4"

and h1_build_v6.py drives s18d's build(). So rebuilding the v6 edition writes
its markdown, PDF and gate report into the **v4** directory, whatever version
it was actually asked to build. h1_build_v6's own docstring claims "both
artifacts coexist and the shipped v1 is untouched"; this checks whether that
claim survived contact with the rebuild.

Written as a file because the LaTeX title pattern needs backslashes that kept
arriving mangled through nested shell quoting in `python -c`.
"""
from __future__ import annotations

import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
TITLE = re.compile(r"bfseries\s+([^\\]+)")
# One sentence that exists ONLY in the rewritten prose from this session.
REWRITE_PROBE = "Of these, 884 were examined closely"
# One that exists ONLY in the original v4 prose.
ORIGINAL_PROBE = "while certain studies concluded"


def git_show(path: str) -> str:
    p = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=ROOT,
                       capture_output=True, text=True)
    return p.stdout


def title_of(text: str) -> str:
    m = TITLE.search(text)
    return m.group(1).strip()[:72] if m else "<no title found>"


def main() -> int:
    rel4 = "manuscript/2026-H1_v4/manuscript_v4.md"
    cur4 = (ROOT / rel4).read_text(encoding="utf-8")
    com4 = git_show(rel4)

    print("=== TITLES ===")
    print(f"  committed v4 : {title_of(com4)}")
    print(f"  current   v4 : {title_of(cur4)}")

    print("\n=== WHOSE PROSE IS IN THE v4 DIRECTORY NOW? ===")
    for label, txt in (("committed v4", com4), ("current   v4", cur4)):
        print(f"  {label}: rewrite={REWRITE_PROBE in txt}  "
              f"original={ORIGINAL_PROBE in txt}")

    print("\n=== IS THE CURRENT v4 FILE JUST THE v6 BUILD OUTPUT? ===")
    for cand in ("runs/2026-H1/manuscript_v4.md",
                 "manuscript/2026-H1_v6/manuscript_v6.md"):
        f = ROOT / cand
        if f.exists():
            same = f.read_text(encoding="utf-8") == cur4
            print(f"  {cand:44s} exists, identical_to_current_v4={same}")
        else:
            print(f"  {cand:44s} does not exist")

    print("\n=== DOES ANY v6 STAGE READ FROM manuscript/2026-H1_v4/ ? ===")
    hits = []
    for py in sorted((ROOT / "scripts" / "stages").glob("h1_*.py")):
        for i, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
            if "_v4" in line and "manuscript" in line and "read" in line.lower():
                hits.append(f"{py.name}:{i}: {line.strip()[:90]}")
    print("  " + ("\n  ".join(hits) if hits else
                  "no v6 stage READS the v4 manuscript dir"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
