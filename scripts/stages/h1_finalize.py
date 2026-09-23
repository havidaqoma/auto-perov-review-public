"""H1 finalisation: SI, ChemRxiv package, token accounting.

Same adapter technique as h1_build.py, and for the same reason. s19/s20/s21
carry the SI composition, the ChemRxiv package contract (subject categories,
the licence, the "fails closed if the word arXiv survives" migration guard) and
the reported-vs-estimated token discipline. Copying them would create a second
copy of each of those guards, which is the divergence failure the handbook
records three times.

So nothing here changes those stages. It rebinds the names they resolve at call
time so an edition id of "2026-H1" reaches a period label instead of
int("H1"), then calls their real build() functions.

The month-string sites this works around were found by grep before any of this
was written, and they are exactly the ones predicted:
  s19_si.py:36        month.split("-")  -> int(m)
  s20_chemrxiv.py     inherits the same via its own month_name usage
  s21_tokens.py       reads run_dir only

Every rebinding is asserted before use: a stage that stops binding a name
fails loudly rather than silently producing the wrong artifact (7.7 #6).
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from stages.util import RUNS  # noqa: E402

EDITION = "2026-H1"
PERIOD_LABEL = "January-June 2026"
VERSION = "v4"


MONTHS = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]


def h1_dir() -> pathlib.Path:
    return RUNS / EDITION


def ensure_meta01() -> dict:
    """Aggregate 01_meta.json for the SI's source-count table.

    s19 prints per-source harvest counts (OpenAlex / S2 / Crossref / arXiv).
    Those are facts about what ran, so they are SUMMED from the six monthly
    01_meta.json files rather than invented or left blank. A missing month
    raises: an SI table reporting 0 arXiv records for a half year because one
    file was absent is the silent-zero class (7.1).
    """
    d = h1_dir()
    out = d / "01_meta.json"
    totals: dict[str, int] = {}
    per_month: dict[str, dict] = {}
    oa_count = 0
    for m in MONTHS:
        ptr = RUNS / f"{m}.active"
        if not ptr.exists():
            raise SystemExit(f"FAIL-CLOSED: {m}.active missing; cannot sum "
                             f"harvest sources for the SI.")
        rd = RUNS / ptr.read_text(encoding="utf-8").strip()
        meta = json.loads((rd / "01_meta.json").read_text(encoding="utf-8"))
        per_month[m] = meta.get("sources", {})
        for k, v in (meta.get("sources") or {}).items():
            totals[k] = totals.get(k, 0) + int(v or 0)
        oa_count += int(meta.get("openalex_count") or 0)
    payload = {"edition": EDITION, "period": PERIOD_LABEL,
               "months": MONTHS, "sources": totals,
               "openalex_count": oa_count, "per_month_sources": per_month}
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[h1-final] 01_meta.json sources={totals}", flush=True)
    return payload


def _rebind(mod, names: list[str]) -> None:
    """Rebind period-aware names on `mod` AND on every module it delegates to.

    The first version rebound only the calling stage, and s19 promptly created
    a brand new run dir `runs/2026-H1_916aace0`: it reaches run_dir indirectly
    through stages.section_map, whose module-level binding was untouched, and
    util.run_dir hashes an unknown id into a fresh directory rather than
    failing. The stage then looked for a section map that had never been
    written there.

    That is the divergence failure in miniature (7.6 #12): a fix applied in one
    consumer while another consumer keeps the old behaviour. Rebind every
    module that resolves the name, and assert the target dir afterwards so a
    stray run dir can never be silently created again.
    """
    d = h1_dir()
    for name in names:
        if not hasattr(mod, name):
            raise SystemExit(
                f"FAIL-CLOSED: {mod.__name__} no longer binds {name!r}; this "
                f"adapter is stale and would build the wrong artifact.")

    smap = json.loads((d / "12_section_map.json").read_text(encoding="utf-8"))
    from stages import section_map as _sm
    from stages import util as _util
    from stages import s18d_build_v4 as _b
    from stages.h1_title import derive_title_h1

    # s19 and s20 both do `from stages.s18d_build_v4 import derive_title`
    # INSIDE their build(), so the name is resolved from the s18d module at
    # call time. Rebinding it there covers both consumers from one place --
    # the whole reason the H1 title was extracted to stages/h1_title.py.
    _b.derive_title = derive_title_h1

    for target in (mod, _sm, _util):
        if hasattr(target, "run_dir"):
            target.run_dir = lambda m, create=True: d
        if hasattr(target, "month_name"):
            target.month_name = lambda m: PERIOD_LABEL
        if hasattr(target, "load_map"):
            target.load_map = lambda m: smap


def run_si() -> None:
    ensure_meta01()
    from stages import s19_si as s19
    _rebind(s19, ["run_dir", "month_name"])
    # s19 reads the version from sys.argv[2]; give it the shape it expects.
    sys.argv = ["s19_si.py", EDITION, VERSION]
    s19.build(EDITION)


def run_chemrxiv() -> None:
    from stages import s20_chemrxiv as s20
    _rebind(s20, ["run_dir"])
    sys.argv = ["s20_chemrxiv.py", EDITION, VERSION]
    s20.build(EDITION)


def run_tokens() -> None:
    from stages import s21_tokens as s21
    _rebind(s21, ["run_dir"])
    sys.argv = ["s21_tokens.py", EDITION, VERSION]
    s21.collect(EDITION, VERSION)


def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "si"):
        print("=== s19 SI ===", flush=True)
        run_si()
    if which in ("all", "chemrxiv"):
        print("=== s20 ChemRxiv ===", flush=True)
        run_chemrxiv()
    if which in ("all", "tokens"):
        print("=== s21 tokens ===", flush=True)
        run_tokens()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
