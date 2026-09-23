# Overnight run 2026-09-09: both requested issues BLOCKED at preconditions

**Operator request (2026-09-09, unattended):**

1. Perovskite PV **2025 yearly** review, using `MASTER_HANDBOOK_YEARLY.md`
2. **ZnO nanoparticle / quantum dots, Aug 2026** monthly review, using
   `MASTER_HANDBOOK_GENERAL.md`
3. "Decide what you think is best" and report on Telegram when done.

**Outcome: neither manuscript was generated. Neither could be generated
truthfully.** Both requests hit hard, documented, fail-closed preconditions
that exist precisely to stop the artifact that was asked for. No gate was
widened, no band was edited, `--partial` was not used, and no PDF was
produced whose title would have named a period its evidence does not cover.

---

## 1. Perovskite PV 2025 yearly — BLOCKED (no 2025 data exists)

### The computed evidence

```
$ python scripts/stages/yearly_aggregate.py 2025
FAIL-CLOSED: no monthly runs on disk for 2025. A yearly issue is assembled
from monthly runs; it is never harvested fresh.

$ python scripts/yearly_preflight.py 2025
YEARLY PREFLIGHT 2025
  verdict         BLOCKED: 0/12 months usable
  months usable   0/12
  corpus total    0
  cards total     0
  MISSING (12): 2025-01 ... 2025-12
rc=1
```

Every month of 2025 is missing. Not thin, not unverified — **absent**. The
only monthly runs on disk are:

| Run dir | Month |
|---|---|
| `runs/2026-06_cf764cbb/` | June 2026 |
| `runs/2026-07_197abe83/`, `runs/2026-07_51e6c170/` | July 2026 |
| `runs/2026-08_b086357d/` | August 2026 |

Control run, to prove the preflight is not simply failing everything:

```
$ python scripts/yearly_preflight.py 2026
  verdict         BLOCKED: 3/12 months usable
  corpus total    1835
  cards total     480
```

3/12 for 2026 matches YEARLY §1.4's verified figures (corpus 1835, cards 480)
exactly, so the checker agrees with the handbook's own measurement.

### Why this cannot be worked around

YEARLY §1 is unambiguous: **the year is the union of the twelve monthly runs.
Nothing is re-extracted.** The obvious "fix" — harvest 2025 literature now
and run the chain over it — is the one thing the handbook forbids, and §1.3
gives the measured reason:

| Month age at retrieval | Full text retrieved |
|---|---|
| two months | 5.0% |
| fourteen months | 2.5% |

A fourteen-month-old month retrieves **worse** than a two-month-old one.
Re-harvesting January in December does not recover January, it loses it. A
2025 issue built by re-harvesting in September 2026 would be built from the
*worst* available view of 2025, and would present it as the year's record.

### Why `--partial` was not used

There is nothing to be partial about: 0/12, not 3/12. Even for 2026,
`--partial` would be wrong here — YEARLY §2.1 requires a recorded decision
plus abstract-and-methods coverage statements, and §1.4 is explicit that a
yearly issue silently built from three months "would state a year's
conclusions from a quarter's evidence, and **every gate would pass**".

Substituting 2026 data under a 2025 title would be a period fabrication of
the §7.2 class. Not done.

### What Havid must decide

1. **Build 2025 monthly runs first**, accepting §1.3's degraded retrieval for
   the older months, then aggregate. Honest, expensive, and the resulting
   issue must state its retrieval handicap.
2. **Wait and build the 2026 yearly** once 2026-09 through 2026-12 exist.
   9 months of the year are still un-built, so this is a Jan-2027 artifact.
3. **Commission an explicit partial-year interim issue** for 2026-06..08,
   titled and abstracted as a quarter, not a year.

Recommendation: **option 2**. It is the only path where the yearly design is
used as designed, and the first yearly build should not also be the first
build fighting a known retrieval handicap.

---

## 2. ZnO nanoparticle / QD, Aug 2026 — BLOCKED (registry has no consumer)

### The computed evidence

```
$ grep -l -- "--domain" scripts/stages/*.py scripts/*.py
(no output)

$ grep -n "argv" scripts/stages/s13d_draft_v4.py
606:    draft(sys.argv[1] if len(sys.argv) > 1 else "2026-08")

$ grep -n "argv" scripts/stages/s18d_build_v4.py
1109:    build(sys.argv[1] if len(sys.argv) > 1 else "2026-08")
```

**The `--domain` flag is wired into zero stages.** Not partially — zero. Every
stage takes a bare period and nothing else. `GENERAL.md` §13 already says
this ("is not yet wired into the stages"), and §0 says "the code generation
that consumes them is specified here and not yet wired". Both statements are
confirmed true as of this session.

### Why a manuscript was not forced through anyway

Running `s01..s21` for ZnO today would run the **perovskite** pipeline with a
ZnO-shaped month argument. Concretely, per GENERAL §1:

- `s09_cards.py` would extract `pce_certified`, `pce_champion`, `t80_h`,
  `active_area_cm2` and `architecture: p-i-n|n-i-p|tandem_2T|module` from ZnO
  abstracts. Those fields do not exist in ZnO nanocrystal papers.
- `s13d`/`s18d` carry 22 and 20 topic-specific strings respectively.
- G3c would apply the 29.4% Shockley-Queisser bound to PLQY.
- The default `"2026-08"` in both stages points at `runs/2026-08.active`,
  which resolves to the **shipped August perovskite issue**. There is no
  domain namespacing in the run path, so a ZnO run would have written into
  the shipped PV run directory.

That last item is the serious one: the request as literally executed would
have corrupted a shipped artifact. It is recorded here as a wiring
requirement, not a hypothetical.

### What was built instead

The maximum safe preparatory work, per GENERAL §7 steps 1-8:

| Artifact | Status |
|---|---|
| `config/domains/zno_qd.yaml` | **passes `domain_lint.py`**, rc=0 |
| `tests/test_zno_domain.py` | **34 tests, all passing** |
| `scripts/yearly_preflight.py` | new, deterministic G11 coverage evidence |
| `MASTER_HANDBOOK_GENERAL.md` | instance table updated |

Full suite: **223 passed**. `domain_lint.py --all`: 4/4 domains pass.

### The topic_type decision, and why it is Type-D

GENERAL §3.3 calls this the highest-stakes field in the registry, and §7 step
1 marks it **HUMAN** and unfixable without re-extraction. Havid was asleep, so
the reasoning is recorded in full both here and in the YAML header, and it is
flagged below as needing confirmation before any extraction runs.

**Chosen: `topic_type: D`.**

The request was "ZnO nanoparticle/quantum dots" — a materials scope spanning
synthesis, optics, defect chemistry, photocatalysis, sensing, bioimaging and
electron-transport layers. No scalar figure of merit ranks across those:

- **PLQY is the tempting wrong frontier.** A 94% PLQY in a dilute colloid is
  not comparable to a 12% PLQY in a working film, and the film is usually the
  harder result. Ranking on PLQY across sample classes is GENERAL §3.3's
  category error exactly: a real, traceable number describing the wrong thing.
- **Emission peak and particle size are scope, not merit.** A 3 nm dot is not
  better than a 6 nm dot; it is a different material.
- **Synthesis yield is a property of a run**, not of a method.

GENERAL §3.1 requires Type-P to declare `frontier` + `penalty_x` +
`durability`, because the monthly argument is "the frontier is thin, it does
not survive scale, it does not survive operation". ZnO nanomaterials cannot
make that argument — there is no agreed frontier to be thin.

**When Type-P would be right instead:** narrow the scope to a device class
(e.g. "ZnO-ETL QLEDs") and a real frontier appears — device EQE, with
luminance as penalty and T50 as durability. That is a *different slug*,
declared before extraction, never a `topic_type` edit afterwards.

### Registry contents

`zno_qd.yaml`: 6 axes, 10 metrics, 4 figures, 11 abstract tokens, Type-D.

Design decisions worth flagging:

- **No metric holds `role: frontier`.** PLQY is `quality`. Lint enforces this
  for Type-D.
- **`plqy_pct` is `device_binding: true`, `requires_condition: sample_class`.**
  This is GENERAL §2.4 in ZnO form and the defect this domain is most likely
  to ship: one abstract routinely reports the authors' colloid PLQY and a film
  or device value in adjacent sentences, and a label taken from the *paper*
  attaches to the wrong number.
- **`sample_taxonomy` separates `colloid` / `powder` / `thin_film` /
  `composite` / `device`** — the whole reason PLQY can be `quality` and not
  `frontier`.
- **`synthesis_yield_pct` has `direction: none`.** Note that
  `domain_lint.py`'s generic yield check matches keys *starting with*
  `yield`, which this key does not, so it is pinned by an explicit test
  instead. See §4 below.
- **Physics bounds**: `bandgap_ev` 2.8-5.0 (brackets bulk 3.37 eV),
  `emission_peak_nm` 300-900 (brackets 370 nm band-edge and 500-600 nm defect
  emission), `particle_size_nm` floor 0.5 nm (a ZnO unit cell).
- **`exclude.word_bound` includes `perovskite`** — the PV corpus overlaps ZnO
  heavily via electron-transport layers.
- **No arXiv PV category assumed.** `cond-mat.mtrl-sci` only, and it is
  documented as not reliable for coverage.

---

## 3. A real defect my own tests caught

`test_every_metric_unit_is_resolvable` failed on first run:

```
AssertionError: metric scale_g uses unit 'g', which is not in
notation.extra_units; it would render flat
```

This is GENERAL §5.3's missing-`J` defect reproduced in a new domain before
it could ship: **a missing unit does not degrade gracefully** — a unit run
matches as a whole, so one unknown token leaves every unit beside it flat and
G9a reports the *neighbour*. Fixed by declaring `"g": "\\gram"`.

Recording it because it is the porting checklist working as designed: step 7
(units) was the step I got wrong, and a test written for step 8 caught it.

---

## 4. Gap found in `domain_lint.py` — NOT patched, needs a decision

`domain_lint.py:245` enforces `direction: none` for Type-D yields via:

```python
if str(m.get("key", "")).startswith("yield") and m.get("direction") != "none":
```

`startswith("yield")` matches `molecular_synthesis.yaml`'s `yield_pct` but
**not** `zno_qd.yaml`'s `synthesis_yield_pct`. A future editor could set
`direction: higher_better` on that key and lint would pass, restoring the
champion-curve category error the check exists to prevent.

I have **not** widened or rewritten the linter, because tightening a shared
gate that four domains depend on is a spec-affecting change and Havid's
standing rule is that recurring defects become enforced assertions — with the
change surfaced, not made silently. Options:

1. Change the check to a substring/regex match (`"yield" in key`), catching
   `synthesis_yield_pct`, `isolated_yield_pct`, etc. Tightens a live gate;
   all four current domains still pass (verified mentally, needs a run).
2. Add a `ranking_forbidden: true` metric flag and enforce on that, making the
   intent declarative rather than name-based.
3. Leave the linter alone and rely on `tests/test_zno_domain.py::
   test_yield_direction_is_none`, which pins it for this domain only.

Recommendation: **option 1 now, option 2 when a third Type-D domain lands.**
Name-based matching is fragile, but it is the mechanism already in place, and
widening the pattern strictly increases what the gate catches.

Currently in force: option 3.

---

## 5. What did NOT happen

Stated explicitly so absence is not read as an oversight:

- No manuscript, PDF, or draft prose was generated for either request.
- No LLM writer or extractor was invoked. Zero model tokens spent on prose.
- No gate, band, or threshold was widened, in `gates.yaml` or `yearly.yaml`.
- `--partial` was not used.
- No `if domain == "..."` branch was added anywhere.
- No stage was forked per domain.
- No shipped run directory was written to.
- `runs/2025_yearly_preflight.json` and `runs/2026_yearly_preflight.json` are
  under gitignored `runs/*`; the numbers are transcribed above.

---

## 6. Verification

```
$ python -m pytest tests/ -q
223 passed

$ python scripts/stages/domain_lint.py --all
PASS molecular_synthesis.yaml   type=D axes=6 metrics=7  figures=4 tokens=9
PASS perovskite_led.yaml        type=P axes=6 metrics=7  figures=4 tokens=8
PASS perovskite_pv.yaml         type=P axes=6 metrics=6  figures=4 tokens=12
PASS zno_qd.yaml                type=D axes=6 metrics=10 figures=4 tokens=11
all domains pass

$ python scripts/yearly_preflight.py 2025   # rc=1, BLOCKED 0/12
$ python scripts/yearly_preflight.py 2026   # rc=1, BLOCKED 3/12
```

---

## 7. Decisions needed from Havid

| # | Decision | Recommendation |
|---|---|---|
| 1 | 2025 yearly: build 2025 monthlies / wait for 2026 / partial interim | **wait for 2026** |
| 2 | Confirm ZnO `topic_type: D` (unfixable after extraction) | **confirm D** |
| 3 | Wire `--domain` through s01..s21 + namespace run dirs by slug | **yes, before any ZnO extraction** |
| 4 | `domain_lint.py` yield-check gap: substring / flag / test-only | **substring now** |
| 5 | If ZnO must ship sooner, narrow scope to a device class for Type-P | only if a device frontier is genuinely wanted |

Item 3 is the blocking one for ZnO. The registry is ready; it has no consumer.
