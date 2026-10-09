# Evaluation studies

Evidence for the perovskite PV system paper. Code lives in
`papers/scripts/studies/`; the committed artifacts live here. Raw machine
outputs are regenerated into `runs/studies/`.

| File | Study |
|---|---|
| `fault_injection.csv` / `.json` | Does each gate catch the defect it exists for? |
| `superseded/fault_injection.first_run_74e3050.json` | The first fault-injection run, kept verbatim (14 of 15) |
| `baseline_fabrication.csv` / `.json` | One-month ungated baseline (2026-07) |
| `baseline_scaled.csv` / `.json` | R3: eight-month ungated baseline, full abstracts |
| `baseline_title_only.csv` / `.json` | R4: eight-month ungated baseline, titles only |
| `ablation_gate.csv` / `.json` | R5: same prompt, same papers, guard off vs on |
| `metric_rescore.json` | Stored R2/R3/R4 outputs re-scored with the corrected matcher |
| `r3_ungrounded_review.json` | Hand verdict on every R3 value the corrected matcher cannot find |
| `tool_use_audit.json` | Which extractor calls had agent tools, and what they did |
| `prereg_deviations.json` | Pre-registered R1 analyses that were not run, and why |
| `label_precision_recall.*`, `relabel_kappa.*`, `label_sheet/` | R1: extractor flags against human labels |
| `superseded/` | Tools-on results replaced by the tools-off re-runs. Never scored |
| `agy_prompt_publish_strategy.md` | Prompt for the independent second opinion |
| `agy_publish_strategy_out.md` | Raw reply, kept verbatim so the opinion is reproducible |

The fault-injection and one-month baseline studies were run on **2026-07**
(169 cards, 648 works).

## Fault injection

Oracle-first mutation testing: the gate that MUST catch each mutation is
declared BEFORE injection. 19 mutations, 15 testable.

- First run (commit 74e3050): 14 caught, 1 real miss (FI-08)
- After the fix (commit e924860, verified in 8d48299): 15 of 15 caught
- 2 documented blind spots confirmed (FI-13, FI-14)
- controls clean

**FI-08 was a real gate miss, now fixed.** A narration paraphrase absent from
`KNOWN_LEAKS` reached the rendered PDF: the filter recognised the sentences it
had already seen, not the grammar of the failure class. This was the same shape
as the leak that shipped in the August v4 issue. Commit e924860 replaced the
sentence list with a grammar-level check; the re-run catches FI-08 at G4.
The paper reports both runs ("14 of 15 in the first run, 15 of 15 after the
fix"), not the second alone.

**FI-13 / FI-14** are the two gaps the handbooks already record: intra-issue
duplication is defined but not enforced (H1 App. B #1), and G9c counts
duplicate figures so it cannot see an absence (H1 §9.2). Deleting every figure
fails no gate.

Four defects were found in the STUDY ITSELF before any of these numbers were
trustworthy, each of which had produced a false gate MISS. See the commit
message for `papers/scripts/studies/fault_injection.py` (74e3050).

## One-month ungated baseline

Same extractor model (qwen3.8-flash), same papers, same abstracts. The prompts
are NOT the same: the guarded arm uses the s09 claim-card prompt and the
ungated arm a shorter open prompt. The prompt-matched comparison is R5.

| Arm | Values | Ungrounded | Rate | 95% CI (Wilson) |
|---|---|---|---|---|
| Ungated baseline | 159 | 2 | 1.26% | 0.35% to 4.47% |
| Guarded pipeline | 152 | 0 | 0.00% | 0.00% to 2.47% |

**The intervals overlap. This is not yet a significant result** and must not be
reported as one. At this sample size the study establishes a method and an
upper bound, not a difference.

The corrected matcher (below) changes this table: `t80_h = 1500` is in its
abstract as "1,500 h", and `active_area_cm2 = 0.0405` is a unit conversion
the matcher does not follow. Under the corrected metric the ungated arm has
1 of 159, and that one is a conversion, not an invented number.

## Corrected grounding metric (2026-09-23)

The number matcher read a thousands comma as a decimal point, so "1,080 h"
became 1.08 and a correct 1080 was scored as ungrounded. All three matchers
(`study_common.numbers_in`, `s09_cards._num_in`, `verify_anchors.num_in`)
now treat exactly three digits after a comma or space as digit grouping
(`tests/test_number_grouping.py`). `rescore_metric.py` re-scores the stored
outputs with no model calls. A value the corrected matcher still cannot find
is not automatically wrong: `r3_ungrounded_review.json` says, for each one,
whether it is a correct unit conversion, a module footprint given as an active
area, or a wrong value.

## Extractor tool access (2026-09-23)

`opencode run` gives the model bash, read, grep, webfetch, write and edit by
default, and the extractor was run that way for the shipped issues and for the
first R3/R4 runs. `tool_use_audit.json` (read-only audit of the opencode
session database) records what the tools were used for. No tracked repository
file was changed by an extractor. The extractor now runs with every tool
denied and fails the call if any tool part appears
(`tests/test_extractor_no_tools.py`); the audit fails if a tool executed after
that fix. R3 and R4 were re-run tools-off, and the tools-on results are kept in
`superseded/` for the record only.

## Gate ablation, R5 (2026-09-23)

`ablation_gate.py` runs the production s09 prompt once on the same 767
papers, tools off, and scores the values twice: as returned (gate off) and
after the verification layer (gate on). The prompt, model and papers are the
same in both arms, so the gate is the only variable. The scorer refuses a
partial run. Every gate-off value the matcher cannot find has a hand verdict
in `r5_ungrounded_review.json`, joined fail-closed by `work_key`, field and
value, with each quote checked verbatim against the abstract.
Result in `ablation_gate.json`: 4 of 1,074 ungrounded with the gate off, 0 of
1,050 with it on, Fisher p = 0.125, so the gate effect is not significant on
this corpus. The generic-prompt baselines (R3, R4) change prompt and gate
together and cannot be credited to the gate alone.

## Detectors re-scored against the R1 labels (2026-09-23)

These use the existing human labels only; no model labels anything.
`label_isos_corrected.json` scores the corrected ISOS pattern (recall 14 of
16). `t80_text_eval.py` scores the pre-specified text-level lifetime pattern
in `stages/protocol.py` once, giving `label_t80_text.json`. Both patterns were
written after the labels existed, so both results are in-sample and the
artifacts say so. The registered analysis in `label_precision_recall.json` is
not changed. `prereg_deviations.json` lists the pre-registered secondary
analyses that were not run and why.

## Second human labeller

`label_sheet/second_labeller_sheet.html` is a blind 20-paper sheet for a second
person. It must be filled by a human; no model may label, pre-label or assist.
`relabel_kappa.py --second` fails closed until `r1_second_filled.csv` exists.

Grounding is checked deterministically: a number is grounded if it appears in
its own source abstract. No model is asked to judge its own output.

## Human sign-off and second labeller (2026-09-24)

Hand verdicts. The Hermes conductor (Claude, not the qwen extractor under
test) gave a first-pass verdict on each of the 13 R3 and R5 values the matcher
cannot find. The operator (Havid Aqoma) checked each one on
`verdict_review.html` (`verdict_review_build.py`). The export is
`verdict_confirmations.csv`, and `confirm_verdicts.py` records it in
`verdict_confirmation.json`. He agreed with 12 and overruled 1. The ruling in
`verdict_rulings.json` is that a module footprint reported as the device area
is valid perovskite PV practice, not an error. Both review files now carry
`counts_as_error` (only `wrong`). No verdict was changed: the values stay
classed as footprints, and the ruling changes only which class counts as an
error. Both scorers read that ruling and fail closed if it is
missing. On this ruling, R3 has 2 wrong values (p = 0.50, not significant) and
R5 has 1, which the gate removed. The stricter reading that counts footprints
as errors is kept as a labelled sensitivity figure.

Second labeller. Jocelyn Lim Jean Yi (PhD student, Xiamen University
Malaysia), a person other than the first labeller, filled
`label_sheet/r1_second_filled.csv` on the blinded sheet (title, venue and
abstract only), without AI assistance and without seeing the pipeline output.
`relabel_kappa.py --second` wrote `interrater_kappa.json`:
99 of 100 judgements agree across 20 papers, kappa
0.9755 (0.9167 to 1.0), PABAK 0.98.
The one disagreement is `states_certified` on `10.26599/emd.2026.9370089`.
Agreement shows the labels are reproducible across people, not that they are
correct.



## gate_loss.json (2026-10-01)

Why the gate discarded correct values in the ablation. Built by
`papers/scripts/studies/gate_loss_analysis.py` from `ablation_gate.json` and the
cached model outputs in `runs/studies/ablation_raw/`; no model call, no model
judgement. Each discarded value gets one cause by fixed rules (typography,
elided, outside_cut, paraphrase, not_object), and the step a typography case
needs is recorded per row. A counterfactual guard with hyphen variants unified
is re-run on all values and reports both sides: correct values recovered and
ungrounded values admitted. The shipped verifier is unchanged; every rate in the
paper refers to the guard as it ran.
