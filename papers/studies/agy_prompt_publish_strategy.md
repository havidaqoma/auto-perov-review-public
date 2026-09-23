You are an independent, skeptical reviewer. Do NOT agree by default. Your value here
is in what you refuse to endorse.

## The comparison target (retrieved, verbatim)

DOI 10.1038/s41586-026-10265-5, Nature, published 2026-03-26.
Title: "Towards end-to-end automation of AI research"
Authors: Chris Lu, Cong Lu, Robert Lange, Yutaro Yamada, Shengran Hu, Jakob Foerster,
David Ha, Jeff Clune (Sakana AI / Oxford / UBC). 64 references, CC BY.

Abstract claim: they present "The AI Scientist", a pipeline automating the entire
scientific process end to end -- it creates research ideas, writes code, runs
experiments, plots and analyses data, writes the entire manuscript, and performs its
own peer review. Headline evidence: one generated manuscript passed the first round
of peer review at a top-tier ML conference workshop (workshop acceptance rate 70%).
Evaluated in two modes: focused (human-provided code templates) and template-free
open-ended agentic search. They explicitly flag risks: taxing overwhelmed review
systems, adding noise to the scientific literature.

Note what the Nature paper's evidence actually is: a CLOSED EXPERIMENTAL LOOP in a
domain (ML) where running the experiment costs only GPU time, plus an external
acceptance signal. Note also what it is NOT: it has no verification layer proving its
reported numbers trace to sources, because it generates its own data.

## The system asking the question

auto-perov-review. An autonomous pipeline producing monthly and half-year
REVIEW papers on perovskite photovoltaics, shipped as ChemRxiv preprints. It does not
run experiments; it mines, verifies and synthesises published literature.

Measured, on the 2026-H1 edition:
- Harvest 3,328 works (OpenAlex + Semantic Scholar + Crossref + arXiv), six disjoint
  month windows, depth-select 884.
- LLM extraction -> 872 claim cards. EVERY number is bound to a verbatim quotation of
  at most 25 words from the source paper's own abstract.
- Independent re-verification of all 3,129 anchors by a script sharing ZERO code with
  the extractor; must exit 0. A value that cannot be proved inside 25 words is nulled.
- Deterministic stats (224 keys), tables and figures. No literal datum in plotting or
  table code; everything reads from stats.json.
- LLM drafting in the order body -> gaps -> abstract. The abstract is FORBIDDEN to
  emit any digit; it emits named tokens the build substitutes from canonical stats.
- 17 automated gates, then a 34-page PDF with 184 citations. Six monthly issues plus
  one half-year issue shipped so far.

Every human-caught defect became a permanent gate, not a prompt reminder. The list:
writer fabrication of three abstract numbers (a positional index into a filtered
list); a REAL certified 32.95% tandem number attached to a single-junction sentence
(every provenance guard passed, because nothing in the chain was broken -- the number
was real and the device label came from a different sentence of the same abstract);
agent-narration leak ("I have launched the search command and will wait for it to
finish.") reaching a shipped PDF under a section heading WHILE the narration gate
reported pass, because the guard existed in three divergent copies; guard-order bug
shipping five quotations that ended immediately before their own number; Unicode
U+2212 minus vs ASCII hyphen shipping units flat while an ASCII-only gate passed it;
a LaTeX \vspace discarded in horizontal mode so the source requested 3.6em and the
page rendered 0.11 pt, after three blind tunings; stale artifacts passing all 17
gates because the gates read the run directory and not the copied PDF; six separate
VERIFIER bugs where the check was wrong and the artifact was right.
Novelty decay was measured and fixed: July-vs-August abstract similarity 0.629 under
v3 (a Python script authored three fixed closing sentences every month) fell to 0.018
under v4 once the writer authored the closing material last.
Physics-plausibility gate: no single-junction PCE above the 29.4% Shockley-Queisser
limit. It caught a 44.36% value that was correct, experimental and correctly labelled
single junction -- but measured under INDOOR LED illumination, not one sun. The
defect was comparability, not correctness. Illumination is now a fourth axis beside
device, verification and area.
Token accounting separates cost SPENT (63 calls) from cost of the SHIPPED artifact
(32 calls); reporting one number for both would overstate roughly threefold.

## What is missing, stated honestly -- do not congratulate us on the above

- NO human-labelled validation set. All audit percentages ship as "detected in at
  least X%". Extraction precision and recall are UNKNOWN. This is the project's own
  top outstanding human task and has been outstanding for the whole programme.
- No blinded expert comparison of generated issues against human-written reviews.
- Single domain. A cross-domain port is designed (a metric registry replacing the
  hardcoded photovoltaic schema) but NOT built; measured topic-lock is 22 hardcoded
  strings in the draft stage, 20 in the build stage, 10 in extraction, 9 in figures.
- No systematic benchmark against AutoSurvey, STORM, The AI Scientist, AI co-scientist
  or Agent Laboratory.
- Artifacts are preprints only. No review article generated by this system has been
  through journal peer review.
- Several defect classes escaped 100% of the automated gates and were caught ONLY by
  a human reading the rendered page. The human read step is documented as
  non-automatable.
- One gate (intra-issue novelty) is defined in config but not enforced.

## The question

Can we publish a peer-reviewed paper ABOUT this system, in the way the Nature paper
above did for The AI Scientist? In what venue, with what framing, and what evidence
is mandatory before submission? Be concrete about whether the review-synthesis task
can ever carry the weight that a closed experimental loop carries.

## Rank these named strategies, 1 = best

A. Methods/systems article at Nature Machine Intelligence / Patterns / Digital
   Discovery. Contribution framed as an AUDITED EVIDENCE CHAIN plus a defect-to-gate
   architecture, with the 200-paper label sheet, a blinded expert evaluation and a
   fault-injection study added first. (This is the plan we currently favour.)
B. Direct Nature flagship submission now, betting on the longitudinal seven-issue
   production record.
C. NLP/ML venue (ACL / EMNLP / NeurIPS Datasets & Benchmarks): reframe as grounded
   generation with fail-closed verification, and RELEASE the defect taxonomy as a
   fault-injection benchmark for agentic scientific writing.
D. Two-track: a short Comment or Perspective in a Nature-family journal on audit-first
   autonomous synthesis, running in parallel with A.
E. Stay preprint-only until the system's own gap analysis closes a discovery loop
   (gap statement -> a real perovskite experiment or simulation -> validated result),
   then aim higher.
F. Something we have not named. If you propose this, it must beat A on a stated
   criterion, not merely sound like a synthesis of the others.

## Known failures already solved -- do NOT re-derive these as advice

Writer fabrication; number-on-wrong-device misattribution; narration leak; six
verifier bugs; silent-zero class; guard-order bug; citation merge vs hyperlink
conflict; Unicode minus; discarded LaTeX vspace; stale artifacts passing all gates;
month hardcoded in five sites; proportional section allocation; prompts that dictate
phrasing and get that phrasing back forever.

## Permission to say no

If this system cannot support a publishable paper without the missing evaluations,
say so plainly. If review synthesis is structurally a weaker publication object than
a closed experimental loop and we should accept a lower venue, say that. If our
favoured plan A has a fatal flaw, name it. A false promise is worse than a no.

## Hard question we want answered, not dodged

The Nature paper's headline is an EXTERNAL acceptance signal. What is the equivalent
external signal available to a literature-review system, and is any such signal
strong enough to carry a top-venue paper? If the honest answer is "none exists",
say that and tell us what the ceiling therefore is.

## Output skeleton -- use these exact headings

STRONGEST DISAGREEMENT
WHAT THE NATURE PAPER HAS THAT WE DO NOT
RANKING (one line of reasoning each)
WHAT IS MISSING BEFORE SUBMISSION (ordered by cost to benefit)
THE EXTERNAL SIGNAL QUESTION
VERDICT (2-3 sentences, no hedging)
