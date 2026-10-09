"""G3e: every number in the body prose must trace to verified evidence.

The abstract has always been held to a no-digit contract (G3-abstract), but the
body sections were drafted from claim cards whose values the model typed into
prose, and no gate read those numerals back. A review found the gap; this gate
closes it with the same rule the extraction stage applies to the cards: a
number is admitted only if separate code can find it in text that was itself
verified against the source.

For each sentence of each body section:

  1. Numerals are read the way a reader reads them: digit grouping is removed
     ("1,000" is 1000) and siunitx arguments (\\qty{625}{...}) count.
  2. Exempt: integers 0 to 10 (counts and ordinals, also caught by the
     abbreviation and notation gates), four-digit years 1900 to 2100, and
     numerals glued to letters (2T, AM1.5G, ISOS-L-1, SnO2), which are names.
  3. A numeral is BOUND when it equals a number inside a verified field value,
     field anchor or claim anchor of a paper cited in the SAME sentence.
  4. Otherwise it is an AGGREGATE when it equals a value the build computed
     (stats.json, the substituted abstract values, card and citation counts).
  5. Otherwise, in a sentence that cites nothing, it is MONTH-BOUND when it
     equals a verified number of any card in the issue.
  6. Anything else fails: MISBOUND if the number belongs to a paper the
     sentence does not cite, UNTRACED if it belongs to no verified text at all.

Pure function; no file I/O, so the build, the regate script and the tests run
the same code.
"""
from __future__ import annotations

import re

NUM_RE = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?![\w])")
HREF_RE = re.compile(r"\\href\{https://doi\.org/([^}]*)\}\{[^}]*\}")
CITE_GROUP_RE = re.compile(r"\[(?:\\href\{[^}]*\}\{[^}]*\},?)+\]")
DOI_RE = re.compile(r"\b10\.\d{4,9}/\S+")
FIG_RE = re.compile(r"\\begin\{figure\}.*?\\end\{figure\}", re.S)
TABLE_LINE_RE = re.compile(r"^\s*\|.*\|\s*$", re.M)
SENT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\\])")
# The definition of T80 carries a fixed 80 that is a convention, not a datum.
T80_DEF_RE = re.compile(r"time to 80\s*(?:\\?%|percent) of (?:the )?initial (?:efficiency|PCE|"
                        r"power conversion efficiency)|80\s*\\?% (?:of )?initial efficiency \(T80\)",
                        re.I)


# Thresholds the drafting prompt itself fixes ("a sub-0.1 cm2 cell"): a
# convention the pipeline supplies, not a datum about any paper.
CONVENTION_RE = re.compile(r"sub-\s*0\.1\b|(?:air mass|AM)\s*1\.5\s*G?\b", re.I)
# A small integer followed by one of these is a COUNT claim about the month
# ("5 papers named a protocol"), so it must trace to a computed count.
COUNT_LEAD_RE = re.compile(r"\b(?:only|merely|just)\s+$", re.I)
COUNT_NOUN_RE = re.compile(r"\s*(?:of\s+(?:the\s+)?\d|(?:closely\s+read\s+|examined\s+)?"
                           r"(?:papers|works|studies|reports|articles)\b)")


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def numbers_in(text: str) -> set[float]:
    """Every number a reader would see in a verified span."""
    t = (text or "").replace("\u2009", "").replace("\u202f", "")
    t = re.sub(r"(?<=\d) (?=\d{3}\b)", "", t)  # "1 000 h" is 1000
    out = set()
    for m in NUM_RE.finditer(t):
        try:
            out.add(round(_num(m.group(1)), 6))
        except ValueError:
            pass
    return out


def card_numbers(card: dict) -> set[float]:
    """Numbers in the verified parts of one card: field values, field anchors,
    claim anchors. Claim TEXT is model-written and is deliberately excluded."""
    out: set[float] = set()
    for grp in ("performance", "stability"):
        for f in (card.get(grp) or {}).values():
            if not isinstance(f, dict):
                continue
            v = f.get("value")
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out.add(round(float(v), 6))
            out |= numbers_in(f.get("anchor") or "")
    for cl in card.get("claims") or []:
        out |= numbers_in(cl.get("anchor") or "")
    return out


def _exempt(raw: str, x: float, after: str = "") -> bool:
    if "." not in raw and "," not in raw:
        if 0 <= x <= 10:
            return not COUNT_NOUN_RE.match(after)
        if 1900 <= x <= 2100:
            return True
    return False


def _plain(sentence: str) -> str:
    """Strip markup that carries digits but is not prose."""
    s = HREF_RE.sub(" ", sentence)
    s = DOI_RE.sub(" ", s)
    s = re.sub(r"\\(?:qty|SI|num)\{([^}]*)\}\{[^}]*\}", r" \1 ", s)  # keep the quantity
    s = re.sub(r"\\ce\{([^}]*)\}", " CHEM ", s)    # formulae are names
    s = re.sub(r"\$[^$]*\$", " ", s)               # math (units, sub/superscripts)
    s = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?", " ", s)
    s = CONVENTION_RE.sub(" CONVENTION ", s)
    return s


def card_aggregates(cards: list, S: dict) -> set:
    """The counts and extremes the drafting prompt hands the model as
    'quantitative ground truth', recomputed here from the same cards so the
    gate admits them without trusting the prompt log."""
    def v(c, k):
        for grp in ("performance", "stability"):
            f = (c.get(grp) or {}).get(k)
            if isinstance(f, dict) and isinstance(f.get("value"), (int, float)):
                return float(f["value"])
        return None
    cert = [x for x in (v(c, "pce_certified") for c in cards) if x]
    t80 = [x for x in (v(c, "t80_h") for c in cards) if x]
    area = [x for x in (v(c, "active_area_cm2") for c in cards) if x]
    from stages.protocol import n_isos_specified
    n_isos = n_isos_specified(cards)
    out = {len(cards), len(cert), len(t80), len(area), n_isos}
    out |= {max(cert)} if cert else set()
    out |= {max(t80), float(int(max(t80)))} if t80 else set()
    out |= {max(area)} if area else set()
    for k in ("axes.scale_up.n_corpus", "corpus.n", "selection.n_depth"):
        if isinstance(S.get(k), (int, float)):
            out.add(float(S[k]))
    return out


# Keywords whose paper counts the drafting prompt states. A sentence that
# makes a count claim about one of them must contain the computed count.
COUNT_KEYS = {"ISOS": re.compile(r"\bISOS\b"), "T80": re.compile(r"\bT80\b")}


def expected_counts(cards: list) -> dict:
    from stages.protocol import n_isos_specified
    t80 = 0
    for c in cards:
        f = (c.get("stability") or {}).get("t80_h")
        if isinstance(f, dict) and isinstance(f.get("value"), (int, float)) and f["value"]:
            t80 += 1
    return {"ISOS": n_isos_specified(cards), "T80": t80}


def _count_claims(plain: str) -> dict:
    """Map each count keyword to the count numerals that refer to it.

    A count numeral ("only 5", "6 papers", "4 of 169") is bound to the first
    count keyword that follows it in the sentence, so "only 4 ... T80, and
    only 6 ... ISOS" checks 4 against T80 and 6 against ISOS."""
    out: dict = {}
    for m in NUM_RE.finditer(plain):
        raw = m.group(1)
        if "." in raw:
            continue
        before, after = plain[max(0, m.start() - 12):m.start()], plain[m.end():m.end() + 30]
        if not (COUNT_NOUN_RE.match(after) or COUNT_LEAD_RE.search(before)):
            continue
        # The keyword must sit in the SAME clause: "only 63 of them reported a
        # certified value, with ... T80" counts certified papers, not T80 ones.
        stop = re.search(r"[,;:]", plain[m.end():])
        end = m.end() + stop.start() if stop else len(plain)
        nxt = None
        for key, rx in COUNT_KEYS.items():
            k = rx.search(plain, m.end(), end)
            if k and (nxt is None or k.start() < nxt[1]):
                nxt = (key, k.start())
        if nxt:
            out.setdefault(nxt[0], set()).add(int(_num(raw)))
    return out


def check_body_numbers(secs: dict, cards: list, aggregates: set,
                       abstracts: dict | None = None) -> dict:
    """Return a gate dict {status, detail} for the body sections.

    `abstracts` maps a lower-case DOI to the stored source abstract. A numeral
    absent from every verified span but present in the abstract of a paper
    the sentence cites is admitted as IN_CITED_ABSTRACT: code still confirms
    the number is in the cited source, but not which span it came from, so
    the tier is counted and reported separately rather than merged.
    """
    abstracts = {k.lower(): v for k, v in (abstracts or {}).items()}
    abs_nums = {k: numbers_in(v) for k, v in abstracts.items()}
    by_doi = {}
    month_nums: set[float] = set()
    for c in cards:
        nums = card_numbers(c)
        month_nums |= nums
        d = (c.get("doi") or c.get("work_key") or "").lower()
        if d:
            by_doi[d] = nums
    agg = set()
    for a in aggregates:
        a = float(a)
        agg.add(round(a, 6))
        if 0 < a < 1:            # shares stored as fractions, printed as percent
            agg |= {round(100 * a, 1), round(100 * a, 2), round(100 * a, 0)}
    counts = {"bound": 0, "in_cited_abstract": 0, "para_bound": 0,
              "para_in_cited_abstract": 0, "aggregate": 0, "month_bound": 0,
              "exempt": 0, "count_claims_checked": 0}
    want = expected_counts(cards)
    bad = []
    for sid in sorted(secs, key=lambda k: (len(str(k)), str(k))):
        text = FIG_RE.sub(" ", secs[sid])
        text = TABLE_LINE_RE.sub(" ", text)
        text = T80_DEF_RE.sub(" T80 ", text)
        for para in re.split(r"\n\s*\n", text):
            # A sentence with no citation of its own inherits its paragraph's:
            # the drafts cite once in a paragraph's lead sentence. Such numbers
            # are counted as para_bound, apart from sentence-level binding.
            para_cited = [d.lower() for d in HREF_RE.findall(para)]
            for sent in SENT_RE.split(para.strip()):
                cited = [d.lower() for d in HREF_RE.findall(sent)]
                inherited = not cited and bool(para_cited)
                if inherited:
                    cited = para_cited
                cited_nums: set[float] = set()
                cited_abs: set[float] = set()
                for d in cited:
                    cited_nums |= by_doi.get(d, set())
                    cited_abs |= abs_nums.get(d, set())
                plain = _plain(sent)
                for key, cn in _count_claims(plain).items():
                    counts["count_claims_checked"] += 1
                    if want[key] not in cn:
                        bad.append({"section": sid, "numeral": sorted(cn),
                                    "kind": "count_mismatch",
                                    "expected": {key: want[key]}, "cited": cited[:4],
                                    "sentence": re.sub(r"\s+", " ", plain).strip()[:220]})
                for m in NUM_RE.finditer(plain):
                    raw = m.group(1)
                    x = round(_num(raw), 6)
                    if _exempt(raw, x, plain[m.end():m.end() + 30]):
                        counts["exempt"] += 1
                    elif x in cited_nums:
                        counts["para_bound" if inherited else "bound"] += 1
                    elif x in cited_abs:
                        counts["para_in_cited_abstract" if inherited
                               else "in_cited_abstract"] += 1
                    elif x in agg:
                        counts["aggregate"] += 1
                    elif not cited and x in month_nums:
                        counts["month_bound"] += 1
                    else:
                        kind = "misbound" if x in month_nums else "untraced"
                        bad.append({"section": sid, "numeral": raw, "kind": kind,
                                    "cited": cited[:4],
                                    "sentence": re.sub(r"\s+", " ", plain).strip()[:220]})
    return {"status": "pass" if not bad else "fail",
            "detail": {**counts, "n_failed": len(bad),
                       "untraced": sum(b["kind"] == "untraced" for b in bad),
                       "misbound": sum(b["kind"] == "misbound" for b in bad),
                       "count_mismatch": sum(b["kind"] == "count_mismatch" for b in bad),
                       "expected_counts": want,
                       "failures": bad[:40]}}
