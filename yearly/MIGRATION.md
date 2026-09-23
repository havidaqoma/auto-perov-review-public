# Yearly pipeline absorbed into auto-perov-review

The yearly review project (formerly `perovskite_pv_yearly`,
remote `havidaqoma/perovskite_pv_yearly`) now lives in this repo under
`yearly/`, carried across with `git subtree add` so its history is intact.

## Layout decision

`yearly/` is a self-contained cadence tree. It keeps its OWN
`scripts/stages/`, `config/`, `tests/`, `runs/` and `manuscript/`. Nothing
was flattened into the monthly stage set.

The reason is measured, not stylistic: 19 stage filenames exist in both
cadences and 13 of them had DIVERGED content. A flat merge would have
silently overwritten monthly logic with yearly logic. The shared-looking
names are not shared code.

Diverged at absorb time: `__init__.py`, `boilerplate.py`, `hygiene.py`,
`notation.py`, `s01_harvest.py`, `s02_06.py`, `s04_10.py`, `s09_cards.py`,
`s18d_build_v4.py`, `s21_tokens.py`, `util.py`, `yearly_section_map.py`,
`yearly_stats.py`, plus `common/env.py`.
Byte-identical: `layout.py`, `s11b_figures_v2.py`, `s13d_draft_v4.py`,
`s19_si.py`, `section_map.py`, and 8 of 9 `common/` modules.

## Why imports did not need rewriting

Every yearly stage inserts `scripts/` on `sys.path` via
`parents[1]`, and `stages/util.py` derives `ROOT` from `parents[2]`.
Both are relative to the file, so moving the whole tree one level down
re-resolved cleanly: `ROOT` now reports `yearly`
and finds `yearly/config/yearly.yaml`. No `from stages.X` import was edited.

## Verified at absorb

- yearly suite: 82 passed, run from the new location
- monthly suite: 223 passed, unchanged by the absorb
- no `.env` and no credential file tracked under `yearly/` (0 matches)
- no literal API keys or private keys in the carried tree
- all 18 yearly commits reachable through the merge's second parent

## Known issue, not fixed here

`yearly/manuscript/2025_yearly/*.md` embeds ABSOLUTE figure paths of the
form `perovskite_pv_yearly/runs/2025_6cb0e6ed/fig/*.pdf`
(8 in the manuscript, 2 in the SI). They still resolve only because the
old checkout was kept as an archive. The same figures already exist under
`yearly/runs/`, so these should be repointed before the next yearly build
is trusted. Left alone deliberately: rewriting them changes shipped
manuscript sources and belongs in a build-stage fix, not a move commit.
