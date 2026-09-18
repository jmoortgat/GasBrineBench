# GasBrineBench

A curated, community-extensible benchmark dataset of experimental
thermodynamic data for **gas–brine systems**: gas solubility, brine
density, water activity (osmotic coefficients, vapor-pressure lowering),
water content of the gas phase, and enthalpy of gas dissolution, in
single- and mixed-salt aqueous electrolyte solutions.

Built to give equation-of-state and correlation developers one verified,
uniformly formatted, quality-coded target set — so model comparisons stop
depending on who curated which data.

**11,444 rows · 109 published sources · 7 gases · 6 ions · 273–633 K ·
0.1–3,500 bar.**

**Status: released.** [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22834146.svg)](https://doi.org/10.5281/zenodo.22834146)
v1.0.0, archived on Zenodo. Cite the original experimental sources for the
numbers (see *Citation* below) and the version DOI above for the compilation.
The schema is stable; the row set will grow, and each release gets its own
version DOI so a result always names the snapshot it used.

## What is here

| family | rows | sources | gases | T [K] | P [bar] | R/T/U |
|---|---:|---:|---|---|---|---|
| `data/solubility.csv` | 9,367 | 103 | CO2, CH4, H2, N2, O2, C2H6, C3H8 | 273–633 | 0.10–3500 | 591 / 8744 / 32 |
| `data/y_h2o.csv` | 1,015 | 26 | CO2, CH4, H2, N2, C2H6, C3H8 | 273–623 | 4.3–3500 | 105 / 884 / 26 |
| `data/rho.csv` | 905 | 42 | — | 283–473 | 9–686 | 0 / 905 / 0 |
| `data/phi_osm.csv` | 101 | 2 | — | 298–373 | 1–1.5 | 75 / 26 / 0 |
| `data/dh_sol.csv` | 22 | 1 | CO2 | 323–373 | 21–202 | 0 / 22 / 0 |
| `data/psat_ratio.csv` | 21 | 1 | — | 373–523 | n/a | 21 / 0 / 0 |
| `data/eps_r.csv` | 13 | 1 | — | 298 | 1 | 0 / 13 / 0 |
| **total** | **11,444** | **109** | | **273–633** | **0.10–3500** | **792 / 10594 / 58** |

`sources` counts distinct `source` cells per family; the 109 total is the
number of distinct *published works*, after the several curation spellings
of one paper collapse onto one citation (`SOURCES.md`).

5,685 rows carry salt (Na+, K+, Ca2+, Mg2+, Cl−, SO4 2−, to 12 mol/kg of a
single ion); 4,697 are the salt-free binaries that anchor them.

**11,287 of the 11,444 rows are scored** as gas–brine equilibrium targets. The
other 157 are kept but sit outside that scope: 144 `lle-regime` propane rows
whose heavy phase is a liquid (mutual solubility, not gas solubility) and the
13 `eps_r` permittivity rows, which are a model-internal extension family
rather than a phase-equilibrium property. `SCHEMA.md` and `data/QUALITY.md`
Sec. 7 explain both.

## Using it from Python

The `gasbrinebench` package in this repository reads, filters and exports the
CSVs. It needs **pandas and nothing else**; there is nothing to install and
nothing to build — clone the repository and import it.

```python
import gasbrinebench as gbb

df = gbb.load()                    # every family, as one DataFrame
co2 = gbb.load("solubility", gas="co2", T=(373, 425), quality="R")
gbb.write(co2, "co2.parquet")
```

`notebooks/gasbrinebench_tour.ipynb` is an executed tour of both the package
and the data — coverage, salting-out trends, isotherms, water content, brine
density, the quality-code mix — and it runs from a fresh clone.

### Loading

| call | does |
|---|---|
| `gbb.load(family="all", **filters)` | read one family, several, or all; returns a DataFrame |
| `gbb.load_family(name)` | one family's CSV verbatim, no filtering, no derived columns |
| `gbb.available_families()`, `gbb.data_dir()` | what is on disk, and where |

`load()` applies the two conventions a hand-rolled `read_csv` gets wrong: it
reads with `keep_default_na=False`, so the legitimately empty `gas` cell of a
brine-only row stays an empty string, and then coerces the numeric columns, so
the genuinely blank cells (`P_bar` on the `psat_ratio` rows, `uncertainty`
where the source stated none) become `NaN` rather than `''`.

**`load()` excludes the 144 `lle-regime` rows by default.** Those propane
points are liquid–liquid mutual solubilities, not gas solubilities
(`data/QUALITY.md` Sec. 7); scoring them as the latter is a category error.
Pass `exclude_tags=None` for all 11,444 rows.

The data directory is found beside the package, or from the working directory
upward, or from `$GASBRINEBENCH_DATA`.

### Filtering

`gbb.select(df, ...)` — every argument optional, all of them ANDed.
`gbb.load()` forwards the same keywords, so one call usually does.

| argument | selects |
|---|---|
| `gas=` | `'co2'`, `['ch4', 'h2']`, …; `''` for the brine-only rows |
| `family=`, `property=` | property family, or specific `property` values |
| `source=`, `dataset_id=` | a named source or dataset block |
| `quality=` | `'R'` / `'T'` / `'U'` |
| `tag=`, `exclude_tags=` | the fit/test partition |
| `T=(lo, hi)`, `P=(lo, hi)` | inclusive windows [K], [bar]; `None` leaves a side open |
| `ionic_strength=`, `total_molality=` | inclusive windows [mol/kg water] |
| `salt_system=` | `'water'` / `'single-salt'` / `'mixed-salt'`, or a label like `'Na-Cl'` |
| `ions=`, `ions_exactly=` | rows containing these ions, or exactly these |
| `salt_free=` | `True` for the binaries, `False` for the brines |

A value outside the vocabulary **raises**, naming the valid set, rather than
returning an empty frame.

### Derived quantities

Not stored in the CSVs, because they follow from what is:

| call | returns |
|---|---|
| `gbb.ionic_strength(df)` | ½ Σ mᵢzᵢ² [mol/kg water] |
| `gbb.total_molality(df)` | Σ mᵢ [mol/kg water] |
| `gbb.charge_imbalance(df)` | Σ mᵢzᵢ [eq/kg]; ≤ 2 × 10⁻³ across the database, from rounded printed molalities |
| `gbb.salt_system(df)`, `gbb.salt_system_kind(df)`, `gbb.ions_present(df)` | ion-set label, single/mixed classification, ion tuple |
| `gbb.with_derived(df)` | all of the above as columns (`load()` does this for you) |
| `gbb.solubility_pairs(df)` | one row per solubility point with both mole-fraction siblings |

`solubility_pairs()` is the one worth knowing about. `data/solubility.csv`
stores a solubility twice where the source reported both conventions —
`solubility_molality` and `xc_saltfree` as separate rows at the same state.
It joins them, recomputes the salt-free fraction so the gaps are filled, and
adds the **salt-inclusive** fraction with the ions counted as species. That
last one is derived and not measured: nobody reports it, many models expect
it, and doing the conversion here makes the convention explicit.

### Inventory

`gbb.inventory(df, by=...)`, `gbb.coverage(df)`, `gbb.sources(df)` — rows,
distinct sources, gases, T/P range and R/T/U mix for any selection; the
(gas × salt system) rectangle, holes included; and one row per contributing
source.

### Export

`gbb.write(df, path)` picks the format from the suffix — `.csv`,
`.parquet`/`.pq`, `.h5`/`.hdf5`/`.hdf` — or pass `fmt=`. `gbb.to_pandas(df)`
keeps it in memory.

**CSV needs nothing beyond pandas. Parquet needs `pyarrow`, HDF5 needs
`tables`, and if either is absent you get a `MissingDependencyError` naming
that one package and the command that installs it** — checked before pandas
is reached, so a missing backend never arrives disguised as an engine
resolution failure or an `AttributeError` from inside `to_hdf`.
`gbb.export.have('parquet')` asks in advance.

### From the shell

```
python3 -m gasbrinebench                     # inventory by family
python3 -m gasbrinebench --by gas            # inventory by gas
python3 -m gasbrinebench --gas co2 --quality R -o co2.csv
python3 -m gasbrinebench --family solubility -o solubility.parquet
```

### Speciation codes: PHREEQC, Geochemist's Workbench

**No native exporter is provided, deliberately.** The brine half of a row maps
onto a PHREEQC `SOLUTION` block cleanly, and `gasbrinebench/interop.py`
tabulates that mapping — `m_Na → Na`, `m_SO4 → S(6)`, `temp = T_K − 273.15`
(°C), `pressure = P_bar / 1.01325` (atm), `units mol/kgw`, `-water 1.0`.

The other half does not map. Reproducing one of these measurements requires
the gas-phase boundary condition — a fugacity — and the database stores the
**total** pressure, as the sources report it. Converting one to the other
needs a water-content model and an equation of state, which are exactly the
modelling steps a gas-solubility benchmark exists to test. An exporter would
have to choose both, bake the choice into the file, and hand you a number that
looks like data; any later disagreement between the code and the measurement
would be partly an artefact of the converter's own assumptions, with nothing
in the file to say so. Two smaller obstacles point the same way: PHREEQC needs
a pH that these experiments do not report, and the databases covering this
pressure range have stated validity limits well inside 0.1–3,500 bar.

For Geochemist's Workbench not even the mapping is asserted: its input-script
specification was not consulted, and writing a file format down from memory is
the same mistake in a different costume.

### Tests

```
python3 -m pytest tests -q                       # the package
python3 -m pytest --doctest-modules gasbrinebench -q   # the examples above
```

Both run in CI on two dependency sets — pandas alone, and pandas with both
export backends — so the missing-backend path is exercised rather than
skipped.

## The provenance chain

Every number in this repository can be walked back to the page it was printed
on, and the chain is inspectable at each link:

```
transcriptions/EoS/.../EXP*.txt      hand-typed source tables, 710 files,
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

- **`transcriptions/`** — 710 hand transcriptions, 7,637 data rows, 122 source
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
- **`SOURCES.md`** — the source manifest. **All 11,444 rows resolve to a real
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

What *does* run against this repository alone is the `gasbrinebench` package,
`tools/validate.py` and `tools/make_sources.py`.

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

All 11,444 rows resolve to a real published source, and all but seven of
those works carry a DOI. Six have none because none was ever issued — two
doctoral theses, two research reports, and two papers in journals that were
never retrospectively registered. The seventh is Sultanov et al. 1972, a
two-page article in a Soviet trade journal that Crossref does not index; its
record is reconstructed from two independent citing bibliographies and says
so. The manifest states these cases rather than supplying a plausible
substitute. A short
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
cite this repository for the compilation:

> Moortgat, J. (2026). *GasBrineBench: a benchmark dataset of experimental
> gas–brine thermodynamic data* (v1.0.0) [Data set]. Zenodo.
> https://doi.org/10.5281/zenodo.22834146

Use the **version** DOI above, not the concept DOI
(`10.5281/zenodo.22834145`), which always resolves to the newest release. A
benchmark number is only reproducible if the citation names the snapshot it
was computed against. Machine-readable metadata is in `CITATION.cff`.

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
