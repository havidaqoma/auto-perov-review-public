# Perovskite PV — Yearly Review Paper Pipeline

Standalone repository for the **yearly** perovskite photovoltaics review
issue. Operating contract: [`MASTER_HANDBOOK_YEARLY.md`](MASTER_HANDBOOK_YEARLY.md) v2.0.

## Relationship to the monthly project

The monthly pipeline lives at `auto-perov-review` and is **working
and must not be disturbed**. This repo exists so yearly work cannot
destabilise it.

Consequence, and the single most important thing to understand here:

> The monthly project builds a yearly issue by **aggregating twelve monthly
> runs**. This project has no monthly runs and never will, so it **harvests a
> year directly in one sweep** and slices it into months in Python.

That inverts handbook v1.0 §1. v2.0 §1 justifies the inversion with
measurements rather than assertion.

## Status — honest

| Component | State |
|---|---|
| shared modules (hygiene, notation, layout, boilerplate, section_map, common/*) | copied verbatim, import clean |
| `s01_harvest_yearly.py` | written, **not yet run against the live API** |
| `yearly_corpus.py`, `yearly_audit.py` | written, contract-tested on synthetic data |
| `yearly_stats.py`, `yearly_section_map.py` | copied from monthly, rewired, determinism re-proven |
| `tests/test_yearly_backfill.py` | **41 tests, all passing** |
| `s02_06`, `s04_10`, `s09_cards` | copied, **still month-shaped — not yet adapted** |
| yearly **draft** stage | **does not exist** |
| yearly **build** stage | **does not exist** |

**No yearly manuscript has been produced by any repository yet.** Nothing here
has touched a live API beyond small read-only probes.

## Key facts, measured

Run `python scripts/probe_2025.py` in the monthly repo to reproduce:

- **2025 holds 7,931 works** on the production filter (2024: 6,784; 2026: 5,557)
- 2025 abstracts reconstruct at **70% (Jun) / 74% (Dec)** vs a **62%** control
  from the month that actually shipped — so an old year is *not* harder to read
- **2025-01 shows 1,569 works vs ~550 elsewhere.** That is OpenAlex storing an
  imprecise date as January 1, not a January surge. Gated by `date_precision()`

## Cost model

**Harvest costs no tokens.** `s01`, `s02`, `s04` are API calls and JSON
parsing with zero LLM involvement. Tokens are spent only at extraction
(`s09`), and only on the depth-selected pool (`depth_target: 450`).

> A **wider** corpus is nearly free. Only **deeper** reading costs money.

## Sources

OpenAlex is primary and the only source whose failure is fatal. Semantic
Scholar is **best-effort** abstract gap-fill: it is wrapped in `try/except`,
records `s2_status`, and a 429 can never fail a build. See handbook §2.1 for
an S2 probe that was rate-limited and is reported as **inconclusive** rather
than banked as a finding.

**Models never perform retrieval or transcription.** They may write prose and
extract cards. See handbook §2.2 — the abstract is the evidence chain's input,
and a model that reflows it passes every downstream guard while being wrong.

## Run order

```bash
python -m pytest tests/ -q                          # must pass first
Y=2025
python scripts/stages/s01_harvest_yearly.py   $Y    # one sweep, no LLM
python scripts/stages/s02_06.py               $Y    # NOT YET ADAPTED
python scripts/stages/s04_10.py               $Y    # NOT YET ADAPTED
python scripts/stages/s09_cards.py            $Y    # NOT YET ADAPTED — the LLM cost
python scripts/verify_anchors.py              $Y    # MANDATORY, must exit 0
python scripts/stages/yearly_corpus.py        $Y
python scripts/stages/yearly_stats.py         $Y
python scripts/stages/yearly_section_map.py   $Y
# draft + build: not yet written
```

## Non-negotiables

1. **If a gate fails, fix the output — never the gate.** `config/gates.yaml`
   describes the *monthly* artifact and stays untouched; yearly bands are new
   keys in `config/yearly.yaml`, asserted by test.
2. **An annual percentage is not the mean of twelve monthly percentages.**
   Pooled = summed numerator / summed denominator. The naive version is a
   five-fold error in the handbook's worked case.
3. **A zero is a bug until proven otherwise.**
4. **Dedupe by dropping a whole card, never by merging two cards' fields.**
5. **Never silently reassign a date.** Exclude from the series, keep in the
   corpus, report the count.
6. **A backfill issue must disclose that it is one** — assembled
   retrospectively, not by month-by-month monitoring.

## Layout

```
MASTER_HANDBOOK_YEARLY.md     the operating contract (v2.0, backfill mode)
config/         yearly.yaml (new keys) + gates.yaml (monthly, untouched) + tex/
scripts/
  stages/       s01_harvest_yearly, yearly_corpus, yearly_audit, yearly_stats,
                yearly_section_map, + copied monthly stages awaiting adaptation
  common/       net (keyed vs plain HTTP), env, titles, ledger, doi, ...
  verify_*.py   anchors, rendered PDF, notation span geometry
tests/          test_yearly_backfill.py — 41 contract tests, no network
docs/decisions/ recorded decisions and corrections
runs/           harvest output (gitignored)
```
