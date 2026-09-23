"""Item 2: fault-injection study of the pipeline's gates.

METHOD: oracle-first mutation testing. For every mutation the gate that MUST
catch it is declared BEFORE injection, from the handbook's defect ledger. Then:
inject -> verify the injection actually landed -> run the real stage -> read
gate_report_v4.json -> record caught / missed / caught-by-a-different-gate.

Three rules this harness will not break:

1. NEVER mutate a live run directory. Every mutation gets its own sandbox copy.
2. GREP-VERIFY THE INJECTION BEFORE READING THE GATE REPORT (handbook 7.5). An
   injection that silently failed to land produces a false "miss", which is the
   single most likely way this study lies to us.
3. A gate is never edited to pass or fail an injection.

An expected miss that the handbooks already document (absent figures, intra-issue
duplication) is recorded as `known_blind`, not presented as a discovery.

Run: python -u scripts/studies/fault_injection.py [month]
"""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from studies.study_common import (ROOT, active_run, gate_status,  # noqa: E402
                                  make_sandbox, run, unfreeze_drafts,
                                  write_report)

MONTH = sys.argv[1] if len(sys.argv) > 1 else "2026-07"
PY = sys.executable

# Narration sentence that ACTUALLY shipped in the August v4 PDF under the
# section 8 heading while G4 reported pass (handbook 6.4).
SHIPPED_LEAK = "I have launched the search command and will wait for it to finish."
# A paraphrase deliberately NOT in KNOWN_LEAKS. This measures whether the filter
# generalises or merely memorises; a miss here is an honest finding, not a bug.
NOVEL_LEAK = "Let me pull up the remaining records before I carry on with this part."


def _cards_path(sb):
    return active_run(MONTH, sb) / "claim_cards.jsonl"


def _read_cards(sb):
    return [json.loads(l) for l in _cards_path(sb).read_text(encoding="utf-8").splitlines() if l.strip()]


def _write_cards(sb, cards):
    _cards_path(sb).write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in cards) + "\n",
        encoding="utf-8")


def _draft(sb, name):
    return active_run(MONTH, sb) / "draft_v4" / name


def _abstracts(sb):
    p = active_run(MONTH, sb) / "private" / "02_abstracts.jsonl"
    return {json.loads(l)["work_key"].lower(): (json.loads(l).get("abstract") or "")
            for l in p.read_text(encoding="utf-8").splitlines() if l.strip()}


# ---------------------------------------------------------------------------
# Mutations. Each returns a marker string that MUST be found afterwards.
# ---------------------------------------------------------------------------

def m_control(sb):
    return None  # negative control: nothing injected


def m_anchor_not_verbatim(sb):
    cards = _read_cards(sb)
    for c in cards:
        for grp in ("performance", "stability"):
            for k, v in (c.get(grp) or {}).items():
                if isinstance(v, dict) and v.get("anchor"):
                    v["anchor"] = v["anchor"].replace(" the ", " the quantum ", 1)
                    if " quantum " not in v["anchor"]:
                        v["anchor"] = "quantum " + v["anchor"]
                    _write_cards(sb, cards)
                    return "quantum"
    return None


def m_anchor_overlong(sb):
    """Verbatim but 30 words: isolates the length rule from the verbatim rule."""
    cards, abst = _read_cards(sb), _abstracts(sb)
    for c in cards:
        src = abst.get((c.get("work_key") or "").lower(), "")
        if len(src.split()) < 40:
            continue
        for grp in ("performance", "stability"):
            for k, v in (c.get(grp) or {}).items():
                if isinstance(v, dict) and v.get("anchor"):
                    v["anchor"] = " ".join(src.split()[:30])
                    _write_cards(sb, cards)
                    return v["anchor"][:40]
    return None


def m_value_outside_anchor(sb):
    cards = _read_cards(sb)
    for c in cards:
        for k, v in (c.get("performance") or {}).items():
            if isinstance(v, dict) and v.get("anchor") and v.get("value") is not None:
                v["value"] = 91.7
                _write_cards(sb, cards)
                return "91.7"
    return None


def m_sj_over_sq_limit(sb):
    """A certified single-junction value above the Shockley-Queisser limit."""
    cards = _read_cards(sb)
    best, bestv = None, -1
    for c in cards:
        a = (c.get("device") or {}).get("architecture")
        v = (c.get("performance") or {}).get("pce_certified")
        if a in ("p-i-n", "n-i-p") and isinstance(v, dict) and isinstance(v.get("value"), (int, float)):
            if v["value"] > bestv:
                best, bestv = v, v["value"]
    if best is None:
        return None
    best["value"] = 34.8
    _write_cards(sb, cards)
    return "34.8"


def m_fabricated_abstract_digit(sb):
    p = _draft(sb, "abstract.md")
    t = p.read_text(encoding="utf-8")
    p.write_text(t.rstrip() + " A record efficiency of 47.3% is now established.",
                 encoding="utf-8")
    return "47.3"


def m_unresolved_placeholder(sb):
    p = _draft(sb, "abstract.md")
    t = p.read_text(encoding="utf-8")
    p.write_text(t.rstrip() + " Growth reached {{P_NOT_A_REAL_TOKEN}} this period.",
                 encoding="utf-8")
    return "P_NOT_A_REAL_TOKEN"


def m_narration_shipped(sb):
    p = _draft(sb, "sec3.md")
    p.write_text(SHIPPED_LEAK + "\n\n" + p.read_text(encoding="utf-8"), encoding="utf-8")
    return "launched the search command"


def m_narration_novel(sb):
    p = _draft(sb, "sec4.md")
    p.write_text(NOVEL_LEAK + "\n\n" + p.read_text(encoding="utf-8"), encoding="utf-8")
    return "pull up the remaining records"


def m_em_dash(sb):
    p = _draft(sb, "sec5.md")
    t = p.read_text(encoding="utf-8")
    p.write_text(t.replace(". ", " \u2014 and therefore ", 1), encoding="utf-8")
    return "\u2014"


def m_unresolvable_citation(sb):
    for n in ("sec2.md", "sec3.md", "sec4.md"):
        p = _draft(sb, n)
        t = p.read_text(encoding="utf-8")
        m = re.search(r"\[@[^\]]+\]", t)
        if m:
            p.write_text(t.replace(m.group(0), "[@10.9999/definitely.not.a.real.doi]", 1),
                         encoding="utf-8")
            return "10.9999/definitely.not.a.real.doi"
    return None


def m_citations_stripped(sb):
    """Cut citations well below the G2c band without touching prose length."""
    rd = active_run(MONTH, sb)
    n = 0
    for p in sorted((rd / "draft_v4").glob("sec*.md")):
        t = p.read_text(encoding="utf-8")
        out = []
        for c in re.finditer(r"\[@[^\]]+\]", t):
            out.append(c.group(0))
        keep = t
        for c in out:
            if n >= 45:
                break
            keep = keep.replace(c, "", 1)
            n += 1
        p.write_text(keep, encoding="utf-8")
    return f"stripped:{n}"


def m_section_bloat(sb):
    p = _draft(sb, "sec3.md")
    t = p.read_text(encoding="utf-8")
    p.write_text(t + "\n\n" + t + "\n\n" + t, encoding="utf-8")
    return "BLOAT"


def m_intra_issue_duplicate(sb):
    """Two sections of one issue carrying identical prose.

    Handbook H1 Appendix B #1: intra_issue_max_ratio is DEFINED but NOT
    ENFORCED. G8 only compares against prior issues, so this is expected to
    survive. Recorded as known_blind.
    """
    src = _draft(sb, "sec3.md").read_text(encoding="utf-8")
    p = _draft(sb, "sec5.md")
    p.write_text(src, encoding="utf-8")
    return "INTRA_DUP"


def m_figures_absent(sb):
    """Delete every figure. H1 9.2: G9c counts DUPLICATES and cannot see an
    ABSENCE, so this is expected to survive. Recorded as known_blind."""
    fd = active_run(MONTH, sb) / "fig"
    n = 0
    for f in list(fd.glob("*.pdf")):
        f.unlink()
        n += 1
    return f"deleted:{n}"


def m_notation_converter_disabled(sb):
    """Code mutation: neuter the unit/formula converter.

    The data-side equivalent does not work, because injecting `cm2` into prose
    is exactly what the converter is supposed to FIX. Regressing the converter
    is the real failure this gate exists to catch (7.6 #13, 7.7 #2/#3).
    """
    p = sb / "scripts" / "stages" / "notation.py"
    t = p.read_text(encoding="utf-8")
    m = re.search(r"^def format_notation\([^)]*\)[^:]*:\n", t, re.M)
    if not m:
        return None
    ins = m.end()
    # format_notation returns (text, counts). Returning a bare string crashes
    # the caller with "too many values to unpack" BEFORE G9a runs, which
    # measures this harness instead of the gate. First run did exactly that.
    t = t[:ins] + "    return text, {}  # FI_INJECTED_BYPASS\n" + t[ins:]
    p.write_text(t, encoding="utf-8")
    return "FI_INJECTED_BYPASS"


def m_bare_abbreviation(sb):
    """Neuter the deterministic expander so a bare abbreviation survives.

    Injecting bare "TRPL" into a draft does NOT test G7: expand_abbrev repairs
    it to "time-resolved photoluminescence (TRPL)" before the gate looks, so
    the build self-heals and G7 correctly reports pass. Verified on the first
    run. G7 is a BACKSTOP for the expander failing, so the honest injection is
    to break the expander and check the backstop fires.
    """
    p = sb / "scripts" / "stages" / "boilerplate.py"
    t = p.read_text(encoding="utf-8")
    m = re.search(r"^def expand_abbrev\([^)]*\)[^:]*:\n(?:\s*\"\"\".*?\"\"\"\n)?",
                  t, re.M | re.S)
    if not m:
        return None
    t = t[:m.end()] + "    return text, []  # FI_ABBREV_BYPASS\n" + t[m.end():]
    p.write_text(t, encoding="utf-8")
    # Bypassing the expander alone does NOT test G7: the writer's own prose
    # already reads "power conversion efficiency (PCE)", so nothing is bare and
    # G7 correctly passes. Verified on run 3. Strip the writer's expansions too,
    # so the abbreviation is genuinely bare on first use.
    rd = active_run(MONTH, sb)
    for f in sorted((rd / "draft_v4").glob("*.md")):
        t2 = f.read_text(encoding="utf-8")
        t2 = re.sub(r"power conversion efficiency\s*\(PCE\)", "PCE", t2, flags=re.I)
        t2 = re.sub(r"self-assembled monolayer[s]?\s*\(SAMs?\)", "SAM", t2, flags=re.I)
        f.write_text(t2, encoding="utf-8")
    return "FI_ABBREV_BYPASS"


def m_model_slug(sb):
    """Back matter naming a CLI slug instead of a product (G9d).

    The reader-facing name is models.yaml `display_name`, NOT a literal in
    boilerplate.py -- provenance() resolves it at build time. Patching
    boilerplate returned marker None on the first run and the harness wrongly
    scored a non-injection as a gate MISS.
    """
    p = sb / "config" / "models.yaml"
    t = p.read_text(encoding="utf-8")
    if "display_name" not in t:
        return None
    t = re.sub(r"display_name:\s*.+", "display_name: opus", t, count=1)
    p.write_text(t, encoding="utf-8")
    return "display_name: opus"


REGISTRY = [
    dict(id="NC-00", desc="negative control, nothing injected",
         oracle="(none)", expect="pass", runner="build", fn=m_control),
    dict(id="NC-01", desc="negative control, anchors untouched",
         oracle="(none)", expect="pass", runner="verify_anchors", fn=m_control),

    dict(id="FI-01", desc="anchor no longer verbatim in source abstract",
         oracle="verify_anchors", expect="catch", runner="verify_anchors",
         fn=m_anchor_not_verbatim),
    dict(id="FI-02", desc="anchor verbatim but 30 words (over the 25-word cap)",
         oracle="verify_anchors", expect="catch", runner="verify_anchors",
         fn=m_anchor_overlong),
    dict(id="FI-03", desc="numeric value absent from its own anchor",
         oracle="verify_anchors", expect="catch", runner="verify_anchors",
         fn=m_value_outside_anchor),

    dict(id="FI-04", desc="certified single junction above the SQ limit (34.8%)",
         oracle="G3c-abstract-physics", expect="catch", runner="build",
         fn=m_sj_over_sq_limit),
    dict(id="FI-05", desc="fabricated digit inserted into the abstract",
         oracle="G3-abstract", expect="catch", runner="build",
         fn=m_fabricated_abstract_digit),
    dict(id="FI-06", desc="unresolvable placeholder token in the abstract",
         oracle="build-fail-closed", expect="catch", runner="build",
         fn=m_unresolved_placeholder),

    dict(id="FI-07", desc="verbatim shipped narration sentence",
         oracle="G4", expect="catch", runner="build", fn=m_narration_shipped),
    dict(id="FI-08", desc="NOVEL narration paraphrase absent from KNOWN_LEAKS",
         oracle="G4", expect="unknown", runner="build", fn=m_narration_novel),
    dict(id="FI-09", desc="em-dash injected into body prose",
         oracle="G4", expect="catch", runner="build", fn=m_em_dash),

    dict(id="FI-10", desc="citation key resolving to no card",
         oracle="G1", expect="catch", runner="build", fn=m_unresolvable_citation),
    dict(id="FI-11", desc="45 citations stripped, pushing below the G2c band",
         oracle="G2c-cite-count", expect="catch", runner="build",
         fn=m_citations_stripped),
    dict(id="FI-12", desc="section tripled in length, over its ceiling",
         oracle="G2", expect="catch", runner="build", fn=m_section_bloat),

    dict(id="FI-13", desc="two sections of the SAME issue carrying identical prose",
         oracle="intra-issue novelty (defined, NOT enforced)",
         expect="known_blind", runner="build", fn=m_intra_issue_duplicate),
    dict(id="FI-14", desc="every figure deleted before the build",
         oracle="G9c (counts duplicates, cannot see absence)",
         expect="known_blind", runner="build", fn=m_figures_absent),

    dict(id="FI-15", desc="notation converter neutered (units ship flat)",
         oracle="G9a-notation", expect="catch", runner="build",
         fn=m_notation_converter_disabled),
    dict(id="FI-16", desc="bare abbreviation used before its expansion",
         oracle="G7-abbrev", expect="catch", runner="build",
         fn=m_bare_abbreviation),
    dict(id="FI-17", desc="AI declaration names a CLI slug, not a product",
         oracle="G9d-model-names", expect="catch", runner="build",
         fn=m_model_slug),
]


def injection_landed(sb, marker: str) -> bool:
    """Handbook 7.5: prove the NEW text is on disk before trusting any verdict."""
    if marker is None or marker.startswith(("stripped:", "deleted:", "BLOAT", "INTRA_DUP")):
        return True
    rd = active_run(MONTH, sb)
    hay = []
    for p in list((rd / "draft_v4").glob("*.md")):
        hay.append(p.read_text(encoding="utf-8", errors="replace"))
    hay.append((rd / "claim_cards.jsonl").read_text(encoding="utf-8", errors="replace"))
    for p in (sb / "scripts" / "stages").glob("*.py"):
        hay.append(p.read_text(encoding="utf-8", errors="replace"))
    # config/ too: the reader-facing model name lives in models.yaml, not in a
    # stage. Omitting it scored FI-17 as INJECTION_FAILED on run 3 even though
    # its oracle gate had fired -- the study contradicting itself in one row.
    for p in (sb / "config").glob("*.yaml"):
        hay.append(p.read_text(encoding="utf-8", errors="replace"))
    return any(marker in h for h in hay)


def main() -> int:
    rows = []
    for mut in REGISTRY:
        tag = f"fi_{mut['id'].replace('-', '')}"
        sb = make_sandbox(MONTH, tag)
        marker = mut["fn"](sb)
        # A mutation returning None found nothing to mutate: the injection did
        # NOT happen. Treating that as "landed" scored a non-injection as a
        # gate MISS on the first run (FI-17 patched a literal that lives in
        # models.yaml, not boilerplate.py). Only a control may have no marker.
        if mut["expect"] == "pass":
            landed = True
        elif marker is None:
            landed = False
        else:
            landed = injection_landed(sb, marker)
        unfreeze_drafts(sb, MONTH)

        if mut["runner"] == "verify_anchors":
            r = run([PY, "-u", "scripts/verify_anchors.py", MONTH], sb, timeout=600)
            gates = {}
            caught = r["rc"] != 0
            fired = "verify_anchors" if caught else ""
        else:
            r = run([PY, "-u", "scripts/stages/s18d_build_v4.py", MONTH], sb, timeout=900)
            gates = gate_status(sb, MONTH)
            failed = [k for k, v in gates.items() if v == "fail"]
            caught = bool(failed) or r["rc"] != 0
            fired = ",".join(failed) or ("build-fail-closed" if r["rc"] != 0 else "")

        oracle_hit = mut["oracle"] in fired.split(",") or (
            mut["oracle"] == "build-fail-closed" and "build-fail-closed" in fired)

        if mut["expect"] == "pass":
            verdict = "control_ok" if not caught else "CONTROL_BROKEN"
        elif not landed:
            verdict = "INJECTION_FAILED"
        elif caught and oracle_hit:
            verdict = "caught_by_oracle"
        elif caught:
            verdict = "caught_by_other_gate"
        elif mut["expect"] == "known_blind":
            verdict = "known_blind_confirmed"
        else:
            verdict = "MISSED"

        rows.append(dict(id=mut["id"], desc=mut["desc"], oracle=mut["oracle"],
                         expect=mut["expect"], runner=mut["runner"],
                         injection_landed=landed, rc=r["rc"], sec=r["sec"],
                         caught=caught, gates_fired=fired, verdict=verdict))
        print(f"[{mut['id']}] {verdict:24s} fired={fired or '-':28s} "
              f"rc={r['rc']} {r['sec']}s  {mut['desc'][:48]}")
        shutil.rmtree(sb, ignore_errors=True)

    n_real = [r for r in rows if r["expect"] in ("catch", "unknown")]
    caught = [r for r in n_real if r["caught"]]
    meta = dict(month=MONTH, n_mutations=len(rows),
                n_testable=len(n_real), n_caught=len(caught),
                controls_ok=all(r["verdict"] == "control_ok"
                                for r in rows if r["expect"] == "pass"),
                known_blind=[r["id"] for r in rows if r["expect"] == "known_blind"])
    csv_p, json_p = write_report("fault_injection", rows, meta)
    print("\n== SUMMARY ==")
    print(json.dumps(meta, indent=2))
    print(csv_p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
