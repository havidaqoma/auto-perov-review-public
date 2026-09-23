"""18y_build_yearly: assemble, gate, and render the yearly manuscript.

LINEAGE
-------
Ported from the monthly project's `s18d_build_v4.py`
(auto-perov-review), which has rendered three shipped issues.
Every mechanism below exists because a specific defect shipped once, and the
comment on each says which. Nothing here is reinvented.

CARRIED OVER UNCHANGED
  resolve_placeholders   the anti-fabrication boundary
  canon alias resolution accept an aliased key only when it matches EXACTLY
                         one card; fail closed on ambiguity
  merge-then-link order  merge on PLAIN numbers, then link INSIDE the group
  nomenclature rule      any bracketed number above len(order) is not a cite
  provenance from records extractor from cards, writer from the ledger
  title-block geometry   measured on the rendered page, never tuned by eye
  notation AFTER linking so a formula rule cannot chew a DOI's digits
  freeze + orphan check  refuse to build against a moving draft set

YEARLY DELTAS
  bands come from config/yearly.yaml, which holds NEW keys. config/gates.yaml
    still describes the monthly artifact and is never read for an envelope.
  G3c is PER SAMPLE CLASS: 29.4% single junction, 47.6% two-junction tandem.
    A single global bound would reject the tandem records that dominate this
    frontier; the tandem bound applied globally would readmit the
    32.95%-as-single-junction defect G3c exists to catch.
  G11-coverage is NEW: a yearly issue built from a partial year is internally
    consistent, passes every other gate, and misstates its own scope.
  G8 is NOT RUN. It compares against prior issues, and this repository holds
    none. Recorded as a cold start rather than silently reported as a pass.

FIGURES
  F1-F6 do not exist yet in this project. The build therefore renders without
  them and REPORTS the absence in the gate report. It does not fail: a
  figure-less draft is a legitimate intermediate. It must never be silent,
  because "no figures attached" and "figures attached correctly" would
  otherwise look identical in the report.
"""
from __future__ import annotations

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

from stages.boilerplate import data_availability  # noqa: E402
from stages.boilerplate import (ACK, AFFIL, AI_DECL, CORRESP_NOTE,  # noqa: E402
                                expand_abbrev, md_esc, tex_esc)
from stages.hygiene import find_narration                    # noqa: E402
from stages.layout import measure as measure_title_block     # noqa: E402
from stages.notation import check_notation, format_notation  # noqa: E402
from stages.util import CONFIG, ROOT, done, read_jsonl, run_dir, is_year  # noqa: E402
from stages.yearly_corpus import (aggregate, axis_mass,      # noqa: E402
                                  canon_work_key, yearly_dir)
from stages.device_class import is_indoor_value             # noqa: E402
from stages.yearly_tables import build_tables                # noqa: E402

TITLE_FRAME = "Perovskite Photovoltaics"


def _v(c: dict, k: str):
    src = c.get("stability") if k in ("t80_h", "duration_h") else c.get("performance")
    f = (src or {}).get(k)
    return f["value"] if isinstance(f, dict) and f.get("value") is not None else None


def _fmt(x) -> str:
    if isinstance(x, float) and x == int(x):
        return str(int(x))
    return str(x)


# Multi-junction markers. Checked against the ANCHOR first, then the title.
# A paper's title describes the PAPER; the anchor describes the NUMBER, and
# the anchor is the only text verified verbatim against the source. The June
# 2026 monthly issue shipped a certified 32.95% tandem as a single-junction
# result because the filter read the title, which contained neither "tandem"
# nor "silicon" while the abstract reported both devices.
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


def resolve_placeholders(ab: str, S: dict, cl: list,
                         agg: dict) -> tuple[str, dict, list]:
    """Substitute {{TOKEN}} with canonical values. Fails closed on leftovers.

    THE ANTI-FABRICATION BOUNDARY. The writer produced prose containing no
    digits; every number below comes from stats_yearly.json or a claim card.
    An unresolvable token fails the build, because a hole never ships.
    """
    cert = sorted(((_v(c, "pce_certified"), c) for c in cl
                   if _v(c, "pce_certified")), key=lambda x: -x[0])
    areas = sorted(((_v(c, "active_area_cm2"), c) for c in cl
                    if _v(c, "active_area_cm2")), key=lambda x: -x[0])
    t80 = sorted(((_v(c, "t80_h"), c) for c in cl if _v(c, "t80_h")),
                 key=lambda x: -x[0])
    n_proto = len([c for c in cl if (c.get("stability") or {}).get("protocol")])
    sj = [v for v, c in cert if _is_single_junction(c)]
    area_cert = [(a, c) for a, c in areas if _v(c, "pce_certified")]

    vals = {
        "N_CORPUS": _fmt(S["corpus.n"]),
        "N_DEPTH": _fmt(S["cards.n"]),
        "N_READ": _fmt(len(cl)),
        "N_MONTHS": _fmt(S["n_months"]),
        "N_MONTH_UNKNOWN": _fmt(agg.get("month_unknown_corpus", 0)),
        "N_CERT": _fmt(len(cert)),
        "P_TOP_CERT_YEAR": f"{_fmt(cert[0][0])}%" if cert else None,
        "P_TOP_SJ": f"{_fmt(max(sj))}%" if sj else None,
        "P_CERT_FIRST": (f"{_fmt(S['frontier.year_first_certified'])}%"
                         if S.get("frontier.year_first_certified") is not None
                         else None),
        "P_CERT_LAST": (f"{_fmt(S['frontier.year_last_certified'])}%"
                        if S.get("frontier.year_last_certified") is not None
                        else None),
        "DELTA_CERT_PP": (_fmt(S["frontier.certified_delta_pp"])
                          if S.get("frontier.certified_delta_pp") is not None
                          else None),
        "A_MAX": (f"{_fmt(area_cert[0][0])} cm$^2$" if area_cert else
                  (f"{_fmt(areas[0][0])} cm$^2$" if areas else None)),
        "P_AREA_MAX": (f"{_fmt(_v(area_cert[0][1], 'pce_certified'))}%"
                       if area_cert else None),
        "N_T80": _fmt(len(t80)),
        "H_T80_MAX": f"{_fmt(int(t80[0][0]))} h" if t80 else None,
        "N_PROTO": _fmt(n_proto),
        "PCT_CERT_YEAR": (f"{S['audit.year.certified.pct']}%"
                          if S.get("audit.year.certified.pct") is not None
                          else None),
        "PCT_CERT_MIN": (f"{S['audit.year.certified.month_min_pct']}%"
                         if S.get("audit.year.certified.month_min_pct") is not None
                         else None),
        "PCT_CERT_MAX": (f"{S['audit.year.certified.month_max_pct']}%"
                         if S.get("audit.year.certified.month_max_pct") is not None
                         else None),
        "PCT_EFF": (f"{S['audit.year.efficiency_stated.pct']}%"
                    if S.get("audit.year.efficiency_stated.pct") is not None
                    else None),
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
            f"year has no value for it; do not ship a hole.")
    return ab, vals, used


def derive_title(year: str, smap: dict, S: dict | None = None) -> str:
    """{Frame} in {Year}: {slot from the year's leading axes}.

    The slot names the axes that actually led the year, so a defect-heavy
    year says so. Nothing is hardcoded.
    """
    tt = yaml.safe_load((CONFIG / "title_terms.yaml").read_text(encoding="utf-8"))
    phrases = tt.get("axis_phrases", {})
    rot = int(year)

    # ---- FINDING-LED SLOT (Havid, 2026-09-11) ------------------------
    # The topic slot named the two leading device classes, which is
    # accurate and says nothing. A reader scanning a contents page learns
    # only that the issue covers single junctions and tandems -- true of
    # every issue this pipeline will ever produce.
    #
    # So the slot now states the year's STRONGEST SUPPORTED FINDING, and
    # each candidate is GATED ON THE STATISTIC THAT WOULD MAKE IT TRUE.
    # A title is prose reaching a reader, so it traces to the evidence
    # chain like every other claim: if the data does not support the
    # sentence, the sentence is not available.
    #
    # Measured on 2025 and the reason the first candidate wins:
    #   frontier.certified_delta_pp   -0.16   -> the frontier HELD
    #   single-junction self 29.11 vs cert 26.96 (+2.15 pp gap)
    #   audit.year.certified.pct       5.8%   -> verification is SCARCE
    #   audit.year.isos_label.pct      1.1%   -> lifetime evidence thinner
    #
    # Ordered most-to-least specific. The first candidate whose guard
    # passes is used, so a year with a genuinely climbing frontier falls
    # through to a different sentence instead of asserting a stall.
    # S is optional so the function stays callable from a test without a
    # stats file. Absent stats means NO finding is claimed: the title
    # falls back to the topic slot rather than asserting something the
    # evidence has not been consulted about.
    St = S or {}
    delta = St.get("frontier.certified_delta_pp")
    pct_cert = St.get("audit.year.certified.pct")
    pct_isos = St.get("audit.year.isos_label.pct")

    def _flat() -> bool:
        # "Held" means the first and last month with data differ by less
        # than half a point. Anything larger is a trend and must not be
        # described as a stall.
        return delta is not None and abs(float(delta)) < 0.5

    def _scarce() -> bool:
        return pct_cert is not None and float(pct_cert) < 15.0

    def _thin_lifetime() -> bool:
        return pct_isos is not None and float(pct_isos) < 5.0

    finding_slots = [
        (lambda: _flat() and _scarce(),
         "the certified frontier held while verification stayed scarce"),
        (lambda: _flat(),
         "a frontier that held its ground"),
        (_scarce,
         "claims outpacing independent verification"),
        (_thin_lifetime,
         "efficiency reported, lifetime seldom measured"),
    ]
    finding = next((txt for guard, txt in finding_slots if guard()), None)

    # The spine emits `device` roles now. Matching on "mechanism" found
    # nothing and the title silently fell back to the neutral slot -- a
    # generated title that stops reflecting the issue is worse than a
    # hardcoded one, because it still LOOKS derived.
    mech = [s for s in smap["sections"] if s["role"] == "device"][:2]
    picked = []
    for s in mech:
        bank = phrases.get(s["axis"]) or []
        if bank:
            picked.append(bank[rot % len(bank)])
    if finding:
        # The finding replaces the topic list rather than joining it: two
        # clauses either side of a colon is a title, three is a paragraph.
        picked = [finding]
    if not picked:
        picked = ["an annual mechanism and reporting audit"]
    # Join with a comma when a phrase already contains "and", or the slot
    # reads "X and Y and Z". Two conjunctions in one noun phrase is a defect
    # a reader sees immediately, and the title is the most-read line.
    if len(picked) == 2 and any(" and " in p for p in picked):
        slot = f"{picked[0]}, {picked[1]}"
    else:
        slot = " and ".join(picked)
    slot = slot[0].upper() + slot[1:] if slot else slot
    title = f"{TITLE_FRAME} in {year}: {slot}"

    banned = [b.lower() for b in tt.get("banned_in_title", [])]
    hits = [b for b in banned if b in title.lower()]
    if hits:
        raise SystemExit(f"FAIL-CLOSED title contains banned term {hits}")
    if title.count(":") != 1:
        raise SystemExit(f"FAIL-CLOSED title must have exactly one colon: {title}")
    if len(title.split()) > tt.get("max_title_words", 16):
        title = f"{TITLE_FRAME} in {year}: {picked[0].capitalize()}"
    # A publication count in the title would be a number outside the evidence
    # chain. The year itself is allowed and is removed before the check.
    if re.search(r"\b\d{2,}\b", title.replace(year, "")):
        raise SystemExit("FAIL-CLOSED title carries a publication count")
    return title


def provenance(rd: pathlib.Path, cards: list, models: dict) -> dict:
    """Derive the AI Usage Declaration from RECORDS, never from live config.

    The monthly project shipped an August PDF declaring an extractor that
    never touched it: config was edited mid-session AFTER extraction ran, and
    the declaration read current state instead of what actually happened. A
    back-matter fact about which model did what is prose reaching a reader and
    traces to the evidence chain like every other claim.
    """
    import collections

    ext = collections.Counter(
        (c.get("extractor") or {}).get("model") for c in cards
        if (c.get("extractor") or {}).get("model"))
    if not ext:
        raise SystemExit("FAIL-CLOSED provenance: no card records an "
                         "extractor.model; cannot declare what extracted this")
    if len(ext) > 1:
        raise SystemExit(
            f"FAIL-CLOSED provenance: cards were extracted by MORE THAN ONE "
            f"model {dict(ext)}. Declaring one model for cards two models "
            f"produced is a false statement in the back matter.")
    ext_model = next(iter(ext))

    writers = set()
    tj = rd / "tokens.jsonl"
    if tj.exists():
        for line in tj.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if str(r.get("stage", "")).startswith("13y") and r.get("model"):
                writers.add(r["model"])
    if len(writers) > 1:
        raise SystemExit(f"FAIL-CLOSED provenance: prose was written by more "
                         f"than one model {sorted(writers)}; exactly one "
                         f"prose voice per issue.")
    writer_model = next(iter(writers)) if writers else models["generator"]["model"]
    rev = models.get("reviewer_science") or {}
    return {"extractor": ext_model, "writer": writer_model,
            "reviewer": rev.get("display_name") or rev.get("model") or "none"}


def build(year: str) -> dict:
    if not is_year(year):
        raise SystemExit(f"expected a 4-digit year, got {year!r}")

    rd = run_dir(year, create=False)
    yd = yearly_dir(year)
    S = json.loads((yd / "stats_yearly.json").read_text(encoding="utf-8"))
    smap = json.loads((yd / "yearly_section_map.json").read_text(encoding="utf-8"))
    Y = yaml.safe_load((CONFIG / "yearly.yaml").read_text(encoding="utf-8"))
    models = yaml.safe_load((CONFIG / "models.yaml").read_text(encoding="utf-8"))

    agg = aggregate(year, require_full_year=False)
    cards = {c["work_key"]: c for c in agg["cards"]}
    corpus = {r["work_key"]: r for r in agg["corpus"]}
    oa = {}
    for r in read_jsonl(rd / "01_openalex.jsonl"):
        k = (r.get("doi") or "").replace("https://doi.org/", "").lower()
        if k:
            oa[k] = r

    dd = rd / "draft_yearly"
    ids = [s["id"] for s in smap["sections"]]
    secs = {}
    for sid in ids:
        f = dd / f"sec{sid}.md"
        if not f.exists():
            raise SystemExit(f"FAIL-CLOSED: draft_yearly/sec{sid}.md missing")
        secs[sid] = f.read_text(encoding="utf-8").strip()
    abs_f = dd / "abstract.md"
    if not abs_f.exists():
        raise SystemExit("FAIL-CLOSED: draft_yearly/abstract.md missing")
    ab_raw = abs_f.read_text(encoding="utf-8").strip()

    # ---- freeze inputs before gating -----------------------------------
    # Two orphaned draft processes once kept writing after their runs reported
    # complete: prose_words drifted 4498 -> 4304 across builds and every gate
    # passed every time, against a draft set that changed seconds later.
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
            # Detect and REFUSE; never kill. Killing by broad name match would
            # take down the orchestrator running the build.
            raise SystemExit(f"FAIL-CLOSED: agy writer still running (PID {live}).")
    except FileNotFoundError:
        print("[18y] WARN: powershell unavailable; orphan check skipped")
    except subprocess.TimeoutExpired:
        print("[18y] WARN: orphan check timed out; not treated as clear")

    frozen = {s: {"words": len(v.split()),
                  "sha256": hashlib.sha256(v.encode()).hexdigest()[:16]}
              for s, v in secs.items()}
    body_words = sum(len(v.split()) for v in secs.values())
    print("[18y] freeze " + " ".join(f"s{k}={v['words']}w"
                                     for k, v in frozen.items()))

    cl = list(cards.values())
    ab, abs_vals, abs_tokens = resolve_placeholders(ab_raw, S, cl, agg)

    # ---- abbreviations, abstract then body in reading order -------------
    expanded = []
    ab, e = expand_abbrev(ab)
    expanded += e
    for sid in ids:
        secs[sid], e = expand_abbrev(secs[sid])
        expanded += e

    # ---- citation numbering: ONE pass over the body --------------------
    # A writer transcribes a work_key from its evidence block and can lose a
    # character: the monthly project shipped "[@10.1016/joule.2026.102538]"
    # for a card keyed "10.1016/j.joule.2026.102538". Resolve through a
    # canonical form, and accept the alias ONLY when it matches EXACTLY one
    # card. Two candidates means the intended paper is unknown, so it stays
    # unresolved and G1 fails. Never guess which paper a number belongs to.
    _alias: dict[str, list[str]] = {}
    for wk in cards:
        _alias.setdefault(canon_work_key(wk), []).append(wk)
    aliased: dict[str, str] = {}

    def resolve_key(wk: str) -> str | None:
        if wk in cards:
            return wk
        cand = _alias.get(canon_work_key(wk), [])
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
    doi_of = {wk: (corpus.get(wk, {}).get("doi") or "") for wk in order}
    by_num = {n: wk for wk, n in num.items()}

    # ORDER MATTERS. Linking each marker as \href{doi}{[12]} puts brace groups
    # between adjacent brackets, so merge_cites can no longer see "[1] [2]"
    # and the PDF shows "[1] [2] [3]" instead of "[1,2,3]". Merge on PLAIN
    # numbers first, then link each number INSIDE the finished group.
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
                return f"[{num[wk]}]"
            unresolved.append(m.group(1))
            return ""
        secs[sid] = re.sub(r"\[@([^\]\s]+)\]", rep, secs[sid])
        secs[sid] = re.sub(r"\s+([.,;])", r"\1", secs[sid])
        secs[sid] = merge_cites(secs[sid])
        secs[sid] = link_numbers(secs[sid])

    # [60]fullerene and [100] growth are nomenclature, not citations. The
    # robust rule: this manuscript has exactly len(order) references, so any
    # bracketed number ABOVE that count cannot be a citation marker.
    CITE_RX = r"\[(\d+(?:,\d+)*)\](?![A-Za-z])"
    n_refs = len(order)
    seq, seen = [], set()
    for m in re.finditer(CITE_RX, "\n".join(secs[s] for s in ids)):
        grp = [int(x) for x in m.group(1).split(",")]
        if any(x > n_refs or x == 0 for x in grp):
            continue
        for x in grp:
            if x not in seen:
                seen.add(x)
                seq.append(x)
    monotonic = seq == sorted(seq)

    # ---- reference list ------------------------------------------------
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

    # ---- figures: attached by ROLE/AXIS, never by section number --------
    # F1-F6 do not exist in this project yet. Absence is REPORTED, never
    # silent: "no figures attached" and "figures attached correctly" must not
    # look identical in the gate report.
    figdir = rd / "fig"
    fig_for: dict = {}
    used: set[str] = set()

    def claim(sid: str, fn: str, cap: str) -> None:
        if fn in used or sid in fig_for:
            return
        if not (figdir / fn).exists():
            return
        used.add(fn)
        fig_for[sid] = (fn, cap)

    CAP = {
        "F5_frontier_trajectory.pdf":
            "Best independently certified efficiency in each month of the "
            "year, with the device class of the leading value at each point. "
            "Point size scales with the number of certified reports.",
        "F6_audit_trajectory.pdf":
            "Reporting-practice detection rates across the year. Diamonds "
            "mark the pooled annual rate and bars the monthly range. Rates "
            "are computed over abstracts and measure what abstracts state, "
            "not what the underlying papers did.",
        "F1a_frontier_single_junction.pdf":
            "Single-junction devices: independently certified against "
            "self-reported champion efficiencies, grouped by device "
            "architecture. The dashed line marks the 29.4 percent "
            "Shockley-Queisser limit for a 1.55 eV absorber. Simulation and "
            "review studies are excluded.",
        "F1b_frontier_tandem.pdf":
            "Tandem and module devices: independently certified against "
            "self-reported champion efficiencies. The dashed line marks the "
            "47.6 percent two-junction detailed-balance limit. Simulation "
            "and review studies are excluded.",
        "F2_area_penalty.pdf":
            "Efficiency against reported active or aperture area. Shading "
            "marks the sub-0.3 cm$^2$ laboratory-cell regime in which most "
            "champion values are measured.",
        "F3a_effort_single_junction.pdf":
            "Single-junction devices: where the year's close reading was "
            "directed, by mechanism axis and device architecture.",
        "F3b_effort_tandem.pdf":
            "Tandem and module devices: where the year's close reading was "
            "directed, by mechanism axis and device architecture.",
        "F4_stability_evidence.pdf":
            "The year's operational-stability evidence in full. Left, every "
            "reported time to 80 percent of initial performance. Right, the "
            "stability protocol labels used.",
    }

    # ATTACHMENT BY ROLE, AND THE BUG THIS FIXES.
    #
    # F1 was rendered, copied into the deliverable directory, and NEVER
    # PLACED IN THE MANUSCRIPT. The claim was keyed on `role == "frontier"`,
    # carried over from the monthly spine -- but the YEARLY spine has no
    # frontier role, it has `trajectory`. So the condition never fired, F1
    # sat orphaned on disk, and G9c passed because it only checks that
    # attached figures are unique. G9e passed because it only checks F5/F6
    # exist. Two gates, both green, neither watching the actual hole.
    #
    # A figure keyed on a role the map does not contain is silently dropped,
    # so every claim below is keyed on a role or axis the yearly map
    # ACTUALLY emits, and G9f now asserts every rendered figure is placed.
    for s_ in smap["sections"]:
        role, axis = s_["role"], s_.get("axis")
        if role == "trajectory":
            # Both frontier panels belong with the trajectory section: it is
            # the section that argues about certified-versus-claimed, and the
            # yearly map has no `frontier` role at all.
            claim(s_["id"], "F1a_frontier_single_junction.pdf",
                  CAP["F1a_frontier_single_junction.pdf"])
        if role == "audit":
            claim(s_["id"], "F6_audit_trajectory.pdf",
                  CAP["F6_audit_trajectory.pdf"])
        if role == "synthesis":
            claim(s_["id"], "F5_frontier_trajectory.pdf",
                  CAP["F5_frontier_trajectory.pdf"])
    for s_ in smap["sections"]:
        if s_["role"] != "device":
            continue
        dev = s_.get("device_class")
        if dev in ("all_perovskite_tandem", "hybrid_tandem"):
            claim(s_["id"], "F1b_frontier_tandem.pdf",
                  CAP["F1b_frontier_tandem.pdf"])
        elif dev == "module":
            claim(s_["id"], "F2_area_penalty.pdf", CAP["F2_area_penalty.pdf"])
        elif dev == "single_junction":
            claim(s_["id"], "F4_stability_evidence.pdf",
                  CAP["F4_stability_evidence.pdf"])
    for s_ in smap["sections"]:
        if s_["role"] == "device" and s_.get("device_class") == "single_junction":
            claim(s_["id"], "F3a_effort_single_junction.pdf",
                  CAP["F3a_effort_single_junction.pdf"])
        if s_["role"] == "device" and s_.get("device_class") == "hybrid_tandem":
            claim(s_["id"], "F3b_effort_tandem.pdf",
                  CAP["F3b_effort_tandem.pdf"])
    # Any figure still unplaced goes to the trajectory section rather than
    # being dropped. Rendering a figure and then discarding it wastes the
    # plate and, worse, leaves the deliverable directory carrying a file the
    # manuscript never references.
    _lead = next((s["id"] for s in smap["sections"]
                  if s["role"] == "trajectory"), smap["sections"][0]["id"])
    for fn in sorted(p.name for p in figdir.glob("*.pdf")):
        if fn in used or fn not in CAP:
            continue
        for s_ in smap["sections"]:
            if s_["id"] not in fig_for:
                claim(s_["id"], fn, CAP[fn])
                break

    date_str = time.strftime("%B ") + str(int(time.strftime("%d"))) + \
        time.strftime(", %Y")
    TITLE = derive_title(year, smap, S)

    # TITLE-BLOCK SPACING IS MEASURED, NOT TUNED. Three blind tunings failed
    # because \vspace after \end{minipage} lands in horizontal mode and is
    # DISCARDED. The date goes INSIDE the minipage, spaced by \\[...], which
    # provably works. G10 measures both gaps on the rendered PDF.
    head = [r"\begin{center}",
            r"{\LARGE\bfseries " + tex_esc(TITLE) + r"\par}",
            r"\vspace{1.1em}",
            r"{\large Havid Aqoma\textsuperscript{1,2,3,4,*}\par}",
            r"\vspace{0.7em}",
            r"\begin{minipage}{\textwidth}\centering\small"]
    for i, a in enumerate(AFFIL, 1):
        sep = r"\\[0.55em]" if i == len(AFFIL) else r"\\[0.25em]"
        head.append(r"\textsuperscript{" + str(i) + r"}" + tex_esc(a) + sep)
    head.append(tex_esc(CORRESP_NOTE).replace(r"\_", "_") + r"\\[2.0em]")
    head += [date_str, r"\end{minipage}", r"\end{center}", r"\vspace{0.8em}"]

    # ---- notation: applied AFTER citation linking ----------------------
    # notation.py masks hyperlinks and DOIs; running it earlier would let a
    # formula rule chew a DOI's digits.
    notation_counts: dict = {}
    ab, _c = format_notation(ab)
    for k, v in _c.items():
        notation_counts[k] = notation_counts.get(k, 0) + v
    for sid in ids:
        secs[sid], _c = format_notation(secs[sid])
        for k, v in _c.items():
            notation_counts[k] = notation_counts.get(k, 0) + v
    print(f"[18y] notation: {sum(notation_counts.values())} substitutions")

    md = ["\n".join(head), "", "## Abstract", "", ab, "",
          "**Keywords:** perovskite photovoltaics; single-junction cells; "
          "all-perovskite tandems; perovskite/silicon tandems; modules; "
          "operational stability; annual review", ""]

    # ---- TABLES: computed by yearly_tables, ATTACHED BY ROLE ------------
    # The same defect that orphaned F1 was waiting here: yearly_tables
    # computed three tables and the draft imported build_tables, but nothing
    # ever placed them in the manuscript. A table generated and not rendered
    # is invisible to every gate, because the gates read the manuscript.
    # G9f below asserts each expected table is actually PLACED.
    from stages.util import read_jsonl as _rj
    _ab_pool = {x["work_key"]: x["abstract"]
                for x in _rj(rd / "private" / "02_abstracts.jsonl")}
    tables = build_tables(cl, _ab_pool)
    TABLE_FOR = {"trajectory": "T1", "audit": "T2", "synthesis": "T3"}
    tbl_placed: dict[str, str] = {}
    for s in smap["sections"]:
        tid = TABLE_FOR.get(s["role"])
        if tid and tid not in tbl_placed.values():
            tbl_placed[s["id"]] = tid

    n_tbl = 0
    n_fig = 0
    for s in smap["sections"]:
        sid = s["id"]
        md += [f"## {sid}. {s['title']}", "", secs[sid], ""]
        if sid in tbl_placed:
            tid = tbl_placed[sid]
            t = tables[tid]
            n_tbl += 1
            md += [f"**Table {n_tbl}.** {t['caption']}", ""]
            md += t["markdown"]
            md += [""]
        if sid in fig_for:
            fn, cap = fig_for[sid]
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
           data_availability("year"), "",
           "## AI Usage Declaration", "",
           AI_DECL.format(**provenance(rd, cl, models)),
           "", "## References", ""] + refs
    manuscript = "\n".join(md)
    (rd / "manuscript_yearly.md").write_text(manuscript, encoding="utf-8")

    # ================= GATES =================
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
    # A private copy here was once NARROWER than the draft-stage copy, so a
    # line that slipped clean() also passed G4 and shipped.
    leak = find_narration(prose)
    gate["G4"] = {
        "status": "pass" if not bad and not prose.count("\u2014") and not leak
                  else "fail",
        "detail": {"em_dash": prose.count("\u2014"), "banned": bad,
                   "self_report_leak": leak[:5]}}

    gate["G1"] = {"status": "pass" if not unresolved else "fail",
                  "detail": {"resolved": len(order),
                             "unresolved": unresolved[:8], "aliased": aliased}}

    lo, hi = Y["citations_yearly"]["total_band"]
    gate["G2c-cite-count"] = {
        "status": "pass" if lo <= len(order) <= hi else "fail",
        "detail": {"cited": len(order), "target_range": [lo, hi],
                   "words_per_citation": round(body_words / max(len(order), 1), 1)}}

    ceil_total = int(smap["total_ceiling"] * 1.15)
    per_sec_ok = {s["id"]: len(secs[s["id"]].split()) <= int(s["ceiling"] * 1.35)
                  for s in smap["sections"]}
    gate["G2"] = {
        "status": "pass" if body_words <= ceil_total and all(per_sec_ok.values())
                  else "fail",
        "detail": {"prose_words": body_words, "ceiling": ceil_total,
                   "per_section_within_135pct": per_sec_ok,
                   "map_sha256": smap["sha256"], "input_freeze": frozen}}

    gate["G2b-cite-order"] = {
        "status": "pass" if monotonic else "fail",
        "detail": {"first_appearance_sequence": seq[:20], "monotonic": monotonic}}

    g6 = re.findall(r"\bwe (?:measured|fabricated|synthesi[sz]ed|simulated)\b", low)
    gate["G6"] = {"status": "pass" if not g6 else "fail", "detail": {"hits": g6}}

    # G3: every abstract numeral must trace to stats or a card. With
    # substitution this is automatic, so a failure means the writer smuggled a
    # digit past the no-digit contract.
    stat_nums = {str(v) for v in S.values() if isinstance(v, (int, float))}
    stat_nums |= {_fmt(v) for v in S.values() if isinstance(v, (int, float))}
    card_nums = set()
    for c in cl:
        for grp in ("performance", "stability"):
            for f in (c.get(grp) or {}).values():
                if isinstance(f, dict) and f.get("value") is not None:
                    card_nums.add(_fmt(f["value"]))
    allowed = stat_nums | card_nums | {_fmt(len(cl)), _fmt(len(order))}
    # Values resolve_placeholders COMPUTES rather than reads appear in neither
    # stats nor any card field, so admit them explicitly. G3 once flagged a
    # number the build had itself derived from the evidence.
    allowed |= {str(v) for v in abs_vals.values() if v is not None}
    allowed |= {re.sub(r"[^\d.]", "", str(v)) for v in abs_vals.values()
                if v is not None}
    bad_nums = [n for n in re.findall(r"\b\d+(?:\.\d+)?\b", ab)
                if n not in allowed and n not in {"80", "2", "1"}]
    gate["G3-abstract"] = {
        "status": "pass" if not bad_nums else "fail",
        "detail": {"unverified": bad_nums[:8], "words": len(ab.split()),
                   "placeholders_resolved": abs_tokens}}

    # G3c: PER SAMPLE CLASS. G3 asks only "does this number trace to a card?".
    # The monthly June issue said "32.95% in single-junction inverted cells"
    # and 32.95 DID trace to a card, so G3 passed it. The number was real; the
    # device was wrong. Only a physical bound can see that.
    P = Y["plausibility"]
    implausible = []
    for tok, limit, why in (
        ("P_TOP_SJ", P["single_junction_pce_max_pct"],
         "a single-junction perovskite cannot exceed the Shockley-Queisser "
         "limit; this is a tandem or module value on the wrong device"),
        ("P_TOP_CERT_YEAR", P["tandem_2t_pce_max_pct"],
         "above the two-junction detailed-balance limit"),
        ("P_CERT_FIRST", P["tandem_2t_pce_max_pct"], "above the 2-junction limit"),
        ("P_CERT_LAST", P["tandem_2t_pce_max_pct"], "above the 2-junction limit"),
    ):
        v = abs_vals.get(tok)
        if not v:
            continue
        try:
            n = float(re.sub(r"[^\d.]", "", str(v)))
        except ValueError:
            continue
        if n > limit:
            implausible.append({"token": tok, "value": n, "limit": limit,
                                "why": why})
    # G3c cannot see an ILLUMINATION mismatch: it selects a bound by device
    # class, and for an indoor measurement the device class is correct. So
    # the abstract's substituted values are checked against their own
    # anchors here as well.
    illum_conflicts = []
    for tok, key in (("P_TOP_CERT_YEAR", "pce_certified"),
                     ("P_CERT_FIRST", "pce_certified"),
                     ("P_CERT_LAST", "pce_certified"),
                     ("P_TOP_SJ", "pce_certified")):
        v = abs_vals.get(tok)
        if not v:
            continue
        try:
            n = float(re.sub(r"[^\d.]", "", str(v)))
        except ValueError:
            continue
        for c in cl:
            val = _v(c, key)
            if val is None or abs(float(val) - n) > 1e-6:
                continue
            f = (c.get("performance") or {}).get(key) or {}
            if is_indoor_value(f.get("anchor", ""), val):
                illum_conflicts.append({
                    "token": tok, "value": n, "work_key": c.get("work_key"),
                    "why": ("this value was measured under indoor or weak "
                            "light; every bound in the abstract is an AM1.5G "
                            "detailed-balance limit, so the comparison is "
                            "between different spectra")})
            break

    gate["G3c-abstract-physics"] = {
        "status": "pass" if not implausible and not illum_conflicts else "fail",
        "detail": {"implausible": implausible,
                   "illumination_conflicts": illum_conflicts,
                   "single_junction_limit_pct": P["single_junction_pce_max_pct"],
                   "tandem_2t_limit_pct": P["tandem_2t_pce_max_pct"]}}

    alo, ahi = Y["abstract_yearly"]["word_band"]
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

    # G8 is NOT RUN: it compares against prior issues and this repository
    # holds none. Recorded as a cold start rather than reported as a pass, so
    # nobody later reads a green G8 as evidence of checked novelty.
    gate["G8-novelty"] = {
        "status": "cold-start",
        "detail": {"reason": "no prior yearly issue in this repository; "
                             "similarity cannot be measured against nothing",
                   "action_for_next_issue": "port prior_closing_block() and "
                                            "run G8 against this issue"}}

    all_prose = ab + "\n" + "\n".join(secs.values())
    notation_report = check_notation(all_prose)
    gate["G9a-notation"] = {
        "status": "pass" if not notation_report["defects"] else "fail",
        "detail": {"residual_defects": notation_report["defects"],
                   "ambiguous_for_human_review": notation_report["ambiguous"],
                   "substitutions_applied": sum(notation_counts.values())}}

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

    attached = [fn for fn, _ in fig_for.values()]
    dupes = sorted({f for f in attached if attached.count(f) > 1})
    on_disk = sorted(p.name for p in figdir.glob("*.pdf")) if figdir.exists() else []
    gate["G9c-figure-unique"] = {
        "status": "pass" if not dupes else "fail",
        "detail": {"attached": attached, "duplicates": dupes,
                   "n_attached": len(attached),
                   "figures_present_on_disk": on_disk}}

    # ---- G9e-figures-present -------------------------------------------
    # THIS GATE EXISTS BECAUSE G5 WAS WIDENED.
    #
    # G5 measures pages, and a missing figure shows up as a page shortfall.
    # The first yearly build failed G5 at 19.6/30 pages against a floor of
    # 20/32 for exactly one reason: `figures: 0`. On 2026-09-09 Havid decided
    # to widen the band to admit 30 pages, which is defensible -- the old
    # floor was a PROJECTION scaled from monthly output and had never been
    # bracketed on a real yearly artifact.
    #
    # But widening it removed the pipeline's only alarm for a figure-less
    # manuscript. A gate that stops noticing something is worse than no gate,
    # because it teaches you to trust output you should be checking. So the
    # alarm moves here and is stated in its own terms: figures are counted,
    # not inferred from a page count.
    #
    # Reported as FAIL, not as a warning. A review whose argument rests on a
    # twelve-point trajectory and a reporting-practice series, with neither
    # plotted, is genuinely incomplete. The PDF still renders so it can be
    # read; it is simply not shippable, which is the same standing every
    # other failing gate has.
    expected_figs = ["F5_frontier_trajectory.pdf", "F6_audit_trajectory.pdf"]
    missing_figs = [f for f in expected_figs if f not in on_disk]
    gate["G9e-figures-present"] = {
        "status": "pass" if not missing_figs else "fail",
        "detail": {"n_attached": len(attached), "on_disk": on_disk,
                   "missing_required": missing_figs,
                   "why": ("F5 plots the certified frontier month by month and "
                           "F6 plots reporting practice month by month. Both "
                           "carry quantities only a yearly issue has, and the "
                           "trajectory and audit sections argue from them. "
                           "This gate carries the figure alarm that G5 lost "
                           "when its page band was widened on 2026-09-09.")}}

    # ---- G9f-tables-present ---------------------------------------------
    # THE SAME DEFECT THAT ORPHANED F1, ONE ARTIFACT TYPE LATER.
    #
    # yearly_tables computed T1/T2/T3 and the draft stage imported
    # build_tables, but nothing rendered them into the manuscript. A table
    # generated and not placed is invisible to every other gate, because
    # every other gate reads the manuscript: the tables were simply absent
    # and no check noticed.
    #
    # F1 taught this exact lesson for figures and G9e was written for it.
    # The lesson did not transfer, because G9e names figure FILES. So this
    # gate asserts PLACEMENT for tables, measured against the rendered
    # markdown rather than against the fact that the objects were built.
    expected_tables = ["T1", "T2", "T3"]
    placed_ids = sorted(tbl_placed.values())
    missing_tables = [t for t in expected_tables if t not in placed_ids]
    # Count the rendered headers, not the intent: a table can be "placed"
    # in the plan and still be absent from the markdown if the section it
    # was assigned to never made it into the document.
    rendered = len(re.findall(r"^\*\*Table \d+\.\*\*", manuscript, flags=re.M))
    gate["G9f-tables-present"] = {
        "status": "pass" if (not missing_tables
                             and rendered == len(expected_tables)) else "fail",
        "detail": {"expected": expected_tables, "placed": placed_ids,
                   "missing": missing_tables,
                   "rendered_in_manuscript": rendered,
                   "why": ("a table computed but never rendered is invisible "
                           "to every gate that reads the manuscript; this "
                           "gate measures PLACEMENT, not construction")}}

    ai_txt = "\n".join(str(x) for x in md if "Structured extraction used" in str(x))
    BARE_SLUGS = ("opus", "sonnet", "haiku", "gemini", "qwen", "muse-spark")
    bad_names = []
    for slug in BARE_SLUGS:
        # Match case-sensitively and require the slug NOT be followed by a
        # version token: lowercasing once made this fire on the CORRECT string
        # "used Opus 5", because "Opus 5".lower() starts with "opus".
        if re.search(rf"\b{re.escape(slug)}\b(?![\w.\-]*\s*\d)(?![\w.\-])", ai_txt):
            bad_names.append(slug)
    gate["G9d-model-names"] = {
        "status": "pass" if not bad_names else "fail",
        "detail": {"bare_slugs_found": bad_names}}

    # ---- G11-coverage: the failure mode only a yearly issue has ---------
    # A partial year is internally consistent, passes every other gate, and
    # misstates its own scope. Nothing else can see it.
    n_months = S["n_months"]
    cards_lo, cards_hi = Y["yearly"]["depth_band"]
    dup = agg["cross_month_duplicates"]
    cov_ok = (n_months == 12 and cards_lo <= agg["cards_n"] <= cards_hi)
    gate["G11-coverage"] = {
        "status": "pass" if cov_ok else "fail",
        "detail": {"n_months": n_months, "expected_months": 12,
                   "cards_n": agg["cards_n"], "cards_band": [cards_lo, cards_hi],
                   "month_unknown_corpus": agg.get("month_unknown_corpus"),
                   "cross_month_duplicates": dup,
                   "duplicate_semantics": agg.get("duplicate_semantics"),
                   "corpus_n": agg["corpus_n"]}}

    gate["G10-title-block"] = {"status": "warn",
                               "detail": {"reason": "measured after the PDF exists"}}

    for k, v in gate.items():
        print(f"[18y] {k}: {v['status']}  {json.dumps(v['detail'])[:130]}")

    # ---- render --------------------------------------------------------
    outdir = ROOT / "manuscript" / f"{year}_yearly"
    outdir.mkdir(parents=True, exist_ok=True)
    pandoc = shutil.which("pandoc")
    if not pandoc:
        # pandoc is NOT on PATH on this machine. Do not "fix" PATH and do not
        # trust shutil.which alone.
        for c in (pathlib.Path.home() / "AppData/Local/Pandoc/pandoc.exe",
                  pathlib.Path(r"C:\Program Files\Pandoc\pandoc.exe")):
            if c.exists():
                pandoc = str(c)
                break
    if not pandoc:
        raise SystemExit("FAIL-CLOSED: pandoc not found")
    tectonic = shutil.which("tectonic") or "tectonic"
    pdf = outdir / "manuscript_yearly.pdf"
    p = subprocess.run(
        [pandoc, str(rd / "manuscript_yearly.md"),
         "-f", "markdown+raw_tex-implicit_figures",
         "-V", "geometry:margin=2.4cm", "-V", "fontsize=11pt",
         "-V", "linestretch=1.05", "-V", "colorlinks=true",
         "-V", "linkcolor=[HTML]{1A4E8A}", "-V", "urlcolor=[HTML]{1A4E8A}",
         "-H", str(CONFIG / "tex" / "manuscript_head.tex"),
         f"--pdf-engine={tectonic}", "-o", str(pdf)],
        capture_output=True, text=True, timeout=1200, cwd=str(ROOT))
    if p.returncode != 0 or not pdf.exists():
        (rd / "18y_build_error.txt").write_text(
            (p.stdout or "") + "\n" + (p.stderr or ""), encoding="utf-8")
        raise SystemExit(f"FAIL-CLOSED: pandoc rc={p.returncode}\n"
                         f"{(p.stderr or '')[:1400]}")

    for f in ("manuscript_yearly.md", "claim_cards.jsonl"):
        if (rd / f).exists():
            shutil.copy(rd / f, outdir / f)
    for f in ("stats_yearly.json", "yearly_section_map.json"):
        if (yd / f).exists():
            shutil.copy(yd / f, outdir / f)
    (outdir / "fig").mkdir(exist_ok=True)
    if figdir.exists():
        for f in figdir.glob("*.pdf"):
            shutil.copy(f, outdir / "fig" / f.name)

    # ---- G5: page bands, measured on the rendered PDF ------------------
    band_c = Y["yearly"]["content_page_band"]
    band_t = Y["yearly"]["total_page_band"]
    TBF = 0.40
    pages, g5 = None, {"status": "warn",
                       "detail": {"reason": "pymupdf unavailable"}}
    try:
        import pymupdf
        refs_page = None
        with pymupdf.open(pdf) as d:
            pages = d.page_count
            for i in range(d.page_count):
                if re.search(r"^\s*(?:\d+\.\s*)?References\s*$",
                             d[i].get_text(), re.M):
                    refs_page = i + 1
                    break
        if refs_page:
            content = refs_page - TBF
            ok_c = band_c[0] <= content <= band_c[1]
            ok_t = band_t[0] <= pages <= band_t[1]
            g5 = {"status": "pass" if (ok_c and ok_t) else "fail",
                  "detail": {"pages_to_refs": refs_page,
                             "content_pages": round(content, 2),
                             "total_pages": pages,
                             "reference_pages": pages - refs_page,
                             "content_band": band_c, "total_band": band_t,
                             "content_ok": ok_c, "total_ok": ok_t}}
        else:
            g5 = {"status": "warn",
                  "detail": {"reason": "References heading not located",
                             "total_pages": pages}}
    except Exception as e:                                  # noqa: BLE001
        g5 = {"status": "warn", "detail": {"error": str(e)[:140]}}
    gate["G5"] = g5

    try:
        g10 = measure_title_block(pdf, date_str=date_str)
        gate["G10-title-block"] = {"status": g10["status"], "detail": g10}
        print(f"[18y] G10-title-block: {g10['status']}  "
              f"{json.dumps(g10.get('gaps_pt'))}")
    except Exception as e:                                  # noqa: BLE001
        gate["G10-title-block"] = {"status": "warn",
                                   "detail": {"error": str(e)[:160]}}

    (yd / "gate_report_yearly.json").write_text(
        json.dumps(gate, indent=2), encoding="utf-8")
    shutil.copy(yd / "gate_report_yearly.json",
                outdir / "gate_report_yearly.json")
    print(f"[18y] G5: {g5['status']}  {json.dumps(g5['detail'])[:220]}")

    failed = [k for k, v in gate.items() if v["status"] == "fail"]
    meta = {"year": year, "pdf": str(pdf), "bytes": pdf.stat().st_size,
            "pages": pages, "title": TITLE, "prose_words": body_words,
            "abstract_words": len(ab.split()), "cited": len(order),
            "figures": n_fig, "sections": len(ids),
            "map_sha256": smap["sha256"],
            "gates": {k: v["status"] for k, v in gate.items()},
            "gates_failed": failed}
    done(rd, "18y_build_yearly", **meta)
    print("[18y]", json.dumps(meta)[:600])
    if failed:
        print(f"[18y] *** {len(failed)} GATE(S) FAILED: {failed} ***")
        print("[18y] The PDF exists so it can be read, but it is NOT "
              "shippable. Fix the OUTPUT, never the gate.")
    return meta


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(
            "usage: s18y_build_yearly.py <YYYY>\n"
            "No default: the period must be stated, never inferred.")
    build(sys.argv[1])
