# GasBrineBench

A curated, community-extensible benchmark dataset of experimental
thermodynamic data for **gas–brine systems**: gas solubility, brine
density, water activity (osmotic coefficients, vapor-pressure lowering),
water content of the gas phase, and enthalpy of gas dissolution, in
single- and mixed-salt aqueous electrolyte solutions.

Built to give equation-of-state and correlation developers one verified,
uniformly formatted, quality-coded target set — so model comparisons stop
depending on who curated which data.

**5,846 rows · 82 published sources · 7 gases · 6 ions · 273–623 K ·
0.1–3,500 bar.**

**Status: the database is complete and in the repository; the v1.0 release is
in preparation.** Until it is tagged and archived there is no version DOI to
cite, so cite the original experimental sources (see *Citation* below) and
expect the schema to be stable but the row set to grow.

## What is here

| family | rows | sources | gases | T [K] | P [bar] | R/T/U |
|---|---:|---:|---|---|---|---|
| `data/solubility.csv` | 3,783 | 57 | CO2, CH4, H2, N2, O2, C2H6, C3H8 | 273–589 | 0.10–1379 | 173 / 3590 / 20 |
| `data/y_h2o.csv` | 1,001 | 26 | CO2, CH4, H2, N2, C2H6, C3H8 | 273–623 | 4.3–3500 | 105 / 870 / 26 |
| `data/rho.csv` | 905 | 42 | — | 283–473 | 9–686 | 0 / 905 / 0 |
| `data/phi_osm.csv` | 101 | 2 | — | 298–373 | 1–1.5 | 75 / 26 / 0 |
| `data/dh_sol.csv` | 22 | 1 | CO2 | 323–373 | 21–202 | 0 / 22 / 0 |
| `data/psat_ratio.csv` | 21 | 1 | — | 373–523 | n/a | 21 / 0 / 0 |
| `data/eps_r.csv` | 13 | 1 | — | 298 | 1 | 0 / 13 / 0 |
| **total** | **5,846** | **82** | | **273–623** | **0.10–3500** | **374 / 5426 / 46** |

`sources` counts distinct `source` cells per family; the 82 total is the
number of distinct *published works*, after the several curation spellings
of one paper collapse onto one citation (`SOURCES.md`).

3,950 rows carry salt (Na+, K+, Ca2+, Mg2+, Cl−, SO4 2−, to 12 mol/kg of a
single ion); 1,896 are the salt-free binaries that anchor them.

**5,689 of the 5,846 rows are scored** as gas–brine equilibrium targets. The
other 157 are kept but sit outside that scope: 144 `lle-regime` propane rows
whose heavy phase is a liquid (mutual solubility, not gas solubility) and the
13 `eps_r` permittivity rows, which are a model-internal extension family
rather than a phase-equilibrium property. `SCHEMA.md` and `data/QUALITY.md`
Sec. 7 explain both.

## The provenance chain

Every number in this repository can be walked back to the page it was printed
on, and the chain is inspectable at each link:

```
transcriptions/EoS/.../EXP*.txt      hand-typed source tables, 819 files,
        |                            each headed #AUTHOR(YEAR)
        |   tools/builders/*.py      unit conversion, ion vectors, tagging
        v
data/*.csv                           the database, one csv per family
        |   tools/make_sources.py
        v
SOURCES.md + SOURCES.bib             reference, DOI and resolvable URL
                                     for every source, with row counts
```

Two of the builders (`hou2013.py`, `yh2o_sources_2026.py`) carry their
transcribed tables in source, table and page number included. The rest read
intermediate curation artefacts assembled earlier from the same
transcriptions; those intermediates are not in this repository, but the
transcriptions they came from are, and `data/README.md` names the route for
each block.

- **`transcriptions/`** — 819 hand transcriptions, 8,565 data rows, 124 source
  headers, with a `MANIFEST.tsv` giving each file's size, row count, source
  header and SHA-256. This is the bottom of the chain: it cannot be
  regenerated from anything, because it is somebody's typing checked against
  the printed page.
- **`data/README.md`** — the per-`dataset_id` provenance table: which paper,
  which table or figure, which page, which unit convention, and what was
  deliberately skipped, for every block of rows.
- **`data/QUALITY.md`** — the R/T/U justification record: what was checked
  against what, which rows were removed, and which apparent defects turned out
  to be in our own pipeline rather than in the source.
- **`SOURCES.md`** — the source manifest. **All 5,846 rows resolve to a real
  published source (100 %).**
- **`LEDGER.md`** — every correction, deduplication and quality-code decision,
  with its reason.

### About the builder scripts

`tools/builders/` holds the five scripts that produced the CSVs
(`build_v0.py`, `build_y_h2o.py`, `hou2013.py`, `yh2o_sources_2026.py`,
`quality_pass.py`). **They do not run standalone and are not meant to.** They
import a model-comparison harness (`bench.core.*`) and read curation artefacts
from maintainer-local paths that will not exist on your machine. They are
included because they are documentation — `hou2013.py` and
`yh2o_sources_2026.py` in particular carry the transcribed tables themselves,
in source, with the page and table numbers they came from, and all five record
exactly which rows were skipped and why. Read them; don't expect to run them.
The same is true of `tools/extract_transcriptions.py`, which selected
`transcriptions/` out of a private trove.

What *does* run against this repository alone is `tools/validate.py` and
`tools/make_sources.py`.

## Reproducing the generated files

Both generated files regenerate from this repository's own inputs
(`data/*.csv` and `bib/references.bib`), with nothing outside the clone on the
path, and are byte-stable across runs:

```
python3 tools/validate.py        # every check must pass; CI runs this
python3 tools/make_sources.py    # rewrites SOURCES.md and SOURCES.bib
```

`bib/references.bib` is the hand-maintained bibliographic library;
`SOURCES.bib` at the root is generated from it and holds the subset the data
actually cites. Edit the former, never the latter.

The validator checks schema conformance, physical ranges, the gas/gas-free
column convention, molality/mole-fraction sibling consistency to 1e-9,
same-source exact duplicates, the quality and tag vocabularies, and that every
`source` cell resolves to a real bibliographic record. It reports — but does
not reject — exact value coincidences between *different* sources at the same
state, because two labs agreeing to the precision they printed is a fact about
the data, not a defect. There are three such coincidences.

## Design principles

1. **Facts with provenance.** Every row carries its source; data points are
   literature facts, the curation is ours, the credit is the original
   experimentalists'. Cite them.
2. **One schema.** All properties share one row format (see `SCHEMA.md`); new
   salts and gases are new rows, not new formats.
3. **Immutable citable versions.** GitHub is the living resource; every
   release is archived on Zenodo with a version DOI. Papers cite version DOIs,
   so results stay reproducible while the dataset grows.
4. **Quality is auditable.** All corrections, deduplications, and quality-code
   decisions live in `LEDGER.md` with reasons, and the quality codes follow the
   consistency methodology of Yang et al. (Ind. Eng. Chem. Res. 2022, 61,
   15576).

## Sources

`SOURCES.md` is the source manifest: for every source contributing data it
records the bibliographic reference, DOI, resolvable URL, the property
families and row counts it contributes, the gas/salt/T/P/molality ranges it
covers, and its quality-code mix.

The manifest exists so that the primary literature never has to be
redistributed to make this dataset reproducible: a reader can walk it, obtain
each paper through their own library, and rebuild the database from primary
sources.

It is **generated** by `tools/make_sources.py`, which reads the CSVs directly —
so the coverage figures cannot drift away from the data. Re-run it after any
change and commit the diff. It never invents a citation: sources without a
bibliographic record are listed by name under *Needs citation*.

All 5,846 rows resolve to a real published source. Six of those works have no
DOI because none was ever issued — two doctoral theses, two research reports,
and two papers in journals that were never retrospectively registered — and
the manifest says so rather than supplying a plausible substitute. A short
*Source-key corrections* table records the handful of `source` cells that name
their paper wrongly (a misspelt surname, a missing year, an online-first year)
together with the evidence that settled each one, so every rewrite can be
checked against the primary paper.

## Contributing

Contributions of additional experimental data — new sources for existing
systems, new salt compositions, new gases, new properties — are welcome via
pull request. See `CONTRIBUTING.md` for the row schema, mandatory fields, and
the validation CI every PR must pass.

Note that `.gitignore` is an **allowlist**: it ignores everything by default
and re-admits known-good paths by name. If your PR adds a kind of file the
repository does not already hold, you will need to add it there first. That is
deliberate — see below.

## Governance

Maintained by the Moortgat research group (The Ohio State University).
Quality-code decisions are documented in the ledger; disputes about specific
data points are handled via GitHub issues.

## Citation

Cite **the original experimental sources** for the numbers you use —
`SOURCES.md` and `SOURCES.bib` give the full reference and DOI for each — and
cite this repository for the compilation. Zenodo DOI and data-descriptor
paper to be added at the v1.0 release; see `CITATION.cff`.

## Licensing, and what is deliberately absent

The numerical values in `data/` and `transcriptions/` are **measurements made
and published by the authors cited in `SOURCES.md`**. They are redistributed
here as transcribed data, with full attribution to those authors, who are the
people to credit. What is ours, and what the CC-BY-4.0 licence covers, is the
compilation: the transcription, the unit conversions, the uniform schema, the
quality coding, the deduplication, and the provenance apparatus. Code under
`tools/` is MIT. See `LICENSE`.

**No publisher PDFs are included here, and none can be.** The papers are
copyrighted by their publishers; we hold copies locally in order to transcribe
them and we cannot pass them on. That is precisely why `SOURCES.md` exists in
the form it does: with a reference, a DOI and a resolvable URL for every
source, a reader can obtain each paper through their own library and check any
row against the original. Nothing in this repository depends on redistributing
a single copyrighted page.

Nothing under a `source_materials/`, `papers/`, `paper/` or `emails/` path,
no manuscript or draft, no reviewer correspondence and no `.tex` source has
ever been committed here, and the allowlist `.gitignore` re-blocks those
extensions and directory names *after* the allowlist so that no future
`git add -A` can introduce one.
