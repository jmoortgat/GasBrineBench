# Changelog

## Unreleased (pre-v1.0)

### The database is now in the repository

Until this point the repository was scaffolding: schema, validator, CI and a
source manifest generated from data held elsewhere. `data/` held a `.gitkeep`.
It now holds the database.

- **Seven family CSVs, 5,846 rows, 82 published sources** — `solubility.csv`
  (3,783), `y_h2o.csv` (1,001), `rho.csv` (905), `phi_osm.csv` (101),
  `dh_sol.csv` (22), `psat_ratio.csv` (21), `eps_r.csv` (13). Seven gases, six
  ions, 273–623 K, 0.1–3,500 bar. 5,689 of those rows are gas–brine
  equilibrium targets; the other 157 (144 `lle-regime` propane rows, 13
  `eps_r` rows) are kept but sit outside that scope.
- **The provenance documents** — `data/README.md` (per-`dataset_id`
  provenance: paper, table, page, unit convention, deliberate omissions) and
  `data/QUALITY.md` (the R/T/U justification record). Both are reproduced
  verbatim from the harness that produced the data, with a header explaining
  which of the paths they mention are outside this repository.
- **819 raw hand transcriptions** under `transcriptions/` — 251 KB, 8,565 data
  rows, 124 source headers, with `MANIFEST.tsv` carrying each file's size, row
  count, source header and SHA-256. All 819 verified against those hashes on
  arrival. This closes the provenance chain: typed source table -> built CSV
  -> source manifest.
- **The builder scripts** under `tools/builders/` (`build_v0.py`,
  `build_y_h2o.py`, `hou2013.py`, `yh2o_sources_2026.py`, `quality_pass.py`)
  and `tools/extract_transcriptions.py`. These do not run standalone — they
  import a harness that is not here and read maintainer-local paths — and the
  README says so. They are here as documentation of how the rows were derived
  and what was skipped.

### Self-contained

- `tools/make_sources.py` read the database from a sibling checkout and
  harvested bibliography from four `.bib` files in other repositories. It now
  reads `data/` and `bib/references.bib`, both in this repository, so
  `SOURCES.md` and `SOURCES.bib` regenerate from a clone alone. The 82
  harvested records were vendored into `bib/references.bib`; `SOURCES.bib`
  remains its generated output and is byte-identical to the version generated
  from the external bibliographies.
- Regeneration is idempotent: a second run reproduces both files byte for
  byte.
- Source coverage is unchanged at **100 %** — all 5,846 rows resolve to a real
  published source, 76 of the 82 works with a DOI and 6 recorded as having
  none.

### Validator and schema corrected against the real data

Documented in full in `LEDGER.md`. In short: `SCHEMA.md` had specified a
per-row `provenance` column the database does not have (the column is `tag`);
`eps_r` was an undeclared property; blank `P_bar` is legitimate for
`psat_ratio`; the `source` column holds curation keys, not bibtex keys, so the
citation check now resolves through the manifest generator's own mapping; and
exact value coincidences between different sources are corroboration rather
than duplicates. No data was reshaped to make the validator pass. The
validator gained checks (gas column convention, uncertainty numeric and
non-negative, value finite, no undeclared columns, tag vocabulary) and each
rule was confirmed to fire against a deliberately corrupted copy.

### Publication safety

- `.gitignore` is now an **allowlist**: `*` ignores everything, directories are
  re-admitted for descent, and known-good paths are re-included by name.
  `*.pdf`, `*.tex`, `*.docx`, archive and binary extensions, and the directory
  names `source_materials/`, `papers/`, `paper/`, `drafts/`, `reviews/`,
  `correspondence/`, `emails/`, `OPT*/` and `TXT/` are re-blocked *after* the
  allowlist, so no re-inclusion rule added later can admit one. Verified
  against 27 paths that must be ignored and 22 that must be trackable.
- `data/.gitkeep` removed.

## Earlier (scaffolding)

- Repository scaffold: schema, contributing rules, validator, CI.
- Source manifest: every one of the 5,846 rows resolves to a real published
  reference, up from 57.4 %. Four placeholder citations and 23 sources with no
  bibliographic record at all were identified from the primary papers and
  confirmed against Crossref; see `LEDGER.md`.
- `tools/make_sources.py`: added an evidence-backed source-key correction
  table for `source` cells that name their paper wrongly, and fixed two
  matching defects (variant suffixes longer than one letter, and `\ce{}`
  being mis-read as a cedilla in titles).
