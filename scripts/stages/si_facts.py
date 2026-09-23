"""si_facts: what an SI must say about its manuscript, read from the manuscript.

Why this exists
---------------
An SI describes exactly one built manuscript. Two facts on its front page
were being produced by a second code path instead of read from that
manuscript, and both diverged:

1. The title. s19_si derives it only when ver == "v4"; any other version falls
   through to the v3 literal "Buried-Interface Chemistry, Defect Tolerance and
   the Certified Efficiency Frontier". The 2026-H1 edition builds as "v6", so
   its SI named July's issue while its manuscript said "The Certified Frontier
   From Cell to Module". All gates passed, because no gate compared the two.

2. The "Cited in the main text" row. s19_si counts plain [12] markers, but the
   build has emitted [\\href{https://doi.org/...}{12}] since v4, so the row
   read 0 beside a body carrying 184 distinct linked citations. The yearly SI
   had already been fixed for this (s19y_si_yearly.measured_citations); the
   monthly counter had not.

s19_si is a MONTHLY stage and the monthly workflow is deliberately not
modified from period layers, so this module is additive: period adapters call
it to correct the SI that s19 wrote, and tests call it to compare any shipped
SI with its manuscript. Every correction fails closed if the line it replaces
is not found exactly once, so a future change to s19's layout cannot make the
correction silently stop applying.
"""
from __future__ import annotations

import re

TITLE_RE = re.compile(r"\{\\LARGE\\bfseries (.+?)\\par\}", re.S)
DATE_RE = re.compile(
    r"^((?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December) \d{1,2}, \d{4})[ \t]*$", re.M)

_SI_FOR_RE = re.compile(r'^For "(.+?)"[ \t]*$', re.M)
_SI_BYLINE_RE = re.compile(r"^(Havid Aqoma, )(.+?)[ \t]*$", re.M)
_SI_RECORDS_RE = re.compile(
    r"^\| Extraction records surviving all guards \| (\d+) \|[ \t]*$", re.M)
_SI_CITED_RE = re.compile(r"^\| Cited in the main text \| (\d+) \|[ \t]*$", re.M)
_SI_AUDITED_RE = re.compile(
    r"^\| Audited but not cited individually \| (\d+) \|[ \t]*$", re.M)


def manuscript_title(mtext: str) -> str | None:
    """The title exactly as the built manuscript's title block prints it."""
    m = TITLE_RE.search(mtext)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else None


def manuscript_date(mtext: str) -> str | None:
    """The date line of the title block (before the first section heading)."""
    cut = mtext.find("\n## ")
    head = mtext[:cut] if cut > 0 else mtext[:4000]
    m = DATE_RE.search(head)
    return m.group(1) if m else None


def measured_citations(mtext: str) -> tuple[int, int]:
    """(n_refs, n_distinct_refs_cited_in_body), both marker forms counted.

    Same rule as s19y_si_yearly.measured_citations: linked markers first, then
    any plain [n] a DOI-less work degraded to. The nomenclature guard applies
    to both: "[60]fullerene" and "[100] growth" are not citations, and a
    bracketed number above the reference count cannot be one.
    """
    if "## References" not in mtext:
        return 0, 0
    head = mtext.index("## References")
    body, reflist = mtext[:head], mtext[head:]
    n_refs = len(re.findall(r"^\d+\. ", reflist, flags=re.M))
    cited: set[int] = set()
    for m in re.finditer(r"href\{https://doi\.org/[^}]*\}\{(\d+)\}", body):
        n = int(m.group(1))
        if 0 < n <= n_refs:
            cited.add(n)
    for m in re.finditer(r"\[(\d+(?:,\d+)*)\](?![A-Za-z])", body):
        grp = [int(x) for x in m.group(1).split(",")]
        if any(x > n_refs or x == 0 for x in grp):
            continue
        cited.update(grp)
    return n_refs, len(cited)


def si_title(si_text: str) -> str | None:
    m = _SI_FOR_RE.search(si_text)
    return m.group(1).strip() if m else None


def draw_funnel(path, labels: list[str], counts: list[int]) -> None:
    """Figure S1 (file S2_corpus_funnel.pdf), drawn from Table S2's own numbers.

    The figure stages used to draw it from stats.json, whose
    selection.n_cited is a pre-drafting CAP (min(depth, max_body_citations)),
    not what the body cites. July's bar read 180 for a manuscript citing 79,
    and the H1 bar read 209 (a stale gate report) against 184. The SI draws it
    from the same list that fills Table S2, so figure and table cannot differ.
    Styling is the figure stages' (serif 8.5 pt, #4C72B0 bars).
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    if len(labels) != len(counts) or not counts:
        raise SystemExit("FAIL-CLOSED si_facts.draw_funnel: labels/counts")
    rc = {"font.size": 8.5, "axes.spines.top": False,
          "axes.spines.right": False, "figure.dpi": 220,
          "font.family": "serif"}
    with plt.rc_context(rc):
        fig, ax = plt.subplots(figsize=(6.2, 0.45 * len(counts) + 0.6))
        ax.barh(range(len(counts)), counts, 0.58, color="#4C72B0",
                edgecolor="k", linewidth=0.4)
        for i, c_ in enumerate(counts):
            ax.text(c_ + max(counts) * 0.015, i, f"{c_:,}", va="center",
                    fontsize=7.5)
        ax.set_yticks(range(len(counts)))
        ax.set_yticklabels(labels, fontsize=7.5)
        ax.invert_yaxis()
        ax.set_xlim(0, max(counts) * 1.18)
        ax.set_xlabel("Works")
        fig.tight_layout()
        fig.savefig(str(path))
        plt.close(fig)


def funnel_pdf_counts(pdf_path) -> list[int]:
    """The bar value labels printed in a rendered funnel figure, top to bottom.

    Every numeric word on the page is either an x-axis tick (all on the
    lowest baseline) or a bar's value label (one per bar row, above it).
    """
    import pymupdf
    with pymupdf.open(str(pdf_path)) as doc:
        words = doc[0].get_text("words")
    nums = [(w[1], int(w[4].replace(",", ""))) for w in words
            if re.fullmatch(r"\d[\d,]*", w[4])]
    if not nums:
        return []
    tick_y = max(y for y, _ in nums)
    return [v for y, v in sorted(nums) if abs(y - tick_y) > 1.0]


def si_cited(si_text: str) -> int | None:
    m = _SI_CITED_RE.search(si_text)
    return int(m.group(1)) if m else None


def _replace_once(rx: re.Pattern, text: str, repl, what: str) -> str:
    hits = rx.findall(text)
    if len(hits) != 1:
        raise SystemExit(
            f"FAIL-CLOSED si_facts: expected exactly one {what} line in the "
            f"SI, found {len(hits)}. s19's layout changed; update si_facts "
            f"rather than letting the correction silently stop applying.")
    return rx.sub(repl, text, count=1)


def correct_si_cited(si_text: str, mtext: str) -> tuple[str, dict]:
    """Rewrite ONLY the two citation rows of Table S2 from the manuscript.

    For repairing shipped editions: title, date and prose stay byte-identical,
    so the repair changes exactly the numbers that were wrong. Fails closed on
    a zero count, on a cited set larger than the audited set, and on any row
    not found exactly once.
    """
    n_refs, n_cited = measured_citations(mtext)
    if n_refs and not n_cited:
        raise SystemExit(
            f"FAIL-CLOSED si_facts: the manuscript lists {n_refs} references "
            f"but 0 were found cited in its body; the counter cannot see this "
            f"build's marker form.")
    rec = _SI_RECORDS_RE.findall(si_text)
    if len(rec) != 1:
        raise SystemExit("FAIL-CLOSED si_facts: expected one 'Extraction "
                         f"records surviving all guards' row, found {len(rec)}.")
    n_records = int(rec[0])
    if n_cited > n_records:
        raise SystemExit(
            f"FAIL-CLOSED si_facts: {n_cited} works cited in the body but only "
            f"{n_records} extraction records; the cited set is not a subset "
            f"of the audited set.")
    out = _replace_once(_SI_CITED_RE, si_text,
                        lambda m: f"| Cited in the main text | {n_cited} |",
                        "'Cited in the main text'")
    out = _replace_once(
        _SI_AUDITED_RE, out,
        lambda m: f"| Audited but not cited individually | "
                  f"{n_records - n_cited} |",
        "'Audited but not cited individually'")
    return out, {"n_refs": n_refs, "n_cited": n_cited, "n_records": n_records}


def correct_si_front(si_text: str, mtext: str) -> tuple[str, dict]:
    """Rewrite the SI's title, date and citation rows from the manuscript.

    Returns (corrected_text, facts). Fails closed when the manuscript lacks a
    title block or when the citation counter finds nothing to count.
    """
    title = manuscript_title(mtext)
    if not title:
        raise SystemExit("FAIL-CLOSED si_facts: the manuscript has no "
                         "\\LARGE\\bfseries title block; the SI cannot name "
                         "the paper it supports.")
    date = manuscript_date(mtext)
    if not date:
        raise SystemExit("FAIL-CLOSED si_facts: no date line in the "
                         "manuscript title block.")
    out, counts = correct_si_cited(si_text, mtext)
    out = _replace_once(_SI_FOR_RE, out,
                        lambda m: f'For "{title}"', "For \"<title>\"")
    out = _replace_once(_SI_BYLINE_RE, out,
                        lambda m: f"{m.group(1)}{date}", "byline/date")
    return out, {"title": title, "date": date, **counts}


def _norm(s: str) -> str:
    for a, b in (("\ufb01", "fi"), ("\ufb02", "fl"), ("\ufb00", "ff"),
                 ("\ufb03", "ffi"), ("\ufb04", "ffl"), ("\u201c", '"'),
                 ("\u201d", '"'), ("\u2019", "'"), ("\u2013", "-"),
                 ("\u2011", "-")):
        s = s.replace(a, b)
    return re.sub(r"\s+", "", s).lower()


def pdf_front_has_title(pdf_path, title: str, pages: int = 2) -> bool:
    """True when the rendered PDF's first pages carry the title text.

    Checks the RENDERED artifact, not the markdown (handbook H1 10.1: verify
    the rendered artifact, not the gate report). Whitespace and ligatures are
    normalised because PDF text extraction splits and fuses them.
    """
    import pymupdf
    with pymupdf.open(str(pdf_path)) as doc:
        text = "".join(doc[i].get_text() for i in range(min(pages, len(doc))))
    return _norm(title) in _norm(text)
