# GasBrineBench

A curated, community-extensible benchmark dataset of experimental
thermodynamic data for **gas–brine systems**: gas solubility, brine
density, water activity (osmotic coefficients, vapor-pressure lowering),
water content of the gas phase, and enthalpy of gas dissolution, in
single- and mixed-salt aqueous electrolyte solutions.

Built to give equation-of-state and correlation developers one verified,
uniformly formatted, quality-coded target set — so model comparisons stop
depending on who curated which data.

**26,815 rows · 255 published sources · 7 benchmark gases (plus 24 further
gases, flagged) · 6 ions · 238–773 K · 0.1–3,500 bar, and a separate
supplementary tier of 5,174 measurements the benchmark families cannot hold.**

> **New here?** Look at the data in your browser first. Each notebook opens in Colab with one click, installs nothing, needs no account
> beyond a Google login, and downloads this repository itself.
>
> - **overview and coverage**: What is in the database: coverage in T and P, gases and salts, quality codes, flags, contributing papers.  
>   <a href="https://colab.research.google.com/github/jmoortgat/GasBrineBench/blob/main/notebooks/01_overview_and_coverage.ipynb" target="_blank" rel="noopener noreferrer"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab"/></a>
> - **gas solubility**: Gas solubility for each of the seven gases: against pressure and temperature, source by source, and salting out.  
>   <a href="https://colab.research.google.com/github/jmoortgat/GasBrineBench/blob/main/notebooks/02_gas_solubility.ipynb" target="_blank" rel="noopener noreferrer"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab"/></a>
> - **water content mixtures enthalpy**: Water content of the gas phase, the CO2 + CH4 + water family, enthalpies of solution.  
>   <a href="https://colab.research.google.com/github/jmoortgat/GasBrineBench/blob/main/notebooks/03_water_content_mixtures_enthalpy.ipynb" target="_blank" rel="noopener noreferrer"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab"/></a>
> - **brine properties**: Density, osmotic coefficient, vapour-pressure ratio, heat capacity, viscosity, density of CO2-loaded water.  
>   <a href="https://colab.research.google.com/github/jmoortgat/GasBrineBench/blob/main/notebooks/04_brine_properties.ipynb" target="_blank" rel="noopener noreferrer"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab"/></a>
> - **uncertainty and variance**: Stated uncertainties, agreement between independent sources, the bias of each source, spread at one state.  
>   <a href="https://colab.research.google.com/github/jmoortgat/GasBrineBench/blob/main/notebooks/05_uncertainty_and_variance.ipynb" target="_blank" rel="noopener noreferrer"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab"/></a>
> - **supplementary tier**: The measurements the benchmark families cannot hold: isopiestic pairs, molar volumes, enthalpies of dilution.  
>   <a href="https://colab.research.google.com/github/jmoortgat/GasBrineBench/blob/main/notebooks/06_supplementary_tier.ipynb" target="_blank" rel="noopener noreferrer"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab"/></a>
>
> They are also committed with their figures, so GitHub shows them without running anything. `python3 tools/make_notebooks.py` rebuilds them.

**Status: v1.2.1 in preparation (this branch).** The last archived release is
v1.1.1, [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22898153.svg)](https://doi.org/10.5281/zenodo.22898153)
(11,537 rows from 111 sources); the version DOIs of v1.2.0 and v1.2.1 are assigned when it
is archived. Cite the original experimental sources for the numbers (see
*Citation* below) and the version DOI for the compilation. The row schema of
v1.1.1 is unchanged except for one optional column (`flags`, below); the row
set grows, and each release gets its own version DOI so a result always names
the snapshot it used.

## What is here

| family | rows | sources | gases | T [K] | P [bar] | R/T/U |
|---|---:|---:|---|---|---|---|
| `data/solubility.csv` | 14,472 | 148 | 23 gases, 7 of them the benchmark gases | 273–773 | 0.10–3500 | 1396 / 12874 / 202 |
| `data/y_h2o.csv` | 1,972 | 51 | CO2, CH4, H2, N2, C2H6, C3H8 and 4 others | 238–623 | 1.0–3500 | 105 / 1810 / 57 |
| `data/ternary.csv` | 93 | 3 | CO2 + CH4 together | 323–423 | 19–1000 | 0 / 93 / 0 |
| `data/rho.csv` | 6,180 | 23 | — | 274–643 | 1.0–700 | 0 / 6180 / 0 |
| `data/rho_gas.csv` | 951 | 4 | CO2 | 274–726 | 99–1008 | 0 / 951 / 0 |
| `data/visc.csv` | 85 | 2 | — and CO2 | 294–449 | 50–965 | 0 / 85 / 0 |
| `data/thermo_brine.csv` | 692 | 8 | — | 278–603 | 1.0–200 | 0 / 692 / 0 |
| `data/phi_osm.csv` | 717 | 11 | — | 298–573 | 0.39–86 | 0 / 717 / 0 |
| `data/dh_sol.csv` | 238 | 7 | 18 gases | 273–373 | 0.89–202 | 0 / 238 / 0 |
| `data/psat_ratio.csv` | 1,402 | 19 | — | 292–647 | n/a | 21 / 1381 / 0 |
| `data/eps_r.csv` | 13 | 1 | — | 298 | 1 | 0 / 13 / 0 |
| **total** | **26,815** | **249** | | **238–773** | **0.10–3500** | **1522 / 25034 / 259** |

`sources` counts distinct *published works* per family, after the several
curation spellings of one paper collapse onto one citation (`SOURCES.md`); the
249 total is the number of distinct works in the whole database.

17,256 rows carry salt (Na+, K+, Ca2+, Mg2+, Cl−, SO4 2−, to 58 mol/kg of
ionic strength); 9,810 are salt-free.

### What changed in v1.2

v1.1.1 held 11,537 rows from 111 papers. v1.2 adds 15,278 rows (net) from 146 further
papers (one v1.1.1 citation, Chapoy 2004, was also split in two; see `CHANGELOG.md`), extracted from the tables of the papers themselves (every table read
twice, independently, the two readings compared by
script and every disagreement settled against the page image;
`data/provenance/provenance_v1_2.csv`, `transcriptions_v1_2/`), three new
families (`rho_gas`, `visc`, `thermo_brine`), and a separate
**supplementary tier** (below). Two principles decided what entered:

* a row enters a benchmark family only if its conversion to the schema needs
  nothing the paper does not print: no model, no assumed density, no assumed
  composition. Where a convention is unavoidable it is applied by the builder
  and **flagged** (`stp-assumed`: gas volumes per gram of water are converted
  with 0 degC and 1 atm; `solution-basis-converted`, `salinity-matrix`, ...);
* **a measurement with no stated pressure is not a benchmark row.** Liquid
  densities and viscosities whose paper states no pressure are left out
  entirely. The exceptions are properties that are conventionally measured
  without a pressure — enthalpies of dissolution, osmotic coefficients
  (isopiestic equilibrium at the solution's own vapour pressure) and apparent
  molar heat capacities. Those 522 rows are kept, carry an empty `P_bar`, are
  flagged `pressure-unstated`, and are excluded by the default loader.

### Modifier flags and what the default loader drops

The optional column `flags` holds `;`-separated modifier flags (empty on all
v1.1.1 rows except where v1.2 rows were added). `tag` keeps its v1.1.1
meaning. `gbb.load()` drops, by default, rows that carry any of
`gas-out-of-scope` (a gas outside the seven), `hydrate-regime`,
`condensed-phase-uncertain`, `fugacity-as-pressure`, `subfreezing`,
`volume-basis-uncertain` (per-litre composition the paper does not settle) and
`pressure-unstated`, together with the `lle-regime` rows. That leaves **23,090
rows** in the default view. `exclude_flags=None, exclude_tags=None` returns all
26,815; `SCHEMA.md` defines every flag.

### Supplementary tier

`supplementary/supplementary_measurements.csv` (5,174 rows from 107 tables)
holds in-scope measurements that no benchmark family can store without a
model: apparent molar volumes, enthalpies of dilution and dissolution,
isopiestic molality pairs (stored as printed, so users can convert them with
the reference model of their choice), mixture volumes, compressions, Henry
constants on a molality basis, gas solubilities in bases that need a density
or a partial pressure the paper does not give (Ostwald and Bunsen
coefficients, mass per litre), and salt solutions outside the six-ion set
(NaBr, LiCl, KBr, SrCl2, ...). Rows carry the value and unit as printed, the
solutes in mol/kg water where the paper's basis allows it, and the composition
as printed otherwise. See `supplementary/README.md`. These rows are **not**
part of the benchmark; they are published so that nothing extracted and
verified is lost.

**Scored rows.** Of the 26,815 benchmark rows, 23,090 are in the default view
(scored as gas–brine equilibrium and brine-property targets); the rest are
kept and flagged.

## Verification

Every row was compared with its paper (see `CHANGELOG.md`, "Full row-by-row audit"). `data/provenance/audit_status.csv` gives each row one status:
`verified` (17,967 rows: printed digits equal the stored ones after the documented conversion), `corrected` (8,158: the audit changed at
least one field, listed in `data/provenance/audit_corrections.csv`), `not-verifiable` (90: no paper or table available, or the paper does not settle the basis)
and `residual-difference` (600: a known difference from the paper that was not corrected, such as a brine composition adjusted for
electroneutrality or a paper whose own columns disagree). A blind random audit of the corrected data found 8 major errors in 531 verifiable readings (1.5 %,
95 % interval 0.8-2.9 %); after adjudication 2 of them (0.4 %) are not already disclosed by a flag or a documented convention. The column `data_origin` says whether a
number is printed in a table, read off a figure or calculated by the authors' model, and the flag `smoothed-values` marks tables the authors state are smoothed.

## Fitting on the audited data only

```python
import gasbrinebench as gbb
fit = gbb.load(reliable=True)            # 20,899 rows: verified or corrected against the paper, quality not U, no unsettled-convention flag
only_checked = gbb.load(audit_status="verified")      # or 'corrected', 'not-verifiable', 'residual-difference' (any of them, as a list)
```

`reliable=True` keeps the rows whose stored digits equal the printed ones (audit status `verified` or `corrected`), drops quality U, everything the default
view drops, and the rows flagged `source-caution`, `stp-assumed`, `salinity-matrix` or `solution-basis-converted`, whose paper does not settle a convention.
It is the strictest set we can defend; it does not mean that a paper has no systematic error of its own (see Verification).

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

Six executed notebooks in `notebooks/` show the data and their uncertainties (`notebooks/README.md`): coverage, gas
solubility by gas and by source, water content and mixtures, brine properties, the spread between datasets, and the supplementary
tier. They run from a fresh clone with pandas, numpy and matplotlib (`python3 tools/make_notebooks.py` rebuilds them).

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

**`load()` excludes the 354 `lle-regime` rows and every row carrying a
default-excluded flag.** The `lle-regime` points (144 propane rows of v1.1.1
and 210 added in v1.2) are liquid–liquid mutual solubilities, not gas
solubilities (`data/QUALITY.md` Sec. 7); scoring them as the latter is a
category error. The flagged rows are listed above. Pass
`exclude_tags=None, exclude_flags=None` for all 26,815 rows.

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
| `flags=`, `exclude_flags=` | rows carrying (or not carrying) modifier flags |
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
transcriptions/EoS/.../EXP*.txt      hand-typed source tables, 700 files,
        |                            each headed #AUTHOR(YEAR) (v1.0-v1.1)
transcriptions_v1_2/<doi>/           v1.2 tables as extracted (table_N.csv),
        |                            with the mapping that converts each
        |                            (mapping_N.json) and paper.json
        |   tools/builders/*.py      unit conversion, ion vectors, tagging
        |   tools/builders_v1_2/     the v1.2 builder (runs from this repo)
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

- **`transcriptions/`** — 700 hand transcriptions, 7,607 data rows, 120 source
  headers, with a `MANIFEST.tsv` giving each file's size, row count, source
  header and SHA-256. This is the bottom of the chain: it cannot be
  regenerated from anything, because it is somebody's typing checked against
  the printed page.
- **`transcriptions_v1_2/`** — the tables of the 207 papers that contribute rows to
  the v1.2 families or the supplementary tier, as extracted and verified, each with the mapping file that says how its columns
  become schema columns, and a `MANIFEST.csv` tying every DOI to its `source`
  key. `data/provenance/provenance_v1_2.csv` lists, for every v1.2
  `dataset_id`, the paper, table, row count, verification status, the
  experimental method and any caution recorded for it.
- **`data/README.md`** — the per-`dataset_id` provenance table: which paper,
  which table or figure, which page, which unit convention, and what was
  deliberately skipped, for every block of rows.
- **`data/QUALITY.md`** — the R/T/U justification record: what was checked
  against what, which rows were removed, and which apparent defects turned out
  to be in our own pipeline rather than in the source.
- **`SOURCES.md`** — the source manifest. **All 26,815 rows resolve to a real
  published source (100 %).** It also carries each paper's OpenAlex citation
  count (`data/provenance/citation_counts.csv`) as metadata, not as a quality
  measure.
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
(`data/*.csv`, `bib/references.bib` and `bib/references_v1_2.bib`), with nothing outside the clone on the
path, and are byte-stable across runs:

```
python3 tools/validate.py        # every check must pass; CI runs this
python3 tools/make_sources.py    # rewrites SOURCES.md and SOURCES.bib
```

`bib/references.bib` is the hand-maintained bibliographic library;
`bib/references_v1_2.bib` holds the records of the sources added in v1.2,
generated from Crossref metadata retrieved by DOI;
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

All 26,815 rows resolve to a real published source, and all but a few of
those works carry a DOI (`SOURCES.md` lists them). Six have none because none was ever issued — two
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
> gas–brine thermodynamic data* (v1.1.1) [Data set]. Zenodo.
> https://doi.org/10.5281/zenodo.22898153

(v1.2.0 and v1.2.1: use the DOI printed here once the release is archived.) Use the
**version** DOI, not the concept DOI, which always resolves to the newest
release. A
benchmark number is only reproducible if the citation names the snapshot it
was computed against. Machine-readable metadata is in `CITATION.cff`.

## Licensing, and what is deliberately absent

The numerical values in `data/`, `supplementary/`, `transcriptions/` and `transcriptions_v1_2/` are **measurements made
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
