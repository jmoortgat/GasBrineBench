# Changelog

## v1.0.0 — 2026-09-18

Archived on Zenodo: [10.5281/zenodo.22834146](https://doi.org/10.5281/zenodo.22834146)
(version DOI, pinned to this row set). The concept DOI
`10.5281/zenodo.22834145` always resolves to the newest release; cite the
version DOI, so a result names the snapshot it was computed against.

### Data corrections

The database arrived at 5,846 rows from 82 sources and is released at 11,444
from 109. Almost none of that is new transcription: it is data that had been
typed, checked and sitting in the source tree, which the builders were not
reading. Each item below was verified against the primary paper before it was
applied, and `LEDGER.md` carries the per-item justification.

- **Salt-free binaries and the Susak high-temperature block promoted.** The
  binary CO2–H2O and CH4–H2O solubilities anchor every salting-out comparison
  in the database but were not themselves in it. About 1,400 rows, plus 64
  Susak (1980) points above 573 K.
- **Every isotherm directory is now read.** The builders walked a hard-coded
  list of three temperatures; the tree holds far more. 1,209 rows.
- **The `_X<author>` files are read.** They were skipped as duplicates of the
  canonical file at the same slot. They are not duplicates — they are a second
  author at a slot whose number was taken. 115 rows at readable isotherms.
- **Duffy (1961) ion vectors corrected.** The divalent cation molality sat in
  the `m_K` column, so a 1.4 m CaCl2 brine was recorded as 1.4 m KCl with no
  calcium and a charge imbalance. Duffy studied CH4–H2O–NaCl–CaCl2 and used no
  potassium at all. 48 rows.
- **Nine isotherms carried the wrong temperature.** Temperature came from the
  name of the directory holding a file, which is an integer kelvin: it cannot
  represent 351.65 K, and it collapses a Fahrenheit-grid source onto its
  Celsius-grid neighbour. A file may now declare its own temperature on the
  source line, audited against the paper. Corrected: Portier (291.15, 310.15),
  Jacob (297), Bastami (351.65, 375.15), Culberson and Olds (344.26, 444.26),
  O'Sullivan (324.65, 375.65, 398.15).
- **16 quality codes fell from R to T as a direct result.** `R` is awarded by
  cross-source corroboration, and four groups corroborated only because the
  rounding had put two different isotherms on one integer — O'Sullivan with
  Gao at 323 K, Culberson with Amirijafari at 343 K. Neither pair had measured
  at the same temperature. Removing false corroboration from the
  highest-confidence tier is the point of the exercise, not a regression.
- **A file that had never been read.** `443K/EXP2_T444K.txt` (Olds 1942,
  340 degF) sits in a directory named `443K`, and the builder matched
  `EXP*_T443K.txt`. Its 11 water-content rows appear in no other source and
  had never entered any build. Its counterpart, a stray copy of a Todheide
  isotherm filed under the wrong directory, is excluded by name.
- **Bibliography.** Records without a DOI went from 30 to 7, each of the seven
  documented as having none issued rather than none found. 27 new records.
- **`benchmark_v0.parquet` was missing a family.** It concatenated six of the
  seven csvs, omitting `y_h2o` — 10,429 rows where the csvs hold 11,444.
  Nothing published was affected (the parquet is gitignored and the reader
  loads csvs), but the local artifact was wrong.
- **Transcriptions 819 -> 710.** The superseded `CO2/CPA/SRK` tree, the
  `(copy)` artifacts and one misfiled file are no longer extracted. SRK is a
  lossy duplicate of the `PR` tree: it carries `X` where Hou (2013) records
  y_CO2 = 0.97189, and stops at 2500 bar where Todheide & Franck (1963) runs
  to 3500. Both trees were compared path by path before either was dropped.

### Documentation held to the data

- `tests/test_loader.py` asserted a row total and a per-family breakdown frozen
  when the reader package was written, so it had been failing since the first
  expansion without telling anyone anything. It is named for the invariant that
  matters — README and data agree — and now reads the counts out of the README
  table, which survives the database changing size.
- Twelve package doctests carried counts from the same era. Two of them were
  not counts growing but statements becoming untrue: `salt_system_kind()` now
  reports a third category, and `coverage()` illustrated "zeros mark the gaps"
  with a cell that had since filled, so it now uses one that is still a gap.


### A Python package and a tour notebook

The repository shipped CSVs and provenance and no way to use them
programmatically. It now ships both.

- **`gasbrinebench/`** — importable from the repository root, pandas the only
  requirement. A loader that reads any family or all of them with the
  `keep_default_na=False` convention applied and the numeric columns coerced
  back to floats; `select()` filtering by gas, family, property, source,
  quality code, tag, salt system (single/mixed, or by ions present), and
  windows on T, P, ionic strength and total molality; derived ionic strength,
  total molality, charge imbalance and salt-system labels; `solubility_pairs()`
  joining the molality and mole-fraction sibling rows and adding the
  salt-inclusive basis; inventory tables; and export to pandas, CSV, Parquet
  and HDF5. **The default loader excludes the 144 `lle-regime` rows**, for the
  reason `data/QUALITY.md` Sec. 7 gives.
- **Optional dependencies fail by name.** Parquet needs `pyarrow` and HDF5
  needs `tables`; if either is absent the package raises a
  `MissingDependencyError` naming the package and the install command, before
  pandas is reached. CSV never needs anything.
- **`python3 -m gasbrinebench`** — inventory of the database, or a filtered
  export, from the shell.
- **`notebooks/gasbrinebench_tour.ipynb`** — executed, outputs committed, runs
  from a fresh clone. Coverage, salting-out trends, isotherms, water content,
  brine density, the quality-code mix, and the inter-laboratory spread shown
  as shaded envelopes.
- **`tests/`** — pytest suite over the package and the vocabularies, plus the
  package doctests. Wired into `.github/workflows/validate.yml`.
- **No PHREEQC or Geochemist's Workbench exporter**, deliberately: the brine
  composition maps cleanly but the gas-phase boundary condition does not,
  because the database stores total pressure and a speciation code needs a
  fugacity. `gasbrinebench/interop.py` documents the column mapping and the
  reasoning.
- `CITATION.cff` gained a `version:` field, which `gasbrinebench.__version__`
  and `tests/test_version.py` hold it to.

### The database is now in the repository

Until this point the repository was scaffolding: schema, validator, CI and a
source manifest generated from data held elsewhere. `data/` held a `.gitkeep`.
It now holds the database.

- **Seven family CSVs, 11,444 rows, 109 published sources** — `solubility.csv`
  (9,367), `y_h2o.csv` (1,015), `rho.csv` (905), `phi_osm.csv` (101),
  `dh_sol.csv` (22), `psat_ratio.csv` (21), `eps_r.csv` (13). Seven gases, six
  ions, 273–633 K, 0.1–3,500 bar. 11,287 of those rows are gas–brine
  equilibrium targets; the other 157 (144 `lle-regime` propane rows, 13
  `eps_r` rows) are kept but sit outside that scope. The database landed at
  5,846 rows from 82 sources; *Data corrections* above is how it grew.
- **The provenance documents** — `data/README.md` (per-`dataset_id`
  provenance: paper, table, page, unit convention, deliberate omissions) and
  `data/QUALITY.md` (the R/T/U justification record). Both are reproduced
  verbatim from the harness that produced the data, with a header explaining
  which of the paths they mention are outside this repository.
- **710 raw hand transcriptions** under `transcriptions/` — 230 KB, 7,637 data
  rows, 122 source headers, with `MANIFEST.tsv` carrying each file's size, row
  count, source header and SHA-256. All 710 verified against those hashes.
  (819 on arrival, before the superseded SRK tree and the `(copy)` artifacts
  were excluded; see *Data corrections*.) This closes the provenance chain: typed source table -> built CSV
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
- Source coverage is **100 %** — all 11,444 rows resolve to a real published
  source, 102 of the 109 works with a DOI and 7 recorded as having none.

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
