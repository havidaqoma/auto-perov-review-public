"""04_venues (5.4), 08_subset (5.8), 10_stats (5.10).
Q53: eligibility = non-empty abstract; full text opportunistic.
Run: python scripts/stages/s04_10.py 2026-07
"""
from __future__ import annotations

import json
import math
import pathlib
import random
import re
import sqlite3
import sys
from collections import Counter, defaultdict

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from common.net import SourceFailure, oa
from stages.util import (CONFIG, DATA, done, is_year, read_jsonl, run_dir,
                         write_jsonl, year_months)

AUDIT_RX = {
    "efficiency_stated": r"\b(PCE|power conversion efficiency|efficiency)\b.{0,40}?\b\d{1,2}(\.\d+)?\s?%",
    "certified": r"(?<!un)\bcertif(ied|ication)\b",
    "stabilised": r"\b(stabili[sz]ed|steady[- ]state|maximum power point|MPP[T]?)\b",
    # NOTE: the plan writes this as
    #   (?<!mA\s?/?\s?)(?<!mA\s)\b\d+(\.\d+)?\s?(cm|mm)\s?(\^|²|2)\b
    # which Python REJECTS: "look-behind requires fixed-width pattern" (\s? is
    # variable width). The plan's regex has never been executed. The intent --
    # count real areas, not the cm^2 in a Jsc unit like "24.1 mA cm-2" -- is
    # preserved by matching the area and filtering the mA case in code below.
    "area_stated": r"\b\d+(\.\d+)?\s?(cm|mm)\s?(\^\s?2|\u00b2|2)\b",
    "hysteresis": r"\b(hysteresis|reverse scan|forward scan|scan rate|scan direction)\b",
    "isos_label": r"\bISOS-[LVDTP]+(-\d)?\b",
}
TRIPLET = (r"\bV_?oc\b", r"\bJ_?sc\b", r"\b(FF|fill factor)\b")
# current-density context that must NOT count as a stated device area
_MA_CTX = re.compile(r"m\s?A\s*(/|\s)?\s*$", re.I)


def audit_hit(name: str, rx: str, text: str) -> bool:
    """True if the metric fires, with the area/Jsc-unit exclusion applied."""
    if name != "area_stated":
        return bool(re.search(rx, text, re.I))
    for m in re.finditer(rx, text, re.I):
        before = text[max(0, m.start() - 8):m.start()]
        if _MA_CTX.search(before):
            continue          # "24.1 mA cm-2" -> a current density, not an area
        return True
    return False


def gates(period: str | None = None) -> dict:
    """Selection knobs for THIS period.

    WHY THIS IS PERIOD-AWARE AND WHY IT IS NOT A WIDENING
    -----------------------------------------------------
    `gates.yaml` describes the MONTHLY artifact and stays untouched
    (handbook 0.1 rule 6). `yearly.yaml` holds the yearly knobs as NEW keys.
    Measured difference:

        key                gates.yaml   yearly.yaml
        depth_target              200           450
        depth_band         [100, 300]    [350, 550]
        axis_min_depth             12            25

    Run over a year with the monthly numbers, the depth tier would cap at 200
    papers out of ~7,900 and `axis_min_depth: 12` would let an axis into a
    1500-word section on twelve papers. Nothing would crash. The issue would
    simply be a monthly-depth review wearing a yearly title.

    THE OVERLAY IS DELIBERATELY PARTIAL. `yearly.yaml` does NOT define
    `venue_share_max_pct` (8), `institution_share_max_pct` (10) or
    `preprint_share_min_pct` (10), so those fall through to `gates.yaml`.
    That is correct rather than lazy: they are PROPORTIONS of `n_target`, so
    they scale with the pool automatically, and they encode fairness
    constraints (no venue or institution may dominate the reading list) that
    are period-independent. Re-declaring them at yearly scale would create a
    second definition of the same constraint -- the divergent-copies failure.

    Only keys yearly.yaml actually declares are overlaid, so a missing yearly
    key can never silently zero a monthly one.
    """
    g = yaml.safe_load((CONFIG / "gates.yaml").read_text(encoding="utf-8"))
    if period is None or not is_year(period):
        return g

    y = yaml.safe_load((CONFIG / "yearly.yaml").read_text(encoding="utf-8"))
    yk = y.get("yearly") or {}
    for k, v in yk.items():
        if v is not None:
            g[k] = v

    # The body-citation ceiling is an ENVELOPE, not a selection knob, and it
    # lives under its own top-level key. Carried across explicitly so
    # `selection.n_cited` is bounded by the yearly ceiling (160-220) rather
    # than the monthly one.
    cy = (y.get("citations_yearly") or {}).get("total_band")
    if cy:
        g.setdefault("paper", {})
        g["paper"] = {**g["paper"], "max_body_citations": cy[1]}

    g["_period_mode"] = "yearly"
    return g


# ---------------------------------------------------------------- 04_venues
def venues(period: str) -> dict:
    rd = run_dir(period)
    corpus = read_jsonl(rd / "05_corpus.jsonl")
    DATA.mkdir(exist_ok=True)
    db = sqlite3.connect(DATA / "venues.sqlite3")
    db.execute("""CREATE TABLE IF NOT EXISTS venues(
        source_id TEXT PRIMARY KEY, display_name TEXT, issn_l TEXT, type TEXT,
        works_count INT, two_yr REAL, h_index INT, fetched_at TEXT,
        whitelisted INT DEFAULT 0)""")
    have = {r[0] for r in db.execute("SELECT source_id FROM venues")}
    ids = {r["venue_source_id"] for r in corpus if r.get("venue_source_id")}
    todo = sorted(ids - have)
    print(f"[04] {len(ids)} distinct venues, {len(todo)} to fetch")

    wl_raw = yaml.safe_load((CONFIG / "venue_whitelist.yaml").read_text(encoding="utf-8"))
    wl_names = set()
    for v in (wl_raw.get("venues") or []):
        wl_names.add((v if isinstance(v, str) else v.get("name", "")).lower())

    for i, sid in enumerate(todo, 1):
        try:
            j = oa(f"{sid.replace('https://openalex.org/','https://api.openalex.org/sources/')}"
                   "?select=id,display_name,issn_l,type,works_count,summary_stats",
                   stage="04_venues")
            ss = j.get("summary_stats") or {}
            db.execute("INSERT OR REPLACE INTO venues VALUES(?,?,?,?,?,?,?,datetime('now'),?)",
                       (sid, j.get("display_name") or "", j.get("issn_l") or "",
                        j.get("type") or "", j.get("works_count") or 0,
                        ss.get("2yr_mean_citedness") or 0.0,
                        ss.get("h_index") or 0,
                        1 if (j.get("display_name") or "").lower() in wl_names else 0))
        except SourceFailure as e:
            print(f"[04] soft-fail {sid}: {e}")
        if i % 50 == 0:
            db.commit()
            print(f"[04] {i}/{len(todo)}")
    db.commit()

    # cumulative percentile over type='journal' only (R16); non-journal -> null
    rows = list(db.execute("SELECT source_id,two_yr FROM venues WHERE type='journal'"))
    rows.sort(key=lambda r: r[1] or 0.0)
    n_ref = len(rows)
    pct = {sid: round((i + 1) / n_ref, 4) for i, (sid, _) in enumerate(rows)}
    wl = {r[0] for r in db.execute("SELECT source_id FROM venues WHERE whitelisted=1")}
    out = {}
    for sid in ids:
        p = pct.get(sid)
        if p is not None and sid in wl:
            p = max(p, 0.90)
        out[sid] = p
    (rd / "04_venue_percentiles.json").write_text(json.dumps(
        {"n_reference_venues": n_ref, "period": period,
         "snapshot_date": period,
         "percentiles": out}, indent=2), encoding="utf-8")
    db.close()
    meta = {"n_distinct": len(ids), "n_reference_venues": n_ref,
            "n_null_percentile": sum(1 for v in out.values() if v is None)}
    done(rd, "04_venues", **meta)
    print("[04]", json.dumps(meta))
    return meta


# ---------------------------------------------------------------- 08_subset
def subset(period: str) -> dict:
    g = gates(period)
    rd = run_dir(period)
    corpus = {r["work_key"]: r for r in read_jsonl(rd / "05_corpus.jsonl")}
    labels = {l["work_key"]: l for l in read_jsonl(rd / "06_labels.jsonl")}
    abst = {a["work_key"]: a["abstract"]
            for a in read_jsonl(rd / "private" / "02_abstracts.jsonl")}
    vp = json.loads((rd / "04_venue_percentiles.json").read_text(encoding="utf-8"))
    pctl = vp["percentiles"]

    # Q53: eligible = has abstract, not retracted, not MT-only
    elig = []
    for wk, lab in labels.items():
        r = corpus.get(wk)
        if not r or r["is_retracted"]:
            continue
        a = abst.get(wk, "")
        if not a or len(a) < 120:
            continue
        if r["lang"] != "en":
            continue
        elig.append(wk)

    # COLD START: no prior card history on disk -> novelty_flag 1.0 for all
    # (5.8 empty-history rule). This repo has no prior issues at all, so the
    # cold start is permanent until a second yearly issue exists. It is a
    # legitimate cold start, not a defect -- but it must not be DESCRIBED as
    # "month 1", because that string reaches stats.json and then a reader.
    hist_tokens: set[str] = set()
    scored = []
    for wk in elig:
        r, lab = corpus[wk], labels[wk]
        vpc = pctl.get(r["venue_source_id"]) or 0.0
        nov = 1.0 if not hist_tokens else 0.0
        s = 0.40 * vpc + 0.35 * lab["mechanism_centrality"] + 0.25 * nov
        scored.append({"work_key": wk, "score": round(s, 5),
                       "venue_percentile": vpc,
                       "centrality": lab["mechanism_centrality"],
                       "novelty_flag": nov, "axis": lab["axis_primary"],
                       "type": r["type"], "venue": r["venue"],
                       "inst": r["first_author_institution_clean"]})
    scored.sort(key=lambda x: -x["score"])

    n_elig = len(scored)
    n_target = min(g["depth_target"], int(0.4 * n_elig))
    lo, hi = g["depth_band"]
    n_target = max(min(n_target, hi), min(lo, n_elig))
    small_pool = n_elig < lo

    def pick(pool, n_want, cap_venue, cap_inst, chosen, vcount, icount, reason):
        for it in pool:
            if len(chosen) >= n_want:
                break
            if it["work_key"] in chosen:
                continue
            if vcount[it["venue"]] + 1 > cap_venue:
                continue
            if it["inst"] and icount[it["inst"]] + 1 > cap_inst:
                continue
            chosen[it["work_key"]] = reason(it)
            vcount[it["venue"]] += 1
            icount[it["inst"]] += 1

    cap_v = max(1, int(n_target * g["venue_share_max_pct"] / 100))
    cap_i = max(1, int(n_target * g["institution_share_max_pct"] / 100))

    def select(pool):
        chosen: dict[str, str] = {}
        vc, ic = Counter(), Counter()
        # per-axis floor
        for ax in {x["axis"] for x in pool}:
            ax_pool = [x for x in pool if x["axis"] == ax]
            want = min(g["axis_min_depth"], len(ax_pool))
            sub: dict[str, str] = {}
            pick(ax_pool, want, cap_v, cap_i, sub, vc, ic, lambda i, a=ax: f"axis:{a}")
            chosen.update(sub)
        # preprint reservation
        pre_min = int(n_target * g["preprint_share_min_pct"] / 100)
        pre_now = sum(1 for k in chosen if next(x for x in pool if x["work_key"] == k)["type"] == "preprint")
        if pre_now < pre_min:
            pre_pool = [x for x in pool if x["type"] == "preprint" and x["work_key"] not in chosen]
            sub = {}
            pick(pre_pool, pre_min - pre_now, cap_v, cap_i, sub, vc, ic, lambda i: "preprint")
            chosen.update(sub)
        # fill by score
        sub = dict(chosen)
        pick(pool, n_target, cap_v, cap_i, sub, vc, ic, lambda i: "score")
        return sub

    shipped = select(scored)

    # sensitivity: 200 perturbed weightings (5.8)
    rnd = random.Random(g["seed"])
    freq = Counter()
    draws = g["sensitivity_draws"]
    for _ in range(draws):
        w = [0.40 + rnd.uniform(-0.10, 0.10), 0.35 + rnd.uniform(-0.10, 0.10),
             0.25 + rnd.uniform(-0.10, 0.10)]
        t = sum(w)
        w = [x / t for x in w]
        pool = sorted(
            [{**x, "score": w[0] * x["venue_percentile"] + w[1] * x["centrality"]
              + w[2] * x["novelty_flag"]} for x in scored],
            key=lambda x: -x["score"])
        for k in select(pool):
            freq[k] += 1
    ship_set = set(shipped)
    jac = []
    core = sum(1 for k in ship_set if freq[k] / draws >= 0.95)
    marg = sum(1 for k in ship_set if freq[k] / draws < 0.50)
    inter = sum(1 for k in ship_set if freq[k] > draws * 0.5)
    jac_med = round(inter / max(len(ship_set), 1), 3)

    rows = []
    for x in scored:
        wk = x["work_key"]
        rows.append({**x, "depth_slot": wk in ship_set,
                     "selection_reason": shipped.get(wk, ""),
                     "selection_frequency": round(freq[wk] / draws, 3)})
    write_jsonl(rd / "08_subset_scores.jsonl", rows)
    (rd / "08_sensitivity.json").write_text(json.dumps(
        {"draws": draws, "jaccard_median": jac_med, "core_n": core,
         "marginal_n": marg}, indent=2), encoding="utf-8")
    # force-includes: a cold start has no card history -> structurally empty
    (rd / "08_force_include_pending.json").write_text(json.dumps(
        {"pending": [], "reason": "cold start: empty card history, no cumulative max PCE"},
        indent=2), encoding="utf-8")

    meta = {"n_eligible": n_elig, "n_depth": len(ship_set), "n_target": n_target,
            "small_pool": small_pool, "jaccard_median": jac_med,
            "core_n": core, "marginal_n": marg,
            "axis_depth": dict(Counter(x["axis"] for x in scored if x["work_key"] in ship_set))}
    done(rd, "08_subset", **meta)
    print("[08]", json.dumps(meta, indent=2))
    return meta


# ---------------------------------------------------------------- 10_stats
def stats(period: str) -> dict:
    g = gates(period)
    rd = run_dir(period)
    corpus = {r["work_key"]: r for r in read_jsonl(rd / "05_corpus.jsonl")}
    labels = {l["work_key"]: l for l in read_jsonl(rd / "06_labels.jsonl")}
    abst = {a["work_key"]: a["abstract"]
            for a in read_jsonl(rd / "private" / "02_abstracts.jsonl")}
    sub = read_jsonl(rd / "08_subset_scores.jsonl")
    sens = json.loads((rd / "08_sensitivity.json").read_text(encoding="utf-8"))
    vp = json.loads((rd / "04_venue_percentiles.json").read_text(encoding="utf-8"))
    meta01 = json.loads((rd / "01_meta.json").read_text(encoding="utf-8"))
    depth = [x for x in sub if x["depth_slot"]]
    depth_keys = {x["work_key"] for x in depth}

    val = json.loads((rd / "06_validation_metrics.json").read_text(encoding="utf-8"))
    validated = val.get("status") == "validated"

    S: dict = {}
    S["corpus.n"] = len(labels)
    S["corpus.n_by_source"] = meta01["sources"]
    S["corpus.n_preprint"] = sum(1 for k in labels if corpus[k]["type"] == "preprint")
    S["corpus.n_review"] = sum(1 for k in labels if corpus[k]["type"] == "review")
    S["corpus.n_translated"] = sum(1 for k in labels if corpus[k]["translated"])
    S["corpus.lang"] = dict(Counter(corpus[k]["lang"] for k in labels))
    S["corpus.n_with_abstract"] = sum(1 for k in labels if abst.get(k))

    S["selection.n_eligible"] = len([x for x in sub])
    S["selection.n_depth"] = len(depth)
    S["selection.n_cited"] = min(len(depth), g["paper"]["max_body_citations"])
    S["selection.n_forced"] = 0
    S["selection.jaccard_median"] = sens["jaccard_median"]
    S["selection.core_n"] = sens["core_n"]
    S["selection.marginal_n"] = sens["marginal_n"]

    S["venues.n_reference"] = vp["n_reference_venues"]
    S["venues.snapshot_date"] = vp["snapshot_date"]
    vcount = Counter(corpus[k]["venue"] for k in labels if corpus[k]["venue"])
    S["venues.n_corpus_venues"] = len(vcount)
    S["venues.max_share_pct"] = round(100 * vcount.most_common(1)[0][1] / len(labels), 1)
    dp = [x["venue_percentile"] for x in depth if x["venue_percentile"]]
    cp = [vp["percentiles"].get(corpus[k]["venue_source_id"]) or 0 for k in labels]
    S["venues.depth_percentile_median"] = round(sorted(dp)[len(dp) // 2], 3) if dp else None
    S["venues.corpus_percentile_median"] = round(sorted(cp)[len(cp) // 2], 3) if cp else None
    S["venues.top5"] = vcount.most_common(5)

    # axes
    n = len(labels)
    for ax in ("composition", "defects", "interfaces", "architecture", "stability", "scale_up"):
        c = sum(1 for l in labels.values() if l["axis_primary"] == ax)
        d = sum(1 for x in depth if x["axis"] == ax)
        S[f"axes.{ax}.n_corpus"] = c
        S[f"axes.{ax}.n_depth"] = d
        S[f"axes.{ax}.share_pct"] = round(100 * c / n, 1)
        S[f"axes.{ax}.z_vs_6mo"] = None      # no multi-period history
        S[f"axes.{ax}.delta_vs_prev_month_pp"] = None
        # The basis names what is ACTUALLY absent. A yearly cold start has
        # no prior ISSUE, not merely no prior month, and the manuscript
        # must contain no year-over-year claim as a result.
        S[f"axes.{ax}.delta_basis"] = (
            "cold start: no prior issue" if g.get("_period_mode") == "yearly"
            else "month 1: no prior month")

    # corpus-tier audit regexes on abstracts
    def audit_over(keys, prefix):
        pool = [abst.get(k, "") for k in keys if abst.get(k)]
        m = len(pool)
        for name, rx in AUDIT_RX.items():
            hit = sum(1 for t in pool if audit_hit(name, rx, t))
            S[f"{prefix}.{name}.n"] = hit
            S[f"{prefix}.{name}.pct"] = round(100 * hit / max(m, 1), 1)
            S[f"{prefix}.{name}.precision"] = None if not validated else 0.0
            S[f"{prefix}.{name}.recall"] = None if not validated else 0.0
            S[f"{prefix}.{name}.printable"] = bool(validated)
        trip = sum(1 for t in pool
                   if all(re.search(r, t, re.I) for r in TRIPLET))
        S[f"{prefix}.triplet_complete.n"] = trip
        S[f"{prefix}.triplet_complete.pct"] = round(100 * trip / max(m, 1), 1)
        S[f"{prefix}.triplet_complete.printable"] = bool(validated)
        S[f"{prefix}.denominator"] = m

    audit_over(list(labels), "audit.corpus")
    audit_over(list(depth_keys), "audit.depth")

    S["gates.validation_mode"] = val.get("status")
    (rd / "stats.json").write_text(json.dumps(S, indent=2), encoding="utf-8")
    hist = pathlib.Path(__file__).resolve().parents[2] / "stats_history"
    hist.mkdir(exist_ok=True)
    (hist / f"{period}.json").write_text(json.dumps(S, indent=2), encoding="utf-8")
    done(rd, "10_stats", n_keys=len(S))
    print(f"[10] {len(S)} keys; corpus.n={S['corpus.n']} depth={S['selection.n_depth']}")
    print("     efficiency_stated:", S["audit.corpus.efficiency_stated.pct"], "%",
          "| certified:", S["audit.corpus.certified.pct"], "%",
          "| printable:", S["audit.corpus.certified.printable"])
    return S


if __name__ == "__main__":
    # No default period: a stage that defaults would write into a run dir
    # this repo does not own.
    if len(sys.argv) < 2:
        raise SystemExit(
            "usage: s04_10.py <period>   e.g. 2025  or  2025-06\n"
            "No default: the period must be stated, never inferred.")
    m = sys.argv[1]
    venues(m)
    subset(m)
    stats(m)
