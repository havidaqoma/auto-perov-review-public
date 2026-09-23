# AGENTS.md

Instructions for an AI agent working in this repository.

This repo produces peer-review-grade literature reviews automatically, at three
cadences: monthly, half-year, and yearly. It is not a normal codebase. It is a
set of machine-checked guarantees about how scientific prose gets written, and
most of its design exists to stop a language model from doing the obvious
thing.

Read this file fully before you edit anything. It takes two minutes and will
save you from the five mistakes that every agent makes here.

---

## First: do you actually need to change anything?

Most people who clone this repo want to check our published numbers. That needs
no model, no API key, and no money:

```bash
pip install -r requirements.txt
python reproduce.py --tier 0
```

Ten checks, fully offline. If you were asked to "verify this paper", you are
done after that command. Do not start editing code.

---

## The contract

These principles are quoted from the handbooks. They are not advice. Each one
exists because a specific defect reached a shipped PDF.

`tests/test_agents_md.py` asserts that every principle below still matches its
handbook heading word for word, so this file cannot drift out of date without
the build going red.

### Core, applies to every cadence

From `MASTER_HANDBOOK.md` section 0:

- **0.1 Format is generated, never model-written**
- **0.2 Every defect becomes a gate, never a prompt reminder**
- **0.3 Verify the artifact, not the process**
- **0.4 No prose reaching a reader may be authored outside the evidence chain**
- **0.5 A generator and its gate must be mutually consistent**

### Period editions (half-year)

From `MASTER_HANDBOOK_H1.md` section 0, which states the five above apply
unchanged:

- **0.6 Extend by ADAPTER, never fork**
- **0.7 A period edition must answer what a single month cannot**
- **0.8 A period title is a claim about coverage, and must be gated**
- **0.9 Fixing the reported site is not fixing the bug**
- **0.10 A number means nothing without its measurement conditions**
- **0.11 Excluded is not the same as erased**

### Yearly

From `yearly/MASTER_HANDBOOK_YEARLY_v2.md` section 0, which restates the core
five and adds three:

6. **Never widen a gate to make output pass.**
7. **A gate that stops noticing something is worse than no gate.**
8. **An artifact that exists is not an artifact that shipped.**

---

## What those mean for you, concretely

The five mistakes an agent makes in this repo, in the order it makes them.

### 1. Do not put formatting rules in a prompt

The title block, affiliations, citation numbering, reference list, figure
environments, and every number in the abstract are emitted by
`scripts/stages/s18d_build_v4.py`. The writing model never sees them.

If a heading looks wrong, fix the builder. Adding "please format the heading
correctly" to a prompt looks like it worked and silently stops working the next
time the model samples differently.

### 2. Do not fix a defect with a prompt reminder

When you find a bug, the correct response is an assertion that fails the build.
Not an instruction telling the model to behave.

A defect with a gate cannot come back next month. A defect with only a prompt
reminder comes back as soon as sampling changes. The monthly handbook calls
this the highest-value habit in the whole workflow.

### 3. Do not trust a stage that reports success

Parse the rendered PDF and assert on what is physically on the page.

Every format defect in the handbook was found by a human reading the output,
and each one had already passed a markdown inspection. There is a corollary
that has cost real time: when a check disagrees with the artifact, one of them
is wrong, and it is often the check. Six verifier bugs have happened so far.

### 4. Do not write reader-facing prose in a script

This includes the abstract. An earlier version closed every abstract with three
fixed sentences that were asserted regardless of that month's evidence. No gate
could see it, because the abstract gate validates only numerals.

If a sentence reaches a reader, it came from the evidence chain or it is a bug.

### 5. Do not widen a gate to make output pass

When a generator and its gate collide, the generator moves. This has come up
four times in the project and the answer was the same every time.

If a gate is genuinely wrong, say so out loud and explain why in your output.
Do not quietly raise a threshold until the build goes green.

---

## Copying code is the other big one

`s18d_build_v4.py` carries all the gates, the citation merge and link ordering,
the abstract placeholder boundary, the notation pass, and the title grammar.
The half-year edition does not fork it. It rebinds the names the stages resolve
at call time.

A guard that exists twice diverges. The handbook records the divergent-copy
failure three times. One of them put the sentence "I have launched the search
command" into a shipped PDF, because a narration filter existed in three copies
and the build-side copy was the narrowest.

If three stages need the same new behaviour, extract one module and import it
from all three.

And when you fix a bug, grep for its class before moving on. Every period
defect so far was the same bug in two or more places.

---

## Running the pipeline

Stage order is defined in code, not here. Read `STAGES` in
`scripts/run_month.py` and the stage list in `yearly/scripts/run_yearly.py`.
The runner is a sequential state machine, so a failed stage stops the run
instead of letting later stages build on bad input.

```bash
python scripts/run_month.py 2026-09              # monthly
python scripts/run_h1_backfill.py                # half-year aggregation
cd yearly && python scripts/run_yearly.py 2025   # yearly
```

Before any of that, you need credentials:

```bash
cp .env.example .env     # fill in your own keys
```

Never commit `.env`. Never paste a key into a config file, a prompt, or a
commit message. `tools/ship_audit.py` scans for credentials and must pass
before anything is pushed.

### Pointing at your own models

`config/models.yaml` declares roles, not vendors. Point them at whatever you
have access to. Three settings are structural and you should keep them:

- `writer_rule: strict` means exactly one model writes prose. The reviewers are
  read-only and cannot edit.
- `fallback_policy: fail_closed` means a missing model stops the run. It does
  not silently downgrade to a weaker model, because a silent downgrade produces
  output that looks fine and is not.
- No gate calls a model. Swapping models therefore cannot loosen a threshold.

The model that reviews an output is never the model that produced it. Self
review does not count as review.

---

## Where the truth lives

| Question | File |
|---|---|
| How does the monthly cadence work? | `MASTER_HANDBOOK.md` |
| How does the half-year cadence work? | `MASTER_HANDBOOK_H1.md` |
| How does the yearly cadence work? | `yearly/MASTER_HANDBOOK_YEARLY_v2.md` |
| What stages run, in what order? | `scripts/run_month.py` |
| What gates exist? | `scripts/stages/s18d_build_v4.py` |
| What are the thresholds? | `config/gates.yaml` |
| Which model does what? | `config/models.yaml` |
| How do I verify the published claims? | `reproduce.py` |

The handbooks are long. `MASTER_HANDBOOK.md` is over 1,400 lines and
`tests/test_handbook.py` asserts that its gate table matches what the build
actually emits, so it is worth trusting. Read section 0 in full, and section 7
(failure modes) before debugging anything.

---

## Before you finish

```bash
python -m pytest tests/ -q                   # monthly and half-year
cd yearly && python -m pytest tests/ -q      # yearly
python reproduce.py --tier 0                 # the full offline check
```

All three must pass. If you changed a handbook, expect a test to tell you that
this file no longer matches it. That is the mechanism working.

State plainly what you did not manage to verify. A skipped step reported as
done is the one failure mode this entire repository is built to prevent.
