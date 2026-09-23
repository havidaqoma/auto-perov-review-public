# ChemRxiv submission checklist

Generated 2026-09-23 10:17 from run `2026-H1`.
Route: **manual_portal** at https://chemrxiv.org -- there is no automated submission code path in this repo, by design.

## Upload

1. Main content: `manuscript_v6.pdf` (ChemRxiv accepts PDF or .docx; the PDF is the built artifact and is gate-checked).
2. Supplementary: `supplementary_v6.pdf`
3. Data pack: attach `data/` or link the repository release.

## Paste-ready fields

- **Title:** Perovskite Photovoltaics in January-June 2026: The Certified Frontier From Cell to Module
- **Corresponding author:** Havid Aqoma, havidaqoma.khoiruddin@xmu.edu.my
- **Primary subject category:** Energy
- **Secondary categories:** Materials Chemistry
- **Licence:** CC BY 4.0
- **Abstract:** see `submission_metadata.json` (copied verbatim from the built manuscript, so it cannot drift from the PDF)

## After posting

- ChemRxiv assigns a DOI under `10.26434`. Paste it into `config/preprint.yaml` as `preprint_doi`. Do not let any script invent this value before it exists.

## Archival, not uploaded

- `manuscript.tex` + `manuscript.bbl` + `fig/` and the tarball are kept for a later journal transfer. ChemRxiv does not compile LaTeX.
