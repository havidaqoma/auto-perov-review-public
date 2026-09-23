"""13y_draft_yearly: write the yearly review's prose. Five phases, one model.

LINEAGE
-------
Ported from the monthly project's `s13d_draft_v4.py`
(auto-perov-review), which has shipped three issues. Everything
load-bearing is carried over rather than reinvented:

  RULES              the writing contract, verbatim
  ANGLES             voice rotation, rotated by YEAR not month
  write_llm          agy, one model, no fallback, retry the same model 3x
  clean              delegates narration stripping to stages.hygiene
  _attempt           word-band + citation-target retries, fail closed
  evidence           per-axis evidence folds, a POOL to select from
  body_digest        the finished body, fed to later phases
  abstract contract  no digits, no citations, named tokens only

WHAT IS NEW FOR YEARLY
----------------------
1. Two extra spine roles the monthly issue cannot have:
     trajectory  what changed across the twelve months
     synthesis   what the separate mechanism literatures say TOGETHER
   Without `synthesis` a yearly issue is twelve monthlies stapled together.

2. Five phases instead of three, so the closing sections react to what the
   body ACTUALLY says:
     A body       intro, trajectory, mechanism sections
     B synthesis  reads the FULL body
     C audit      reads the body + the twelve-point series
     D gaps       reads everything above
     E abstract   reads everything; NO citations, NO digits

3. A BACKFILL DISCLOSURE. This issue was assembled retrospectively in 2026,
   not by month-by-month monitoring across 2025. The intro must say so and
   the abstract carries {{N_MONTHS}} / {{N_MONTH_UNKNOWN}}. An issue that
   reads as if it tracked the field live, when it did not, is a misstatement
   no gate can catch because the text is internally consistent.

4. YEAR-OVER-YEAR IS FORBIDDEN. There is no 2024 yearly issue, so
   `prior_year_stats()` returns None. 2024's raw count is knowable (6,784)
   and that is exactly the temptation: a count is not a prior-year stats
   file. There is no YoY token, so an invented one fails the build.

WHAT IS DELIBERATELY NOT PORTED
-------------------------------
`prior_closing_block()`. It quotes the PRIOR issue's actual closing text back
to the writer so month N+1 differs from month N. There is no prior yearly
issue, so it would feed an empty block. It must be added when the SECOND
yearly issue is written, and a note in the returned meta says so.

THE CACHE TRAP
--------------
A change to RULES, a task prompt, or hygiene.py does NOT change the section
map sha. A yearly draft is the most expensive artifact in the project, so the
temptation to reuse cached sections is strongest here. If you edit prompt
text, delete the affected draft_yearly/sec*.md by hand.
"""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
import sys
import time

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from stages.hygiene import strip_narration                  # noqa: E402
from stages.util import CONFIG, done, is_year, read_jsonl, run_dir  # noqa: E402
from stages.yearly_corpus import aggregate, axis_mass, yearly_dir  # noqa: E402
from stages.device_class import (CLASS_LABEL, CLASS_SHORT,  # noqa: E402
                                 classify)
from stages.yearly_device_map import build_map              # noqa: E402
from stages.yearly_tables import build_tables               # noqa: E402

MODEL = "gemini-3.8-flash-high"

# Carried over VERBATIM from the monthly project. Every clause here encodes a
# defect that shipped once; none of it is period-specific.
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

# Rotated by YEAR, so consecutive yearly issues argue differently with no
# per-run randomness.
ANGLES = [
    "Lead with the mechanism the year's evidence supports most strongly, "
    "then work outward to the weaker claims.",
    "Lead with the disagreement: where papers across the year reach "
    "incompatible conclusions about the same physical process, and what "
    "measurement would settle it.",
    "Lead with what the year's measurements cannot distinguish, then show "
    "which results survive that ambiguity.",
    "Lead with the quantitative frontier for this physics, then ask what "
    "the reported evidence actually licenses.",
]


def _agy() -> str:
    exe = shutil.which("agy")
    if not exe:
        raise SystemExit("FAIL-CLOSED: agy not on PATH (writer, no fallback)")
    return exe


def write_llm(prompt: str, timeout: int = 1800, attempts: int = 3) -> str:
    """One model writes prose. Retrying the same model is not a fallback.

    A fallback would put two prose voices in one document; the retry keeps
    one voice and survives a transient failure.
    """
    exe = _agy()
    last = ""
    for i in range(attempts):
        p = subprocess.run(
            [exe, "-p", prompt, "--model", MODEL,
             "--dangerously-skip-permissions", "--print-timeout", "1500s"],
            capture_output=True, text=True, timeout=timeout, cwd=str(CONFIG.parent))
        out = (p.stdout or "").strip()
        if p.returncode == 0 and len(out) > 200:
            return out
        last = f"rc={p.returncode} out={len(out)}B err={(p.stderr or '')[:150]!r}"
        if i < attempts - 1:
            time.sleep(2 ** i + 1)
    raise RuntimeError(f"agy failed after {attempts}: {last}")


def clean(raw: str) -> str:
    """Strip fences, stray headings, and agent narration.

    Narration removal is delegated to stages.hygiene so this filter and the
    build's G4 can never diverge. Three divergent copies once existed and the
    narrowest let "I have launched the search command and will wait for it to
    finish." reach a shipped PDF with G4 reporting pass.
    """
    t = re.sub(r"^```(?:\w+)?|```$", "", raw.strip(), flags=re.M).strip()
    t = re.sub(r"^#+ .*$", "", t, flags=re.M)
    t, removed = strip_narration(t)
    for ln in removed:
        print(f"[13y]   STRIPPED narration: {ln[:90]}")
    return t


def _v(c: dict, k: str):
    src = c.get("stability") if k in ("t80_h", "duration_h") else c.get("performance")
    f = (src or {}).get(k)
    return f["value"] if isinstance(f, dict) and f.get("value") is not None else None


def evidence(cards: list, axes: list, limit: int = 46) -> str:
    """Per-axis evidence fold. A POOL to select from, never a checklist.

    limit is 46 rather than the monthly 34: a yearly mechanism section has a
    1500-word ceiling and a 33-citation target, so it needs a deeper pool.
    Handing the writer all ~450 cards raw would multiply input tokens and
    produce a list rather than an argument.
    """
    sel = [c for c in cards if c.get("axis") in axes]
    sel.sort(key=lambda c: -(_v(c, "pce_certified") or _v(c, "pce_champion") or 0))
    out = []
    for c in sel[:limit]:
        bits = []
        for k, lab in (("pce_certified", "CERTIFIED"), ("pce_champion", "champion"),
                       ("pce_stabilised", "stabilised"), ("active_area_cm2", "area cm2")):
            v = _v(c, k)
            if v is not None:
                bits.append(f"{lab} {v}")
        if (c.get("stability") or {}).get("protocol"):
            bits.append(f"protocol {c['stability']['protocol']}")
        t = _v(c, "t80_h")
        if t:
            bits.append(f"T80 {t} h")
        mo = c.get("source_month") or "month unknown"
        out.append(f"[@{c['work_key']}] {c.get('venue')} | {mo} | "
                   f"{(c.get('device') or {}).get('architecture')} | "
                   f"{'; '.join(bits) if bits else 'no numeric field'}\n"
                   f"    {c.get('title')}\n    FINDINGS: "
                   f"{' | '.join(x['text'] for x in (c.get('claims') or [])[:2])}")
    return "\n".join(out)


def evidence_for(pool: list, limit: int = 60) -> str:
    """Evidence fold for an explicit CARD LIST rather than an axis list.

    `evidence()` above selects by mechanism axis, which the device spine no
    longer uses: a device section's membership is decided by
    device_class.classify(), not by the axis field. Passing the pool in
    directly keeps ONE definition of what belongs in a section -- the
    classifier -- instead of letting the draft stage re-derive membership
    and drift from the section map.

    limit is 60 rather than 46: a device section's ceiling rose to 2200
    words with a 49-citation target, so the pool must be deeper than the
    target or the writer cannot meet it while still selecting.
    """
    sel = sorted(pool, key=lambda c: -(_v(c, "pce_certified")
                                       or _v(c, "pce_champion") or 0))
    out = []
    for c in sel[:limit]:
        bits = []
        for k, lab in (("pce_certified", "CERTIFIED"),
                       ("pce_champion", "champion"),
                       ("pce_stabilised", "stabilised"),
                       ("active_area_cm2", "area cm2")):
            v = _v(c, k)
            if v is not None:
                bits.append(f"{lab} {v}")
        if (c.get("stability") or {}).get("protocol"):
            bits.append(f"protocol {c['stability']['protocol']}")
        t = _v(c, "t80_h")
        if t:
            bits.append(f"T80 {t} h")
        mo = c.get("source_month") or "month unknown"
        lens = c.get("lens") or "unknown"
        # The lens is shown so the writer can see which entries are
        # computational and avoid presenting a simulated value as measured.
        out.append(f"[@{c['work_key']}] {c.get('venue')} | {mo} | {lens} | "
                   f"{(c.get('device') or {}).get('architecture')} | "
                   f"{'; '.join(bits) if bits else 'no numeric field'}\n"
                   f"    {c.get('title')}\n    FINDINGS: "
                   f"{' | '.join(x['text'] for x in (c.get('claims') or [])[:2])}")
    return "\n".join(out)


def body_digest(secs: dict, smap: dict, budget: int = 11000) -> str:
    """The finished body, trimmed, for phases B through E.

    Those phases exist to react to what the body ACTUALLY says. Handing the
    writer statistics alone recreates the failure where closing text could
    have been written before the body existed and therefore reads the same
    every issue.
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
    if len(txt) > budget:
        per = budget // max(len(parts), 1)
        txt = "\n\n".join(p[:per] for p in parts)
    return txt


def _attempt(sid: str, task: str, ceiling: int, cite_target: int,
             f: pathlib.Path, log: list) -> str:
    """Draft one section, enforcing the word band and citation target.

    Fails closed after three attempts. A section that cannot meet its own
    generated target is a signal about the evidence or the prompt, never a
    reason to lower the target.
    """
    for attempt in range(3):
        print(f"[13y] sec{sid}{' retry ' + str(attempt) if attempt else ''} ...",
              flush=True)
        cand = clean(write_llm(task))
        nw = len(cand.split())
        if nw < 0.45 * ceiling:
            print(f"[13y]   REJECT {nw}w < floor {int(0.45 * ceiling)}")
            continue
        if nw > 1.35 * ceiling:
            print(f"[13y]   REJECT {nw}w > 135% of ceiling {ceiling}")
            continue
        ncit = len(set(re.findall(r"\[@([^\]\s]+)\]", cand)))
        if ncit < cite_target:
            print(f"[13y]   REJECT {ncit} citations < target {cite_target}")
            continue
        f.write_text(cand, encoding="utf-8")
        print(f"[13y]   {nw}w (ceiling {ceiling}), {ncit} cites")
        log.append({"stage": f"13y_s{sid}", "cli": "agy", "model": MODEL,
                    "words": nw, "attempt": attempt, "shipped": True,
                    "tokens_in": 0, "tokens_out": 0,
                    "token_source": "estimated",
                    "at": time.strftime("%H:%M:%S")})
        return cand
    raise SystemExit(f"FAIL-CLOSED: sec{sid} no usable prose in 3 attempts")


def trajectory_block(S: dict) -> str:
    """The twelve-point series, with DEVICE CLASS on every point.

    The highest certified values in this corpus are tandems. An unlabelled
    trajectory of mixed device classes is the misattribution defect rendered
    as a line chart, so the class travels with the number.
    """
    months = S.get("frontier.months") or []
    cert = S.get("frontier.top_certified_series") or []
    champ = S.get("frontier.top_champion_series") or []
    ncert = S.get("frontier.n_certified_series") or []
    rows = []
    for i, m in enumerate(months):
        c = cert[i] if i < len(cert) else None
        ch = champ[i] if i < len(champ) else None
        nc = ncert[i] if i < len(ncert) else 0
        rows.append(f"  {m}: best certified {c if c is not None else 'none'}"
                    f" | best self-reported {ch if ch is not None else 'none'}"
                    f" | certified papers {nc}")
    delta = S.get("frontier.certified_delta_pp")
    tail = ""
    if delta is not None:
        tail = (f"\nChange in best certified value from the first month with "
                f"data to the last: {delta} percentage points. State what the "
                f"data shows. Do not imply steady progress if the series does "
                f"not show it, and do not imply stagnation if it does.")
    return "MONTH-BY-MONTH FRONTIER:\n" + "\n".join(rows) + tail


def audit_block(S: dict) -> str:
    """Pooled annual rates WITH the monthly spread.

    A pooled rate hides whether a value sat flat all year or swung wildly,
    and those are different findings. The spread is therefore mandatory.
    """
    keys = ["efficiency_stated", "certified", "stabilised",
            "area_stated", "isos_label", "hysteresis"]
    rows = []
    for k in keys:
        pct = S.get(f"audit.year.{k}.pct")
        lo = S.get(f"audit.year.{k}.month_min_pct")
        hi = S.get(f"audit.year.{k}.month_max_pct")
        den = S.get(f"audit.year.{k}.denominator")
        if pct is None:
            continue
        rows.append(f"  {k}: {pct}% of {den} abstracts "
                    f"(monthly range {lo}% to {hi}%)")
    return ("REPORTING PRACTICE ACROSS THE YEAR, pooled over summed "
            "denominators (NOT the mean of twelve monthly percentages):\n"
            + "\n".join(rows))


def draft(year: str, only: list | None = None) -> dict:
    if not is_year(year):
        raise SystemExit(f"expected a 4-digit year, got {year!r}")

    rd = run_dir(year, create=False)
    yd = yearly_dir(year)
    S = json.loads((yd / "stats_yearly.json").read_text(encoding="utf-8"))
    agg = aggregate(year, require_full_year=False)
    cards = agg["cards"]

    dd = rd / "draft_yearly"
    dd.mkdir(exist_ok=True)

    abstracts = {x["work_key"]: x["abstract"]
                 for x in read_jsonl(rd / "private" / "02_abstracts.jsonl")}
    smap = build_map(year, cards, abstracts, n_months=agg["n_months"])
    tables = build_tables(cards, abstracts)
    (yd / "yearly_section_map.json").write_text(
        json.dumps(smap, indent=2), encoding="utf-8")
    sections = smap["sections"]
    angle = ANGLES[int(year) % len(ANGLES)]

    yy = yaml.safe_load((CONFIG / "yearly.yaml").read_text(encoding="utf-8"))
    ab_lo, ab_hi = yy["abstract_yearly"]["word_band"]

    cert = sorted(((_v(c, "pce_certified"), c) for c in cards
                   if _v(c, "pce_certified")), key=lambda x: -x[0])
    areas = sorted(((_v(c, "active_area_cm2"), c) for c in cards
                    if _v(c, "active_area_cm2")), key=lambda x: -x[0])
    t80 = sorted(((_v(c, "t80_h"), c) for c in cards if _v(c, "t80_h")),
                 key=lambda x: -x[0])
    n_proto = len([c for c in cards
                   if (c.get("stability") or {}).get("protocol")])

    top_cert = "; ".join(
        f"{v}% ({c.get('venue')}, {(c.get('device') or {}).get('architecture')}, "
        f"{c.get('source_month') or 'month unknown'}) [@{c['work_key']}]"
        for v, c in cert[:12])
    top_area = "; ".join(
        f"{a} cm2 at {_v(c,'pce_champion') or _v(c,'pce_certified')}% "
        f"[@{c['work_key']}]" for a, c in areas[:8])
    top_t80 = "; ".join(f"{int(v)} h [@{c['work_key']}]" for v, c in t80[:12])
    protos = "; ".join(f"{c['stability']['protocol']} [@{c['work_key']}]"
                       for c in cards
                       if (c.get("stability") or {}).get("protocol"))

    n_corpus = S["corpus.n"]
    n_cards = S["cards.n"]
    n_months = S["n_months"]
    n_unknown = agg.get("month_unknown_corpus", 0)
    threads = ", ".join(s["title"].lower() for s in sections
                        if s["role"] == "device")
    traj = trajectory_block(S)
    audit = audit_block(S)

    # The backfill disclosure, stated once and reused, so every phase that
    # needs it says the same true thing.
    BACKFILL = (
        f"HOW THIS ISSUE WAS ASSEMBLED, and this must be stated plainly in "
        f"the text rather than implied: this review was compiled "
        f"retrospectively from the complete {year} publication record, not by "
        f"monitoring the literature month by month during {year}. "
        f"{n_corpus} works met the scope gate; {n_months} months carry "
        f"date-resolved works and {n_unknown} works are dated only to the "
        f"year, so they contribute to the corpus but not to any month-by-"
        f"month series. There is no prior yearly issue of this review, so "
        f"make NO year-over-year comparison of any kind.")

    log: list = []
    secs: dict = {}
    only = only or []

    # ---------------- Phase A: body ----------------
    for s in sections:
        sid, role = s["id"], s["role"]
        if role in ("synthesis", "audit", "gaps"):
            continue

        if role == "intro":
            task = f"""Write the Introduction of a mechanistic and critical review of
perovskite photovoltaics covering the whole of {year}. AT MOST {s['ceiling']} words.
This is a SHORT, DENSE introduction. Four or five paragraphs at most.
{RULES}
ANGLE FOR THIS ISSUE: {angle}

{BACKFILL}

Cover these five jobs. Choose your own wording for each.
1. Locate the field's open problem. The frontier is no longer raw efficiency.
   Say in your own words what it has become, drawing on the sections that
   follow: verification, area, and operating lifetime.
2. State once, in one sentence, the scale of the evidence base: {n_corpus}
   indexed works met the scope gate and {n_cards} were read closely.
3. Say plainly how the issue was assembled, per the paragraph above. A reader
   must not be able to mistake this for month-by-month monitoring.
4. Name the mechanistic threads this issue follows: {threads}.
5. Declare the critical stance. This review distinguishes what the year's
   literature verified from what it asserted.

Spell out power conversion efficiency (PCE) on first use.
Do not cite individual papers here."""

        elif role == "trajectory":
            task = f"""Write "{s['title']}". AT MOST {s['ceiling']} words.
Be terse and quantitative. Three or four paragraphs.
{RULES}
ANGLE FOR THIS ISSUE: {angle}

{traj}

Independently certified efficiencies across the year, highest first, each
with its device class and the month it was published:
{top_cert}

Only {len(cert)} of {n_cards} closely read papers reported an independently
certified efficiency.

CITATION TARGET FOR THIS SECTION: at least {s['cite_target']} distinct papers.

Your job is the one thing a single-month issue cannot do: say what moved
across the year and what did not. Two hard requirements.
- EVERY efficiency you quote must carry its device class. The highest values
  in this corpus are multi-junction tandems, and a tandem number presented as
  a single-junction result is a misstatement.
- Some works are dated only to the year and carry no month. They are in the
  corpus and absent from the series. Do not describe the series as complete
  coverage of the year's publications."""

        elif role == "device":
            dev = s.get("device_class")
            # Evidence pool is THIS DEVICE CLASS only. A tandem section fed
            # single-junction cards would invite the writer to compare a
            # 26% single cell against a 33% stack as if they were rivals.
            pool = [c for c in cards
                    if classify(c, abstracts.get(c.get("work_key"), "")) == dev]
            ev = evidence_for(pool)
            limit = s.get("pce_limit_pct")
            n_pool = len(pool)
            n_meas = len([c for c in pool
                          if c.get("lens") not in ("theory", "review")])

            extra = ""
            if dev == "module":
                m_area = "; ".join(
                    f"{_v(c,'active_area_cm2')} cm2 at "
                    f"{_v(c,'pce_champion') or _v(c,'pce_certified')}% "
                    f"[@{c['work_key']}]"
                    for c in pool if _v(c, "active_area_cm2") is not None)
                extra = (f"\nEvery area and efficiency pair in this class: "
                         f"{m_area or 'none reported'}\n")
            if dev in ("all_perovskite_tandem", "hybrid_tandem"):
                extra = (f"\nThis class is bounded by the two-junction "
                         f"detailed-balance limit of {limit}%, NOT the "
                         f"single-junction limit. Do not describe a value "
                         f"below {limit}% as approaching a fundamental "
                         f"ceiling.\n")
            if dev == "single_junction":
                extra = (f"\nThis class is bounded at {limit}% by the "
                         f"Shockley-Queisser limit for a 1.55 eV absorber. "
                         f"Papers in this class that discuss tandems as a "
                         f"future application are still single-junction "
                         f"studies; treat them as such.\n")
            folded = s.get("folded_in") or []
            fold_note = (f"\nThis section also carries papers from: "
                         f"{', '.join(CLASS_SHORT.get(k, k) for k in folded)}. "
                         f"Integrate them into the argument; do not append "
                         f"them." if folded else "")

            task = f"""Write "{s['title']}". AT MOST {s['ceiling']} words.
{RULES}
ANGLE FOR THIS ISSUE: {angle}
CITATION TARGET FOR THIS SECTION: at least {s['cite_target']} distinct papers.
{fold_note}{extra}
This section covers ONE DEVICE CLASS: {CLASS_LABEL.get(dev, dev)}.
{n_pool} papers were read closely in this class, of which {n_meas} report
measured rather than computed results.

This is a YEAR of literature on this device class, not a month. Develop two
or three physical problems in depth and say where the year's evidence
converged, where it conflicted, and where it stayed thin. A section that
lists papers month by month has failed; the device class is the organising
principle and the months are data.

Every device class has its own physical ceiling, so do not compare a value
in this section against a value from another class as though they were
competing for the same record.

EVIDENCE POOL for this device class (select from it; do not cite every
entry):
{ev}"""
        else:
            raise SystemExit(f"FAIL-CLOSED: unknown Phase A role {role!r}")

        f = dd / f"sec{sid}.md"
        if f.exists() and sid not in only:
            secs[sid] = f.read_text(encoding="utf-8").strip()
            print(f"[13y] sec{sid} KEPT ({len(secs[sid].split())}w)")
        else:
            secs[sid] = _attempt(sid, task, s["ceiling"], s["cite_target"],
                                 f, log)

    # ---------------- Phase B: synthesis, reads the FULL body -------------
    syn = next((s for s in sections if s["role"] == "synthesis"), None)
    if syn:
        digest = body_digest(secs, smap)
        task = f"""Write "{syn['title']}". AT MOST {syn['ceiling']} words.
{RULES}
CITATION TARGET FOR THIS SECTION: at least {syn['cite_target']} distinct papers.

This section is the reason a yearly review exists. The mechanism sections
above each treat one literature. Your job is to say what they mean TOGETHER:
where two mechanisms are the same physics described in different vocabularies,
where a gain claimed in one section is paid for in another, and which
combination the year's evidence does not let anyone claim at once.

Do not summarise the sections. A summary of what a reader just read is wasted
words. Say what follows from reading them side by side.

THE REVIEW AS WRITTEN:
{digest}"""
        f = dd / f"sec{syn['id']}.md"
        if f.exists() and syn["id"] not in only:
            secs[syn["id"]] = f.read_text(encoding="utf-8").strip()
            print(f"[13y] sec{syn['id']} KEPT")
        else:
            secs[syn["id"]] = _attempt(syn["id"], task, syn["ceiling"],
                                       syn["cite_target"], f, log)

    # ---------------- Phase C: audit, body + the series -------------------
    aud = next((s for s in sections if s["role"] == "audit"), None)
    if aud:
        task = f"""Write "{aud['title']}". AT MOST {aud['ceiling']} words.
{RULES}
CITATION TARGET FOR THIS SECTION: at least {aud['cite_target']} distinct papers.

{audit}

These rates are computed by script over abstracts, by regular expression.
They measure what abstracts STATE, not what the papers did, and they carry no
validated precision figure. Describe them as detection rates in abstracts and
do not present them as measured practice.

The thin rows are the finding. A reporting quantity that almost no abstract
states is a fact about the field's practice.

Say whether practice changed across the year. The monthly range is given for
each rate: a rate that sat flat and a rate that swung are different findings."""
        f = dd / f"sec{aud['id']}.md"
        if f.exists() and aud["id"] not in only:
            secs[aud["id"]] = f.read_text(encoding="utf-8").strip()
            print(f"[13y] sec{aud['id']} KEPT")
        else:
            secs[aud["id"]] = _attempt(aud["id"], task, aud["ceiling"],
                                       aud["cite_target"], f, log)

    # ---------------- Phase D: gaps, LAST section, reads everything -------
    gaps = next((s for s in sections if s["role"] == "gaps"), None)
    if not gaps or gaps["id"] != sections[-1]["id"]:
        raise SystemExit("FAIL-CLOSED: gaps must be the last section")
    digest = body_digest(secs, smap)
    task = f"""Write "{gaps['title']}". AT MOST {gaps['ceiling']} words.
{RULES}
CITATION TARGET FOR THIS SECTION: at least {gaps['cite_target']} distinct papers.

THE YEAR IN NUMBERS:
- {n_corpus} works met the scope gate, {n_cards} read closely
- {len(cert)} reported an independently certified efficiency
- {len(t80)} reported a T80 lifetime, {n_proto} named an ISOS protocol
- largest reported aperture {areas[0][0] if areas else 0} cm2

{traj}

THE REVIEW AS WRITTEN:
{digest}

End by naming what the field should MEASURE differently, in your own words.
State the job, not a wish: identify which specific comparison this year's
evidence could not support, and what reporting would have supported it. Do not
recycle a generic call for standardised reporting.

NOTE: there is no prior yearly issue to differ from, so this section is a cold
start. Write what the year's evidence supports."""
    f = dd / f"sec{gaps['id']}.md"
    if f.exists() and gaps["id"] not in only:
        secs[gaps["id"]] = f.read_text(encoding="utf-8").strip()
        print(f"[13y] sec{gaps['id']} KEPT")
    else:
        secs[gaps["id"]] = _attempt(gaps["id"], task, gaps["ceiling"],
                                    gaps["cite_target"], f, log)

    # ---------------- Phase E: abstract, LAST, no digits, no citations ----
    full = body_digest(secs, smap, budget=12000) + \
        "\n\n### Research Gaps\n" + \
        re.sub(r"\[@[^\]\s]+\]", "", secs[gaps["id"]])

    abs_task = f"""Write the ABSTRACT of this review. Between {ab_lo} and {ab_hi}
words, one paragraph.
{RULES}

You can see the entire finished review below. The abstract must reflect what
THIS issue actually argues. Do not write a generic perovskite abstract.

TWO HARD CONSTRAINTS, both machine-checked:

1. NO CITATIONS. Do not write [@key], [1], [2] or any bracketed marker.

2. NO DIGITS. Do not write any number, in figures or in words. Where a number
   belongs, write the exact placeholder token from this list and nothing else:
     {{{{N_CORPUS}}}}          works meeting the scope gate
     {{{{N_DEPTH}}}}           number read closely
     {{{{N_MONTHS}}}}          months carrying date-resolved works
     {{{{N_MONTH_UNKNOWN}}}}   works dated only to the year
     {{{{N_CERT}}}}            how many reported a certified efficiency
     {{{{P_TOP_CERT_YEAR}}}}   highest certified efficiency, with % sign
     {{{{P_CERT_FIRST}}}}      best certified value in the first month with data
     {{{{P_CERT_LAST}}}}       best certified value in the last month with data
     {{{{DELTA_CERT_PP}}}}     change between those two, in percentage points
     {{{{A_MAX}}}}             largest reported aperture area, with unit
     {{{{N_T80}}}}             how many reported a T80 lifetime
     {{{{H_T80_MAX}}}}         longest reported T80, with unit
     {{{{N_PROTO}}}}           how many named an ISOS protocol
     {{{{PCT_CERT_YEAR}}}}     pooled annual share stating certification, with %
     {{{{PCT_CERT_MIN}}}}      lowest monthly value of that share, with %
     {{{{PCT_CERT_MAX}}}}      highest monthly value of that share, with %
   A script substitutes the real values afterwards. If you write a digit
   yourself the abstract is rejected.

There is NO year-over-year token because there is no prior yearly issue. Make
no comparison to a previous year.

Cover, in this order: what the corpus was, how much was read closely, and that
the issue was assembled retrospectively rather than by month-by-month
monitoring; what the certified frontier showed across the year and through
which mechanisms; the area penalty; the state of operational-stability
evidence; the reporting-completeness picture; and the mechanistic conclusions
THIS issue reached.

The conclusions must be the ones argued in the sections below. If the evidence
for a conclusion is thin, say it is thin.

THE FINISHED REVIEW:
{full}"""

    af = dd / "abstract.md"
    ab = ""
    for attempt in range(3):
        print(f"[13y] abstract{' retry ' + str(attempt) if attempt else ''} ...",
              flush=True)
        cand = clean(write_llm(abs_task))
        cand = re.sub(r"^\s*abstract\s*[:.]?\s*", "", cand, flags=re.I).strip()
        bad_cite = re.findall(r"\[@?[\w.\-/]+\]", cand)
        if bad_cite:
            print(f"[13y]   REJECT abstract has citations {bad_cite[:4]}")
            continue
        stray = re.findall(r"(?<!\{)\b\d[\d.,]*\b(?!\})", cand)
        if stray:
            print(f"[13y]   REJECT abstract has literal digits {stray[:6]}")
            continue
        nw = len(cand.split())
        if not (ab_lo * 0.9 <= nw <= ab_hi * 1.1):
            print(f"[13y]   REJECT abstract {nw}w outside [{ab_lo},{ab_hi}]")
            continue
        ab = cand
        break
    if not ab:
        raise SystemExit("FAIL-CLOSED: abstract failed the no-citation / "
                         "no-digit / word-band contract in 3 attempts")
    af.write_text(ab, encoding="utf-8")
    print(f"[13y]   abstract {len(ab.split())}w (placeholders unresolved)")
    log.append({"stage": "13y_abstract", "cli": "agy", "model": MODEL,
                "words": len(ab.split()), "shipped": True,
                "tokens_in": 0, "tokens_out": 0,
                "token_source": "estimated", "at": time.strftime("%H:%M:%S")})

    if log:
        with (rd / "tokens.jsonl").open("a", encoding="utf-8") as fh:
            for r in log:
                fh.write(json.dumps(r) + "\n")

    tot = sum(len(v.split()) for v in secs.values())
    meta = {"year": year,
            "words": {k: len(v.split()) for k, v in secs.items()},
            "abstract_words_raw": len(ab.split()),
            "total_words": tot,
            "sections": len(sections),
            "map_sha256": smap["sha256"],
            "angle_index": int(year) % len(ANGLES),
            "writer": f"agy/{MODEL}",
            "yoy": None,
            "prior_yearly_issue": False,
            # Recorded so the SECOND yearly issue does not silently inherit a
            # cold-start design: prior_closing_block() must be ported then.
            "todo_next_issue": "port prior_closing_block() from the monthly "
                               "project once a prior yearly issue exists"}
    done(rd, "13y_draft_yearly", **meta)
    print("[13y]", json.dumps(meta)[:500])
    return meta


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(
            "usage: s13y_draft_yearly.py <YYYY> [section_ids to redraft]\n"
            "No default: the period must be stated, never inferred.")
    ids = [a for a in sys.argv[2:] if a.isdigit()]
    draft(sys.argv[1], only=ids or None)
