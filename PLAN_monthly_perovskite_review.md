# Monthly Perovskite PV Literature → Review + Reporting Audit Automation

# Implementation Plan v5 (plain-English execution edition) and Task List for Hermes

Status: **v5, decisions resolved, ready to execute in order. NOTHING EXECUTED YET.** Written 2026-09-07. Supersedes `PLAN_monthly_perovskite_review_v4.md` (2026-09-06). v4, v3, v2, v1 stay in the repo, byte-frozen, with SUPERSEDED banners. Owner: Havid Aqoma (ORCID 0000-0003-1264-1916, from `config/author_manifest.yaml`). Executor: Hermes (auto-researcher). Companion files: `QUESTIONS.md`, `docs/BRAIN_PENDING.md`, `docs/PROBES_v5.md` (new), `docs/PROGRESS_v5.md` (new).

**What changed from v4.** Three things you asked for, plus eight fixes we agreed on last turn.

1. The writer is now one model only: qwen via the opencode CLI, thinking level high, **no fallback model**.
2. Claude (opus, **effort medium**, was xhigh) and agy (gemini-3.8-flash-high) never write review text. They plan and they review.
3. The whole document is written in plain English. Numbers, regexes, commands, file paths, and YAML are **not** simplified — those are copied from v4 exactly.
4. Fixes: the broken security check in T-02, the stage-number clash with the scripts already in this repo, quarantining the old July files, two missing config files, two competing prose-rule files, the empty-history hole in the selector, a regex note, and the probe dates.

This document has two parts. **Part I** is the specification — what each piece is and what it must do. **Part II** is the ordered task list. Hermes executes Part II and looks up the details in Part I. Where Part I and v4 disagree, Part I wins. Where Part I says nothing, v4 applies, and where v4 says nothing, v3 applies. That is why the old files stay in the repo.

---

## What the machine does, start to finish

Read this page first. Everything after it is detail.

Once a month, on one day, the machine does this without being watched:

 1. Asks OpenAlex for every paper published last month about perovskite solar cells.
 2. Checks the number is sane. If it is zero, or wildly too big or too small, it stops and messages Havid.
 3. Asks three more places for the same thing: Semantic Scholar, arXiv, Crossref.
 4. Cleans up the records: fixes DOIs, fixes titles, detects the language, tidies the institution names.
 5. Translates the abstracts that are not in English.
 6. Looks up how well-cited each journal is, and works out a percentile for it.
 7. Removes duplicates, so one paper appears once even if four sources returned it.
 8. Labels each paper with the mechanism it is about, using a keyword table: composition, defects, interfaces, architecture, stability, or scale-up.
 9. Tries to download the full PDF of every paper and read the text out of it.
10. Picks about 200 papers to read closely. Only papers whose full text was actually read can be picked, if not available, then read the title and abstract. Picking is by a score, and the score is deliberately checked for how fragile it is.
11. Reads each of those 200 papers and pulls out the numbers into a "claim card". Every number must come with a short quote from the paper that contains that number, or the number is thrown away.
12. Counts everything. Every single number that will ever appear in the review paper is written into one file now, and nowhere else.
13. Draws the figures. Every figure reads its numbers out of that one file.
14. Plans the paper: opus produces a structured brief — a list of which claims and which numbers go in which section. Not prose, a list.
15. Writes the paper: qwen writes every section from that brief — about 5,100 words, 6-7 content pages (Q45).
16. Checks the paper against ten gates. The important one reads each sentence that cites a paper and asks a checker model whether the paper's own quoted words actually support that sentence.
17. Reviews the paper twice, in parallel: agy checks structure and format, claude checks the science. Their complaints go back to qwen to fix. Up to three rounds.
18. Builds the PDF, the Word file, the LaTeX source, and the ChemRxiv submission package.
19. Sends Havid a summary on Telegram and **stops**. It never submits anything anywhere.

If anything goes wrong at any step, the machine stops at that step, sends a message, and runs nothing after it. It never guesses a missing input and it never carries on with half the data.

---

## Glossary (plain meanings of the words used throughout)

| Word | What it means here |
| --- | --- |
| **preprint** | A paper the authors posted publicly before a journal accepted it. Not peer reviewed yet. |
| **abstract** | The short summary at the top of a paper. Usually free to read. |
| **full text** | The whole paper. Usually inside a PDF. Often not free. |
| **DOI** | The permanent ID of a paper, like `10.1002/pip.3919`. |
| **OpenAlex** | A free database of academic papers. Our main source. |
| **venue** | Where a paper was published: a journal, or a preprint server. |
| **percentile** | Where a journal ranks among all journals, 0 to 1. 0.95 means "better cited than 95% of journals". |
| **corpus tier** | Every paper that passed the topic filter. We only have its abstract. |
| **eligible tier** | Corpus papers whose full text we successfully downloaded and read. |
| **depth tier** | The \~200 eligible papers we chose to read closely. Only these get claim cards. |
| **claim card** | A structured file of the numbers and claims from one paper, each with a quote proving it. |
| **anchor** | The short quote (25 words or fewer) that proves a number came from the paper. |
| **entailment** | Asking a model: "does this quoted text actually support this sentence?" |
| **precision** | Of the things we flagged, what fraction were right. |
| **recall** | Of the things we should have flagged, what fraction we caught. |
| **z-score** | How unusual this month is compared with the last six months, measured in standard deviations. |
| **Jaccard** | How much two sets overlap, 0 to 1. Used to test whether our 200 picks are stable. |
| **ceiling** | A maximum. We use maximum word counts, never minimums. |
| **content floor** | A minimum amount of *evidence* a section must rest on. Not a word count. |
| **gate** | An automatic check that must pass. A failed gate stops the run. |
| **force-include** | A paper so important the machine asks Havid whether to include it by hand. |
| **fail closed** | When in doubt, stop. Never continue on partial or guessed data. |
| **MT** | Machine translation. |
| **SI** | Supplementary Information — the extra files published alongside a paper. |
| **stats key** | A dotted name like `audit.corpus.certified.pct` identifying one number. |
| **run directory** | `runs/<month>_<hash>/`. Everything one monthly run produces lands here. |
| `.done` **marker** | A small file each stage writes when it finishes. It is how a stopped run resumes. |
| **probe** | A small read-only test against a real API to find out how it actually behaves. |

---

## 0. Operating rules for Hermes (read first, apply always)

 1. **Do the tasks in order.** Part II is ordered. A task may start only when every task it depends on has finished and its proof is committed.
 2. **Stop points are real stops.** A task marked `⛔ HUMAN` ends by messaging Havid on Telegram and writing a line in `QUESTIONS.md`, and then it waits. While it waits, Hermes may only work on tasks that do not depend on it.
 3. **Probe before you code.** Anything tagged `[PROBE]` is a guess about how an API behaves. Run the probe, write down what happened in `docs/PROBES_v5.md` (the date, the exact command, and the response with any key blanked out), and then write the code against what actually came back.
 4. **A failed probe is reported as failed.** You never quietly change the plan to make a failure look like a pass. If the API returns 1,900 papers and the allowed band is 250 to 1,200, you report that the band was breached. You do not widen the band to 2,000 so it passes.
 5. **Fail closed.** Any failed gate, exhausted quota, out-of-range count, or missing input stops the run at that stage and sends a message. No stage ever runs on partial or guessed input (Q26=b).
 6. **Secrets live in** `.env` **and nowhere else.** Havid types keys into `.env` himself. Keys are never pasted into chat, a prompt, a log, a commit message, a test, or any document (Q43). Only `scripts/common/net.py` reads them. Its `oa()` function checks the host really is `api.openalex.org` before it attaches the OpenAlex key. Its `plain()` function cannot reach any key at all. No other function anywhere may build an OpenAlex URL. Never print, log, or commit what is in `.env`. Tests never make live calls.
 7. **Never** turn the cron job on, submit anything to ChemRxiv (Q17=b), redistribute abstract text or full text or PDFs (G10), or mark a task done without its proof.
 8. **Keep a progress log.** After each task, add one line to `docs/PROGRESS_v5.md`: `T-xx | <date> | done|blocked | <proof path or commit> | <one-line note>`.
 9. **Branch and commits.** Work on branch `v4-build` (the branch name stays; it is already created and referenced elsewhere). One commit per task, message `T-xx: <task title>`, with the proof pasted underneath the title. Merge into `main` only at T-46.
10. **Scripts first, models second.** Models are used at only these stages: 09, 12, 13, 14, 15, 16 (gate G1b only), 17. Everything else is plain Python with fixed random seeds. Every prompt lives in `prompts/` as a numbered file, and its SHA-256 is recorded in the run.
11. **Do not invent anything.** If you do not know a number, a field name, or how something behaves, it is a probe or a question. It is never a guess written into code or into the paper.
12. **The writing rule (new in v5, Q40).** Every word of the review paper is written by one model: qwen, through the opencode CLI. Claude and agy never write review text. They plan it, they review it, and they tell the writer what to change — but they do not type the manuscript. There is exactly one exception: the emergency rewrite in stage 17, where a section has already failed twice. That exception is written into the log and reported in the Telegram summary.

---

## 1. Decisions register (all resolved; the only source of truth for decision IDs)

| ID | Decision | Value |
| --- | --- | --- |
| Q1 | Scope | Perovskite photovoltaics / solar cells only. LED, laser, photodetector, X-ray, thermoelectric, supercapacitor, ferroelectric, cement, catalysis **out** (Python post-filter, never in the query) |
| Q7 | Preprints | In corpus; 10-15% of depth slots reserved; never the basis of a validated-record claim |
| Q8 | Non-English | c: machine translation of abstracts with `Lang` / `Translated` provenance; MT papers are corpus-tier only (G7) |
| Q10 | Secrets | a: `.env` |
| Q14 | Summary column | a: extractive Summary for every corpus row |
| Q15 | Storage | a: repo only; read-only sheet check retained |
| Q16 | Month assignment | c: strict canonical month by OpenAlex `publication_date`; no reconcile pass; indexing loss disclosed (S3) |
| Q17 | Submission | b: auto-build everything, **hard stop** before ChemRxiv submission (target changed from arXiv 2026-09-09, Q68) |
| Q18 | Text depth | abstracts for the corpus tier; **full text required for the depth tier** (Q37) |
| Q19, Q23 | Preprint subject categories, licence | as `config/preprint.yaml`: ChemRxiv, primary `Energy`, secondary `Materials Chemistry`, CC BY 4.0 (Q68 supersedes the arXiv archive codes; set 2026-09-09 -- perovskite PV is energy-device work. Note `Materials Chemistry` is a DIFFERENT ChemRxiv category from `Materials Science`) |
| Q20 / Q-β | Model allocation | **Superseded by Q40.** The Option A rails remain, but opus no longer writes prose |
| Q21 | Repo | **Private for now (Q47).** Public later, and only through the T-47 export gate. Every design rule that assumes a public artifact (G10 especially) stays fully in force in the meantime, because the plan is not to retrofit privacy at the end |
| Q22 | Notification | Telegram digest (+ revision-round counter, force-include confirmations, cap alerts, writer failures) |
| Q24 | Backfill | **July 2026 is the pilot (Q49), then Aug 2026, then the Sep live month.** July is signed off by hand at T-40b before Aug is harvested |
| Q26 | Failure mode | b: fail closed + notify |
| Q27 | Versioning | one git tag per month |
| Q28 | Cost | c: unbounded but ledgered in `cost.json`; opus additionally hard-capped (Q38) |
| Q28b | Future research | §10 present, gap-derived |
| Q29 | Venue impact signal | OpenAlex `summary_stats.2yr_mean_citedness` percentile on the **cumulative** journal table; optional SJR CSV tie-break; whitelist floor; Clarivate JIF refused |
| Q30 | Depth subset | N=200, band \[100, 300\], on the **depth-eligible** pool |
| Q31 / Q-α | Genre | **Monthly digest + reporting audit (see Q45).** PRISMA demoted to Methods + SI figure; "PRISMA" banned from title/abstract/headers/captions |
| Q32 | Reviewer conflicts | opus wins science; gemini wins structure/format; unresolved after one round → `[VERIFY]` flag to Havid |
| Q33 | Deliverables | `.tex`, `.bib`, `.bbl` first-class alongside PDF, DOCX, tarball, SI files (§10) |
| Q34 | Prose hygiene | `avoid-ai-writing` enforced as gate G4 with proof artefact |
| Q35 | Length regime | **Superseded by Q45.** The principle survives: ceilings on words, floors on evidence, no minimum word counts anywhere |
| Q36 | Protocol paper | **Yes.** Built from the **July** pilot after go/no-go and T-40b pass (T-42). Until it exists, the full method ships as SI-A |
| Q37 | Full-text eligibility | **OVERRIDDEN by Q53.** Kept as the option record: v5 required parsed full text for the depth tier. Probe P-04 measured 5.0% |
| **Q53** | **Abstract-first depth tier (supersedes Q37)** | **Havid 2026-09-07: "that's okay if full text is not available in most cases, just read the abstract."** Depth eligibility = a non-empty abstract. Full text is used **opportunistically**: when a PDF does parse (~5%) the card is extracted from it and flagged `text_basis=fulltext`, otherwise `text_basis=abstract`. Every card, figure, and audit row carries that flag, and §6 reports the two tiers separately — the audit must never average a full-text finding with an abstract-level one |
| Q38 | Opus access path | **RESOLVED 2026-09-07: subscription.** Havid has a Claude Code subscription login; there is no API key and none is needed. `opus_path: subscription`, `max_opus_calls: 45` stays as a runaway guard. No `ANTHROPIC_API_KEY` anywhere. P-06 is folded into P-05 and T-11 is no longer a human wait. The real budget is **quota**, not dollars, so §7.4 records `subscription_quota_used` and the 5-hour window each call landed in |
| Q39 | Cron day | **Measured.** Placeholder `DAY=12`. Four probes (P-07) on 2026-09-07/14/21/28 re-run the Aug gate; DAY = first weekly point with count ≥95% of the 28-Sep count. The cron itself is not created until T-43 and not enabled until T-46, which is now after **two** signed-off months |
| **Q40** | Writer / reviewer split | **Strict.** The opencode CLI with `opencode-go/qwen3.8-flash`, thinking high, **no fallback**, writes all manuscript prose. claude (`opus`, **effort medium**) and agy (`gemini-3.8-flash-high`) are read-only: they brief, adjudicate, check entailment, and review. Sole prose exception: the §5.17 escalation rewrite, which is logged |
| **Q41** | Model error policy | A **retry** is the same model trying again after a network or rate-limit error: 3 attempts with backoff, allowed. A **fallback** is a different model writing instead: never allowed for the writer. Writer failure = stop, Telegram, resume later with `run_month.py --from NN` |
| **Q42** | Legacy state in this repo | `common/` moves to `scripts/common/`; the v2-era scripts, `csv/perovskite_2026-07.csv`, `runs/307ba569460d/`, `runs/d099bec6d1c6/`, and `data/ledger.sqlite3` move to `archive/legacy-v2/`; July is re-harvested under the v5 schema; a fresh ledger is created rather than a pretend migration |
| **Q43** | Secret delivery | Havid writes keys into `.env` himself. A key that appears anywhere else — chat, prompt, log, commit, document — is treated as burned and rotated |
| **Q44** | Document style | Plain English. Every spec sentence says what happens and what happens when it fails. Tables, regexes, commands, file paths, and numbers are never simplified |
| **Q45** | **Length regime v3 (supersedes Q35 and the 2,400-word draft)** | **Measured on CONTENT pages, which is main text plus figures and tables, excluding the title block, the reference list, and the back matter.** Target **6-7 content pages**, which is **prose ceiling 5,500 words, expected 4,600-5,100** once the 1.82 pages of floats are subtracted. Total document lands near **9 pages**. Reader model: a working scientist with no time to read 500 papers. Mechanism coverage is **3 grouped sections** (§8.2), not 6 and not 1. **Audited-N stays 200; cited-in-body-N is capped at 180.** Both length modes live in `config/gates.yaml` keyed by mode |
| **Q46** | **Month-over-month delta** | From **month 2**, report the raw percentage-point change against the previous month, labelled provisional. Switch to the z-score once ≥3 months of history exist (§5.10). Without this the first monthly comparison would appear in month 3, and "what changed" is the reason anyone reads a monthly digest |
| **Q47** | **Public release path** | **Confirmed private by Havid 2026-09-07.** This repo stays private for now. Going public later happens by **exporting a fresh repo from a squashed clean snapshot** (T-47), never by scrubbing this history. A private repo is not a private transcript, so Q43 still holds |
| **Q48** | **Token accounting** | Every model call appends one line to `runs/<run>/tokens.jsonl`, aggregated per **stage × model × CLI** into `cost.json` and shipped as SI table S4 (§7.4). Estimated token counts are labelled `estimated`, never presented as measured |
| **Q50** | **Title grammar** | **Fixed frame + one evidence-derived slot, exactly one colon.** The frame is identical every month so the series is citable; the slot is drafted from this month's data and **must resolve to a stats key** (§8.1). Publication count is REMOVED from the title. Written by qwen under Q40, validated by script under G2 |
| **Q51** | **Axis name reconciliation** | `config/axes.yaml` on disk uses `devices_tandems` and `scaleup`; this plan's §5.6 uses `architecture` and `scale_up`. **The plan names are canonical.** T-04 renames the two keys in `axes.yaml` and `tests/test_config.py` asserts the six names match §5.6 exactly. Caught 2026-09-07 by reading the real config, not the plan |
| **Q55** | **Model reassignment (supersedes Q40's assignment, keeps its rule)** | **Havid 2026-09-07.** WRITER: `agy` with `gemini-3.8-flash-high`, thinking high, `fallback: null`. REVIEWERS, both read-only: `claude` `opus` at **effort high** (raised from medium, since opus no longer carries a writing load) for science, and `opencode` `qwen3.8-flash --variant high` for structure. `hermes` orchestrates, gates and aggregates, and writes no prose. Q40's *rule* is unchanged: exactly one model writes prose and it never has a fallback. `opus_stages` shrinks to `[17_review]` |
| **Q56** | **Main text is science; method and audit go to the SI** | **Havid 2026-09-07.** The main text is a mechanistic and critical review in eight sections: introduction, certified frontier, buried interfaces and contacts, defect tolerance and ion migration, wide-bandgap absorbers and tandems, operational stability, scale-up and the area penalty, research gaps and outlook. Methodology, the reporting audit, corpus statistics and limitations move to `supplementary.pdf` (Notes S1-S7). Prose ceiling rises to **8,000 words**, because the product is now a review rather than a digest and §8.2's 5,500 was set for the digest form |
| **Q57** | **Title grammar v2** | Title Case on every significant word. Frame is `Perovskite Photovoltaics in {Month Year}`, then one colon, then the evidence-derived slot naming the month's mechanistic themes. `Progress in Perovskite Photovoltaics` is **banned in `title_terms.yaml`**: it mimics the journal *Progress in Photovoltaics* and damages both discoverability and citation. Q50's machinery (one colon, ≤16 words, banned vocabulary, basis key for every comparative) still applies |
| **Q58** | **Abstract carries science, not only statistics** | The abstract must name the month's actual scientific highlights: the certified efficiency records by device family, the largest certified area, the longest reported T80, and the mechanistic conclusions. **Every highlight is bound to ONE extraction record by explicit DOI fragment**, and the new **G3-abstract** gate rejects any numeral in the abstract that is absent from `stats.json` and from every card field (see R35 for why this exists) |
| **Q59** | **Manuscript format follows `manuscript/example_manuscript_v2.pdf`** | **Single column** (not two). Numbered `[n]` references with **clickable `https://doi.org/` links**. Author block with four superscripted affiliations from Q19's manifest. **Exact write date**, not the month alone. Back matter: Acknowledgements (XMUM Research Fund XMUMRF/2022-C10/IENG/0046 and NSFC 52503390), Declaration of Competing Interest, Data Availability, then the AI Usage Declaration, which **opens verbatim** with "This manuscript was prepared as part of our Research Project for making a reliable Autonomous Researcher Agent." |
| **Q60** | **Figures serve the argument, not the corpus** | Main text: F1 certified frontier (certified against self-reported, by device family), F2 area penalty (efficiency against aperture area, log axis), F3 effort map (mechanism axis by device family), F4 stability evidence (every T80 plus the ISOS labels). The v1 audit bars and corpus funnel are demoted to SI figures S1 and S2. A figure earns main-text space by carrying an argument the prose cannot make in a sentence |
| **Q63** | **Figure discipline: measured devices only** | **Havid 2026-09-07.** A performance frontier plots MEASURED hardware. Exclude `lens in (theory, review)` from F1 and F2 and annotate the excluded count on the axes: a drift-diffusion study reporting ~30.8% sat beside certified hardware until Havid spotted it. **`scale_up` is kept deliberately** because those are real module measurements, so filtering to `lens == experimental` alone would wrongly drop 11 papers. Band labels use axis-fraction coordinates with `va="top"`; pinning to `ylim` collided with the data and the legend. Date block spacing is `space{2.2em}`, not 0.9em |
| **Q64** | **SI describes THIS build** | The SI takes the manuscript version as an argument and counts main-text citations by parsing the manuscript itself. A hard-coded `gate_report_v2.json` made the SI report 110 citations while the v3 main text cited 42. Never let one document quote a number computed for another |
| **Q65** | **Citation density is a gate, not a hope** | Target 60-80 references for a ~3,100-word main text (about 40 words per citation). Per-section citation targets sum into that range and a section MISSING its target is rejected. Without this, the Q61 length cut silently took citations from 110 to 42: length and bibliography are coupled, so cutting one halves the other unless the floor is enforced. New gate **G2c-cite-count** |
| **Q66** | **Submission deliverables** | **Amended by Q68: the bundle is now ChemRxiv-shaped.** Every month emits a ChemRxiv package (the rendered `manuscript_<ver>.pdf` as the main upload, `submission_metadata.json`, a generated `SUBMISSION_CHECKLIST.md`, plus archival `.tex`/`.bbl`/relative-path figures) and a CSV data pack: corpus metadata, one row per extracted number **with its verbatim source quotation**, the raw rows behind every plotted panel **including which points were excluded and why**, the audit table, and the axis distribution. The build fails closed if any absolute path survives in the tarball |
| **Q67** | **The workflow is a skill, and the format lives in Python** | Recorded as skill `monthly-review-paper-production`. The consistency mechanism, in priority order: (1) Python emits everything the reader sees, so the model cannot drift the format; (2) every defect a human finds becomes a GATE, never a prompt reminder; (3) verification parses the rendered PDF, because a stage's own success report is not evidence. For a new topic only `axes.yaml`, `exclude.yaml`, `title_terms.yaml` and the harvest FILTER change |
| **Q68** | **Preprint target is ChemRxiv, not arXiv** | Changed by Havid on 2026-09-09: the review topic is chemistry-scoped, so the series goes to ChemRxiv. This is a FORMAT change, not a rename: ChemRxiv takes the **rendered PDF** (or .docx) as the main upload and does not compile LaTeX, it uses **subject categories** (primary `Energy`, secondary `Materials Chemistry`) rather than arXiv archive codes, and it assigns a DOI under `10.26434` only **on posting** — so `preprint_doi` stays null and no script may invent it. The platform lives in ONE file, `config/preprint.yaml`, because the string `arxiv` had spread into a stage filename, an output directory, a tarball stem, a `.done` key and six documents. The stage `s20_chemrxiv` supersedes the old arXiv one and fails closed if the main PDF is missing or if the word arXiv survives in the generated metadata or checklist. **arXiv remains a harvest source** (stage 01 queries it, the ledger keeps `arxiv_id`, cited works carry arXiv DOIs); that meaning is untouched |
| **Q49** | **Pilot month = July 2026** | The first full 01→19 run is **July**, and Havid signs off on the July PDF (T-40b) before August is harvested. The validation label set moves to July with it (§6). Probes stay on August: P-01's band was measured there and P-07 is deliberately measuring indexing lag, which needs a recent month |

---

## 2. Repository layout (target state after Part II)

```
perovskite-monthly/
  .env                          # secrets, git-ignored
  .gitignore                    # data/private/, data/fulltext/, .env, runs/*/tmp/
  PLAN_monthly_perovskite_review_v{1,2,3,4}.md  # immutable, SUPERSEDED banners
  PLAN_monthly_perovskite_review_v5.md          # this file
  QUESTIONS.md  docs/BRAIN_PENDING.md  docs/PROBES_v5.md  docs/PROGRESS_v5.md
  archive/legacy-v2/            # Q42: retired v2-era scripts, CSV, runs, ledger
  config/
    author_manifest.yaml        # from v2
    models.yaml                 # §7.1
    axes.yaml                   # §5.6
    venue_whitelist.yaml        # §5.4
    exclude.yaml                # EXCLUDE / EXCLUDE_BOUND lists copied from the daily script
    hygiene.yaml                # §9 banned list, thresholds (replaces prose_rules.yaml)
    endash_allow.txt            # §9
    cards_schema.json           # §5.9
    gates.yaml                  # numeric thresholds for G1-G10, plus cron_day and page bands
    title_terms.yaml            # §8.1 frame, axis phrase table, banned-in-title list
    mt.yaml                     # §5.3 translation provider, model, prompt file
    product.yaml                # mode: review|bulletin (T-40 fallback switch)
    sjr_2025.csv                # OPTIONAL, human-dropped only
  prompts/
    cards_extract_v1.md  cards_adjudicate_v1.md  axis_adjudicate_v1.md
    brief_v1.md  draft_section_v1.md  critical_brief_v1.md  future_brief_v1.md  voice_v1.md
    entailment_v1.md  review_structure_v1.md  review_science_v1.md  offtopic_audit_v1.md
    title_v1.md
    mt_v1.md
  scripts/
    common/  net.py  ledger.py  dates.py  cleaners.py  bibtex.py  llm.py  stats_keys.py  env.py
             csvio.py  doi.py  titles.py       # carried over from the existing common/
    tools/   secret_scan.py  make_label_sheet.py  sample_picks.py  sample_cards.py
             sample_paragraphs.py
    01_harvest.py … 19_deliver.py           # §5
    run_month.py                            # driver: runs 01→19 for month M, or a stage range
  tests/                                    # fixtures only, zero live calls
    fixtures/openalex_aug2026_sample.json  fixtures/fulltext_sample.txt  fixtures/manuscript_sample.md
  data/
    ledger.sqlite3              # every work ever seen (public-safe fields)
    venues.sqlite3              # cumulative venue table
    validation/labels_v1.csv    # §6
    private/                    # git-ignored: abstracts, MT text
    fulltext/                   # git-ignored: parsed text, PDFs
  stats_history/<YYYY-MM>.json
  runs/<YYYY-MM>_<hash>/        # everything a run produces before assembly (see §5)
  csv/perovskite_<YYYY-MM>.csv  # PUBLIC corpus CSV
  manuscript/<YYYY-MM>/         # §10 deliverables
```

### 2.1 What is already in this repo, and what happens to it (Q42)

This repo is not empty. Before writing any v5 stage, map the old files onto the new ones. One commit per row, so `git blame` still works. Never delete a legacy script in the same commit that introduces its replacement.

| What exists now | v5 stage it corresponds to | Action |
| --- | --- | --- |
| `common/` (net, ledger, dates, cleaners, csvio, doi, titles, env) | `scripts/common/` | **move** — this must happen inside T-01, because T-02's security check depends on it |
| `scripts/01_harvest.py` (143 lines) | `01_harvest` (§5.1) | **rework** — keep the exclusion rules and regression tests, add the count band, the cursor logic, and the three secondary sources |
| `scripts/02_normalize.py` (214 lines) | `02_normalize` (§5.2) | **rework** |
| `scripts/03_dedupe.py` (150 lines) | `05_dedupe` (§5.5) — **the numbers clash** | **rework and renumber**. v5's `03` is translation. Do the rename in its own commit |
| `scripts/validate_csv.py` (82 lines) | folded into `16_verify` gates | **retire** to `archive/legacy-v2/` |
| `config/prose_rules.yaml` | `config/hygiene.yaml` | **replace** — every rule and threshold must be carried across, checked by diff |
| `config/category_rules.yaml`, `countries.yaml`, `csv_columns.yaml` | `axes.yaml`, CSV spec §3.2 | **rework** — v5's CSV has 23 columns, the old one has 22 |
| `csv/perovskite_2026-07.csv` (409 rows, 22 columns, longest Summary **116 words**) | rebuilt by T-13 | **quarantine.** G10 caps Summary at 60 words, so this file would fail its own gate, and July is now the pilot month that gets rebuilt properly from scratch. The repo is private for now but T-47 gates publication on the whole history, so nothing that fails a v5 gate is left at a live path |
| `runs/307ba569460d/`, `runs/d099bec6d1c6/` | run dirs are now `<YYYY-MM>_<hash>` | **quarantine** |
| `data/ledger.sqlite3` | §3.1 schema | **start fresh.** The old table does not match §3.1. `ledger.py` owns migrations, but do not fake a migration here: archive the old file, create a new one, and let the July re-harvest fill it |

---

## 3. Data contracts

### 3.1 Ledger (`data/ledger.sqlite3`, table `works`)

`work_key` (DOI lowercased, else `title_norm|first_author_surname`), `openalex_id`, `doi`, `title`, `publication_date`, `canonical_month`, `type`, `lang`, `translated` (bool), `source_primary` (openalex|s2|arxiv|crossref), `sources_seen` (csv), `venue_source_id`, `venue_type`, `first_author_institution_clean`, `axis_primary`, `axis_secondary`, `lens`, `mechanism_centrality`, `tier` (corpus|eligible|depth), `fulltext_status` (none|fetched|parsed|rejected), `fulltext_sha256`, `venue_percentile`, `depth_score`, `selection_reason`, `superseded_preprint` (doi or null), `doi_verified_at`, `first_seen_run`, `offtopic_risk` (0/1).

Abstract text, MT text, and Summary text live in `data/private/`, keyed by `work_key`. They never go in the ledger, because the ledger is committed and the repo is public.

### 3.2 Public corpus CSV (`csv/perovskite_<YYYY-MM>.csv`)

Columns: `DOI, OpenAlex ID, Title, Publication Date, Type, Venue, Venue Type, Venue Percentile, Lang, Translated, First Author Institution, Axis Primary, Axis Secondary, Lens, Mechanism Centrality, Tier, Fulltext Status, Depth Slot, Depth Score, Selection Reason, Selection Frequency, Superseded Preprint, Summary`.

`Summary` (Q14=a) is the extractive summary **only if it is 2 sentences or fewer taken from the abstract**; G10 enforces 60 words or fewer. There is no `Abstract` or `Translated Abstract` column in the public file — that would be redistributing text we do not own. The private file `data/private/<YYYY-MM>_abstracts.csv` holds `work_key, abstract, abstract_mt, summary_full`.

### 3.3 Venue table (`data/venues.sqlite3`, table `venues`)

`source_id, display_name, issn_l, type, works_count, two_yr_mean_citedness, h_index, i10_index, fetched_at, sjr_quartile (nullable), whitelisted (bool)`.

The percentile is **not stored**. It is recomputed at run time across every row where `type='journal'`, and written into the run alongside `n_reference_venues` and `snapshot_date`. Storing it would let it go stale silently.

### 3.4 Claim cards (`runs/<run>/cards/<work_key>.json`, shipped as `claim_cards.jsonl`)

Schema in `config/cards_schema.json`; structure in §5.9. Every numeric field is `{value, unit, anchor, page}`. Every anchor is 25 words or fewer and appears word-for-word in the parsed text.

### 3.5 `stats.json` key namespace (the only source of every number in the paper)

```
corpus.n, corpus.n_after_postfilter, corpus.n_by_source.{openalex,s2,arxiv,crossref}, corpus.n_preprint, corpus.n_review
corpus.lang.{en,zh,…}, corpus.n_translated
selection.n_eligible, selection.n_depth, selection.n_forced, selection.jaccard_median, selection.core_n, selection.marginal_n
venues.n_reference, venues.snapshot_date, venues.n_corpus_venues, venues.max_share_pct, venues.depth_percentile_median, venues.corpus_percentile_median
axes.<axis>.n_corpus, axes.<axis>.n_depth, axes.<axis>.share_pct, axes.<axis>.z_vs_6mo, axes.<axis>.baseline_mean_6mo
audit.corpus.<metric>.{n, pct, precision, recall, printable}     # metrics: efficiency_stated, triplet_complete, certified, stabilised, area_stated, hysteresis, isos_label
audit.depth.<metric>.{n, pct}                                    # metrics: device_count_ge20, area_stated, certified, mppt_duration, isos_label, t80_present, scan_direction
audit.trend.<tier>.<metric>.{delta_vs_6mo_pp, z}
cards.n, cards.n_claims, cards.n_nulled_fields, cards.n_dropped_papers
performance.pce_champion.{median, p90, max, n}, performance.by_architecture.<arch>.{n, pce_median}
stability.protocol_reported_pct, stability.t80_median_h
gates.<G>.{status, detail}
title.frame, title.slot_axis, title.slot_basis_key, title.slot_basis_key_2, title.slot_basis_value, title.n_words, title.has_superlative, title.superlative_basis
cost.<see §7.4>
```

Naming rule: lowercase, dots separate levels, underscores inside a name. `scripts/common/stats_keys.py` holds the list. G3 rejects any number in the paper whose key is not on it.

---

## 4. Corpus gate (Q1; carries the v3 §B-§C evidence)

### 4.1 The canonical OpenAlex query (the only place scope is decided)

```
GET https://api.openalex.org/works
  ?filter=title_and_abstract.search:perovskite AND ("solar cell" OR photovoltaic),
          from_publication_date:YYYY-MM-01,to_publication_date:YYYY-MM-<last>,
          type:article|preprint|review
  &sort=publication_date&per-page=100&cursor=*
  &select=id,doi,title,display_name,publication_date,type,language,authorships,
          primary_location,best_oa_location,open_access,abstract_inverted_index,
          cited_by_count,related_works,is_retracted            # [PROBE P-01: every select field accepted]
```

Measured 2026-09-04: **535** works for Aug 2026. Allowed band **250-1,200**.

### 4.2 Traps already found the hard way (verified in v3 — do not re-learn these)

- Putting `-term` in the query returns count 0, not a filtered list. **Never** put exclusions in the query. Exclusions happen in Python, after.
- Wildcards are rejected on `title_and_abstract.search`. Spell every variant out.
- The response key is `group_by`, not `grouped_by`.
- Source objects inside `/works` are stripped down. `summary_stats` exists only on `/sources/{id}`, and `h_index` lives **inside** `summary_stats` — it is not a top-level select field.
- Count-band check: ask first with `per-page=1`, read `meta.count`, and **abort** if `count == 0` or outside \[250, 1200\].

### 4.3 The three secondary sources (same topic conjunction; merged after dedupe)

| Source | Query sketch | \[PROBE\] |
| --- | --- | --- |
| Semantic Scholar | `graph/v1/paper/search/bulk`, query `perovskite ("solar cell" | photovoltaic)`, `publicationDateOrYear=YYYY-MM-01:YYYY-MM-<last>`, fields `externalIds,title,abstract,publicationDate,venue,openAccessPdf,authors` | P-02: bulk syntax, rate limit, whether a key is needed |
| arXiv | `search_query=all:perovskite AND (all:"solar cell" OR all:photovoltaic)`, filter `submittedDate` to the month | P-02 |
| Crossref | `query.bibliographic=perovskite solar cell photovoltaic`, `filter=from-pub-date:…,until-pub-date:…,type:journal-article`, mailto header | P-02 |

Expected total after removing duplicates: 600-750 records a month, most of them from OpenAlex.

### 4.4 Post-filter order (this replaces v3's flat exclusion list)

Let `PV = {solar cell, solar cells, photovoltaic, photovoltaics, PSC, PSCs, tandem, power conversion efficiency, PCE}`, and take `EXCLUDE` and `EXCLUDE_BOUND` from `config/exclude.yaml` (copied word-for-word from the daily script).

Apply these in order and stop at the first one that matches:

1. If any `PV` term is in the **title** → keep it, and do not test anything else.
2. Otherwise, if any `EXCLUDE` term is in the title → drop it, `selection_reason=postfilter:<term>`.
3. Otherwise, if an `EXCLUDE` term is in the abstract and no `PV` term is in the abstract → drop it.
4. Otherwise keep it, and set `offtopic_risk=1` if any `EXCLUDE` term appears anywhere.

Order matters: a paper titled "perovskite solar cell with a LED-like emission profile" is kept by rule 1 and never reaches the LED exclusion.

Dropped records go to `runs/<run>/postfilter_dropped.csv` with their title and reason, so a human can audit them. Each run, 20 random kept titles with `offtopic_risk=1` and 20 random dropped titles go to `prompts/offtopic_audit_v1.md` (agy). Disagreements are written down. They are **not** acted on automatically.

---

## 5. Stage specifications

Order is the file order. Each stage is `scripts/NN_name.py` and each one writes `runs/<run>/NN_<name>.done` containing the hashes of what went in and what came out. That `.done` file is what lets a stopped run pick up where it left off.

Run directory name: `runs/<YYYY-MM>_<8-char sha of (month, git commit, config hash)>/`. Every stage reads only from the run directory and the databases, and writes only into the run directory. The databases are written by stages 04 and 05 alone.

### 5.1 `01_harvest`

In: the month M. Out: `01_openalex.jsonl`, `01_s2.jsonl`, `01_arxiv.jsonl`, `01_crossref.jsonl`, `01_meta.json` (counts, pages, wall time).

Steps: run the count-band check (§4.2) → page through with the cursor using `net.oa()` (6 pages expected; abort past 15) → fetch the secondary sources with `net.plain()` → log the count from each source. Abstracts are rebuilt from `abstract_inverted_index` straight away and written to the run's `private/` sub-directory, never into the public JSONL.

### 5.2 `02_normalize`

In: the stage 01 files. Out: `02_records.jsonl` (one canonical record per §3.1), `private/02_abstracts.jsonl`.

Steps: normalise the DOI (lowercase, strip `https://doi.org/`); normalise the title (`title_norm` = lowercase alphanumerics with single spaces); detect the language from title plus abstract (`lingua` or `langdetect`, pinned version); clean up institutions using the v2 §4.2 rules (strip "Key Laboratory of…", "Ministry of Education", department suffixes; use the OpenAlex institution `display_name` when there is one); take `venue_source_id` from `primary_location.source.id` and `venue_type` from `primary_location.source.type`.

### 5.3 `03_translate`

In: stage 02 records where `lang != en`. Out: `private/03_abstracts_mt.jsonl`, and `Translated=mt` set on the record.

The provider, the model, and the prompt file are pinned in `config/mt.yaml` and `prompts/mt_v1.md`. v4 said "exactly as v2" — that is a dead reference now that v2 is frozen, so v5 pins it in its own config file instead.

Numbers in the original language are kept next to the translation, because G3 has to check the paper's numbers against the original tokens, not against the translation.

### 5.4 `04_venues`

In: the distinct `venue_source_id` values in the stage 02 records. Out: rows in `data/venues.sqlite3`, and `04_venue_percentiles.json` (per source_id: the percentile or null, plus `n_reference_venues` and `snapshot_date`).

For every id that is missing from the table, or whose `fetched_at` is more than 90 days old: `GET /sources/{id}?select=id,display_name,issn_l,type,works_count,summary_stats` through `net.oa()`.

The percentile is computed over **every cumulative row where** `type='journal'`: `percentile = rank(two_yr_mean_citedness, ascending) / n_reference`. A source that is not a journal gets `null`, never 0 — a preprint server is not a badly cited journal, it is not a journal. If `config/sjr_<year>.csv` is present, join on `issn_l` to add `sjr_quartile`. The whitelist flag comes from `config/venue_whitelist.yaml` (about 25 venues, listed in v3 §D.2 Tertiary).

The reference set must be **cumulative** (R16). Do not narrow it to this month's venues, or the percentiles will drift every month for no real reason.

### 5.5 `05_dedupe`

In: stage 02 records. Out: `05_corpus.jsonl` (one record per work, all with `canonical_month == M`), and the ledger updated.

Steps: `work_key` is the DOI, or `title_norm|first_author_surname` when there is no DOI. Merge duplicates across sources into one record and list them in `sources_seen`. The OpenAlex `publication_date` wins. A record from S2, arXiv, or Crossref with no OpenAlex match is kept if its own publication date falls in M.

Linking a preprint to its published version: if `related_works` \[PROBE P-03\] matches, or if `title_norm` similarity is 0.90 or higher by `rapidfuzz.token_set_ratio` **and** the first-author surname matches, and the match is an earlier ledger row with `type=preprint`, then set `superseded_preprint=<earlier doi>`. The earlier row is **not** edited (Q16=c) — past months are already published and stay as they were.

Retracted works (`is_retracted`) stay in the corpus with a flag, and are barred from the depth tier.

### 5.6 `06_mechanism`

In: the stage 05 corpus plus abstracts. Out: `06_labels.jsonl` (`axis_primary, axis_secondary, lens, mechanism_centrality, matched_keywords`), and `06_validation_metrics.json` when `labels_v1.csv` exists.

`config/axes.yaml` shape:

```yaml
axes:
  composition:   {keywords: {"formamidinium": 2, "FA/Cs": 2, "phase segregation": 3, "halide segregation": 3, "2D/3D": 2, "strain": 1, "lead-free": 2, "tin perovskite": 2, "cesium": 1, …}}
  defects:       {keywords: {"passivation": 3, "trap density": 3, "ion migration": 3, "defect": 2, "non-radiative recombination": 3, "additive": 1, …}}
  interfaces:    {keywords: {"self-assembled monolayer": 3, "SAM": 2, "hole transport": 2, "electron transport": 2, "buried interface": 3, "band alignment": 2, "NiOx": 1, "SnO2": 1, …}}
  architecture:  {keywords: {"tandem": 3, "two-terminal": 3, "four-terminal": 3, "recombination layer": 3, "current matching": 3, "bifacial": 2, "back-contact": 2, …}}
  stability:     {keywords: {"ISOS": 3, "damp heat": 3, "light soaking": 2, "T80": 3, "encapsulation": 2, "reverse bias": 2, "thermal cycling": 2, "degradation": 1, …}}
  scale_up:      {keywords: {"module": 3, "slot-die": 3, "blade coating": 3, "roll-to-roll": 3, "large-area": 2, "techno-economic": 3, "LCA": 2, "minimodule": 3, …}}
lens:
  theory:   ["DFT", "first-principles", "simulation", "machine learning", "drift-diffusion", "SCAPS"]
  review:   ["review", "perspective", "roadmap"]
  scale_up: ["module", "roll-to-roll", "slot-die", "techno-economic"]
```

Each axis scores `Σ weight × (2 if the word is in the title else 1)`, matched on whole words, ignoring case. `axis_primary` is the highest scorer. `mechanism_centrality` is that top score divided by the maximum possible score for that axis, clipped into \[0,1\].

If the runner-up axis scores at least 0.8 of the winner, set `axis_secondary` and send the pair to qwen (`prompts/axis_adjudicate_v1.md`, title plus abstract). qwen must return one axis **and** the keywords that decided it. The script then checks those keywords really are in the text; if they are not, the keyword winner stands. A model that cannot show its evidence does not get to overrule the regex.

Lens comes from a keyword hit, defaulting to `experimental`.

Validation (§6): when `data/validation/labels_v1.csv` exists, compute scope precision and recall, exclusion precision and recall, axis micro-F1, and precision and recall for each §9 regex, into `06_validation_metrics.json`. When it does not exist, write `{"status": "unvalidated"}`, and every corpus-tier §9 metric is forced to `printable=false`, which means the paper may only use lower-bound wording for it.

### 5.7 `07_fulltext`

In: the stage 05 corpus. Out: `data/fulltext/<work_key>.txt` and `.pdf` (both git-ignored), plus `07_fulltext_status.jsonl` (`status, source, sha256, n_words, pages`).

**Why this stage exists.** It is the decision that makes §9 defensible. Abstracts do not say whether a measurement was certified, how many devices were made, or what the aperture area was — a paper can do all of it properly and mention none of it in 200 words. Auditing reporting practice from abstracts measures what authors chose to summarise, not what they did. So the depth tier requires the real paper. The price is a smaller and more open-access-biased subset, which S4 discloses in the paper.

Per work, try these in order and stop at the first success: (a) `best_oa_location.pdf_url` \[PROBE P-04: how often is this non-null on August\]; (b) `open_access.oa_url` if it ends in `.pdf`; (c) Unpaywall, `GET https://api.unpaywall.org/v2/{doi}?email=<from .env>` → `best_oa_location.url_for_pdf` \[PROBE P-04\]; (d) for `type=preprint`, the arXiv or ChemRxiv PDF URL on the record.

Fetch with `net.plain()`, 20 s timeout, 1 request per second per host, 2 retries. Parse with `pymupdf` (`fitz`), inserting `<<p=N>>` page markers so an anchor can carry a page number.

**Reject** the text if the body has fewer than 2,000 words, or more than 0.30 of it is non-alphanumeric, or the language is not English (G7: the extractor has only been validated on English). A rejected parse is not a silent zero — it is a recorded `rejected` status.

`tier=eligible` only when `status=parsed`. Retracted works and MT-only works are never eligible. Budget about 15 minutes. Per-source success rates go to `07_fulltext_summary.json`.

### 5.8 `08_subset` (constrained picker, plus a fragility test)

In: the stage 05 corpus, the 04 percentiles, the 06 labels, the 07 statuses, and the cumulative card history (composition and architecture tokens from `data/ledger`). Out: `08_subset_scores.csv`, `08_sensitivity.json`, `08_force_include_pending.json`.

Score, for eligible works only:

```
score = 0.40*venue_percentile (null→0.0, whitelisted→max(percentile, 0.90))
      + 0.35*mechanism_centrality
      + 0.25*novelty_flag   (1.0 if a composition or architecture token in title/abstract is absent from cumulative history, else 0.0)
```

Selection, deterministic, seed 0:

1. `N_target = min(200, floor(0.4 * n_eligible))`, clipped into \[100, 300\]. If `n_eligible < 100`, then `N_target = n_eligible` and set `small_pool=true`.
2. Force-includes: any eligible work whose abstract matches `\bcertif(ied|ication)\b` and co-occurs with a PCE at or above the cumulative maximum in card history goes into `08_force_include_pending.json`, and the run **pauses** (⛔ HUMAN, one Telegram yes/no per item; if nobody answers within 48 h it stays paused). Confirmed items are selected first.
3. Per axis: take the highest-scoring eligible works until each axis has at least 12. Skip an axis with fewer than 12 eligible works, and record the shortfall.
4. Preprints: if preprints are under 10% of `N_target`, add the highest-scoring eligible preprints until they reach 10%. Never go past 15%.
5. Fill up to `N_target` by score, subject to two caps: no single venue over 8% of `N_target`, and no single `first_author_institution_clean` over 10%.
6. Write `Depth Slot, Depth Score, Selection Reason` (`forced|axis:<a>|preprint|score`) for each work.

**First month, empty history (new in v5).** In the pilot month there is no card history at all. Two consequences, stated so nobody has to guess: no force-include can fire in step 2, because there is no cumulative maximum PCE to compare against; and `novelty_flag = 1.0` for every eligible work, so the novelty term adds a flat 0.25 to everyone and does no sorting whatsoever. Ranking in August is effectively 0.40 venue plus 0.35 centrality. The novelty term only starts doing work from month 3.

**A regex note, so nobody "tidies" it into a bug.** v4 wrote this as `(?<!un)\bcertif(ied|ication)\b`. That lookbehind is inert: `\b` sits between `un` and `certif`, so the negative lookbehind can never see the `un`. It is harmless and it is left as `\bcertif(ied|ication)\b` here. If you actually want to exclude "uncertified", the working form is `(?<![A-Za-z])certif(ied|ication)\b`. Do not change this without deciding which behaviour you want and writing down why.

Fragility test: draw 200 weight vectors `w ~ (0.40,0.35,0.25) + U(-0.10, 0.10)` per component, renormalise each to 1, and run steps 3-5 with each. `Selection Frequency` for a work is the share of draws that selected it. Record `jaccard_median` against the shipped set, `core_n` (frequency 0.95 or higher), and `marginal_n` (frequency under 0.50). All of it goes into `08_sensitivity.json` and into the CSV. This is how the paper can say out loud how arbitrary its own 200 picks are.

### 5.9 `09_cards`

In: the depth-selected works and their parsed text. Out: `cards/<work_key>.json`, `09_cards_summary.json`, and possibly a signal to re-run 08.

Prompt `prompts/cards_extract_v1.md`: qwen3.8-flash through the opencode CLI, temperature 0, output constrained to the JSON schema in `config/cards_schema.json`. Input is the full text with page markers, chunked at about 12k tokens with 500 tokens of overlap, merged field by field with the rule "the first non-null anchored value wins".

Two independent passes with different chunk boundaries (offset 0 and offset 2k tokens). Where the two passes disagree on a field, send both candidates plus the surrounding text to `prompts/cards_adjudicate_v1.md` on agy.

Card structure:

```json
{"doi": "...", "work_key": "...", "axis": ["defects","interfaces"], "lens": "experimental",
 "device": {"architecture": "p-i-n|n-i-p|tandem_2T|tandem_4T|module|none|unknown", "absorber": "…|null"},
 "performance": {"pce_champion": {"value": 25.1, "unit": "%", "anchor": "…", "page": 3},
                 "pce_certified": {…}, "pce_stabilised": {…}, "voc": {…}, "jsc": {…}, "ff": {…},
                 "active_area_cm2": {…}, "device_count_n": {…}},
 "stability": {"protocol": "ISOS-L-1|null", "duration_h": {…}, "t80_h": {…}},
 "claims": [{"id": "<work_key>#1", "text": "…", "anchor": "…", "page": 5, "evidence_type": "measurement|simulation|inference"}],
 "reporting_flags": {"states_certification": false, "states_area": true, "states_device_stats": true, "states_mppt_duration": false, "isos_labelled": false, "states_scan_direction": true},
 "extractor": {"model": "qwen3.8-flash", "prompt_sha": "…", "adjudicated_fields": ["voc"], "run": "…"}}
```

Then the script — not the model — enforces these guards. This is the part that stops invented numbers:

1. The anchor must appear word-for-word in the parsed text (whitespace normalised, case sensitive). If it does not, the field becomes null and is counted in `n_nulled_fields`.
2. The numeric `value` must appear inside its own anchor as digits (allowing `,` and `.` variants). If it does not, the field becomes null. A model cannot claim 25.1% while quoting a sentence that does not contain 25.1.
3. Anchors are truncated to 25 words **after** checks 1 and 2, not before.
4. `reporting_flags` are recomputed by the script from the anchored fields. A flag is true only when the matching field has a valid anchor. Whatever the model put in `reporting_flags` is advisory and is discarded.
5. If a card has no claims left after the guards, that paper becomes corpus-only, its depth slot is freed, and stage 08 re-runs **once** to fill it. Cards are then extracted for the newly picked papers. Anything that drops out on the second pass stays unfilled and is disclosed rather than backfilled.

Log tokens per pass and the number of adjudications.

### 5.10 `10_stats`

In: everything above, plus `stats_history/`. Out: `stats.json` (§3.5) and `stats_history/<M>.json`.

Corpus-tier §9 regexes run on the abstract, on whole words, ignoring case. Each carries its precision and recall from `06_validation_metrics.json`, and `printable = precision ≥ 0.85`:

```
efficiency_stated : \b(PCE|power conversion efficiency|efficiency)\b.{0,40}?\b\d{1,2}(\.\d+)?\s?%
triplet_complete  : all three of \bV_?oc\b, \bJ_?sc\b, \b(FF|fill factor)\b
certified         : (?<!un)\bcertif(ied|ication)\b
stabilised        : \b(stabili[sz]ed|steady[- ]state|maximum power point|MPP[T]?)\b
area_stated       : (?<!mA\s?/?\s?)(?<!mA\s)\b\d+(\.\d+)?\s?(cm|mm)\s?(\^|²|2)\b   # excludes the Jsc unit form
hysteresis        : \b(hysteresis|reverse scan|forward scan|scan rate|scan direction)\b
isos_label        : \bISOS-[LVDTP]+(-\d)?\b
```

(The same `(?<!un)` note from §5.8 applies to `certified` here. It is inert, it is harmless, leave it alone.)

Depth-tier metrics come from the cards: `reporting_flags`, `device_count_n ≥ 20`, `t80_h` non-null, `stability.protocol` non-null, `active_area_cm2` non-null, `pce_certified` non-null, and `states_scan_direction`.

Axis z-scores: `z = (share_M − mean(share over previous 6 months)) / std(...)`. With fewer than 3 months of history, `z=null`.

**Month-over-month delta (Q46, new).** `z=null` alone used to mean the digest could say nothing comparative until month 3, which is fatal for a monthly product — "what changed since last month" is the reason anyone opens it. So from **month 2**, every axis share and every `audit.*` percentage also carries `delta_vs_prev_month_pp`: the raw percentage-point change against the immediately preceding month, plus `delta_basis: "single-month, provisional"`. The paper prints it as "up 6 percentage points on June, a single-month change and not yet a trend". From month 3 the z-score appears alongside it and becomes the headline number. New keys: `axes.<axis>.delta_vs_prev_month_pp`, `audit.<tier>.<metric>.delta_vs_prev_month_pp`, and `<...>.delta_basis`. This also makes F5 usable from month 2 instead of month 3.

### 5.11 `11_figures`

matplotlib, PNG (carrying the `run_hash` in a `tEXt` chunk) plus PDF.

Main figures: F1 axis shares and z-scores; F2 venue-percentile distribution, corpus against depth; F3 corpus-tier audit metrics with precision/recall error bars; F4 depth-tier audit metrics; F5 the longitudinal audit series (from month 3 onward; before that, single-month bars); F6 champion PCE by architecture (from cards); F7 stability protocol reporting and the T80 distribution (from cards); optional F8 institution and country share; optional F9 the selection-frequency histogram.

SI figures: S1 the corpus construction funnel (this is the demoted PRISMA-style figure, and its caption never uses the word), S2 the sensitivity Jaccard distribution.

Every plotted number is read out of `stats.json`. F6 and F7 read the card aggregates that stage 10 wrote into `performance.*` and `stability.*`. The script asserts that no number is hard-coded in the figure code.

### 5.12 `12_brief` (opus, effort medium — a brief, not prose)

In: `stats.json`, all the cards, and the §8 section spec. Out: `12_brief.json`, holding for each section `{ceiling_words, thesis_sentence, claim_ids_in_order[], stats_keys_used[], figure_refs[]}`.

**This stage no longer writes prose (Q40).** It produces a structured plan: which claim IDs go in which section in which order, which stats keys that section may use, and one thesis sentence per section for the writer to work from.

Rules in `prompts/brief_v1.md`: reference only card claim IDs and stats keys that exist; **§§3-5 each open with their axis shares and, from month 2, the month-over-month delta (Q46)**; each depth paper is cited in at most one section; **select at most `gates.yaml: max_body_citations` (180) works for in-body citation out of the 200 audited, and record which** — the brief owns that choice, because it is a scientific judgement about what mattered this month, not a truncation; flag any section whose assigned cards yield fewer than 8 claims, so stage 13 knows the G2 content floor may not be reachable. **Also decides the title slot (Q50)** by the deterministic order in §8.1 and records `title.slot_axis`, `title.slot_basis_key`, and the basis value, so the title is fixed from evidence before any prose exists. One call for the skeleton plus one call per two sections, roughly 4 calls.

### 5.13 `13_draft` (qwen3.8-flash via opencode, thinking high)

For each section, the input is that section's brief entry, the cards it references, the slice of `stats.json` it is allowed to use, and `prompts/draft_section_v1.md`.

Output is markdown with citation markers `[@<work_key>]` and stats markers `{{stats:<key>}}`. The assembler turns the stats markers into real numbers later, which is exactly what lets G3 trace every number back to a key.

Rules: every sentence that states a fact about a specific paper carries a citation marker. No number appears without a stats marker or a card field behind it. The word ceiling is enforced by drafting again, shorter — never by chopping the end off a finished section. §1 and §2 are also written by qwen, with §2 built on a fixed template that contains the three-tier sentence.

### 5.14 `14_critical` (opus brief → qwen draft)

This is the section that judges the field's reporting practice, so v4 had opus writing it. Under Q40 opus produces the brief and qwen writes it.

opus (effort medium) produces `14_brief.json` from the `audit.*` keys, the depth cards, the axis shortfalls, and the card claims whose `evidence_type=inference`: the findings for **§6** and the gaps for **§7**, each tied to a stats key or a claim ID. Prompts `prompts/critical_brief_v1.md` and `prompts/future_brief_v1.md`. 2-3 calls. qwen then drafts `sec06.md` and `sec07.md` from that brief exactly as in §5.13.

**Quality guard, because a flash model is now writing the scientific heart of the digest.** **§6 (the audit) and §7 (the gaps)** get a minimum of two review rounds in stage 17, not one. And pilot criterion 4 in §12 (at least 8 of 10 spot-checked depth flags agree with the PDF) is a hard pass/fail. If pilot criterion 3 or 4 fails, the first lever to pull is raising the reviewer's effort back up — and only Havid may pull it (see Appendix B).

### 5.15 `15_voice` (qwen3.8-flash via opencode)

A coherence and voice pass over the assembled `manuscript.md`, in chunks of about 2,000 words, each chunk given the previous chunk's last paragraph as context so the seams do not show.

This stage may not add facts, markers, or numbers. G3 and G1 diff the marker set and the number set before and against after, and any addition fails the run. That check matters more in v5 than it did in v4, because the model doing the voice pass is now a flash model rather than opus. 5-6 calls.

### 5.16 `16_verify`

Runs gates G1 to G10 (§10). Writes `gate_report.json`, `g1b_fidelity.jsonl`, and `g4_prose.txt`.

### 5.17 `17_review` (agy and opus in parallel, both read-only)

agy reviews structure and format; opus (effort medium) reviews the science. They run at the same time and never see each other's output.

Each finding is JSON: `{"section": "§4", "severity": "red|orange|yellow", "finding": "…", "evidence": "<quote or key>", "fix": "…"}`, written to `runs/<run>/review/round<k>_<model>.json`.

Reviewers receive `manuscript.md`, `stats.json`, `claim_cards.jsonl`, and the public CSV. They never receive the prompts or the brief — a reviewer that has read the instructions grades the instructions, not the output.

Revisions are made by qwen for every section (Q40; v4 sent its §§9-11 to opus, which under the §8.2 map are now §§6-8). Conflicts follow Q32: opus wins on science, agy wins on structure and format. After each round, G4 and G1b run again.

ACCEPT means zero red and no more than 3 orange from both reviewers. Up to 3 rounds. **§6 and §7** always get at least 2 rounds (§5.14).

If a section is still red after the rounds, opus rewrites it once. **This is the single documented exception to the writing rule (Q40)**, it is recorded in `cost.json` as an escalation, and it is named in the Telegram summary. If it is still red after that, a `[VERIFY]` item goes to Havid and the run pauses.

### 5.18 `18_build`

`manuscript.md` → `manuscript.tex` (pandoc, natbib `super,sort&compress`, `naturemag.bst`) → tectonic inside `.staging/` with `--keep-intermediates` to capture the `.bbl` → swap the results into `manuscript/<M>/`. DOCX through `pandoc --citeproc nature.csl` with `.png` figure paths. The archival LaTeX tarball uses relative paths and `\graphicspath{{fig/}}`. Plus `metadata.txt` and the SI files copied in. Finally, compile the `.tex` on its own from a clean temporary directory, to prove it does not secretly depend on something in the build tree.

### 5.19 `19_deliver`

Send the Telegram summary: **the title together with its `slot_basis_key` and basis value, so the reason for that title is visible and not just the wording**, the three-tier sentence, the gate table, how many revision rounds ran, opus calls against the cap, `opus_path: subscription`, and the quota windows used, **any writer failures and any Q40 escalation**, **the per-stage token totals (§7.4)**, the G4 and G1b proof lines, the force-include decisions, and any `[VERIFY]` items. Write `cost.json`. Commit with the G4 and G1b proof pasted into the message, and tag `<YYYY-MM>`.

Then ⛔ **hard stop**. There is no submission call anywhere in the codebase -- not to arXiv, not to ChemRxiv -- and there never will be. ChemRxiv is a manual portal upload (`submission_route: manual_portal`).

---

## 6. Validation set (`data/validation/labels_v1.csv`)

Nothing in §6 can be stated as a percentage until a human has labelled a sample by hand. This is the file that turns "our regex matched 61%" into "61%, with precision 0.9 and recall 0.84".

- **What goes in it:** 200 works from **Jul 2026, the pilot month** — 100 picked at random from inside the gate after post-filtering; 50 picked at random from `bare perovskite` minus the gate (this measures scope **recall**, the papers we wrongly missed); 50 picked at random from the post-filter drops (this measures exclusion **precision**, the papers we wrongly threw away).

**Why July and not August (changed in this revision).** The label set must be drawn from the month the pilot actually ships, or the audit's precision and recall figures describe a different distribution than the one being audited. July has a second advantage: its indexing has settled, so a paper missing from the gate is much more likely to be a genuine scope miss than an indexing lag, which makes the recall number mean what it claims to mean. The probes stay on August, because P-01's band was measured there and P-07 is deliberately measuring lag, which needs a recent month.
- **The sheet** is generated by `scripts/tools/make_label_sheet.py` with columns `work_key, title, abstract (private copy), in_scope_pv (Y/N), axis_primary (one of six), axis_secondary (optional), efficiency_stated, triplet_complete, certified, stabilised, area_stated, hysteresis, isos_label` — each judged from the abstract. Havid fills it in, about 3-4 hours. ⛔ HUMAN.
- **Frozen** once it is done. `labels_v2.csv` may only add rows, never change existing ones, or the metrics stop being comparable month to month.
- **Metrics**, recomputed in stage 06 every run: scope precision and recall, exclusion precision and recall, axis accuracy and micro-F1, and precision and recall for each regex. Written to `validation_metrics.json` and shipped as SI.
- **The print rule:** a corpus-tier §9 metric may be printed as a plain "x%" only when its precision is 0.85 or better. Otherwise the assembler writes "detected in at least x% of abstracts (precision p, recall r)". G2 checks the wording actually matches the `printable` flag.

**Havid's labelling is the critical path.** Nothing downstream can print a corpus-tier percentage without it, so the label sheet is generated as early as the task order permits.

---

## 7. Models, CLI, budget

### 7.1 `config/models.yaml`

```yaml
allocation: A                       # Option A rails; prose ownership per Q40
writer_rule: strict                 # Q40: only the generator writes manuscript prose

generator:                          # writes EVERY word of the manuscript
  cli: opencode
  provider: opencode-go
  model: qwen3.8-flash
  thinking: high
  fallback: null                    # Q40: no fallback model, ever
  fallback_policy: fail_closed      # Q41: stop, notify, resume with --from
  retries: 3                        # Q41: same model only, exponential backoff

extractor:                          # 09_cards; same model, schema-constrained
  cli: opencode
  provider: opencode-go
  model: qwen3.8-flash
  passes: 2
  temperature: 0
  thinking: see_P-08                # decided by probe P-08; for constrained JSON, low/off is likely better

adjudicator:        {cli: agy, model: gemini-3.8-flash-high}
entailment:         {cli: agy, model: gemini-3.8-flash-high, temperature: 0}
reviewer_structure: {cli: agy, model: gemini-3.8-flash-high}
reviewer_science:   {cli: claude, model: opus, effort: medium, allowed_tools: "Read,Grep,Glob", max_turns: 10}

opus_stages: [12_brief, 14_brief, 17_review, 17_escalation]
max_opus_calls: 45                  # Q38; pause-and-notify when reached
opus_path: subscription             # Q38 RESOLVED: Claude Code subscription login, no API key
max_review_rounds: 3
min_rounds_sections: {"6": 2, "7": 2}   # §5.14 quality guard: audit + gaps sections
```

Note on YAML: `fallback: no fall back` is not valid YAML — a loader reads a bare `no` as the boolean false and then chokes on the rest of the line. The correct way to say "there is no fallback" is `fallback: null` plus an explicit `fallback_policy` string.

### 7.2 How each model is actually invoked

The invariant, in one sentence: **claude and agy are always called read-only, and only opencode ever writes a file — and only inside the run directory.**

- **Writer and extractor (opencode).** Exact flags are set by probe **P-08**. v4 had no verified non-interactive opencode invocation, and a no-fallback policy makes that hole expensive, so P-08 must land before stage 13 is written. Until then, do not write a guessed command line into any script.
- **Science reviewer and briefer (claude):** `claude -p "<prompt>" --model opus --effort medium --output-format json --max-turns 10 --allowedTools "Read,Grep,Glob"`. Read-only consultant. Never an executor. (v4 used `--effort xhigh`; every occurrence is now `medium`.)
- **Adjudicator, entailment, structure reviewer (agy):** `agy -p "<prompt>" --model gemini-3.8-flash-high --dangerously-skip-permissions --print-timeout 900s`.
- Cron pins the writer with `hermes cron edit <id> --provider opencode-go --model qwen3.8-flash`. Cron's `--reasoning-effort` does not reach the claude CLI, so effort is passed on the command line instead.

Every call goes through `scripts/common/llm.py`, which records the model, the prompt SHA, the token counts, and the wall time, and bumps that model's counter in `cost.json`. When `opus_calls >= max_opus_calls`, it writes `cost.json.cap_hit=true`, sends a Telegram alert, and exits with code 75, which means "paused, not failed".

**Retries versus fallbacks (Q41), spelled out so nobody re-adds a fallback later.** A retry is the same model trying again after a network or rate-limit error: 3 attempts, exponential backoff, allowed everywhere. A fallback is a different model doing the work instead: **not allowed for the writer, at all**. If the writer is unavailable, the stage fails closed, Telegram fires, and the run resumes later with `run_month.py --from NN`. The `.done` markers are what make a no-fallback policy survivable — nothing already finished is ever redone. The opus science review is likewise never substituted; if opus is unavailable, the run pauses at stage 17.

### 7.3 Opus budget (per month)

Because opus no longer writes prose, its call count drops a lot.

| Stage | Calls | Change from v4 |
| --- | --- | --- |
| 12 brief (was outline + prose briefs) | 3-4 | same |
| 14 §9 + §10 brief only (was writing them) | 2-3 | same count, no prose |
| 15 voice | **0** | was 5-6; now qwen |
| 17 science review, \~5 per round × ≤3 | 5-15 | same |
| 17 escalation rewrite (Q40 exception) | 0-3 | new, was folded into "escalations" |
| escalations / `[VERIFY]` follow-ups | 0-5 | was 0-8 |
| **Total** | **10-30**, cap 45 | was 25-40 |

The cap stays at 45 rather than dropping to match. The headroom pays for escalation rewrites, `[VERIFY]` follow-ups, and the T-42 protocol paper, and a cap that is never reached costs nothing.

### 7.4 Token and quota ledger

**Q48 (new): count every call, per stage, per model, per CLI.** Every call through `scripts/common/llm.py` appends one line to `runs/<run>/tokens.jsonl` before it returns:

```json
{"stage": "09_cards", "model": "qwen3.8-flash", "cli": "opencode", "prompt_sha": "…",
 "tokens_in": 11840, "tokens_out": 620, "token_source": "reported|estimated",
 "wall_time_s": 18.4, "retry_n": 0, "window_id": "2026-09-07T14", "work_key": "10.1002/…"}
```

Append-only, one line per call including retries, written before the return so a crashed stage still leaves its accounting behind. `10_stats` aggregates it into `cost.json` as `tokens.<model>.by_stage.<NN>.{in,out,calls}` and totals, and stage 19 renders a **stage × model matrix** as SI table S4 plus one summary line in the Telegram digest.

`token_source` is not decoration. If P-08 finds that opencode does not report usage, tokens are estimated with a pinned tokeniser and every downstream number says `estimated` — an estimate labelled as measured is the kind of quiet lie this whole plan exists to prevent.

**Subscription changes what "cost" means (Q38).** On a Claude Code subscription an opus call costs no money and consumes **quota**. So `est_cost_usd.opus` is `null`, never `0.0` — zero would imply free, and the truth is that it is rationed. Instead `cost.json` carries `subscription_quota_used` and the rolling 5-hour `window_id` each call landed in. This is the only way to learn whether one monthly run fits inside the allowance, which is now the binding budget. It also means `llm.py` must treat "rate-limited right now" as **exit 75, pause and resume**, not a failure — the run is not broken, it is early.

`cost.json` keys: `opus_path, opus_calls, opus_cap, subscription_quota_used, quota_windows[], gemini_calls, qwen_calls, writer_failures, writer_retries, escalation_rewrites, tokens.<model>.{in,out}, tokens.<model>.by_stage.<NN>.{in,out,calls}, token_source.<model>, est_cost_usd.<model>, api_calls.{openalex,s2,arxiv,crossref,unpaywall}, pagination_pages, fulltext_fetches.{attempted,parsed}, review_rounds, g1b_rounds, wall_time_s.<stage>`.

**What this is for.** After the July run you will know exactly which stage burned the tokens. The prediction is that stage 09 dominates — 200 PDFs × 2 passes × ~12k-token chunks — and that writing 2,200 words is a rounding error beside it. If that holds, the lever for cost is the depth-tier size and the chunk overlap, not the manuscript length. Verify it against `tokens.jsonl` rather than trusting the prediction.

---

## 8. Manuscript specification

### 8.1 Title, abstract, back matter

**Title grammar (Q50).** Two parts: a frame that never changes, and one slot derived from this month's data.

```
{frame}, {Month Year}: {slot}
```

- `{frame}` — fixed string from `config/title_terms.yaml: frame`, default `Perovskite photovoltaics`. Identical every month, so the series is citable and recognisable.
- `{Month Year}` — the run month, placed in the frame half so it never collides with the slot and no trailing `(July 2026 Update)` is needed.
- `{slot}` — 6-14 words, drafted by qwen from a controlled phrase table, and **required to resolve to a stats key**.

**Why the slot is gated at all.** Every number in the body resolves to a `stats.json` key or a card field (G3), but an adjective in a title resolves to nothing. A free-text title slot is exactly where an over-claim would enter this pipeline — and over-claiming is the thing §6 exists to audit. So the title joins the evidence regime rather than floating above it.

Rules:

1. At most `max_title_words` (16) words in total.
2. **Exactly one colon**, and no other subtitle punctuation. Em-dash is banned outright by §9; en-dash is legal only under the §9 allowances, so `p–i–n` is fine and a decorative dash is not. (v4 and the v5 draft said "no subtitle" while shipping a colon in the pattern — that clause meant no *second* subtitle, and it is stated properly here.)
3. The §9 banned-vocabulary list applies to the title with **no exceptions**. The "state-of-the-art on a line with a citation marker" allowance does not extend to the title.
4. **No publication count in the title.** v4 and the v5 draft both put `{corpus.n}` there. S3 says the count is the indexed record as of a snapshot date and "not the month itself", so a headline figure contradicts our own caveat, goes stale silently as the month backfills, and is the number most likely to be quoted out of context. Counts belong in the abstract and §2, where S3 can qualify them.
5. **Comparatives and superlatives are evidence-bound.** A slot claiming an improvement, advance, rise, record, or highest value must carry `title.slot_basis_key`. If the claim concerns efficiency, the basis must be a `pce_certified` or `pce_stabilised` anchor from a **non-preprint depth paper** — the reporting failure §6 audits is not allowed to appear in our own headline. An uncertified champion may still be the month's story, but the slot must then say what kind of number it is.
6. `title.slot_axis` must be one of the six §5.6 axis names or `audit` for a reporting finding, and must be phrased from `title_terms.yaml` for that axis. This is what stops the title inventing a seventh category or a synonym the labelling stage never used, and it means a reader finds the headline topic in the section where it is actually written.
7. A slot may carry **at most two claims**: one mechanism clause plus one audit clause, each with its own basis key (`slot_basis_key_2` is the optional second). That is what makes "X rises, Y still lags" both legal and checkable.

**Slot selection, deterministic, decided in stage 12 before any prose exists:**

1. the axis with the largest positive `axes.<axis>.delta_vs_prev_month_pp` (from month 2, Q46), if it is at least 3 pp;
2. else the axis with the highest mean `mechanism_centrality` in the depth tier;
3. else a reporting finding from `audit.*` whose `printable` is true;
4. else the `neutral_slot` from `title_terms.yaml`.

Illustrative outputs, not fixed strings:

- `Perovskite photovoltaics, July 2026: defect passivation compounds while certification reporting stalls`
- `Perovskite photovoltaics, July 2026: tin perovskites reach the depth tier, stability protocols do not`
- `Perovskite photovoltaics, July 2026: a monthly mechanism and reporting audit` (the neutral fallback)

Havid's worked example, `"Progress in Perovskite Photovoltaics: Halide Passivation Strategies for Enhanced Efficiency and Durability (July 2026 Update)"`, was checked against these rules and fails four of them, which is why they exist: it carries two colon-level separators (rule 2), `Progress in Perovskite Photovoltaics` mimics the real Wiley journal *Progress in Photovoltaics* and hurts both discoverability and citation, `Enhanced` is an unmeasured comparative (rule 5), and `Durability` is not an axis name — stage 06 calls it `stability` (rule 6). The compliant form of the same idea is `Perovskite photovoltaics, July 2026: halide passivation lifts certified efficiency, stability reporting still lags`.
- Abstract: 250 words or fewer; must contain the three-tier sentence S1 and at least 5 audit numerals, each with a stats marker (R19). **It must also carry a verdict, not only counts (Q45):** how much was published, the single most notable mechanism result, what fraction of claims are not auditable, and what should change. That is roughly 120 words and it is the part a reader forwards to a colleague.
- Back matter order: Acknowledgements · Competing interests · Data availability (repo URL, public CSV, SI files, and a statement that abstracts and full texts are not redistributed) · **AI Usage Declaration** (template §8.5) · a bare `References` heading last.

### 8.2 Section map (Q45: 6-7 content pages, 5,500-word prose ceiling)

Section numbers below are the **canonical** ones; every `§n` reference elsewhere in this plan points at this table.

| § | Title | Ceiling (words) | Content floor (G2) | Brief by | Written by |
| --- | --- | --- | --- | --- | --- |
| 1 | Introduction and the month's question | 400 | \- | \- | qwen |
| 2 | Corpus, selection, and audit method | 350 (250 once the protocol paper exists) | S1 and S6 present; gate query cited; three tier counts | template | qwen |
| 3 | Composition, phases, and defects | 900 | ≥8 card claims; ≥12 depth papers across its two axes | opus | qwen |
| 4 | Interfaces and device architecture | 900 | same | opus | qwen |
| 5 | Stability, scale-up, and deployment | 900 | same | opus | qwen |
| 6 | Reporting audit | 1,000 | ≥6 corpus metrics each with P/R; ≥5 depth metrics | opus | qwen |
| 7 | Gaps and suggested future research | 350 | ≥3 gaps each tied to a stats key or card claim | opus | qwen |
| 8 | Limitations | 300 | S2, S3, S4 present; S5 if `jaccard_median<0.70` | opus | qwen |

Allocated 5,100 words with 400 of slack under the 5,500 ceiling (G2). That is 4.64 pages of prose plus 1.82 pages of floats, so **6.46 content pages** — inside the 6-7 target. There are still no minimum word counts anywhere: a thin month produces a shorter paper, not a padded one.

**Why three mechanism sections and not six or one.** The six axes are the labelling scheme (§5.6) and they stay exactly as they are in the data, the CSV, T1, and F1. But six 900-word sections would need 5,400 words for mechanisms alone, leaving nothing for the audit. One collapsed section, which the 2,400-word draft of this plan proposed, could not carry 200 audited papers at any useful depth. Three sections at 900 words pair the axes that share physics and share literature:

| § | Axes it covers | Why they pair |
| --- | --- | --- |
| 3 | composition + defects | the same papers: A-site engineering and passivation are usually one experiment |
| 4 | interfaces + architecture | contact stacks and tandem design are one design conversation |
| 5 | stability + scale_up | both are about what survives outside a glovebox |

An axis with fewer than 12 depth papers is written at whatever length its cards support and says so in one sentence; G2 accepts that when `axes.<axis>.n_depth < 12` holds in `stats.json`.

**The trade, stated openly.** The audit is now 1,000 of 5,100 words, so **20%** rather than the 29% it held at 2,400 words. It is still the single largest section, and it is the only section with a measured methodology behind it, so it keeps first claim on the slack. If a month is thin on mechanism results, the slack goes to the audit rather than to padding §§3-5.

**Audited-N versus cited-N (Q45).** The depth tier stays at 200 because the audit percentages need it: at n=200 a 50% metric carries a 95% confidence interval of ±6.9 pp; at n=120 that widens to ±8.9 pp and at n=60 to ±12.7 pp, where the audit stops being quantitative. The body cites at most **180** distinct works, which at 5,100 words is about 28 words per citation — comfortable prose. At the 2,400-word draft the same cap would have been 18 words per citation, which is a citation list wearing sentences. The remaining audited papers are indexed in SI table S3 and in the public CSV. G1-cite is unchanged: every `[@key]` must still resolve to a depth-selected card, and only the *count* of in-body markers is capped, by G2.

### 8.3 Mandatory sentences (templates; the assembler fills `{…}`; G2 matches with the numbers wild-carded)

- **S1 (§2 and abstract):** "Of {corpus.n} works published in {Month Year} that met the scope gate, {selection.n_eligible} had retrievable full text and {selection.n_depth} of those met the depth-review threshold."
- **S2 (§8):** "Venue-impact-prioritised selection systematically under-samples preprints, regional journals, and non-English venues; combined with machine translation of non-English abstracts, the depth subset is biased toward well-indexed English-language publishing."
- **S3 (§8):** "Because indexing lags publication, this digest describes the indexed record of {Month Year} as of {venues.snapshot_date}, not the month itself."
- **S4 (§8):** "Full-text eligibility further biases the depth subset toward open-access and preprint publishing."
- **S5 (§8, only when** `jaccard_median<0.70`**):** "Selection is weight-sensitive: median Jaccard overlap {selection.jaccard_median} across perturbed weightings; {selection.core_n} papers are selected under at least 95% of weightings."
- **S6 (§2, new under Q45):** "All {selection.n_depth} depth-tier papers were audited; {selection.n_cited} are cited individually below and the remainder are indexed in Supplementary Table S3."

All six are the paper's honesty budget. They are not optional and G2 fails without them. S2-S5 live in §8 Limitations and S6 in §2, per the §8.2 map.



### 8.4 Figures and tables

7-9 main figures from §5.11. Tables: T1 corpus and selection counts by source and tier; T2 depth papers by axis with champion PCE, area, certification, and protocol (from cards); T3 audit summary for both tiers with precision and recall; T4 selection sensitivity (core and marginal counts, Jaccard). SI: S1 funnel, S2 sensitivity, **S3 the index of audited-but-not-cited papers (Q45), S4 the stage x model token matrix (Q48)**, `subset_scores.csv`, `claim_cards.jsonl`, `validation_metrics.json`, `g1b_fidelity.jsonl`, and SI-A the full method (until the Q36 protocol paper exists).

### 8.5 AI Usage Declaration (template, updated for Q40)

"This manuscript was produced by an automated pipeline. Literature harvesting, selection, statistics, and figures are deterministic scripts (repository and commit hash in Data availability). Structured extraction from full texts used {extractor.model}; extraction disagreements and citation entailment checks used {adjudicator.model}. The title uses a fixed frame with one data-derived slot, drafted by {generator.model} from statistics keys and recorded in the run log. All manuscript prose was drafted by {generator.model} from structured briefs; the briefs, which contain no prose, were produced by {reviewer_science.model}. Two independent automated reviews ({reviewer_structure.model}, {reviewer_science.model}) preceded assembly, and any section rewritten under escalation by {reviewer_science.model} is listed in the run log shipped as supplementary information. Of the {selection.n_depth} papers whose full texts were audited, {selection.n_cited} are cited individually here and the remainder are indexed in the supplementary corpus table. Every quantitative statement resolves to a machine-generated statistics file shipped as supplementary information. The human author reviewed the selection, spot-checked extraction against source PDFs, and approved release." Followed by the mandated project sentence from `config/author_manifest.yaml`.

---

## 9. Prose hygiene (G4; `avoid-ai-writing` as a gate; body text only)

Scope: `manuscript.md`, minus the References section, minus BibTeX, minus anything inside a `\cite*` or `[@key]` span, minus figure and table captions that quote paper titles. A banned word inside a quoted title is the title's problem, not ours.

| Rule | Check | Threshold |
| --- | --- | --- |
| Em-dash | count of U+2014 | 0 |
| En-dash | U+2013 allowed only (a) between digits/units (`400–1200 nm`), (b) joining single-letter tokens (`p–i–n`), (c) joining two capitalised tokens (`Shockley–Queisser`), (d) in `config/endash_allow.txt` (seed: p–i–n, n–i–p, Shockley–Queisser, Li–TFSI, FA–Cs, Cs–FA, MA–FA, Sn–Pb, Pb–Sn, perovskite–silicon, Si–perovskite, C60–BCP, Voc–Jsc) | 0 other |
| Banned vocabulary | case-insensitive, whole words: delve, harness(ed), pivotal, seamless(ly), leverage(d), moreover, furthermore, it is worth noting, noteworthy, in conclusion, comprehensive, robust(ly), cutting-edge, state-of-the-art, tapestry, unlock, showcase, underscore(s), realm, ever-evolving, a myriad of, in the realm of | 0 (`state-of-the-art` allowed on a line that carries a citation marker) |
| Openers | \`In this (paper | study |
| Rhetorical questions | `?` outside citations in §6 and §8 | 0 |
| Hedging adverbs | \`significantly | dramatically |
| Sentence rhythm | no 3 consecutive sentences with the same first two tokens; sentence-length stdev ≥ 6 words per paragraph | warn (§§1-5), fail (§§6-8) |
| Numbers | every numeral outside citations carries a unit or `%` and a stats marker or card field (delegated to G3) | fail |
| Passive openers | paragraphs starting with a passive construction | warn |

G4 runs after stage 15 and after every stage 17 rewrite. `g4_prose.txt` holds the raw grep output; stage 19 pastes it into the commit message and the Telegram summary. Any additions to the allowlist are named in the summary, so the allowlist cannot quietly grow to cover bad writing.

---

## 10. Gates (`16_verify`; thresholds in `config/gates.yaml`)

| Gate | Check | On failure |
| --- | --- | --- |
| G1-cite | every `[@key]` resolves to a **depth-selected card**; the DOI is verified live once per month (`/works/doi:<doi>` via `oa()`, cached in ledger `doi_verified_at`); title containment ≥0.9 | fail |
| G1b-fidelity | for every citation marker in **§§3-5 and §7** (the sections that make paper-specific claims): hand the host sentence plus that card's claims and anchors to the entailment model and get \`supported | partial |
| G2-struct | section order per §8.2; per-section **ceilings**; content floors; S1-S5 present per their rules; the three tier counts equal the CSV; "PRISMA" absent from title, abstract, headers, and captions; ≥5 audit numerals in the abstract; abstract ≤250 words; **total prose ≤5,500 words (paper mode) or ≤3,000 (bulletin mode), read from `gates.yaml`**; **in-body distinct `[@key]` count ≤180 (Q45)**; a bare `References` last; **title (Q50): exactly one colon and no other subtitle punctuation, ≤16 words, `{Month Year}` matching the run month, no publication count, §9 banned vocabulary with no exceptions, every comparative or superlative backed by `title.slot_basis_key` (efficiency claims additionally require a certified or stabilised anchor from a non-preprint depth paper), `slot_axis` one of the six §5.6 names or `audit`, slot phrasing drawn from `title_terms.yaml`**; metrics with `printable=false` use lower-bound wording | fail |
| G3-corpus | every number resolves to a `stats.json` key (through its `{{stats:}}` marker) or to a card field within 1%; numbers from MT papers resolve against the original-language tokens; stage 15 added no numbers and no markers | fail |
| G3b-small | magnitude grep for unit-scaled small values (`mA cm−2`, `cm2`, `h`, `nm`) against the card ranges | fail |
| G4-hygiene | §9 | fail (hard rules) / warn (soft rules) |
| G5-build | every §11 deliverable exists and is non-empty; `%PDF-` header present; **two page checks from `gates.yaml` (Q45): `content_page_band` `[6,7]` and `total_page_band` `[8,10]`.** Content pages are measured, not assumed: pymupdf locates the page carrying the bare `References` heading, so `pages_to_refs` = that page index. Havid's definition of content excludes the title block, so `content_pages = pages_to_refs - title_block_fraction`, where the title block is measured as the fraction of page 1 above the first body paragraph (typically 0.40). Report all three numbers in `gate_report.json` — `pages_to_refs`, `title_block_fraction`, `content_pages` — because a band failure needs to say which of them moved. Both bands must hold. (v4 asserted `pages > 5`; that check is fine at this length but it was fine by luck, so it is replaced by explicit bands in both directions.); no `Citation … undefined`; author block inside the margins (pymupdf x1 ≤ pageW−72); DOCX has `word/media/` entries, zero `[?]`, and a non-empty reference list; `tar -tzf` succeeds and the tarball holds only relative paths; **the** `.tex` **compiles on its own from a clean directory**; the PDF and DOCX reference lists are identical | fail |
| G6-novelty | no sentence claims results produced by this study (regex over "we measured/fabricated/synthesised/simulated"); §10 speculation is allowed | fail |
| G7-translate | sentences citing `Translated=mt` works carry only title, venue, and date; MT provenance disclosed in §2; no MT work is depth-selected | fail |
| G8-subset | `N_depth ∈ [100,300]` or `small_pool` disclosed; each axis ≥12 or its shortfall disclosed; venue ≤8%; institution ≤10%; the S1 numbers equal the CSV counts; every depth paper has a card with ≥1 valid claim; `subset_scores.csv` and the sensitivity file are shipped | fail |
| G9-cost | `cost.json` complete; opus calls ≤ cap; access path recorded; `writer_failures` and `escalation_rewrites` present | warn |
| **G10-release** | the public CSV has no abstract and no MT columns, and `Summary` is ≤60 words; every card anchor is ≤25 words; no `.pdf` or `.txt` full texts under `manuscript/` or in the tarball; `data/fulltext/` and `data/private/` are absent from the commit; `.env` is absent | fail |

G10 is the gate that keeps a public repo legal. It is the last one to ever be relaxed.

---

## 11. Deliverables per month (all committed unless git-ignored)

```
manuscript/<YYYY-MM>/
  manuscript.md  manuscript.tex  references.bib  manuscript.bbl  manuscript.pdf  manuscript.docx
  fig/*.pdf  fig/*.png  chemrxiv_<YYYY-MM>.tar.gz  metadata.txt
  subset_scores.csv  claim_cards.jsonl  validation_metrics.json  g1b_fidelity.jsonl  g4_prose.txt
  gate_report.json  cost.json  tokens.jsonl  token_matrix.md  review/round*_{gemini,opus}.json
csv/perovskite_<YYYY-MM>.csv
stats_history/<YYYY-MM>.json
```

Style stack (v3 §I.3, unchanged): `research-paper-writing`, `manuscript-production`, `manuscript-review`, `avoid-ai-writing`, `grounded-citations`; `\parbox{0.92\textwidth}` author block; BibTeX hygiene (`&`→`\&`, entity collapse, `html.unescape`) before compiling; numbered sections.

---

## 12. Pilot go/no-go (July 2026; scored by Havid at T-40, then the product gate at T-40b)

| \# | Criterion | Threshold | Evidence |
| --- | --- | --- | --- |
| 1 | Grounding | G1b round 1: 0 `not`, ≤5% `partial` | `g1b_fidelity.jsonl` |
| 2 | Selection sanity | ≥24 of 30 random depth picks judged reasonable to close-read | `tools/sample_picks.py` sheet |
| 3 | Prose quality | mean ≥3.5/5 over **20 random §§3-5 paragraphs** (a 5,100-word paper supports the full 20-paragraph sample again) on insight, grounding, readability | blind sheet from `tools/sample_paragraphs.py` |
| 4 | §6 credibility | every printed corpus % has P≥0.85; ≥8/10 spot-checked depth flags agree with the PDF | `validation_metrics.json`, cards |
| 5 | Hygiene | G4 0 hard flags, ≤5 allowlist additions | `g4_prose.txt` |
| 6 | Cost | opus calls ≤45; wall clock ≤4 h | `cost.json` |

Criteria 3 and 4 carry more weight in v5 than they did in v4, because a flash model now writes §6 and §7. If either fails, the first lever is raising the reviewer effort — Havid's decision only (Appendix B).

**Go** (6/6): T-40b product gate → T-38 August → T-42 protocol paper → T-44 Sep live month → T-46 turn the cron on. **Retry** (2 or fewer failures): fix, re-run July once. **Fallback** (fails twice): the product becomes the *Reporting audit bulletin* = §1, §2, §6, §7, §8 with §§3-5 reduced to one table (about 3,000 words; `content_page_band` [4,5], `total_page_band` [6,8]) plus the CSV, the cards, and `stats_history`, switched on with `config/product.yaml: mode=bulletin`. The decision is recorded in `QUESTIONS.md`.

---

## 13. Risks with active mitigations (R1-R20 carried from v3; R21-R28 from v4; R29-R30 new)

| \# | Risk | Mitigation in this plan |
| --- | --- | --- |
| R13 | flash-model writing quality, now across the whole paper | Q40 single writer with structured briefs; ≥2 rounds for §9/§10; escalation rewrite; revision counter in `cost.json`; pilot criteria 3 and 4 |
| R14 | Claude quota | cap 45, pause-and-notify; Q38 path recorded; the science review is never substituted; opus load reduced by Q40 |
| R16/R17 | venue percentile drift / repository contamination | cumulative table; `type=journal` guard; null instead of 0 |
| R18 | §9 overclaiming | measured precision/recall; the print rule; the depth tier comes from full text |
| R20 | key leak | the `oa()`/`plain()` split; T-00 rotation blocks everything; Q43 |
| R21 | invented card values | anchor and number-in-anchor guards; two passes; adjudication; G1b |
| R22 | small depth-eligible pool | N shrinks; disclosed; preprint reservation |
| R23 | weight sensitivity | measured; S5 discloses it |
| R24 | over-fitting the validation set | frozen set; append-only v2; monthly precision/recall published |
| R25 | preprint and article counted twice | §5.5 linking; `superseded_preprint` |
| R26 | preprint-server policy change | AI declaration; audit framing; Zenodo and GitHub release fallback; no automated submission exists; the platform is one config file (`config/preprint.yaml`) so a target change is not a repo-wide edit |
| R27 | copyright exposure | G10; anchors ≤25 words; private directories git-ignored |
| R28 | human bottleneck | batched confirmations; the 48 h pause rule; label sheet generated early |
| **R29** | **one writer, no fallback: an opencode outage stalls the whole run** | `.done` resume; 3 retries with backoff (Q41); exit code 75 also means "writer unavailable"; `writer_failures` always in the digest; G9 reports it |
| **R30** | **the key pasted into chat on 2026-09-07** | Q43; T-00 rotates it; `secret_scan.py` also scans `docs/`, `QUESTIONS.md`, and commit messages; `net.redact()` masks key material in probe logs mechanically |
| **R31** | **subscription rate limit stalls a run** | Q38: rate-limited is exit 75 pause-and-resume, never a failure; `quota_windows[]` records which 5-hour window each call used, so a run that does not fit the allowance is visible in the first month rather than the third |
| **R32** | **a page ceiling squeezes out the honesty sentences** | S1-S6 are G2-mandatory and counted inside the 5,500 ceiling, not exempted from it; if the paper cannot fit its own caveats it fails the gate rather than dropping them |
| **R34** | **secret or PII leaking into a probe note** | `net.redact()` masks `api_key`, `email`, `mailto`, `token` in anything bound for a log, note or exception. Unpaywall carries the contact address in the query string and §0 rule 3 tells probes to record the exact command, so redaction is mechanical rather than remembered |
| **R35** | **a hand-authored section bypassing the evidence chain** | **Happened 2026-09-07 and is the worst error of the build.** The first v2 abstract was written as a Python f-string using positional lookups into filtered, sorted lists. The extractor had labelled a perovskite/silicon tandem as `p-i-n`, so `[v for v,c in cert if arch in ("p-i-n","n-i-p")][0]` returned 33.1% and the sentence attached it to a paper whose certified value is 27.12%; a second positional fallback reported 28.84% for a paper measuring 29.57%; and `n_cited` read the *cap* (180) instead of citations actually resolved (110). Three fabricated numbers in the most-read part of the paper, in the one section that bypassed the card chain because it was authored in code. Mitigation: every abstract highlight resolves ONE card by explicit DOI fragment and fails closed if the fragment matches ≠1 card or the paper is not cited in the body; positional indexing into filtered lists is banned in the abstract builder; and **G3-abstract** rejects any unverified numeral. **Rule: no prose that reaches a reader may be authored outside the evidence chain, including by me.** |
| **R36** | **model self-commentary leaking into shipped prose** | Two leaks reached the v1 PDF: `"1030 words, over the 900 limit. Condensing."` inside §5 and `"Saved to runs/.../sec8.md (257 words...)"` in §8. The guard knew `"written to runs/"` but not `"Saved to"`, and nothing matched a bare word tally. `SELF_REF` now matches the *shape* of a status line (verb plus path, word counts, limit or gate talk, our own rule names) and strips per line so one leaked line does not discard a good section. G4 reports `self_report_leak` on every build |
| **R37** | **the silent-zero class** | Six instances this build, each producing plausible output instead of an error: the run directory relocating mid-run when a config was added (0 venues from a 655-work corpus); an ignored subprocess return code (181 cards silently becoming zero); a `.done` marker trusted by existence rather than payload; guard 3 truncating away the number guard 2 had just verified; two orphaned writer processes rewriting drafts *after* the build read them; and `_v()` reading `performance` for `t80_h`, which lives in `stability`, so a figure panel rendered empty while four real values sat in the cards. **Operating rule: a zero is a bug until proven otherwise, and a stage's own counters are never the verification.** |
| **R38** | **an edit reporting success while changing nothing** | Exact-string patching failed repeatedly on stale anchors, and because the assertion fired BEFORE the file write, a "successful" run left the file untouched. This happened five times this build, once leaving a gate (`G2c`) described in a report but absent from the code. Mitigation: after any patch, grep for the NEW text to prove it landed; after two failures on one anchor, switch to a fuzzy-matching patch tool instead of retrying |
| **R33** | **"private for now" quietly becomes permanent leak exposure** | Q47 keeps G10 and Q43 in force while private; T-47 scans the whole history and publishes from a clean snapshot; the burned key is rotated there |

---

# PART II. TASK LIST FOR HERMES

Format: `T-xx | title | depends on | flags`, then **Do**, **Out**, **Accept**.

Flags: `⛔ HUMAN` (ends by messaging Havid, then waits), `[PROBE]` (a live read-only call, result written to `docs/PROBES_v5.md`), `⚠ LIVE` (writes to databases or spends model budget), `LLM` (uses a model). Anything unflagged is offline Python against fixtures.

Task numbers are unchanged from v4 so that every dependency line still resolves. The one new probe task is numbered **T-12b** for the same reason.

## Phase 0: Security and scaffolding

**T-00 | Confirm private visibility and seed `.env` | - | ⛔ HUMAN**Do: **Changed under Q47 — this is no longer a key rotation.** The repo stays private for now, so the burned OpenAlex key does not need rotating before work starts. Confirm the remote's visibility really is private (`gh repo view --json visibility`, or that there is no remote at all yet), confirm `.env` is git-ignored, and have Havid put `OPENALEX_API_KEY`, `UNPAYWALL_EMAIL`, `TELEGRAM_BOT_TOKEN`, and `TELEGRAM_CHAT_ID` into `.env` himself. **No** `ANTHROPIC_API_KEY` — Q38 is resolved as subscription and there is no API key in this project. **Q43 still holds in full:** a private repo is not a private transcript, so keys are still never pasted into chat, a prompt, a log, or a document. The key exposed on 2026-09-07 is rotated at T-47, before anything becomes public, and the plan says so there rather than pretending it was handled here. Out: a line in `docs/PROGRESS_v5.md`; no key material anywhere in the repo. Accept: visibility confirmed private; `scripts/tools/secret_scan.py` prints `LEAKED: NONE` across the working tree, `docs/`, `QUESTIONS.md`, and `git log --format=%B`; `.env` has the four keys and `python -c "from scripts.common import env; env.require_all()"` passes. **Blocks every other task.**

**T-01 | Repo scaffold, legacy migration, immutable banners | T-00**Do: Build the §2 layout. Carry out the §2.1 migration map, one commit per row: move `common/` → `scripts/common/` (this one is required before T-02 can pass); move the retired v2-era files into `archive/legacy-v2/`. Add SUPERSEDED banners to v1-v4 (the banner line only, nothing else touched) — note that v4 is currently **untracked**, so commit it with its banner rather than leaving a hole in the plan history exactly where the big revision happened. Create `docs/PROBES_v5.md` and `docs/PROGRESS_v5.md`, and the `.gitignore` from §2. Branch `v4-build`. Out: commit `T-01` (several commits, one per migration row). Accept: `tree` matches §2 (empty directories carry `.gitkeep`); `git diff` on v1-v3 shows only the banner line; v4 is tracked and carries its banner; `archive/legacy-v2/` holds the old CSV, both old run directories, the old ledger, and `validate_csv.py`; `scripts/common/` exists and root `common/` does not.

**T-02 |** `scripts/common/net.py` **with a structural key split | T-01**Do: `oa(path, params)` asserts `urlparse(url).netloc == "api.openalex.org"` before it appends `api_key`; `plain(url, params)` cannot reach the key at all (separate module scope, no import of the key loader). Rate limiting (10 requests/s for OpenAlex, 1/s for everything else), retries with backoff, `x-deny-reason` header logging, 20 s timeout. Add `redact()` (R30) so anything logged has key material masked by the code rather than by hand. Out: `scripts/common/net.py`, `tests/test_net.py` (mocked; asserts a non-OpenAlex host raises before any request is built; asserts `plain` has no key in its closure). Accept: tests pass. The security check, **corrected from v4** (v4 grepped `scripts/` while the key loader sat in root `common/`, so it passed while auditing nothing): `grep -rn "api_key\|API_KEY" --include=*.py . | grep -v "scripts/common/net.py"` returns **zero lines**, and the same grep without the filter returns only the loader's own lines inside `scripts/common/net.py`.

**T-03 | the rest of** `scripts/common/` **| T-02**Do: `env.py` (loads `.env`, never logs a value), `ledger.py` (the §3.1 schema, upsert by `work_key`, migrations — and per Q42 a fresh database rather than a pretend migration of the archived one), `dates.py` (month bounds, MYT), `cleaners.py` (title_norm, DOI normalisation, the v2 §4.2 institution rules), `bibtex.py` (escaping, entity collapse), `stats_keys.py` (the §3.5 list plus a validator), `llm.py` (the wrapper for opencode, claude, and agy: prompt SHA, token count, per-model counters, the cap check → exit 75, retry-versus-fallback logic per Q41, and `writer_failures` accounting). Keep the carried-over `csvio.py`, `doi.py`, `titles.py`. Out: the modules, plus `tests/` with fixtures. Accept: `pytest` is green with the network disabled (`pytest --disable-socket` or equivalent); `stats_keys.validate("audit.corpus.certified.pct")` is true and `validate("Audit.Corpus")` is false; a test proves `llm.py` retries the writer 3 times and then raises rather than switching model.

**T-04 | Config files | T-01**Do: Write `config/models.yaml` (§7.1), `axes.yaml` (§5.6, the full keyword tables — at least 15 weighted keywords per axis), `venue_whitelist.yaml` (the v3 §D.2 list with an ISSN-L for each; ISSNs are public so no probe is needed, and any unknown one is left blank and filled from stage 04 later), `exclude.yaml` (copied word-for-word from the daily script), `hygiene.yaml` + `endash_allow.txt` (§9), `cards_schema.json` (§5.9, JSON Schema draft-07, `additionalProperties: false`), `gates.yaml` (every §10 threshold as a number, plus `cron_day`, `content_page_band`, `total_page_band`, `max_body_citations`), `mt.yaml` (§5.3: provider, model, and prompt file — new in v5 because v4 pointed at frozen v2), **`title_terms.yaml`** (Q50/§8.1: `frame`, `max_title_words: 16`, `slot_words: [6,14]`, `neutral_slot`, `banned_in_title`, and `axis_phrases` for the six axes plus `audit`), and `product.yaml` (`mode: review`, the T-40 fallback switch — new in v5 because v4 referenced it without ever creating it). Delete `config/prose_rules.yaml` in the same commit that adds `hygiene.yaml`. Out: the config files, plus `tests/test_config.py` which loads each and checks the required keys. Accept: tests pass; `cards_schema.json` validates the example card in §5.9 and rejects one with an extra field; **`axes.yaml` has been renamed per Q51 so its six keys are exactly `composition, defects, interfaces, architecture, stability, scale_up`, with a test asserting it and a test asserting `title_terms.yaml: axis_phrases` covers those six plus `audit`**; a diff-check proves every rule and threshold from the deleted `prose_rules.yaml` landed in `hygiene.yaml`; `models.yaml` parses and `generator.fallback` is `None`, not the boolean `False`.

**T-05 | Prompt files v1 | T-04**Do: Write every file in `prompts/` (§2). Each prompt states its role, the inputs it will receive (with exact JSON keys), the output format (a JSON schema, or markdown with markers), the hard rules (no facts outside the cards; every number carries a marker; respect the ceiling), and one worked example. `entailment_v1.md` returns exactly `{"verdict": "supported|partial|not", "reason": "…"}`. **New in v5:** `brief_v1.md`, `critical_brief_v1.md`, and `future_brief_v1.md` must return structured JSON and are explicitly forbidden from returning prose — they replace v4's `outline_v1.md`, `critical_v1.md`, and `future_v1.md`. `voice_v1.md` is now addressed to qwen. Add `mt_v1.md`. **Also `title_v1.md`** (Q50): inputs are the six axis deltas and centrality means, the printable `audit.*` metrics, and the certified champion if one exists; output is JSON `{frame, slot, slot_axis, slot_basis_key, slot_basis_key_2, basis_values, n_words}`; it must state that a comparative without a basis key is a failure and not a style preference. Out: 14 prompt files; `prompts/README.md` mapping prompt → stage → model → which CLI. Accept: each prompt is under 1,500 words; a SHA-256 list is committed in `prompts/SHA256SUMS`; the three brief prompts contain an explicit "return JSON only, never prose" instruction.

## Phase 1: Probes (read-only; keys only ever through `net.oa()`)

**T-06 | P-01 OpenAlex select fields and count band | T-02 | \[PROBE\**]Do: Run the §4.1 query for Aug 2026 with `per-page=1` and the full `select` list, then one page with `per-page=100`. Record `meta.count`, which select fields were accepted and which rejected, and how often `best_oa_location.pdf_url`, `open_access.oa_url`, `related_works`, and `is_retracted` are present and non-null across the 100 sampled works. Out: `docs/PROBES_v5.md` §P-01. Accept: the count is inside \[250, 1200\]; the final `select` list is fixed in `01_harvest.py`.

**T-07 | P-02 secondary sources | T-02 | \[PROBE\**]Do: For Aug 2026, run the S2 bulk search (note whether a key is required and what the rate limit is), the arXiv API with a month filter, and Crossref with date filters and `mailto`. Record the counts, 5 sample records each, and the response shapes. Out: `docs/PROBES_v5.md` §P-02. Accept: a working query string is recorded for all three; the estimated union size is noted.

**T-08 | P-03 preprint→article linkage | T-06 | \[PROBE\**]Do: Across the 100 sampled works, count how many have `related_works` pointing at a work of a different `type`. Separately, test `rapidfuzz.token_set_ratio ≥ 90` plus a first-author match on 20 known preprint/article pairs (pick arXiv IDs that also have a DOI). Out: `docs/PROBES_v5.md` §P-03, including the precision of the title rule on those 20 pairs. Accept: the decision is recorded — use `related_works` if its coverage is 30% or more, otherwise the title rule alone.

**T-09 | P-04 full-text availability | T-06 | \[PROBE\**]Do: On the 100 sampled Aug works, try (a) `best_oa_location.pdf_url`, (b) `oa_url`, (c) Unpaywall with `UNPAYWALL_EMAIL`, (d) preprint PDFs. Download **only the headers and the first 64 KB** to confirm the `%PDF-` magic bytes — do not pull whole PDFs during a probe. Record the success rate at each step and cumulatively. Out: `docs/PROBES_v5.md` §P-04. Accept: the cumulative eligible share is recorded. If it is under 30%, add an item to `QUESTIONS.md`: the depth N will shrink, so decide whether to accept that or add another source.

**T-10 | P-05 CLI re-verification | T-01 | \[PROBE\**]Do: `claude --version`; `claude -p "reply OK" --model opus --effort medium --output-format json --max-turns 1`; `agy models`; `agy -p "reply OK" --model gemini-3.8-flash-high --print-timeout 60s`. Record exactly which flags work. **Note the change from v4:** `--effort medium`, not `xhigh`. The opencode writer is covered by T-12b, not here. Out: `docs/PROBES_v5.md` §P-05. Accept: both claude and agy return a response; the §7.2 flags are corrected if anything differs.

**T-11 | Record the opus access path and its real limits (Q38) | T-10**Do: **No longer a human wait — Q38 is resolved.** Havid has a Claude Code subscription login and there is no API key, so just record it: set `models.yaml.opus_path: subscription`, confirm no `ANTHROPIC_API_KEY` is read anywhere (`grep -rn ANTHROPIC scripts/` is empty), and note from the P-05 session what the account's actual rate-limit behaviour looks like — the message text and whether a retry-after window is given — because Q38's exit-75 pause depends on recognising it. Out: `docs/PROBES_v5.md` §P-06 (one paragraph, folded into P-05); `models.yaml` updated. Accept: `opus_path: subscription` committed; `est_cost_usd.opus` is `null` rather than `0.0` in the `cost.json` schema; `subscription_quota_used` and `quota_windows[]` present; no ANTHROPIC key referenced anywhere in the tree.

**T-12 | P-07 indexing-lag series (Q39) | T-06 | \[PROBE\**]Do: Re-run the Aug 2026 count on **2026-09-07, 09-14, 09-21, and 09-28** (a `per-page=1` call, key through `oa()`). v4 planned 09-06, which has already passed, so the series starts today and the fourth point is the 28th. After the fourth point, `DAY` is the first weekly date whose count is at least 0.95 × the 28-Sep count, expressed as a day of the month. What this is actually measuring, in plain terms: papers published in August keep being added to OpenAlex for weeks afterwards. This finds out when the number stops moving, so the monthly cron does not run before the month has finished arriving. Out: `docs/PROBES_v5.md` §P-07 table; `config/gates.yaml: cron_day`. Accept: four counts recorded; `DAY` set (placeholder 12 until then). This runs in the background and does not block Phases 2-9.

**T-12b | P-08 opencode as a scripted writer (new in v5) | T-01 | \[PROBE\**]Do: Verify non-interactive opencode for `opencode-go/qwen3.8-flash`. Find and record: the exact flag that pins the model; the exact flag that sets thinking to high; how a system prompt from a `prompts/*.md` file is supplied; whether the response comes back on stdout or is written to a file; whether the CLI reports token usage (`cost.json.tokens` needs it); and what it does on a rate-limit or an error, since Q41's retry logic depends on being able to tell a transient failure from a hard one. Also test whether `thinking: high` is compatible with schema-constrained JSON output, which decides `extractor.thinking` in `models.yaml`. Why this task exists: v4's P-05 probed claude, agy, and the Hermes provider, but never opencode as a scripted writer. Under Q40 the writer has no fallback, so an unverified command line is now a single point of failure for the whole pipeline. Out: `docs/PROBES_v5.md` §P-08; §7.2 filled in with real flags; `models.yaml.extractor.thinking` resolved with a comment citing P-08. Accept: a scripted opencode call returns text on demand; the model-pin and thinking flags are recorded; token reporting is confirmed present or explicitly absent (if absent, `cost.json` records estimated tokens and says they are estimates). **Blocks T-24 and T-30.**

## Phase 2: Harvest to corpus (July, the pilot month)

**T-13 |** `01_harvest.py` **| T-03, T-06, T-07 | ⚠ LIVE**Do: Implement §5.1, including the count-band abort, cursor pagination, the secondary sources, and private abstract storage. Keep the exclusion rules and regression tests that the existing v2-era harvest script already earned (the Wiley cover-caption and issue-suffix cases) — those were real bugs found in production, so carry them across rather than rediscovering them. Unit tests run against `fixtures/openalex_aug2026_sample.json`. Then run it for **Jul 2026 first — July is the pilot month (Q49)** — and for Aug 2026 only after Havid has signed off on the July PDF at T-40b. Out: `runs/2026-07_*/01_*`, `01_meta.json`. Accept: the Jul OpenAlex count is inside the [250, 1200] band and recorded next to the Aug P-01 count so the band has two data points; per-source counts logged; no abstract text anywhere outside `private/`; the carried-over exclusion regression tests still pass.

**T-14 |** `02_normalize.py` **+** `03_translate.py` **| T-13**Do: §5.2 and §5.3. Tests for DOI and title normalisation and for institution cleanup (10 hand-written cases, including "Key Laboratory of … Ministry of Education"). Out: `02_records.jsonl` and `private/03_abstracts_mt.jsonl` for **Jul**. Accept: `lang` is populated for 100% of records; the `Translated=mt` count matches the `lang != en` count; original-language numeric tokens are preserved in the MT records.

**T-15 |** `04_venues.py` **| T-14 | ⚠ LIVE**Do: §5.4. Populate `venues.sqlite3` for the **Jul** venues, compute the cumulative percentiles, and join SJR if the CSV is present (it is optional, and its absence must never fail the run). Out: `data/venues.sqlite3`; `04_venue_percentiles.json` for **Jul**. Accept: Zenodo-type rows have `type != journal` and a null percentile; Advanced Materials scores above 0.90; `n_reference_venues` is recorded; when Aug is added later it changes Jul percentiles only through the cumulative set, and that delta is documented.

**T-16 |** `05_dedupe.py` **| T-15, T-08**Do: §5.5, including the ledger upsert, the cross-source merge, the canonical month, the preprint→article rule chosen by P-03, and the retraction flag. Note the renumbering: this replaces the existing `scripts/03_dedupe.py`, and per §2.1 the rename lands in its own commit. Carry across its in-batch dedupe and its short-circuit behaviour (never rewrite an existing CSV partially). Out: `05_corpus.jsonl` for **Jul**; ledger rows. Accept: no duplicate `work_key` within a month; every row has `canonical_month == '2026-07'`; 5 hand-checked merges are correct; the Jul corpus count is reported (600-750 expected).

**T-17 |** `06_mechanism.py` **(unvalidated mode) | T-16, T-04 | LLM (qwen, adjudication only**)Do: §5.6 keyword scoring, adjudication for the multi-axis cases, the lens, `offtopic_risk`, the §4.4 post-filter order, `postfilter_dropped.csv`, and the off-topic audit sample (agy). The validation branch returns `unvalidated` until T-19. Out: `06_labels.jsonl` for **Jul**; `postfilter_dropped.csv`; `06_offtopic_audit.json`. Accept: the axis distribution is printed; the adjudication rate is 20% of the corpus or lower; every adjudicated result cites keywords that really are in the text; Hermes reviews the dropped list for obvious PV false drops and reports the count.

**T-18 | Corpus CSV eyeball | T-17 | ⛔ HUMAN**Do: Build the public CSV (§3.2, without the depth columns yet) for **Jul**, and the label sheet (§6) with `tools/make_label_sheet.py`. Send both to Havid with three questions: does the gate yield look plausible? Is the Summary column readable? Are `Lang` and `Translated` right on 5 spot checks? Out: `csv/perovskite_2026-07.csv` (draft), `data/validation/labels_v1_TO_FILL.csv`. Accept: Havid answers all three and confirms he will fill the sheet. This is the earliest point the 3-4 hour labelling job can start, and it is the critical path, so do not sit on it.

**T-19 | Validation set frozen | T-18 | ⛔ HUMAN**Do: Wait for `labels_v1.csv`. Validate the format, freeze it (`chmod a-w`, plus `SHA256SUMS`), and re-run stage 06 in validated mode for **Jul**. Out: `data/validation/labels_v1.csv`, `06_validation_metrics.json` for **Jul**. Accept: scope precision/recall, exclusion precision/recall, axis micro-F1, and per-regex precision/recall are all present. Any regex with precision under 0.85 is listed in `QUESTIONS.md` with a proposed fix — and a fix may only be made if it is tested against `labels_v1` and committed with before-and-after precision/recall.

## Phase 3: Full text, selection, cards (July)

**T-20 |** `07_fulltext.py` **| T-16, T-09 | ⚠ LIVE**Do: §5.7 — the fetch order that P-04 decided, the parsing, the rejection rules, and the per-source summary. Run it for **Jul**. Out: `data/fulltext/*` (git-ignored), `07_fulltext_status.jsonl`, `07_fulltext_summary.json`. Accept: the `parsed` share is within 10 percentage points of the P-04 estimate; 10 random parsed texts have correct page markers; `git status` shows nothing from `data/fulltext/` is tracked.

**T-21 |** `08_subset.py` **| T-20, T-19**Do: §5.8 — the score, the constrained selection, the force-include pause, and the sensitivity draws. Include the **empty-history rule** (no force-includes fire and `novelty_flag=1.0` for everyone in the first month). Unit tests against a synthetic 500-work pool, checking every constraint, the small-pool rule, and the empty-history path. Out: `08_subset_scores.csv`, `08_sensitivity.json`, `08_force_include_pending.json` for **Jul**. Accept: every G8 numeric constraint is satisfied or its shortfall is recorded; `jaccard_median` and `core_n` are printed; tests green, including one asserting that an empty card history produces zero force-includes rather than crashing.

**T-22 | Force-include confirmation | T-21 | ⛔ HUMAN**Do: If `08_force_include_pending.json` is not empty, send each item to Havid for a yes or no — the title, the DOI, the claimed PCE, and the anchor sentence from the abstract. Apply the answers and re-run the selection step of stage 08. On the **Jul** pilot this list is expected to be empty, because there is no card history to compare against (§5.8). Accept: `selection.n_forced` equals the number of "yes" answers.

**T-23 | Subset review | T-22 | ⛔ HUMAN**Do: `tools/sample_picks.py` produces 30 random depth picks with title, venue, axis, and the score components. Havid marks each one reasonable or not. Accept: 24 or more of 30 are reasonable (pilot criterion 2, recorded now and reused at T-40). If it is under 24, adjust only `axes.yaml` weights or the whitelist, re-run stage 08, and repeat once.

**T-24 |** `09_cards.py` **| T-21, T-05, T-12b | LLM (qwen ×2, agy) ⚠ LIVE**Do: §5.9 — extraction, the two passes, adjudication, the deterministic guards, and the slot-freeing with a single stage-08 re-run. Run for **Jul**. Unit tests for the guards against `fixtures/fulltext_sample.txt` with a hand-written card covering all four cases: anchor present, anchor absent, number outside the anchor, and anchor over 25 words. Out: `cards/*.json`, `09_cards_summary.json`, `claim_cards.jsonl`, `tokens.jsonl` lines for every call. Accept: an independent script finds 100% of the shipped anchors word-for-word in the parsed text; `n_dropped_papers` is reported; the median claims per card is 2 or more; the guard tests are green; **`tokens.jsonl` has one line per call including retries, and this stage's token total is reported — it is expected to dominate the whole run (§7.4)**.

**T-25 | Card spot-check | T-24 | ⛔ HUMAN**Do: `tools/sample_cards.py` produces 10 random cards with links to the PDF pages. Havid checks each anchored field against the PDF. Accept: 8 or more of 10 cards are fully correct (pilot criterion 4b). If it is under 8, revise `cards_extract_v1.md` to `v2`, re-run stage 09, and repeat once.

## Phase 4: Statistics and figures

**T-26 |** `10_stats.py` **| T-24, T-19**Do: §5.10 — every key in §3.5, the corpus regexes with precision and recall attached, the depth metrics from the cards, the axis z-scores (null with fewer than 3 months of history), the **Q46 month-over-month delta keys (null in month 1, since July is the first month)**, the **§7.4 aggregation of `tokens.jsonl` into `cost.json`**, and `stats_history/2026-07.json`. Out: `stats.json`; `stats_history/2026-07.json`. Accept: `stats_keys.validate_all(stats.json)` passes; every `audit.corpus.*` has `printable` set; the `selection.*` numbers equal the CSV counts; a printed summary of the **§6** numerals looks sane (for instance `efficiency_stated.pct` between 40 and 95); `delta_vs_prev_month_pp` is null everywhere with a recorded reason; `cost.json` carries a stage × model token matrix that sums to `tokens.jsonl`.

**T-27 |** `11_figures.py` **| T-26**Do: §5.11 — F1 to F7 (F8 and F9 optional), plus SI S1 and S2; PNGs carrying `tEXt run_hash`; PDF twins. Out: `fig/*`. Accept: the script asserts no literal numbers appear in figure code, so every plotted value is read from `stats.json`; PNGs carry the hash; captions contain no banned words and never the string "PRISMA".

**T-28 | Sanity review of §9 numerals and z-scores | T-27 | ⛔ HUMAN**Do: Send Havid F3, F4, and F1 plus the top 12 `audit.*` numbers with their precision and recall. One question: are these believable? Accept: Havid confirms, or names the metric to re-examine. Any change goes through `labels_v1` precision/recall, never by hand.

## Phase 5: Drafting

**T-29 |** `12_brief.py` **| T-26, T-05 | LLM (opus) ⚠ LIVE**Do: §5.12 — the structured brief, no prose. Record the calls in `cost.json`. Out: `12_brief.json` including the chosen title slot and its basis. Accept: every `claim_id` exists in the cards; **the title slot resolves to a real stats key and its `slot_axis` is one of the six or `audit`**; every `stats_key` validates; per-section claim counts are printed; sections under the 8-claim floor are flagged; **a check confirms the output contains no prose paragraphs — JSON only** (Q40).

**T-30 |** `13_draft.py` **| T-29, T-12b | LLM (qwen) ⚠ LIVE**Do: §5.13 for **§§1-5 and §8** (§6 and §7 come from T-31). The assembler renders `{{stats:key}}` and validates each key. Out: `draft/sec01.md` … `draft/sec05.md`, `draft/sec08.md`. Accept: every sentence with a paper-specific fact carries `[@key]` (heuristic check: list any sentence containing a card absorber or number without a marker); the §8.2 ceilings are respected; no unknown stats keys; `cost.json.writer_retries` recorded; the distinct in-body citation count is on track for the 180 cap.

**T-31 |** `14_critical.py` **| T-29 | LLM (opus brief + qwen draft) ⚠ LIVE**Do: §5.14 — opus produces the **§6 (audit) and §7 (gaps)** brief, qwen drafts both sections from it. Out: `14_brief.json`, `draft/sec06.md`, `draft/sec07.md`. Accept: **§6** references at least 6 corpus and 5 depth `audit.*` keys with the correct precision/recall wording; **§7** has at least 3 gaps, each tied to a stats key or a claim ID; the brief is JSON only; the drafts were written by the generator, as `cost.json` confirms.

**T-32 | Assemble +** `15_voice.py` **| T-30, T-31 | LLM (qwen) ⚠ LIVE**Do: Assemble `manuscript.md` — **the Q50 title rendered from the frame plus the stage-12 slot, with `title.*` written into `stats.json`**, the abstract with S1, the Q45 verdict, and at least 5 audit markers, **§§1-8 with S6 in §2 and the S2-S5 templates in §8**, and the back matter including the §8.5 AI declaration. Then run the §5.15 voice pass. Out: `manuscript.md`; `15_voice_diff.json` (the marker and number sets before and after). Accept: the marker set and the number set are unchanged by stage 15; **prose word count is 5,500 or fewer**; distinct in-body `[@key]` count is 180 or fewer. This check is stricter in practice now that a flash model runs the voice pass, so treat any diff as a hard failure rather than something to eyeball.

## Phase 6: Verification and review

**T-33 |** `16_verify.py` **G1-G10 | T-32, T-04**Do: §10 — all gates, including G1b with `entailment_v1.md` and its rewrite loop, G4 per §9, and the live DOI check through `oa()` cached in the ledger. Out: `gate_report.json`, `g1b_fidelity.jsonl`, `g4_prose.txt`. Accept: every gate reports a status; any failure is fixed **at its source stage**, never by editing the manuscript by hand, and then stage 16 runs again; the final report is all-pass, with G9 allowed to warn.

**T-34 |** `17_review.py` **dual review | T-33 | LLM (agy, opus) ⚠ LIVE**Do: §5.17 — the rounds, the Q32 conflict rule, **at least 2 rounds for §6 and §7**, G4 and G1b after each round, and the logged escalation path. Out: `review/round*_*.json`, the revision counter in `cost.json`. Accept: ACCEPT is reached within 3 rounds, or `[VERIFY]` items go to Havid (⛔ HUMAN if so); every red finding has a recorded resolution; any Q40 escalation rewrite is recorded in `cost.json.escalation_rewrites` and named in the digest.

## Phase 7: Build and deliver (July pilot)

**T-35 |** `18_build.py` **| T-34**Do: §5.18, including the standalone `.tex` compile test in a temporary directory and the PDF-versus-DOCX reference-list diff. Out: every §11 deliverable in `manuscript/2026-07/`. Accept: G5 green, including the standalone compile **and both Q45 page checks — content pages in [6,7] and total pages in [8,10], measured from the `References` page index**; the DOCX opens with its figures; the tarball lists only relative paths.

**T-36 |** `19_deliver.py` **| T-35**Do: §5.19 — the Telegram digest, `cost.json`, the **stage × model token matrix (SI table S4 plus one digest line, §7.4)**, a commit with the G4 and G1b proof, and the tag `2026-07-pilot`. No submission action. Out: digest sent; tag exists. Accept: the digest contains S1, the gate table, opus calls against the cap and `opus_path: subscription`, the G4 zero-count lines, the G1b pass line, the writer-failure and escalation counts, and **the per-stage token totals with `token_source` marked reported or estimated**; `git show 2026-07-pilot` shows the proof in the message.

**T-37 |** `run_month.py` **driver + resume | T-36**Do: A driver that runs 01→19 for a month with `--from NN --to NN`, resumes from the last `.done` marker, treats exit code 75 as paused (cap reached, human needed, or **writer unavailable** per Q41), and sends Telegram on pause or failure. Accept: `run_month.py 2026-08 --from 10 --to 11` re-runs only the stats and the figures and produces a byte-identical `stats.json` (that is the determinism check); a simulated writer outage exits 75 and resumes cleanly on the next invocation.

**T-38 | August: second month, full pipeline | T-40b (Havid signed off on July) | ⚠ LIVE**Do: **Resequenced under Q49 — this used to be a July backfill.** With July signed off, run the full 01→19 for **Aug 2026** via `run_month.py 2026-08`. August is the first month where the Q46 month-over-month delta actually computes, so check it prints as provisional and is not silently reported as a trend. Accept: `stats_history/` holds two months; z-scores are still null (3 needed); `delta_vs_prev_month_pp` is populated and labelled provisional; `manuscript/2026-08/` complete; the August token totals are within a factor of 2 of July's per stage, and any stage that is not gets explained in `docs/RETRO`.

**T-39 | Pilot scoring sheets | T-36**Do: `tools/sample_paragraphs.py` (**20 random §§3-5 paragraphs**, blind, scored 1-5 on insight, grounding, and readability); reuse the T-23 and T-25 results; collect the G1b round-1 statistics, the G4 counts, and the **per-stage token totals**. Out: `docs/PILOT_2026-07.md`, with all six §12 criteria pre-filled wherever a machine can compute them. Accept: the file is complete except for Havid's ratings.

**T-40 | Go/no-go decision | T-39 | ⛔ HUMAN**Do: Havid fills in the ratings. Hermes computes the verdict per §12 and writes it into `QUESTIONS.md` and `docs/PILOT_2026-07.md`. Accept: Go → T-40b. Retry → a fix list in `QUESTIONS.md`, re-run from the failing stage, back to T-39 once. Fallback → set `config/product.yaml: mode=bulletin` (the assembler drops §§3-5 to one table, the G2 ceiling moves to 3,000, and the page bands move to the bulletin values) and re-run 12→19. If criterion 3 or 4 was the failure, the reviewer-effort question goes to Havid first (Appendix B), because it is his quota being spent.

**T-40b | Havid reads the July PDF and approves the product | T-40 | ⛔ HUMAN**Do: **New under Q49, and it is the real gate in this plan.** Send Havid `manuscript/2026-07/manuscript.pdf` and ask one question: is this a thing a working scientist would read? Everything before this point is machinery; this is the first time anyone judges the actual output. Nothing downstream — August, the protocol paper, the cron — starts until he says yes. Accept: Havid approves the July PDF explicitly, and his verdict is recorded verbatim in `QUESTIONS.md`. On a no, the fix goes to whichever stage caused it, 12→19 re-runs, and this task repeats. **Blocks T-38, T-41, T-42, T-43.**

## Phase 8: Protocol paper and live month

**T-41 | Freeze the pilot | T-40b (product approved**)Do: Tag `2026-07-pilot-final`; snapshot `config/`, `prompts/SHA256SUMS`, and the `labels_v1` hash into `docs/PROTOCOL_FREEZE.md`. Accept: the tag exists; the hashes are recorded.

**T-42 | Protocol paper (Q36) | T-41 | LLM (opus brief, qwen draft) ⚠ LIVE**Do: About 5,000 words using the same stack: the gate and its traps; the venue percentile method; the selector and its sensitivity; the card schema and guards; the validation results from `labels_v1`; the gates; the hygiene rules; the AI usage. opus briefs, qwen drafts (Q40 applies here too). G1 is limited to the methods references. G4 applies. Deliverables per §11 into `manuscript/protocol/`. Accept: G2 (protocol variant), G4, and G5 are green; Havid reads and approves (⛔ HUMAN). The monthly §2 ceiling then drops to 300 words and cites this paper.

**T-43 | Cron created DISABLED | T-37, T-12, T-40b**Do: Create the `hermes cron` job `0 7 <DAY> * *` MYT running `run_month.py --previous-month`, with the §7.2 provider and model pins, **disabled**. Accept: `hermes cron list` shows the job disabled, with the right pins and the measured DAY.

**T-44 | Sep 2026 live month, manual | T-43, T-38, after 2026-10- | ⚠ LIVE ⛔ HUMAN**Do: Run `run_month.py 2026-09` by hand; handle any pauses; Havid signs off on the digest. Accept: all gates green; opus calls 45 or fewer; `manuscript/2026-09/` complete; tag `2026-09`.

**T-45 | Post-live retrospective | T-44**Do: Compare the Sep `cost.json`, revision rounds, G1b partial rate, nulled card fields, writer failures, and **per-stage token totals** against July and Aug. Write `docs/RETRO_2026-09.md` with proposed prompt or config changes — versioned, and never applied silently. Accept: the file is written; the changes are listed in `QUESTIONS.md` for approval.

**T-46 | Enable cron and merge | T-45 | ⛔ HUMAN**Do: On Havid's word: merge `v4-build` into `main`, enable the cron, and confirm the next run date in the digest. By this point **two** months (July and September) have been signed off by hand. Accept: `hermes cron list` shows it enabled; `main` is at the merged commit; `docs/PROGRESS_v5.md` is closed with the date.

**T-47 | Public-repo gate (Q47) | T-46 | ⛔ HUMAN**Do: **New in this revision, and it is the only task that may make anything public.** Going public is not a settings toggle. Run `secret_scan.py` and the G10 release checks over the **entire commit history**, not just the working tree: keys, abstract text, MT text, `data/fulltext/`, `data/private/`, and the archived `runs/`. Rotate the OpenAlex key exposed in chat on 2026-09-07 **now**, before anything is published. Then publish by **exporting a fresh repository from a squashed clean snapshot** — never by rewriting this history. Scrubbing a history is where leaks survive; starting from a clean snapshot is where they do not. Out: `docs/PUBLIC_RELEASE_CHECK.md` with the scan output and the export commit hash. Accept: the history scan is clean; the key is rotated; the exported repo contains no `data/private/`, no `data/fulltext/`, no `archive/legacy-v2/`, and no `.env`; Havid approves the export explicitly. Until this task passes, `Q21: repo open, public` is an **intention, not a fact**.

---

## Appendix A. Human checkpoints in order (Havid's calendar)

T-00 confirm private + seed `.env` (5 min) → T-18 CSV eyeball (20 min) → **T-19 label 200 July works (3-4 h — the critical path; every §6 percentage waits on this)** → T-22 force-include yes/no (5 min, expected empty in month 1) → T-23 30 picks (20 min) → T-25 10 cards against PDFs (45 min) → T-28 §6 sanity (15 min) → T-34 `[VERIFY]` items (if any) → T-40 pilot ratings (60 min) → **T-40b read the July PDF and approve the product (30 min — the real gate)** → T-42 protocol paper read (60 min) → T-44 Sep sign-off (30 min) → T-46 enable cron → T-47 public-release approval.

T-11 no longer needs Havid: Q38 is resolved as subscription. The only opening ask is T-00, and it is now a confirmation rather than a rotation.

Nothing here needs Hermes to be watched. Every item is Hermes stopping and waiting.

## Appendix B. Things Hermes must ask before doing (write it into `QUESTIONS.md`; never decide alone)

- Any change to `labels_v1`.
- Any change to the weights (0.40 / 0.35 / 0.25) or to the selection constraints.
- Any new banned word, or any allowlist entry beyond the seed list.
- **Raising the reviewer effort above** `medium`**, or lowering it** (Q40, §5.14) — it is Havid's quota.
- **Any model substitution at all**, and in particular anything that would give the writer a fallback (Q40, Q41).
- Any deliverable added or removed.
- Anything that would send abstract text or full text outside this host.
- Anything touching the preprint target (ChemRxiv) or `config/preprint.yaml`.
- Any change to the `(?<!un)` regex behaviour in §5.8 or §5.10.
- **Any change to the 5,500-word prose ceiling, the `[6,7]` content-page band, the `[8,10]` total-page band, or the 180 in-body citation cap (Q45).**
- **Making the repository public — that is T-47 and only Havid may approve it (Q47).**
- **Changing the title frame string, the `axis_phrases` table, or the slot-selection order (Q50).**

## Appendix C. Open item carried into execution

**Q40 was decided by Hermes, not by Havid.** Your instruction was "no claude cli and agy cli in writer". Read strictly, that removes opus from §12 outline, §14 (§9 and §10), and §15 voice, because all three emitted manuscript prose in v4. v5 takes the strict reading: opus produces briefs (JSON, never prose), qwen writes everything, and the only prose exception is the logged stage-17 escalation rewrite.

The cost of this choice, stated plainly: §9 is the scientific heart of the deliverable, and it is now written by a flash model instead of opus, while opus itself has also been stepped down from `xhigh` to `medium`. The mitigations are in the plan (a JSON brief that hands over every claim and number, at least two review rounds for §9 and §10, and pilot criteria 3 and 4 as hard gates).

**Q40 ratified by Havid 2026-09-07** ("I agree all in v5"), so the strict split is now his decision and not a silent Hermes one. The paragraphs below are kept as the rationale record. If you would rather opus kept writing the audit and gaps sections, say so before T-05 and only these change: §5.12, §5.14, §5.15, §7.1, §7.3, §8.2's writer column, §8.5, T-29, T-31, T-32. Nothing else in this plan depends on it.