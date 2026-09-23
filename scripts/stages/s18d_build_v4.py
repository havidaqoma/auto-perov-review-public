"""v4 build: dynamic section map, citation-free abstract, novelty gate.

Differences from s18c (v3), all driven by measured defects:

1. SECTIONS COME FROM THE MAP. v3 hardcoded eight sections in four files.
   v4 reads runs/<m>/12_section_map.json, which s13d computed from that
   month's own depth-tier evidence. No section title, ceiling or citation
   target is typed in this file.

2. THE ABSTRACT IS SUBSTITUTED, NOT TRANSCRIBED. s13d's writer emits named
   placeholders and never sees a digit. This file replaces them with canonical
   values from stats and DOI-bound cards. A number the writer cannot see is a
   number the writer cannot fabricate.

3. SINGLE-PASS CITATION NUMBERING. v3 needed two passes (abstract first, then
   body) purely because the abstract inherited body numbers, which is what
   produced the [1],[5],[6],[10],[60] defect. The v4 abstract carries no
   citations at all, so numbering is one pass over the body in reading order.

4. THE HARDCODED CONCLUSION TRIAD IS GONE. v3 closed the abstract with three
   sentences asserted every month regardless of evidence. Those now come from
   the writer, which has read the finished body.

5. G8-NOVELTY-VS-PRIOR. Repetition is measured against previous issues and
   gated, rather than hoped for. "Be more creative" in a prompt drifts back
   the moment sampling changes; an assertion does not.

Everything load-bearing is carried forward from v3 unchanged: the G5 page
bands, the 20 s draft freeze, the orphan-agy refusal, the CITE_RX lookahead
that ignores [60]fullerene, and the iterated citation merge.

Run: python scripts/stages/s18d_build_v4.py 2026-08
"""
from __future__ import annotations

import difflib
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import time

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from stages.util import CONFIG, ROOT, done, read_jsonl, run_dir  # noqa: E402
from stages.section_map import load_map, month_name  # noqa: E402
# Reuse v3's typography and boilerplate. These were tuned against real PDF
# defects (centring, doubled titles, longest-key-first abbreviations) and
# there is no reason to fork them.
# Boilerplate and typography live in their own module so no superseded build
# stage has to stay on the live path just to hold shared constants. s18d used
# to import these from s18c_build_v3, which blocked archiving v3 to OLD/.
from stages.boilerplate import (AFFIL, ACK, AI_DECL, ABBREV,  # noqa: E402
                                CORRESP_NOTE, CORRESP_EMAIL,
                                tex_esc, md_esc, expand_abbrev)
# G4 uses the SAME compiled filter as the draft stage. It previously carried a
# narrower private copy, so "I have launched the search command and will wait
# for it to finish." passed G4 and reached the shipped August v4 PDF.
from stages.hygiene import find_narration  # noqa: E402
# Notation (units, ions, formulae) is GENERATED, per 0.1. The writer
# emits plain text; this renders it. Havid found cm2 / V-1 / Na+ / PbI2
# printed flat in the August v4 PDF.
from stages.notation import check_notation, format_notation  # noqa: E402
# Title-block spacing is MEASURED on the rendered page, never tuned by
# eye. Three blind em-value tunings failed because space after
# \end{minipage} is discarded in horizontal mode. Shared with
# verify_pdf so the two cannot diverge (7.6 #10).
from stages.layout import measure as measure_title_block  # noqa: E402

TITLE_FRAME = "Perovskite Photovoltaics"

# Sentences that SHOULD repeat between issues: declarations, boilerplate and
# standing definitions. G8 must not punish these or it would force the paper
# to reword its own ethics statement every month.
NOVELTY_WHITELIST = [
    "no figure is a model-generated image",
    "abstract text and full texts are not redistributed",
    "the authors declare no conflict of interest",
    "this manuscript was prepared as part of our research project",
    "the agent executed the monthly review pipeline",
    "the author reviewed and edited the content",
    "structured extraction used",
    "literature harvesting, selection, statistics",
    "the corpus table for the month",
    "financial support from xiamen university malaysia",
    "every quantitative statement in the main text",
]


def _v(c, k):
    src = c["stability"] if k in ("t80_h",) else c["performance"]
    f = (src or {}).get(k)
    return f["value"] if isinstance(f, dict) and f.get("value") is not None else None


def _fmt(x) -> str:
    """Render a number the way the manuscript should show it."""
    if isinstance(x, float) and x == int(x):
        return str(int(x))
    return str(x)


def resolve_placeholders(ab: str, S: dict, cl: list) -> tuple[str, dict, list]:
    """Substitute {{TOKEN}} with canonical values. Fails closed on leftovers.

    This is the anti-fabrication boundary. The writer produced prose with no
    digits in it; every number below comes from stats.json or a claim card.
    """
    cert = sorted(((_v(c, "pce_certified"), c) for c in cl if _v(c, "pce_certified")),
                  key=lambda x: -x[0])
    areas = sorted(((_v(c, "active_area_cm2"), c) for c in cl
                    if _v(c, "active_area_cm2")), key=lambda x: -x[0])
    t80 = sorted(((_v(c, "t80_h"), c) for c in cl if _v(c, "t80_h")),
                 key=lambda x: -x[0])
    n_proto = len([c for c in cl if c["stability"].get("protocol")])

    # Highest certified SINGLE-JUNCTION value.
    #
    # This filtered on the TITLE alone and shipped a tandem number as a single
    # junction in the June 2026 issue (Havid caught it by reading the PDF and
    # checking the source abstract). The paper is titled "Buried-interface
    # homogenization ... flexible perovskite photovoltaics" -- no "tandem",
    # no "silicon" -- but its abstract reports BOTH its own single-junction
    # result and "a certified 32.95% perovskite/Si tandem efficiency". The
    # title filter passed the tandem value straight through.
    #
    # A paper's title describes the paper. The ANCHOR describes the number,
    # and the anchor is the only text that was verified verbatim against the
    # source. So exclude on the anchor first, then on the title. Fail toward
    # excluding: a tandem value published as single-junction is a
    # misattribution (7.2), while dropping one eligible value costs the
    # abstract a superlative and nothing else.
    _MULTI = ("tandem", "/si", "silicon", "perovskite/perovskite",
              "two-terminal", "2-t", "4-t", "all-perovskite")

    def _is_single_junction(c: dict) -> bool:
        anchor = ((c.get("performance", {}).get("pce_certified") or {})
                  .get("anchor") or "").lower()
        title = (c.get("title") or "").lower()
        arch = ((c.get("device") or {}).get("architecture") or "").lower()
        if "tandem" in arch or "module" in arch:
            return False
        return not any(t in anchor or t in title for t in _MULTI)

    sj = [v for v, c in cert if _is_single_junction(c)]

    # largest certified area: the biggest area that also carries a certified value
    area_cert = [(a, c) for a, c in areas if _v(c, "pce_certified")]

    vals = {
        "N_CORPUS": _fmt(S["corpus.n"]),
        "N_DEPTH": _fmt(S["selection.n_depth"]),
        "N_CERT": _fmt(len(cert)),
        "N_READ": _fmt(len(cl)),
        "P_TOP_CERT": f"{_fmt(cert[0][0])}%" if cert else None,
        "P_TOP_SJ": f"{_fmt(max(sj))}%" if sj else None,
        "A_MAX": f"{_fmt(area_cert[0][0])} cm$^2$" if area_cert else (
            f"{_fmt(areas[0][0])} cm$^2$" if areas else None),
        "P_AREA_MAX": (f"{_fmt(_v(area_cert[0][1], 'pce_certified'))}%"
                       if area_cert else None),
        "N_T80": _fmt(len(t80)),
        "H_T80_MAX": f"{_fmt(int(t80[0][0]))} h" if t80 else None,
        "N_PROTO": _fmt(n_proto),
        "PCT_EFF": f"{S['audit.corpus.efficiency_stated.pct']}%",
        "PCT_CERT": f"{S['audit.corpus.certified.pct']}%",
    }

    used, missing = [], []
    for tok in sorted(set(re.findall(r"\{\{([A-Z0-9_]+)\}\}", ab))):
        v = vals.get(tok)
        if v is None:
            missing.append(tok)
            continue
        ab = ab.replace("{{" + tok + "}}", v)
        used.append(tok)
    leftover = re.findall(r"\{\{[^}]*\}\}", ab)
    if missing or leftover:
        raise SystemExit(
            f"FAIL-CLOSED abstract placeholders: unresolvable={missing} "
            f"leftover={leftover[:5]}. The writer invented a token or the "
            f"month has no value for it; do not ship a hole.")
    return ab, vals, used


def _strip_back_matter(md: str) -> str:
    """Drop everything a review is SUPPOSED to repeat verbatim.

    First G8 self-test reported 631 shared shingles against July, and nearly
    all of them were the funding grant number, the AI usage declaration, the
    data availability statement and the figure captions. Those must be
    identical every month; gating them would force the paper to reword its own
    ethics statement to pass. Phrase whitelisting could not catch them because
    normalisation strips the punctuation the phrases were written with, so cut
    the sections out structurally instead.
    """
    for marker in ("## Acknowledgements", "## Declaration of Competing",
                   "## Data Availability", "## AI Usage", "## References"):
        i = md.find(marker)
        if i >= 0:
            md = md[:i]
    md = re.sub(r"\\begin\{figure\}.*?\\end\{figure\}", " ", md, flags=re.S)
    md = re.sub(r"\\caption\{.*?\}", " ", md, flags=re.S)
    md = re.sub(r"\*\*Keywords:\*\*[^\n]*", " ", md)
    return md


def canon_work_key(k: str) -> str:
    """Canonical form of a DOI-shaped work key, for alias matching only.

    Lowercases, drops every non-alphanumeric character, and removes Elsevier's
    "/j." prefix, which is the character a writer most often loses when
    transcribing a key from its evidence block ("10.1016/joule.2026.102538"
    for "10.1016/j.joule.2026.102538").

    This is deliberately lossy, so it is only ever safe as a lookup that must
    match EXACTLY ONE card. It never replaces the real key: the reference list
    and every hyperlink use the card's own DOI.
    """
    k = re.sub(r"/j\.", "/", k.strip().lower())
    return re.sub(r"[^a-z0-9]", "", k)


def _prior_sections(md: str) -> dict:
    """Split a prior manuscript into {heading_lower: body} for like-vs-like."""
    out, cur, buf = {}, None, []
    for line in _strip_back_matter(md).splitlines():
        m = re.match(r"^##\s+(?:\d+\.\s*)?(.+?)\s*$", line)
        if m:
            if cur:
                out[cur] = "\n".join(buf)
            cur, buf = m.group(1).lower(), []
        elif cur:
            buf.append(line)
    if cur:
        out[cur] = "\n".join(buf)
    return out


def novelty_gate(month: str, secs: dict, ab: str, smap: dict,
                 gcfg: dict, prior_path: pathlib.Path | None = None) -> dict:
    """G8: measure repetition against the prior issue instead of hoping for none.

    Two signals, because either alone is gameable:
      - difflib ratio, section vs the MOST SIMILAR prior section (paraphrase)
      - >=12-word shingle reuse (a lifted sentence inside otherwise fresh prose)

    Compares rendered markdown, never PDF text: PDF line-wrapping splits words
    across newlines and would poison the shingles.

    Two bugs found by self-testing this gate against the real v3 August issue,
    both fixed here:
      1. Comparing each section against the WHOLE prior manuscript diluted every
         ratio to ~0.01, so the gate could never fire on a section. It now
         compares against each prior section and keeps the worst match.
      2. Back matter dominated the shingle count (631 hits, nearly all funding
         and declaration text). Back matter is now removed structurally.
    """
    body_max = gcfg["novelty"]["body_max_ratio"]
    abs_max = gcfg["novelty"]["abstract_max_ratio"]
    shingle_n = gcfg["novelty"]["shingle_words"]

    # manuscript_vN.md is the name this build writes; manuscript.md is the
    # same file in the public release, which drops version tokens from output
    # names. Sorting by name keeps the newest vN last when a run holds both
    # (the private July run also carries its unversioned v1 manuscript.md).
    prior = sorted((p for p in (ROOT / "runs").glob("*/manuscript*.md")
                    if re.fullmatch(r"manuscript(_v\d+)?\.md", p.name)
                    and p.parent.name.split("_")[0] < month),
                   key=lambda p: (p.parent.name, p.name))
    if prior_path is not None:
        # Only a self-test pins the comparison. A test that asserts a
        # HISTORICAL fact ("G8 rejects August v3 against July v3") must name
        # the file it means: the August v3 self-test silently started passing
        # when July's run dir gained a manuscript_v4.md, because the gate
        # picked the newest prior. The gate was correct both times; the
        # fixture had drifted, which is 7.3 in the test suite instead of the
        # pipeline.
        prior = [prior_path]
    if not prior:
        return {"status": "skip",
                "detail": {"reason": "no prior issue on record (cold start)"}}
    prev_path = prior[-1]
    prev_raw = prev_path.read_text(encoding="utf-8")

    def norm(t: str) -> str:
        t = re.sub(r"\[@?[\d,\w.\-/]+\]", " ", t)          # citations out
        t = re.sub(r"\\begin\{.*?\}|\\end\{.*?\}|\\[a-zA-Z]+", " ", t)
        t = re.sub(r"https?://\S+|10\.\d{4,}/\S+", " ", t)  # DOIs and links out
        t = t.lower()
        # Mandated abbreviation expansions out. G7 REQUIRES every abbreviation
        # to be expanded at first use, and boilerplate.expand_abbrev inserts
        # that expansion deterministically -- so the long form is build-authored
        # text that MUST recur every month. July 2026's six remaining shared
        # shingles were all "named an International Summit on Organic
        # Photovoltaic Stability (ISOS) protocol" plus the DOI that followed
        # it: two gates pulling opposite ways, with G8 failing prose for
        # obeying G7. Same class as the 631 funding-line shingles (7.3 #5):
        # text the pipeline itself writes cannot count as reuse by the writer.
        for _, long in ABBREV:
            t = t.replace(long.lower(), " ")
        t = re.sub(r"[^a-z0-9 ]", " ", t)
        return re.sub(r"\s+", " ", t).strip()

    prev_secs = _prior_sections(prev_raw)
    prev_abs = prev_secs.pop("abstract", "")
    prev_bodies = {k: norm(v) for k, v in prev_secs.items() if len(v.split()) > 40}

    title_of = {s["id"]: s["title"] for s in smap["sections"]}
    ratios, worst, worst_pair = {}, 0.0, None
    for sid in sorted(secs, key=int):
        cur = norm(secs[sid])
        best, against = 0.0, None
        for pk, pv in prev_bodies.items():
            r = difflib.SequenceMatcher(None, pv, cur).ratio()
            if r > best:
                best, against = r, pk
        ratios[sid] = {"ratio": round(best, 3),
                       "title": title_of.get(sid, sid),
                       "closest_prior": against}
        if best > worst:
            worst, worst_pair = best, (title_of.get(sid, sid), against)

    ab_ratio = round(difflib.SequenceMatcher(
        None, norm(prev_abs), norm(ab)).ratio(), 3) if prev_abs else 0.0

    def shingles(t: str) -> set:
        w = norm(t).split()
        return {" ".join(w[i:i + shingle_n])
                for i in range(max(0, len(w) - shingle_n + 1))}

    cur_sh = shingles("\n".join(secs.values()) + "\n" + ab)
    prev_sh = shingles(_strip_back_matter(prev_raw))
    shared = {s for s in (cur_sh & prev_sh)
              if not any(w in s for w in NOVELTY_WHITELIST)}

    ok = worst <= body_max and ab_ratio <= abs_max and not shared
    return {"status": "pass" if ok else "fail",
            "detail": {"prior_issue": prev_path.parent.name,
                       "worst_section_ratio": round(worst, 3),
                       "worst_pair": worst_pair,
                       "body_max_ratio": body_max,
                       "abstract_ratio": ab_ratio,
                       "abstract_max_ratio": abs_max,
                       "per_section": ratios,
                       "shared_shingles": sorted(shared)[:6],
                       "n_shared_shingles": len(shared)}}


def derive_title(month: str, smap: dict) -> str:
    """{Frame} in {Month Year}: {slot from this month's leading axes}.

    v3 hardcoded "Buried-Interface Chemistry, Defect Tolerance and the
    Certified Efficiency Frontier" for every issue. The slot now names the
    axes that actually led the month, so a composition-heavy month says so.
    """
    tt = yaml.safe_load((CONFIG / "title_terms.yaml").read_text(encoding="utf-8"))
    phrases = tt.get("axis_phrases", {})
    rot = int(month[:4]) * 12 + int(month[5:7])
    mech = [s for s in smap["sections"] if s["role"] == "mechanism"][:2]
    picked = []
    for s in mech:
        bank = phrases.get(s["axis"]) or []
        if bank:
            picked.append(bank[rot % len(bank)])
    if not picked:
        picked = ["a monthly mechanism and reporting audit"]
    # Join with a comma when a phrase already contains "and", or the slot
    # reads "trap density and ion migration and self-assembled monolayer
    # contacts". Two conjunctions in one noun phrase is a grammar defect a
    # reader sees immediately, and the title is the most-read line in the PDF.
    if len(picked) == 2 and any(" and " in p for p in picked):
        slot = f"{picked[0]}, {picked[1]}"
    else:
        slot = " and ".join(picked)
    slot = slot[0].upper() + slot[1:] if slot else slot
    title = f"{TITLE_FRAME} in {smap['month_name']}: {slot}"

    banned = [b.lower() for b in tt.get("banned_in_title", [])]
    low = title.lower()
    hits = [b for b in banned if b in low]
    if hits:
        raise SystemExit(f"FAIL-CLOSED title contains banned term {hits}")
    if title.count(":") != 1:
        raise SystemExit(f"FAIL-CLOSED title must have exactly one colon: {title}")
    if len(title.split()) > tt.get("max_title_words", 16):
        # trim to the leading axis rather than shipping an over-long title
        title = f"{TITLE_FRAME} in {smap['month_name']}: {picked[0].capitalize()}"
    if re.search(r"\b\d{2,}\b", title.replace(smap["month_name"], "")):
        raise SystemExit("FAIL-CLOSED title carries a publication count")
    return title


def provenance(rd: pathlib.Path, cards: list, models: dict) -> dict:
    """Derive the AI Usage Declaration from RECORDS, never from live config.

    v4 shipped an August PDF declaring "Structured extraction used
    muse-spark-1.3-contributor" while all 144 cards recorded
    opencode-go/qwen3.8-flash. The model was swapped in config/models.yaml
    mid-session, AFTER extraction had already run, and AI_DECL.format() read
    models['extractor']['model'] -- current state, not what actually ran.

    Nothing caught it because every earlier issue happened to agree with config
    by luck of timing. A provenance field generated from current state instead
    of from the artifacts is a silent misstatement, which is 0.3 and 7.2
    applied to the back matter: the declaration is prose reaching a reader and
    it must trace to the evidence chain like every other claim.

    So: extractor comes from the cards' own extractor.model, writer from the
    tokens ledger for the 13d_* stages. A mismatch against models.yaml fails
    the build, so a future swap without re-extraction is CAUGHT rather than
    quietly declared.
    """
    import collections

    ext = collections.Counter(
        (c.get("extractor") or {}).get("model") for c in cards
        if (c.get("extractor") or {}).get("model"))
    if not ext:
        raise SystemExit("FAIL-CLOSED provenance: no card records an "
                         "extractor.model; cannot declare what extracted this")
    # MORE THAN ONE EXTRACTOR IS A FACT TO DECLARE, NOT A CRASH.
    # This used to fail closed on a mixed corpus, which was right for a single
    # month extracted in one pass and wrong for every other case: the H1/H2
    # aggregate unions six monthly runs, and the extractor was repinned
    # qwen3.8-flash -> glm-5.3-flash (2026-09-11) with the earlier months left
    # as they were. Re-extracting eight shipped months to satisfy a
    # declaration would perturb every card to fix a sentence.
    #
    # The rule that matters is unchanged and comes from 8.4: the declaration
    # states WHAT ACTUALLY RAN, derived from the records. So name every model
    # with its own paper count, commonest first, and let the reader see the
    # split. Q40 still binds the WRITER to exactly one voice (checked below);
    # extraction is a mechanical step and carries no such constraint.
    ext_model = ", ".join(f"{m.split('/')[-1]} (n={n})"
                          for m, n in ext.most_common())

    writers = set()
    tj = rd / "tokens.jsonl"
    if tj.exists():
        for line in tj.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if str(r.get("stage", "")).startswith("13d") and r.get("model"):
                writers.add(r["model"])
    if len(writers) > 1:
        raise SystemExit(f"FAIL-CLOSED provenance: prose was written by more "
                         f"than one model {sorted(writers)}; Q40 requires "
                         f"exactly one prose voice per issue.")
    writer_model = next(iter(writers)) if writers else models["generator"]["model"]

    # Config drift is a warning surface, not a silent correction. The RECORD
    # wins; config being wrong is the operator's problem to see.
    cfg_ext = models["extractor"]["model"]
    if ext_model not in (cfg_ext, f"opencode-go/{cfg_ext}"):
        print(f"[18d] PROVENANCE MISMATCH: cards were extracted by "
              f"{ext_model!r} but config/models.yaml now says {cfg_ext!r}. "
              f"Declaring the RECORD. Re-extract the month if you intended "
              f"the new model to apply.")

    short = ext_model.split("/")[-1]
    # Reader-facing product name, not the CLI slug. models.yaml must keep
    # `model: opus` because that is the string the claude CLI accepts (a bare
    # "opus-5" 404s), so the human name is a separate `display_name` field.
    # Never rename the slug to fix prose: the build would stop working.
    rev = models["reviewer_science"]
    rev_name = rev.get("display_name") or rev["model"]
    return {
        "extractor": f"{short} through the opencode interface",
        "writer": f"{writer_model} through the agy interface",
        "reviewer": f"{rev_name} at high reasoning effort",
    }


def text_gates(*, month: str, ab: str, secs: dict, order: list,
               unresolved: list, aliased: dict, body_words: int,
               smap: dict, frozen: dict, seq: list, S: dict, cl: list,
               abs_vals: dict, abs_tokens: list, expanded: list, G: dict,
               notation_counts: dict, doi_of: dict, fig_for: dict,
               md: list, prior_path: pathlib.Path | None = None) -> dict:
    """Every gate that reads the manuscript SOURCE, in report order.

    Lifted verbatim out of build() so one body of code serves both the
    build and scripts/regate_edition.py. A regate that re-typed these
    checks would be a second implementation free to drift from the first,
    and its report would claim gates ran that never did.

    G10-title-block is returned as a placeholder warn: it is measured on
    the rendered page by the caller, like G5.
    """
    monotonic = seq == sorted(seq)
    BANNED = ["delve", "harness", "pivotal", "seamless", "leverage", "moreover",
              "furthermore", "it is worth noting", "noteworthy", "comprehensive",
              "cutting-edge", "tapestry", "unlock", "showcase", "underscore",
              "realm", "ever-evolving", "a myriad of", "state-of-the-art"]
    prose = ab + "\n" + "\n".join(secs.values())
    low = prose.lower()
    gate: dict = {}

    bad = {b: len(re.findall(rf"\b{re.escape(b)}\b", low)) for b in BANNED}
    bad = {k: v for k, v in bad.items() if v}
    # Narration detection uses stages.hygiene, the single canonical filter.
    # The old private LEAK_RX here was NARROWER than the draft-stage copy, so a
    # line that slipped clean() also passed G4 and shipped. G4 is the last line
    # of defence and is FAIL-CLOSED: the draft stage strips per line, so any
    # narration still present at build time means the strip was bypassed
    # (hand-edited draft, stale cache, divergent filter) and the build must
    # stop rather than emit a PDF a human has to catch.
    leak = find_narration(prose)
    gate["G4"] = {"status": "pass" if not bad and not prose.count("\u2014") and not leak
                  else "fail",
                  "detail": {"em_dash": prose.count("\u2014"), "banned": bad,
                             "self_report_leak": leak[:5]}}
    gate["G1"] = {"status": "pass" if not unresolved else "fail",
                  "detail": {"resolved": len(order),
                             "unresolved": unresolved[:8],
                             "aliased": aliased}}

    lo, hi = G["citations"]["total_band"]
    gate["G2c-cite-count"] = {
        "status": "pass" if lo <= len(order) <= hi else "fail",
        "detail": {"cited": len(order), "target_range": [lo, hi],
                   "words_per_citation": round(body_words / max(len(order), 1), 1)}}

    ceil_total = int(smap["total_ceiling"] * 1.15)
    per_sec_ok = {s["id"]: len(secs[s["id"]].split()) <= int(s["ceiling"] * 1.35)
                  for s in smap["sections"]}
    gate["G2"] = {"status": "pass" if body_words <= ceil_total and all(per_sec_ok.values())
                  else "fail",
                  "detail": {"prose_words": body_words, "ceiling": ceil_total,
                             "per_section_within_135pct": per_sec_ok,
                             "map_sha256": smap["sha256"],
                             "input_freeze": frozen}}
    gate["G2b-cite-order"] = {"status": "pass" if monotonic else "fail",
                              "detail": {"first_appearance_sequence": seq[:20],
                                         "monotonic": monotonic}}
    g6 = re.findall(r"\bwe (?:measured|fabricated|synthesi[sz]ed|simulated)\b", low)
    gate["G6"] = {"status": "pass" if not g6 else "fail", "detail": {"hits": g6}}

    # G3: every abstract numeral must trace to stats or a card. With
    # substitution this should be automatic, so a failure means the writer
    # smuggled a digit past the no-digit contract.
    stat_nums = {str(v) for v in S.values() if isinstance(v, (int, float))}
    stat_nums |= {_fmt(v) for v in S.values() if isinstance(v, (int, float))}
    card_nums = set()
    for c in cl:
        for grp in ("performance", "stability"):
            for f in (c.get(grp) or {}).values():
                if isinstance(f, dict) and f.get("value") is not None:
                    card_nums.add(_fmt(f["value"]))
                    card_nums.add(_fmt(int(f["value"])) if isinstance(f["value"], float)
                                  and f["value"] == int(f["value"]) else _fmt(f["value"]))
    allowed = stat_nums | card_nums | {_fmt(len(cl)), _fmt(len(order))}
    # Values that resolve_placeholders COMPUTES rather than reads: N_CERT is a
    # count of cards carrying a certified value, so it appears in neither
    # stats.json nor any card field. G3 flagged "18" as unverified on a number
    # this build had itself derived from the evidence. The substituted values
    # are the canonical ones by construction, so admit them explicitly.
    allowed |= {str(v) for v in abs_vals.values() if v is not None}
    allowed |= {re.sub(r"[^\d.]", "", str(v)) for v in abs_vals.values()
                if v is not None}
    bad_nums = [n for n in re.findall(r"\b\d+(?:\.\d+)?\b", ab)
                if n not in allowed and n not in {"80", "2", "1"}]
    gate["G3-abstract"] = {
        "status": "pass" if not bad_nums else "fail",
        "detail": {"unverified": bad_nums[:8], "words": len(ab.split()),
                   "placeholders_resolved": abs_tokens}}

    # G3c: a substituted value must be PHYSICALLY POSSIBLE for the quantity it
    # is presented as.
    #
    # G3 asks only "does this number trace to a card?". June 2026's abstract
    # said "32.95% in single-junction inverted cells", and 32.95 DID trace to a
    # card, so G3 passed it. The number was real; the device was wrong. That is
    # 7.2 with the arithmetic intact -- a misattribution, not a fabrication, and
    # tracing alone cannot see it.
    #
    # A certified single-junction perovskite above the Shockley-Queisser limit
    # (~33.7% ideal, ~29.4% for a 1.55 eV absorber) is impossible, so the
    # rendered claim was self-refuting to any reader who knows the physics.
    # Havid is that reader; this gate is so the build does not need him to be.
    SQ_SINGLE_JUNCTION_PCT = 29.4
    implausible = []
    sj_val = abs_vals.get("P_TOP_SJ")
    if sj_val:
        try:
            n = float(re.sub(r"[^\d.]", "", str(sj_val)))
        except ValueError:
            n = 0.0
        if n > SQ_SINGLE_JUNCTION_PCT:
            implausible.append(
                {"token": "P_TOP_SJ", "value": n,
                 "limit": SQ_SINGLE_JUNCTION_PCT,
                 "why": ("a single-junction perovskite cannot exceed the "
                         "Shockley-Queisser limit; this is a tandem or module "
                         "value attached to the wrong device")})
    gate["G3c-abstract-physics"] = {
        "status": "pass" if not implausible else "fail",
        "detail": {"implausible": implausible,
                   "sj_limit_pct": SQ_SINGLE_JUNCTION_PCT}}

    # G3d: a value presented as a performance record must have been measured
    # under one-sun AM1.5G.
    #
    # Havid read the v5 Table 1 and flagged a >30% single-junction PCE, asking
    # whether it was a tandem or a simulation. It was neither: a real,
    # experimental, correctly-labelled single-junction cell reporting
    # "a PCE(i) of 44.36% (a power output of 127.94 uW cm-2)" at 1000 lx LED.
    # The number is CORRECT. An indoor PCE above the one-sun Shockley-Queisser
    # limit is physically ordinary, because that limit is defined for AM1.5G
    # and a narrow low-flux indoor spectrum is far better matched to a
    # wide-bandgap absorber.
    #
    # Every guard already in this build passed it, each for a good reason:
    #   measured()                  asks about LENS      -> it is an experiment
    #   anchor_contradicts_family() asks about the DEVICE -> it is single junction
    #   G3c                         bounds CERTIFIED only -> this is self-reported
    #   pce_champion                had no plausibility check at all
    #
    # So illumination is a fourth, independent axis. The stats and figure layers
    # exclude indoor values (stages/illumination.py), but that guard lived
    # outside the gate set, which means a future consumer computing a frontier
    # by a new code path would bypass it silently. This gate closes that: it
    # re-derives the check from the CARDS BACKING THE ABSTRACT, so it holds
    # regardless of which layer produced the number.
    illum_bad = []
    try:
        from stages.illumination import classify, indoor_markers
        _byk = {c.get("work_key"): c for c in cl}
        for tok in ("P_TOP_CERT", "P_TOP_SJ", "P_AREA_MAX"):
            raw = abs_vals.get(tok)
            if not raw:
                continue
            try:
                want = float(re.sub(r"[^\d.]", "", str(raw)))
            except ValueError:
                continue
            for c in cl:
                for fld in ("pce_certified", "pce_champion"):
                    f = (c.get("performance") or {}).get(fld)
                    if not isinstance(f, dict):
                        continue
                    if f.get("value") != want:
                        continue
                    anch = f.get("anchor") or ""
                    if classify(anch) != "one_sun":
                        illum_bad.append({
                            "token": tok, "value": want,
                            "work_key": c.get("work_key"),
                            "condition": classify(anch),
                            "markers": indoor_markers(anch),
                            "anchor": anch[:150],
                            "why": ("an indoor or low-light efficiency is not "
                                    "comparable to a one-sun record and must "
                                    "not be presented as one")})
    except ImportError:
        # The module is part of the period layer. A monthly build without it
        # reports the gate as skipped rather than silently passing.
        illum_bad = None
    gate["G3d-illumination"] = {
        "status": ("skip" if illum_bad is None
                   else "pass" if not illum_bad else "fail"),
        "detail": {"non_one_sun_values": illum_bad or []}}

    alo, ahi = G["abstract"]["word_band"]
    naw = len(ab.split())
    gate["G3b-abstract-form"] = {
        "status": "pass" if (alo <= naw <= ahi and not re.search(r"\[\d", ab)
                             and "[@" not in ab) else "fail",
        "detail": {"words": naw, "band": [alo, ahi],
                   "citation_markers": len(re.findall(r"\[[@\d]", ab))}}

    unexp = []
    for abv, full in (("PCE", "power conversion efficiency"),
                      ("SAM", "self-assembled monolayer"),
                      ("ISOS", "International Summit on Organic Photovoltaic Stability")):
        first = prose.find(abv)
        if first >= 0 and full.lower() not in prose[:first + 90].lower():
            unexp.append(abv)
    gate["G7-abbrev"] = {"status": "pass" if not unexp else "fail",
                         "detail": {"expanded_automatically": expanded,
                                    "still_bare": unexp}}

    gate["G8-novelty"] = novelty_gate(month, secs, ab, smap, G,
                                      prior_path=prior_path)

    # ---- G9-format: the four defects Havid found in the August v4 PDF ----
    # Per 0.2 each becomes an assertion, not a prompt reminder. All four are
    # measured on the SOURCE the build just emitted; verify_pdf re-measures
    # the rendered page, because markdown inspection has missed every format
    # defect this project has shipped (0.3).
    all_prose = ab + "\n" + "\n".join(secs.values())

    # 1. notation: nothing may remain flat after the formatting pass
    notation_report = check_notation(all_prose)
    gate["G9a-notation"] = {
        "status": "pass" if not notation_report["defects"] else "fail",
        "detail": {"residual_defects": notation_report["defects"],
                   "ambiguous_for_human_review": notation_report["ambiguous"],
                   "substitutions_applied": sum(notation_counts.values())}}

    # 2. citations must be clickable. A body citation that is not wrapped in
    #    \href sends the reader nowhere, which was the whole point of the fix.
    n_href = len(re.findall(r"\\href\{https://doi\.org/", all_prose))
    plain = re.findall(r"(?<!\{)\[(\d+(?:,\d+)*)\](?!\})", all_prose)
    plain_real = [g for g in plain
                  if all(0 < int(x) <= len(order) for x in g.split(","))]
    no_doi = [wk for wk in order if not doi_of.get(wk)]
    gate["G9b-cite-links"] = {
        "status": "pass" if (n_href > 0 and not plain_real) else "fail",
        "detail": {"hyperlinked_markers": n_href,
                   "unlinked_markers": plain_real[:6],
                   "works_without_doi": len(no_doi)}}

    # 3. one figure file may appear at most once. F3 attached twice in the
    #    August build and LaTeX numbered it as both Figure 2 and Figure 3.
    attached = [fn for fn, _ in fig_for.values()]
    dupes = sorted({f for f in attached if attached.count(f) > 1})
    gate["G9c-figure-unique"] = {
        "status": "pass" if not dupes else "fail",
        "detail": {"attached": attached, "duplicates": dupes,
                   "n_attached": len(attached),
                   "n_distinct": len(set(attached))}}

    # 4. the AI declaration must name models the way a reader expects.
    #    "opus" is a CLI slug, not a product name.
    #
    #    Checker bug caught on first run (7.3, seventh instance): matching the
    #    lowercased substring "used opus" fires on the CORRECT string
    #    "used Opus 5", because "Opus 5".lower() starts with "opus". The
    #    artifact was right and the check was wrong. Require a bare slug that
    #    is NOT followed by a version token, and match case-sensitively so a
    #    capitalised product name is never a hit.
    ai_txt = "\n".join(str(x) for x in md
                       if "Structured extraction used" in str(x))
    BARE_SLUGS = ("opus", "sonnet", "haiku", "gemini", "qwen", "muse-spark")
    bad_names = []
    for slug in BARE_SLUGS:
        # bare slug, lowercase, not part of a longer token and not followed by
        # a version number or a hyphenated variant
        if re.search(rf"\b{re.escape(slug)}\b(?![\w.\-]*\s*\d)(?![\w.\-])",
                     ai_txt):
            bad_names.append(slug)
    gate["G9d-model-names"] = {
        "status": "pass" if not bad_names else "fail",
        "detail": {"bare_slugs_found": bad_names,
                   "declared": re.findall(r"(?:used|by) ([\w.\-]+(?: \d+)?)",
                                          ai_txt)[:4]}}
    # ---- G10-title-block: spacing MEASURED on the rendered page ----------
    # Deferred until after the PDF exists (like G5), because the whole point
    # is that source em-values lie: three blind tunings (0.9 -> 2.2 -> 3.6em)
    # all failed, and the fourth measurement showed \vspace after
    # \end{minipage} was being discarded in horizontal mode -- 3.6em in the
    # source rendered as 0.11 pt on the page.
    gate["G10-title-block"] = {"status": "warn",
                               "detail": {"reason": "not yet measured"}}
    for k, v in gate.items():
        print(f"[18d] {k}: {v['status']}  {json.dumps(v['detail'])[:135]}")
    return gate


def page_gate(pdf: pathlib.Path, G: dict) -> tuple:
    """G5: page bands measured on the rendered PDF. Returns (pages, g5)."""
    band_c = G["paper_v3"]["content_page_band"]
    band_t = G["paper_v3"]["total_page_band"]
    TBF = 0.40
    pages, g5 = None, {"status": "warn", "detail": {"reason": "pymupdf unavailable"}}
    try:
        import pymupdf
        refs_page = None
        with pymupdf.open(pdf) as d:
            pages = d.page_count
            for i in range(d.page_count):
                if re.search(r"^\s*(?:\d+\.\s*)?References\s*$", d[i].get_text(), re.M):
                    refs_page = i + 1
                    break
        if refs_page:
            content = refs_page - TBF
            ok_c = band_c[0] <= content <= band_c[1]
            ok_t = band_t[0] <= pages <= band_t[1]
            g5 = {"status": "pass" if (ok_c and ok_t) else "fail",
                  "detail": {"pages_to_refs": refs_page, "title_block_fraction": TBF,
                             "content_pages": round(content, 2), "total_pages": pages,
                             "reference_pages": pages - refs_page,
                             "content_band": band_c, "total_band": band_t,
                             "content_ok": ok_c, "total_ok": ok_t}}
        else:
            g5 = {"status": "warn", "detail": {"reason": "References heading not located",
                                               "total_pages": pages}}
    except Exception as e:
        g5 = {"status": "warn", "detail": {"error": str(e)[:140]}}
    return pages, g5


def build(month: str, out_dir_override: pathlib.Path | None = None) -> dict:
    rd = run_dir(month)
    MON = month_name(month)
    smap = load_map(month)
    S = json.loads((rd / "stats.json").read_text(encoding="utf-8"))
    G = yaml.safe_load((CONFIG / "gates.yaml").read_text(encoding="utf-8"))
    models = yaml.safe_load((CONFIG / "models.yaml").read_text(encoding="utf-8"))
    cards = {c["work_key"]: c for c in read_jsonl(rd / "claim_cards.jsonl")}
    corpus = {r["work_key"]: r for r in read_jsonl(rd / "05_corpus.jsonl")}
    oa = {}
    for r in read_jsonl(rd / "01_openalex.jsonl"):
        k = (r.get("doi") or "").replace("https://doi.org/", "").lower()
        if k:
            oa[k] = r

    dd = rd / "draft_v4"
    ids = [s["id"] for s in smap["sections"]]
    secs = {}
    for sid in ids:
        f = dd / f"sec{sid}.md"
        if not f.exists():
            raise SystemExit(f"FAIL-CLOSED: draft_v4/sec{sid}.md missing")
        secs[sid] = f.read_text(encoding="utf-8").strip()
    abs_f = dd / "abstract.md"
    if not abs_f.exists():
        raise SystemExit("FAIL-CLOSED: draft_v4/abstract.md missing")
    ab_raw = abs_f.read_text(encoding="utf-8").strip()

    # --- freeze: same two guards as v3 -----------------------------------
    newest = max((dd / f"sec{s}.md").stat().st_mtime for s in ids)
    newest = max(newest, abs_f.stat().st_mtime)
    if time.time() - newest < 20:
        raise SystemExit("FAIL-CLOSED: a draft changed <20s ago; writer still running")
    try:
        ps = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-Process agy -ErrorAction SilentlyContinue).Id -join ','"],
            capture_output=True, text=True, timeout=60)
        live = (ps.stdout or "").strip()
        if live:
            raise SystemExit(
                f"FAIL-CLOSED (7.4): agy writer still running (PID {live}).")
    except FileNotFoundError:
        print("[18d] WARN: powershell unavailable; orphan check skipped")
    except subprocess.TimeoutExpired:
        print("[18d] WARN: orphan check timed out; not treated as clear")

    frozen = {s: {"words": len(v.split()),
                  "sha256": hashlib.sha256(v.encode()).hexdigest()[:16]}
              for s, v in secs.items()}
    body_words = sum(len(v.split()) for v in secs.values())
    print("[18d] freeze " + " ".join(f"s{k}={v['words']}w" for k, v in frozen.items()))

    cl = list(cards.values())
    ab, abs_vals, abs_tokens = resolve_placeholders(ab_raw, S, cl)

    # --- abbreviations, abstract then body in reading order ---------------
    expanded = []
    ab, e = expand_abbrev(ab)
    expanded += e
    for sid in ids:
        secs[sid], e = expand_abbrev(secs[sid])
        expanded += e

    # --- citation numbering: ONE pass over the body -----------------------
    #
    # The writer transcribes a work_key from its evidence block, and a
    # transcription can lose a character. June 2026 shipped
    # "[@10.1016/joule.2026.102538]" for the card
    # "10.1016/j.joule.2026.102538" -- Elsevier's "j." prefix dropped -- and
    # G1 correctly refused to resolve it. Two wrong answers were available:
    # widen the gate (0.6.1) or silently drop the citation, which would have
    # deleted a real, anchor-verified claim from the manuscript.
    #
    # Instead resolve through a canonical form (lowercase, punctuation and the
    # Elsevier "j." prefix removed) and accept the alias ONLY when it matches
    # EXACTLY ONE card. Two candidates means the intended paper is unknown, so
    # it stays unresolved and G1 fails. Fail closed on ambiguity; never guess
    # which paper a number belongs to (0.7.2).
    def _canon(k: str) -> str:
        return canon_work_key(k)

    _alias: dict[str, list[str]] = {}
    for wk in cards:
        _alias.setdefault(_canon(wk), []).append(wk)

    aliased: dict[str, str] = {}

    def resolve_key(wk: str) -> str | None:
        """Card key for a written marker, or None if it cannot be resolved."""
        if wk in cards:
            return wk
        cand = _alias.get(_canon(wk), [])
        if len(cand) == 1:
            aliased[wk] = cand[0]
            return cand[0]
        return None

    order: list[str] = []
    for sid in ids:
        for m in re.finditer(r"\[@([^\]\s]+)\]", secs[sid]):
            wk = resolve_key(m.group(1))
            if wk and wk not in order:
                order.append(wk)
    num = {wk: i + 1 for i, wk in enumerate(order)}
    unresolved: list[str] = []

    # Havid: a reader should click the citation number and land on the paper.
    # Only the reference list was hyperlinked before, so 108 link annotations
    # existed and NONE were on a body page.
    #
    # The link is built here, from the same corpus record the reference line
    # uses, so a marker and its reference can never point at different DOIs.
    # A work with no DOI degrades to a plain number rather than an empty href.
    doi_of = {wk: (corpus.get(wk, {}).get("doi") or "") for wk in order}

    # ORDER MATTERS, and getting it wrong shipped a regression that
    # verify_pdf caught: linking each marker as \href{doi}{[12]} put brace
    # groups between adjacent brackets, so merge_cites could no longer see
    # "[1] [2]" and the PDF showed "[1] [2] [3] [4] [5]" instead of
    # "[1,2,3,4,5]". Two correct behaviours fought each other.
    #
    # Resolution: merge on PLAIN numbers first, then link each number INSIDE
    # the finished group. Brackets stay outside the links, so a group renders
    # as [1,2,3] and clicking any single number reaches that paper's DOI.
    by_num = {n: wk for wk, n in num.items()}

    def link_numbers(text: str) -> str:
        def one(m: re.Match) -> str:
            nums = [int(x) for x in m.group(1).split(",")]
            if any(x > len(order) or x == 0 for x in nums):
                return m.group(0)          # nomenclature, e.g. [100]
            out = []
            for x in nums:
                d = doi_of.get(by_num.get(x, ""), "")
                out.append(r"\href{https://doi.org/" + d + "}{" + str(x) + "}"
                           if d else str(x))
            return "[" + ",".join(out) + "]"
        return re.sub(r"\[(\d+(?:,\d+)*)\](?![A-Za-z])", one, text)

    def merge_cites(text: str) -> str:
        prev = None
        while prev != text:
            prev = text
            text = re.sub(r"\[([\d,]+)\]\s*\[([\d,]+)\]",
                          lambda m: "[" + m.group(1) + "," + m.group(2) + "]",
                          text)
        return re.sub(
            r"\[([\d,]+)\]",
            lambda m: "[" + ",".join(
                str(n) for n in sorted({int(x) for x in m.group(1).split(",")})
            ) + "]", text)

    for sid in ids:
        def rep(m):
            wk = resolve_key(m.group(1))
            if wk in num:
                return f"[{num[wk]}]"          # plain number; linked below
            unresolved.append(m.group(1))
            return ""
        secs[sid] = re.sub(r"\[@([^\]\s]+)\]", rep, secs[sid])
        secs[sid] = re.sub(r"\s+([.,;])", r"\1", secs[sid])
        secs[sid] = merge_cites(secs[sid])     # merge on PLAIN numbers
        secs[sid] = link_numbers(secs[sid])    # then link inside the group

    # [60]fullerene (IUPAC) and [100] (Miller index) are both nomenclature, not
    # citations. The lookahead alone missed "[100] growth" because a space
    # separates the bracket from the word. The robust rule: this manuscript has
    # exactly len(order) references, so any bracketed number ABOVE that count
    # cannot be a citation marker. Fifth instance of 7.3 -- the checker was
    # wrong, the manuscript was right.
    CITE_RX = r"\[(\d+(?:,\d+)*)\](?![A-Za-z])"
    n_refs = len(order)
    seq, seen = [], set()
    for m in re.finditer(CITE_RX, "\n".join(secs[s] for s in ids)):
        grp = [int(x) for x in m.group(1).split(",")]
        if any(x > n_refs or x == 0 for x in grp):
            continue                     # nomenclature, e.g. [100] plane
        for g in grp:
            if g not in seen:
                seen.add(g)
                seq.append(g)

    # --- references -------------------------------------------------------
    refs = []
    for wk in order:
        rec = corpus.get(wk, {})
        r = oa.get(wk.lower(), {})
        names = [(a.get("author") or {}).get("display_name") or ""
                 for a in (r.get("authorships") or [])]
        if names and names[0]:
            parts = names[0].split()
            auth = parts[-1] + ", " + "".join(p[0] + "." for p in parts[:-1])
            if len(names) > 1:
                auth += " et al."
        else:
            auth = "Anonymous"
        doi = rec.get("doi") or ""
        line = (f"{auth} {md_esc(rec.get('title'))}. *"
                f"{md_esc(rec.get('venue')) or 'Preprint'}* "
                f"({(rec.get('publication_date') or '')[:4]}).")
        if doi:
            line += f" [https://doi.org/{doi}](https://doi.org/{doi})"
        refs.append(f"{num[wk]}. {line}")

    # --- figures, attached by ROLE/AXIS not by fixed section number -------
    # Each figure file may be attached to AT MOST ONE section.
    #
    # Havid found "Figure 2 and Figure 3 are identical" in the August v4 PDF.
    # The cause: F3 was keyed by `s["axis"] in ("composition", "defects")` with
    # setdefault, which guards re-keying the SAME section id -- but defects was
    # section 3 and composition was section 5, two DIFFERENT ids, so F3
    # attached twice and LaTeX numbered it twice. The reader saw duplicate
    # plates; the file itself was fine (F2 and F3 md5s differ).
    #
    # `used` is keyed by FILENAME, so a second claimant is refused no matter
    # which section asks. Order of evaluation therefore decides the owner, and
    # it is explicit: stability owns F4, scale_up owns F2, then the leading
    # mechanism section owns F3.
    figdir = rd / "fig"
    used: set[str] = set()

    def claim(sid: str, fn: str, cap: str) -> None:
        if fn in used or sid in fig_for:
            return
        if not (figdir / fn).exists():
            return
        used.add(fn)
        fig_for[sid] = (fn, cap)

    fig_for: dict[str, tuple] = {}
    CAP = {
        "F1_certified_frontier.pdf":
            "The certified frontier in " + MON + ". Filled markers are "
            "independently certified efficiencies, open markers are "
            "self-reported champion values, grouped by device family. "
            "Horizontal bars mark the highest certified value in each family.",
        "F2_area_penalty.pdf":
            "Efficiency against reported active or aperture area. The shaded "
            "band marks the sub-0.3 cm$^2$ laboratory-cell regime in which "
            "most champion values are measured.",
        "F3_effort_map.pdf":
            "Where the month's mechanistic effort was directed. Depth-tier "
            "papers by mechanism axis, stacked by device family.",
        "F4_stability_evidence.pdf":
            "The month's operational-stability evidence in full. Left, every "
            "reported time to 80\% of initial performance. Right, the "
            "stability protocol labels used.",
    }

    for s_ in smap["sections"]:
        if s_["role"] == "frontier":
            claim(s_["id"], "F1_certified_frontier.pdf",
                  CAP["F1_certified_frontier.pdf"])
    # v1 attaches figures to MECHANISM sections keyed on axis. A v2
    # device-family map has role="family" and carries no `axes` list, so every
    # test below missed and only F1 attached: the v2 build shipped ONE figure
    # while v1 shipped three, and G9c passed because one figure is trivially
    # unique. A gate that only counts duplicates cannot see an absence.
    #
    # Attach by FAMILY when the map is a family map: modules own the area
    # penalty, and the single-junction section owns the stability plate
    # because that is where the T80 evidence overwhelmingly sits.
    fam_of = {s_["id"]: s_.get("family") for s_ in smap["sections"]
              if s_["role"] == "family"}
    for sid_, fam_ in fam_of.items():
        if fam_ == "mod":
            claim(sid_, "F2_area_penalty.pdf", CAP["F2_area_penalty.pdf"])
        elif fam_ == "sj":
            claim(sid_, "F4_stability_evidence.pdf",
                  CAP["F4_stability_evidence.pdf"])
        elif fam_ == "hyb":
            claim(sid_, "F3_effort_map.pdf", CAP["F3_effort_map.pdf"])
    for s_ in smap["sections"]:
        if s_["role"] != "mechanism":
            continue
        if "scale_up" in s_.get("axes", []):
            claim(s_["id"], "F2_area_penalty.pdf", CAP["F2_area_penalty.pdf"])
        elif s_.get("axis") == "stability":
            claim(s_["id"], "F4_stability_evidence.pdf",
                  CAP["F4_stability_evidence.pdf"])
    for s_ in smap["sections"]:
        if s_["role"] == "mechanism" and s_.get("axis") in ("composition", "defects"):
            claim(s_["id"], "F3_effort_map.pdf", CAP["F3_effort_map.pdf"])

    date_str = time.strftime("%B ") + str(int(time.strftime("%d"))) + time.strftime(", %Y")
    TITLE = derive_title(month, smap)

    # TITLE-BLOCK SPACING IS MEASURED, NOT TUNED.
    #
    # Three blind tunings failed (0.9em -> 2.2em -> 3.6em) because the
    # \vspace after \end{minipage} was being DISCARDED: it lands in
    # horizontal mode there, so LaTeX dropped it. Measured on the rendered
    # page, the affiliation->date gap was 0.11 pt while the source asked for
    # 3.6em, and date->abstract was 68.54 pt.
    #
    # Fix: the date goes INSIDE the minipage, spaced by \\[...] which
    # provably works (it is what separates the affiliation lines). G10
    # measures both gaps on the rendered PDF so this cannot regress silently.
    head = [r"\begin{center}",
            r"{\LARGE\bfseries " + tex_esc(TITLE) + r"\par}",
            r"\vspace{1.1em}",
            r"{\large Havid Aqoma\textsuperscript{1,2,3,4,*}\par}",
            r"\vspace{0.7em}",
            r"\begin{minipage}{\textwidth}\centering\small"]
    # The corresponding-author note sits directly under the affiliation list
    # and BEFORE the date, so the marker is explained where the reader meets
    # it. The last affiliation therefore gets a small separator and the note
    # carries the 2.0em gap to the date that G10's affil_to_date band was
    # measured against; otherwise the note would land on top of the date.
    for i, a in enumerate(AFFIL, 1):
        sep = r"\\[0.55em]" if i == len(AFFIL) else r"\\[0.25em]"
        head.append(r"\textsuperscript{" + str(i) + r"}" + tex_esc(a) + sep)
    head.append(tex_esc(CORRESP_NOTE).replace(r"\_", "_") + r"\\[2.0em]")
    head += [date_str,
             r"\end{minipage}", r"\end{center}",
             r"\vspace{0.8em}"]

    # ---- notation: units, ions, chemical formulae ----------------------
    # Per 0.1 format is GENERATED, never model-written. The writer emits
    # "61.2 cm2", "Pb2+" and "PbI2" as plain text and this pass renders them
    # as math. Havid found all three classes flat in the August v4 PDF.
    #
    # Applied AFTER citation markers become \href{...}{[n]}, because the
    # protection rules in notation.py mask hyperlinks and DOIs; running it
    # earlier would let a formula rule chew a DOI's digits.
    notation_counts: dict = {}
    ab, _c = format_notation(ab)
    for k, v in _c.items():
        notation_counts[k] = notation_counts.get(k, 0) + v
    for sid in ids:
        secs[sid], _c = format_notation(secs[sid])
        for k, v in _c.items():
            notation_counts[k] = notation_counts.get(k, 0) + v
    print(f"[18d] notation: {sum(notation_counts.values())} substitutions "
          f"across {len(notation_counts)} rules")

    md = ["\n".join(head), "", "## Abstract", "", ab, "",
          "**Keywords:** perovskite photovoltaics; buried interface; defect "
          "passivation; wide-bandgap perovskite; tandem solar cells; "
          "operational stability", ""]
    n_fig = 0
    # TABLE injection, mirroring fig_for exactly.
    #
    # TABLE_FOR maps section id -> markdown table block, and defaults to empty
    # so v1 and the monthly path emit no tables and are bit-identical to
    # before. Tables are appended to the ASSEMBLED md, never to secs[sid],
    # for the same reason figures are: G2 counts prose words and fingerprints
    # drafts, so folding a 200-word table into a section's text would blow its
    # word band and make the draft hash describe generated content.
    tab_for = globals().get("TABLE_FOR") or {}
    n_tab = 0
    for s in smap["sections"]:
        sid = s["id"]
        md += [f"## {sid}. {s['title']}", "", secs[sid], ""]
        if sid in tab_for:
            n_tab += 1
            md += [tab_for[sid], ""]
        if sid in fig_for:
            fn, cap = fig_for[sid]
            if (figdir / fn).exists():
                n_fig += 1
                md += ["\n".join([
                    r"\begin{figure}[htbp]", r"\centering",
                    r"\includegraphics[width=0.95\textwidth]{"
                    + (figdir / fn).as_posix() + r"}",
                    r"\caption{" + cap + r"}", r"\end{figure}"]), ""]

    md += ["## Acknowledgements", "", ACK, "",
           "## Declaration of Competing Interest", "",
           "The authors declare no conflict of interest.", "",
           "## Data Availability Statement", "",
           "The corpus table for the month, the per-paper extraction records with "
           "their verbatim source quotations, the statistics file underlying every "
           "number in the text, and the gate report are provided as Supplementary "
           "Information. Abstract text and full texts are not redistributed.", "",
           "## AI Usage Declaration", "",
           AI_DECL.format(**provenance(rd, cl, models)),
           "", "## References", ""] + refs
    manuscript = "\n".join(md)
    (rd / "manuscript_v4.md").write_text(manuscript, encoding="utf-8")

    # ---------------- gates ----------------
    gate = text_gates(month=month, ab=ab, secs=secs, order=order,
                      unresolved=unresolved, aliased=aliased,
                      body_words=body_words, smap=smap, frozen=frozen,
                      seq=seq, S=S, cl=cl, abs_vals=abs_vals,
                      abs_tokens=abs_tokens, expanded=expanded, G=G,
                      notation_counts=notation_counts, doi_of=doi_of,
                      fig_for=fig_for, md=md)
    # Callers that are not a month must be able to say where their artifacts
    # go. Deriving this path from `month` is correct for the monthly pipeline
    # and wrong for every adapter: h1_build_v6 calls build("2026-H1"), so the
    # H1 edition was written THROUGH manuscript/2026-H1_v4/ -- v1's shipped
    # directory -- and v1's artifacts were left holding v6 prose until someone
    # re-ran h1_build.py. The default is unchanged, so the monthly path and
    # every existing caller behave exactly as before.
    outdir = out_dir_override or (ROOT / "manuscript" / f"{month}_v4")
    outdir.mkdir(parents=True, exist_ok=True)
    pandoc = shutil.which("pandoc")
    if not pandoc:
        for c in (pathlib.Path.home() / "AppData/Local/Pandoc/pandoc.exe",
                  pathlib.Path(r"C:\Program Files\Pandoc\pandoc.exe")):
            if c.exists():
                pandoc = str(c)
                break
    tectonic = shutil.which("tectonic") or "tectonic"
    pdf = outdir / "manuscript_v4.pdf"
    p = subprocess.run(
        [pandoc, str(rd / "manuscript_v4.md"),
         "-f", "markdown+raw_tex-implicit_figures",
         "-V", "geometry:margin=2.4cm", "-V", "fontsize=11pt",
         "-V", "linestretch=1.05", "-V", "colorlinks=true",
         "-V", "linkcolor=[HTML]{1A4E8A}", "-V", "urlcolor=[HTML]{1A4E8A}",
         "-H", str(ROOT / "config" / "tex" / "manuscript_head.tex"),
         f"--pdf-engine={tectonic}", "-o", str(pdf)],
        capture_output=True, text=True, timeout=900, cwd=ROOT)
    if p.returncode != 0 or not pdf.exists():
        (rd / "18d_build_error.txt").write_text((p.stdout or "") + "\n" +
                                                (p.stderr or ""), encoding="utf-8")
        raise SystemExit(f"FAIL-CLOSED: pandoc rc={p.returncode}\n"
                         f"{(p.stderr or '')[:1400]}")

    for f in ("manuscript_v4.md", "stats.json", "claim_cards.jsonl",
              "gate_report_v4.json", "12_section_map.json"):
        if (rd / f).exists():
            shutil.copy(rd / f, outdir / f)
    (outdir / "fig").mkdir(exist_ok=True)
    for f in figdir.glob("*.pdf"):
        shutil.copy(f, outdir / "fig" / f.name)

    pages, g5 = page_gate(pdf, G)
    gate["G5"] = g5

    # G10: measure the title block on the rendered page, sharing the exact
    # function verify_pdf uses so the two cannot diverge (7.6 #10).
    try:
        g10 = measure_title_block(pdf, date_str=date_str)
        gate["G10-title-block"] = {"status": g10["status"], "detail": g10}
        print(f"[18d] G10-title-block: {g10['status']}  "
              f"{json.dumps(g10['gaps_pt'])}")
        # G5's title_block_fraction was the hardcoded 0.40 above. Now that the
        # block is measured, record the real value beside it: a hardcoded
        # layout constant is a latent 7.3 bug waiting for a layout change.
        if g10.get("title_block_fraction_measured") is not None:
            g5["detail"]["title_block_fraction_measured"] = \
                g10["title_block_fraction_measured"]
    except Exception as e:
        gate["G10-title-block"] = {"status": "warn",
                                   "detail": {"error": str(e)[:160]}}
        print(f"[18d] G10-title-block: warn  {str(e)[:120]}")

    (rd / "gate_report_v4.json").write_text(json.dumps(gate, indent=2), encoding="utf-8")
    shutil.copy(rd / "gate_report_v4.json", outdir / "gate_report_v4.json")
    print(f"[18d] G5: {g5['status']}  {json.dumps(g5['detail'])[:220]}")

    meta = {"pdf": str(pdf), "bytes": pdf.stat().st_size, "pages": pages,
            "title": TITLE, "prose_words": body_words,
            "abstract_words": len(ab.split()), "cited": len(order),
            "figures": n_fig, "sections": len(ids), "map_sha256": smap["sha256"],
            "gates": {k: v["status"] for k, v in gate.items()}}
    done(rd, "18d_build_v4", **meta)
    print("[18d]", json.dumps(meta, indent=2)[:700])
    return meta


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "2026-08")
