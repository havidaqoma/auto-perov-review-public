"""v2 draft: the main text written by DEVICE FAMILY.

Reuses s13d_draft_v4 BY IMPORT (RULES, ANGLES, write_llm, clean, _attempt,
body_digest) for the same reason v1 does: those carry the unified narration
filter, the word-band and citation-target retries, and the no-digit /
no-citation abstract contract. Forking them recreates the
three-divergent-copies failure (handbook 7.6 #10).

v1 (`h1_draft.py`) is untouched. This writes to draft_h1_v6/.

What each family section is GIVEN
---------------------------------
- its own cards only, as an evidence pool
- its own measured numbers, already guarded so no value whose anchor names a
  different family can appear
- the mechanism axes that dominate ITS papers, so mechanism is written where it
  matters instead of as a competing section
- the OTHER families' headline numbers, so it can position itself

What it is NOT given: a sentence to echo. Every prompt states a job
(handbook 4.1c). The tables are never shown to the writer -- they are generated
(handbook 0.1), and a writer that sees a table transcribes it.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from stages.util import RUNS, read_jsonl                          # noqa: E402
from stages.s13d_draft_v4 import (ANGLES, MODEL, RULES, _attempt,  # noqa: E402
                                  body_digest, clean, write_llm)
from stages.device_family import LABEL, family, family_or_fold     # noqa: E402
from stages.h1_family_stats import (_anchor, _v,                   # noqa: E402
                                    anchor_contradicts_family, measured)
from stages.h1_section_map_v6 import ROT, gaps_id                  # noqa: E402
from stages.protocol import canon_protocol, is_isos                # noqa: E402

EDITION = "2026-H1"
PERIOD = "January-June 2026"
ABSTRACT_WORDS = (380, 520)
MONTH_LAB = {"2026-01": "January", "2026-02": "February", "2026-03": "March",
             "2026-04": "April", "2026-05": "May", "2026-06": "June"}


def family_evidence(cards: list, fam: str, limit: int = 46) -> str:
    """Evidence block for one family: only its cards, only guarded numbers."""
    pool = [c for c in cards if family_or_fold(c) == fam]

    def score(c):
        s = 0
        for f in ("pce_certified", "pce_champion", "t80_h", "active_area_cm2"):
            if isinstance(_v(c, f), (int, float)):
                s += 2 if f == "pce_certified" else 1
        return -s

    pool.sort(key=score)
    lines = []
    for c in pool[:limit]:
        bits = []
        for f, unit in (("pce_certified", "% certified"),
                        ("pce_champion", "% champion"),
                        ("active_area_cm2", " cm2"),
                        ("t80_h", " h T80")):
            v = _v(c, f)
            if not isinstance(v, (int, float)):
                continue
            # A number whose own quotation names another family must never be
            # offered to this section's writer.
            if anchor_contradicts_family(c, f, fam):
                continue
            bits.append(f"{v}{unit}")
        proto = (c.get("stability") or {}).get("protocol")
        if proto:
            bits.append(canon_protocol(proto))
        axis = c.get("axis")
        head = f"[@{c.get('work_key')}] {(c.get('title') or '')[:105]}"
        meta = f"    axis={axis} lens={c.get('lens')} " + \
               (f"| {'; '.join(bits)}" if bits else "| no numeric claim")
        lines.append(head + "\n" + meta)
    return "\n".join(lines)


def family_axes(cards: list, fam: str, top: int = 4) -> str:
    """Which mechanism axes dominate this family's own papers."""
    c = Counter(x.get("axis") for x in cards
                if family_or_fold(x) == fam and x.get("axis"))
    return ", ".join(f"{a} ({n})" for a, n in c.most_common(top))


def cross_family_block(S: dict) -> str:
    """The other families' headline numbers, so a section can position itself."""
    out = []
    for f in ("sj", "ap", "hyb", "mod"):
        p = f"family.{f}."
        out.append(
            f"- {LABEL[f]}: {S.get(p+'n_cards')} papers, "
            f"best certified {S.get(p+'top_certified')}%, "
            f"{S.get(p+'n_certified')} of them reported any certified value, "
            f"largest area {S.get(p+'max_area_cm2')} cm2, "
            f"longest T80 {S.get(p+'max_t80_h')} h")
    return "\n".join(out)


def indoor_block_prose(S: dict) -> str:
    """Indoor / low-light evidence, for DISCUSSION only.

    Havid's decision (2026-09-10): indoor values are excluded from every figure
    and table, but still discussed in the prose.

    That split is the right one and it needs stating plainly, because the two
    halves have opposite failure modes. In a table or a plot an indoor PCE sits
    in a column of one-sun records with no room to caveat it, and a reader
    concludes single junctions beat tandems -- which is how the 44.36% reached
    Table 1 in the first place. In prose the condition travels with the number
    in the same sentence, so the work is reported without being compared to
    something it cannot be compared with.

    The writer therefore gets these numbers WITH their illumination conditions
    and an explicit instruction never to present them as one-sun results.
    """
    n = S.get("indoor.n_values") or 0
    if not n:
        return ""
    top = S.get("indoor.top") or {}
    lines = [
        f"INDOOR / LOW-LIGHT PHOTOVOLTAICS ({n} values across "
        f"{S.get('indoor.n_papers')} papers).",
        "",
        "These are EXCLUDED from every table and figure in this issue, and "
        "from every efficiency number quoted above, because an indoor "
        "efficiency is not comparable to a one-sun efficiency: the "
        "Shockley-Queisser limit is defined for the AM1.5G spectrum, so a "
        "narrow low-flux indoor spectrum legitimately yields a higher "
        "conversion efficiency at a far lower absolute power output.",
        "",
        "You MAY discuss them, and should, but ONLY as indoor photovoltaics "
        "with the illumination stated in the same sentence as the number. "
        "Never write one of these values as a champion or record efficiency, "
        "and never compare one to a one-sun value.",
        "",
    ]
    for r in (S.get("indoor.values") or []):
        lines.append(
            f"- {r['value']}% [@{r['work_key']}] ({r['family']}, "
            f"{MONTH_LAB.get(r.get('month'), '')}, {r.get('venue')}): "
            f"\"{(r.get('anchor') or '')[:150]}\"")
    amb = S.get("indoor.n_ambiguous") or 0
    if amb:
        lines += [
            "",
            f"A further {amb} paper(s) report an indoor AND a one-sun value in "
            f"one sentence, so which condition the extracted number belongs to "
            f"cannot be established. They are excluded from every number in "
            f"this issue. If you mention them, say only that both conditions "
            f"were reported together:",
        ]
        for r in (S.get("indoor.ambiguous") or []):
            lines.append(
                f"- {r['value']}% [@{r['work_key']}]: "
                f"\"{(r.get('anchor') or '')[:140]}\"")
    return "\n".join(lines)


def family_numbers(S: dict, fam: str) -> str:
    p = f"family.{fam}."
    ch = S.get(p + "champion") or {}
    lines = [
        f"Papers in this family: {S.get(p+'n_cards')} "
        f"({S.get(p+'pct_certified')}% reported an independently certified value)",
        f"Best certified: {S.get(p+'top_certified')}%  "
        f"median certified: {S.get(p+'median_certified')}%",
        f"Best self-reported: {S.get(p+'top_champion')}%",
        f"Largest area: {S.get(p+'max_area_cm2')} cm2   "
        f"({S.get(p+'pct_area')}% of papers stated an area)",
        f"Longest T80: {S.get(p+'max_t80_h')} h   "
        f"({S.get(p+'pct_t80')}% reported a T80)",
        f"Named a specified ISOS protocol: {S.get(p+'n_isos_specified')} papers "
        f"({S.get(p+'pct_isos')}%)",
        f"Excluded from measured values as simulation or review: "
        f"{S.get(p+'n_excluded_theory_review')} papers",
    ]
    if ch:
        lines.append(
            f"The single best certified device: {ch.get('value')}% "
            f"[@{ch.get('work_key')}] in {ch.get('venue')}, "
            f"{MONTH_LAB.get(ch.get('month'), '')}, area {ch.get('area_cm2')} cm2. "
            f"Its own quotation reads: \"{(ch.get('anchor') or '')[:170]}\"")
    return "\n".join(lines)


def draft() -> dict:
    d = RUNS / EDITION
    S = json.loads((d / "stats.json").read_text(encoding="utf-8"))
    cards = read_jsonl(d / "claim_cards.jsonl")
    smap = json.loads((d / "12_section_map_v6.json").read_text(encoding="utf-8"))
    dd = d / "draft_h1_v6"
    dd.mkdir(exist_ok=True)

    sections = smap["sections"]
    gid = gaps_id(smap)
    angle = ANGLES[ROT % len(ANGLES)]
    cross = cross_family_block(S)

    # Cross-family frontier series, for the frontier section.
    ser = S.get("family.frontier_series") or {}
    months = [MONTH_LAB.get(m, m) for m in (S.get("months") or [])]
    ser_txt = ["Month | " + " | ".join(LABEL[f] for f in ("sj", "ap", "hyb", "mod"))]
    for i, m in enumerate(months):
        row = [str(ser.get(f, [None] * 6)[i]) for f in ("sj", "ap", "hyb", "mod")]
        ser_txt.append(f"{m} | " + " | ".join(row))
    series_block = "\n".join(ser_txt)

    tasks, ceil_of, cite_of = {}, {}, {}
    for s in sections:
        ceil_of[s["id"]] = s["ceiling"]
        cite_of[s["id"]] = s["cite_target"]

    fam_titles = ", ".join(s["title"].lower() for s in sections
                           if s["role"] == "family")

    for s in sections:
        sid, role = s["id"], s["role"]

        if role == "intro":
            tasks[sid] = f"""Write the Introduction of a mechanistic and critical review of
perovskite photovoltaics covering papers published across {PERIOD}. AT MOST {s['ceiling']} words.
Three or four paragraphs at most.
{RULES}
ANGLE FOR THIS ISSUE: {angle}

This issue is organised by DEVICE FAMILY, not by mechanism. Cover these jobs,
in your own words:
1. Locate the field's open problem. The frontier is no longer raw efficiency.
   Say what it has become.
2. Say why device family is the right cut for this literature: the four
   families face different physical limits and are at different stages of
   verification. Name them: {fam_titles}.
3. State once the scale of the evidence base: {S['corpus.n']} indexed works met
   the scope gate across six months and {S['selection.n_depth']} were read closely.
4. Declare the critical stance: this review separates what was verified from
   what was asserted.

HEADLINE NUMBERS PER FAMILY (do not tabulate these; the tables are generated):
{cross}

Spell out power conversion efficiency (PCE) on first use.
Do not cite individual papers here."""

        elif role == "frontier":
            tasks[sid] = f"""Write "{s['title']}". AT MOST {s['ceiling']} words.
Terse and quantitative. Three or four paragraphs.
{RULES}
ANGLE FOR THIS ISSUE: {angle}

BEST CERTIFIED EFFICIENCY PER FAMILY PER MONTH:
{series_block}

HEADLINE NUMBERS PER FAMILY:
{cross}

CITATION TARGET: at least {s['cite_target']} distinct papers.

Your job: establish what the half year VERIFIED, family by family, and whether
each family's ceiling MOVED or merely repeated. Be explicit that the leading
certified values belong to different device architectures and are therefore not
comparable as a single number.

Two things this section must state plainly, in your own words:
- a single-junction cell and a two-junction tandem are bounded by different
  physics, so a higher tandem number is not a better cell
- a value certified on a square-centimetre cell and one certified at module
  area are different kinds of evidence
Do not describe any trend as a rate or project it forward."""

        elif role == "family":
            fam = s["family"]
            ev = family_evidence(cards, fam, limit=46)
            axes = family_axes(cards, fam)
            nums = family_numbers(S, fam)
            extra = ""
            if fam == "mod":
                extra = ("\nThis family is where the area penalty lives. The "
                         "comparison that matters is the same process at cell "
                         "and at module scale, so quantify the drop wherever a "
                         "paper reports both.")
            if fam == "ap":
                extra = ("\nThe narrow-bandgap Sn-Pb sub-cell is this family's "
                         "limiting component. Where the evidence supports it, "
                         "say whether its instability is intrinsic to the "
                         "composition or a consequence of processing.")
            if fam == "hyb":
                extra = ("\nThis family includes silicon partners AND organic, "
                         "CIGS, CdTe and kesterite partners. Do not write as "
                         "though every hybrid tandem is perovskite/silicon: say "
                         "what the non-silicon partners are for and what they "
                         "cost.")
            if fam == "sj":
                extra = ("\nThis is 79% of the literature, so be selective "
                         "rather than encyclopaedic. Develop the two or three "
                         "problems the evidence actually settles or contests.")
            # Indoor evidence goes to the two families that actually carry it,
            # so it is discussed where it belongs rather than bolted onto a
            # section with no indoor papers.
            if fam in ("sj", "mod"):
                ind = indoor_block_prose(S)
                if ind:
                    extra += "\n\n" + ind

            tasks[sid] = f"""Write "{s['title']}". AT MOST {s['ceiling']} words.
This is a DEVICE-FAMILY section: {LABEL[fam]}.
DENSE and WELL CITED. CITATION TARGET: at least {s['cite_target']} distinct papers.
Falling short of that target is a failure; group citations behind shared claims
to reach it without padding.
{RULES}
ANGLE FOR THIS ISSUE: {angle}

THIS FAMILY'S MEASURED NUMBERS:
{nums}

MECHANISM AXES DOMINATING THIS FAMILY'S OWN PAPERS: {axes}
Write the mechanism where it belongs: inside this family, tied to this
family's devices. Do not survey mechanisms in general.

THE OTHER FAMILIES, FOR POSITIONING ONLY (do not review them here):
{cross}
{extra}

You are covering SIX MONTHS. Where the evidence supports it, say whether the
approach to this family's central problem changed over the period, and where
papers reach incompatible conclusions about the same physical process. Do not
manufacture a narrative of progress the papers do not support.

EVIDENCE (cite by the [@key] shown; every number is quoted verbatim from that
paper's own abstract):
{ev}"""

    # ---------------- Phase A ----------------
    only = [a for a in sys.argv[1:] if a.isdigit()] or None
    secs, log = {}, []
    map_sha = smap["sha256"]
    stamp = dd / "_map.sha"
    if stamp.exists() and stamp.read_text(encoding="utf-8").strip() != map_sha:
        for old in dd.glob("sec*.md"):
            old.unlink()
        print("[h1v6-13] map changed; cleared cached sections")
    stamp.write_text(map_sha, encoding="utf-8")

    from stages.hygiene import SELF_REF
    body_ids = [s["id"] for s in sections
                if s["role"] not in ("gaps", "synthesis", "audit")]
    for sid in body_ids:
        f = dd / f"sec{sid}.md"
        if only and sid not in only and f.exists():
            secs[sid] = f.read_text(encoding="utf-8").strip()
            print(f"[h1v6-13] sec{sid} KEPT ({len(secs[sid].split())}w)")
            continue
        if not only and f.exists():
            prev = f.read_text(encoding="utf-8").strip()
            nw = len(prev.split())
            if 0.45 * ceil_of[sid] <= nw <= 1.25 * ceil_of[sid] and not SELF_REF.search(prev):
                secs[sid] = prev
                print(f"[h1v6-13] sec{sid} KEPT ({nw}w)")
                continue
        secs[sid] = _attempt(sid, tasks[sid], ceil_of[sid], cite_of[sid], f, log)

    # ---------------- Phase B1: synthesis ----------------
    syn = next((s for s in sections if s["role"] == "synthesis"), None)
    if syn:
        digest = body_digest(secs, smap, budget=9000)
        syn_task = f"""Write "{syn['title']}". AT MOST {syn['ceiling']} words.
{RULES}
ANGLE FOR THIS ISSUE: {angle}

You can see the four finished device-family sections below. Do NOT summarise them.

Your job is the one thing a single-family review cannot do: say what these four
device families mean WHEN READ TOGETHER. Find where the same physical failure
appears in more than one family under different names, where a solution proven
in one family fails in another and why, and where the families make
incompatible demands on the same layer or interface. Ground every claim in
specific papers.
CITE at least {syn['cite_target']} papers by [@work_key], using ONLY keys that
appear below.

If the families do NOT share a story, say so plainly. A forced synthesis is
worse than an honest statement that the device families are still separate
engineering problems.

THE DEVICE-FAMILY SECTIONS AS WRITTEN:
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
        rows = []
        for fam in ("sj", "ap", "hyb", "mod"):
            p = f"family.{fam}."
            rows.append(
                f"- {LABEL[fam]} ({S.get(p+'n_cards')} papers): "
                f"efficiency stated {S.get(p+'pct_champion')}%, "
                f"independently certified {S.get(p+'pct_certified')}%, "
                f"area stated {S.get(p+'pct_area')}%, "
                f"T80 reported {S.get(p+'pct_t80')}%, "
                f"specified ISOS protocol {S.get(p+'pct_isos')}%")
        aud_task = f"""Write "{aud['title']}". AT MOST {aud['ceiling']} words.
{RULES}
ANGLE FOR THIS ISSUE: {angle}

REPORTING COMPLETENESS BY DEVICE FAMILY (percentages are of that family's
depth-tier papers):
{chr(10).join(rows)}

Pooled across the whole corpus: {S.get('audit.h1.efficiency_stated.pct')}% of
abstracts stated an efficiency and {S.get('audit.h1.certified.pct')}% reported
independent certification, over {S.get('audit.corpus.denominator')} abstracts.

Your job: say what these rates mean for a reader trying to compare devices
ACROSS families, and whether the families verify themselves to the same
standard. The interesting comparison is between families, not the pooled
average.

Be careful with causation. These are detection rates over abstracts, not audits
of what the papers did: an unstated protocol is not a protocol that was not
followed. Say that limitation once, in your own words.
CITE at least {aud['cite_target']} papers by [@work_key] where a specific paper
illustrates good or absent reporting."""
        f = dd / f"sec{aud['id']}.md"
        if not only or aud["id"] in only or not f.exists():
            secs[aud["id"]] = _attempt(aud["id"], aud_task, aud["ceiling"],
                                       aud["cite_target"], f, log)
        else:
            secs[aud["id"]] = f.read_text(encoding="utf-8").strip()

    # ---------------- Phase B3: gaps ----------------
    digest = body_digest(secs, smap, budget=10000)
    gs = next(s for s in sections if s["id"] == gid)
    t80 = sorted((_v(c, "t80_h") for c in cards
                  if isinstance(_v(c, "t80_h"), (int, float))), reverse=True)
    n_proto = len([c for c in cards if (c.get("stability") or {}).get("protocol")])
    gaps_task = f"""Write "Research Gaps and Outlook". AT MOST {gs['ceiling']} words.
{RULES}
ANGLE FOR THIS ISSUE: {angle}

You are writing the CLOSING section and can see the whole review below.
Do not summarise it. Identify what the half year's evidence, as actually argued
in these sections, does NOT establish.

Give four or five concrete research gaps. Each must name the measurement or
experiment that would close it, and each must follow from something the body
actually says. At least one gap must be specific to a single device family, and
at least one must cut across families.
CITE at least {gs['cite_target']} papers by [@work_key], using ONLY keys that
appear below.

QUANTITATIVE GROUND TRUTH (use these numbers only):
{cross}
- {len(t80)} of {len(cards)} closely read papers reported a T80 lifetime,
  longest {int(t80[0]) if t80 else 0} h
- {n_proto} papers named any stability protocol

THE REVIEW AS WRITTEN:
{digest}

End by naming what the field should MEASURE differently, in your own words.
State the job, not a wish: identify which specific cross-family comparison this
half year's evidence could not support, and what reporting would have supported
it."""
    f = dd / f"sec{gid}.md"
    if not only or gid in only or not f.exists():
        secs[gid] = _attempt(gid, gaps_task, gs["ceiling"], gs["cite_target"], f, log)
    else:
        secs[gid] = f.read_text(encoding="utf-8").strip()

    # ---------------- Phase C: abstract ----------------
    full = body_digest({**secs}, smap, budget=11000)
    abs_task = f"""Write the ABSTRACT of this review. Between {ABSTRACT_WORDS[0]} and
{ABSTRACT_WORDS[1]} words, one paragraph.
{RULES}

You can see the entire finished review below. The abstract must reflect what
THIS issue argues. This issue is organised by DEVICE FAMILY, so the abstract
must be too: single junction, all-perovskite tandem, hybrid tandem, module.

TWO HARD CONSTRAINTS, both machine-checked:

1. NO CITATIONS. No [@key], no [1], no bracketed marker of any kind.

2. NO DIGITS. Do not write any number, in figures or in words. Where a number
   belongs, write the exact placeholder token and nothing else:
     {{{{N_CORPUS}}}}     indexed works across the six months
     {{{{N_DEPTH}}}}      number read closely
     {{{{N_MONTHS}}}}     how many months the issue covers
     {{{{N_CERT}}}}       how many reported a certified efficiency
     {{{{P_TOP_CERT}}}}   the highest certified efficiency, with % sign
     {{{{P_TOP_SJ}}}}     highest certified single junction, with % sign
     {{{{A_MAX}}}}        largest reported aperture area, with unit
     {{{{P_AREA_MAX}}}}   the certified efficiency at that largest area
     {{{{N_T80}}}}        how many reported a T80 lifetime
     {{{{H_T80_MAX}}}}    the longest reported T80, with unit
     {{{{N_PROTO}}}}      how many named a stability protocol
     {{{{PCT_EFF}}}}      share of abstracts stating an efficiency, with %
     {{{{PCT_CERT}}}}     share stating independent certification, with %
   A script substitutes the real values. A digit you write is a rejection.

Cover, in this order: the corpus and how much was read closely; what each
device family verified and whether its ceiling moved; the area penalty; the
state of operational-stability evidence; reporting completeness across
families; and the mechanistic conclusions THIS issue reached.

Say what changed over the period rather than describing a snapshot. If evidence
for a conclusion is thin, say it is thin.

THE FINISHED REVIEW:
{full}"""

    af = dd / "abstract.md"
    ab = ""
    for attempt in range(3):
        print(f"[h1v6-13] abstract{' retry ' + str(attempt) if attempt else ''} ...",
              flush=True)
        cand = clean(write_llm(abs_task))
        cand = re.sub(r"^\s*abstract\s*[:.]?\s*", "", cand, flags=re.I).strip()
        if re.findall(r"\[@?[\w.\-/]+\]", cand):
            print("[h1v6-13]   REJECT abstract has citations")
            continue
        stray = re.findall(r"(?<!\{)\b\d[\d.,]*\b(?!\})", cand)
        if stray:
            print(f"[h1v6-13]   REJECT abstract has digits {stray[:6]}")
            continue
        nw = len(cand.split())
        if not (ABSTRACT_WORDS[0] * 0.9 <= nw <= ABSTRACT_WORDS[1] * 1.1):
            print(f"[h1v6-13]   REJECT abstract {nw}w outside {ABSTRACT_WORDS}")
            continue
        ab = cand
        break
    if not ab:
        raise SystemExit("FAIL-CLOSED: abstract failed its contract in 3 attempts")
    af.write_text(ab, encoding="utf-8")
    print(f"[h1v6-13]   abstract {len(ab.split())}w")
    log.append({"stage": "h1v6_abstract", "cli": "agy", "model": MODEL,
                "words": len(ab.split())})

    if log:
        with (d / "tokens.jsonl").open("a", encoding="utf-8") as fh:
            for r in log:
                fh.write(json.dumps(r) + "\n")

    meta = {"edition": EDITION, "version": "v6", "structure": "device_family",
            "words": {k: len(v.split()) for k, v in secs.items()},
            "abstract_words_raw": len(ab.split()),
            "total_words": sum(len(v.split()) for v in secs.values()),
            "sections": len(sections), "map_sha256": map_sha,
            "writer": f"agy/{MODEL}"}
    (d / "13_draft_h1_v6.json").write_text(json.dumps(meta, indent=2),
                                           encoding="utf-8")
    print("[h1v6-13]", json.dumps(meta)[:400])
    return meta


if __name__ == "__main__":
    draft()
