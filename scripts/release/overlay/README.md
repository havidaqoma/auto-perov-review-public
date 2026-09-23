# Automated perovskite photovoltaics literature review

A validator-gated pipeline that turns a scholarly-database query into a
review manuscript, at three cadences: **monthly**, **half-year**, and
**yearly**. This repository holds the code, the stored run artifacts, the
gate reports, and the rendered documents for every issue produced so far, so
that a third party can re-verify the results without re-running anything that
costs money.

The system's design claim is narrow and worth stating plainly: **a language
model writes prose and extracts values, and a deterministic script decides
whether that output is allowed to ship.** Seventeen gates compute over stored
JSON. No gate consults a model, and the model that reviews an output is never
the model that produced it.

## What is here

| Cadence | Code | Issues shipped | Stored runs |
|---|---|---|---|
| Monthly | `scripts/stages/s*` | 2026-01 to 2026-08 | `runs/2026-0*` |
| Half-year | `scripts/stages/h1_*` | 2026-H1 | `runs/2026-H1` |
| Yearly | `yearly/scripts/stages/` | 2025 | `yearly/runs/` |

Measured contents of this tree:

- **16,437 corpus rows** across 11 stored runs, after normalisation and
  deduplication
- **2,658 claim cards**, each carrying the anchor span it was extracted from
- **21 gate reports**, of which **9 verdicts are not `pass`** and every one of
  them is explained in `verification/gate_verdicts.json`
- **46 rendered PDFs**, 721 pages total
- **305 unit tests** (223 at the root, 82 under `yearly/`)

The failing verdicts are deliberately left standing. A repository that shows
only clean gate reports teaches the reader nothing about what the gates
actually catch, and rewriting a shipped report to look tidy is the exact
behaviour the handbook forbids.

## Reproduce it

Three tiers, because they have genuinely different requirements. Only the
first one is free and fully deterministic, and it is the one that checks the
paper's actual claim.

### Tier 0: re-verify offline, no network, no model calls

```bash
pip install -r requirements.txt
python reproduce.py --tier 0
```

Ten checks: the environment matches the manifest, both config trees validate
against their schemas, both unit suites pass, the socket block is still in
place, every claim card maps to a published corpus row, every gate verdict
still matches what shipped, every PDF opens with its recorded page count,
every figure reference resolves, and every study CSV agrees with its JSON
summary. Exit code is 0 only if all of them pass.

This tier needs Python, pyyaml, pymupdf, pydantic and pytest. It touches no
network and calls no model. It should pass on any machine, and if it does not,
the failure names the artifact it read.

Or in a container, with the toolchain pinned:

```bash
docker build -t auto-perov-review .
docker run --rm auto-perov-review
```

### Tier 1: rebuild the documents

```bash
python reproduce.py --tier 1
```

Adds pandoc 3.11 and tectonic 0.15.0 and rebuilds the PDFs from the stored
drafts. **Byte-identical PDFs are not expected**: tectonic embeds a build
timestamp and subsets fonts. The criterion is that the gates pass again and
the page counts match.

### Tier 2: re-run the whole pipeline with your own agent

Tier 2 re-harvests from the scholarly APIs and re-extracts claim cards through
a language model. `reproduce.py` deliberately refuses to run it, and prints
why.

**It will not give you the same numbers, and no manifest can make it.** Two
reasons, both irreducible:

1. The corpus grows. OpenAlex and Crossref keep indexing after our harvest
   date, so a query for 2026-08 run today returns more works than it returned
   in September 2026.
2. Providers update weights behind a stable model name. An identical prompt at
   temperature 0 is not guaranteed to give an identical completion next month.

This is why the reproducibility claim in the manuscript is scoped to the
deterministic half. What tier 2 does check is that the pipeline still works
end to end, which is a different and still useful thing.

**If you are pointing an AI agent at this repo, have it read `AGENTS.md`
first.** It is the operating contract in two pages: what the gates guarantee,
why formatting never lives in a prompt, and the five mistakes an agent makes
here. `tests/test_agents_md.py` asserts it still matches the handbooks, so it
cannot quietly go stale.

To run it with your own agent and your own keys:

```bash
cp .env.example .env        # then fill in your own keys
# edit config/models.yaml to point at the models you have access to
python scripts/run_month.py 2026-09
```

`config/models.yaml` declares the roles, not the vendors: one **writer**, two
**read-only reviewers**, and an **extractor**. Point them at whatever you
have. The contract that matters is structural and holds regardless of which
models you use:

- `writer_rule: strict` — exactly one agent writes; the reviewers cannot edit
- `fallback_policy: fail_closed` — a missing model stops the run instead of
  silently degrading to a weaker one
- no gate calls a model, so swapping models cannot loosen a threshold

Read `MASTER_HANDBOOK.md` before running tier 2. It is the operating contract
for the monthly and half-year cadences, it is 1,462 lines, and
`tests/test_handbook.py` asserts that its gate table matches what the build
actually emits. `yearly/MASTER_HANDBOOK_YEARLY_v2.md` covers the yearly
cadence.

## Abstracts are not redistributed

Publisher abstracts are not ours to republish, so `runs/*/private/` ships a
**sha256 digest per work** instead of the abstract text:
`ABSTRACTS_DIGEST_02_abstracts.json`.

This is enough to prove provenance. Tier 0's claim-card check confirms every
extracted value maps to a work in the published corpus. For quotation-level
verification, re-fetch the text yourself:

```bash
python tools/rehydrate_abstracts.py --all
python scripts/verify_anchors.py 2026-08
```

The rehydrator rebuilds each abstract from the OpenAlex inverted index and
checks it against the shipped digest. A hash mismatch is reported, never
silently accepted: it usually means the publisher revised the abstract after
our harvest, which is a real finding about the corpus.

## Layout

```
reproduce.py              tiered verification entry point
requirements.txt          pinned packages
env.lock.json             interpreter, external binaries, determinism scope
Dockerfile                pinned container (python 3.11.15, pandoc, tectonic)
verification/             measured expectations reproduce.py asserts against
tools/                    check_env, validate_config, ship_audit, rehydrate
MASTER_HANDBOOK.md        monthly + half-year operating contract
MASTER_HANDBOOK_H1.md     half-year specifics
scripts/stages/           the pipeline, one module per stage
scripts/verify_*.py       standalone verifiers (anchors, PDFs, citations)
config/                   gate thresholds, mechanism axes, model roles
runs/<period>_<hash>/     stored artifacts per run, stage by stage
manuscript/<period>_vN/   shipped drafts and rendered PDFs
papers/studies/           evaluation study data behind the system paper
tests/                    223 unit tests
yearly/                   the yearly cadence, same shape, 82 tests
```

Run directories are addressed through `runs/<period>.active`, which holds the
run id that shipped. The stages read that pointer rather than guessing the
newest directory.

## Honest limitations

- **Tier 2 is not reproducible.** See above. The manuscript says so too.
- **The gates check consistency, not truth.** A gate confirms that a number in
  the abstract traces to a claim card and is physically possible for the
  quantity it is presented as. It cannot confirm the underlying paper measured
  it correctly.
- **Nine gate verdicts in this tree are not `pass`.** Two monthly issues carry
  a failing `G8-novelty` from shingle reuse of the review's own framing
  sentence, one carries a `G5` page-band failure against a band written for a
  superseded layout, and several report `skip` or `cold-start` where there was
  no prior issue to compare against. All nine are in
  `verification/gate_verdicts.json` with a reason.
- **The system-paper manuscript is not in this repository.** It is unpublished.
  Its evidence is here: `papers/studies/` holds the study data and
  `papers/scripts/studies/` the scripts that produced it.
- **Superseded stage code is not shipped.** Earlier pipeline versions are kept
  privately for the audit trail. Shipping them would invite someone to run a
  v1 stage against v4 data.

## Citation

See `CITATION.cff`. The manuscripts are not yet published; cite the
repository.

## License

Code and generated text: MIT, see `LICENSE`.

Stored bibliographic metadata in `runs/` comes from OpenAlex (CC0), Crossref,
arXiv and Semantic Scholar, under each source's own terms. Abstract text is
not redistributed.
