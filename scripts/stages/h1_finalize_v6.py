"""v2 finalisation: SI, ChemRxiv package, token accounting.

Same adapter technique as h1_finalize.py (v1), with one structural advantage
discovered by reading s19/s20 rather than assuming: BOTH stages take the
version from sys.argv[2] and use it for every path --

    gate_report_{ver}.json      manuscript_{ver}.md
    supplementary_{ver}.pdf     manuscript/{month}_{ver}/

So passing ver="v2" makes the output directory land at
manuscript/2026-H1_v6/ by itself. No copy-out, no relocation, and no writing
through v1's directory -- which is exactly the overlap defect that
h1_build_v6 had to back up and restore around.

The one thing that must be prepared: the v2 build wrote `manuscript_v4.md` and
`gate_report_v4.json` (s18d hardcodes "v4" in those filenames). s19/s20 with
ver="v2" look for the _v2 names, so those two files are published under the v2
names in the run dir first. They are COPIES, not moves: v1's finalize still
needs the _v4 names.

v1 (`h1_finalize.py`) is untouched.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from stages.util import RUNS  # noqa: E402

EDITION = "2026-H1"
PERIOD_LABEL = "January-June 2026"
VERSION = "v6"
MONTHS = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]


def h1_dir() -> pathlib.Path:
    return RUNS / EDITION


def publish_v2_names() -> dict:
    """Give s19/s20 the _v2 filenames they will look for.

    s18d hardcodes manuscript_v4.md / gate_report_v4.json regardless of the
    structure it built, so the v2 build's outputs carry v4 names. Copy them to
    the v2 names rather than renaming: v1's finalize reads the v4 names and
    must keep working.

    Asserted, because a stale copy here would let the v2 SI describe the v1
    manuscript -- the exact defect of handbook 7.6 #6, a verifier that passed
    by examining a different artifact.
    """
    d = h1_dir()
    info = {}
    pairs = [("manuscript_v4.md", f"manuscript_{VERSION}.md"),
             ("gate_report_v4.json", f"gate_report_{VERSION}.json")]
    for src, dst in pairs:
        s, t = d / src, d / dst
        if not s.exists():
            raise SystemExit(
                f"FAIL-CLOSED: {s} missing; run h1_build_v6 before finalising.")
        shutil.copy2(s, t)
        info[dst] = t.stat().st_size

    # s20 fails closed unless manuscript_<ver>.pdf exists in the MANUSCRIPT
    # dir, and it is right to: "a package without its main file is not a
    # package". s18d only ever writes manuscript_v4.pdf, so publish the v2
    # name from the v2 render.
    #
    # Source is manuscript/2026-H1_v6/manuscript_v4.pdf, which h1_build_v6
    # copied out of the build. Deliberately NOT the _v4 directory: that one
    # holds whichever structure was built last, so reading it here could stage
    # a v1 PDF inside a v2 package -- handbook 7.6 #6, a stage that passed by
    # examining a different artifact.
    mdir = ROOT / "manuscript" / f"{EDITION}_{VERSION}"
    mdir.mkdir(parents=True, exist_ok=True)
    src_pdf = mdir / "manuscript_v4.pdf"
    if not src_pdf.exists():
        raise SystemExit(
            f"FAIL-CLOSED: {src_pdf} missing; run h1_build_v6 before "
            f"finalising.")
    dst_pdf = mdir / f"manuscript_{VERSION}.pdf"
    shutil.copy2(src_pdf, dst_pdf)
    info[dst_pdf.name] = dst_pdf.stat().st_size

    # The gate report must describe the DEVICE-FAMILY build, not a mechanism
    # one. If it does not, the v2 build has not been run since the last v1
    # build and the SI would quote v1's gates under a v2 heading.
    g = json.loads((d / f"gate_report_{VERSION}.json").read_text(encoding="utf-8"))
    smap = json.loads((d / "12_section_map_v6.json").read_text(encoding="utf-8"))
    if g.get("map_sha256") and g["map_sha256"] != smap["sha256"]:
        raise SystemExit(
            f"FAIL-CLOSED: gate report map_sha {g.get('map_sha256')} != v2 map "
            f"sha {smap['sha256']}. Re-run h1_build_v6 first; the v2 SI would "
            f"otherwise describe a different manuscript.")
    info["map_sha"] = smap["sha256"]
    info["sections"] = len(smap["sections"])
    return info


def ensure_meta01() -> dict:
    """Aggregate 01_meta.json for the SI's harvest-source table."""
    d = h1_dir()
    out = d / "01_meta.json"
    if out.exists():
        return json.loads(out.read_text(encoding="utf-8"))
    totals: dict[str, int] = {}
    per_month: dict[str, dict] = {}
    oa = 0
    for m in MONTHS:
        ptr = RUNS / f"{m}.active"
        if not ptr.exists():
            raise SystemExit(f"FAIL-CLOSED: {m}.active missing.")
        rd = RUNS / ptr.read_text(encoding="utf-8").strip()
        meta = json.loads((rd / "01_meta.json").read_text(encoding="utf-8"))
        per_month[m] = meta.get("sources", {})
        for k, v in (meta.get("sources") or {}).items():
            totals[k] = totals.get(k, 0) + int(v or 0)
        oa += int(meta.get("openalex_count") or 0)
    payload = {"edition": EDITION, "period": PERIOD_LABEL, "months": MONTHS,
               "sources": totals, "openalex_count": oa,
               "per_month_sources": per_month}
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def _rebind(mod) -> None:
    """Rebind period names on `mod` AND every module it delegates to.

    v1's version of this rebound only the calling stage and s19 promptly
    created a fresh run dir `runs/2026-H1_916aace0`, because it reaches
    run_dir indirectly through stages.section_map. Rebind every module that
    resolves the name (handbook 7.6 #12).
    """
    d = h1_dir()
    smap = json.loads((d / "12_section_map_v6.json").read_text(encoding="utf-8"))
    from stages import section_map as _sm
    from stages import util as _util
    from stages import s18d_build_v4 as _b
    from stages.h1_build_v6 import derive_title_v6_standalone

    # s19 and s20 both do `from stages.s18d_build_v4 import derive_title`
    # inside build(), so rebinding it on the s18d module covers both.
    _b.derive_title = derive_title_v6_standalone

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
    _rebind(s19)

    # Append the expanded period notes (S8-S14) to s19's own S1-S7.
    #
    # Havid (2026-09-10): the SI must let a reader understand the methodology
    # "without see our code block". s19 composes the monthly method notes; the
    # period-specific method -- why six months, the January date decision,
    # device-family assignment, the illumination exclusion, which denominator
    # applies where, what is and is not verified automatically, and how to
    # check any number -- lives in the period layer.
    #
    # Done by wrapping s19.build rather than editing it: s19 is a MONTHLY stage
    # and Havid's standing instruction is that the monthly workflow is not
    # disturbed. The wrapper reads the markdown s19 wrote, appends the extra
    # notes, and re-renders the PDF from the combined file, so there is exactly
    # one SI document rather than two.
    from stages.h1_si_extra import build_notes
    from stages.util import RUNS as _R
    import json as _json
    import shutil as _sh
    import subprocess as _sp

    _orig = s19.build

    def build_with_extra(month):
        meta = _orig(month)
        d = h1_dir()
        si_md = d / f"supplementary_{VERSION}.md"
        if not si_md.exists():
            raise SystemExit(f"FAIL-CLOSED: {si_md} missing after the SI stage.")
        S = _json.loads((d / "stats.json").read_text(encoding="utf-8"))
        extra = build_notes(S)
        body = si_md.read_text(encoding="utf-8")
        # Title, date and "Cited in the main text" come from the manuscript
        # this SI supports, not from s19's own derivation. s19 derives the
        # title only for ver "v4" and falls back to July's literal subtitle
        # otherwise, and it counts only plain [n] markers while the build
        # emits \href-wrapped ones, so the H1 v6 SI named a different paper
        # and said 0 works were cited. See stages/si_facts.py.
        from stages.si_facts import correct_si_front
        mtext = (d / f"manuscript_{VERSION}.md").read_text(encoding="utf-8")
        body, facts = correct_si_front(body, mtext)
        si_md.write_text(body, encoding="utf-8")
        meta.update({"title": facts["title"], "date": facts["date"],
                     "n_cited_main": facts["n_cited"]})
        print(f"[h1v6-final] SI front from manuscript: {facts}", flush=True)
        if "## Note S8." in body:
            return meta                      # idempotent
        # The lead paragraph promises seven notes; it must promise them all.
        body = body.replace(
            "and the automated gate report for this build (Note S7).",
            "the automated gate report for this build (Note S7), the "
            "half-year assembly method (Note S8), a date-precision limitation "
            "in the first month (Note S9), device-family assignment "
            "(Note S10), illumination conditions and excluded efficiencies "
            "(Note S11), the corpus denominators (Note S14), what was and was "
            "not verified automatically (Note S12), and how to check any "
            "number in this review (Note S13).")
        si_md.write_text(body.rstrip() + "\n\n" + extra + "\n", encoding="utf-8")

        # Re-render from the combined markdown.
        pandoc = _sh.which("pandoc")
        if not pandoc:
            for c in (pathlib.Path.home() / "AppData/Local/Pandoc/pandoc.exe",
                      pathlib.Path(r"C:\Program Files\Pandoc\pandoc.exe")):
                if c.exists():
                    pandoc = str(c)
                    break
        tectonic = _sh.which("tectonic") or "tectonic"
        outdir = ROOT / "manuscript" / f"{EDITION}_{VERSION}"
        outdir.mkdir(parents=True, exist_ok=True)
        pdf = outdir / f"supplementary_{VERSION}.pdf"
        p = _sp.run([pandoc, str(si_md), "-V", "geometry:margin=2.4cm",
                     "-V", "fontsize=10pt", "-V", "colorlinks=true",
                     "-V", "linkcolor=[HTML]{1A4E8A}",
                     "-V", "urlcolor=[HTML]{1A4E8A}",
                     # Suppress pandoc's automatic float labels.
                     #
                     # The SI numbers its own floats "Figure S1.", "Table S4."
                     # because supplementary floats carry an S prefix LaTeX
                     # counters do not produce. Pandoc then prepended its own
                     # label and the reader saw it twice:
                     #     "Figure 1: Figure S1. Corpus construction funnel."
                     #     "Figure 2: Figure S2. Reporting-completeness ..."
                     # Havid found both on the rendered page.
                     #
                     # Suppressing the AUTOMATIC label is the right fix rather
                     # than deleting the manual one: the manual labels are what
                     # the body text cross-references and what a reader cites
                     # when quoting the SI. Letting pandoc number them would
                     # renumber every reference to 1, 2, 3 and silently break
                     # each cross-reference. The header also keeps a table
                     # caption with its table (Table S4 rendered a page away
                     # from its own body).
                     "-H", str(ROOT / "config" / "tex" / "si_head.tex"),
                     f"--pdf-engine={tectonic}", "-o", str(pdf)],
                    capture_output=True, text=True, timeout=900, cwd=ROOT)
        if p.returncode != 0 or not pdf.exists():
            raise SystemExit(f"FAIL-CLOSED expanded SI: rc={p.returncode}\n"
                             f"{(p.stderr or '')[:1200]}")
        _sh.copy(si_md, outdir / si_md.name)
        try:
            import pymupdf
            with pymupdf.open(pdf) as doc:
                meta["pages"] = doc.page_count
        except Exception:
            pass
        meta["notes"] = 14
        print(f"[h1v6-final] SI expanded to {meta['notes']} notes, "
              f"{meta.get('pages')} pages")
        return meta

    s19.build = build_with_extra
    sys.argv = ["s19_si.py", EDITION, VERSION]
    s19.build(EDITION)


def run_chemrxiv() -> None:
    from stages import s20_chemrxiv as s20
    _rebind(s20)
    sys.argv = ["s20_chemrxiv.py", EDITION, VERSION]
    s20.build(EDITION)


def run_tokens() -> None:
    from stages import s21_tokens as s21
    _rebind(s21)
    sys.argv = ["s21_tokens.py", EDITION, VERSION]
    s21.collect(EDITION, VERSION)


def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    info = publish_v2_names()
    print(f"[h1v6-final] v2 names published: {info}", flush=True)
    if which in ("all", "si"):
        print("=== s19 SI (v2) ===", flush=True)
        run_si()
    if which in ("all", "chemrxiv"):
        print("=== s20 ChemRxiv (v2) ===", flush=True)
        run_chemrxiv()
    if which in ("all", "tokens"):
        print("=== s21 tokens (v2) ===", flush=True)
        run_tokens()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
