# v5: readable empirical register

This directory is a revision of the shipped `..._v4` edition. Only the prose
register changed. No number, citation, unit or figure was touched.

## What changed

The v4 text piled up clauses. Measured against five Nature-family empirical
papers, with the reference list excluded from the count:

| Document | mean words/sentence | share over 35 words | aphorism rate |
|---|---|---|---|
| July main, v4 | 29.2 | 26.9% | 10.8% |
| July main, v5 | 21.8 | 8.5% | 13.1% |
| July SI, v4 | 22.8 | 11.1% | 18.5% |
| July SI, v5 | 25.0 | 13.5% | 8.1% |
| August main, v4 | 31.9 | 36.3% | 7.1% |
| August main, v5 | 23.5 | 13.1% | 12.4% |
| August SI, v4 | 23.0 | 10.9% | 18.2% |
| August SI, v5 | 24.4 | 11.5% | 11.5% |

Exemplar means are 23.9 words, 13.7% over 35 words, 14.7% aphorisms. Target
bands are 20 to 27, 8 to 18, and under 18. All eight figures above now sit
inside their band; in v4, five sat outside.

The main-text fix was splitting result-stacked sentences so each claim keeps
its own number and its own citation. The SI fix was narrower: bare
propositions were merged onto the evidence already sitting beside them, and
sentence length was left alone.

## What was verified, and how

Numbers, citations, citation numbers, `{{TOKEN}}` placeholders and `\qty`
units were frozen before the rewrite and compared afterwards as MULTISETS,
against the v4 originals rather than against a self-report:

- `scripts/drift_audit.py` : 0 defects, both editions
- `scripts/check_content_contract.py` : CONTRACT HELD, both editions
- `scripts/_meaning_review.py` : 0 problems

That last one exists because the token ledger cannot see a softened bound.
It compares assertion verbs (demonstrates, reveals, shows) against hedging
verbs (suggests, indicates) and counts calibration words. Both editions came
back identical on every count: July main 22 assertions before and after,
August main 18 before and after, calibration vocabulary 41 to 41 in both.
Headings, figure blocks, table lines and the entire reference list are
byte-identical to v4.

Rendered PDFs were re-made from the revised markdown with the same pandoc and
tectonic invocation the build uses, and checked:

- `verify_notation_pdf.py` : July main 48 correct, 0 flat; August main 52
  correct, 0 flat. Both SIs carry no notation tokens.
- Page counts: July 15pp main (unchanged), 7pp SI (was 6). August 14pp main
  (unchanged), 6pp SI (was 5). The SIs each gained a page because merged
  sentences reflow.

## What was NOT done, and why it matters

**There is no `gate_report_v5.json`.** The copy from v4 produced one by
rename, and it was DELETED rather than kept. It would have asserted that 16
build gates passed on v5 prose when those gates never ran on v5 prose: the
gate report is an output of `s18d_build_v4.py`, which rebuilds an edition from
the draft caches and the section map, and that would discard this hand-revised
markdown. A stale report claiming a passing run is worse than no report.

So `scripts/verify_pdf.py <month> v5` cannot run: it reads the reference count
and the expected page count out of that gate report. The checks it performs
that do not depend on gates (stale month names, unresolved placeholders, agent
narration, doubled figure captions, citation monotonicity) remain unverified
for v5.

**The chemrxiv submission package was not copied into v5.** `chemrxiv/` and
`chemrxiv_<month>.tar.gz` are v4 submission artifacts. A v5 package must be
built from the v5 PDFs if this revision is ever submitted.

**Figure paths are absolute.** Both manuscripts embed
`runs/<run>/fig/*.pdf`. The v5 PDFs render only
because the v4 run directories still exist on this machine. All 8 paths
resolve today; none are relative.
