# Master Handbook: Autonomous Monthly Review Paper Production

**Version 2.1 · 2026-09-12 · Havid Aqoma**

This file is the complete specification for producing one monthly literature
review paper with verified numbers and a controlled format. **Read this file
first every month.** It is the operating contract: if this file and the code
disagree, that is a defect in one of them and must be resolved before the run.

Reference implementation: `auto-perov-review`

| Issue | Built | Result |
|---|---|---|
| July 2026 v3 | 2026-09-07 | 657 works → 15 pp, 80 citations, 8 gates |
| August 2026 v3 | 2026-09-08 | 531 works → 15 pp, 82 citations, 9 gates |
| **August 2026 v4** | 2026-09-08 | 531 works → **15 pp, 75 citations, 11/11 gates** |
| **June 2026 v4** | 2026-09-08 | 623 works → **14 pp, 76 citations, all gates** (G8 cold start) |
| **July 2026 v4** | 2026-09-08 | 648 works → **15 pp, 80 citations, all gates** (G8 vs June) |

June and July were rebuilt on v4 after the handbook was written, which is how
six further defects surfaced (§7.7). Build the OLDER month first: G8 compares
against the latest prior issue on disk, so July can only be measured against
June once June exists.

v4 exists because Havid read the August v3 issue and found it too close to
July. See §4.1b for the measurement and §7.6 for everything that broke on the
way to fixing it.

---

## 0. Read this first: the five principles

Everything below is downstream of these. If you remember nothing else,
remember them in this order.

### 0.1 Format is generated, never model-written

The title block, affiliations, citation numbering, reference list, figure
environments, back matter, and every number in the abstract are emitted by
`s18d_build_v4.py`. The writing model never sees them and cannot alter them.
Nothing about the format lives in a prompt, so nothing about the format can
drift.

### 0.2 Every defect becomes a gate, never a prompt reminder

When a human finds a defect, the response is **an assertion that fails the
build**, not an instruction telling the model to behave. A defect with a gate
cannot return next month. A defect with only a prompt reminder returns as soon
as the model's sampling changes.

This is the highest-value habit in the entire workflow.

### 0.3 Verify the artifact, not the process

A stage reporting success is not evidence that it succeeded. Parse the rendered
PDF and assert on what is physically on the page. **Every format defect in this
handbook was found by a human reading the output**, and each had already passed
a markdown inspection.

**Corollary that cost real time:** when a check disagrees with the artifact,
one of them is wrong and it is often the check. Six verifier bugs have occurred
so far (§7.3, §7.6).

### 0.4 No prose reaching a reader may be authored outside the evidence chain

Including the abstract. **Including by a script.** v3 violated this in code: it
closed every abstract with three fixed sentences asserted regardless of that
month's evidence, and no gate could see it because G3 validates only numerals
(§7.2, §4.1b).

### 0.5 A generator and its gate must be mutually consistent

A writer that obeys every instruction it is given must produce output that
passes. If per-section citation minimums sum above the issue-level ceiling,
the writer cannot win, and the failure looks like a model problem when it is an
arithmetic problem. **The generator moves, never the gate** (§6.5).

---

## 1. Pipeline architecture

**Twelve live stage scripts** plus two shared modules (`hygiene.py`,
`boilerplate.py`) and `util.py` — 15 files in `scripts/stages/`, verified by a
test. They implement the 16 logical stages below, because `s02_06.py` covers
02/05/06 and `s04_10.py` covers 04/08/10. **Only two stages use a language
model.** Everything else is deterministic Python with fixed seeds.

```
01 harvest       OpenAlex + Semantic Scholar + Crossref + arXiv
02 normalize     DOI/title normalisation, language detect        (s02_06)
05 dedupe        work_key merge across sources, canonical month  (s02_06)
06 label         mechanism axis + lens, weighted keyword scoring (s02_06)
04 venues        cumulative journal citation percentile          (s04_10)
08 select        constrained depth-tier selection + sensitivity  (s04_10)
10 stats         every number the manuscript may ever cite       (s04_10)
09 extract       [LLM] structured claims, each anchor-bound
   verify        independent anchor re-verification (separate script)
11 figures       plots, every value read from stats or cards
12 section map   generated per issue from depth-tier mass
13 draft         [LLM] Phase A body -> B gaps -> C abstract
18 build         format assembly + 11 gates + PDF
19 SI            supplementary information
20 chemrxiv      ChemRxiv preprint package + CSV data pack
21 tokens        per-model / per-CLI / per-process token CSV
```

Stage numbers have gaps because they follow the original plan. **Do not
renumber.** Superseded stages live in `OLD/` (§1.3).

### 1.1 Run commands, in order

```bash
cd auto-perov-review
M=2026-09        # the month being built

python scripts/stages/s01_harvest.py      $M      # ~5 min, network
python scripts/stages/s02_06.py           $M
python scripts/stages/s04_10.py           $M
python scripts/stages/s09_cards.py        $M      # LLM, ~35 min / 144 papers
python scripts/verify_anchors.py          $M      # MANDATORY, see §3.2
python scripts/stages/s11b_figures_v2.py  $M
python scripts/stages/s13d_draft_v4.py    $M      # LLM, ~25 min
python scripts/stages/s18d_build_v4.py    $M      # gates + PDF
python scripts/stages/s19_si.py           $M v4
python scripts/stages/s20_chemrxiv.py     $M v4
python scripts/stages/s21_tokens.py       $M v4   # token accounting CSV
```

Argument shapes, verified: `s19`, `s20`, `s21` take `<month> v4`; everything
else takes `<month>` alone. `s13d` accepts trailing section ids to redraft only
those: `s13d_draft_v4.py 2026-09 8`.

### 1.2 Resume semantics

Each stage writes `runs/<month>_<hash>/<NN>_<name>.done` containing its output
counts. **`is_done()` reads the marker payload, not its existence** — a marker
recording `n_cards: 0` counts as not done (§7.1).

The run id is pinned in `runs/<month>.active` by the first stage to run.
Never construct a run path any other way.

`s13d` additionally records the section-map `sha256` in
`draft_v4/_map.sha`. **If the map changes, cached sections are deleted**, since
prose drafted against different titles, ceilings and evidence folds cannot be
reused under a new map.

> **Cache trap:** a change to `RULES`, a task prompt, **or `hygiene.py`** does
> **not** change the map sha. If you edit prompt text or filter text, clear the
> affected drafts by hand or the stage will happily reuse prose written under
> the old instructions. The narration-leak fix hit exactly this: the filter
> changed, the map did not, and the cached section 8 would have survived
> untouched.

### 1.3 The OLD/ folder

Superseded files are **moved** (`git mv`) into `OLD/`, organised by version,
with an index at `OLD/README.md`:

```
OLD/v1_stages/   s11_figures, s12_brief, s13_draft, s18_build
OLD/v2_stages/   s13b_draft_v2, s18b_build_v2
OLD/v3_stages/   s13c_draft_v3, s18c_build_v3
OLD/v3_config/   gates/models/title_terms snapshots at the v3->v4 cutover
OLD/plans/       PLAN_v1..v4  (v5 stays live in the root)
OLD/probes/      one-shot feasibility probes, answers now in this handbook
```

Rules: nothing in `scripts/stages/` may import from `OLD/`; config files are
**copied** (they are still live) while stages are **moved**; to re-run an old
version, copy the stage out rather than editing it in place.

Before archiving a stage, **extract anything still shared**. `s18c` held
`AFFIL`, `ACK`, `AI_DECL`, `tex_esc`, `md_esc` and `expand_abbrev`, which
`s18d` imported — those now live in `scripts/stages/boilerplate.py`, otherwise
a superseded build stage would have to stay on the live path to hold constants.

---

## 2. Model assignment

| Role | CLI | Model | Notes |
|---|---|---|---|
| **Writer** | `agy` | `gemini-3.8-flash-high` | writes ALL manuscript prose |
| **Extractor** | `opencode` | `opencode-go/glm-5.3-flash` | claim extraction |
| **Science reviewer** | `claude` | `opus`, effort `high` | read-only |
| **Structure reviewer** | `opencode` | `glm-5.3-flash` | read-only |
| **Orchestrator** | hermes | — | dispatch, gates, aggregation. Writes no prose |

Non-negotiable:

- **Exactly one model writes prose, and it has no fallback.** If the writer is
  unavailable the stage fails closed. A fallback model means two prose voices
  in one document.
- **Reviewers never write.** A model that reviews its own output validates its
  own mistakes.
- Retry the **same** model 3× with backoff on transient failure. A retry is not
  a fallback.

Invocations, verified working:

```bash
agy -p "<prompt>" --model gemini-3.8-flash-high \
    --dangerously-skip-permissions --print-timeout 900s

opencode run -m opencode-go/glm-5.3-flash --format json "<prompt>"

claude -p "<prompt>" --model opus --effort high \
    --output-format json --max-turns 10 --allowedTools "Read,Grep,Glob"
```

### 2.1 Changing the extractor requires a JSON-shape probe

The extractor's output is parsed, not read. **Before adopting a new extractor
model, probe it** and confirm `parse_array()` succeeds and every schema key
survives:

```python
from stages.s09_cards import call_opencode, parse_array, MODEL
raw, meta = call_opencode(one_object_prompt, timeout=420, attempts=2)
arr = parse_array(raw)
assert arr and set(arr[0]) >= {"work_key", "architecture", "pce_champion",
                               "pce_certified", "t80_h", "claims"}
```

`muse-spark-1.3-contributor` passed this probe on 2026-09-08 (10/10 keys
intact) and was adopted, then **reverted the same day** at Havid's direction:
"to be safe, change back to qwen3.8-flash". A model that returns prose around
its JSON, or renames a field, silently produces zero cards — the silent-zero
class (§7.1).

> **A JSON-shape probe is necessary but not sufficient.** It proves one object
> parses; it does not prove 144 abstracts extract with comparable recall.
> Prefer the model with a measured track record over the one that passed a
> smoke test, and if you do swap, **re-extract the month** rather than letting
> the new model debut on a shipping issue.

**The current pin is `glm-5.3-flash` (2026-09-11), and it has passed the probe
but NOT the sufficiency bar above.** Run the probe with
`scripts/probe_glm53_extractor.py`, which reports shape and recall as two
separate verdicts so a well-formed object full of nulls cannot be mistaken for
a working extractor.

Measured on 2026-09-12, `opencode-go/glm-5.3-flash`, one real 2026 abstract:

| Check | Result |
|---|---|
| `parse_array` on raw output | parsed, array non-empty |
| required schema keys | 6/6 present |
| `pce_champion` / `pce_certified` | 26.7 / 26.1, both correct |
| `t80_h` | **null**, though the abstract states 1500 h |
| claims returned | 4 |
| anchors verbatim in abstract | 4/4 |
| latency / tokens | 14.0 s, 505 out |

The `t80_h` miss is the one result that matters here. The abstract phrases
stability as "retained 92% of initial efficiency after 1500 h", which is a T92
statement rather than a literal T80, so returning null is defensible and may
even be the more careful answer. It is recorded rather than waved away because
**`n_t80 > 0` is a checklist assertion (step 9) and the silent-zero class is
exactly how a stability figure empties out without failing.** On the first
month extracted under this pin, compare the T80 count against the same month's
prior run before trusting the stability figure.

Every card of 2026-H1 on record was extracted by `qwen3.8-flash`, which carries
313 verified anchors across two shipped issues (§3.2). That remains permanently
true of those cards; this pin governs the NEXT extraction only.

**Config and record now disagree on purpose, and the next build will say so.**
`config/models.yaml` names `glm-5.3-flash` while all 872 cards of 2026-H1
record `qwen3.8-flash`, so `provenance()` will print its loud mismatch warning
and will declare the *record* in the AI Usage Declaration (§8.4). That is the
guard working, not a defect. **Do not "fix" it by editing the cards**, which
would assert that a model extracted work it never saw. The warning clears when
a month is extracted under the new pin.

### 2.2 Windows: resolve the real executable

`opencode` on PATH is a shim. `CreateProcess` cannot run a POSIX shell script,
and `cmd.exe /c` splits on the space in `<HOME>`. Resolve
`node_modules/opencode-ai/bin/opencode.exe` directly (`_opencode_exe()`).

---

## 3. The evidence chain

**Every number in the manuscript traces to a verbatim quotation from the cited
paper's own abstract.** This is the core of the system.

Extraction returns numeric fields, each with a quotation. Then **scripts**,
never the model, apply three guards:

1. The quotation must appear **word for word** in the source abstract.
2. The numeric value must appear **inside its own quotation**.
3. **Truncate the quotation to 25 words FIRST, then apply check 2**, sliding
   the window to a position that contains the value.
4. **The device label must come from the value's own quotation, not from the
   paper.** An abstract can report two devices — its own result and a record it
   cites — and a label taken from the paper will attach to the wrong number
   (§7.8).

**Checks 1-3 prove a number is real. They do not prove it describes what the
sentence says it describes.** That is a separate failure mode, it survived
every guard above, and it shipped: see §7.8.

### 3.1 Guard order is not cosmetic

The original spec said "check the value, then truncate". That order shipped
five fields whose quotations ended immediately before their own number:

```
pce_champion 16.16  anchor: "...leading to"
pce_champion 21.4   anchor: "...power conversion efficiency (PCE)"
pce_champion 26.0   anchor: "...increases efficiency from"
```

The stage reported `nulled_number: 0` while shipping quotations that proved
nothing. A value that cannot be proved within 25 words is **nulled** — that is
the fail-closed answer.

### 3.2 Independent re-verification is mandatory

Run `scripts/verify_anchors.py <month>` after extraction. It shares **no code**
with `s09_cards.py` and re-derives every count from `claim_cards.jsonl` plus
`private/02_abstracts.jsonl`. It exits non-zero on any of:

- an anchor not found word for word in its source abstract
- an anchor longer than 25 words
- a numeric value absent from its own anchor
- zero anchors (a zero is a bug until proven otherwise)

Do not reuse the extraction stage's own counters. **The guard-order bug was
found this way and only this way.**

| Month | Cards | Anchors | Verbatim | Over 25 w | Number missing |
|---|---|---|---|---|---|
| July 2026 | 169 | 625 | 625 | 0 | 0 |
| August 2026 | 144 | 539 | 539 | 0 | 0 |

### 3.3 The abstract placeholder contract

The abstract is written **last**, by the writer, and is **forbidden from
emitting any digit**. It emits named tokens; `s18d` substitutes canonical
values. A number the writer cannot see is a number the writer cannot fabricate.

| Token | Source |
|---|---|
| `{{N_CORPUS}}` | `stats["corpus.n"]` |
| `{{N_DEPTH}}` | `stats["selection.n_depth"]` |
| `{{N_CERT}}` | count of cards carrying `pce_certified` |
| `{{P_TOP_CERT}}` | highest `pce_certified` across cards, with `%` |
| `{{P_TOP_SJ}}` | highest certified single junction (title excludes tandem/silicon) |
| `{{A_MAX}}` | largest `active_area_cm2` that also has a certified value |
| `{{P_AREA_MAX}}` | the certified efficiency at that area |
| `{{N_T80}}` | count of cards with `t80_h` |
| `{{H_T80_MAX}}` | longest `t80_h`, with unit |
| `{{N_PROTO}}` | count naming an ISOS protocol |
| `{{PCT_EFF}}` | `stats["audit.corpus.efficiency_stated.pct"]` |
| `{{PCT_CERT}}` | `stats["audit.corpus.certified.pct"]` |

Rules, all machine-checked:

- **No citations in the abstract.** It is written after the body, so inheriting
  body numbers would force a renumber.
- **No digits.** The draft stage rejects any literal digit and retries.
- **An unresolvable token fails the build.** A hole never ships.
- Values the build *computes* (e.g. `N_CERT`) are admitted to G3's allow-list
  explicitly; otherwise G3 flags a number the build itself derived (§7.6).

### 3.4 Full text is not required

A full-text retrieval probe succeeded for **5.0%** of a month's papers.
`pdf_url` is present 17-38% of the time but the fetch is refused (HTTP 403),
and a **fourteen-month-old month retrieved worse (2.5%) than a two-month-old
one (5.0%)**. This is publisher WAF behaviour, not indexing delay: waiting does
not help and neither does a politer crawler.

Abstract-first is the correct design, not a compromise:

| Basis | Eligible | Depth tier | 95% CI on a 50% metric |
|---|---|---|---|
| full text (5.0%) | 32 | 12, small pool | ±28.3 pp |
| **abstract (68%)** | **446** | **178** | **±7.3 pp** |

---

## 4. Manuscript format

Emitted entirely by `s18d_build_v4.py`. Single column, 11 pt, 2.4 cm margins.

1. Centred raw-LaTeX title block: title, author with superscript numerals,
   numbered affiliations, exact write date
2. Abstract, 260-340 words, no citations
3. Keywords
4. Numbered sections from the generated map
5. Acknowledgements / Declaration of Competing Interest / Data Availability
6. AI Usage Declaration
7. Numbered references with clickable `https://doi.org/...` links

### 4.1 Section map: generated, not fixed

**v3 hardcoded eight sections in four files. v4 computes them per issue.**
The map lives in `runs/<m>/12_section_map.json`, written by `section_map.py`,
and every downstream stage reads it. **No stage may hardcode a section title,
ceiling, or citation target.**

Fixed spine, always in this order:

| Role | Section | Ceiling | Cite target |
|---|---|---|---|
| `intro` | Introduction | 300 | 0 |
| `frontier` | The Certified Frontier in {Month} | 290 | 8 |
| `gaps` | Research Gaps and Outlook (**always last**) | 400 | 4 |

Between them sit **4-5 mechanism sections chosen by depth-tier evidence mass**:

| Knob | Value | Why |
|---|---|---|
| `MIN_MECH` / `MAX_MECH` | 4 / 5 | fewer loses coverage, more loses shape |
| `MIN_DEPTH` | 10 papers | below this an axis cannot support a section |
| `BODY_WORDS` | 2400 | distributed proportionally to mass |
| `MECH_MIN/MAX_WORDS` | 320 / 620 | floor keeps a thin section real; ceiling stops one axis eating the issue |
| `WORDS_PER_CITE` | 42 | `cite_target = ceiling / 42`, clamped 5-15 |
| `CITE_SUM_BAND` | 55-72 | **asserted**: minimums must leave headroom under G2c (§6.5) |

An axis that misses the cut is **folded** into a related section, so its papers
still reach the writer rather than vanishing.

Why this changed: August's depth tier was defects 42, interfaces 32,
**composition 25**, architecture 17, stability 16, **scale_up 12**. The fixed
v3 map gave scale_up (thinnest) a full section and composition (third largest)
none.

Titles rotate from a per-axis bank indexed by month, so consecutive issues
leading on the same axis do not reuse one phrasing. **Rotation is
deterministic** — the same month always yields the same map, or resumes would
redraft forever. The map carries a `sha256` (§1.2).

**Both word bounds are enforced.** Floor at 45% of ceiling catches stubs;
ceiling at 135% stops the writer buying coverage with length. **Citation
targets are enforced too** — a section under target is rejected and redrafted.

### 4.1b Authorship order: the fix for repetition

Measured July-vs-August similarity on v3 output, citations stripped:

| Part | Similarity |
|---|---|
| **Abstract** | **0.629** |
| Introduction | 0.343 |
| Certified Frontier | 0.272 |
| Body sections 3-7 | 0.055 - 0.183 |

**The writer was never the problem.** Repetition sat exactly in the parts a
Python script authored. So v4 moves the closing material to the writer, last:

```
Phase A   body       sections 1..n-1, from stats + cards
Phase B   gaps       reads the FULL body, cites [@work_key], target >= 4
Phase C   abstract   reads the FULL body + gaps, NO citations, NO digits
```

Phases B and C exist to react to what the body **actually says**. Handing the
writer statistics alone would recreate the v3 failure: closing text that could
have been written before the body existed, and therefore reads the same every
month.

**The hardcoded conclusion triad is gone.** v3 closed every abstract with
three fixed sentences ("Buried-interface chemistry, not absorber composition,
now sets the achievable open-circuit voltage." and two more) asserted
regardless of evidence. That was §0.4 violated in code, in the most-read part
of the paper, in the one place no gate looked.

Result, same measurement:

| Build | Abstract | Worst body section |
|---|---|---|
| v3 | 0.042 | **0.290** (over the 0.25 band) |
| **v4** | **0.018** | **0.144** |

Each issue also gets one rotating **angle** that changes the order of attack
(lead with the strongest mechanism / with the disagreement / with what the
measurements cannot distinguish / with the quantitative frontier). The angle
never changes the standard of evidence.

### 4.1c Never dictate phrasing in a prompt

Two G8 failures traced to prompts that supplied sentences instead of jobs.
The writer obediently echoed them, so those sections scored 0.239 and 0.064
while genuinely free sections scored 0.02.

```
BAD   "Say: whether a claimed efficiency is verifiable, whether it
       survives at module area, and whether it survives operation."
GOOD  "Locate the field's open problem. The frontier is no longer raw
       efficiency. Say in your own words what it has become."
```

> **Rule: state the JOB, never the wording. A prompt that contains a sentence
> will get that sentence back, every month, forever.**

### 4.2 Title grammar

```
{Frame} in {Month Year}: {slot derived from the month's leading axes}
```

Derived by `derive_title()` from the two leading mechanism sections, using
`config/title_terms.yaml` axis phrases, rotated by month. Checks, all
fail-closed:

- exactly one colon
- ≤16 words (falls back to the single leading axis if over)
- no banned term (`banned_in_title`, which includes frames colliding with real
  journals: `Progress in Perovskite Photovoltaics` mimics *Progress in
  Photovoltaics*)
- **no publication count** — it goes stale as the month backfills and
  contradicts the indexing caveat the paper itself states
- **comma-join when an axis phrase already contains "and"**, or the slot reads
  "trap density and ion migration and self-assembled monolayer contacts"

### 4.3 Citation formatting

- Numbering is **one pass over the body in reading order**. v3 needed two
  passes (abstract first) purely to serve the abstract, which is what produced
  the `[1],[5],[6],[10],[60]` defect. A citation-free abstract deletes the
  whole problem.
- Adjacent brackets merge: `[8,9] [10]` → `[8,9,10]`
- Merging must **iterate** — `[30,31] [32,33] [34]` needs three passes
- Groups sort ascending and deduplicate: `[14,8]` → `[8,14]`
- Verify no unmerged runs remain: `(?:\[\d+(?:,\d+)*\]\s*){2,}` finds none

**Nomenclature is not a citation.** Two real cases reached gates:

| Text | Meaning |
|---|---|
| `[60]fullerene-phosphonic acid` | IUPAC name for C₆₀ |
| `out-of-plane [100] growth` | Miller index |

The marker regex is `\[(\d+(?:,\d+)*)\](?![A-Za-z])`, **plus** a rule that any
bracketed number above `len(order)` cannot be a citation, because the
manuscript has exactly that many references. The lookahead alone missed
`[100] growth` (a space follows the bracket).

### 4.4 Notation: units, ions and formulae

**Every unit, ion and chemical formula is typeset by siunitx and mhchem, not
by a regex table.** `scripts/stages/notation.py` converts the writer's plain
text; the writer never emits LaTeX, so §0.1 holds.

| Plain text from the writer | Emitted | Renders |
|---|---|---|
| `61.2 cm2` | `\qty{61.2}{\centi\meter\squared}` | 61.2 cm² |
| `1.3 × 10−3 cm2 V−1 s−1` | `\qty{1.3e-3}{\centi\meter\squared\per\volt\per\second}` | 1.3 × 10⁻³ cm² V⁻¹ s⁻¹ |
| `24 mA cm-2` | `\qty{24}{\milli\ampere\per\centi\meter\squared}` | 24 mA cm⁻² |
| `Pb2+` | `\ce{Pb^2+}` | Pb²⁺ |
| `[PbI4]2-` | `\ce{[PbI4]^2-}` | [PbI₄]²⁻ |
| `PbI2`, `NiOx`, `Cs2AgInCl6` | `\ce{...}` | PbI₂, NiOₓ, Cs₂AgInCl₆ |

Preamble lives in **`config/tex/manuscript_head.tex`** — tracked, because it
previously sat in gitignored `.staging/` where a fresh clone would silently
lose the packages and revert every unit to plain text.

```latex
\usepackage{siunitx}
\usepackage[version=4]{mhchem}     % version PINNED: v3 changed charge syntax
\sisetup{detect-all, per-mode = reciprocal, exponent-product = \times, ...}
```

**Four rules that cost real defects:**

1. **Normalise Unicode BEFORE matching, in the converter *and* the gate.**
   The writer emits U+2212 (typographic minus), not ASCII `-`. Identical
   glyph, different codepoint. v1's ASCII-only rules converted `cm2` but
   missed `V−1`, and the ASCII-only gate reported **pass** on the broken
   line — ninth instance of §7.3.
2. **`per-mode = reciprocal`, not `symbol`.** `symbol` renders the mobility
   as `cm²/(V s)`, which is correct typography but not this literature's
   convention; every perovskite paper writes `cm² V⁻¹ s⁻¹`.
3. **`\squared` follows its unit; `\per` precedes the group.**
   `\per\centi\meter\squared` is cm⁻², `\per\squared\centi\meter` is wrong.
4. **Mask before substituting.** Existing `\qty`/`\ce` spans (idempotence),
   `\href` targets, DOIs, citation markers and defined terms (`T80`,
   `ISOS-L-1`, `p-i-n`, `2T`, `C60-PA`, `I-V`) are masked first. Without
   that, a formula rule chews DOI digits and a second build double-wraps.

**Deliberately not converted:**

- **Bare percentages.** `27.12%` is already correct; `\qty{}{\percent}` would
  insert a thin space across hundreds of accepted appearances. *Consistency
  means the broken classes become correct, not that every token is rewritten.*
- **Bare anions** (`I-`, `Br-`). Genuinely ambiguous: "I-V curve" is a real
  term. G9a **reports** them for human judgement rather than guessing. Inside
  brackets the ambiguity disappears, which is why `[PbI4]2-` *is* converted.
  *A silent wrong guess in a formula is worse than a flagged one.*

### 4.4b Typography can NEVER be verified from flat PDF text

This is the most transferable lesson of the whole format cycle.

`page.get_text()` concatenates spans and **discards font size and baseline**,
so `"cm"` + a raised `"2"` reads as `"cm2"` — byte-identical to the broken
form. After the notation fix landed, a flat scan still reported `cm2`, `Na+`
and `PbI2` as defective. They were correct. Eighth instance of §7.3.

Three levels of verification, and you need the middle one as the gate:

| Level | Method | Catches | Cost |
|---|---|---|---|
| 1 | source assertions (G9a) | wrong or missing markup | free |
| 2 | **span geometry** (`verify_notation_pdf.py`) | flat vs scripted, per token | seconds |
| 3 | pixel diff vs golden image | collisions, kerning | breaks on any content change |

**Level 2 is the gate.** For each notation token, read
`page.get_text("dict")` and require **both**:

- **smaller**: script span `size ≤ 0.85 × body_size` (7.64 vs 10.91 pt here)
- **displaced**: superscript baseline *above* its base, subscript *below*

Both, because smaller-at-the-same-baseline is just small text (a caption),
and raised-at-body-size is a rendering artefact. The decisive proof that this
works: `\ce{[PbI4]^2-}` puts the subscript `4` at y=487.70 and the charge
`2−` at y=479.47 in **one token, two directions** — something no regex table
could produce, and something flat text cannot see.

Level 3 is rejected here: a monthly paper changes content every issue, so a
golden image would fail every month for the wrong reason. It suits a fixed
template, not this.

### 4.5 Title-block spacing is MEASURED, never tuned by eye

Four attempts. The first three were blind em-value guesses and **none of them
could have worked**:

| Attempt | Source | Rendered gap |
|---|---|---|
| 1 | `\vspace{0.9em}` after `\end{minipage}` | date almost touching the affiliation |
| 2 | `\vspace{2.2em}` | still too close |
| 3 | `\vspace{3.6em}` | **0.11 pt** |

`\vspace` placed after `\end{minipage}` lands in **horizontal mode**, where
LaTeX discards it. The source asked for 3.6em and the page rendered 0.11 pt.
Three tunings changed a number that was never applied.

**Fix:** put the date *inside* the minipage, separated by `\\[2.0em]` — the
mechanism that provably works, because it is what separates the affiliation
lines. Then trim below the block with a single `\vspace{0.8em}`.

Accepted layout, measured on the rendered page:

| Gap | Points |
|---|---|
| author → affiliation 1 | 14.42 |
| affiliation → date | 22.52 |
| date → Abstract | 23.74 |
| Abstract → body | 10.17 |

The two middle gaps differ by 1.2 pt (**ratio 1.05**), which is the balance
requirement in Havid's own words: the date must not crowd the affiliations and
the Abstract must not drift away from the date.

**G10** measures all four on the rendered PDF against bands in
`scripts/stages/layout.py`, plus a `MAX_MIDDLE_RATIO` check so the block
cannot become lopsided even while every individual gap stays in band. The
module is shared with `verify_pdf.py` deliberately: a guard applied in one
consumer diverges (§7.6 #10, #12).

G10 also derives `title_block_fraction` (measured **0.329**) which G5 had
hardcoded as `0.40`. A hardcoded layout constant is a latent §7.3 bug waiting
for a layout change.

> **Rule: a spacing value in the source is a request, not a result. If a
> reader reports a spacing defect, measure the rendered page before editing
> any constant — the constant may not be reaching the page at all.**

### 4.6 Abbreviations

Deterministic first-use expansion, abstract then body in reading order,
skipping any the writer already expanded. Order the table
**longest-key-first** so `TRPL` is not consumed by `PL`.

---

## 5. Figures

A figure earns main-text space by carrying an argument the prose cannot make in
a sentence. Corpus funnels and audit bar charts belong in the SI.

| Fig | Content | Argument |
|---|---|---|
| F1 | certified vs self-reported efficiency by device family | how thin the verified layer is |
| F2 | efficiency vs aperture area, log x | the cell-to-module gap |
| F3 | mechanism axis × device family | which physics each family is pushed on |
| F4 | every reported lifetime + protocol labels | its thinness *is* the finding |

**v4 attaches figures by role/axis, not by section number**, because section
numbers now vary: F1 → the `frontier` section, F2 → whichever section carries
`scale_up`, F4 → the `stability` section, F3 → composition or defects.

**One figure file attaches to at most one section**, enforced by `claim()`
keyed on the FILENAME and asserted by G9c. The August v4 PDF showed the same
plate as Figure 2 *and* Figure 3, because F3 was claimed with `setdefault`
keyed on the section id: `defects` was section 3 and `composition` section 5,
two different ids, so both got it. The files were never identical (their md5s
differ) — the *attachment* was.

> **Consequence worth internalising:** PDF figure numbers are assigned by
> LaTeX in order of appearance, so they are **not** the `F1..F4` file numbers.
> When a human reports "Figure 4 is wrong", resolve which FILE that is before
> touching anything. In the August build, the reader's "Figure 4" was
> `F2_area_penalty.pdf`.

### 5.1b Band labels go outside the axes frame

Three attempts, and only the third is safe:

| Attempt | Placement | Failure |
|---|---|---|
| 1 | pinned to `ylim` bottom | collided with data points and the legend |
| 2 | axis fraction `y=0.97`, `va="top"` | still INSIDE the plot area; overlapped data |
| 3 | axis fraction `y=1.02`, `va="bottom"`, `clip_on=False` | in the margin above the frame, unreachable by any data point |

> **Rule: a label that must never touch data does not belong inside the data
> region. Put it in the margin, not at a cleverer position inside.**

### 5.1 Exclude simulation from measured-performance figures

A drift-diffusion study reporting ~30.8% sat beside certified hardware on the
efficiency frontier until a human noticed. Filter
`lens in ("theory", "review")` and annotate the excluded count on the axes.

**Keep `scale_up`.** Those are real module measurements. Filtering to
`lens == "experimental"` alone silently drops 11 real papers.

### 5.2 Other figure rules

- **Never hard-code a plotted number.** Every value reads from `stats.json` or
  the cards, and the figure script asserts no literal data appears in code.
- Band labels use **axis-fraction coordinates with `va="top"`**. Pinning to
  `ylim` collided with data points and the legend.
- **Check field locations.** `t80_h` lives under `stability`, not
  `performance`. Reading the wrong dict printed `n_t80 = 0` and rendered an
  empty panel while four real values sat in the cards.

---

## 6. Gates

Seventeen gates. All are computed in `s18d_build_v4.py` and written to
`runs/<m>/gate_report_v4.json`.

The count is stated here and asserted against a real report by
`tests/test_handbook.py::test_gate_table_matches_a_real_gate_report`. It read
"Eleven" while the build emitted seventeen, and **G3d-illumination** was
missing from the table below for four issues: exactly the failure §6 opens by
warning about, a gate nobody was checking because nobody knew it existed.
Update this number and this table in the same commit as any new gate.

| Gate | Check | Threshold | Exists because |
|---|---|---|---|
| **G1-cite** | every marker resolves to an extraction record | 0 unresolved | founding requirement |
| **G2-struct** | total words + per-section ≤135% of ceiling; SHA-256 of each draft | map total ×1.15 | only the total was enforced, so a section ran over unseen |
| **G2b-cite-order** | first-appearance numbering monotonic | strict | abstract read `[1],[5],[6],[10],[60]` |
| **G2c-cite-count** | citations in band | `citations.total_band` 60-85 | a length cut silently dropped citations 110→42 |
| **G3-abstract** | every abstract numeral traces to stats, a card, or a computed value | 0 unverified | three fabricated numbers shipped |
| **G3b-abstract-form** | abstract word band, zero citation markers | `abstract.word_band` 260-340 | `abstract_word_max: 250` sat in config while a 326-word abstract shipped, because no gate read it |
| **G3c-abstract-physics** | a substituted value must be physically possible for the quantity it is presented as | single junction ≤ 29.4% | a **real** certified tandem value shipped as single-junction; it traced to a card, so G3 passed it (§7.8) |
| **G3d-illumination** | a value presented as a one-sun record must come from a card whose anchor classifies as one-sun | 0 non-one-sun values in `P_TOP_CERT`, `P_TOP_SJ`, `P_AREA_MAX` | indoor and low-light efficiencies reach 40%+ under a lamp and are not comparable to AM1.5G. The stats and figure layers already excluded them via `stages/illumination.py`, but that guard sat **outside** the gate set, so any new consumer computing a frontier by a different code path would have bypassed it silently. Re-derived from the cards backing the abstract, so it holds whichever layer produced the number. Reports `skip`, not `pass`, when the period layer is absent |
| **G4-hygiene** | em-dash, banned vocabulary, **agent-narration leak** | 0 each | 25 lines of status chatter shipped; then a 26th (§6.4) |
| **G5-build** | page bands measured from the References page index | `paper_v3` 12-17 total, 8-11 content | `pages > 5` was right by luck |
| **G6-novelty** | no first-person experimental claims | 0 hits | this reviews others' work |
| **G7-abbrev** | no bare abbreviation before its expansion | 0 bare | reader complaint |
| **G8-novelty-vs-prior** | section-vs-prior-section similarity, abstract similarity, ≥12-word shingle reuse | 0.25 / 0.30 / 0 | the August issue read like July's |
| **G9a-notation** | no flat unit, power of ten, ion or formula survives the siunitx/mhchem pass | 0 residual | `cm2`, `V−1`, `Na+`, `PbI2` printed flat in the August v4 PDF |
| **G9b-cite-links** | every body citation marker is wrapped in `\href` to its DOI | 0 unlinked | a reader could not click a citation to reach the paper |
| **G9c-figure-unique** | one figure file attaches to at most one section | 0 duplicates | F3 attached twice; LaTeX numbered it Figure 2 **and** Figure 3 |
| **G9d-model-names** | the AI declaration names products, not CLI slugs | 0 bare slugs | the declaration said "opus" instead of "Opus 5" |
| **G10-title-block** | four title-block gaps measured on the rendered page, in points | see §4.5 | three blind em-value tunings all failed; the source asked for 3.6em and the page rendered 0.11 pt |

### 6.1 Never widen a gate to make output pass

If a gate says 13 pages against a band of 8-10, either fix the output or record
a deliberate decision with its reason. **Editing the threshold to match the
artifact defeats the entire mechanism.**

Legitimate exception, and the only one so far: v4 added a **new** `paper_v3`
page band rather than editing the v1 `paper` band, because the v1 numbers
described a retired two-column layout and had never been measured against v3
output at all. Adding a band where none applied is not widening one.

### 6.2 Report which number moved

G5 emits `pages_to_refs`, `title_block_fraction`, `content_pages`,
`reference_pages` and `total_pages` separately. "17 pages, too long" is not
actionable. "Content is 7.6 pages of a 7-page target and 9 pages are the
reference list" points straight at the fix.

### 6.3 Freeze inputs before gating

Fingerprint every draft the build reads, store the hashes in the gate report,
**refuse to build if any draft changed in the last 20 seconds**, and refuse if
an `agy` process is alive (§7.4).

The orphan check **detects and refuses; it never kills.** The writer is `agy`;
killing by a broad name match (`node`, `python`) would take down the
orchestrator running the build.

### 6.4 The agent-narration guard

**One canonical definition, in `scripts/stages/hygiene.py`**, imported by
`s13d` (per-line strip), `s18d` (G4), and `s19` (SI notes). A test asserts they
are the *same object*, because equal-looking patterns drift.

This matters more than it sounds. Three divergent copies used to exist, and the
build-side copy was the **narrowest**. On the August v4 issue the writer opened
section 8 with:

> I have launched the search command and will wait for it to finish.

It survived the draft filter, then **also passed G4**, and reached the rendered
PDF directly under the "8. Research Gaps and Outlook" heading. Havid found it by
reading the page.

**A gate reporting `pass` on leaked text is worse than no gate: it teaches you
to trust output you should be checking.**

Why all three near-misses happened:

| Pattern | Writer wrote | Miss |
|---|---|---|
| `the command has been launched` | "I have launched the search command" | exact phrase, different voice |
| `\bI (?:will\|'ll) wait\b` | "and will wait for it to finish" | required `I` adjacent to `will wait` |
| `waiting for ...` | "wait for it to finish" | required the gerund |

The taxonomy had been written from **remembered sentences instead of from the
grammar of the failure**. Six classes now, each written as a class of sentence:

1. progress / waiting narration
2. **launch + future-wait** (the class that shipped)
3. tool / filesystem vocabulary
4. file-path / save reporting
5. self-reported gate or word-count results
6. conversational framing

Aggressive patterns are scoped by first person or a tool noun so ordinary
review prose is untouched. `hygiene.py` ships `KNOWN_LEAKS` (20 real shipped
sentences plus paraphrases) and `KNOWN_CLEAN` (12 legitimate sentences,
including "further research is required" and "a systematic search of the
indexed literature", since **"research" contains "search"**). Both lists are
parametrised tests.

**Strip per line, do not reject the section.** An early version discarded whole
sections and threw away three usable drafts while the identical prompt run by
hand produced clean prose. The model intermittently wraps one status line
around real content.

**Draft strips; build fails closed.** `strip_narration()` removes narration
line by line and *prints what it removed*. If anything is still present at
build time, the strip was bypassed (hand-edited draft, stale cache, divergent
filter) and the build must stop.

### 6.5 The generator/gate consistency invariant

Per-section citation minimums must leave headroom under the issue-level G2c
ceiling. `build_map()` asserts `CITE_SUM_BAND`:

```
sum(cite_target) must be in [55, 72]   against G2c band [60, 85]
```

At `WORDS_PER_CITE = 34` the minimums summed to **78** against a ceiling of
85. A writer that merely met every section minimum landed 7 short of the
ceiling, so the August v4 build cited 87 and failed G2c **while every
individual section had done exactly what it was told**.

The fix moved the generator (`34 → 42`, minimums now 68), not the gate. The
assertion exists so a future tuning change cannot silently recreate it.

Related: `RULES` used to say "cite MOST of the papers in your evidence block".
With 136 papers offered across five sections, that instruction *guarantees*
overshoot. It now says the block is "a pool to select from, not a checklist".

---

## 7. Failure modes

Every bug below actually happened. **The overwhelming majority produced
plausible output instead of an error.** Internalise the pattern: this class of
bug does not announce itself, so the pipeline's own reports cannot serve as
verification.

### 7.1 The silent-zero class

| # | Bug | Symptom |
|---|---|---|
| 1 | Run directory relocated mid-run when a config file was added | **0 venues from a 655-work corpus**, no crash |
| 2 | Subprocess return code ignored | every writer call failed, stage reported **"181 cards, 0 dropped"** |
| 3 | `.done` marker trusted by existence | marker said `n_cards: 0`; a resume would have built the paper with zero cards |
| 4 | Guard 3 destroyed what guard 2 verified | 5 quotations shipped without their own number, `nulled_number: 0` |
| 5 | Orphaned writer processes rewrote drafts after the build read them | all gates passed against text that changed seconds later |
| 6 | Field read from wrong dict | `n_t80 = 0`, empty figure panel, 4 real values in the cards |

Fixes: pin the run id to `runs/<month>.active`; raise on non-zero rc; make
`is_done()` read the marker **payload**; truncate before checking; fingerprint
and freeze inputs; verify field locations.

> **Operating rule: a zero is a bug until proven otherwise.**

### 7.2 Fabrication: the worst bug

The v3 abstract was a Python f-string using positional lookups into filtered,
sorted lists:

```python
[v for v, c in cert if c["device"]["architecture"] in ("p-i-n", "n-i-p")][0]
```

The extractor had labelled a perovskite/silicon tandem as `p-i-n`, so this
returned 33.1% and attached it to a paper whose certified value is 27.12%. A
second fallback reported 28.84% for a paper measuring 29.57%. `n_cited` read
the *cap* (180) instead of citations actually resolved (110).

**Three fabricated numbers in the most-read part of the paper, in the one
section that bypassed the evidence chain because it was authored in code.**

Fixes: every highlight resolves ONE card by explicit DOI fragment and fails
closed if the fragment matches ≠1 card; **positional indexing into filtered
lists is banned**; and in v4 the abstract is written by the writer with
substituted values, so the failure mode no longer has a home.

### 7.3 Verifier bugs

Six checks have reported failures that were faults in the **checker**:

1. A title substring search failed because PDF text line-wraps as
   `"Buried-\nInterface"`. Normalise whitespace before substring checks.
2. A centring check flagged failure because the loop included the legitimately
   left-aligned `Abstract` heading.
3. `\[(\d+)(?:,(\d+))*\]` — a **repeated capture group**, of which Python
   retains only the last repetition. For `[8,9,10]` it yielded `("8","10")`,
   dropping 9, and reported non-monotonic ordering on a correct manuscript.
4. G8 compared each section against the **whole** prior manuscript, diluting
   every ratio to ~0.01. The gate could never have fired.
5. G8 counted 631 shared shingles that were the funding number, the AI
   declaration and figure captions — text that **must** repeat every month.
6. An ad-hoc PDF leak scan flagged "gate check" inside the legitimate sentence
   "…statistics, figures and gate checking are deterministic scripts". The
   real regex is `\bgate checks?\b`; "gate checking" has no word boundary
   after "check". **G4 was right and the ad-hoc scan was wrong.**

> **Rule: a check that disagrees with the artifact is a suspect until you know
> which one is wrong.** Bugs 4 and 5 were found only by self-testing the new
> gate against known-bad output, which is now a permanent test.

### 7.4 Concurrency

Two orphaned draft processes kept writing after their runs reported complete.
`sec4.md` carried mtime 15:45:13 while the PDF built at 15:43:43, and
`prose_words` drifted 4498 → 4353 → 4317 → 4304 across builds. All gates passed
every time, against a draft set that changed seconds later, so **no gate report
described the shipped file**.

Fix: SHA-256 fingerprint every draft, refuse to build if any changed within
20 s, and refuse if `agy` is alive (§6.3).

### 7.5 Patching discipline

Exact-string patching failed repeatedly on stale anchors, and because the
assertion fires **before** the file write, a "successful" run left the file
untouched. Once this meant a gate (`G2c`) existed in a status report but not in
the code.

> **Rule: after any patch, grep for the NEW text to prove it landed. After two
> failures on one anchor, rewrite the enclosing function or file.**

### 7.6 The v4 incidents

Nine more, all found by running:

| # | Bug | Why it mattered |
|---|---|---|
| 1 | 26 inline `(?i)` groups in the narration regex | Python 3.11 raises `global flags not at the start`; the module **failed at import**, so stage 13c died before writing one section |
| 2 | Month hardcoded `"July 2026"` in 5 sites | an August run drafted August evidence under July headings; the Figure 1 caption survived to the shipped PDF |
| 3 | R35 fail-closed on four July DOI fragments | correct behaviour — but swapping DOIs alone was **not** safe, because the surrounding prose named July's mechanisms. August numbers under July mechanism text is §7.2 in a new costume; every clause was rewritten from the bound card's own claim |
| 4 | `[100]` Miller index read as citation 100 | G2b failed a correct manuscript (§4.3) |
| 5 | `s19` read `draft/sec2,6,8` from the **v1** draft dir | a v3-only month never creates it → `FileNotFoundError`. Reusing July's text was impossible: it names its own month and counts. Notes S1/S3/S6 are now composed deterministically from stats |
| 6 | `s19` SI title and `s20` data-pack README hardcoded July | both now ask the build for the derived title |
| 7 | `s19` read `gate['G2']['cited']` | v4's G2 dropped that key → `KeyError`. **A supplementary table must never be what stops a verified manuscript shipping**; the gate table now reads defensively |
| 8 | Per-section cite minimums summed above the G2c ceiling | §6.5 |
| 9 | Dictated phrasing in intro and frontier prompts | §4.1c |
| 10 | Narration filter existed in **three** divergent copies, build-side narrowest | "I have launched the search command and will wait for it to finish." passed G4 and reached the shipped PDF under the section 8 heading. **A gate reporting pass on leaked text is worse than no gate.** Now one object, identity-tested (§6.4) |
| 11 | `AI_DECL` read live config instead of provenance | the August PDF declared an extractor that never touched it (§8.4) |
| 12 | `s19`'s `n_cited_main` used a plain citation regex | the SI's "Cited in the main text" row counted `[100]` (Miller index) as a citation. **A guard documented in the handbook but applied in only one consumer is the same divergence that let the narration leak through** (§4.3) |
| 13 | Notation rules matched ASCII `-` while the writer emitted U+2212 | `V−1`, `s−1`, `10−3` shipped flat in the electron-mobility line, and the ASCII-only gate reported **pass** on it. Fixed by normalising Unicode in the converter *and* the gate, then migrating to siunitx/mhchem (§4.4) |
| 14 | `\vspace` after `\end{minipage}` silently discarded | **three** blind em-value tunings (0.9 → 2.2 → 3.6em) all failed because the space lands in horizontal mode and LaTeX drops it. Source asked 3.6em, page rendered **0.11 pt**. Only measuring the artifact found it (§4.5) |
| 15 | Hyperlinking each marker broke citation merging | `\href{}{[12]}` put brace groups between adjacent brackets, so `[1,2,3,4,5]` shipped as `[1] [2] [3] [4] [5]`. Two correct behaviours fighting; fixed by merging on plain numbers **then** linking inside the group. Note G9b passed at 122 linked markers while merging was broken: "are markers linked?" and "did grouping survive?" are different questions |
| 16 | The LaTeX preamble lived in gitignored `.staging/` | a fresh clone would have lost siunitx and mhchem and reverted every unit to plain text. **Anything the build cannot run without belongs under version control** (§10.3) |

### 7.7 The back-issue incidents (June and July 2026 on v4)

Rebuilding two earlier months on the v4 chain surfaced six more. Note the
shape: **not one of them was a writer failure**, and two were faults in
checking rather than in output.

| # | Bug | Why it mattered |
|---|---|---|
| 1 | The writer transcribed `10.1016/joule.2026.102538` for the card `10.1016/j.joule.2026.102538` | G1 refused it, correctly — a citation that resolves to nothing is the founding defect. But the writer copies a key out of its evidence block by hand, so a lost character is a **transcription** failure, not a fabrication. `canon_work_key()` now matches on canonical form (lowercased, non-alphanumerics dropped, Elsevier's `/j.` removed) and must match **exactly one** card: an ambiguous alias still fails. A test asserts no two real cards of either shipped month collapse together |
| 2 | `_VAL` matched `1.6 x 1017` but not `1.6e17` | June's writer used e-notation, so `_QTY` never matched, the unit shipped flat, and G9a reported `cm-3` on the rendered page. **The converter had silently supported only one of the two ways a writer can spell a power of ten** |
| 3 | `J` was missing from `_UNITS` | July reported a fracture energy of `4.82 J m-2`. A unit **run** matches as a whole, so one unknown token left the neighbouring `m-2` flat and G9a reported that instead. The lesson generalises past joules: **a missing unit does not degrade gracefully, it drops every unit beside it** |
| 4 | The gaps prompt ended `"End with one or two sentences on what would make next month's literature more useful..."` | §4.1c, and it took **two** issues to see: the writer returned essentially that sentence in June and again in July, and G8 failed on seven shared shingles. A prompt containing a sentence gets that sentence back forever. Fixed by stating the job, and by adding `prior_closing_block()`, which quotes last month's actual closing text — **a recurring instruction needs its own recurring output shown to it, or nothing makes month N+1 differ from month N** |
| 5 | G8 counted the ISOS abbreviation expansion as reuse | G7 *requires* that expansion and `expand_abbrev()` inserts it, so **G8 was failing prose for obeying G7**. Six of July's shingles were that long form plus the DOI after it. Mandated expansions, DOIs and URLs are now stripped before shingling; the August-v3 self-test still fails as it must, proving the gate did not go blind. Same class as the 631 funding shingles (§7.3 #5): **text the pipeline itself authors can never be writer reuse** |
| 6 | `verify_notation_pdf.py` took a path and defaulted to a **hardcoded August** manuscript | run during the June cycle it verified the wrong file and reported PASS. Same class as the month hardcoded in five sites (§7.6 #2). Every verifier now takes `<month> [version]` so the month can only come from argv |

Two of these lived in the **checking layer**, which is why they are worth
their own section:

- #6 is a verifier that passed by examining a different artifact.
- The G8 self-test on the August v3 issue **silently began passing** once
  July's run dir gained a `manuscript_v4.md`, because the gate compares against
  the newest prior on disk and the fixture never named the file it meant.
  `novelty_gate()` now accepts an explicit `prior_path` for self-tests.

> **Rule: a test asserting a HISTORICAL fact must pin every input it depends
> on. A fixture that resolves "the latest prior issue" describes a moving
> target, and it will stop testing what you wrote it to test without ever
> failing.**

### 7.8 Misattribution: a real number on the wrong device

**The worst defect the pipeline has shipped since §7.2, and the evidence chain
did not catch it, because nothing in the chain was broken.**

June 2026's abstract stated `32.95% in single-junction inverted cells`, and its
body read `In single-junction inverted (p-i-n) cells, certified PCE reached
32.95% [3]`. Figure 1 plotted it under single junction. Havid found it by
reading the PDF and checking the cited paper's abstract.

Every guard passed, correctly:

- the anchor was **verbatim** in the source abstract
- the value **appeared inside its own anchor**
- G1 resolved the citation; G3 confirmed the number **traced to a card**

The number was real. **The device was wrong.** The card's own anchor reads
`"a certified 32.95% perovskite/Si tandem efficiency"`, while its
`architecture` field said `p-i-n` — and both were true statements about
*different things*. The paper genuinely is a p-i-n flexible cell; its abstract
also quotes a tandem record. **One abstract carried two devices, and the label
followed the paper while the number came from the other one.**

| # | Bug | Fix |
|---|---|---|
| 1 | `architecture` described the PAPER, not the device the certified value was measured on | **Guard 5** in `s09_cards.py`: if the certified anchor names a multi-junction stack, the architecture is corrected to match **the number**. A number and its device label must come from the same sentence |
| 2 | `P_TOP_SJ` excluded tandems by searching the **title** | that paper's title names neither tandem nor silicon. Now excludes on the **anchor** first, then the title and architecture, and fails toward excluding |
| 3 | No gate could see it | **G3c-abstract-physics**: a single-junction value above the Shockley-Queisser limit (29.4%) fails the build. 32.95% is not merely mislabelled, it is *impossible* for one junction |

Then the guard found the **same defect in July** — a certified 33.1%
perovskite/silicon tandem labelled `p-i-n`, appearing in three body sites. One
reader-reported defect in one month was a class defect in two. August was
clean.

`scripts/repair_arch_from_anchor.py` applies guard 5 to already-extracted
cards, so a shipped month can be corrected without a 35-minute re-extraction
that would perturb every other card. It is deterministic, idempotent, backs up
the original, and runs no model. A test then asserts every shipped month stays
clean, so a re-extraction cannot quietly reintroduce the mislabel.

> **Rule: verifying that a number is REAL is not verifying that it describes
> what the sentence says it describes. Bind every number to the device, sample
> and conditions named in its own anchor — an abstract that reports two devices
> will otherwise lend the wrong one its record.**

> **Corollary: add a plausibility gate wherever physics bounds a quantity.**
> Traceability proves provenance, not meaning. A value above a physical limit
> is self-refuting to an expert reader, and the build should not need one.

---

## 8. Deliverables

```
manuscript/<YYYY-MM>_v4/
  manuscript_v4.pdf          main text
  manuscript_v4.md           source
  supplementary_v4.pdf       method, audit, statistics, limitations
  fig/*.pdf                  vector figures
  stats.json                 every citable number
  claim_cards.jsonl          extraction records with source quotations
  12_section_map.json        this issue's generated section map
  gate_report_v4.json        11 gate results + draft fingerprints
  chemrxiv_<YYYY-MM>.tar.gz  archival bundle (NOT the upload)
  chemrxiv/                  the submission package
  chemrxiv/manuscript_v4.pdf the file uploaded to ChemRxiv
  chemrxiv/submission_metadata.json  paste-ready portal fields
  chemrxiv/SUBMISSION_CHECKLIST.md   generated manual steps
  chemrxiv/manuscript.tex    standalone LaTeX (journal transfer)
  data/*.csv                 the data pack, incl. token accounting
```

### 8.1 ChemRxiv package

The target is **ChemRxiv**, not arXiv (changed 2026-09-09; the topic is
chemistry-scoped). Everything about the platform is read from
`config/preprint.yaml` -- platform name, slug, subject categories, licence,
DOI prefix. Never hardcode the platform in a stage again.

- **The main upload is the rendered PDF.** ChemRxiv takes PDF or `.docx` by
  drag-and-drop and does not compile LaTeX. Stage 20 fails closed if
  `manuscript_<ver>.pdf` is missing, because a package without its main file
  is not a package.
- **Subject categories, not archive codes.** `Energy` primary,
  `Materials Chemistry` secondary (NOT `Materials Science` -- ChemRxiv
  lists both and they are different categories). arXiv's `physics.app-ph`
  is meaningless here.
- **The DOI does not exist until posting.** ChemRxiv assigns one under
  `10.26434`. `preprint_doi` stays `null` and the checklist asks the human to
  paste it back. A script must never invent this value.
- **Generated checklist.** The route is a manual portal upload, so
  `SUBMISSION_CHECKLIST.md` and `submission_metadata.json` are generated with
  paste-ready title, abstract, corresponding author and licence. The abstract
  is read out of the built manuscript so it cannot drift from the PDF.
- **Archival LaTeX is still built.** Relative figure paths, the `.bbl`, and a
  pdflatex-portable preamble (strip `fontspec`) are kept for a later journal
  transfer, and the standalone compile still proves the preamble is portable.
- **Migration guard.** The stage fails closed if the word arXiv survives in
  the generated metadata or checklist.
- **arXiv remains a HARVEST SOURCE.** Stage 01 queries the arXiv API, the
  ledger has an `arxiv_id` column, and cited works carry arXiv DOIs. That is
  unrelated to where we submit and must not be renamed.

### 8.2 CSV data pack

The point: a reader can trace any figure or claim back to a sentence in a cited
paper's abstract.

| File | Contents |
|---|---|
| `corpus_metadata.csv` | every work passing the scope gate |
| `extracted_claims.csv` | one row per number, **each with its verbatim quotation** |
| `figure1..4_*.csv` | rows behind each panel, **including exclusions and why** |
| `reporting_audit.csv` | detection rates, both tiers, with denominators |
| `axis_distribution.csv` | corpus and depth counts per axis |
| `statistics.json` | every number the manuscript may cite |
| `extraction_records.jsonl` | full structured records |
| `gate_report.json` | automated gate results |
| **`token_usage.csv`** | one row per LLM call and per deterministic stage |
| **`token_summary.csv`** | totals per role / CLI / model |

### 8.3 Token accounting (required on every full-stack run)

`s21_tokens.py` reads `runs/<m>/tokens.jsonl` plus the `.done` markers and
emits both CSVs. Columns: `month, stage, process, role, cli, model, batch,
n_papers, words_out, tokens_in, tokens_out, cache_read, est_tokens_out,
token_source, at`.

**Reported and estimated are never mixed into one figure.** `agy -p` prints
prose to stdout and reports no usage, so writer rows carry
`token_source=estimated` with `est_tokens_out = words × 1.33`. The extractor
reports real usage and is marked `reported`. Deterministic stages appear with
`token_source=deterministic` and zeroes, so the CSV is a complete process
inventory rather than an LLM-only log.

**Cost incurred is not cost of the artifact.** The ledger is append-only, so a
section redrafted three times leaves three rows. Every row carries `attempt`
and `shipped`, and the summary reports both: `*_total` is what was spent,
`*_shipped` is what produced the manuscript. Reporting one number for both
would overstate the artifact roughly threefold.

August 2026 v4, measured (63 rows, 32 shipped):

| role | cli | model | calls total | calls shipped | tokens_out total | tokens_out shipped | cache_read |
|---|---|---|---|---|---|---|---|
| extractor | opencode | qwen3.8-flash* | 12 | 12 | 134,472 | 134,472 | 83,897 |
| writer | agy | gemini-3.8-flash-high | 29 | 9 | est 17,717 | est 5,571 | — |
| none | python | — | 13 | 13 | 0 | 0 | 0 |

The writer's 29 calls span four draft attempts (A-D) plus per-section retries;
only the last of each stage shipped. \* August's cards were extracted by
`qwen3.8-flash`. That was also the configured extractor at the time, so config
and record agreed and `provenance()` emitted no mismatch warning. **Since the
2026-09-11 swap to `glm-5.3-flash` they no longer agree**, and a rebuild of any
already-extracted issue will now emit the warning while correctly declaring the
recorded model (§2.1, §8.4).

### 8.4 Provenance comes from records, never from live config

The AI Usage Declaration names the extractor, the writer and the reviewer.
Those are **facts about what ran**, so they are derived from the artifacts:
the extractor from the mode of `card["extractor"]["model"]`, the writer from
the `tokens.jsonl` rows for `13d_*` stages.

They used to be read from `config/models.yaml`. That shipped a false
statement: the extractor model was changed mid-session, *after* August's
extraction, and the rebuilt PDF declared `muse-spark-1.3-contributor` while
all 144 cards recorded `qwen3.8-flash`. Every earlier issue agreed with config
only by luck of timing.

The config was later reverted to `qwen3.8-flash`, so the two agreed again and
the warning stopped firing. **That is not the reason the guard exists.** It
exists
because a provenance field derived from current state instead of from the
artifacts is a silent misstatement whenever the two drift, and they will drift
again the next time a model is swapped.

`provenance()` in `s18d` now fails closed if cards disagree about the
extractor, or if more than one model wrote prose (Q40 allows exactly one voice
per issue), and **prints a loud mismatch warning** if the record disagrees with
config while declaring the record. The record wins; config being stale is the
operator's problem to see, not the build's to paper over.

> **Rule: a back-matter fact about which model did what is prose reaching a
> reader. It traces to the evidence chain like every other claim.**

---

## 9. Porting to a different topic

**Postponed by Havid (2026-09-08): perovskite PV first, until the writing is
satisfactory. A quantum-dot pilot comes later.**

Recorded now so the work is not re-derived. Four files are topic-specific:

| File | Change |
|---|---|
| `config/axes.yaml` | the 6 mechanism axes + weighted keywords |
| `config/exclude.yaml` | off-topic terms for the post-filter |
| `config/title_terms.yaml` | title frame, axis phrases, banned-in-title list |
| `s01_harvest.py` FILTER | the search conjunction |

**But the deeper lock is the extraction schema**, and swapping `axes.yaml`
would not touch it: `pce_certified`, `pce_champion`, `t80_h`,
`active_area_cm2`, and `architecture: p-i-n | n-i-p | tandem_2T | module` are
photovoltaic concepts. Quantum dots would need PLQY, emission peak, FWHM,
ensemble vs single-dot, photostability.

The eventual fix is a **metric registry** (a new domain.yaml under config/,
which does not exist yet) declaring
metrics with units and direction, a sample taxonomy, and figure *roles*
("frontier axis", "penalty x-axis", "durability metric"), from which the
extraction prompt is generated and figures plot by role. Measured topic-lock
today: `s13d` 22 strings, `s18d` 20, `s09_cards` 10, `s11b` 9, `s19` 4.

Keep the gates, the guards, and the build untouched: they encode format and
evidence discipline, not subject matter.

### 9.1 Corpus gate traps, already paid for

- Putting `-term` in an OpenAlex query returns count **0**, not a filtered set.
  Never put exclusions in the query; exclude in Python afterwards.
- Wildcards are rejected on `title_and_abstract.search`. Spell out variants.
- The response key is `group_by`, not `grouped_by`.
- `summary_stats` exists only on `/sources/{id}`, and `h_index` lives **inside**
  it, not as a top-level select field.
- Assert the count band with `per-page=1` **before** paginating. Abort if the
  count is 0 or outside the expected range.
- arXiv has no server-side month filter; filter `published` client-side.

---

## 10. Environment

### 10.1 Windows specifics, all hit for real

- CLI tools may be POSIX shell scripts bash can run but `CreateProcess` cannot.
  Resolve the real `.exe` (§2.2).
- `cmd.exe /c <path with spaces>` splits on the space in
  `<HOME>`. Bypass the shim entirely.
- winget installs may land off PATH. **pandoc lives at
  `%LOCALAPPDATA%\Pandoc\pandoc.exe`** and is *not* on PATH; the build probes
  known locations. Do not "fix" PATH and do not trust `shutil.which` alone.
- MSYS `/tmp` is invisible to native Python. Use a workspace path.
- `taskkill //F` has its flags eaten by MSYS. Use PowerShell `Get-Process`.

### 10.2 Python specifics

- f-strings cannot contain backslashes. Build regex strings outside the
  f-string when verifying PDFs.
- **Inline `(?i)` mid-pattern raises `global flags not at the start` on 3.11.**
  Use `flags=`. This crashed a whole stage at import (§7.6).
- Repeated capture groups retain only the last repetition (§7.3).
- A `git rm`-pending file still counts as tracked: deleting files that tests
  enumerate from `git ls-files` breaks them until the deletion is staged.

### 10.3 Dependencies

```
pymupdf langdetect rapidfuzz matplotlib requests pyyaml pytest
pandoc 3.11+   tectonic   agy   opencode   claude
```

**LaTeX packages** (`config/tex/manuscript_head.tex`): `graphicx`, `float`,
`caption`, `etoolbox`, **`siunitx`**, **`mhchem` (version=4, pinned)**.

tectonic downloads `mhchem.sty` and `chemgreek.sty` from its own bundle on
first use, so **no manual TeX Live install is required** — verified
2026-09-08. Before adding any further package, compile a minimal document
with it and check the log for `downloading <pkg>.sty`; do not assume
availability.

The preamble is **tracked in the repo**. It previously lived in gitignored
`.staging/`, where a fresh clone would have silently lost siunitx and mhchem
and reverted every unit in the paper to plain text. Anything the build cannot
run without belongs under version control.

---

## 11. The monthly checklist

Run in this order. Anything marked **HUMAN** cannot be delegated.

```
[ ] 1. git status clean; git log -1 to confirm the starting point
[ ] 2. probe the tools:  agy / opencode / claude / tectonic resolve,
       pandoc.exe exists at its known path, 7 python deps import
[ ] 3. HUMAN: .env credentials present (OPENALEX_API_KEY, UNPAYWALL_EMAIL).
       Typed into .env directly, never pasted into a chat, prompt or log
[ ] 4. writer probe:  agy -p "Reply with exactly: OK"   (fails closed, no fallback)
[ ] 5. extractor JSON-shape probe if the model changed (§2.1)
[ ] 6. orphan check:  no agy process alive
[ ] 7. run stages 01 -> 04_10, checking every .done payload for a zero
[ ] 8. s09_cards, then verify_anchors.py  <- MANDATORY, must exit 0
[ ] 9. s11b figures; confirm n_t80 > 0 and the lens split looks sane
[ ] 10. s13d draft; watch for "STRIPPED narration" lines in the log
[ ] 11. s18d build; ALL 11 GATES MUST PASS
[ ] 12. s19 v4, s20 v4, s21 v4
[ ] 13. rendered-PDF verification (§12)
[ ] 14. similarity proof against the prior issue
[ ] 15. HUMAN: READ THE PDF
[ ] 16. commit: code fixes and artifacts in separate commits
```

### 11.1 Why step 15 cannot be automated

Gates catch **regressions**. Humans catch **new** defects. Every defect class
in this handbook entered it because Havid read a rendered page:

- a simulated data point sitting on a measured-performance figure
- affiliations 24.7 pt left of the page midline
- a doubled figure caption
- out-of-order citation numbers
- an August issue that read like July's
- **"I have launched the search command and will wait for it to finish."**
  under the section 8 heading, with G4 reporting `pass`

### 11.2 Outstanding human task

**The 200-paper validation label sheet** (3-4 h, still not done). Until it
exists, every audit percentage ships as "detected in at least X%" rather than
"X% (precision 0.91)". This is the single highest-value human task in the
project.

---

## 12. Quick reference

```bash
# full month, v4 chain
M=2026-09
for s in s01_harvest s02_06 s04_10 s09_cards; do
  python scripts/stages/$s.py $M || break
done
python scripts/verify_anchors.py $M            || echo "ANCHOR CHECK FAILED"
python scripts/stages/s11b_figures_v2.py $M
python scripts/stages/s13d_draft_v4.py   $M
python scripts/stages/s18d_build_v4.py   $M
python scripts/stages/s19_si.py          $M v4
python scripts/stages/s20_chemrxiv.py    $M v4
python scripts/stages/s21_tokens.py      $M v4
```

Rendered-artifact verification:

```bash
python scripts/verify_pdf.py $M v4        # exits non-zero on any failure
python scripts/verify_notation_pdf.py $M  # LEVEL 2: span geometry (§4.4b)
```

**Nothing in it is typed in.** The month comes from argv, the expected title
from the section map, the reference count from `gate_report_v4.json`, and the
stale-month list from every other `runs/*.active` on disk. The handbook used to
carry this as a snippet with two hardcoded constants, which is precisely how
the "July 2026" class of bug is born: the operator edits three of four sites
and the fourth ships.

Ten checks, each encoding a defect that shipped once:

| Check | Defect it catches |
|---|---|
| title names this month | month hardcoded in 5 sites (§7.6) |
| no stale month name | Figure 1 caption said "July" in an August PDF |
| no unresolved placeholders | `{{P_TOP_CERT}}` reaching a reader |
| no agent narration | "I have launched the search command…" (§6.4) |
| no doubled figure captions | "Figure 4: Figure 4." |
| no unmerged citation runs | `[8,9] [10]` |
| citations monotonic | `[1],[5],[6],[10],[60]` |
| every reference is cited | an orphan reference-list entry |
| every mapped section present | a section silently dropped from the build |
| page count matches gate report | the gate describing a different file (§7.4) |

It also re-reads the gate report and fails if any gate failed, so a stale
"all pass" memory cannot substitute for the artifact.

Use `find_narration` from `hygiene`, **not** an ad-hoc substring scan: an
ad-hoc scan produced a false positive on the legitimate phrase "gate checking"
(§7.3 bug 6).

**If a gate fails, fix the output. Never the gate.**

---

## Appendix A. Configuration reference

`config/gates.yaml`

| Key | Value | Used by |
|---|---|---|
| `count_band` | `[250, 1200]` | s01 pre-pagination assertion |
| `max_pages` | 15 | s01 cursor pagination cap |
| `depth_target` / `depth_band` | 200 / `[100, 300]` | s04_10 selection |
| `axis_min_depth` | 12 | s04_10 per-axis floor |
| `sensitivity_draws` / `seed` | 200 / 0 | s04_10 reproducibility |
| `anchor_word_max` | 25 | s09 guard 3, verify_anchors |
| `paper_v3.total_page_band` | `[12, 17]` | G5 |
| `paper_v3.content_page_band` | `[8, 11]` | G5 |
| `novelty.body_max_ratio` | 0.25 | G8 |
| `novelty.abstract_max_ratio` | 0.30 | G8 |
| `novelty.shingle_words` | 12 | G8 |
| `abstract.word_band` | `[260, 340]` | G3b |
| `citations.total_band` | `[60, 85]` | G2c |
| `paper.*` | v1 two-column, **retired** | nothing on the v4 path |

`section_map.py` knobs are listed in §4.1. `config/models.yaml` holds the role
assignments in §2. `config/title_terms.yaml` holds the title frame, per-axis
phrases, `banned_in_title`, and `comparative_markers`.

## Appendix B. Version history

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-09-07 | first handbook, written from the July v3 build |
| **2.0** | **2026-09-08** | v4 pipeline: generated section map, body→gaps→abstract order, citation-free/digit-free abstract, G3b + G8, unified narration filter, generator/gate consistency invariant, token accounting, `OLD/` policy, monthly checklist |
| **2.1** | **2026-09-12** | extractor and structure-reviewer pin moved to `glm-5.3-flash` with the probe result recorded in §2.1 (shape pass, `t80_h` null caveat); 2026-H1 standardised to the v6 edition; v5 reader-facing artifacts archived to `OLD/2026-H1_v5_artifacts/` |

## Appendix C. Glossary

| Term | Meaning |
|---|---|
| **anchor** | verbatim quotation from a paper's abstract that proves a number |
| **card** | one paper's structured extraction record (`claim_cards.jsonl`) |
| **depth tier** | the subset read closely and cited individually |
| **axis** | mechanism category (composition, defects, interfaces, architecture, stability, scale_up) |
| **lens** | study type (experimental, theory, review, scale_up) |
| **section map** | generated per-issue plan of sections, ceilings, cite targets |
| **angle** | rotating instruction changing the order of attack, never the evidence standard |
| **shingle** | contiguous 12-word span, used by G8 to detect lifted sentences |
| **silent zero** | a stage reporting success with a zero count instead of failing |
