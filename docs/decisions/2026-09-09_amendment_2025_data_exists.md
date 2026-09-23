# AMENDMENT to 2026-09-09: the "no 2025 data" claim was wrong, and §1.3 was misapplied

**Date:** 2026-09-09 (same session, after operator challenge)
**Amends:** `2026-09-09_overnight_blocked.md`
**Trigger:** Havid: *"it dont make sense that no perovskite PV was published
in 2025. can you deeply check and investigate? did you use openalex and
Semantic, etc, to search the paper already?"*

He was right on both counts. This file records the correction, because a
misapplied handbook argument sitting in `docs/decisions/` becomes citable
precedent, and monthly §0.2 says a defect becomes a gate, not a reminder.

---

## 1. What I said vs what is true

The original log said **"no 2025 data exists"**. That sentence conflated two
claims that are not the same:

| Claim | Truth |
|---|---|
| (a) "no 2025 perovskite PV literature was published" | **FALSE, and absurd** |
| (b) "no 2025 monthly *harvest* exists in `runs/`" | **true, verified** |

Only (b) was ever measured. The wording implied (a). That is my error, and it
is the §7.3 verifier-bug shape applied to prose: a true measurement described
in words that assert something much bigger.

### Did I search OpenAlex / Semantic Scholar for 2025?

**No — and the original log never said I had.** That is the honest answer to
the direct question. What I checked was `runs/`, the local harvest state. I
never queried any scholarly API for 2025 before declaring it blocked.

The pipeline *is* wired to four sources (`scripts/stages/s01_harvest.py`):

| Source | Mode |
|---|---|
| OpenAlex | keyed, **primary/authoritative** |
| arXiv | plain, soft-fail |
| Crossref | plain, soft-fail |
| Semantic Scholar | plain, **anonymous, soft-fails to OpenAlex** |

So "did you use OpenAlex and Semantic Scholar" resolves to: the code queries
both, S2 contributes little by design (anonymous, soft-fail), and **neither
was ever run for 2025.**

---

## 2. The measurement, using the production filter

`scripts/probe_2025.py`. It **imports** `FILTER` from `s01_harvest.py` rather
than retyping a query, because a hand-written query returns a number that
does not mean what the pipeline's number means.

```
production filter: title_and_abstract.search:perovskite AND ("solar cell" OR photovoltaic)

=== YEAR TOTALS ===
  2024:   6,784 works
  2025:   7,931 works
  2026:   5,557 works

=== 2025 BY MONTH ===
  2025-01: 1,569     2025-05:   607     2025-09:   550
  2025-02:   478     2025-06:   567     2025-10:   621
  2025-03:   544     2025-07:   576     2025-11:   600
  2025-04:   614     2025-08:   555     2025-12:   650
```

**7,931 works in 2025.** Every month carries 478-1,569 — comfortably inside
`gates.yaml`'s `count_band`. There is no thin month and no empty month.

2025 is also the **largest** of the three years measured, which makes the
original sentence not merely imprecise but backwards.

*(Note: 2025-01's 1,569 is an outlier. That is the well-known OpenAlex
January-lumping artefact — works with imprecise dates default to Jan 1. It
must be handled at harvest, not treated as a real January surge.)*

---

## 3. The measurement that refutes my own argument

The original log leaned on YEARLY §1.3: *a fourteen-month-old month retrieves
worse (2.5%) than a two-month-old one (5.0%), so re-harvesting loses it.* I
used that to argue 2025 could not be back-filled.

**Two things are wrong with that.**

### 3a. §1.3 is about re-harvesting, not first-time harvesting

§1.3 and §1.2 exist to stop you **re-extracting a month you already have**,
because re-extraction perturbs cards a shipped issue already cited. For a
year with **zero** prior harvest, the comparison is not "recover vs lose" —
it is "harvest now vs never have it at all." §1.3 does not, on its own,
forbid a first-time 2025 run. I applied a preservation rule as an
availability rule.

### 3b. §1.3 measures FULL TEXT. This pipeline is abstract-first.

GENERAL §6.1 is explicit: full-text retrieval succeeds ~5% of the time,
abstract coverage is ~68%, and **abstract-first is the correct design, not a
compromise**. Guard 1 anchors every claim verbatim in the *abstract*. So the
load-bearing question is whether 2025 abstracts still reconstruct.

Measured, 50-work samples, against the shipped August 2026 issue as control:

| Period | Usable abstract | Median words |
|---|---|---|
| 2025-01 | 26/50 = **52.0%** | 188 |
| 2025-06 | 35/50 = **70.0%** | 188 |
| 2025-12 | 37/50 = **74.0%** | 187 |
| **2026-08 (control, shipped)** | 31/50 = **62.0%** | 176 |

**2025-06 (70%) and 2025-12 (74%) reconstruct BETTER than the month that
actually shipped (62%).** Median abstract length is identical, ~187 words.

§1.3's degradation does not bind the abstract path. My blocker's stated
reason was wrong. **2025 is a cost-and-design question, not a
data-availability one.**

---

## 4. The blocker that is actually real, and larger

While re-checking, a more serious gap surfaced:

```
$ grep -rln "yearly" scripts/stages/*.py scripts/*.py
scripts/stages/yearly_aggregate.py
scripts/stages/yearly_section_map.py
scripts/stages/yearly_stats.py
scripts/stages/yearly_tokens.py
scripts/yearly_preflight.py
```

**There is no yearly draft stage and no yearly build stage.** YEARLY §2 and
§12 both describe a "[LLM] draft" and a "build" step "which take `<year>` as
argv". Those stages do not exist. Confirmed further:

- only the four `yearly_*` analysis modules accept a 4-digit year
- `config/yearly.yaml` has exactly **one** consumer: `yearly_section_map.py`.
  Nothing reads `citations_yearly`, `abstract_yearly`, `novelty_yearly` or
  `plausibility` — i.e. **G2c-yearly, G3b-yearly, G5-yearly, G8-yearly and
  G3c per-class bounds are configured but unimplemented**
- `s13d`/`s18d` default `sys.argv[1]` to `"2026-08"`, a **month** format

So the pipeline can aggregate, compute stats and generate a section map for a
year — and then stops. **No yearly issue can currently be built for any year,
2025 or 2026.**

This is consistent with the handbook's own admission that "nothing in this
handbook has produced a shipped yearly issue yet", but the handbook's status
table reads "live, verified on 3 real months", which is true of the
*intermediate artifacts* and could be read as end-to-end. It is not
end-to-end. G11-coverage is likewise specified but has no implementation
beyond the preflight I added.

> **This outranks the data question. Do not spend ~12 h harvesting and
> extracting twelve months into a pipeline whose last two stages do not
> exist.**

---

## 5. Corrected cost picture for a 2025 issue

A 2025 issue is a **retrospective backfill**, a mode the yearly handbook never
designed for. Consequences:

- YEARLY §1.1's ~1.2 h aggregation figure **does not apply.** That figure
  assumes twelve monthly runs already exist. Nothing is being reused, so the
  honest estimate is the naive end-to-end one: **~12 h** (12 × 35 min
  extraction + 12 × 25 min drafting), plus the yearly draft on top.
- §1.4's "one OpenAlex delta for late-indexed works" is **meaningless** here.
  Everything is late-indexed.
- §4.5's YoY cold start is **guaranteed**: there is no 2024 issue either. The
  abstract must contain no year-over-year claim. Note 2024 *counts* are now
  known (6,784), which is exactly the temptation §4.5 warns about — a count
  is not a prior-year stats file, and there is no YoY token to substitute.
- §1.5's `cross_month_duplicates` assertion gets its **first real test**: a
  zero across twelve months is a bug until proven otherwise.
- The 2025-01 January-lumping artefact must be handled before it becomes a
  fabricated January surge in the trajectory section.

---

## 6. Options for 2025, restated honestly

| # | Option | Assessment |
|---|---|---|
| A | Full 12-month 2025 backfill, then yearly build | **Legitimate.** ~12 h + draft. Requires the yearly draft/build stages to be written first. Abstract and methods must state it was assembled retrospectively, not by monthly monitoring. |
| B | A correctly-titled 2025 **retrospective review**, not posing as a monthly aggregation | Honest and cheaper. Different artifact from a "yearly issue". |
| C | Build the yearly path properly and target **2026** | Needs 2026-09..12, so a Jan-2027 artifact. |
| D | 2025 issue from a subset of months under a yearly title | **REFUSED.** This is exactly the internally-consistent, all-gates-green misstatement §1.4 and G11 exist to catch. `--partial` stays unused. |

Sequencing recommendation, unchanged in shape but for corrected reasons:
**write the yearly draft + build stages first** (they block every option
except B), then choose A or C. My earlier recommendation of "wait for 2026"
was reached partly through the misapplied §1.3 argument; option A is more
viable than I said, because the abstracts are there.

---

## 7. Two hygiene findings, reported not fixed

- **`runs/307ba569460d/` is an empty, orphaned run directory.** No month
  prefix, so no `.active` pointer can ever resolve it — the §7.1 bug-1
  relocated-run shape. Empty on inspection. Not deleted.
- **Two harvest scripts exist**: `scripts/01_harvest.py` and
  `scripts/stages/s01_harvest.py`, both hitting OpenAlex. This is the
  three-divergent-copies failure mode of monthly §6.4 arriving again — the
  one that let a narration leak through the narrowest copy. Needs
  consolidation or an explicit archive to `OLD/`.

---

## 8. Lesson for the handbook

Two rules earned, both instances of things the handbooks already say:

1. **State the measurement, not its implication.** "No 2025 harvest exists in
   `runs/`" is checkable and true. "No 2025 data exists" is neither. A
   blocker's stated reason is prose reaching a reader (§0.4) and traces to
   evidence like any other claim.
2. **A preservation rule is not an availability rule.** §1.3 forbids
   re-harvesting a month you already hold. It says nothing about a year you
   never harvested, and its numbers are full-text numbers in an
   abstract-first pipeline. Before citing a handbook rule as a blocker,
   check that the quantity it measures is the quantity in question.

Candidate gate: `yearly_preflight.py` should print abstract-availability per
missing month, so a "blocked" verdict always ships with the feasibility
number beside it rather than an inference.
