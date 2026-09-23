# Master Handbook: Half-Year (H1/H2) Review Paper Production

**Version 2.0 · 2026-09-10 · Havid Aqoma**

Complete specification for producing one **half-year** review paper with
verified numbers and a controlled format. Operating contract for the period
edition: if this file and the code disagree, that is a defect in one of them and
must be resolved before the run.

Companion to `MASTER_HANDBOOK.md`, which specifies the **monthly** issue. Read
that first. This records only what is DIFFERENT, plus the defects that appear
only at period scale.

Reference implementation: `auto-perov-review`

| Issue | Structure | Built | Result |
|---|---|---|---|
| 2026-H1 **v1** | mechanism axes | 2026-09-09 | 3328 works → 36 pp, 209 citations, 17/17 gates |
| **2026-H1 v5** | **device family** | **2026-09-10** | **34 pp, 184 citations, 4 tables, 17/17 gates** |

**v5 is the current structure.** v1 is retained and reproducible.

### Why the version is v5 and not v2

The device-family edition was first built as "v2" and renamed on Havid's
instruction (2026-09-10): *"there is some confusion in the version, so to
standardize, maybe make all the newest to v5 (instead of v2, because the latest
version is v4)"*.

He was right. The monthly pipeline is at v4, so a structure that is strictly
newer must not carry a lower number. **A version number that decreases over
time is a documentation defect** that costs every future reader real time.

`scripts/rename_v2_to_v5.py` performed the move and asserts what must NOT move:
`s11b_figures_v2.py` is a MONTHLY stage whose "v2" means the second generation
of the monthly figure set. Renaming it would break the monthly chain.

> **Rule: version numbers are global and monotonic. Before adding one, check
> what the highest existing number is anywhere in the repo.**

---

## 0. The rules that produced this artifact

The five principles of the monthly handbook (§0.1-0.5) apply **unchanged**.
Format is generated never model-written; every defect becomes a gate; verify the
artifact not the process; no prose reaching a reader is authored outside the
evidence chain; a generator and its gate must be mutually consistent.

Six more earned their place at period scale.

### 0.6 Extend by ADAPTER, never fork

`s18d_build_v4.py` is 1116 lines carrying all seventeen gates, the citation
merge/link ordering, the abstract placeholder boundary, the notation pass and
the title grammar. `s19`/`s20`/`s21` carry the SI, the ChemRxiv contract and the
token discipline.

**None was copied.** Both H1 structures make their run directory satisfy those
contracts and rebind the handful of names the stages resolve at call time.

The monthly handbook records the divergent-copy failure **three times** (§7.6
#10 the narration filter in three copies with the build-side copy narrowest,
which put "I have launched the search command" into a shipped PDF; §7.6 #12 the
citation regex applied in only one consumer). A guard that exists twice
diverges. A fork of an 1116-line build stage is 17 guards existing twice.

> **Rule: if a period edition needs different behaviour from a stage, rebind the
> name. If three stages need the same new behaviour, extract ONE module and
> import it from all three.**

That clause is not hypothetical. The v5 title was first defined inline in
`h1_build_v5.py`; the moment `s19` needed a title it would have become a second
copy and `s20` a third. It is now module-level and imported by both.

### 0.7 A period edition must answer what a single month cannot

If the half-year issue is six monthly issues stapled together it is not worth
writing. `month` is therefore a first-class dimension in `stats.json`
(`series.*`, `frontier.*_series`, `coverage.*`, `family.month_matrix`), the
section map gains **trajectory**/**synthesis** roles, and one figure (T1) exists
solely to carry the six-point series.

### 0.8 A period title is a claim about coverage, and must be gated

June indexes better than January (monthly §3.4: an older month retrieves
WORSE). Left alone, a "January-June" issue silently becomes a May-June review
wearing a six-month label. `config/h1.yaml` sets
`month_min_citation_share_pct: 8.0`; measured on 2026-H1: **12.6%** against even
representation of 16.7%.

### 0.9 Fixing the reported site is not fixing the bug

Every period defect so far was the same bug in two or more places:

- `shutil.rmtree` refused `draft_v4/` with WinError 5; the identical call for
  `.h1_config/` was three functions away.
- The audit-key alias was patched into `h1_build`; `s19` needed it too.
- The illumination guard was added to `family_block()`; `area_ladder()` computed
  the same quantity by a second path and still printed the indoor value.
- The family-contradiction guard was added to `champion_of()`; `family_block()`
  still reported the contradicted value as `top_certified`.

> **Rule: when you fix a bug, grep for its class before moving on. Then grep for
> every other consumer of the quantity you just corrected.**

### 0.10 A number means nothing without its measurement conditions

The single hardest-won rule of the v5 cycle, and the one with the widest reach.

Every guard before it asked **what device** (`anchor_contradicts_family`) or
**how verified** (G3c, `measured()`). None asked **under what illumination**.
So a real, experimental, correctly-labelled single-junction cell reporting
**44.36%** reached Table 1 (§7.11).

Device, verification, area, illumination: a headline number needs all four, and
each is a separate axis that must be checked separately.

### 0.11 Excluded is not the same as erased

When a value cannot be compared, it must leave the tables and figures **and**
stay in the prose. Havid's instruction (2026-09-10): *"the indoor PV is exclude
in plot and table, but still discuss."*

The two halves fail in opposite directions. In a table an indoor PCE sits in a
column of one-sun records with no room to caveat it, and a reader concludes
single junctions beat tandems. Deleting it entirely misrepresents the literature
the other way: indoor PV is a real and growing subfield with four papers in this
corpus. **In prose the condition travels with the number in the same sentence**,
so the work is reported without being compared to something it cannot be
compared with.

---

## 1. Pipeline architecture

The H1 edition is an **AGGREGATOR**, not a harvest. It unions monthly runs that
already exist, re-extracts nothing, and adds a period layer.

```
      MONTHLY CHAIN (unchanged, once per month)
      s01 → s02_06 → s04_10 → s09_cards → verify_anchors
                          │
                          ▼  six anchor-verified monthly runs
      ─────────────────────────────────────────────────────
      SHARED PERIOD LAYER
      h1_aggregate     union 6 runs, membership+bibliography join
      h1_stats         pooled rates, month series, coverage
      h1_family_stats  device-family cuts, guarded (v5)
      h1_tables        5 generated tables (v5)
      h1_figures       T1 trajectory + F1-F4 + S1
      ─────────────────────────────────────────────────────
      v1 (mechanism)              v5 (device family)  ← CURRENT
      h1_section_map              h1_section_map_v5
      h1_draft                    h1_draft_v5
      h1_build      ─┐            h1_build_v5      ─┐
      h1_finalize   ─┴→ ADAPTER → h1_finalize_v5   ─┴→ ADAPTER →
                        real s18d/s19/s20/s21, all 17 gates
```

### 1.1 Run commands, in order

```bash
cd auto-perov-review

# 0. every month in the window must exist and be anchor-verified FIRST
python scripts/run_h1_backfill.py 2026-02 2026-03 2026-04 2026-05
python scripts/h1_harvest_january.py          # special window, §3.2
python scripts/stages/s02_06.py    2026-01
python scripts/stages/s04_10.py    2026-01
python scripts/stages/s09_cards.py 2026-01
python scripts/verify_anchors.py   2026-01    # MANDATORY, must exit 0

# 1. shared period layer
python scripts/stages/h1_aggregate.py         # ~20 s
python scripts/stages/h1_stats.py             # ~10 s
python scripts/stages/h1_family_stats.py      # ~10 s, v5
python scripts/stages/h1_figures.py           # ~30 s
python scripts/stages/h1_tables.py            # ~5 s,  v5

# 2. v5 device-family edition
python scripts/stages/h1_section_map_v5.py    # ~2 s
python scripts/stages/h1_draft_v5.py          # LLM, ~55 min
python scripts/stages/h1_build_v5.py          # gates + PDF
python scripts/stages/h1_finalize_v5.py all   # SI + ChemRxiv + tokens
```

`h1_draft_v5.py` takes trailing section ids to redraft only those:
`python scripts/stages/h1_draft_v5.py 3 6`.

### 1.2 Isolation test for a new agent

```bash
grep -rn "H1\|h1_\|v5" scripts/stages/s0*.py scripts/stages/s1*.py
```

Must return nothing but `s11b_figures_v2` self-references. If a monthly stage
mentions the period edition, isolation has been broken.

---

## 2. Environment defects

### 2.1 The `.env` path bug — affects the MONTHLY pipeline too

**Highest-value finding of the whole H1 programme, and not about H1 at all.**

`scripts/common/env.py` computed `ROOT = parents[1]`, which from
`scripts/common/env.py` is **`scripts/`**. It looked for `scripts/.env`; the real
file is at the repo root. `OPENALEX_API_KEY` was never loaded, so **every
OpenAlex request in the entire pipeline, monthly included, ran anonymous** on the
shared throttled pool.

Presentation: a harvest that produced an empty `private/` directory, wrote
nothing for ten minutes, printed nothing. Not an error — the keyed client retries
429 with backoff, so the stage sat in backoff indefinitely.

Found by a stepwise probe printing `key_len` at each import:

```
BEFORE: env import 0.0s key_len=0    → 429, then silent backoff
AFTER : env import 0.0s key_len=22   → COUNT=511 in 1.0s
```

> **Rule: a credential that fails to load does not raise. It downgrades you to
> an anonymous tier and the symptom arrives hours later as a hang. Assert the
> KEY IS PRESENT, never that the file was found.**

### 2.2 Buffered stdout hides whether a stage is alive

`python foo.py > log` buffers; the log sat at 44 bytes while the stage appeared
frozen. **Always `python -u`** for any long stage.

### 2.3 Windows: never `rmtree` a directory you will recreate

`shutil.rmtree` raised `WinError 5` on an EMPTY directory left by a crashed
build — a stale handle outlives the process. Both sites now sync file-by-file
with `copytree(..., dirs_exist_ok=True)`.

### 2.4 An exit code from a shell chain is the LAST command's

A job reported exit 1; the log showed `rc=0`. The 1 came from a trailing
`grep -c` that exits 1 on zero matches, and zero matches was the desired result.
**Read the log, not the exit code, when the command is a chain.**

---

## 3. The corpus

### 3.1 Always dry-run the per-month counts first

`scripts/probe_h1_counts.py` is read-only and imports `FILTER` verbatim from
`s01_harvest` so it can never drift from the real query.

| Month | Count | In monthly band [250,1200]? |
|---|---|---|
| **2026-01** | **1311** | **NO — fails closed** |
| 2026-02 | 511 | yes |
| 2026-03 | 569 | yes |
| 2026-04 | 611 | yes |
| 2026-05 | 595 | yes |
| 2026-06 | 644 | yes |

### 3.2 January: the year-only indexing placeholder

```
2026-01-01 .. 2026-01-01   →  823      ← 63% of the month, on ONE day
2026-01-02 .. 2026-01-31   →  488
```

`2026-01-01` is what OpenAlex stamps on a work indexed with **year-only
precision**. A 25-work sample confirmed real, in-scope papers in strong venues
(EES, Nature Photonics, Science, Chem Soc Rev): a **date-precision** problem, not
a relevance problem.

**Decision: January is harvested as `2026-01-02 .. 2026-01-31` (488 works).**
An issue titled "January-June 2026" may not assert a month the record cannot
support. Implemented in `scripts/h1_harvest_january.py` by rebinding
`month_bounds` in the `s01_harvest` namespace for that process only — **zero
edits to any monthly file**. See `docs/H1_JANUARY_DATE_DECISION.md`.

> **Generalise: before harvesting any period, split the FIRST month by day. A
> single day holding >20% of a month is an indexing artifact, not a surge.**

### 3.3 The aggregation join: membership vs bibliography

Two files carry two different facts and BOTH are needed:

| File | Contains | Missing |
|---|---|---|
| `05_corpus.jsonl` | doi, title, venue, date | pre-scope-filter, 86 works too many |
| `06_labels.jsonl` | axis, lens, `n_kept` = monthly `corpus.n` | **no bibliographic fields at all** |

- **05 alone**: corpus 3414 vs the monthly issues' 3328 — an 86-work inflation
  under every audit percentage.
- **06 alone**: right denominator, but **207 works with no DOI** and zero
  hyperlinked citation markers. G9b caught it.

**Neither file alone is the corpus.** 06 decides WHICH works are in; 05 says WHAT
they are. The join fails closed if a labelled work has no bibliographic record.

### 3.4 Zero cross-month duplicates is CORRECT here

The month windows are disjoint and `canonical_month` assigns each work upstream.
Verified explicitly (3414 raw rows → 3414 distinct canonical keys, 0 in >1 month)
rather than assumed. **A zero is a bug until proven otherwise — so prove it,
then record the proof.**

### 3.5 Measured corpus, 2026-H1

| Month | Corpus | Depth | Cards | Anchors | Verify |
|---|---|---|---|---|---|
| 2026-01 | 475 | 122 | 110 | 396 | pass |
| 2026-02 | 499 | 131 | 131 | 475 | pass |
| 2026-03 | 559 | 146 | 146 | 535 | pass |
| 2026-04 | 589 | 164 | 164 | 581 | pass |
| 2026-05 | 583 | 154 | 154 | 560 | pass |
| 2026-06 | 623 | 167 | 167 | 582 | pass |
| **Total** | **3328** | **884** | **872** | **3129** | **all pass** |

Extractor: `opencode-go/qwen3.8-flash` on all 872 cards — one model, no mid-run
swap.

---

## 4. Device families (v5)

### 4.1 Four families, and the classifier that binds them

`scripts/stages/device_family.py`, ONE definition:

| Key | Family | Cards |
|---|---|---|
| `sj` | Single junction | 692 |
| `hyb` | Perovskite/silicon **and other hybrid** tandems | 77 |
| `ap` | All-perovskite tandem | 60 (13 explicit + 47 unspecified) |
| `mod` | Module | 43 |

**`s11b`'s `cls()` could NOT be reused.** It has four buckets (sj/ap/psi/mod) and
**no bucket for a non-silicon partner**, so 19 tandems with organic, CIGS, CdTe
or kesterite partners were classified `ap` — reported as ALL-PEROVSKITE:

```
"Perovskite/Organic Tandem Solar Cells with 26.49% Efficiency"    → ap  ✗
"Efficient Perovskite-Cu(In,Ga)Se2 Tandem Solar Cells"            → ap  ✗
"Thermally Stable Halide-Tuned CsPbX3/CdTe Four-Terminal Tandem"  → ap  ✗
"...kesterite/perovskite tandem solar cells..."                   → ap  ✗
```

That is monthly §7.8: a real number attached to the wrong device. It shipped
invisibly because no gate compares a device label against its own anchor.

Havid surfaced it in one sentence: *"also other like Perovskite/OPV or perovskite
CIGS"*.

### 4.2 PRECEDENCE and ANCHOR-FIRST, both explicit

```
mod  >  hyb  >  ap  >  sj
```

`mod` wins because the FINDING for a module-scale measurement is the area
penalty, not the junction count. `hyb` beats `ap` because a paper naming both
silicon and a wide-bandgap perovskite is a perovskite/Si tandem.

Classification reads the **anchor first**, then architecture, then title. The
anchor is the only text verified verbatim, so it describes the DEVICE THE NUMBER
WAS MEASURED ON. `tandem_unspecified` is a real answer: a tandem naming no
partner is NOT silently assigned.

### 4.3 The module floor: `MODULE_MIN_AREA_CM2 = 1.0`

Three failures, in both directions, before this settled:

1. **Missed two real modules.** The module test read only the efficiency anchors
   and the title, not the **area anchor** — which is where the word lives. Result:
   `family.sj.max_area_cm2 = 651 cm²` for a "single-junction cell".
2. **`\bmodule\b` cannot match "modules".** The trailing `\b` fails against the
   following `s`. Both defect anchors said "modules". Identical to monthly §7.3
   #6, where `gate checks?` missed "gate checking".
3. **Over-captured after the plural fix.** `mod` went 30 → 68, including ten
   cards under 1 cm² (one at 0.045 cm²). Their anchors name TWO devices and the
   card's area is the small one:

```
"21.46% (small-area, 0.108 cm2) and 19.38% (large-area module, 15.52 cm2)"
"26.41% (0.096 cm2) and 22.18% (10.04 cm2 module)"
```

Word adjacency would be fragile, so the guard is the handbook's own corollary:
**add a plausibility gate wherever physics bounds a quantity.** The smallest
genuine mini-module in this corpus is 3.9 cm²; typical lab cells are 0.04-0.12.

Even `architecture == "module"` is subject to the floor — one card carries that
architecture while its own anchor says "flexible all-perovskite tandem **CELLS**
(active area of 0.049 cm²)". The architecture describes the paper; the anchor
describes the number.

### 4.4 Anchor-contradicts-family, applied to EVERY number

A card carries ONE family label but an abstract can report several devices:

```
card family = mod   (area anchor "...57.6 cm2...", a real module)
certified anchor    = "a certified 32.95% perovskite/Si tandem efficiency"
```

Reporting 32.95% as the MODULE certified frontier asserts a 32.95% perovskite
module, which does not exist. **Both statements are true; they are about two
different devices.** Same paper as monthly §7.8.

The guard was first applied only in `champion_of()`, while `family_block()` kept
computing `top_certified` with a plain `max()` — two code paths, one guarded,
inside one file. §0.9.

---

## 5. Illumination (v5) — §7.11 in full

**Havid flagged a >30% single-junction PCE and asked whether it was a tandem or
a simulation. Both guesses were reasonable. Both were wrong.**

```
44.36%  lens=experimental  family=sj
anchor: "wide-band gap (WBG)-PIPVs achieve a PCE(i) of 44.36%
         (a power output of 127.94 µW cm−2) with a high Voc of 1.091 V"
title:  "...for High-Efficiency Wide-Bandgap Perovskite Indoor Photovoltaics"

41.6%   lens=scale_up      family=mod
anchor: "record indoor power conversion efficiencies of 41.60% at 900 lux
         and 41.22% at 300 lux under TL84 illumination"
```

**Neither is an error, a tandem, or a simulation.** Both are CORRECT numbers for
a different measurement. An indoor PCE above the one-sun Shockley-Queisser limit
is physically ordinary: the limit is defined for AM1.5G, and a 1000 lx LED
spectrum is narrow, low-flux and well matched to a wide-bandgap absorber, so
conversion efficiency is legitimately higher while absolute output is ~128 µW/cm²
instead of ~25 mW/cm².

**The defect was COMPARABILITY, not correctness.**

### 5.1 Why every existing guard missed it

| Guard | Asks | Verdict on 44.36% |
|---|---|---|
| `measured()` | is lens theory/review? | **passes** — it IS an experiment |
| `anchor_contradicts_family()` | what device? | **passes** — it IS single junction |
| G3c | is a CERTIFIED SJ value >29.4%? | **passes** — it is self-reported |
| `pce_champion` | *(no check existed)* | — |

`pce_champion` had no plausibility check at all, on the reasoning that a
self-reported number is the paper's own claim to make. **That reasoning is wrong:
an impossible self-reported number is either an extraction error or a different
measurement, and either way the review must not print it as a champion.**

### 5.2 Havid's guess was right about a different population

7 of the 8 single-junction cards above 29.4% ARE simulations (32.39%, 31.76%,
32.41%, 31.92%, SCAPS-1D and similar). Those were already correctly excluded by
the `lens in (theory, review)` filter — monthly §5.1 working as designed. Only
the indoor one slipped through.

### 5.3 The rule, and the ambiguous case

`scripts/stages/illumination.py` classifies `indoor` / `one_sun` / `ambiguous`
and **fails on ambiguous too**:

```
"achieving 35.54% under indoor LED illumination and 20.28% under standard one sun"
"PCEs of 18.40% under 1 sun and 34.54% under indoor LED illumination"
```

One anchor, two measurements — the bound value could be either. Not a valid
one-sun record OR a valid indoor record. §7.8's shape again.

Absence of evidence is treated as one-sun, because papers state indoor
conditions explicitly (it is their selling point). The asymmetry is deliberate
and documented so it can be argued with rather than discovered.

### 5.4 Measured effect

| Family | Best self-reported BEFORE | AFTER |
|---|---|---|
| Single junction | ~~44.36%~~ | **28.01%** |
| Module | ~~41.6%~~ | **27.12%** |

4 indoor values across 4 papers (sj 2, mod 1, hyb 1) + 3 ambiguous, out of 595
measured values. T3's 1-10 cm² band went 41.6% → 33.84%.

### 5.5 Excluded from tables and figures, DISCUSSED in prose

Guards live in three places because three code paths compute these numbers:
`family_block()`, `area_ladder()` and `h1_figures._illum_anchor()`. The figure
guard drops the **whole card**, not the field: F1 plots certified and champion
side by side for the same device, so keeping one would draw a half-device.

The writer receives `indoor_block_prose()` — every value with its illumination
condition and an explicit instruction: *"ONLY as indoor photovoltaics with the
illumination stated in the same sentence as the number. Never write one of these
values as a champion or record efficiency."*

It worked, and better than instructed — the writer picked up the ambiguous case
unprompted as a reporting-practice criticism:

> *"...by reporting indoor and one-sun efficiencies together in a single
> sentence: 35.54% under indoor LED illumination and 20.28% under standard one
> sun conditions"*

### 5.6 A grep is not a verification

Mid-check the redrafted sections showed `41.6` six times in sec3 and five in
sec6, up from once, and I reported the redraft as worse. **The test was wrong,
not the draft.** A bare grep for a number cannot distinguish a bad claim from a
properly qualified one. The correct test is whether every indoor value carries
its illumination condition in the same sentence:

```python
COND = re.compile(r"indoor|\blux\b|\blx\b|\bLED\b|TL84|one[- ]sun|AM1\.5|µW", re.I)
for sentence in re.split(r"(?<=[.!?])\s+", text):
    if value in sentence and not COND.search(sentence):
        fail(value, sentence)
```

Result: **0 unqualified mentions**. The count rose because the issue now
discusses indoor PV properly, which is what was asked for.

> **Rule: when a check disagrees with the artifact, suspect the check. Write the
> check that tests the actual requirement, not the one that is easy to grep.**

---

## 6. Numbers: the period stats contract

### 6.1 A period rate is NEVER the mean of monthly rates

Months have different denominators (January 475, June 623). Every rate is
`summed_numerator / summed_denominator`, with the monthly series reported
alongside.

| Metric | Pooled | Monthly range |
|---|---|---|
| efficiency stated | 52.1% | 48.1 - 55.3 |
| certified | 8.5% | 5.9 - 11.6 |
| stabilised | 11.0% | 9.2 - 13.5 |
| area stated | 8.4% | 5.8 - 10.3 |
| ISOS label | 1.7% | 0.6 - 2.7 |
| hysteresis | 2.7% | 1.5 - 4.3 |
| triplet complete | 2.9% | 1.2 - 3.8 |

**The spread matters more than the mean.** A rate that swung 0.6-2.7% and one
that sat flat are different findings, and the pooled number hides which.

### 6.2 Key namespaces: publish both, compute once

`audit.h1.*` is authoritative; `s18d`/`s19` were written against
`audit.corpus.*`. **Publish both names for the same computed value in
`h1_stats.py`** — not in a build adapter, because two consumers need it.

### 6.3 Every key a consumer reads must exist, or fail closed

`s19` raised `KeyError` four times in succession. **Fail-closed working
correctly** — it refused to print a table with a hole. Each was fixed by
COMPUTING the value from the six monthly runs, never by dropping the row.

Final: **224 stats keys** (127 v1 + 89 family + 8 indoor).

### 6.4 The frontier series and the SQ limit

```
2026-01  29.20      2026-04  32.81
2026-02  32.46      2026-05  33.50
2026-03  31.93      2026-06  33.60      delta +4.40 pp
```

Five of six exceed 29.4%. **Expected and correct**: the frontier is the best
certified device of ANY architecture, and the records are perovskite/silicon
tandems. It is only a defect if such a value is PRESENTED as single junction.

Audited before drafting: 15 cards carry `pce_certified > 29.4`; guard 5 corrected
14 to `tandem_2T` from their own anchor. One is `architecture: unknown` — its
anchor names no architecture, so guard 5 correctly did NOT invent one.

**No repair applied.** `repair_arch_from_anchor.py` corrects labels that
contradict their own anchor; this anchor contradicts nothing. See
`docs/H1_FRONTIER_AUDIT.md`.

> **Run this audit before drafting, every period.**

---

## 7. The v5 section map

### 7.1 Nine sections: spine + four families

```
 1  intro        700w  cite>=0
 2  frontier     900w  cite>=18   What Jan-Jun 2026 Verified, by Device Family
 3  family      2100w  cite>=34   [sj]   Single-Junction Frontier and Its Losses
 4  family      1210w  cite>=27   [ap]   All-Perovskite Tandems: Sn-Pb Stability
 5  family      1400w  cite>=31   [hyb]  Hybrid Tandems: Si, CIGS and Organic
 6  family      1160w  cite>=26   [mod]  Modules and the Cost of Area
 7  synthesis    900w  cite>=10   Reading the Device Families Together
 8  audit        700w  cite>=7    How Each Device Family Reports Itself
 9  gaps         900w  cite>=9    Research Gaps and Outlook
```

sha `62044c6bbcc31f39`, total ceiling 9970, cite_sum **162** inside band.

### 7.2 Allocation is DECLARED, not proportional

Family mass is **79% single junction**. Proportional allocation — what v1 does —
would give it ~5700 of 7200 body words and modules ~355. Arithmetically faithful,
editorially indefensible: **a device family earns a section because it poses a
distinct device-physics question, not because many groups publish on it.** The
module section carries the area penalty, the field's translation bottleneck, on
5% of the papers.

```
ceiling_f = BODY_WORDS * (W_DECLARED[f] * (1 - DAMP) + share_f * DAMP)
W_DECLARED = {sj 0.34, hyb 0.24, ap 0.21, mod 0.21}     DAMP = 0.30
```

The weights are **visible and arguable in the map JSON** — unlike a proportional
rule whose output looks objective while encoding a judgement nobody made.

### 7.3 Mechanism is not abandoned

Each family section is told which mechanism axes dominate ITS OWN papers, so
buried-interface chemistry is still written about — inside the family where it
matters. The synthesis section then reads all four.

### 7.4 The title states the ARGUMENT, not the section list

v5's first title was "Single Junctions, Tandems and Modules". Havid rejected it:
it enumerates the table of contents and argues nothing.

```
Perovskite Photovoltaics in January-June 2026:
    The Certified Frontier From Cell to Module
```

That is what the issue established: the ceiling moves with architecture (27.6%
sj, 30.3% ap, 33.6% hyb) and collapses with area (33.6% at 1 cm² vs 26.8% at
655 cm²), under a 9.1% certification rate. Same grammar checks as every other
title: one colon, ≤16 words, no banned term, no publication count.

> **Rule: a title slot that could be replaced by the table of contents is not a
> title slot. Name the finding.**

---

## 8. Tables (v5)

Five generated, four in the main text. A table earns main-text space on the same
terms as a figure: it must carry an argument the prose cannot make in a sentence.

| Table | Content | Placed in |
|---|---|---|
| **T1** | State of the art by device family | frontier |
| **T2** | Best certified device per family, with provenance | frontier |
| **T3** | Efficiency vs aperture area, binned | `mod` section |
| **T4** | Reporting completeness by family | audit |
| T5 | Family × month attention matrix | **SI** |

Assignment is **by argument**, not by order: each table goes to the section whose
claim it supports, so a reader meets the numbers where they are argued about.

### 8.1 T1 as shipped

| Family | Papers | Certified | Best certified | Best self-reported | Largest area | Longest T80 |
|---|---|---|---|---|---|---|
| Single junction | 692 | 63 (9.1%) | 27.6% | 28.01% | 4 cm² | 4100 h |
| All-perovskite tandem | 60 | 15 (25%) | 30.3% | 30.3% | 64.6 cm² | 1600 h |
| Hybrid tandem | 77 | 19 (24.7%) | 33.6% | 34.02% | 16 cm² | 1000 h |
| Module | 43 | 10 (23.3%) | 26.8% | 27.12% | 900 cm² | 1050 h |

### 8.2 Hard rules

- **No literal data in `h1_tables.py`.** Every value reads from `stats.json`'s
  `family.*` keys. A hardcoded number in a table is §7.2 with extra steps.
- **A cell with no evidence prints an em-rule, never 0.** "0" asserts a
  measurement of zero; "--" says nothing was reported.
- **The writer never sees a table.** A writer shown a table transcribes its
  numbers into prose, putting the same value in two places with no gate
  comparing them.

### 8.3 A table generated but never injected reaches no reader

`tables_markdown()` wrote `tables.md` and **nothing injected the tables into the
manuscript body**. Verification caught it as `Tables rendered in PDF: 0` — the
tables existed in a file no reader opens.

Fixed by mirroring `fig_for`: `TABLE_FOR` on the s18d module, defaulting empty so
v1 and the monthly path stay byte-identical, plus a fail-closed assertion that
all four declared tables are placed.

> **Rule: generating an artifact is not delivering it. Assert it reached the
> rendered page.**

---

## 9. Figures

| Fig | Content | Why it earns main-text space |
|---|---|---|
| **T1** | certified + champion frontier by month | one month is a point, six are a shape |
| F1 | certified vs self-reported by family | how thin the verified layer is |
| F2 | efficiency vs aperture area, log x | the cell-to-module gap |
| F3 | axis × MONTH | which physics gained and lost attention |
| F4 | every T80 + protocol labels | its thinness IS the finding |
| S1 | audit rates as six-point series | whether practice changed |

### 9.1 PDF figure numbers are NOT file numbers

Havid reported "Figure 2 x-axis labels overlap". **The file was
`F4_stability_evidence.pdf`.** LaTeX numbers by order of appearance. Resolve which
FILE a reader means before touching anything.

### 9.2 v5 shipped ONE figure and G9c passed

Figure attachment keyed on `s["axes"]`/`s["axis"]`, which a family map does not
have. Every test missed and only F1 attached. **G9c passed because one figure is
trivially unique.**

> **Rule: a gate that counts duplicates cannot see an absence. Assert the
> EXPECTED COUNT, not just uniqueness.**

### 9.3 The F4 defect: a label problem that was a DATA problem

The crowded axis was the symptom. The cause: the panel plotted
`protocol.split()[0]`, and papers spell one protocol several ways:

```
ISOS-L-1 (9)  vs  ISOS‐L‐1 (1)     ← U+2010 HYPHEN, identical glyph
ISOS-L-2 (7)  vs  ISOS-L2 (1)  vs  ISOS‐L‐2 (1)
ISOS-D-1 (3)  vs  ISOS-D1 (1)
```

**19 categories for 13 real protocols**, every bar understated. Monthly §4.4
rule 1 (normalise Unicode BEFORE matching) applied to protocol labels;
`scripts/stages/protocol.py`, imported never inlined. `ISOS-L-2I` is preserved as
distinct from `ISOS-L-2`.

Three layout rules confirmed: **transpose, don't rotate** (13 long labels in a
3-inch panel cannot be rotated into legibility); **decade ticks on a log axis**;
**one-line titles**.

### 9.4 Verify figure legibility by MEASURING SPAN GEOMETRY

```python
def ov(a, b):
    return (min(a[2],b[2]) - max(a[0],b[0])) > 0.6 and \
           (min(a[3],b[3]) - max(a[1],b[1])) > 0.6
```

The figure analogue of monthly §4.4b level-2 verification. It caught a collision
the FIRST fix introduced (a two-line title). Final: **44 spans, 0 collisions.**

### 9.5 When a figure and the prose disagree, the figure yields

Canonicalisation showed 39 papers name a protocol but only **31** name a
SPECIFIED ISOS protocol. The prose says 39 via `{{N_PROTO}}`. Havid chose: keep
39, relabel the figure to "Any stability protocol named: 39 of 872". The 31-vs-8
split moved to the bar colour and legend.

> **Rule: a figure that contradicts the prose is worse than a figure that says
> less. If a newly-computed number disagrees with one already in the abstract,
> surface the choice — do not silently change either.**

---

## 10. Deliverables

```
manuscript/2026-H1_v5/
  manuscript_v5.pdf                  34 pp, 4 tables, 4 figures
  manuscript_v5.md
  supplementary_v5.pdf               8 pp, 7 notes, 6 tables
  tables.md  14_tables.json          the generated tables
  fig/*.pdf                          T1, F1-F4, S1
  stats.json                         224 keys
  claim_cards.jsonl                  872 records with source quotations
  12_section_map_v5.json
  gate_report_v5.json                17 gates + draft fingerprints
  chemrxiv_2026-H1.tar.gz
  chemrxiv/                          the submission package
  data/*.csv                         10 CSVs + token accounting
```

ChemRxiv: Energy primary, Materials Chemistry secondary, CC BY 4.0,
`preprint_doi: null` (assigned on posting; a script must never invent it).

**Acknowledgements include the Anthropic AI for Science program** (Havid,
2026-09-09). `ACK` is one constant in `boilerplate.py` with three consumers.

### 10.1 s18d hardcodes its output directory

`s18d` writes `manuscript/<edition>_v4/` regardless of structure, so a v5 build
writes THROUGH v1's directory on its way to `_v5/`. `h1_build_v5` backs up v1's
map, restores it afterwards, **asserts the restore**, and prints a warning that
`_v4/` holds a v5 render until `h1_build.py` is re-run.

**This bit once, exactly as predicted.** The first post-rename build still had
`out_dir = _v2`, so it wrote `_v4/` → copied to `_v2/` and left STALE PDFs in
`_v5/`. The stale PDF carried the OLD title while the fresh markdown carried the
new one, **and all 17 gates passed** — because gates read the run dir, not that
copy. Monthly §7.6 #6: a stage that passed by examining a different artifact.

> **Rule: after any rename, verify the RENDERED artifact's mtime and content, not
> the gate report.**

### 10.2 The SI reads its front page from the manuscript

The v6 SI shipped naming July's issue ("Buried-Interface Chemistry, Defect
Tolerance and the Certified Efficiency Frontier") while its manuscript said "The
Certified Frontier From Cell to Module", and its corpus table said "Cited in the
main text | 0" beside 184 linked citations. All 17 gates passed. Two causes, both
a second code path re-deriving a fact the manuscript already prints:

- monthly `s19` derives the title only for `ver == "v4"`, so H1's `"v6"` fell
  through to the v3 literal;
- monthly `s19` counts plain `[n]`, but the build emits
  `[\href{https://doi.org/...}{n}]`.

A hand-patched PDF (17 Sep, via the GitHub web UI) fixed the title in the
ChemRxiv copy only. It left the count at 0 and the edition copy unfixed, and
the next rebuild would have reverted it. **Fix outputs by fixing the code that
makes them.**

`h1_finalize_v6` now passes s19's markdown through `stages/si_facts.py`
(`correct_si_front`). That rewrites the title, date and cited/audited rows from
the manuscript's own title block and reference list, and fails closed if any
target line is not found exactly once. s19 itself is unchanged (it is a monthly
stage). `tests/test_si_matches_manuscript.py` compares every shipped SI with its
manuscript, including the rendered H1 PDFs (edition and ChemRxiv copies).
Editions that shipped before this gate carry the defect in a `KNOWN_DEFECTS`
list that can only shrink.

---

## 11. The half-year checklist

**HUMAN** cannot be delegated.

```
[ ]  1. git status clean; git log -1
[ ]  2. probe tools: agy / opencode / claude / tectonic / pandoc / 7 deps
[ ]  3. HUMAN: .env present AND LOADING -- assert key_len > 0 (§2.1)
[ ]  4. writer probe: agy -p "Reply with exactly: OK"
[ ]  5. orphan check: no agy process alive
[ ]  6. dry-run per-month counts; SPLIT THE FIRST MONTH BY DAY (§3.2)
[ ]  7. backfill missing months; each exits 0 AND passes verify_anchors
[ ]  8. h1_aggregate: assert corpus_n == sum of monthly corpus.n
[ ]  9. h1_stats + h1_family_stats: no key a consumer reads is missing
[ ] 10. AUDIT the frontier (§6.4) AND the illumination axis (§5):
        no SJ value >29.4% may be one-sun; no indoor value in any table
[ ] 11. h1_section_map_v5: cite_sum inside CITE_SUM_BAND
[ ] 12. h1_tables: assert all four main-text tables PLACED (§8.3)
[ ] 13. h1_figures: n_t80 > 0, n_certified_points > 0, assert figure COUNT
        (§9.2), and MEASURE SPAN COLLISIONS on every figure PDF (§9.4)
[ ] 14. h1_draft_v5: watch for "STRIPPED narration" lines
[ ] 15. h1_build_v5: ALL 17 GATES MUST PASS
[ ] 16. h1_finalize_v5 all
[ ] 17. rendered-PDF verification: title, placeholders, narration, stale
        months, doubled captions, unmerged cite runs, refs cited, table
        count, pages == gate report, PDF MTIME newer than the build (§10.1),
        SI names the manuscript and counts its citations (§10.2)
[ ] 18. HUMAN: READ THE PDF
[ ] 19. commit: code fixes and artifacts in SEPARATE commits
```

### 11.1 Why step 18 cannot be automated

Gates catch regressions. Humans catch NEW defects. **Every defect class in §5,
§9.2 and §9.3 entered this handbook because Havid read a rendered page and said
a number looked wrong.** All 17 gates passed on every one of those builds.

- "the x-axis label is overlapped" → found 19 protocol categories for 13
  protocols
- "there is reported of >30% of PCE ... maybe tandem device or simulation" →
  found the entire illumination axis
- "also other like Perovskite/OPV or perovskite CIGS" → found 19 mislabelled
  tandems

> **A reader's "this looks wrong" is the highest-value signal in the system.
> Chase what is underneath it, not only what was reported.**

---

## Appendix A. Configuration (`config/h1.yaml`)

| Key | Value | Used by |
|---|---|---|
| `h1.months` | six month ids | aggregate |
| `h1.count_band` | `[2200, 4800]` | corpus assertion |
| `h1.depth_target` / `depth_band` | 320 / `[250, 400]` | selection |
| `h1.month_min_citation_share_pct` | 8.0 | coverage |
| `h1.content_page_band` | `[20, 30]` | G5 |
| `h1.total_page_band` | `[30, 44]` | G5 |
| `citations_h1.total_band` | `[150, 250]` | G2c |
| `abstract_h1.word_band` | `[380, 520]` | G3b |
| `novelty_h1.*` | 0.25 / 0.30 / 12 | G8 |
| `plausibility.single_junction_pce_max_pct` | 29.4 | G3c |
| `MODULE_MIN_AREA_CM2` | 1.0 | `device_family.py` |
| `W_DECLARED` / `DAMP` | see §7.2 | `h1_section_map_v5.py` |

## Appendix B. Known gaps, honestly stated

1. **`intra_issue_max_ratio` is defined but not enforced.** Four family sections
   on overlapping physics can converge even when each is novel against prior
   issues. G8 only compares against prior issues.

2. **The 200-paper validation label sheet still does not exist.** Every audit
   percentage ships as "detected in at least X%". Still the highest-value human
   task in the project.

3. **`N_PROTO` counts any protocol string (39), not specified ISOS (31).**
   Deliberate (§9.5).

4. **No gate enforces the illumination axis.** §5's guard lives in the stats and
   figure layers, not in a G-numbered gate, so a future consumer computing a
   frontier by a fourth code path would bypass it. A `G3d-illumination` gate
   asserting no table value carries an indoor marker is the right fix.

5. **`manuscript/2026-H1_v4/` may hold a v5 render** (§10.1). Either re-run
   `h1_build.py` or retire `_v4/` to `OLD/`.

6. **v1 and v5 share `runs/2026-H1/`.** Drafts and maps are suffixed, but
   `stats.json`, `claim_cards.jsonl` and `fig/` are common. A future H2 built
   alongside would need its own run dir.

## Appendix C. Version history

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-09-09 | First half-year handbook, from the mechanism-structure build |
| **2.0** | **2026-09-10** | Device-family structure (v5); generated tables; the device-family, module-floor, family-contradiction, illumination and protocol-canonicalisation guards; v2→v5 renumbering; the "grep is not a verification" and "generated is not delivered" rules |
