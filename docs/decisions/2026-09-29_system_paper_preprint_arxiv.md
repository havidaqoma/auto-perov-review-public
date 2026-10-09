# Decision: the system paper's preprint goes to arXiv

**Date:** 2026-09-29
**Decided by:** Havid
**Scope:** the system paper only (`papers/system/`). The monthly perovskite PV
review series is unchanged and stays on ChemRxiv
(`2026-09-09_preprint_target_chemrxiv.md`).

## Why the two differ

The monthly reviews are chemistry content, so a chemistry server suits them.
The system paper is a methods paper on language-model extraction and
verification, and that community reads arXiv. Its journal target, J. Chem.
Inf. Model., explicitly allows an initial draft on arXiv.

## What changed

- `papers/scripts/build_arxiv_bundle.py` builds `submission/arxiv/arxiv_upload.tar.gz`
  from the same LaTeX as the JCIM submission (text identical, TOC-graphic page
  removed), with the `.bbl` files and a `00README.json` for pdflatex.
- `submission/preprint.json` records the server and, once announced, the arXiv
  identifier. `build_cover_letter.py` reads it; while the identifier is empty
  the letter shows a yellow `[CHECK]` rather than a guessed number.

## Licence

arXiv's default non-exclusive licence is the conservative choice for a paper
that will go through ACS copyright transfer, for the same reasons given in the
2026-09-09 note. The author selects it on the arXiv form.
