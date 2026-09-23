# Decision: preprint target moves from arXiv to ChemRxiv

**Date:** 2026-09-09
**Decided by:** Havid
**Plan reference:** Q68 (amends Q66; supersedes the arXiv half of Q17/Q19/Q23)

## The change

The monthly perovskite PV review series is submitted to **ChemRxiv**, not
arXiv. Reason: the topic is chemistry-scoped, so a chemistry preprint server
(ACS/RSC/GDCh) is the right venue for it.

## Why this was a format change, not a rename

A blind `s/arxiv/chemrxiv/` would have been wrong twice over.

**First, the two servers want different things.** The old stage was built
around what arXiv accepts: a self-contained tarball of `.tex` + `.bbl` +
relative-path figures, a `00README.XXX` naming the compile engine, and an
archive code (`physics.app-ph`) with cross-lists. ChemRxiv instead takes the
**main content as a PDF or .docx upload** and does not compile LaTeX for you,
and it classifies by **subject category** rather than archive code. So the
deliverable the human actually submits changed from a tarball to
`manuscript_v4.pdf`, and stage 20 now fails closed if that PDF is missing --
a failure the old stage structurally could not detect, because its payload was
the tarball it had just built itself.

**Second, `arxiv` has two unrelated meanings in this repo.** Only one moved:

| Meaning | Status |
| --- | --- |
| arXiv as a **harvest source** -- stage 01 queries the arXiv API, stage 05 dedupes arXiv IDs, the ledger has an `arxiv_id` column, cited works carry `10.48550/arxiv.*` DOIs | **Untouched, permanent.** A blind rename would have silently dropped a literature source |
| arXiv as the **submission target** | Moved to ChemRxiv |

`tests/test_preprint_target.py::test_arxiv_survives_as_a_harvest_source`
asserts the first row, so a future cleanup cannot collapse the distinction.

## Why the platform now lives in one file

By the time the target changed, the string `arxiv` had spread into a stage
filename, an output directory, a tarball stem, a `.done` marker key, a
metadata schema and six documents. That is a value with no single definition,
copied until nobody knows which copy is authoritative.

Everything platform-specific is now in **`config/preprint.yaml`**: platform
name, slug, subject categories, licence, DOI prefix, submission route. A
future move is a config edit, not a repo-wide hunt.

## The DOI rule

ChemRxiv assigns a DOI under prefix `10.26434` **on posting**. `preprint_doi`
stays `null` and the generated checklist asks the human to paste the real one
back. No script may write this field: a DOI invented before the preprint
exists is a fabricated identifier, which is the one output class this pipeline
must never produce. Gated by
`test_preprint_doi_is_never_invented_by_a_script`.

## Still no automated submission

Unchanged from Q17=b, and now asserted rather than assumed.
`submission_route: manual_portal`, `api_submission_supported: false`, and
`test_no_automated_submission_path_exists` greps stage 20 for `requests.post`
and friends. The hard stop before submission is the design, not an oversight.

## What was built

- `config/preprint.yaml` -- the platform contract (new).
- `scripts/stages/s20_arxiv.py` -> `scripts/stages/s20_chemrxiv.py`, rewritten:
  PDF as main upload, `submission_metadata.json` with paste-ready portal
  fields, a generated `SUBMISSION_CHECKLIST.md`, archival `.tex`/`.bbl`/figures
  kept for a later journal transfer, and a fail-closed guard that refuses to
  emit a package whose own metadata still says arXiv.
- The abstract in the metadata is **read out of the built manuscript**, not
  retyped, so the portal paste box cannot drift from the PDF. Same reason
  `CORRESP_EMAIL` is imported from `boilerplate.py` rather than duplicated:
  the title page and the submission metadata must not be able to disagree.
- `tests/test_preprint_target.py` -- 9 assertions (new).
- Docs revised: `MASTER_HANDBOOK.md` §8.1, `MASTER_HANDBOOK_YEARLY.md`,
  `MASTER_HANDBOOK_GENERAL.md`, `PLAN_...v5.md` (Q68 row added, Q66 amended),
  `IDEA.md`, `config/cron_prompt_monthly.txt`.

The cron prompt mattered most: it drives an unattended monthly run, so a stale
"prepare the arXiv bundle" line there would have quietly restored the old
target on the next build.

## History preserved, not rewritten

Old arXiv packages moved to `archive/deprecated_arxiv_pkg/<month>_v4/` rather
than being deleted. Run logs, `.done` markers and gate reports from past
builds still say `20_arxiv`, because that is what actually ran; rewriting them
would be dishonest about the pipeline's own history. The migration gate
therefore skips `OLD/`, `archive/`, `runs/`, `manuscript/` and `.staging/`.

## Verified

- 232/232 tests pass.
- June, July and August 2026 ChemRxiv packages rebuilt, exit 0 each.
- Each package: `platform: ChemRxiv`, `route: manual_portal`,
  `api_submission_supported: false`, primary category `Energy`,
  secondary `Materials Chemistry`, `CC BY 4.0`, `preprint_doi: null`, corresponding email
  `havidaqoma.khoiruddin@xmu.edu.my`, main content `manuscript_v4.pdf`,
  supplementary `supplementary_v4.pdf`.
- No live file targets arXiv for submission (gated).
- The only `arxiv` string left inside a package is
  `10.48550/arxiv.2606.27592` in `manuscript.tex` -- a **cited work's DOI**,
  correctly preserved.


## Amendment 1 -- primary subject category (2026-09-09)

Havid set the ChemRxiv categories to **`Energy` primary, `Materials
Chemistry` secondary**. Reason: perovskite PV is energy-device work and the
review's spine is certified efficiency, stability and scale-up, so Energy
leads. Materials Chemistry carries the mechanism sections (defect passivation,
buried interfaces, composition).

**`Materials Chemistry` is not `Materials Science`.** ChemRxiv lists both as
separate categories and Havid corrected an initial draft that said Materials
Science. The gate asserts the exact secondary label rather than a substring,
because the two names differ by one word and would both satisfy a loose check.

Amended in the same commit: `config/preprint.yaml`, the G-test
`test_chemrxiv_subject_categories_not_arxiv_archive_codes`,
`MASTER_HANDBOOK.md` §8.1, `PLAN` Q19/Q23 and Q68, and the three regenerated
packages.

**Still unverified against the live portal:** the exact category labels.
`Energy` and `Materials Chemistry` were chosen by Havid, not read off the
ChemRxiv submission form. Confirm the dropdown wording before posting; it is a
one-line config edit if it differs.

## Open question -- licence (2026-09-09)

Havid asked about `CC BY-NC-ND 4.0` instead of `CC BY 4.0`, reasoning that he
may want to use the PDF for a journal submission. The licence is UNCHANGED
pending his decision, because it cannot be revoked once a preprint is posted.

The premise needs one correction: **the preprint licence does not gate journal
submission.** Submitting your own manuscript to a journal is not a reuse event
under the CC licence you attached to the preprint, so CC BY does not block a
later submission. What the licence controls is what *third parties* may do
with the posted preprint, permanently.

The real trade-off, and it does favour NC-ND on one axis: Wiley,
Chemistry Europe and Angewandte Chemie explicitly *recommend* that authors
post preprints under CC BY-NC-ND or a no-reuse licence, so that the author
retains rights the publisher will later want. So NC-ND is the more
conservative choice if subscription/copyright-transfer journals are the target.
Against it: NC-ND blocks commercial reuse and derivatives, which some funders
and open-access mandates disallow for the posted version.
