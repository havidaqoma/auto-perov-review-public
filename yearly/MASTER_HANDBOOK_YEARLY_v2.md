# Master Handbook: Autonomous **Yearly** Review Paper Production

**Version 2 (device-class spine) · 2026-09-10 · Havid Aqoma**
**Supersedes the mechanism-axis spine of v3.0 for the BODY only.**

Reference implementation: `perovskite_pv_yearly`
Sibling projects, working and **not to be modified**:
- `auto-perov-review` — the monthly pipeline (source of every reused module)
- `manuscript\2026-H1_v4` — the six-month issue

> **Naming note.** This file is `MASTER_HANDBOOK_YEARLY_v2.md`. The earlier
> `MASTER_HANDBOOK_YEARLY.md` (v3.0) is deliberately left in place and
> untouched. v3.0 documents the mechanism-axis spine, which is still the
> correct design for a monthly issue and is still the fallback if a year's
> device mass is too thin. Read v3.0 for anything this file marks *inherited*.

---

## 0. Read this first

You are an autonomous agent. Your job is to produce **one yearly review paper**
of perovskite photovoltaics from a year's literature, as **two PDFs plus a
raw-data pack**, with every number traceable to a verbatim quotation from a
cited paper's own abstract.

**This handbook has produced a shipped artifact.** Every number below is a
measurement taken from the 2025 issue after it built. Where something is a
projection it says so.

### 0.1 What the 2025 issue actually produced

Reproduce this or better:

| Artifact | Measured |
|---|---|
| `manuscript_yearly.pdf` | **36 pages** (24.6 content), 9,198 words, **170 citations** |
| Abstract | 484 words, zero digits, zero citation markers |
| `supplementary_yearly.pdf` | **4 pages**, 8 notes, cites 170 of 170 references |
| `fig/` | **8 plates** (F1a, F1b, F2, F3a, F3b, F4, F5, F6) |
| Main-text tables | **3** (T1 champions, T2 reporting, T3 evidence ledger) |
| `data/` | **17 CSV files** + `claim_cards.jsonl` |
| Gates | **20 total: 19 pass, 1 cold-start, 0 fail** |
| Anchor verification | **1,655 anchors, 1,655 verbatim, 0 defects** |
| Corpus | 7,931 works → 7,794 in scope → 450 read closely |
| Section map | sha `2382b7c2c99a0970`, cite_sum 162 |
| Tests | 82 passing, no network |
| Wall clock | harvest ~15 m · extraction 1 h 59 m · draft ~50 m · build ~3 m |

Title, generated from the year's own evidence mass:
> *Perovskite Photovoltaics in 2025: Defect passivation, interface and contact engineering*

### 0.2 The seven principles

1. **Format is generated, never model-written.**
2. **Every defect becomes a gate, never a prompt reminder.**
3. **Verify the artifact, not the process.** Parse the rendered PDF.
4. **No prose reaching a reader may be authored outside the evidence chain**,
   including by a script.
5. **A generator and its gate must be mutually consistent.** When the two
   collide, the **generator** moves. This fired **four times** in this
   project; §6.4 lists all four.
6. **Never widen a gate to make output pass.** One narrow exception exists
   (§9.3). Read it before considering a second.
7. **A gate that stops noticing something is worse than no gate.**

### 0.3 The eighth principle, earned this cycle

> **8. An artifact that exists is not an artifact that shipped. Every check
> must ask "did it reach the reader?", never "was it built?"**

This is new, and it is here because **one defect class appeared three times
in two days**:

| Instance | The artifact | What happened |
|---|---|---|
| F1 | rendered PDF plate | copied to the deliverable folder, **never attached to a section** |
| T1–T3 | computed tables | built by `yearly_tables`, imported by the draft, **never rendered** |
| figure/table CSVs | 10 data files | written to `runs/…/figdata`, **never copied into `data/`** |

Every time, the object was on disk. Every check that asked *"was it built?"*
said yes. Two gates were green over the F1 hole — G9c checks that *attached*
figures are unique, G9e checks that files *exist*. Neither asked whether the
manuscript referenced them.

**Write placement gates, not construction gates.** G9e and G9f now do this.

---

## 1. Why a DEVICE-CLASS spine

### 1.1 The reader's question decides the spine

A mechanism spine (defects, interfaces, composition…) is right for a monthly
issue: one month rarely holds enough of any device class to argue about.

Over a year it is wrong, and the test is a reader's question. Ask *"what
happened in tandems in 2025"* and a mechanism-organised review cannot answer:
tandem evidence is scattered across six sections and compared against the
wrong physical bound in each.

Four device sections, sized by measured mass:

| Class | Cards | Section ceiling | Cite target |
|---|---|---|---|
| Single junction | **332** | 2200 | 49 |
| Perovskite/Si and other hybrid tandems | **47** | 1330 | 28 |
| Modules and large-area devices | **43** | 1330 | 25 |
| All-perovskite tandems | **28** | 1330 | 16 |

### 1.2 Perovskite/Si and "other hybrids" are ONE section

The brief listed perovskite/silicon and "other (OPV, CIGS)" as possibly
separate topics. Measured: **17** cards name a silicon subcell, **10** name
CIGS or organic. Split, both sit far below the 25-card floor and each makes a
thin claim. Merged they are a solid 47.

> **Rule: a section's existence is decided by measured mass, not by the
> elegance of the outline. Ask the corpus before drawing the contents page.**

### 1.3 THE TANDEM-KEYWORD TRAP — the most important paragraph here

A first classifier keyed on the word `tandem` anywhere in title, abstract or
anchors. It produced 28 "tandems" whose titles read:

```
Efficient and Moisture Resistant Wide-Bandgap Perovskite Solar Cells...
Grain Boundary Engineering Enables 22.2%-Efficient Inverted Wide-Bandgap
  Perovskite Solar Cells...
Multifunctional Passivator Enables High-Efficient Gas-Quenching Sn-Pb
  Perovskite Solar Cells
```

**None of those built a stack.** Wide-bandgap and Sn-Pb chemistry exists
largely *to serve* tandems, so the word saturates single-junction papers that
merely name tandems as motivation.

Counted as tandems, those **18 cards** (measured, after the fix) would have:

- inflated the tandem sections by roughly a third
- placed single-junction efficiencies under a heading where a reader compares
  them against **47.6%** instead of **29.4%**

That is the misattribution defect — a real number describing the wrong device
— applied to an entire section rather than one value.

**The rule.** A device class is claimed only by evidence the DEVICE WAS BUILT:

- an explicit stack (`perovskite/silicon tandem`, `all-perovskite tandem`)
- a terminal count (`two-terminal`, `4-T`, `monolithically integrated`)
- a named partner absorber as a subcell (Si, CIGS, organic, CdTe)
- the extracted `architecture` field, which guard 5 already reconciled
  against the value's own anchor

The bare word `tandem` **never** claims a card. Neither does `wide-bandgap`
nor `Sn-Pb`: both describe a *composition*, not a device.

### 1.4 The anchor decides, not the title

Three cards looked misassigned on their titles. All three were correct, and
the **anchor** was decisive:

| Title says | Anchor says | Class |
|---|---|---|
| "Wide-Bandgap Perovskite **Solar Cells**" | *"four-terminal **all-perovskite tandem** reaches 28.71%"* | ALLPK ✓ |
| "Flexible Perovskite **Photovoltaics**" | *"25 cm2 **module** devices reach 20%"* | MODULE ✓ |
| "passivation agent for tandem solar cells" | *"four-terminal **perovskite/silicon**, 31.02%"* | HYBRID ✓ |

> **A paper's title describes the paper. The anchor describes the number.**
> This is guard 4 applied to section assignment.

### 1.5 Section mass counts ALL cards; figures stay filtered

All-perovskite has 28 cards but only 24 with `lens == experimental`. The lens
filter exists to keep simulation off **measured figures**. It is not a
membership rule: a drift-diffusion study of an all-perovskite stack is
legitimately *discussed* in that section; it simply cannot have its computed
value plotted beside certified hardware.

Conflating the two would drop a real section below its floor for the wrong
reason.

### 1.6 Classification precedence is fixed and load-bearing

Classes overlap in reality, so order decides ownership:

1. **MODULE first.** An all-perovskite tandem mini-module belongs in the
   module section: its argument is area and uniformity, not junction physics.
2. **HYBRID before ALLPK.** "Perovskite/silicon" is unambiguous.
3. **ALLPK next.**
4. **Generic two-terminal device language → HYBRID**, because an unspecified
   stack is far more often silicon-partnered in this corpus.
5. **SINGLE is the default.** Tandem *motivation* language lands here, which
   is the correct home for a wide-bandgap top-cell study.

---

## 2. Inherited from v3.0 without change

Read v3.0 for the detail. These are **not** restated here and are **not**
optional:

| Topic | v3.0 § |
|---|---|
| Backfill mode: one annual sweep, not twelve monthly runs | §1.1 |
| Cost model: harvest is free, only extraction and draft cost tokens | §1.2 |
| Abstract-first is a decision, not a compromise (63.8% coverage) | §1.3 |
| The January lumping artefact and `date_precision` | §1.4 |
| Duplicate semantics are inverted in a single sweep | §1.5 |
| OpenAlex primary, S2 best-effort, a 429 never fails a build | §2.1 |
| **Models never perform retrieval or transcription** | §2.2 |
| Provenance from records, never live config | §2.3 |
| The five guards and their fixed order | §4.1 |
| `verify_anchors.py` is mandatory and shares no code with extraction | §4.2 |
| The silent batch-parse hole and its three-layer fix | §4.3 |
| Fields must survive `normalize()` | §4.4 |
| Pooled rates, never the mean of twelve monthly rates | §5.1 |
| Simulation never reaches the measured frontier | §5.4 |
| Year-over-year is a cold start and must stay one | §5.5 |
| The cache trap: prompt edits do not change the map sha | §6.5 |
| Never dictate phrasing to the writer | §7.4 |
| The abstract contract: no digits, no citations, named tokens | §7.5 |
| Backfill disclosure in intro and abstract | §7.6 |
| Windows, Python and patching specifics | §12 |

---

## 3. Repository layout

```
MASTER_HANDBOOK_YEARLY_v2.md   this contract (device spine)
MASTER_HANDBOOK_YEARLY.md      v3.0, mechanism spine, still valid
config/
  yearly.yaml                  yearly bands (NEW keys)
  gates.yaml                   MONTHLY bands, never read for a yearly envelope
  axes.yaml exclude.yaml title_terms.yaml venue_whitelist.yaml models.yaml
  tex/manuscript_head.tex      TRACKED: siunitx + mhchem(version=4)
scripts/
  run_yearly.py                unattended runner
  verify_anchors.py            MANDATORY gate
  verify_pdf.py verify_notation_pdf.py
  common/                      net env titles ledger doi dates csvio cleaners
  stages/
    s01_harvest_yearly.py      ONE annual sweep + date_precision
    s02_06.py                  scope, dedupe, mechanism labels
    s04_10.py                  venues, depth selection, audit flags
    s09_cards.py               [LLM] extraction, the only paid harvest stage
    device_class.py            NEW: one card -> one device class
    yearly_corpus.py           annual corpus + cards, month-sliced
    yearly_audit.py            twelve-point audit series
    yearly_stats.py            POOLED rates + trajectory + YoY
    yearly_device_map.py       NEW: 9-section map, device-class body
    yearly_section_map.py      v3.0 mechanism map, kept as fallback
    yearly_tables.py           NEW: T1/T2/T3 + their CSVs
    s11y_figures_yearly.py     8 plates + per-figure CSV
    s13y_draft_yearly.py       [LLM] 5-phase draft
    s18y_build_yearly.py       assemble, 20 gates, PDF
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
python scripts/stages/s09_cards.py            $Y    # PAID
python scripts/verify_anchors.py              $Y    # MANDATORY, must exit 0
python scripts/stages/yearly_corpus.py        $Y --partial
python scripts/stages/yearly_stats.py         $Y --partial
python scripts/stages/yearly_device_map.py    $Y --partial   # DEVICE spine
python scripts/stages/yearly_tables.py        $Y --partial   # free
python scripts/stages/s11y_figures_yearly.py  $Y    # free
python scripts/stages/s13y_draft_yearly.py    $Y    # PAID
python scripts/stages/s18y_build_yearly.py    $Y
python scripts/stages/s19y_si_yearly.py       $Y
```

**`--partial` is correct and is not a compromise.** All twelve months are
present; the flag relaxes only the "twelve run directories exist" check,
which cannot apply to a single-sweep harvest. G11 independently asserts
`n_months == 12`.

---

## 4. The section map

`yearly_device_map.py`. Nothing is typed in: titles, ceilings and citation
targets all fall out of measured card mass.

### 4.1 Spine. `gaps` is ALWAYS last, asserted in code

| # | Role | Ceiling | Cites | Job |
|---|---|---|---|---|
| 1 | `intro` | 700 | 0 | locate the open problem |
| 2 | `trajectory` | 900 | 18 | **what changed across twelve months** |
| 3–6 | `device` ×4 | 1330–2200 | 16–49 | **one device class each** |
| 7 | `synthesis` | 900 | 10 | **what the classes share** |
| 8 | `audit` | 700 | 7 | reporting practice |
| 9 | `gaps` | 900 | 9 | what to measure differently |

`trajectory` and `synthesis` are the two roles a monthly issue cannot have.
**Without `synthesis`, a yearly issue is four device reviews stapled
together.**

### 4.2 Knobs

| Knob | Value | Reason |
|---|---|---|
| `DEVICE_MIN_WORDS` | 900 | below this a device section cannot argue |
| `DEVICE_MAX_WORDS` | **2200** | raised from 1500; see §6.4 instance 3 |
| `WORDS_PER_CITE` | 45 | unchanged from the mechanism map |
| `POOL_CITE_FRACTION` | **0.60** | see §6.4 instance 4 — this one cost a failed draft |
| `MIN_CLASS_CARDS` | 25 | below this a class folds, never ships thin |
| `CITE_SUM_BAND` | (150, 210) | must leave headroom under G2c's 220 |

### 4.3 Allocation is clamped, then rebalanced deterministically

Single junction carries ~74% of the corpus. Pure proportional allocation
would hand it the whole budget and starve the other three, so every section
is clamped to [900, 2200] and the remainder redistributed **in fixed key
order**. The same mass must always produce the same map, or a resume redrafts
forever.

### 4.4 Folding, not dropping

A class below `MIN_CLASS_CARDS` folds into the nearest larger class
(all-perovskite → hybrid, everything else → single junction). Folding keeps
its papers reachable by the writer; dropping would delete evidence. On 2025
nothing folded.

---

## 5. Drafting

Five phases, unchanged from v3.0 §7.1. The **device** branch replaces the
mechanism branch in Phase A.

### 5.1 Each device section gets its OWN evidence pool

```python
pool = [c for c in cards if classify(c, abstracts[c["work_key"]]) == dev]
ev   = evidence_for(pool)          # NOT evidence(cards, axes)
```

A tandem section fed single-junction cards would invite the writer to compare
a 26% single cell against a 33% stack as though they were rivals.

`evidence_for()` takes an explicit card list rather than an axis list, so
**membership has exactly one definition** — the classifier. Letting the draft
re-derive membership would let it drift from the section map.

Pool depth is 60 entries (up from 46): a 2200-word section with a 49-citation
target needs a pool deeper than its target, or the writer cannot select.

### 5.2 Each section carries its own physical bound into the prompt

```
Single junction:  bounded at 29.4% by Shockley-Queisser for a 1.55 eV
                  absorber. Papers here that discuss tandems as a future
                  application are still single-junction studies.
Tandems:          bounded by the two-junction detailed-balance limit of
                  47.6%, NOT the single-junction limit. Do not describe a
                  value below 47.6% as approaching a fundamental ceiling.
```

Plus a standing instruction: *do not compare a value in this section against
a value from another class as though they were competing for the same
record.*

### 5.3 The lens is shown in the evidence block

Every pool entry carries its lens (`experimental` / `theory` / `review`) so
the writer can see which entries are computational and avoid presenting a
simulated value as measured.

---

## 6. Gates

**20 gates. 19 pass, 1 cold-start, 0 fail on the 2025 issue.**

| Gate | Checks |
|---|---|
| G1 | every `[@key]` resolves; 170 resolved, 0 unresolved |
| G2 | body ≤ ceiling×1.15, each section ≤ its ceiling×1.35 |
| G2b | citation numbers monotonic by first appearance |
| G2c | total citations in `[160, 220]`; measured 170 |
| G3 | every abstract numeral traces to stats or a card |
| G3b | abstract 400–550 words, no citation markers |
| G3c | **per-class** physical bounds **and illumination match** |
| G4 | no em-dash, no banned words, **no agent narration** |
| G5 | page bands, measured on the rendered PDF |
| G6 | no "we measured/fabricated" |
| G7 | abbreviations expanded at first use |
| G8 | novelty vs prior issues — **cold-start here** |
| G9a | no flat units or unrendered formulae |
| G9b | every citation marker hyperlinked; 305 links, 0 unlinked |
| G9c | one figure file attaches to at most one section |
| G9d | AI declaration names products, not CLI slugs |
| G9e | **required figures PLACED** |
| **G9f** | **required tables PLACED** — new, §0.3 |
| G10 | title-block spacing, measured on the page |
| G11 | coverage: `n_months == 12`, cards in band |

### 6.1 G3c is per sample class

| Quantity | Bound | Basis |
|---|---|---|
| single-junction PCE | ≤ 29.4% | 1.55 eV Shockley-Queisser |
| 2-terminal tandem PCE | ≤ 47.6% | two-junction detailed balance |
| EQE | ≤ 100% | definitional |
| FF | ≤ 92% | practical ceiling |

G3 asks only *"does this number trace to a card?"*. A monthly issue once said
*"32.95% in single-junction inverted cells"* and 32.95 **did** trace to a
card, so G3 passed it. The number was real; **the device was wrong.**

> **Traceability proves provenance, not meaning.**

G3c also checks ILLUMINATION, because the bound alone is not enough. Every
limit in the table above is derived for the AM1.5G solar spectrum, so a
value measured under indoor light is compared against a ceiling that does
not apply to it — and G3c's device-class selector cannot see that, because
for an indoor single-junction cell the DEVICE CLASS IS CORRECT. The gate
therefore re-opens each substituted abstract value against its own anchor
and fails on any indoor value sitting under a solar bound. See §8.5.

### 6.2 G8 reports `cold-start`, not `pass`

No prior yearly issue exists. **A green G8 would later be misread as evidence
that novelty was checked.**

### 6.3 G9e and G9f measure PLACEMENT

G9f counts rendered `**Table N.**` headers in the manuscript markdown, not
the fact that table objects were constructed. See §0.3.

### 6.4 The generator/gate invariant, all four instances

Every time, the **generator** moved and the gate band was untouched.

| # | Collision | Fix |
|---|---|---|
| 1 | mechanism map: per-section minimums summed 214 vs band top 200 | `WORDS_PER_CITE` 40 → 45 |
| 2 | four device sections summed ~132 vs G2c floor 160 | `DEVICE_MAX_WORDS` 1500 → 2200 |
| 3 | (same event, spine cites retuned) | 18/10/7/9 |
| 4 | **all-perovskite told to cite 30 papers from a pool of 28** | `POOL_CITE_FRACTION` 0.60 |

**Instance 4 is the one that cost real money.** `cite_target` was derived from
the word ceiling alone (`ceiling / 45`) and never consulted the pool. Word
budget and evidence supply are independent quantities, and they diverge worst
for a *thin* class — precisely because the 900-word floor gives it a generous
ceiling when it has the fewest papers.

The writer reached 28, was rejected three times, and the stage failed closed
after three wasted LLM calls. **No model could have passed.**

`POOL_CITE_FRACTION` is 0.60 rather than 1.0 on purpose: the evidence block is
*"a pool to select from, not a checklist"*, so demanding every paper in a
class would force the writer to cite work that does not bear on the problems
it chose to develop — padding, dressed as rigour.

After the fix, every section passed **first attempt**, citing well above
target:

| Section | Target | Achieved |
|---|---|---|
| All-perovskite | 16 | **28** |
| Hybrid tandem | 28 | **43** |
| Module | 25 | **32** |

> **Rule: any target derived from one quantity must be checked against every
> other quantity that bounds it. A word budget cannot know how many papers
> exist.**

### 6.5 What the failed draft proved about the narration filter

During those three rejected attempts the writer emitted:

```
STRIPPED narration: I will check the abstract.
STRIPPED narration: I will wait for the task to finish.     (x5)
STRIPPED narration: I will check the metadata from CrossRef.
```

All stripped by `hygiene.py` before reaching a page. Note the writer narrated
**only on retries against an impossible gate** — narration was a symptom of
the bad target, not an independent fault.

### 6.6 Bands are NEW keys

`config/yearly.yaml` holds every yearly band. `config/gates.yaml` is **never
read for a yearly envelope** and still describes the monthly artifact exactly:
`[12,17]` total, `[8,11]` content. A test asserts the monthly bands are
unchanged **and** that yearly floors sit above monthly ceilings.

---

## 7. Figures

Eight plates. A figure earns main-text space by carrying an argument the prose
cannot make in a sentence.

| Fig | Plot | Argument |
|---|---|---|
| **F1a** | certified vs self-reported, **single junction** | 41 certified, max 26.96%, against the 29.4% line |
| **F1b** | certified vs self-reported, **tandem/module** | 24 certified, max 33.15%, against the 47.6% line |
| **F2** | efficiency vs area, log x | 58 pairs over 0.04–764 cm² |
| **F3a** | effort map, **single junction** | where close reading went |
| **F3b** | effort map, **tandem/module** | same question for stacks |
| **F4** | stability evidence in full | **15 T80 values, 24 protocol labels of 450** |
| **F5** | frontier trajectory, 12 points | whether the frontier moved |
| **F6** | audit trajectory, 6 rates | whether reporting practice improved |

### 7.1 Why F1 and F3 are split by junction class

| | Single junction | Tandem/module |
|---|---|---|
| cards | 306 | 81 |
| certified | 41, max **26.96%** | 24, max **33.15%** |

Two populations, **two different physical ceilings**. Plotted on one axis the
tandem points sat above every single-junction point and a reader could not
tell whether the frontier was a single-junction achievement or a stack. **It
is the misattribution defect in chart form.** Separating the panels is what
lets each carry its own limit line.

Classification imports `_is_single_junction()` from the build, so figure and
gate agree on what a tandem is.

### 7.2 Rules, each from a real defect

1. **Never hard-code a plotted number.**
2. **Simulation never sits on a measured figure** (63 of 450 cards excluded).
3. **Band labels go OUTSIDE the axes frame** (`y=1.02`, `clip_on=False`).
4. **F5 labels every point with its device class.**
5. **A figure with no data is not written.** An empty axes frame looks like a
   finding.
6. **Every plate emits its own CSV**, including exclusions.
7. **Control tick density on log axes.** F4's T80 axis spans 144–3,200 h and
   matplotlib's default decade+minor labels **collided into an unreadable
   smear**. Fix: a small number of explicit ticks at round hours **derived
   from the data range**, minor labels suppressed, integer-only ticks on
   count axes.

### 7.3 Attach by a role the map ACTUALLY emits

F1 was orphaned because its claim was keyed on `role == "frontier"`, carried
over from the monthly spine. **The yearly spine has no `frontier` role.** The
condition never fired.

Under the device spine, attachment keys on `device_class`:

```
trajectory  -> F1a          synthesis -> F5
audit       -> F6           single_junction -> F4, F3a
tandem/alp  -> F1b          hybrid_tandem   -> F3b
module      -> F2
```

Plus a fallback loop that places any still-unattached figure rather than
dropping it.

---

## 8. Main-text tables

`yearly_tables.py`. A table earns space where a reader must **read a specific
value and its provenance** rather than see a shape.

### 8.1 T1 — champions, and why it is the most important table

| Device class | Certified | Self-reported | Limit | n cert |
|---|---|---|---|---|
| Single-junction | 26.96 | 29.11 | **29.4** | 29 |
| All-perovskite | 29.2 | 30.69 | 47.6 | 8 |
| Hybrid tandem | **33.15** | 33.5 | 47.6 | 12 |
| Module | 28.78 | 28.94 | 47.6 | 16 |

Read row 1 alone: single-junction self-reported claims reach 29.11%, just
under that class's own 29.4% ceiling, while **certified** sits at 26.96%.
The gap between the two columns is the issue's central argument, and it is
visible only because certified and self-reported occupy separate columns
with the correct bound beside each.

> **Certified and self-reported never share a cell.** A single "best PCE"
> column silently equates a 0.05 cm² laboratory champion with an
> independently certified result.

**A CORRECTION THIS TABLE ALREADY NEEDED ONCE.** The first version of this
section read *"single-junction self-reported claims reach 33.2%, ABOVE that
class's own 29.4% ceiling"* and called that the issue's central argument.
It was false, and it survived because the handbook was written from the
table rather than from the cards behind it. The 33.2% is an INDOOR
measurement (§8.5). Writing a headline finding straight out of a generated
table, without opening the anchor beneath the number, is how a pipeline
launders its own defect into prose.

### 8.2 T2 — reporting completeness per class

Modules state their area **55.8%** of the time against **7.8%** for single
junctions — unsurprising, since area *is* the module claim. Certification runs
37.2% for modules against 9.0% for single junctions.

Every rate is a **lower bound**: flags read abstracts, and the hand-labelled
validation set does not exist. The caption says so.

### 8.3 T3 — the evidence ledger

Papers, measured vs simulation, extracted values, verified quotations per
class. **This is the table that makes the review auditable rather than
assertable.** `Simulation or review` is reported explicitly, because a section
resting largely on computation is a different claim from one resting on
measured hardware.

### 8.4 Tables are emitted as markdown AND CSV from one computation

So the manuscript and the data pack can never disagree.

---

### 8.5 Illumination: the third form of the misattribution defect

Havid read the first build and asked why a single-junction card reported
above 30%, guessing a tandem or a simulation. **Neither.** Both offending
values were indoor photovoltaics:

```
33.2%  "a record-high PCE of 33.2% ... under WEAK LIGHT ILLUMINATION
        conditions, demonstrating excellent INDOOR PHOTOVOLTAIC performance"
30.3%  "Stable and Efficient INDOOR PHOTOVOLTAICS ... reaches 30.30%"
```

The Shockley-Queisser 29.4% ceiling is derived **for the AM1.5G solar
spectrum**. Under narrow indoor light a wide-gap perovskite legitimately
exceeds it. The numbers are real, the extraction is correct, the device
class is correct — and plotting them against a solar limit line is still
wrong, because they are not the same quantity.

This is the misattribution defect in a **third** form, and the pattern is
now clear enough to state as a rule:

| Form | Wrong dimension | Caught by |
|---|---|---|
| 32.95% tandem labelled single-junction | device class | G3c |
| tandem-motivation papers classed as tandems | device class | §1.3 |
| **indoor PCE against an AM1.5G bound** | **illumination condition** | **G3c illumination check** |

> **Rule: a physical bound is defined for a set of measurement conditions,
> not for a number. Before comparing a value against a limit, verify that
> the value was measured under the conditions the limit assumes.**

#### 8.5a The fix that would have been worse than the bug

The obvious detector asks *"does the anchor mention indoor light?"*. Run on
the real corpus it tagged six values, of which **three were false
positives**:

```
"a 23.7% PCE (22.9% certified) under AM 1.5 G illumination
 and a 42.46% PCE under 1000 lux"        <- 22.9 IS the AM1.5G value
"achieved 21.9% under 1-sun equivalent illumination
 and 42.6% under indoor light"           <- 21.9 IS the 1-sun value
"Under standard sunlight conditions, the devices reach 20.1%"
                                         <- title says indoor, value is not
```

Papers routinely report **both** conditions in one sentence, and the
extractor had correctly taken the solar value each time. A whole-anchor
test would have deleted three legitimate outdoor values while fixing two
indoor ones: a misattribution introduced while repairing a misattribution.

**The illumination condition belongs to THE NUMBER'S OWN LOCAL CONTEXT.**
This is guard 4 taken one level finer: within the quotation, the marker
nearest the value wins, and a marker *after* the value is preferred because
"X% under Y" is how the language works. Titles are advisory only.

#### 8.5b Guard 3 truncation, and what NOT to do about it

The 30.3% anchor stops at exactly 25 words — one word before "lux":

```
anchor : "...PCE of 30.30% and an open-circuit voltage (VOC) of 936 mV
          under 1000"
source : "...936 mV under 1000 lux (3000 K LED)"
```

An anchor-only test returns "unknown" and the value reaches an AM1.5G
figure.

**Do not widen guard 3.** The 25-word cap exists because checking the value
before truncating once shipped five fields whose quotations ended
immediately before their own number.

> **Guard 3 governs what may be QUOTED to a reader. It does not govern what
> the pipeline may KNOW.** The full abstract is on disk and already
> verified, so the illumination condition falls back to the source when the
> anchor is inconclusive. The anchor is consulted FIRST and the source never
> overrides a definite anchor reading, or the whole-abstract false positives
> of §8.5a return.

#### 8.5c An unmarked value is KEPT

`is_indoor_value` is deliberately not `!= AM15`. Standard conditions are the
overwhelming default in this literature, so treating "unmarked" as indoor
would silently drop most of the corpus from every performance figure.

Measured effect of the whole fix: **2 values excluded** from F1a/F1b and T1,
`n_values_excluded_indoor` recorded per class in the T1 CSV, and the
single-junction self-reported figure corrected from 33.2% to 29.11%.

## 9. Supplementary Information and the data pack

`s19y_si_yearly.py`. **No LLM runs in this stage** — a method described by a
model is a method nobody verified.

### 9.1 Eight notes, all script-composed

S1 corpus and selection **with the retrospective-assembly disclosure** ·
S2 date precision and the Jan-1 artefact · S3 the five guards plus
re-verification counts · S4 the audit with pooled rates **and** monthly
spread · S5 the twelve-point trajectory · S6 limitations · S7 the gate table ·
S8 reproduction, citation count, map fingerprint.

### 9.2 Count citations in BOTH marker forms

The SI first reported **"cites 0 of 174 references"** — a false statement
about the manuscript, in the document whose job is to describe it. The build
wraps citations as `[\href{https://doi.org/…}{12}]` and the counter looked
only for plain `[12]`. It found **zero** in a body carrying **312**.

Count the linked form first, then any surviving plain form. The nomenclature
guard applies to both: `[60]fullerene` and `[100] growth` are not citations,
and any bracketed number above `n_refs` cannot be one.

### 9.3 The data pack — 17 files

| File | Contents |
|---|---|
| `corpus_metadata.csv` | every work in scope, with `date_precision`, `source_month` |
| `extracted_claims.csv` | **one row per number, each with its VERBATIM QUOTATION** |
| `device_class_distribution.csv` | **new**: papers, measured, simulation per class |
| `axis_distribution.csv` | mechanism axes, kept for **selection** provenance |
| `monthly_series.csv` | per-month per-quantity series |
| `frontier_trajectory.csv` | per-month leading value **with device class** |
| `reporting_audit.csv` | rates **with denominators**, precision "not validated" |
| `figure*.csv` ×7 | one per plate, including exclusions |
| `table*.csv` ×3 | T1, T2, T3 |
| `claim_cards.jsonl` | the full extraction record |

`extracted_claims.csv` is the important one. **The verbatim column is what
makes the audit checkable rather than assertable.**

The mechanism-axis table is retained even though the body no longer uses it:
selection still scores on axis centrality, and a reader auditing the
**selection** needs it. It no longer describes the manuscript's structure.

---

## 10. Checklist

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
[ ] 11. verify_anchors.py exits 0                        MANDATORY
[ ] 12. device map: check cite_target <= 0.6 x class pool for EVERY section
[ ] 13. tables: T1/T2/T3 build and their CSVs exist
[ ] 13a. T1: check n_values_excluded_indoor per class, and open the
         anchor behind any value within 1 pp of its own bound
[ ] 14. figures: 8 plates, none skipped, each with a CSV
[ ] 15. draft: watch for "STRIPPED narration" and REJECT lines
[ ] 16. build: ALL GATES PASS; G8 cold-start acceptable, fail is not
[ ] 17. check for ORPHANED figures and UNRENDERED tables
[ ] 18. SI: cited_in_main_text must equal references_listed
[ ] 19. data pack: 17 files, including every figure and table CSV
[ ] 20. rendered-PDF verification, incl. span-geometry notation
[ ] 21. HUMAN: READ THE PDF
[ ] 22. commit code fixes and artifacts separately
```

### 10.1 Why step 21 cannot be automated

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

Read the **device sections and T1 first**: that is where this handbook's own
analysis says the novel failure modes live.

---

## 11. Known limitations, stated plainly

1. **No validated detector.** Every audit rate is a lower bound. This is the
   highest-value outstanding human task.
2. **Composition under-selected.** 3,311 corpus works (42.5%) yielded 30
   depth papers (6.7%); its mechanism-centrality averages 0.039 against 0.139
   for defects. **Documented, not silently corrected** — tuning the selector
   after seeing the distribution is close to fitting the generator to a
   preferred outcome. Fixing the keywords is a free `s04_10` re-run. Note the
   device spine reduces the impact, since composition is no longer a section.
3. **`bare anion: Cl-, I-`** sits in G9a's `ambiguous_for_human_review`. The
   converter refuses to guess whether `I-` is iodide or a hyphenated
   fragment. A flagged ambiguity beats a wrong guess.
4. **60 of 891 venues carry no citation percentile** (6.7%).
5. **G8 untested at yearly scale.** Cold start; thresholds assumed until the
   second issue measures them.
6. **`prior_closing_block()` not ported.** Port it when the second yearly
   issue is written, or issue N+1 will not be shown issue N's actual closing
   text.
7. **Illumination detection is regex-based and unvalidated.** Six values
   were reviewed by hand on the 2025 corpus and the three false positives
   were the reason the local-context rule exists (§8.5a). Three checked
   cases are not a validation set. `unknown` defaults to KEPT, so the
   failure mode is an indoor value slipping onto a solar figure, not a
   solar value being deleted.
8. **Device classification is regex-based and unvalidated.** §1.3's trap is
   fixed and spot-checked on three cards, but no hand-labelled set exists.
   The 18 tandem-motivation cards are reported in the SI so the exclusion is
   visible.

---

## 12. Version history

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-09-08 | first yearly handbook. Aggregate-twelve-monthly-runs design |
| 2.0 | 2026-09-09 | BACKFILL mode. §1 inverted with measurements |
| 3.0 | 2026-09-10 | written after the 2025 issue shipped; mechanism spine |
| **v2 (this file)** | **2026-09-10** | **DEVICE-CLASS SPINE.** Four device sections replace six mechanism sections. Adds `device_class.py` with the tandem-keyword trap (§1.3), `yearly_device_map.py`, `yearly_tables.py` with T1–T3 (§8), G9f-tables-present, `POOL_CITE_FRACTION` after a failed draft (§6.4 instance 4), the eighth principle on placement vs construction (§0.3), and the Anthropic AI for Science acknowledgement |
| **v2.1** | **2026-09-11** | **Illumination fix.** Havid challenged a >30% single-junction PCE; not a tandem and not a simulation, but two INDOOR measurements compared against an AM1.5G bound. Adds `illumination_of` / `is_indoor_value` (local context, plus a source fallback past guard-3 truncation), the G3c illumination check, exclusion from F1a/F1b and T1, and §8.5. Corrects §8.1, which had stated the false comparison as the issue's central finding. Also folds U+03BC to U+00B5 in `_normalise`: one Greek mu passed all 20 gates and then killed the render. |

---

## Appendix A. Configuration reference

| Key | Value | Used by |
|---|---|---|
| `yearly.count_band` | `[4500, 9500]` | harvest assertion |
| `yearly.depth_target` / `depth_band` | 450 / `[350, 550]` | selection |
| `yearly.axis_min_depth` | 25 | per-axis floor (selection) |
| `yearly.content_page_band` | `[18, 28]` | G5 |
| `yearly.total_page_band` | `[28, 45]` | G5 |
| `citations_yearly.total_band` | `[160, 220]` | G2c |
| `abstract_yearly.word_band` | `[400, 550]` | G3b |
| `plausibility.single_junction_pce_max_pct` | 29.4 | G3c, F1a, T1 |
| `plausibility.tandem_2t_pce_max_pct` | 47.6 | G3c, F1b, T1 |

Device-map knobs live in `yearly_device_map.py` (§4.2), not in YAML, because
they are coupled to the allocation algorithm and must move together.

## Appendix B. Measurements vs projections

| Quantity | Status |
|---|---|
| 7,931 works; 63.8% usable abstracts | **measured** |
| device mass 332 / 47 / 43 / 28 | **measured** |
| 18 tandem-motivation cards kept in single junction | **measured** |
| 1,655 anchors, all verbatim | **measured** |
| 170 citations; 9,198 words; 36 pages | **measured** |
| T1/T2/T3 values | **measured** |
| pooled audit rates + monthly spreads | **measured** |
| extraction 1 h 59 m; draft ~50 m | **measured** |
| device classification precision | **UNKNOWN** — no labelled set |
| 2 indoor values excluded; T1 single-junction 33.2 -> 29.11 | **measured** |
| illumination detection precision | **UNKNOWN** — 6 hand-reviewed, no labelled set |
| S2 gap-fill contribution | **UNRESOLVED** — probe throttled |
| G8 thresholds at yearly scale | **assumed** |
| audit-rate precision | **unknown** — no validation set |
