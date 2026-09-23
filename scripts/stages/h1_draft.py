"""H1 draft: Phase A body -> B gaps -> C abstract, for the half-year issue.

Reuses s13d_draft_v4 BY IMPORT: RULES, ANGLES, write_llm, clean, _attempt,
evidence, body_digest, _v. Those carry every paid-for lesson -- the unified
narration filter, the "state the job, never the wording" prompts, the
word-band and citation-target retries, the no-digit/no-citation abstract
contract. Forking them would recreate the three-divergent-copies failure that
put "I have launched the search command" into a shipped PDF.

Authorship order is the v4 order and for the same reason (handbook 4.1b): the
parts a script authored were the repetitive ones, so the writer writes the
closing material LAST, reacting to what the body actually says.

What is new here, because six months affords what one month cannot:
- a TRAJECTORY section, which gets the month-by-month frontier series
- a SYNTHESIS section, which reads the finished mechanism sections and says
  what they mean together
- an AUDIT section, which gets the reporting-practice series with its spread
- period-scoped abstract placeholders

Every one of those is given EVIDENCE and a JOB, never a sentence to echo.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from stages.util import read_jsonl  # noqa: E402
from stages.s13d_draft_v4 import (ANGLES, MODEL, RULES, _attempt,  # noqa: E402
                                  _v, body_digest, clean, evidence, write_llm)
from stages.h1_aggregate import EDITION, edition_dir  # noqa: E402
from stages.h1_section_map import gaps_id  # noqa: E402

PERIOD = "January-June 2026"
ABSTRACT_WORDS = (380, 520)  # config/h1.yaml abstract_h1.word_band
MONTH_LAB = {"2026-01": "January", "2026-02": "February", "2026-03": "March",
             "2026-04": "April", "2026-05": "May", "2026-06": "June"}


def series_block(S: dict) -> str:
    """The month-by-month numbers, as evidence for the trajectory section."""
    months = S["frontier.months"]
    lab = [MONTH_LAB.get(m, m) for m in months]
    cert = S["frontier.top_certified_series"]
    champ = S["frontier.top_champion_series"]
    ncert = S["frontier.n_certified_series"]
    corpus = S["series.corpus_n"]
    lines = ["Month | indexed works | best certified PCE | best self-reported | "
             "papers reporting any certified value"]
    for i, m in enumerate(lab):
        lines.append(f"{m} | {corpus[i]} | {cert[i]} | {champ[i]} | {ncert[i]}")
    d = S.get("frontier.certified_delta_pp")
    if d is not None:
        lines.append(
            f"\nThe best certified value moved from {S['frontier.h1_first_certified']}% "
            f"in {lab[0]} to {S['frontier.h1_last_certified']}% in {lab[-1]}, "
            f"a change of {d} percentage points over the half year.")
    return "\n".join(lines)


def audit_block(S: dict) -> str:
    """Reporting-practice rates with their month-to-month spread."""
    keys = ["efficiency_stated", "certified", "stabilised", "area_stated",
            "isos_label", "hysteresis"]
    lines = ["Reporting practice across the half year, pooled over all six "
             "months (summed numerator / summed denominator, NOT an average "
             "of monthly rates):"]
    for k in keys:
        pct = S.get(f"audit.h1.{k}.pct")
        lo = S.get(f"audit.h1.{k}.month_min_pct")
        hi = S.get(f"audit.h1.{k}.month_max_pct")
        n = S.get(f"audit.h1.{k}.n")
        den = S.get(f"audit.h1.{k}.denominator")
        if pct is None:
            continue
        lines.append(f"- {k.replace('_',' ')}: {pct}% ({n} of {den}); "
                     f"monthly range {lo}% to {hi}%")
    return "\n".join(lines)


def coverage_block(S: dict) -> str:
    cov = S.get("coverage.card_share_pct") or {}
    parts = [f"{MONTH_LAB.get(m,m)} {v}%" for m, v in sorted(cov.items())]
    return ("Share of the closely read papers contributed by each month: "
            + ", ".join(parts) + ".")


def draft() -> dict:
    d = edition_dir()
    S = json.loads((d / "stats.json").read_text(encoding="utf-8"))
    cards = read_jsonl(d / "claim_cards.jsonl")
    smap = json.loads((d / "12_section_map.json").read_text(encoding="utf-8"))
    dd = d / "draft_h1"
    dd.mkdir(exist_ok=True)

    sections = smap["sections"]
    gid = gaps_id(smap)
    # Rotate by period, deterministically: same edition -> same angle.
    from stages.h1_section_map import _period_index
    angle = ANGLES[_period_index(EDITION) % len(ANGLES)]

    cert = sorted(((_v(c, "pce_certified"), c) for c in cards
                   if _v(c, "pce_certified")), key=lambda x: -x[0])
    areas = sorted(((_v(c, "active_area_cm2"), c) for c in cards
                    if _v(c, "active_area_cm2")), key=lambda x: -x[0])
    t80 = sorted(((_v(c, "t80_h"), c) for c in cards if _v(c, "t80_h")),
                 key=lambda x: -x[0])
    n_proto = len([c for c in cards if (c.get("stability") or {}).get("protocol")])
    n = S["corpus.n"]

    top_cert = "; ".join(
        f"{v}% ({c['venue']}, {c['device']['architecture']}, "
        f"{MONTH_LAB.get(c.get('source_month'), '')}) [@{c['work_key']}]"
        for v, c in cert[:12])
    top_area = "; ".join(
        f"{a} cm2 at {_v(c,'pce_champion') or _v(c,'pce_certified')}% "
        f"[@{c['work_key']}]" for a, c in areas[:6])
    top_t80 = "; ".join(f"{int(v)} h [@{c['work_key']}]" for v, c in t80[:20])
    protos = "; ".join(
        f"{c['stability']['protocol']} [@{c['work_key']}]"
        for c in cards if (c.get("stability") or {}).get("protocol"))[:2000]

    threads = ", ".join(s["title"].lower() for s in sections
                        if s["role"] == "mechanism")
    series = series_block(S)
    audit = audit_block(S)
    coverage = coverage_block(S)

    tasks, ceil_of, cite_of = {}, {}, {}
    for s in sections:
        ceil_of[s["id"]] = s["ceiling"]
        cite_of[s["id"]] = s["cite_target"]

    for s in sections:
        sid, role = s["id"], s["role"]
        if role == "intro":
            tasks[sid] = f"""Write the Introduction of a mechanistic and critical review of
perovskite photovoltaics covering papers published across {PERIOD}. AT MOST {s['ceiling']} words.
This is a SHORT, DENSE introduction. Three or four paragraphs at most.
{RULES}
ANGLE FOR THIS ISSUE: {angle}

Cover these four jobs. Choose your own wording for each.
1. Locate the field's open problem. The frontier is no longer raw efficiency.
   Say in your own words what it has become, drawing on what follows:
   verification, area, and operating lifetime.
2. State once, in one sentence, the scale of the evidence base: {n} indexed
   works met the scope gate across the six months and {S['selection.n_depth']}
   were read closely.
3. Name the mechanistic threads this issue follows: {threads}.
4. Say why a half-year view is worth writing: a single month shows a value,
   six months show whether it moved. Do not overclaim what six months can
   settle.

Spell out power conversion efficiency (PCE) on first use.
Do not cite individual papers here."""

        elif role == "trajectory":
            tasks[sid] = f"""Write "{s['title']}". AT MOST {s['ceiling']} words.
Be terse and quantitative. Three or four paragraphs.
{RULES}
ANGLE FOR THIS ISSUE: {angle}

THE MONTH-BY-MONTH RECORD:
{series}

{coverage}

Independently certified efficiencies across the half year, highest first:
{top_cert}
Largest reported areas: {top_area}
Only {len(cert)} of {len(cards)} closely read papers reported an independently
certified efficiency.
CITATION TARGET FOR THIS SECTION: at least {s['cite_target']} distinct papers.

Your job: establish what the half year VERIFIED as opposed to claimed, and
whether the certified ceiling actually MOVED or merely repeated. A single month
cannot answer that; six can. Be careful and honest about what a six-point
series can support: say plainly if the movement is within the noise of which
papers happened to be indexed, and note that most of the leading certified
values are multi-junction devices rather than single junctions.
Do not describe the trend as a rate or a projection."""

        elif role == "mechanism":
            ev = evidence(cards, s["axes"], limit=44)
            extra = ""
            if s["axis"] == "stability":
                extra = (f"\nEvery T80 reported across the half year (longest first): "
                         f"{top_t80 or 'none'}\nISOS protocol labels: {protos or 'none'}\n"
                         f"Only {len(t80)} of {len(cards)} closely read papers "
                         f"reported a T80 value and {n_proto} named an ISOS "
                         f"protocol. Treat that scarcity as a finding.")
            if s["axis"] == "scale_up":
                extra = f"\nArea and efficiency pairs: {top_area}\n"
            folded = [a for a in s["axes"] if a != s["axis"]]
            if folded:
                extra += (f"\nThis section also carries the work on "
                          f"{', '.join(folded)}; integrate it, do not append it.")
            tasks[sid] = f"""Write "{s['title']}". AT MOST {s['ceiling']} words.
This must be DENSE and WELL CITED. Pick the two or three physical problems this
literature actually attacks and develop those properly, supporting each claim
with ALL the papers below that bear on it, cited together.
CITATION TARGET FOR THIS SECTION: at least {s['cite_target']} distinct papers.
Falling short of that target is a failure; group citations behind shared claims
to reach it without padding the prose.
{RULES}
ANGLE FOR THIS ISSUE: {angle}

You are covering SIX MONTHS, not one. Where the evidence supports it, say
whether the approach to this problem changed over the period, and where papers
from different months reach incompatible conclusions about the same physical
process. Do not manufacture a narrative of progress the papers do not support.
{extra}
EVIDENCE (cite by the [@key] shown; every number is quoted verbatim from that
paper's own abstract):
{ev}"""

    # ---------------- Phase A ----------------
    only = [a for a in sys.argv[1:] if a.isdigit()] or None
    secs, log = {}, []
    map_sha = smap["sha256"]
    stamp_f = dd / "_map.sha"
    if stamp_f.exists() and stamp_f.read_text(encoding="utf-8").strip() != map_sha:
        for old in dd.glob("sec*.md"):
            old.unlink()
        print("[h1-13] section map changed; cleared cached sections")
    stamp_f.write_text(map_sha, encoding="utf-8")

    from stages.hygiene import SELF_REF
    body_ids = [s["id"] for s in sections
                if s["role"] not in ("gaps", "synthesis", "audit")]
    for sid in body_ids:
        f = dd / f"sec{sid}.md"
        if only and sid not in only and f.exists():
            secs[sid] = f.read_text(encoding="utf-8").strip()
            print(f"[h1-13] sec{sid} KEPT ({len(secs[sid].split())}w)")
            continue
        if not only and f.exists():
            prev = f.read_text(encoding="utf-8").strip()
            nw = len(prev.split())
            if 0.45 * ceil_of[sid] <= nw <= 1.25 * ceil_of[sid] and not SELF_REF.search(prev):
                secs[sid] = prev
                print(f"[h1-13] sec{sid} KEPT ({nw}w)")
                continue
        secs[sid] = _attempt(sid, tasks[sid], ceil_of[sid], cite_of[sid], f, log)

    # ---------------- Phase B1: synthesis, reads the mechanism sections -----
    syn = next((s for s in sections if s["role"] == "synthesis"), None)
    if syn:
        digest = body_digest(secs, smap, budget=9000)
        syn_task = f"""Write "{syn['title']}". AT MOST {syn['ceiling']} words.
{RULES}
ANGLE FOR THIS ISSUE: {angle}

You can see the finished mechanism sections below. Do NOT summarise them.

Your job is the one thing a single-month review cannot do: say what these
separate mechanism literatures mean WHEN READ TOGETHER. Find where two axes are
describing the same physical failure through different measurements, where they
make incompatible demands on the same layer, and where a gain claimed on one
axis is paid for on another. Ground every such claim in specific papers.
CITE at least {syn['cite_target']} papers by [@work_key]. Use ONLY keys that
appear in the sections below.

If the axes do NOT converge on a shared story, say that plainly. A forced
synthesis is worse than an honest statement that the literatures are still
separate.

THE MECHANISM SECTIONS AS WRITTEN:
{digest}"""
        f = dd / f"sec{syn['id']}.md"
        if not only or syn["id"] in only or not f.exists():
            secs[syn["id"]] = _attempt(syn["id"], syn_task, syn["ceiling"],
                                       syn["cite_target"], f, log)
        else:
            secs[syn["id"]] = f.read_text(encoding="utf-8").strip()

    # ---------------- Phase B2: audit ----------------
    aud = next((s for s in sections if s["role"] == "audit"), None)
    if aud:
        aud_task = f"""Write "{aud['title']}". AT MOST {aud['ceiling']} words.
{RULES}
ANGLE FOR THIS ISSUE: {angle}

{audit}

{coverage}

Your job: say what these reporting rates mean for a reader trying to compare
devices across the field, and whether practice changed over the six months.
Use the monthly RANGE, not just the pooled rate: a rate that swung widely and
one that sat flat are different findings, and the range is given above.

Be careful with causation. These are detection rates over abstracts, not audits
of what the papers did; an unstated protocol is not a protocol that was not
followed. Say that limitation once, in your own words.
CITE at least {aud['cite_target']} papers by [@work_key] where a specific paper
illustrates good or absent reporting."""
        f = dd / f"sec{aud['id']}.md"
        if not only or aud["id"] in only or not f.exists():
            secs[aud["id"]] = _attempt(aud["id"], aud_task, aud["ceiling"],
                                       aud["cite_target"], f, log)
        else:
            secs[aud["id"]] = f.read_text(encoding="utf-8").strip()

    # ---------------- Phase B3: gaps, reads the WHOLE body ----------------
    digest = body_digest(secs, smap, budget=10000)
    gs = next(s for s in sections if s["id"] == gid)
    gaps_task = f"""Write "Research Gaps and Outlook". AT MOST {gs['ceiling']} words.
{RULES}
ANGLE FOR THIS ISSUE: {angle}

You are writing the CLOSING section and you can see the whole review below.
Do not summarise it. Identify what the half year's evidence, as actually argued
in these sections, does NOT establish.

Give four or five concrete research gaps. Each must name the measurement or
experiment that would close it, and each must follow from something the body
actually says, not from general knowledge of the field.
CITE at least {gs['cite_target']} papers by [@work_key] where they ground a gap.
Use ONLY keys that appear in the review below.

QUANTITATIVE GROUND TRUTH (use these numbers only, do not invent others):
- best certified across the half year {cert[0][0]}% ({cert[0][1]['device']['architecture']}),
  {len(cert)} of {len(cards)} closely read papers reported any certified value
- {len(t80)} papers reported a T80 lifetime, longest {int(t80[0][0]) if t80 else 0} h
- {n_proto} papers named an ISOS protocol
- largest reported aperture {areas[0][0] if areas else 0} cm2

{series}

THE REVIEW AS WRITTEN:
{digest}

End by naming what the field should MEASURE differently, in your own words.
State the job, not a wish: identify which specific comparison this half year's
evidence could not support, and what reporting would have supported it. Do not
recycle a generic call for standardised reporting."""

    f = dd / f"sec{gid}.md"
    if not only or gid in only or not f.exists():
        secs[gid] = _attempt(gid, gaps_task, gs["ceiling"], gs["cite_target"], f, log)
    else:
        secs[gid] = f.read_text(encoding="utf-8").strip()

    # ---------------- Phase C: abstract, LAST, no citations, no digits ------
    full = body_digest({**secs}, smap, budget=11000)
    abs_task = f"""Write the ABSTRACT of this review. Between {ABSTRACT_WORDS[0]} and
{ABSTRACT_WORDS[1]} words, one paragraph.
{RULES}

You can see the entire finished review below. The abstract must reflect what
THIS issue actually argues. Do not write a generic perovskite abstract.

TWO HARD CONSTRAINTS, both machine-checked:

1. NO CITATIONS. Do not write [@key], [1], [2] or any bracketed marker.

2. NO DIGITS. Do not write any number, in figures or in words. Where a number
   belongs, write the exact placeholder token from this list and nothing else:
     {{{{N_CORPUS}}}}     indexed works across the six months
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
     {{{{N_MONTHS}}}}     how many months the issue covers
   A script substitutes the real values afterwards. If you write a digit
   yourself the abstract is rejected.

Cover, in this order: what the corpus was and how much was read closely; what
the certified frontier showed ACROSS the period and whether it moved; through
which mechanisms; the area penalty; the state of operational-stability
evidence; the reporting completeness picture; and the mechanistic conclusions
THIS issue reached.

This is a HALF-YEAR review, so say what changed over the period rather than
describing a static snapshot. Do not assert a general claim about the field
that this evidence does not support. If evidence for a conclusion is thin, say
it is thin.

THE FINISHED REVIEW:
{full}"""

    af = dd / "abstract.md"
    ab = ""
    for attempt in range(3):
        print(f"[h1-13] abstract{' retry ' + str(attempt) if attempt else ''} ...",
              flush=True)
        cand = clean(write_llm(abs_task))
        cand = re.sub(r"^\s*abstract\s*[:.]?\s*", "", cand, flags=re.I).strip()
        bad_cite = re.findall(r"\[@?[\w.\-/]+\]", cand)
        if bad_cite:
            print(f"[h1-13]   REJECT abstract has citations {bad_cite[:4]}")
            continue
        stray = re.findall(r"(?<!\{)\b\d[\d.,]*\b(?!\})", cand)
        if stray:
            print(f"[h1-13]   REJECT abstract has literal digits {stray[:6]}")
            continue
        nw = len(cand.split())
        if not (ABSTRACT_WORDS[0] * 0.9 <= nw <= ABSTRACT_WORDS[1] * 1.1):
            print(f"[h1-13]   REJECT abstract {nw}w outside {ABSTRACT_WORDS}")
            continue
        ab = cand
        break
    if not ab:
        raise SystemExit("FAIL-CLOSED: abstract failed the no-citation / "
                         "no-digit / word-band contract in 3 attempts")
    af.write_text(ab, encoding="utf-8")
    print(f"[h1-13]   abstract {len(ab.split())}w (placeholders unresolved)")
    log.append({"stage": "h1_13_abstract", "cli": "agy", "model": MODEL,
                "words": len(ab.split())})

    if log:
        with (d / "tokens.jsonl").open("a", encoding="utf-8") as fh:
            for r in log:
                fh.write(json.dumps(r) + "\n")

    tot = sum(len(v.split()) for v in secs.values())
    meta = {"edition": EDITION,
            "words": {k: len(v.split()) for k, v in secs.items()},
            "abstract_words_raw": len(ab.split()),
            "total_words": tot,
            "sections": len(sections),
            "map_sha256": map_sha,
            "writer": f"agy/{MODEL}"}
    (d / "13_draft_h1.json").write_text(json.dumps(meta, indent=2),
                                        encoding="utf-8")
    print("[h1-13]", json.dumps(meta)[:400])
    return meta


if __name__ == "__main__":
    draft()
