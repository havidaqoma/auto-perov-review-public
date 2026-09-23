# Master Handbook: Autonomous **Yearly** Review Paper Production

**Version 3.0 · 2026-09-10 · Havid Aqoma**
**Mode: BACKFILL — a year harvested directly, not aggregated from monthly runs.**

Reference implementation: `perovskite_pv_yearly`
Sibling projects, both working and **not to be modified**:
- `auto-perov-review` — the monthly pipeline (source of every reused module)
- `manuscript\2026-H1_v4` — the six-month issue

---

## 0. Read this first

You are an autonomous agent. Your job is to produce **one yearly review paper**
of perovskite photovoltaics from a year's literature, as **two PDFs plus a
raw-data pack**, with every number traceable to a verbatim quotation from a
cited paper's own abstract.

**This handbook has produced a shipped artifact.** Version 3.0 is written
*after* the 2025 issue was built end to end, so the numbers below are
measurements, not projections. Where something is still a projection it says
so.

### 0.1 What the 2025 issue actually produced

Reproduce this quality or better:

| Artifact | Measured |
|---|---|
| `manuscript_yearly.pdf` | **35 pages**, 9,070 words, 174 citations, 470-word abstract |
| `supplementary_yearly.pdf` | 8 notes, every number script-computed |
| `fig/F1a…F6.pdf` | **8 plates** |
| `data/*.csv` | 6 files + `claim_cards.jsonl` |
| Gates | **18 pass, 1 cold-start, 0 fail** |
| Anchor verification | **1,655 anchors, 1,655 verbatim, 0 defects** |
| Corpus | 7,931 works → 7,794 in scope → 450 closely read |
| Wall clock | harvest ~15 min · extraction 1 h 59 m · draft 1 h 1 m · build ~3 min |

Title, generated from the year's own evidence mass:
> *Perovskite Photovoltaics in 2025: Defect passivation, interface and contact engineering*

### 0.2 The seven principles

1. **Format is generated, never model-written.** Title blocks, citation
   numbering, reference lists, back matter: all script output.
2. **Every defect becomes a gate, never a prompt reminder.** A defect with a
   gate cannot return. A defect with a note in a prompt returns next issue.
3. **Verify the artifact, not the process.** Parse the rendered PDF. Every
   format defect this project shipped was found by a human reading output
   that had already passed a markdown inspection.
4. **No prose reaching a reader may be authored outside the evidence chain**,
   including by a script.
5. **A generator and its gate must be mutually consistent.** When per-section
   minimums collide with an issue-level ceiling, the **generator** moves.
6. **Never widen a gate to make output pass.** One narrow exception exists and
   is documented in §9.3. Read it before you consider a second.
7. **A gate that stops noticing something is worse than no gate**, because it
   teaches you to trust output you should be checking. §9.3 is the instance.

### 0.3 Two errors this handbook made, kept as warnings

**"No 2025 data exists."** Asserted in a decision log; false. It conflated
*"no 2025 harvest exists in `runs/`"* (true, checkable) with *"no 2025
literature was published"* (absurd). Measured: **7,931 works**, the largest of
2024/2025/2026.

**§1.3 applied to the wrong question.** v1.0 argued an old year "retrieves
worse", citing a full-text table. This pipeline is abstract-first. Measured
abstract reconstruction: 2025-06 **70%**, 2025-12 **74%**, against a **62%**
control from the month that actually shipped.

> **Rule: state the measurement, not its implication. Before citing a
> handbook rule as a blocker, check that the quantity it measures is the
> quantity in question.**

---

## 1. Why BACKFILL, and the cost model

### 1.1 The inversion

v1.0 built a yearly issue by aggregating twelve monthly runs. **This project
has no monthly runs and never will** — the monthly pipeline is a separate
repository producing good work, and the yearly effort was moved out precisely
so it could not destabilise it.

So a year is **harvested directly in one sweep** and sliced into months in
Python afterwards. One sweep, not twelve, because:

- one count-band assertion instead of twelve
- **consistent month assignment**: a work whose date is revised between two
  monthly sweeps would otherwise land in two months or neither

### 1.2 Cost — measured, and the answer to the obvious question

> **Harvest costs NO tokens.** `s01`, `s02`, `s04` are API calls and JSON
> parsing with zero LLM involvement. Tokens are spent only at extraction
> (`s09`), and only on the depth-selected pool.

`depth_target: 450`, so the extractor reads ~450 cards **regardless of corpus
size**. A wider corpus is nearly free; only **deeper reading** costs money.

| Stage | LLM? | Measured 2025 |
|---|---|---|
| harvest | no | ~15 min, 40 pages |
| scope + dedupe | no | 16 s |
| venues + depth | no | ~5 min (951 venues) |
| **extraction** | **yes** | **1 h 59 m**, 425,643 tokens out |
| verify anchors | no | ~1 min |
| stats + map | no | ~1 min |
| figures | no | ~20 s |
| **draft** | **yes** | **1 h 1 m**, 11 sections |
| build + SI | no | ~3 min |

Total ~3 h 20 m, of which **3 h is model time**. An earlier "12 hours" figure
was the cost of running the monthly chain twelve times — a different thing.

### 1.3 Abstract-first is a decision, not a compromise

Full-text retrieval succeeds for ~5% of papers; publisher WAFs refuse
automated fetches. Abstract coverage on 2025: **5,062 of 7,931 (63.8%)**.

| Basis | Eligible | 95% CI on a 50% rate |
|---|---|---|
| full text (5%) | ~400 | ±5 pp, tiny pool |
| **abstract (64%)** | **5,062** | **±1.4 pp** |

Guard 1 anchors every claim in the abstract, so the abstract *is* the evidence
chain's input. Do not block on full text.

### 1.4 The January lumping artefact — measured, and gated

```
raw 2025-01: 1,569 works        every other month: ~550
```

**OpenAlex stores an imprecise publication date as January 1.** A work known
only as "2025" lands on `2025-01-01`.

Untreated this is a **fabricated spike** in the trajectory section and on F5 —
a real number describing something that did not happen.

The fix, in `date_precision()`:

- a work dated exactly `YYYY-01-01` → `date_precision: "year"`, month unknown
- every other date → `"day"`, assigned to its month
- **genuine January papers are kept** (`2025-01-15` is day-precision)
- imprecise works **stay in the corpus** — real papers, unknown month
- the count is **reported** (`imprecise_dated: 1089`, 13.7%)

Result: 2025-01 shows **480**, against 478–650 elsewhere.

> **Rule: never silently reassign a date. Exclude it from the series, keep it
> in the corpus, report the count.**

### 1.5 Duplicate semantics are INVERTED here

v1.0 warns that **zero** cross-month duplicates across twelve months is
suspicious — a work published late in June is backfilled into July's index and
appears in two sweeps.

**One annual sweep cannot produce that.** A zero here is a property of the
design. `aggregate()` returns an explicit `duplicate_semantics` string so no
reader has to infer it. Collapse still runs on `canon_work_key`, which drops
Elsevier's `/j.` (a writer once transcribed `10.1016/joule…` for a card keyed
`10.1016/j.joule…`).

---

## 2. Sources and model boundaries

### 2.1 OpenAlex is primary and sufficient; S2 is best-effort

Measured per-source yield, monthly project:

| Month | openalex | arxiv | crossref | s2 |
|---|---|---|---|---|
| 2026-06 | 644 | 11 | 200 | **0** |
| 2026-07 | 657 | 6 | 200 | 549 |

Only OpenAlex is paginated and only OpenAlex returns
`abstract_inverted_index`. Crossref is capped at `rows=200` and requests no
abstract. S2 is anonymous and non-deterministic.

But S2 is not decoration: monthly `s02_06.py` closes a **40% abstract gap**
with it. So **demote, do not drop**: wrapped in `try/except`, records
`s2_status`, and **a 429 can never fail a build**. It failed twice on the 2025
run (HTTP 500, then 429) and cost nothing.

An S2 gap-fill probe was **rate-limited on 2 of 3 periods** and is recorded as
**inconclusive**, not as "S2 adds nothing."

> **Rule: a throttled or implausible zero is a bug until proven otherwise.
> Surface it; never bank it as a result.**

### 2.2 Models never perform retrieval

| Role | Model allowed? |
|---|---|
| write prose (`s13y`) | **yes** — exactly one model, no fallback |
| extract cards from abstracts (`s09`) | **yes** — under JSON-shape probe + provenance from records |
| **retrieve or transcribe the source record** | **NEVER** |
| review | yes, and reviewers never write |

**Why.** The abstract is the evidence chain's input. Guard 1 requires the
anchor to appear word-for-word in it. That abstract exists because
deterministic code rebuilt it from an integer→word inverted index. A model in
that path can drop a row, merge two, reflow whitespace or normalise a DOI —
and **every downstream guard still passes**, because the guards check the
anchor against *the text the model handed them*.

It also attacks nothing: harvest already has zero LLM cost.

Constructive form, if you want a model in the loop: run it **once** as an
independent coverage auditor with a hard-constrained prompt (return only a
JSON array of DOIs), diff against the deterministic harvest, feed genuine gaps
back as an explicit DOI allow-list. **The model proposes; Python records.**

### 2.3 Provenance comes from records, never live config

`aggregate()` derives the extractor from `card["extractor"]["model"]` and
returns the **full distribution**. More than one key ⇒ the declaration must
name **both models with card counts**.

The monthly project shipped a false statement here once: config was edited
mid-session and the rebuilt PDF declared an extractor that never touched it.

---

## 3. Repository layout and the chain

```
MASTER_HANDBOOK_YEARLY.md      this contract
config/
  yearly.yaml                  yearly bands (NEW keys)
  gates.yaml                   MONTHLY bands, never read for a yearly envelope
  axes.yaml exclude.yaml title_terms.yaml venue_whitelist.yaml models.yaml
  tex/manuscript_head.tex      TRACKED: siunitx + mhchem(version=4)
scripts/
  run_yearly.py                unattended runner, cards -> both PDFs
  verify_anchors.py            MANDATORY gate
  verify_pdf.py verify_notation_pdf.py
  common/                      net env titles ledger doi dates csvio cleaners
  stages/
    s01_harvest_yearly.py      ONE annual sweep + date_precision
    s02_06.py                  scope, dedupe, mechanism labels
    s04_10.py                  venues, depth selection, audit flags
    s09_cards.py               [LLM] extraction, the only paid stage
    yearly_corpus.py           annual corpus + cards, month-sliced
    yearly_audit.py            twelve-point audit series
    yearly_stats.py            POOLED rates + trajectory + YoY
    yearly_section_map.py      11 sections from annual mass
    s11y_figures_yearly.py     8 plates + per-figure CSV
    s13y_draft_yearly.py       [LLM] 5-phase draft
    s18y_build_yearly.py       assemble, 19 gates, PDF
    s19y_si_yearly.py          SI PDF + data pack
    hygiene.py notation.py layout.py boilerplate.py section_map.py util.py
tests/                         82 tests, no network
```

### 3.1 Run order

```bash
cd perovskite_pv_yearly
Y=2025

python -m pytest tests/ -q                          # must pass FIRST
python scripts/stages/s01_harvest_yearly.py   $Y    # free
python scripts/stages/s02_06.py               $Y    # free
python scripts/stages/s04_10.py               $Y    # free
python scripts/stages/s09_cards.py            $Y    # THE ONLY PAID STAGE
python scripts/verify_anchors.py              $Y    # MANDATORY, must exit 0
python scripts/stages/yearly_corpus.py        $Y --partial
python scripts/stages/yearly_stats.py         $Y --partial
python scripts/stages/yearly_section_map.py   $Y --partial
python scripts/stages/s11y_figures_yearly.py  $Y    # free
python scripts/stages/s13y_draft_yearly.py    $Y    # paid
python scripts/stages/s18y_build_yearly.py    $Y
python scripts/stages/s19y_si_yearly.py       $Y
```

Or `python scripts/run_yearly.py $Y` from cards onward.

**`--partial` is correct here and is not a compromise.** All twelve months are
present; the flag relaxes only the "twelve run directories exist" check, which
cannot apply to a single-sweep harvest. **G11-coverage independently asserts
`n_months == 12`.**

### 3.2 What was copied, what was written, what was refused

| Copied verbatim | Why it must not be rewritten |
|---|---|
| `hygiene.py` | narration filter, ONE canonical object. Three divergent copies once let `"I have launched the search command…"` into a shipped PDF **with G4 reporting pass** |
| `notation.py` | siunitx/mhchem, Unicode normalisation, mask-before-substitute |
| `layout.py` | title-block bands **measured on rendered pages** |
| `boilerplate.py` | affiliations, acknowledgements, AI declaration |
| `section_map.py` | `TITLE_BANK` + `FOLD_INTO` |
| `common/*` | keyed-vs-plain HTTP separation, redaction, retry |
| `verify_*.py` | evidence and rendered-artifact discipline |
| `config/tex/manuscript_head.tex` | **tracked**; it once sat in gitignored `.staging/` where a fresh clone would silently lose siunitx |

| Written new | Replaces | Why a copy would fail |
|---|---|---|
| `s01_harvest_yearly.py` | `s01_harvest.py` | monthly asserts a monthly count band; annual needs one sweep + `date_precision` |
| `yearly_corpus.py` | `yearly_aggregate.py` | the aggregator resolves `runs/<YYYY-MM>.active` **twelve times** — it would fail closed on day one here |
| `yearly_audit.py` | `yearly_stats.monthly_series()` | that reads twelve per-month `stats.json` files; none exist |
| `s11y_figures_yearly.py` | `s11b_figures_v2.py` | needs F5/F6 and the junction split |
| `s13y_draft_yearly.py` | `s13d_draft_v4.py` | 5 phases, two new spine roles |
| `s18y_build_yearly.py` | `s18d_build_v4.py` | yearly bands, per-class G3c, G11 |
| `s19y_si_yearly.py` | `s19_si.py` | 8 notes from `stats_yearly.json` |

**`yearly_corpus.aggregate()` reproduces the old aggregator's contract
exactly** — `year, months, n_months, corpus_n, cards_n,
cross_month_duplicates, per_month{...}, extractors, corpus[], cards[]`. That
is what let two verified downstream modules be reused with a **one-line import
change each**.

**Deliberately not copied:** `yearly_aggregate.py`, `yearly_tokens.py`. Both
need twelve monthly run directories.

### 3.3 Copying is not the same as being current

A staleness audit over all 17 copied modules found **two genuinely stale**,
both load-bearing for the build:

- `layout.py` missing `measure()` → gate G10 needs it
- `boilerplate.py` missing `CORRESP_NOTE` → the title block needs it

Two others differ **deliberately** (`util.py` = year helpers, `env.py` = the
`.env` path fix) and 13 are byte-identical.

> **Both were found only by trying to IMPORT what the build needs. Copying
> files and assuming they are current is how the divergent-copies defect
> entered the monthly project. Run the import check, not an eyeball diff.**

---

## 4. The evidence chain

**Every number in the manuscript traces to a verbatim quotation from the cited
paper's own abstract.** Unlike v1.0's design, this project *runs* extraction,
so it *runs* the guards.

### 4.1 The five guards, in order

1. the quotation appears **word for word** in the source abstract
2. the numeric value appears **inside its own quotation**
3. **truncate to 25 words FIRST**, then apply check 2
4. the device label comes from **the value's own quotation**, not the paper
5. if a certified anchor names a multi-junction stack, the architecture is
   corrected to match **the number**

> Guard order is not cosmetic. Checking the value then truncating shipped five
> fields whose quotations ended immediately before their own number, while the
> stage reported `nulled_number: 0`.

Measured on 2025: `nulled_anchor: 18`, `nulled_number: 2`,
`arch_corrected_to_tandem: 1` — guard 5 fired on a real card.

### 4.2 `verify_anchors.py` is mandatory

It shares **no code** with the extraction stage. The guard-order bug was found
this way and only this way.

```
1655 anchors, 1655 verbatim, 0 over 25 words,
0 values missing from their own quote      status: PASS
```

A non-zero exit **stops the chain**. Drafting on unverified cards puts
unanchored numbers in front of a reader.

### 4.3 The silent batch-parse hole — closed, and worth understanding

Measured on a single-month dry run:

```
[09]  96/152 -> 96 cards
[09] 108/152 -> 96 cards      <- 12 papers in, 0 cards out
```

Papers 96–107 were exactly one batch. Their abstracts were 148–342 words —
good input. The batch's response failed to parse.

`call_opencode` already fails loudly on `rc != 0` or empty stdout. But when it
returns **text that will not decode**, `parse_array` returns `[]` by design,
`got` is empty, every paper receives `o = {}`, and the loop produces no card
**without raising**. The summary reported `dropped_papers: 12` as if normal.

**Loud failure on one side of the seam, silent zero on the other.**

Three-layer fix:

1. `parse_batch_or_raise()` retries the **same** model once (not a fallback —
   a fallback puts two models in one corpus), then **raises**. A *partial*
   batch still passes; short is not dead.
2. `MIN_COVERAGE = 0.98` on cards/depth_papers, checked after the loop. A test
   pins that 140/152 = 92.1% would be **rejected** and 449/450 accepted.
3. `09_batch_coverage.json` records per-batch `n_answered`, so
   `dropped_papers` is auditable.

`parse_array` is **unchanged** — it is a pure decoder; raising there would
conflate "cannot decode" with "decoded an empty list."

Measured on 2025: **450/450 cards, coverage 100.0%, 38 batches,
`batches_short: 0`**, with one retry firing on batch 0. The failure is
**random, not content-specific** — different batch each run — which is why the
retry is the correct fix.

### 4.4 Fields must survive the pipeline

`s01_harvest_yearly` stamps `date_precision`, but `s02_06.normalize()`
rebuilds each record field-by-field and **silently dropped it**. Cards carried
neither `publication_date` nor `date_precision`, because a monthly run never
needed them: the run directory *was* the month.

Consequence, measured: **all 7,931 works came out month-unknown**, not just
the 1,089 genuinely undated ones. That empties the trajectory series, F5, F6
and the trajectory/synthesis spine roles — the only things making this a
*yearly* review — and `{{P_CERT_FIRST}}` becomes unresolvable, failing the
build **after extraction is paid for**.

Fixed by carrying the field **through**, never recomputing it. Recomputing
would be a second definition of the Jan-1 rule.

> **Rule: after adding a field upstream, assert it survives to the consumer.
> `normalize()` drops anything not literally named in its dict.**

---

## 5. Statistics

### 5.1 A pooled rate is NOT the mean of twelve rates

| | month 1 | month 2 | pooled | mean of rates |
|---|---|---|---|---|
| numerator | 10 | 0 | 10 | |
| denominator | 100 | 900 | 1000 | |
| rate | 10.0% | 0.0% | **1.0%** | **5.0%** |

A **five-fold error**, from a calculation nobody would think to check. Every
rate is summed-numerator-over-summed-denominator, and a unit test pins the
extreme case.

### 5.2 Report the spread

A pooled rate hides whether a value sat flat or swung. Measured 2025, over
4,730 abstracts:

| Quantity | Pooled | Monthly range |
|---|---|---|
| efficiency stated | 51.6% | 47.8 – 54.0 |
| stabilised | 8.8% | 6.2 – 12.0 |
| area stated | 7.3% | 5.2 – 9.3 |
| certified | 5.8% | 3.4 – 7.6 |
| hysteresis | 3.1% | 1.6 – 4.3 |
| **ISOS labelled** | **1.1%** | **0.2 – 3.2** |

**The ISOS row is the finding.** Its thinness is a fact about the field.

### 5.3 The denominator is works WITH a usable abstract

≥40 words. Counting abstract-less works would depress every rate, **and the
depression would look like a finding**. A zero denominator yields `None`,
never `0.0%`.

### 5.4 Simulation never reaches the measured frontier

`frontier_series()` filters `lens in ("theory", "review")`. A drift-diffusion
study reporting ~30.8% once sat beside certified hardware until a human
noticed. A unit test feeds a 40% theory value and proves it never arrives.
**`scale_up` is kept** — real module measurements.

Measured 2025: 63 of 450 cards (14%) are theory or review.

### 5.5 Year-over-year is a cold start and must stay one

No 2024 yearly issue exists, so `prior_year_stats()` returns `None`, the issue
ships `yoy.prior_year: null`, and **there is no YoY token**. An invented
comparison fails the build.

2024's raw count is knowable (6,784) and that is exactly the temptation: **a
count is not a prior-year stats file.**

### 5.6 The trajectory series

```
frontier.months            [2025-01 … 2025-12]
top_certified_series       [30.26, 27.17, 28.78, 28.31, None, 28.81,
                            26.56, 33.15, 31.47, 28.9, 26.96, 30.1]
n_certified_series         [8, 4, 6, 4, 0, 3, 8, 6, 7, 7, 7, 5]
certified_delta_pp         -0.16
```

Two things a yearly issue must handle honestly:

1. **The frontier did not rise.** −0.16 pp first-to-last. State what the data
   says.
2. **May has no certified value.** That is an evidence gap, not a zero. F5
   draws it as a grey column.

`certified_delta_pp` is an **absolute delta in percentage points**, never a
growth rate: a percentage change between two percentages is routinely
misread.

---

## 6. The section map

`yearly_section_map.py`. Nothing is typed in — titles, ceilings and citation
targets all fall out of the annual evidence mass.

### 6.1 Spine, in order. `gaps` is ALWAYS last, asserted in code

| Role | Ceiling | Cite target | Job |
|---|---|---|---|
| `intro` | 700 | 0 | locate the open problem |
| `trajectory` | 900 | 18 | **what changed across twelve months** |
| 5–6 × `mechanism` | 700–1500 | ceiling/45 | the physics |
| `synthesis` | 900 | 10 | **what the mechanisms say TOGETHER** |
| `audit` | 700 | 7 | reporting practice |
| `gaps` | 900 | 9 | what to measure differently |

`trajectory` and `synthesis` are the two roles a monthly issue cannot have.
**Without `synthesis`, a yearly issue is twelve monthlies stapled together.**

**One section per month is not on this table and never will be.** The
mechanism axes are the organising principle; the months are the *data*.

### 6.2 Knobs, and why each moved

| Knob | Monthly | Yearly | Reason |
|---|---|---|---|
| `MIN_MECH`/`MAX_MECH` | 4/5 | 5/6 | annual mass supports one more |
| `MIN_DEPTH` | 10 | 25 | below this an axis cannot carry 700 words |
| `BODY_WORDS` | 2400 | 7000 | 2.9× |
| `MECH_MAX_WORDS` | 620 | 1500 | stops one axis eating the year |
| `WORDS_PER_CITE` | 42 | **45** | §6.3 — not a free choice |
| `CITE_SUM_BAND` | 55–72 | 150–200 | asserted against the 220 ceiling |

### 6.3 The generator/gate invariant fired during development

`WORDS_PER_CITE` was first 40, spine cites 22/12/8/10:

```
FAIL-CLOSED: per-section citation minimums sum to 214, outside (150, 200).
Retune WORDS_PER_CITE / CITE_CLAMP, never the gate.
```

A writer meeting every section minimum would overshoot the issue ceiling, and
G2c would fail while every section had done exactly what it was told.

Fixed by moving the **generator**: 40 → 45, spine cites 18/10/7/9. Measured
result 195, then 174 on the real 2025 mass — inside band with headroom.

> **When per-section minimums collide with an issue-level ceiling, the
> generator moves. Always.**

### 6.4 Determinism

The same year and mass always yield the same `sha256`. Verified: two
consecutive `s04_10` runs produced identical 450-paper selections and the same
map sha. A map that changed per run would make resumes redraft forever.

### 6.5 The cache trap

A change to `RULES`, a task prompt, **or `hygiene.py`** does **not** change the
map sha. A yearly draft is the most expensive artifact here, so the temptation
to reuse cached sections is strongest.

> **If you edit prompt text, delete the affected `draft_yearly/sec*.md` by
> hand. The stage will otherwise happily reuse prose written under the old
> instructions, and nothing will tell you.**

---

## 7. Drafting

### 7.1 Five phases, so closing text reacts to what the body says

```
A  body        intro, trajectory, mechanism sections
B  synthesis   reads the FULL body
C  audit       reads the body + the twelve-point series
D  gaps        reads everything above
E  abstract    reads everything; NO citations, NO digits
```

Handing the writer statistics alone recreates closing text that could have
been written before the body existed — and therefore reads the same every
issue.

### 7.2 Exactly one model writes prose, with no fallback

`agy` / `gemini-3.8-flash-high`. Retry the **same** model 3× with backoff. A
retry is not a fallback; a fallback means two prose voices in one document.

Probe before drafting: `agy -p "Reply with exactly: OK"`. Fails closed.

### 7.3 `_attempt` enforces the contract

Word band 45–135% of ceiling, citation target as a **floor**. Three attempts,
then fail closed.

This is load-bearing. Measured 2025: section 2 returned **12 citations against
a target of 18**, was rejected, and the retry returned **25**. Without that
loop the issue total would have drifted under the 160 floor and G2c would have
failed after the whole draft was paid for.

### 7.4 Never dictate phrasing

```
BAD   "Say that the certified frontier was flat while reporting practice
       improved."
GOOD  "The trajectory series and the audit series may disagree. Say what
       the year's evidence supports, in your own words."
```

> **A prompt that contains a sentence will get that sentence back, every
> year, forever.** A gaps prompt phrased as a sentence came back nearly
> verbatim in two consecutive monthly issues, and it took two issues to
> notice.

`ANGLES` rotates by **year**, so consecutive issues argue differently with no
per-run randomness.

### 7.5 The abstract contract

- **no digits** — the stage rejects any literal digit and retries
- **no citations** — written last
- **400–550 words**
- named tokens only; the build substitutes canonical values
- **an unresolvable token fails the build.** A hole never ships.

Backfill-specific tokens: `{{N_MONTHS}}`, `{{N_MONTH_UNKNOWN}}`,
`{{P_CERT_FIRST}}`, `{{P_CERT_LAST}}`, `{{DELTA_CERT_PP}}`,
`{{PCT_CERT_MIN}}`, `{{PCT_CERT_MAX}}`.

`{{N_MONTHS}}` and `{{N_MONTH_UNKNOWN}}` are not padding — they force the
issue to state its own coverage in the most-read part of the paper.

### 7.6 A backfill issue must disclose that it is one

This issue was **not** produced by monthly monitoring. It was assembled
retrospectively. The intro must say so and the abstract must carry its
coverage tokens.

> An issue that reads as if it tracked the field month by month, when it did
> not, is a misstatement **no gate can catch**, because the text is internally
> consistent.

### 7.7 Not yet ported

`prior_closing_block()` quotes the prior issue's **actual** closing text back
to the writer, so issue N+1 differs from N. There is no prior yearly issue, so
it would feed an empty block. **Port it when the second yearly issue is
written** — recorded as `todo_next_issue` in the draft metadata so a cold-start
design is not silently inherited.

---

## 8. Figures

Eight plates. A figure earns main-text space by carrying an argument the prose
cannot make in a sentence.

| Fig | Plot | Argument |
|---|---|---|
| **F1a** | certified vs self-reported, **single junction** | 41 certified, max 27.3%, against the 29.4% SQ line |
| **F1b** | certified vs self-reported, **tandem/module** | 24 certified, max 33.15%, against the 47.6% line |
| **F2** | efficiency vs area, log x | 58 pairs over 0.04–764 cm². The frontier does not survive scale |
| **F3a** | effort map, **single junction** | where close reading went, by axis |
| **F3b** | effort map, **tandem/module** | same question for stacks |
| **F4** | stability evidence in full | **15 T80 values, 24 protocol labels of 450.** Its thinness is the finding |
| **F5** | frontier trajectory, 12 points | whether the frontier moved, and on how much evidence |
| **F6** | audit trajectory, 6 rates | whether reporting practice improved |

### 8.1 Split by junction class — why this is two figures, not one

Measured 2025:

| | Single junction | Tandem/module |
|---|---|---|
| cards | 306 | 81 |
| certified | 41, max **27.3%** | 24, max **33.15%** |
| champion | 240, max 33.2% | 63, max 33.5% |

Two populations, **two different physical ceilings** — 29.4% for a 1.55 eV
single junction, 47.6% for a two-junction stack.

Plotting them on one axis actively **hid** that: the tandem points sat above
every single-junction point and a reader could not tell whether the frontier
was a single-junction achievement or a stack. **It is the misattribution
defect in chart form.** Separating the panels is what lets each carry its own
limit line.

Classification uses `_is_single_junction()`, **imported from the build** so
the figure and the gate agree on what a tandem is. It checks the value's own
**anchor** first, the title second: a paper's title describes the paper, the
anchor describes the number.

### 8.2 Rules, each from a real defect

1. **Never hard-code a plotted number.** Every value reads from stats or
   cards.
2. **Simulation never sits on a measured figure.** `theory` and `review` are
   excluded from every performance plate.
3. **Band labels go OUTSIDE the axes frame** (`y=1.02`, `va="bottom"`,
   `clip_on=False`). Two cleverer positions inside the data region both
   collided with data.
4. **F5 labels every point with its device class.** The highest values are
   tandems; an unlabelled trajectory of mixed classes is the misattribution
   defect as a line chart.
5. **A figure with no data is not written.** An empty axes frame published as
   a figure looks like a finding. Skipped plates are reported.
6. **Every plate emits its own CSV**, including exclusions.
7. **Control tick density on log axes.** F4's T80 axis spans 144–3,200 h;
   matplotlib's default decade+minor labels **collided into an unreadable
   smear**. Fix: a small number of explicit ticks at round hours **derived
   from the data range**, minor labels suppressed, and integer-only ticks on
   count axes.

### 8.3 The orphaned-figure bug — and why two gates missed it

F1 was rendered, copied into the deliverable directory, and **never placed in
the manuscript**. The claim was keyed on `role == "frontier"` — carried over
from the monthly spine. **The yearly spine has no `frontier` role**; it has
`trajectory`. The condition never fired.

- **G9c passed** — it only checks that *attached* figures are unique
- **G9e passed** — it only checks F5/F6 *exist on disk*

Two gates, both green, neither watching the actual hole.

Fix: every claim is keyed on a role or axis the yearly map **actually emits**,
plus a fallback loop that places any still-unattached figure rather than
dropping it.

> **Rule: a figure keyed on a role the map does not contain is silently
> dropped. Assert that every rendered figure is PLACED, not merely present.**

---

## 9. Gates

**19 gates. 18 pass, 1 cold-start, 0 fail on the 2025 issue.**

| Gate | Checks |
|---|---|
| G1 | every `[@key]` resolves to a card; 174 resolved, 0 unresolved |
| G2 | body words ≤ ceiling×1.15, each section ≤ its ceiling×1.35 |
| G2b | citation numbers monotonic by first appearance |
| G2c | total citations in `[160, 220]`; measured 174 |
| G3 | every abstract numeral traces to stats or a card |
| G3b | abstract 400–550 words, no citation markers |
| G3c | **per-class** physical bounds |
| G4 | no em-dash, no banned words, **no agent narration** |
| G5 | page bands, measured on the rendered PDF |
| G6 | no "we measured/fabricated" |
| G7 | abbreviations expanded at first use |
| G8 | novelty vs prior issues — **cold-start here** |
| G9a | no flat units or unrendered formulae |
| G9b | every citation marker hyperlinked; 312 links, 0 unlinked |
| G9c | one figure file attaches to at most one section |
| G9d | AI declaration names products, not CLI slugs |
| G9e | **required figures present** |
| G10 | title-block spacing, measured on the page |
| G11 | **coverage**: `n_months == 12`, cards in band |

### 9.1 G3c is per sample class

| Quantity | Bound | Basis |
|---|---|---|
| single-junction PCE | ≤ 29.4% | 1.55 eV Shockley-Queisser |
| 2-terminal tandem PCE | ≤ 47.6% | two-junction detailed balance |
| EQE | ≤ 100% | definitional |
| FF | ≤ 92% | practical ceiling |

G3 asks only "does this number trace to a card?". A monthly issue once said
*"32.95% in single-junction inverted cells"* and 32.95 **did** trace to a
card, so G3 passed it. The number was real; **the device was wrong.** Only a
physical bound can see that.

Applying the single-junction limit globally would reject the tandems that
dominate the frontier; applying the tandem limit globally would readmit the
original defect.

> **Traceability proves provenance, not meaning.**

### 9.2 G8 reports `cold-start`, not `pass`

It compares against prior issues; this repository holds none. **A green G8
would later be misread as evidence that novelty was checked.**

### 9.3 The one legitimate widening, and what it cost

The first build failed G5 at **19.6 content / 30 total** pages against
`[20,28]/[32,45]`. Havid decided to widen to `[18,28]/[28,45]`.

**Why that was defensible:** Appendix B listed the old band as **projected**,
scaled from monthly output. It had never been bracketed on a real yearly
artifact, so the floor described an issue nobody had built. That is a
different act from relaxing a band a measured artifact had already satisfied.

**What it cost, and why the cost was paid separately:** G5 measures pages, and
a missing figure shows up as a page shortfall. That first failure had exactly
one cause — `figures: 0`. Widening the band removed the pipeline's **only**
alarm for a figure-less manuscript.

So the alarm moved to **G9e-figures-present**, which counts figures directly
instead of inferring them from a page count.

**The postscript matters.** Once the eight figures existed the manuscript
reached **35 pages / 23.6 content**, which clears even the *original* bands.
The widening turned out not to be load-bearing: the real problem was the
missing figures all along, exactly as the first diagnosis said.

> **Rule: if you widen a band, ask what that band was the only witness to,
> and give that thing its own gate in the same commit.**

### 9.4 Bands are NEW keys

`config/yearly.yaml` holds every yearly band. **`config/gates.yaml` is never
read for a yearly envelope** and still describes the monthly artifact exactly:
`[12,17]` total, `[8,11]` content. A test asserts the monthly bands are
unchanged **and** that yearly floors sit above monthly ceilings.

### 9.5 Freeze inputs before gating

Fingerprint every draft, refuse to build if any changed within 20 s, refuse if
`agy` is alive. Two orphaned draft processes once kept writing after their runs
reported complete: `prose_words` drifted 4498 → 4304 across builds, every gate
passed every time, and **no gate report described the shipped file.**

The orphan check **detects and refuses; it never kills.** Killing by broad
name match would take down the orchestrator running the build.

### 9.6 If a gate fails, fix the OUTPUT

The build writes the gate report and the PDF, then reports which gates failed.
The artifact exists so a human can **read** it; it is simply not shippable.

---

## 10. Supplementary Information and the data pack

`s19y_si_yearly.py`. **No LLM runs in this stage** — a method described by a
model is a method nobody verified.

### 10.1 Eight notes, all script-composed

| Note | Content |
|---|---|
| S1 | corpus construction, selection, **the retrospective-assembly disclosure** |
| S2 | publication-date precision and the Jan-1 artefact |
| S3 | the five guards in order + independent re-verification counts |
| S4 | reporting audit: pooled rates **with** monthly spread |
| S5 | the twelve-point trajectory table |
| S6 | limitations |
| S7 | the gate table |
| S8 | reproduction, citation count, map fingerprint |

### 10.2 Honest bounds

The hand-labelled validation set for the reporting detector **does not
exist**. So every audit percentage is written **"detected in at least X%"**
with no precision or recall figure. A bare percentage would imply a validated
detector.

This is the **single highest-value outstanding human task** in the project.

### 10.3 The data pack

| File | Contents |
|---|---|
| `corpus_metadata.csv` | every work in scope, with `date_precision` and `source_month` |
| `extracted_claims.csv` | **one row per number, each with its VERBATIM QUOTATION** |
| `monthly_series.csv` | per-month per-quantity series |
| `frontier_trajectory.csv` | per-month leading value **with device class** |
| `reporting_audit.csv` | rates **with denominators**, precision marked "not validated" |
| `axis_distribution.csv` | depth papers per axis |
| `figure*.csv` | one per plate, including exclusions |
| `claim_cards.jsonl` | the full extraction record |

`extracted_claims.csv` is the important one. **The verbatim column is what
makes the audit checkable rather than assertable.**

### 10.4 Count citations in BOTH marker forms

The SI first reported **"cites 0 of 174 references"** — a false statement
about the manuscript, in the document whose job is to describe it.

Cause: the build wraps every citation as `[\href{https://doi.org/…}{12}]` for
clickability, and the counter looked only for a plain `[12]`. It found **zero**
markers in a body carrying **312**.

Fix: count the linked form first, then any surviving plain form. The
nomenclature guard applies to both — `[60]fullerene` and `[100] growth` are
not citations, and any bracketed number above `n_refs` cannot be one.

---

## 11. Checklist

```
[ ]  1. python -m pytest tests/ -q          82 tests, all green
[ ]  2. git status clean; git log -1
[ ]  3. probe tools: agy / opencode.exe / pandoc.exe / tectonic
[ ]  4. writer probe: agy -p "Reply with exactly: OK"    (fails closed)
[ ]  5. orphan check: no agy process alive
[ ]  6. harvest: count band OK, twelve months non-empty
[ ]  7. check imprecise_dated; ~14% expected, 0% is SUSPICIOUS
[ ]  8. scope: dropped_wrong_month MUST be 0
[ ]  9. depth: jaccard_median and marginal_n; a perfect 1.0 is suspect
[ ] 10. EXTRACTION: coverage_pct >= 98, batches_short 0
[ ] 11. verify_anchors.py exits 0            MANDATORY
[ ] 12. stats: sanity-check pooled rates against the monthly spread
[ ] 13. section map: 5-6 mechanism sections, cite_sum in band
[ ] 14. figures: 8 plates, none skipped, each with a CSV
[ ] 15. draft: watch for "STRIPPED narration" and REJECT lines
[ ] 16. build: ALL GATES PASS; G8 cold-start is acceptable, fail is not
[ ] 17. check for ORPHANED figures: rendered but not attached
[ ] 18. SI: cited_in_main_text must equal references_listed
[ ] 19. rendered-PDF verification, incl. span-geometry notation
[ ] 20. HUMAN: READ THE PDF
[ ] 21. commit code fixes and artifacts separately
```

### 11.1 Why step 20 cannot be automated

Gates catch **regressions**. Humans catch **new** defects. Every defect class
in this handbook entered it because Havid read a rendered page:

- a simulated data point on a measured-performance figure
- affiliations 24.7 pt left of the page midline
- a doubled figure caption
- out-of-order citation numbers
- an August issue that read like July's
- **overlapping axis labels on F4**
- **single junctions and tandems sharing one axis**
- `"I have launched the search command and will wait for it to finish."`
  under a section heading, **with G4 reporting pass**

This project's first issue has **no regression history**, so the gates are at
their weakest and the human read is at its most valuable. Read the
**trajectory section and F5 first**.

---

## 12. Environment

### 12.1 Windows specifics, all hit for real

- Resolve the real `.exe`. CLI shims may be POSIX scripts `CreateProcess`
  cannot run: `node_modules/opencode-ai/bin/opencode.exe`.
- `cmd.exe /c <path with spaces>` splits on the space in
  `<HOME>`. Bypass the shim.
- **pandoc lives at `%LOCALAPPDATA%\Pandoc\pandoc.exe`** and is **not** on
  PATH. Do not "fix" PATH; do not trust `shutil.which` alone.
- MSYS `/tmp` is invisible to native Python.
- `taskkill //F` has its flags eaten by MSYS. Use PowerShell `Get-Process`.
- **`.env` lives at the REPO ROOT.** `common/env.py` originally used
  `parents[1]`, which is `scripts/`, so it looked for `scripts/.env`, found
  nothing, and returned **silently**. Every OpenAlex call ran anonymously in
  both repos despite a populated `.env` on disk. Nothing complained, because
  `net.py` appends the key only `if key` and an anonymous request still
  returns HTTP 200. The only symptom is a lower rate limit.

### 12.2 Python specifics

- f-strings cannot contain backslashes.
- **Inline `(?i)` mid-pattern raises `global flags not at the start`** on
  3.11. This crashed a whole stage **at import**.
- Repeated capture groups retain only the last repetition.
- `canon_work_key` strips non-alphanumerics, so synthetic test keys **must be
  zero-padded**: `w1-11` and `w11-1` both canonicalise to `101w111`.
- **A compound unit needs its joiner in the pattern.** `_QTY`'s trailing
  `(?![\w\-/])` made `1.5 mA/cm2` match `mA`, hit the `/`, and reject the
  **whole quantity**. Slash and "per" forms never converted.
- **A missing unit does not degrade gracefully.** `uW` was absent from the
  units table, so the unknown token broke the run and the neighbouring `cm2`
  stayed flat — and G9a reported the **neighbour**, not the cause.

### 12.3 Patching discipline

> **After any patch, grep for the NEW text to prove it landed. After two
> failures on one anchor, rewrite the enclosing function.** The assertion
> fires *before* the file write, so a "successful" run can leave the file
> untouched.

**Do not use shell heredocs for Python edits.** Escaped newlines inside a
heredoc produced `SyntaxError: unterminated string literal` in two files, and
a third heredoc patch failed its own assertion silently while leaving the file
unchanged. Use a patch tool with exact-match anchors, and **run the test suite
after every mechanical edit**, not only after logic changes.

### 12.4 Dependencies

```
pymupdf langdetect rapidfuzz matplotlib requests pyyaml pytest
pandoc 3.11+   tectonic   agy   opencode
```

LaTeX packages in `config/tex/manuscript_head.tex`: `graphicx`, `float`,
`caption`, `etoolbox`, **`siunitx`**, **`mhchem` (version=4, pinned)**.

> **Anything the build cannot run without belongs under version control.**

---

## 13. Known limitations, stated plainly

1. **No validated detector.** Every audit rate is a lower bound. Highest-value
   human task.
2. **Composition axis under-selected.** 3,311 corpus works (42.5%) yielded
   only 30 depth papers (6.7%). Its mechanism-centrality scores average 0.039
   against 0.139 for defects, so `axes.yaml`'s composition keywords may be
   matching a shallow pile. **Documented, not silently corrected** — tuning
   the selector after seeing the distribution is uncomfortably close to
   fitting the generator to a preferred outcome. Fixing the keywords is a free
   `s04_10` re-run.
3. **`bare anion: F-, I-`** sits in G9a's `ambiguous_for_human_review`. The
   converter refuses to guess whether `I-` is iodide or a hyphenated fragment.
   A flagged ambiguity beats a wrong guess.
4. **60 of 891 venues carry no citation percentile** (6.7%). They score 0 and
   can enter the depth tier only through mechanism centrality.
5. **G8 untested at yearly scale.** Cold start; thresholds are assumed until
   the second issue measures them.
6. **`prior_closing_block()` not ported.** §7.7.

---

## 14. Version history

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-09-08 | first yearly handbook. Aggregate-twelve-monthly-runs design |
| 2.0 | 2026-09-09 | BACKFILL mode. §1 inverted with measurements; Jan-1 artefact gated; S2 demoted; model boundaries written down |
| **3.0** | **2026-09-10** | **Written after the 2025 issue shipped.** All figures measured, not projected. Adds: the silent batch-parse hole and its three-layer fix (§4.3); field-survival rule (§4.4); junction-class figure split (§8.1); the orphaned-figure bug and why two gates missed it (§8.3); log-axis tick control (§8.2 r7); the one legitimate band widening and its paired gate (§9.3); SI citation-form counting (§10.4); the `.env` path bug (§12.1); compound-unit joiners and missing-unit cascade (§12.2); heredoc patching prohibition (§12.3) |

---

## Appendix A. Configuration reference

`config/yearly.yaml`

| Key | Value | Used by |
|---|---|---|
| `yearly.count_band` | `[4500, 9500]` | harvest assertion |
| `yearly.depth_target` / `depth_band` | 450 / `[350, 550]` | selection |
| `yearly.axis_min_depth` | 25 | per-axis floor |
| `yearly.content_page_band` | `[18, 28]` | G5 — see §9.3 |
| `yearly.total_page_band` | `[28, 45]` | G5 — see §9.3 |
| `citations_yearly.total_band` | `[160, 220]` | G2c |
| `abstract_yearly.word_band` | `[400, 550]` | G3b |
| `novelty_yearly.*` | 0.25 / 0.30 / 0.20 | G8 |
| `plausibility.single_junction_pce_max_pct` | 29.4 | G3c, F1a |
| `plausibility.tandem_2t_pce_max_pct` | 47.6 | G3c, F1b |

The overlay in `s04_10.gates(period)` is **deliberately partial**:
`venue_share_max_pct` (8), `institution_share_max_pct` (10) and
`preprint_share_min_pct` (10) fall through to `gates.yaml` because they are
**proportions of `n_target`** and scale with the pool by themselves.
Re-declaring them would create a second definition of one constraint. A test
asserts they are not zeroed.

## Appendix B. Measurements vs projections

| Quantity | Status |
|---|---|
| 7,931 works; 63.8% usable abstracts | **measured** |
| Jan-1 artefact 1,089 works (13.7%) | **measured** |
| 450 depth from 5,303 eligible; jaccard 0.993 | **measured** |
| 1,655 anchors, all verbatim | **measured** |
| 174 citations; 9,070 words; 35 pages | **measured** |
| pooled audit rates + monthly spreads | **measured** |
| trajectory −0.16 pp; May has no certified value | **measured** |
| 306 single-junction / 81 tandem cards | **measured** |
| extraction 1 h 59 m; draft 1 h 1 m | **measured** |
| S2 gap-fill contribution | **UNRESOLVED** — probe throttled |
| G8 thresholds at yearly scale | **assumed** |
| audit-rate precision | **unknown** — no validation set |
