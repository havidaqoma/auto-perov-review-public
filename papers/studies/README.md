# Evaluation studies

Evidence for the system paper. Code lives in `scripts/studies/`; the committed
artifacts live here. Raw machine outputs are regenerated into `runs/studies/`.

| File | Study |
|---|---|
| `fault_injection.csv` / `.json` | Item 2: does each gate catch the defect it exists for? |
| `baseline_fabrication.csv` / `.json` | Item 3: does the guard layer prevent fabrication? |
| `agy_prompt_publish_strategy.md` | Prompt for the independent second opinion |
| `agy_publish_strategy_out.md` | Raw reply, kept verbatim so the opinion is reproducible |

Both studies were run on **2026-07** (169 cards, 648 works).

## Item 2 — fault injection

Oracle-first mutation testing: the gate that MUST catch each mutation is
declared BEFORE injection. 19 mutations, 15 testable.

- 14 caught by their declared oracle
- 1 honest miss (FI-08)
- 2 documented blind spots confirmed (FI-13, FI-14)
- controls clean

**FI-08 is a real finding, not a pass.** A narration paraphrase absent from
`KNOWN_LEAKS` reaches the rendered PDF. The filter recognises the sentences it
has already seen, not the grammar of the failure class. This is the same shape
as the leak that shipped in the August v4 issue and it is still open.

**FI-13 / FI-14** are the two gaps the handbooks already record: intra-issue
duplication is defined but not enforced (H1 App. B #1), and G9c counts
duplicate figures so it cannot see an absence (H1 §9.2). Deleting every figure
fails no gate.

Four defects were found in the STUDY ITSELF before any of these numbers were
trustworthy, each of which had produced a false gate MISS. See the commit
message for `scripts/studies/fault_injection.py`.

## Item 3 — ungated baseline

Same extractor model, same papers, same abstracts. The guard layer is the only
variable, so nothing here can be attributed to a model difference.

| Arm | Values | Ungrounded | Rate | 95% CI (Wilson) |
|---|---|---|---|---|
| Ungated baseline | 159 | 2 | 1.26% | 0.35% – 4.47% |
| Guarded pipeline | 152 | 0 | 0.00% | 0.00% – 2.47% |

**The intervals overlap. This is not yet a significant result** and must not be
reported as one. At this sample size the study establishes a method and an
upper bound, not a difference. Reaching significance against a ~1% base rate
needs roughly 1,000+ extracted values, i.e. several months of corpus.

The two ungrounded baseline values (`t80_h = 1500 h`, `active_area_cm2 =
0.0405`) are plausible-looking numbers absent from their own source abstracts —
the failure mode is quiet, not obviously wrong, which is the point.

Grounding is checked deterministically: a number is grounded if it appears in
its own source abstract. No model is asked to judge its own output.
