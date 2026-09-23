"""domain_lint: refuse a domain registry that would ship a defect.

Run this BEFORE the first harvest of a new domain. Every assertion here
encodes a defect the perovskite pipeline actually shipped, generalised to any
topic. A domain that passes this linter cannot reproduce those defects; a
domain that fails it would have, silently.

Usage
-----
    python scripts/stages/domain_lint.py config/domains/perovskite_pv.yaml
    python scripts/stages/domain_lint.py --all

Exit code is non-zero on any error, so this belongs in the porting checklist
as a gate rather than a suggestion.
"""
from __future__ import annotations

import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DOMAINS = ROOT / "config" / "domains"

VALID_ROLES = {"frontier", "penalty_x", "durability", "secondary",
               "scope", "quality", "significance"}

# Venue-prestige proxies. These are REFUSED as metrics in every domain, and
# the refusal is not stylistic -- see GENERAL 3.4 for the full argument.
#
# Short version: a metric must trace to a verbatim quotation from the cited
# paper's own abstract (monthly 3). A journal impact factor is external
# metadata. It has no anchor, cannot pass guards 1-3, and cannot be checked
# by G3. Admitting one would put a number in front of a reader that the
# evidence chain cannot see -- which is 0.4 violated in exactly the way v3
# violated it, only sourced from a database instead of an f-string.
#
# It is also a journal-level quantity used as an article-level judgement,
# which is the DORA/Leiden objection, and it is the Type-D category error
# wearing a different hat: it restores a scalar ranking through the side
# door after 3.2 removed it on purpose.
VENUE_PRESTIGE_KEYS = {
    "journal_if", "impact_factor", "if", "jif", "journal_impact_factor",
    "sjr", "snip", "citescore", "h_index", "h5_index", "eigenfactor",
    "journal_rank", "venue_rank", "venue_prestige", "quartile",
    "jcr_quartile", "altmetric", "cite_score",
}
VALID_DIRECTIONS = {"higher_better", "lower_better", "none"}
VALID_TYPES = {"P", "D"}

# Banned in every domain regardless of topic. A domain may ADD to this list
# but never remove from it.
UNIVERSAL_BANNED = {
    "comprehensive", "novel", "unprecedented", "breakthrough", "cutting-edge",
    "state-of-the-art", "enhanced", "improved", "superior", "remarkable",
    "pivotal", "delve", "unlock", "showcase", "realm", "update",
}


def lint(path: pathlib.Path) -> list[str]:
    """Return a list of errors. Empty list means the domain is usable."""
    err: list[str] = []
    try:
        D = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as e:                                  # noqa: BLE001
        return [f"{path.name}: unparseable YAML: {e}"]

    def e(msg: str) -> None:
        err.append(f"{path.name}: {msg}")

    dom = D.get("domain") or {}
    ttype = dom.get("topic_type")

    # ---- identity -------------------------------------------------------
    for k in ("name", "slug", "topic_type", "scope_note"):
        if not dom.get(k):
            e(f"domain.{k} is empty; a domain without it cannot be cited "
              f"in its own methods section")
    if ttype not in VALID_TYPES:
        e(f"domain.topic_type must be one of {sorted(VALID_TYPES)}, got "
          f"{ttype!r}")
    if dom.get("slug") and dom["slug"] != path.stem:
        e(f"domain.slug {dom['slug']!r} != filename stem {path.stem!r}; the "
          f"slug names run dirs and deliverables, so a mismatch splits one "
          f"domain's artifacts across two names")

    # ---- harvest --------------------------------------------------------
    h = D.get("harvest") or {}
    if not h.get("query_terms"):
        e("harvest.query_terms is empty")
    band = h.get("count_band")
    if not (isinstance(band, list) and len(band) == 2 and band[0] < band[1]):
        e("harvest.count_band must be [lo, hi] with lo < hi; it is the "
          "pre-pagination assertion that catches a silent zero (handbook 7.1)")
    # OpenAlex returns count 0 for a query containing an exclusion, rather
    # than a filtered set (handbook 9.1). This is unrecoverable at runtime
    # because zero looks like a legitimately empty month.
    for grp in (h.get("query_terms") or []):
        for term in (grp if isinstance(grp, list) else [grp]):
            s = str(term)
            if s.strip().startswith("-"):
                e(f"harvest.query_terms contains an exclusion {s!r}. A "
                  f"'-term' in an OpenAlex query returns count 0, not a "
                  f"filtered set. Exclude in Python via exclude.*")
            if "*" in s:
                e(f"harvest.query_terms contains a wildcard {s!r}; "
                  f"wildcards are rejected on title_and_abstract.search. "
                  f"Spell out the variants")

    # ---- axes -----------------------------------------------------------
    axes = D.get("axes") or {}
    if len(axes) < 4:
        e(f"only {len(axes)} axes; below 4 the section map cannot fill its "
          f"MIN_MECH band and every issue looks the same")
    for name, ax in axes.items():
        if not (ax or {}).get("keywords"):
            e(f"axis {name!r} has no keywords, so it can never score")
        fi = (ax or {}).get("fold_into")
        if fi and fi not in axes:
            e(f"axis {name!r} folds into {fi!r}, which is not an axis. An "
              f"axis that misses the section cut must fold somewhere real "
              f"or its papers vanish from the issue")

    # ---- metrics: the centrepiece ---------------------------------------
    metrics = D.get("metrics") or []
    if not metrics:
        e("metrics is empty; the extraction schema is generated from it")
    keys = set()
    roles: dict[str, list[str]] = {}
    for m in metrics:
        k = m.get("key")
        if not k:
            e("a metric has no key")
            continue
        if k in keys:
            e(f"duplicate metric key {k!r}")
        keys.add(k)

        # Venue prestige is refused as a METRIC in every domain, Type-P and
        # Type-D alike. See GENERAL 3.4. A journal impact factor has no
        # anchor in the cited paper's abstract, so it cannot pass guards
        # 1-3 and G3 cannot trace it; it is a journal-level quantity used
        # as an article-level judgement (DORA); and in a Type-D domain it
        # restores the scalar ranking that 3.2 removed on purpose.
        norm = str(k).lower().replace("-", "_").replace(" ", "_")
        if norm in VENUE_PRESTIGE_KEYS or norm.endswith("_impact_factor"):
            e(f"metric {k!r} is a VENUE-PRESTIGE PROXY and is refused as a "
              f"metric in every domain. It has no anchor in the cited "
              f"paper's abstract, so it cannot pass the evidence guards and "
              f"G3 cannot trace it; it judges an article by its journal "
              f"(DORA); and in a Type-D domain it reinstates the scalar "
              f"ranking that the significance section exists to replace. "
              f"Venue quality may inform SELECTION (s04_10's citation "
              f"percentile) and may be audited in the SI, but it may never "
              f"be a reported metric")
        src = str(m.get("source") or "").lower()
        if src and (src in VENUE_PRESTIGE_KEYS
                    or any(t in src for t in ("impact_factor", "journal_if",
                                              "venue_rank", "quartile"))):
            e(f"metric {k}: source {m.get('source')!r} is venue metadata, "
              f"not a claim from the paper's own abstract")

        if not m.get("label"):
            e(f"metric {k}: no label, so prose and figures cannot name it")
        if "unit" not in m:
            e(f"metric {k}: unit missing. Declare \"\" for dimensionless "
              f"rather than omitting it, or the schema-and-unit contract "
              f"cannot be checked")
        if m.get("direction") not in VALID_DIRECTIONS:
            e(f"metric {k}: direction must be one of "
              f"{sorted(VALID_DIRECTIONS)}, got {m.get('direction')!r}")
        role = m.get("role")
        if role not in VALID_ROLES:
            e(f"metric {k}: role must be one of {sorted(VALID_ROLES)}, got "
              f"{role!r}")
        else:
            roles.setdefault(role, []).append(k)

        # Plausibility is NOT optional. Handbook 7.8's corollary: add a
        # plausibility gate wherever physics bounds a quantity, because
        # traceability proves provenance, not meaning. The worst defect the
        # PV pipeline shipped was a REAL number on the wrong device, and the
        # only gate that could see it was a physical bound.
        p = m.get("plausibility") or {}
        if not isinstance(p, dict) or "min" not in p or "max" not in p:
            e(f"metric {k}: plausibility {{min, max}} is REQUIRED. A metric "
              f"without a physical bound cannot be gated, and a value above "
              f"its limit is self-refuting to an expert reader (handbook "
              f"7.8)")
        elif p["min"] >= p["max"]:
            e(f"metric {k}: plausibility min >= max")
        # A ratio-like unit with a max above 100 is nearly always a mistake.
        if str(m.get("unit")) == "%" and isinstance(p.get("max"), (int, float)):
            if p["max"] > 100.0:
                e(f"metric {k}: unit is % but plausibility.max is "
                  f"{p['max']}; a percentage above 100 is impossible unless "
                  f"this is a relative change, in which case say so in the "
                  f"label")

        if "device_binding" not in m:
            e(f"metric {k}: device_binding must be declared true or false. "
              f"When true the label MUST come from the value's own anchor, "
              f"never from the paper -- one abstract can report two devices "
              f"and lend the wrong one its record (handbook 7.8)")
        if m.get("requires_condition") and not m.get("device_binding"):
            e(f"metric {k}: requires_condition is set but device_binding is "
              f"false; a value that needs a stated condition is bound by "
              f"definition")

    # ---- topic-type coherence: the Type-D trap --------------------------
    spine = D.get("section_spine") or {}
    lead = spine.get("lead_role")
    if ttype == "P":
        if "frontier" not in roles:
            e("topic_type P declares no metric with role 'frontier'. A "
              "performance domain needs one scalar figure of merit, or it "
              "is really a Type-D domain")
        if lead != "frontier":
            e(f"topic_type P must use section_spine.lead_role 'frontier', "
              f"got {lead!r}")
    elif ttype == "D":
        # This is the single most valuable assertion in the file. Yield, ee
        # and dr are numbers, so a Type-D domain configured carelessly will
        # declare one of them a frontier and the pipeline will happily build
        # a champion curve over chemistry that no chemist ranks that way.
        # Every gate would pass.
        if "frontier" in roles:
            e(f"topic_type D must NOT declare a 'frontier' metric "
              f"({roles['frontier']}). Discovery chemistry has no scalar "
              f"figure of merit: a 41% yield forming a quaternary "
              f"stereocentre beats 95% on a trivial coupling. Use roles "
              f"'scope' and 'quality' and let the significance section "
              f"argue")
        if lead != "significance":
            e(f"topic_type D must use section_spine.lead_role "
              f"'significance', got {lead!r}")
        if not (D.get("advance_taxonomy") or {}).get("values"):
            e("topic_type D requires advance_taxonomy.values: a Type-D "
              "paper's contribution is classified, not scored")
        # A metric with direction higher_better and role quality is fine
        # (ee genuinely is better higher). A YIELD declared higher_better
        # is the category error in miniature.
        for m in metrics:
            if str(m.get("key", "")).startswith("yield") and \
                    m.get("direction") != "none":
                e(f"metric {m['key']}: direction must be 'none' in a Type-D "
                  f"domain. Yield does not order papers; a lower yield on a "
                  f"harder transformation is the better result")

    if ttype == "P":
        for want in ("penalty_x", "durability"):
            if want not in roles:
                e(f"topic_type P declares no {want!r} metric. The monthly "
                  f"argument is 'the frontier is thin, it does not survive "
                  f"scale, and it does not survive operation'; without "
                  f"{want} the issue cannot make it")

    # ---- lens -----------------------------------------------------------
    lens = D.get("lens") or {}
    lv = set(lens.get("values") or [])
    if not lv:
        e("lens.values is empty")
    ml = set(lens.get("measured_lenses") or [])
    ex = set(lens.get("exclude_from_measured_figures") or [])
    if not ml:
        e("lens.measured_lenses is empty; no figure could plot anything")
    for s, nm in ((ml, "measured_lenses"), (ex, "exclude_from_measured_figures")):
        bad = s - lv
        if bad:
            e(f"lens.{nm} names non-declared lenses {sorted(bad)}")
    if ml & ex:
        e(f"lens: {sorted(ml & ex)} is both measured and excluded from "
          f"measured figures")
    if not ex:
        e("lens.exclude_from_measured_figures is empty. A simulation or "
          "review value standing beside measured hardware is a defect a "
          "human had to catch once already (handbook 5.1)")

    # ---- figures --------------------------------------------------------
    figs = D.get("figure_roles") or []
    if not figs:
        e("figure_roles is empty")
    fids, attach_seen = set(), []
    for f in figs:
        fid = f.get("id")
        if not fid:
            e("a figure role has no id")
            continue
        if fid in fids:
            e(f"duplicate figure id {fid!r}")
        fids.add(fid)
        if not f.get("argument"):
            e(f"figure {fid}: no argument. A figure earns main-text space "
              f"by carrying an argument the prose cannot make in a sentence")
        for mk in ("y_metric", "x_metric", "compare_metric", "colour_metric"):
            mv = f.get(mk)
            if mv and mv not in keys:
                e(f"figure {fid}: {mk}={mv!r} is not a declared metric")
        # G9c: one figure file attaches to at most one section. The August
        # v4 PDF showed the same plate as Figure 2 AND Figure 3 because the
        # claim was keyed on section id rather than filename.
        tgt = f.get("attach_role") or f.get("attach_axis")
        if not tgt:
            e(f"figure {fid}: neither attach_role nor attach_axis; a figure "
              f"attached by section NUMBER breaks when the map changes")
        attach_seen.append((fid, str(tgt)))
        for ax in ([f["attach_axis"]] if isinstance(f.get("attach_axis"), str)
                   else (f.get("attach_axis") or [])):
            if ax not in axes:
                e(f"figure {fid}: attach_axis {ax!r} is not a declared axis")

    # ---- abstract tokens ------------------------------------------------
    toks = D.get("abstract_tokens") or []
    if not toks:
        e("abstract_tokens is empty; the abstract is digit-free and needs "
          "tokens to substitute (handbook 3.3)")
    seen_t = set()
    for t in toks:
        tk = t.get("token")
        if not tk:
            e("an abstract token has no token name")
            continue
        if tk in seen_t:
            e(f"duplicate abstract token {tk!r}")
        seen_t.add(tk)
        if not t.get("source"):
            e(f"abstract token {tk}: no source. An unresolvable token FAILS "
              f"THE BUILD -- a hole never ships")
        src = str(t.get("source", ""))
        # A cards: source naming an undeclared metric can never resolve.
        for part in src.split(":"):
            if part in ("stats", "cards", "count", "max", "min", "at",
                        "count_class", ""):
                continue
        if src.startswith("cards:"):
            bits = src.split(":")
            named = [b for b in bits[2:3]]
            for b in named:
                if b and b not in keys and not b.startswith(("class", "count")):
                    if b not in {v for v in (D.get("advance_taxonomy") or {}).get("values", [])}:
                        e(f"abstract token {tk}: source names {b!r}, which "
                          f"is not a declared metric or advance class")

    # ---- title ----------------------------------------------------------
    tt = D.get("title_terms") or {}
    if not tt.get("frame"):
        e("title_terms.frame is empty")
    banned = {str(b).lower() for b in (tt.get("banned") or [])}
    missing = UNIVERSAL_BANNED - banned
    if missing:
        e(f"title_terms.banned omits universal entries {sorted(missing)}. A "
          f"domain may add to the banned list, never remove from it")
    ap = tt.get("axis_phrases") or {}
    for ax in axes:
        if not ap.get(ax):
            e(f"title_terms.axis_phrases has no entry for axis {ax!r}, so a "
              f"month led by it cannot build a title")

    # ---- spine ----------------------------------------------------------
    sw = spine.get("spine_words") or {}
    sc = spine.get("spine_cites") or {}
    for k in ("intro", "lead", "gaps"):
        if k not in sw:
            e(f"section_spine.spine_words missing {k!r}")
        if k not in sc:
            e(f"section_spine.spine_cites missing {k!r}")
    if not spine.get("lead_title_template"):
        e("section_spine.lead_title_template is empty")
    elif "{month}" not in spine["lead_title_template"] and \
            "{year}" not in spine["lead_title_template"]:
        # The month hardcoded in five sites shipped a "July 2026" caption
        # into an August PDF (handbook 7.6 #2).
        e("section_spine.lead_title_template contains neither {month} nor "
          "{year}; a hardcoded period ships a stale month into a later issue")

    return err


def main(argv: list[str]) -> int:
    if "--all" in argv:
        paths = sorted(DOMAINS.glob("*.yaml"))
        if not paths:
            print(f"no domain files in {DOMAINS}")
            return 1
    else:
        args = [a for a in argv[1:] if not a.startswith("--")]
        if not args:
            print(__doc__)
            return 2
        paths = [pathlib.Path(a) for a in args]

    total = 0
    for p in paths:
        if not p.exists():
            print(f"MISSING {p}")
            total += 1
            continue
        errs = lint(p)
        if errs:
            total += len(errs)
            print(f"\nFAIL {p.name}  ({len(errs)} error"
                  f"{'s' if len(errs) != 1 else ''})")
            for x in errs:
                print(f"  - {x}")
        else:
            D = yaml.safe_load(p.read_text(encoding="utf-8"))
            d = D["domain"]
            print(f"PASS {p.name:<32} type={d['topic_type']} "
                  f"axes={len(D.get('axes') or {})} "
                  f"metrics={len(D.get('metrics') or [])} "
                  f"figures={len(D.get('figure_roles') or [])} "
                  f"tokens={len(D.get('abstract_tokens') or [])}")
    if total:
        print(f"\n{total} error(s). A domain that fails this linter would "
              f"have shipped a defect the pipeline has already paid for.")
        return 1
    print("\nall domains pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
