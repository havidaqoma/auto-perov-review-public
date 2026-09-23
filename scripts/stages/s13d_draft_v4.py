"""v4 draft: body first, then Research Gaps, then the Abstract LAST.

Why the order changed (Havid, 2026-09-08)
-----------------------------------------
Measured July-vs-August section similarity on the v3 output:

    Abstract          0.629      <-- authored in Python as an f-string
    Introduction      0.343      <-- half-templated framing
    Certified Frontier 0.272
    Body sections 3-7 0.055-0.183 <-- writer-drafted, genuinely different

The writer was never the problem. Repetition lived exactly in the parts a
script authored. Worse, the v3 abstract closed with a hardcoded triad
("Buried-interface chemistry, not absorber composition, now sets the
achievable open-circuit voltage." and two more) asserted every month
regardless of whether that month's evidence supported it. G3 only validates
numerals, so three unverified scientific claims shipped in the most-read
position. That is the 7.2 fabrication class in a place no gate could see.

v4 fixes the sameness and the integrity hole with one change: the closing
material is written LAST, from the finished body, by the writer.

    Phase A  body      sections 1..n-1, from stats + cards
    Phase B  gaps      reads the FULL body, cites [@work_key], target >= 4
    Phase C  abstract  reads the FULL body + gaps, NO citations at all

Numbers are never transcribed by the model
------------------------------------------
The abstract prompt forbids digits. The writer emits named placeholders
({{P_TOP_CERT}}, {{N_DEPTH}}, ...) and this script substitutes canonical
values from stats and DOI-bound cards. A number the writer cannot see is a
number the writer cannot fabricate. G3 still re-checks every numeral against
stats or a card afterwards.

Abstract carries no citations
-----------------------------
Havid's call, and it simplifies the build: v3 needed a two-pass numbering
scheme purely because the abstract inherited body numbers. With a
citation-free abstract, numbering is one pass over the body in reading order.

Run: python scripts/stages/s13d_draft_v4.py 2026-08 [section id...]
"""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from stages.util import ROOT, RUNS, done, read_jsonl, run_dir  # noqa: E402
from stages.section_map import (month_name, write_map,  # noqa: E402
                                load_map, gaps_id)

MODEL = "gemini-3.8-flash-high"

ABSTRACT_WORDS = (260, 340)   # measured: July 295, August 326

# Reused verbatim from v3 -- these are load-bearing and were tuned against
# real leaks. Do not paraphrase them.
ABBREV = {
    "PCE": "power conversion efficiency",
    "PSC": "perovskite solar cell",
    "SAM": "self-assembled monolayer",
    "ETL": "electron-transport layer",
    "HTL": "hole-transport layer",
    "ISOS": "International Summit on Organic Photovoltaic Stability",
    "MPPT": "maximum power point tracking",
    "Voc": "open-circuit voltage",
    "Jsc": "short-circuit current density",
    "FF": "fill factor",
    "WBG": "wide-bandgap",
    "T80": "time to 80% of initial performance",
}

RULES = """
WRITING RULES (violations fail an automated gate, so treat them as hard):
- You are writing one section of a MECHANISTIC AND CRITICAL REVIEW in Nature
  Reviews Materials style. Continuous scientific prose. No bullet lists, no
  headings, no sub-headings, no meta-commentary of any kind.
- NEVER write about the writing. Do not mention word counts, limits, gates,
  file paths, or what you did or did not include. Output the section text only.
- DENSITY IS THE POINT. You have a tight word budget. Every sentence must
  either state a mechanism, weigh evidence, or draw a consequence. Delete
  scene-setting, delete restatement, delete "this section will". If two
  sentences make one point, write one.
- Build an ARGUMENT. Group studies attacking the same physical problem, name
  the mechanism, say where evidence converges and where it conflicts or is
  thin. "X et al. reported Y" with no interpretation is wasted words.
- CITATION DENSITY MATTERS. Cite generously. When three or four papers support
  the same mechanistic point, cite them together as [@k1] [@k2] [@k3] behind
  one claim rather than picking a single example. Meet the citation target for
  your section, and go past it where the evidence genuinely supports a shared
  claim. Do NOT try to cite every paper in your evidence block: the block is a
  pool to select from, not a checklist. Papers that do not bear on the two or
  three problems you chose to develop should be left out.
- Be critical in the same breath as the claim: if a number is uncertified, on
  a sub-0.1 cm2 cell, or from an unlabelled stability test, say so there.
- SPELL OUT EVERY ABBREVIATION AT FIRST USE, then abbreviate freely, e.g.
  "power conversion efficiency (PCE)", "self-assembled monolayer (SAM)".
- Cite as [@work_key] straight after the sentence using that paper. Use ONLY
  the work_keys given below.
- Use ONLY the numbers given. Never invent, round, or extrapolate a value.
  Your own physical reasoning is welcome; invented data is not.
- No em-dash. Do not use: delve, harness, pivotal, seamless, leverage,
  moreover, furthermore, noteworthy, comprehensive, robust, cutting-edge,
  unlock, showcase, underscore, realm, "it is worth noting", "in conclusion",
  "a myriad of", state-of-the-art.
- Never claim WE performed an experiment. This reviews other groups' work.
"""

# Voice variation. The writer gets ONE angle per issue, rotated by month, so
# successive issues open and argue differently without any per-run randomness.
# Each angle changes the ORDER OF ATTACK, never the standard of evidence.
ANGLES = [
    "Lead with the mechanism that the month's evidence supports most strongly, "
    "then work outward to the weaker claims.",
    "Lead with the disagreement: where two or more papers this month reach "
    "incompatible conclusions about the same physical process, and what "
    "measurement would settle it.",
    "Lead with what the month's measurements cannot distinguish, then show "
    "which results survive that ambiguity.",
    "Lead with the quantitative frontier for this physics, then ask what "
    "the reported evidence actually licenses.",
]


def _agy() -> str:
    exe = shutil.which("agy")
    if not exe:
        raise SystemExit("FAIL-CLOSED: agy not on PATH (Q55 writer, no fallback)")
    return exe


def write_llm(prompt: str, timeout: int = 1200, attempts: int = 3) -> str:
    exe = _agy()
    last = ""
    for i in range(attempts):
        p = subprocess.run(
            [exe, "-p", prompt, "--model", MODEL,
             "--dangerously-skip-permissions", "--print-timeout", "900s"],
            capture_output=True, text=True, timeout=timeout, cwd=ROOT)
        out = (p.stdout or "").strip()
        if p.returncode == 0 and len(out) > 200:
            return out
        last = f"rc={p.returncode} out={len(out)}B err={(p.stderr or '')[:150]!r}"
        if i < attempts - 1:
            time.sleep(2 ** i + 1)
    raise RuntimeError(f"agy failed after {attempts}: {last}")


# Prose hygiene lives in ONE place now. Three divergent copies of this filter
# used to exist (here, s18d's G4, s19's strip()), and the build-side copy was
# the narrowest: "I have launched the search command and will wait for it to
# finish." survived this filter AND passed G4, reaching the shipped August v4
# PDF under the section 8 heading. See stages/hygiene.py.
from stages.hygiene import (AGENT_NARRATION, SELF_REF,  # noqa: E402,F401
                            strip_narration)


def clean(raw: str) -> str:
    """Strip code fences, stray headings, and narration lines.

    Narration removal is delegated to stages.hygiene so the draft filter and
    gate G4 can never diverge again. Removed lines are printed rather than
    silently dropped: a writer that narrates once per section is a prompt
    problem worth seeing.
    """
    t = re.sub(r"^```(?:\w+)?|```$", "", raw.strip(), flags=re.M).strip()
    t = re.sub(r"^#+ .*$", "", t, flags=re.M)
    t, removed = strip_narration(t)
    for ln in removed:
        print(f"[13d]   STRIPPED narration: {ln[:90]}")
    return t


def _v(c, k):
    src = c["stability"] if k in ("t80_h", "duration_h") else c["performance"]
    f = (src or {}).get(k)
    return f["value"] if isinstance(f, dict) and f.get("value") is not None else None


def evidence(cards: list, axes: list, limit: int = 34) -> str:
    sel = [c for c in cards if c["axis"] in axes]
    sel.sort(key=lambda c: -(_v(c, "pce_certified") or _v(c, "pce_champion") or 0))
    out = []
    for c in sel[:limit]:
        bits = []
        for k, lab in (("pce_certified", "CERTIFIED"), ("pce_champion", "champion"),
                       ("pce_stabilised", "stabilised"), ("active_area_cm2", "area cm2")):
            v = _v(c, k)
            if v is not None:
                bits.append(f"{lab} {v}")
        if c["stability"].get("protocol"):
            bits.append(f"protocol {c['stability']['protocol']}")
        t = _v(c, "t80_h")
        if t:
            bits.append(f"T80 {t} h")
        out.append(f"[@{c['work_key']}] {c['venue']} | {c['device']['architecture']} | "
                   f"{'; '.join(bits) if bits else 'no numeric field'}\n"
                   f"    {c['title']}\n    FINDINGS: "
                   f"{' | '.join(x['text'] for x in c['claims'][:2])}")
    return "\n".join(out)


def body_digest(secs: dict, smap: dict, budget: int = 8000) -> str:
    """The finished body, trimmed, for the gaps and abstract prompts.

    Phases B and C exist to react to what the body ACTUALLY says. Handing the
    writer stats alone would recreate the v3 failure: closing text that could
    have been written before the body existed, and therefore reads the same
    every month.
    """
    parts, order = [], {s["id"]: s for s in smap["sections"]}
    for sid in sorted(secs, key=int):
        s = order.get(sid)
        if not s or s["role"] == "gaps":
            continue
        body = re.sub(r"\[@[^\]\s]+\]", "", secs[sid])
        body = re.sub(r"\s+", " ", body).strip()
        parts.append(f"### {s['title']}\n{body}")
    txt = "\n\n".join(parts)
    if len(txt) > budget:                       # keep heads, drop tails evenly
        per = budget // max(len(parts), 1)
        txt = "\n\n".join(p[:per] for p in parts)
    return txt


def prior_closing_block(month: str) -> str:
    """The prior issue's closing sentences, quoted so the writer can avoid them.

    July 2026 failed G8 on seven shared 12-word shingles, all inside one
    sentence: "Next month's literature would be far more comparable if authors
    reported certified steady-state power tracking on ... apertures alongside
    accredited T80 lifetimes under ... ISOS protocols." June had closed with
    almost exactly that sentence.

    The cause was 4.1c, not the model: the prompt said "End with one or two
    sentences on what would make next month's literature more useful to a
    reader trying to compare results", which is a SENTENCE, and the writer
    returned it both months. A recurring job needs its recurring output shown
    to it, or nothing in the prompt makes month N+1 differ from month N.
    """
    prev = sorted(p for p in RUNS.glob("*.active")
                  if p.name[:7] < month)
    if not prev:
        return ""
    rd = RUNS / prev[-1].read_text(encoding="utf-8").strip()
    f = rd / "draft_v4" / "sec8.md"
    if not f.exists():
        return ""
    lines = [ln.strip() for ln in f.read_text(encoding="utf-8").split("\n")
             if ln.strip()]
    if not lines:
        return ""
    tail = " ".join(lines[-1].split()[-90:])
    return (f"\nLAST MONTH'S ISSUE CLOSED WITH THIS TEXT:\n\"{tail}\"\n"
            "Your closing must not reuse its sentence shape, its list of "
            "recommended measurements, or any twelve consecutive words of it. "
            "A gate compares the two and fails the build on a reused span.\n")


def trend_block(month: str, S: dict) -> tuple[str, dict]:
    """Month-over-month observations, or an explicit 'no prior' notice.

    Two data points are not a trend. Everything here is worded as an
    observation with explicit n, and the prompt says so, because the fastest
    way to get a fabricated trend is to hand a model two numbers and the word
    'trend'.
    """
    hist = ROOT / "stats_history"
    prior = sorted(p for p in hist.glob("*.json") if p.stem < month) if hist.exists() else []
    if not prior:
        return ("NO PRIOR ISSUE. Do not write any comparison, trend, "
                "increase or decrease. This is the first issue on record.", {})
    P = json.loads(prior[-1].read_text(encoding="utf-8"))
    pm = prior[-1].stem
    lines, deltas = [], {}
    for key, lab in (("audit.corpus.certified.pct", "certified reporting share"),
                     ("audit.corpus.efficiency_stated.pct", "efficiency reporting share"),
                     ("corpus.n", "indexed works"),
                     ("selection.n_depth", "depth-tier papers")):
        if key in S and key in P and P[key]:
            lines.append(f"- {lab}: {P[key]} in {pm} -> {S[key]} in {month}")
            deltas[key] = {"prev": P[key], "now": S[key], "prev_month": pm}
    if not lines:
        return ("NO COMPARABLE PRIOR FIELDS. Do not write any comparison.", {})
    return ("PRIOR ISSUE COMPARISON (exactly two data points, so these are "
            "OBSERVATIONS, not trends. You may state at most ONE such "
            "observation, you must give both numbers and both months, and you "
            "must not use the words trend, trajectory, accelerating or "
            "increasingly):\n" + "\n".join(lines), deltas)


def draft(month: str) -> dict:
    rd = run_dir(month)
    S = json.loads((rd / "stats.json").read_text(encoding="utf-8"))
    cards = read_jsonl(rd / "claim_cards.jsonl")
    dd = rd / "draft_v4"
    dd.mkdir(exist_ok=True)
    MON = month_name(month)

    smap = write_map(month, S)
    sections = smap["sections"]
    gid = gaps_id(smap)
    angle = ANGLES[(int(month[:4]) * 12 + int(month[5:7])) % len(ANGLES)]

    cert = sorted(((_v(c, "pce_certified"), c) for c in cards if _v(c, "pce_certified")),
                  key=lambda x: -x[0])
    areas = sorted(((_v(c, "active_area_cm2"), c) for c in cards
                    if _v(c, "active_area_cm2")), key=lambda x: -x[0])
    t80 = sorted(((_v(c, "t80_h"), c) for c in cards if _v(c, "t80_h")),
                 key=lambda x: -x[0])
    n_proto = len([c for c in cards if c["stability"].get("protocol")])
    n = S["corpus.n"]

    top_cert = "; ".join(f"{v}% ({c['venue']}, {c['device']['architecture']}) "
                         f"[@{c['work_key']}]" for v, c in cert[:8])
    top_area = "; ".join(f"{a} cm2 at {_v(c,'pce_champion') or _v(c,'pce_certified')}% "
                         f"[@{c['work_key']}]" for a, c in areas[:5])
    top_t80 = "; ".join(f"{int(v)} h [@{c['work_key']}]" for v, c in t80)
    protos = "; ".join(f"{c['stability']['protocol']} [@{c['work_key']}]"
                       for c in cards if c["stability"].get("protocol"))
    trends, deltas = trend_block(month, S)

    threads = ", ".join(s["title"].lower() for s in sections
                        if s["role"] == "mechanism")

    # ---------------- Phase A prompts: body ----------------
    tasks, ceil_of, cite_of = {}, {}, {}
    for s in sections:
        ceil_of[s["id"]] = s["ceiling"]
        cite_of[s["id"]] = s["cite_target"]

    for s in sections:
        sid, role = s["id"], s["role"]
        if role == "intro":
            # Dictating phrasing here is what produced the highest-similarity
            # section in the whole issue. G8 on the v4 build listed six shared
            # 12-word shingles and every one traced to THIS prompt: "whether a
            # claimed efficiency is verifiable, whether it survives at module
            # area", "the month's headline numbers are strong, the evidence
            # behind them is unevenly reported". The writer was obediently
            # echoing my sentences back, so intro scored 0.064 while genuinely
            # free sections scored 0.02.
            #
            # Fix the prompt, not the gate: state the JOB, never the wording.
            tasks[sid] = f"""Write the Introduction of a mechanistic and critical review of
perovskite photovoltaics covering papers published in {MON}. AT MOST {s['ceiling']} words.
This is a SHORT, DENSE introduction. Three or four paragraphs at most.
{RULES}
ANGLE FOR THIS ISSUE: {angle}

Cover these four jobs. Choose your own wording for each; do not reuse phrasing
from any previous issue of this review.
1. Locate the field's open problem. The frontier is no longer raw efficiency.
   Say in your own words what it has become, drawing on the sections that
   follow: verification, area, and operating lifetime.
2. State once, in one sentence, the scale of the evidence base: {n} indexed
   works met the scope gate in {MON} and {S['selection.n_depth']} were read
   closely.
3. Name the mechanistic threads this issue follows: {threads}.
4. Declare the critical stance. This review distinguishes what the month's
   literature verified from what it asserted.

Spell out power conversion efficiency (PCE) on first use.
Do not cite individual papers here."""
        elif role == "frontier":
            tasks[sid] = f"""Write "{s['title']}". AT MOST {s['ceiling']} words.
Be terse and quantitative. Two or three paragraphs.
{RULES}
ANGLE FOR THIS ISSUE: {angle}
Independently certified efficiencies this month, highest first:
{top_cert}
Largest reported areas: {top_area}
Only {len(cert)} of {len(cards)} closely read papers reported an independently
certified efficiency.
CITATION TARGET FOR THIS SECTION: at least {s['cite_target']} distinct papers.
Establish what the month VERIFIED as opposed to claimed: where the certified
ceiling sits for each device family, and how far the best self-reported values
run ahead of the best certified ones.
Make the point, in your own words, that a champion value measured on a tiny
laboratory cell and an independently certified value measured at module area
are not the same kind of evidence. Do not reuse phrasing from a previous issue
of this review."""
        elif role == "mechanism":
            ev = evidence(cards, s["axes"])
            extra = ""
            if s["axis"] == "stability":
                extra = (f"\nEvery T80 reported this month: {top_t80 or 'none'}\n"
                         f"Every ISOS protocol label: {protos or 'none'}\n"
                         f"Only {len(t80)} of {len(cards)} closely read papers "
                         f"reported a T80 value and {n_proto} named an ISOS "
                         f"protocol. Treat that scarcity as a finding.")
            if s["axis"] == "scale_up":
                extra = f"\nArea and efficiency pairs this month: {top_area}\n"
            folded = [a for a in s["axes"] if a != s["axis"]]
            if folded:
                extra += (f"\nThis section also carries the month's work on "
                          f"{', '.join(folded)}; integrate it, do not append it.")
            tasks[sid] = f"""Write "{s['title']}". AT MOST {s['ceiling']} words.
This must be DENSE and WELL CITED. Pick the two or three physical problems this
month's work actually attacks here and develop those properly, but support each
claim with ALL the papers below that bear on it, cited together.
CITATION TARGET FOR THIS SECTION: at least {s['cite_target']} distinct papers.
Falling short of that target is a failure; group citations behind shared claims
to reach it without padding the prose.
{RULES}
ANGLE FOR THIS ISSUE: {angle}
{extra}
EVIDENCE (cite by the [@key] shown; every number is quoted verbatim from that
paper's own abstract):
{ev}"""

    # ---------------- run Phase A ----------------
    only = [a for a in sys.argv[2:] if a.isdigit()] or None
    secs, log = {}, []
    map_sha = smap["sha256"]
    stamp_f = dd / "_map.sha"
    if stamp_f.exists() and stamp_f.read_text(encoding="utf-8").strip() != map_sha:
        # The section map changed, so cached prose was written to different
        # titles, ceilings and evidence folds. Reusing it would silently ship
        # last map's text under this map's headings.
        for old in dd.glob("sec*.md"):
            old.unlink()
        print("[13d] section map changed; cleared cached draft_v4 sections")
    stamp_f.write_text(map_sha, encoding="utf-8")

    body_ids = [s["id"] for s in sections if s["role"] != "gaps"]
    for sid in body_ids:
        f = dd / f"sec{sid}.md"
        if only and sid not in only and f.exists():
            secs[sid] = f.read_text(encoding="utf-8").strip()
            print(f"[13d] sec{sid} KEPT ({len(secs[sid].split())}w)")
            continue
        if not only and f.exists():
            prev = f.read_text(encoding="utf-8").strip()
            nw = len(prev.split())
            if 0.45 * ceil_of[sid] <= nw <= 1.25 * ceil_of[sid] and not SELF_REF.search(prev):
                secs[sid] = prev
                print(f"[13d] sec{sid} KEPT ({nw}w)")
                continue
        secs[sid] = _attempt(sid, tasks[sid], ceil_of[sid], cite_of[sid], f, log)

    # ---------------- Phase B: Research Gaps, reads the finished body -------
    digest = body_digest(secs, smap)
    gs = next(s for s in sections if s["id"] == gid)
    gaps_task = f"""Write "Research Gaps and Outlook". AT MOST {gs['ceiling']} words.
{RULES}
ANGLE FOR THIS ISSUE: {angle}

You are writing the CLOSING section, and you can see the whole review below.
Do not summarise it. Identify what the month's evidence, as actually argued in
these sections, does NOT establish.

Give four concrete research gaps. Each must name the measurement or experiment
that would close it, and each must follow from something the body actually
says, not from general knowledge of the field.
CITE at least {gs['cite_target']} papers from the month by [@work_key] where they
ground a gap. Use ONLY keys that appear in the review below.

QUANTITATIVE GROUND TRUTH (use these numbers only, do not invent others):
- best certified this month {cert[0][0]}% ({cert[0][1]['device']['architecture']}),
  {len(cert)} of {len(cards)} closely read papers reported any certified value
- {len(t80)} papers reported a T80 lifetime, longest {int(t80[0][0]) if t80 else 0} h
- {n_proto} papers named an ISOS protocol
- largest reported aperture {areas[0][0] if areas else 0} cm2
- scale-up was addressed by {S.get('axes.scale_up.n_corpus', 0)} of {n} works

{trends}

THE REVIEW AS WRITTEN:
{digest}

End by naming what the field should MEASURE differently, in your own words.
State the job, not a wish: identify which specific comparison this month's
evidence could not support, and what reporting would have supported it. Do not
recycle a generic call for standardised reporting.
{prior_closing_block(month)}"""

    f = dd / f"sec{gid}.md"
    if not only or gid in only or not f.exists():
        secs[gid] = _attempt(gid, gaps_task, gs["ceiling"], gs["cite_target"], f, log)
    else:
        secs[gid] = f.read_text(encoding="utf-8").strip()
        print(f"[13d] sec{gid} KEPT ({len(secs[gid].split())}w)")

    # ---------------- Phase C: Abstract, LAST, no citations, no digits ------
    full = body_digest({**secs}, smap, budget=9000) + "\n\n### Research Gaps\n" + \
        re.sub(r"\[@[^\]\s]+\]", "", secs[gid])
    abs_task = f"""Write the ABSTRACT of this review. Between {ABSTRACT_WORDS[0]} and
{ABSTRACT_WORDS[1]} words, one paragraph.
{RULES}

You can see the entire finished review below. The abstract must reflect what
THIS issue actually argues. Do not write a generic perovskite abstract.

TWO HARD CONSTRAINTS, both machine-checked:

1. NO CITATIONS. Do not write [@key], [1], [2] or any bracketed marker. This
   abstract carries no reference numbers at all.

2. NO DIGITS. Do not write any number, in figures or in words. Where a number
   belongs, write the exact placeholder token from this list and nothing else:
     {{{{N_CORPUS}}}}     number of indexed works this month
     {{{{N_DEPTH}}}}      number read closely
     {{{{N_CERT}}}}       how many reported a certified efficiency
     {{{{P_TOP_CERT}}}}   the highest certified efficiency, with % sign
     {{{{P_TOP_SJ}}}}     highest certified single junction, with % sign
     {{{{A_MAX}}}}        largest reported aperture area, with unit
     {{{{P_AREA_MAX}}}}   the certified efficiency at that largest area
     {{{{N_T80}}}}        how many reported a T80 lifetime
     {{{{H_T80_MAX}}}}    the longest reported T80, with unit
     {{{{N_PROTO}}}}      how many named an ISOS protocol
     {{{{PCT_EFF}}}}      share of abstracts stating an efficiency, with %
     {{{{PCT_CERT}}}}     share stating independent certification, with %
   A script substitutes the real values afterwards. If you write a digit
   yourself the abstract is rejected.

Cover, in this order: what the month's corpus was and how much was read
closely; what the certified frontier now shows and through which mechanisms;
the area penalty; the state of operational-stability evidence; the reporting
completeness picture; and the mechanistic conclusions THIS issue reached.

The conclusions must be the ones argued in the sections below. Do not assert a
general claim about the field that this month's evidence does not support. If
the evidence for a conclusion is thin, say it is thin.

THE FINISHED REVIEW:
{full}"""

    af = dd / "abstract.md"
    ab = ""
    for attempt in range(3):
        print(f"[13d] abstract{' retry ' + str(attempt) if attempt else ''} ...",
              flush=True)
        cand = clean(write_llm(abs_task))
        cand = re.sub(r"^\s*abstract\s*[:.]?\s*", "", cand, flags=re.I).strip()
        bad_cite = re.findall(r"\[@?[\w.\-/]+\]", cand)
        if bad_cite:
            print(f"[13d]   REJECT abstract has citations {bad_cite[:4]}")
            continue
        stray = re.findall(r"(?<!\{)\b\d[\d.,]*\b(?!\})", cand)
        if stray:
            print(f"[13d]   REJECT abstract has literal digits {stray[:6]}")
            continue
        ab = cand
        break
    if not ab:
        raise SystemExit("FAIL-CLOSED: abstract failed the no-citation / "
                         "no-digit contract in 3 attempts")
    af.write_text(ab, encoding="utf-8")
    print(f"[13d]   abstract {len(ab.split())}w (placeholders unresolved)")
    log.append({"stage": "13d_abstract", "cli": "agy", "model": MODEL,
                "words": len(ab.split())})

    if log:
        with (rd / "tokens.jsonl").open("a", encoding="utf-8") as fh:
            for r in log:
                fh.write(json.dumps(r) + "\n")

    tot = sum(len(v.split()) for v in secs.values())
    meta = {"words": {k: len(v.split()) for k, v in secs.items()},
            "abstract_words_raw": len(ab.split()),
            "total_words": tot,
            "sections": len(sections),
            "map_sha256": map_sha,
            "angle_index": (int(month[:4]) * 12 + int(month[5:7])) % len(ANGLES),
            "trend_deltas": deltas,
            "writer": f"agy/{MODEL}"}
    done(rd, "13d_draft_v4", **meta)
    print("[13d]", json.dumps(meta)[:400])
    return meta


def _attempt(sid: str, task: str, ceiling: int, cite_target: int,
             f: pathlib.Path, log: list) -> str:
    """Draft one section with the word-band and citation-target retries."""
    for attempt in range(3):
        print(f"[13d] sec{sid}{' retry ' + str(attempt) if attempt else ''} ...",
              flush=True)
        cand = clean(write_llm(task))
        nw = len(cand.split())
        if nw < 0.45 * ceiling:
            print(f"[13d]   REJECT {nw}w < floor {int(0.45 * ceiling)}")
            continue
        if nw > 1.35 * ceiling:
            print(f"[13d]   REJECT {nw}w > 135% of ceiling {ceiling}")
            continue
        ncit = len(set(re.findall(r"\[@([^\]\s]+)\]", cand)))
        if ncit < cite_target:
            print(f"[13d]   REJECT {ncit} citations < target {cite_target}")
            continue
        f.write_text(cand, encoding="utf-8")
        print(f"[13d]   {nw}w (ceiling {ceiling}), {ncit} cites")
        log.append({"stage": f"13d_s{sid}", "cli": "agy", "model": MODEL,
                    "words": nw})
        return cand
    raise SystemExit(f"FAIL-CLOSED: sec{sid} no usable prose in 3 attempts")


if __name__ == "__main__":
    draft(sys.argv[1] if len(sys.argv) > 1 else "2026-08")
