"""v2 statistics: the H1 number set cut by DEVICE FAMILY.

Additive, never destructive. `h1_stats.py` (v1) is untouched and still emits the
mechanism-axis view; this module ADDS `family.*` keys to the same stats.json so
both structures are available and v1 artifacts stay reproducible.

Every number here is computed from anchor-verified cards. Nothing is typed in.

The measured mass imbalance, and why it is not hidden
----------------------------------------------------
    sj 705 | hyb 78 | ap 59 | mod 30      (872 cards, folded to four buckets)

Single junction is 81% of the corpus. Proportional word allocation, which is
what the v1 mechanism map does, would hand single junction ~5800 of 7200 body
words and modules ~250. That is arithmetically faithful and editorially wrong:
a device family earns a section because it poses a distinct device-physics
question, not because many groups publish on it.

So v2 clamps (see h1_section_map_v2.MECH_MIN/MAX_WORDS) and records the raw
mass here so a reader can see what was damped and by how much.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from stages.util import RUNS, read_jsonl                       # noqa: E402
from stages.device_family import (FAMILIES, LABEL, family,      # noqa: E402
                                  family_or_fold)
from stages.illumination import comparable_to_one_sun           # noqa: E402
from stages.protocol import canon_protocol, is_isos             # noqa: E402

EDITION = "2026-H1"
MONTHS = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]
MONTH_LAB = {"2026-01": "Jan", "2026-02": "Feb", "2026-03": "Mar",
             "2026-04": "Apr", "2026-05": "May", "2026-06": "Jun"}

# Audit fields, per family. Same detection the corpus audit uses, but the
# denominator is the family's own card count -- a rate over 705 single-junction
# papers and a rate over 30 module papers are different measurements.
AUDIT_FIELDS = ["pce_champion", "pce_certified", "active_area_cm2"]


def _v(card: dict, key: str):
    src = card.get("stability") if key in ("t80_h", "duration_h") else card.get("performance")
    f = (src or {}).get(key)
    return f["value"] if isinstance(f, dict) and f.get("value") is not None else None


def _anchor(card: dict, key: str) -> str:
    src = card.get("stability") if key in ("t80_h", "duration_h") else card.get("performance")
    f = (src or {}).get(key)
    return (f.get("anchor") or "") if isinstance(f, dict) else ""


# _FAM_WORDS: what text in a NUMBER's own anchor proves it belongs to
# another family. Deliberately narrow: only unambiguous device names.
_FAM_WORDS = {
    "hyb": re.compile(r"perovskite\s*[/\u2013\u2014-]\s*si\b|/si\b|silicon|\bshj\b|"
                      r"\bcigs\b|cu\s*\(\s*in|\bcdte\b|kesterite|\bczts\b|"
                      r"perovskite\s*[/\u2013\u2014-]\s*organic|\bopv\b", re.I),
    "ap": re.compile(r"all[- ]perovskite|perovskite\s*[/\u2013\u2014-]\s*perovskite|"
                     r"\baptscs?\b", re.I),
    "mod": re.compile(r"\bmodules?\b|submodules?", re.I),
}


def anchor_contradicts_family(card: dict, field: str, fam: str) -> bool:
    """True when a value's own anchor names a family OTHER than `fam`.

    The card carries ONE family label; an abstract can report several devices.
    So a value may belong to different hardware than its card. Measured on the
    H1 cards, and it is the same paper as handbook 7.8:

        card family = mod   (its area anchor says 57.6 cm2, a real module)
        certified anchor    = "a certified 32.95% perovskite/Si tandem efficiency"

    Reporting 32.95% as the MODULE certified frontier would assert a 32.95%
    perovskite module, which does not exist. Both statements in that abstract
    are true; they are about two different devices.

    Fail toward excluding (handbook 7.8 fix #2): dropping one eligible value
    costs a superlative, admitting a wrong one fabricates a record.
    """
    anch = _anchor(card, field)
    if not anch:
        return False
    for other, rx in _FAM_WORDS.items():
        if other == fam:
            continue
        if rx.search(anch):
            # `mod` is a size, not a junction count, so a tandem-cell anchor
            # inside a module paper is a contradiction, but a module anchor
            # inside a tandem paper is only a contradiction for the cell
            # families -- a module CAN be a tandem.
            if fam in ("sj", "ap", "hyb") and other == "mod":
                return True
            if fam == "mod" and other in ("hyb", "ap"):
                return True
            if fam in ("ap", "hyb") and other in ("ap", "hyb"):
                return True
            if fam == "sj" and other in ("ap", "hyb"):
                return True
    return False


def measured(card: dict) -> bool:
    """Simulation and review papers never enter a measured-performance number.

    Handbook 5.1: a drift-diffusion study reporting ~30.8% sat beside certified
    hardware on the efficiency frontier until a human noticed.
    """
    return card.get("lens") not in ("theory", "review")


def champion_of(cards: list, fam: str, field: str = "pce_certified") -> dict | None:
    """The single best card in a family for one field, with its full provenance.

    Returns the record the manuscript may cite: value, its verbatim anchor, the
    work_key, venue and month. Resolving ONE card explicitly is the fix for
    handbook 7.2 -- positional indexing into a filtered, sorted list is banned,
    because that is exactly how three fabricated numbers shipped.

    GUARD: the value's own anchor must not name a DIFFERENT family.
    ----------------------------------------------------------------
    A card carries one family label but an abstract can report several devices,
    so the label and the number can belong to different hardware. Measured
    here, and it is the same paper that caused handbook 7.8:

        family=mod  area anchor "...57.6 cm2..."      -> legitimately a module
        certified anchor: "a certified 32.95% perovskite/Si tandem efficiency"

    32.95% is a tandem CELL record. Reported as the module frontier it would
    have claimed a 32.95% perovskite module, which does not exist. The area
    anchor and the certified anchor describe two different devices in one
    abstract, and both are true statements.

    So a value is admitted to a family's frontier ONLY if its own anchor does
    not name another family. Fail toward excluding: dropping one eligible value
    costs a superlative, while admitting a wrong one is a fabricated record.
    """
    best = None
    for c in cards:
        if family_or_fold(c) != fam or not measured(c):
            continue
        v = _v(c, field)
        if not isinstance(v, (int, float)):
            continue
        if anchor_contradicts_family(c, field, fam):
            continue
        if best is None or v > best["value"]:
            best = {
                "value": v,
                "anchor": _anchor(c, field),
                "work_key": c.get("work_key"),
                "venue": c.get("venue"),
                "month": c.get("source_month"),
                "architecture": (c.get("device") or {}).get("architecture"),
                "area_cm2": _v(c, "active_area_cm2"),
                "t80_h": _v(c, "t80_h"),
                "title": c.get("title"),
            }
    return best


def family_block(cards: list, fam: str) -> dict:
    """Everything the manuscript may say about one device family."""
    fc = [c for c in cards if family_or_fold(c) == fam]
    meas = [c for c in fc if measured(c)]

    # EVERY family number passes anchor_contradicts_family, not just the
    # champion record.
    #
    # The guard was first applied only in champion_of(), and this function kept
    # computing top_certified with a plain max(). Result: family.mod.champion
    # correctly excluded the 32.95% perovskite/Si tandem value, while
    # family.mod.top_certified still reported 32.95% as the MODULE frontier --
    # two code paths for one quantity, one guarded. That is handbook 7.6 #12
    # (a guard applied in only one consumer) reproduced inside a single file.
    def _vals(field, pool):
        out = []
        for c in pool:
            v = _v(c, field)
            if not isinstance(v, (int, float)):
                continue
            if anchor_contradicts_family(c, field, fam):
                continue
            # ILLUMINATION. An indoor PCE is not comparable to a one-sun PCE.
            #
            # Havid read Table 1 and flagged a >30% single junction, expecting a
            # tandem or a simulation. It was neither: the 44.36% is a real,
            # experimental, single-junction measurement at 1000 lx LED
            # ("PCE(i) of 44.36% ... 127.94 uW cm-2"), and the module 41.6% is
            # TL84 at 900 lux. Both numbers are CORRECT and neither belongs in
            # a column of one-sun records.
            #
            # No previous guard could see this: measured() asks about lens,
            # anchor_contradicts_family() asks about the device, G3c bounds only
            # CERTIFIED values, and pce_champion had no plausibility check at
            # all. Illumination is a third axis (see stages/illumination.py).
            if not comparable_to_one_sun(_anchor(c, field)):
                continue
            out.append(v)
        return out

    cert = _vals("pce_certified", meas)
    champ = _vals("pce_champion", meas)
    areas = _vals("active_area_cm2", meas)
    t80 = [_v(c, "t80_h") for c in fc if isinstance(_v(c, "t80_h"), (int, float))]
    protos = [canon_protocol((c.get("stability") or {}).get("protocol") or "")
              for c in fc if (c.get("stability") or {}).get("protocol")]
    n_isos = sum(1 for p in protos if is_isos(p))

    n = len(fc)
    pct = (lambda k: round(100.0 * k / n, 1) if n else None)
    return {
        "n_cards": n,
        "n_measured": len(meas),
        "n_excluded_theory_review": n - len(meas),
        "n_certified": len(cert),
        "pct_certified": pct(len(cert)),
        "top_certified": max(cert) if cert else None,
        "median_certified": (sorted(cert)[len(cert) // 2] if cert else None),
        "n_champion": len(champ),
        "pct_champion": pct(len(champ)),
        "top_champion": max(champ) if champ else None,
        "n_area": len(areas),
        "pct_area": pct(len(areas)),
        "max_area_cm2": max(areas) if areas else None,
        "n_t80": len(t80),
        "pct_t80": pct(len(t80)),
        "max_t80_h": max(t80) if t80 else None,
        "n_protocol": len(protos),
        "n_isos_specified": n_isos,
        "pct_isos": pct(n_isos),
    }


def family_month_matrix(cards: list) -> dict:
    """family x month card counts: did attention shift between families?"""
    out = {f: {m: 0 for m in MONTHS} for f in FAMILIES}
    for c in cards:
        f, m = family_or_fold(c), c.get("source_month")
        if f in out and m in out[f]:
            out[f][m] += 1
    return out


def family_frontier_series(cards: list) -> dict:
    """Best certified value per family per month -- the v2 trajectory figure."""
    out = {}
    for f in FAMILIES:
        ser = []
        for m in MONTHS:
            vals = [_v(c, "pce_certified") for c in cards
                    if family_or_fold(c) == f and c.get("source_month") == m
                    and measured(c)
                    and isinstance(_v(c, "pce_certified"), (int, float))]
            ser.append(max(vals) if vals else None)
        out[f] = ser
    return out


AREA_BINS = [(0, 0.1, "< 0.1"), (0.1, 1, "0.1 - 1"), (1, 10, "1 - 10"),
             (10, 100, "10 - 100"), (100, 1e9, "> 100")]


def area_ladder(cards: list) -> list:
    """Efficiency against aperture area, binned. The cell-to-module gap, as a table.

    ILLUMINATION guard applies here too. This is a SEPARATE code path from
    family_block(), so adding comparable_to_one_sun() there left this table
    still printing 41.6% in the 1-10 cm2 band -- the indoor TL84 mini-module.
    Third instance of the same lesson in this file: a quantity computed by two
    paths needs the guard on both (handbook 7.6 #12).
    """
    rows = []
    for lo, hi, lab in AREA_BINS:
        sel = []
        for c in cards:
            if not measured(c):
                continue
            a = _v(c, "active_area_cm2")
            if not isinstance(a, (int, float)) or not (lo <= a < hi):
                continue
            p = _v(c, "pce_certified")
            q = _v(c, "pce_champion")
            # Drop the value, not the row: a card may report a valid area with
            # an indoor efficiency, and the area itself is still real.
            if isinstance(p, (int, float)) and not comparable_to_one_sun(
                    _anchor(c, "pce_certified")):
                p = None
            if isinstance(q, (int, float)) and not comparable_to_one_sun(
                    _anchor(c, "pce_champion")):
                q = None
            sel.append((a, p if isinstance(p, (int, float)) else None,
                        q if isinstance(q, (int, float)) else None))
        if not sel:
            rows.append({"band_cm2": lab, "n": 0, "best_certified": None,
                         "best_champion": None, "median_champion": None})
            continue
        certs = [p for _, p, _ in sel if p is not None]
        chs = [q for _, _, q in sel if q is not None]
        rows.append({
            "band_cm2": lab,
            "n": len(sel),
            "best_certified": max(certs) if certs else None,
            "best_champion": max(chs) if chs else None,
            "median_champion": (sorted(chs)[len(chs) // 2] if chs else None),
        })
    return rows


def indoor_block(cards: list) -> dict:
    """Indoor / low-light photovoltaics, reported SEPARATELY.

    These values are excluded from every one-sun frontier number by
    comparable_to_one_sun(), which is correct: an indoor PCE and a one-sun PCE
    are different measurements and must never share a column.

    But exclusion is not the same as erasure. Indoor photovoltaics is a real
    and growing subfield, the corpus carries several such papers, and silently
    dropping them would misrepresent the literature in the opposite direction
    from the original defect. So they are counted, reported with their
    illumination conditions, and carried into the SI.

    `ambiguous` anchors (one quotation reporting BOTH an indoor and a one-sun
    value) are counted separately again: their bound value could be either, so
    they are neither a valid one-sun record nor a valid indoor record.
    """
    from stages.illumination import classify, indoor_markers

    rows, ambig = [], []
    for c in cards:
        for field in ("pce_certified", "pce_champion"):
            v = _v(c, field)
            if not isinstance(v, (int, float)):
                continue
            anch = _anchor(c, field)
            kind = classify(anch)
            if kind == "one_sun":
                continue
            rec = {
                "value": v,
                "field": field,
                "family": family_or_fold(c),
                "lens": c.get("lens"),
                "work_key": c.get("work_key"),
                "venue": c.get("venue"),
                "month": c.get("source_month"),
                "title": c.get("title"),
                "anchor": anch,
                "markers": indoor_markers(anch),
            }
            (rows if kind == "indoor" else ambig).append(rec)

    rows.sort(key=lambda r: -r["value"])
    ambig.sort(key=lambda r: -r["value"])
    by_fam: dict[str, int] = {}
    for r in rows:
        by_fam[r["family"]] = by_fam.get(r["family"], 0) + 1
    return {
        "n_values": len(rows),
        "n_papers": len({r["work_key"] for r in rows}),
        "by_family": by_fam,
        "top": rows[0] if rows else None,
        "values": rows,
        "n_ambiguous": len(ambig),
        "ambiguous": ambig,
    }


def build(cards: list) -> dict:
    S: dict = {}
    honest = {}
    for c in cards:
        k = family(c)
        honest[k] = honest.get(k, 0) + 1
    S["family.raw_counts_honest"] = honest
    S["family.unspecified_tandem_n"] = honest.get("tandem_unspecified", 0)

    for f in FAMILIES:
        blk = family_block(cards, f)
        S[f"family.{f}.label"] = LABEL[f]
        for k, v in blk.items():
            S[f"family.{f}.{k}"] = v
        ch = champion_of(cards, f, "pce_certified")
        if ch:
            S[f"family.{f}.champion"] = ch

    S["family.month_matrix"] = family_month_matrix(cards)
    S["family.frontier_series"] = family_frontier_series(cards)
    S["family.area_ladder"] = area_ladder(cards)

    # Indoor / low-light PV, reported separately rather than erased.
    ind = indoor_block(cards)
    S["indoor.n_values"] = ind["n_values"]
    S["indoor.n_papers"] = ind["n_papers"]
    S["indoor.by_family"] = ind["by_family"]
    S["indoor.top"] = ind["top"]
    S["indoor.values"] = ind["values"]
    S["indoor.n_ambiguous"] = ind["n_ambiguous"]
    S["indoor.ambiguous"] = ind["ambiguous"]
    return S


def main() -> int:
    d = RUNS / EDITION
    cards = read_jsonl(d / "claim_cards.jsonl")
    S = json.loads((d / "stats.json").read_text(encoding="utf-8"))
    add = build(cards)
    S.update(add)
    S["n_keys"] = len(S)
    (d / "stats.json").write_text(json.dumps(S, indent=2), encoding="utf-8")
    (d / "stats_family.json").write_text(json.dumps(add, indent=2), encoding="utf-8")

    print(f"[h1v2-stats] +{len(add)} family keys, {S['n_keys']} total")
    print(f"[h1v2-stats] honest counts: {add['family.raw_counts_honest']}")
    for f in FAMILIES:
        print(f"   {f:4} n={add[f'family.{f}.n_cards']:4} "
              f"cert={add[f'family.{f}.n_certified']:3} "
              f"top={add[f'family.{f}.top_certified']} "
              f"area_max={add[f'family.{f}.max_area_cm2']} "
              f"t80_max={add[f'family.{f}.max_t80_h']}")
    # 7.1: a zero is a bug until proven otherwise.
    for f in FAMILIES:
        if not add[f"family.{f}.n_cards"]:
            print(f"FAIL: family {f} has zero cards")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
