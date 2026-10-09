# GasBrineBench row schema

One csv per property family (`data/<family>.csv`), all sharing the
columns below, in this order. Encoding UTF-8, comma-separated, one
header row. Read them with `keep_default_na=False`: the `gas` column is
legitimately empty for brine-only properties and must not become `NaN`.

| column | type | required | meaning |
|---|---|---|---|
| dataset_id | str | yes | short id for the (source, system) block, e.g. `co2_part1`, `haas1976`, `h2_water_binaries`. The per-dataset provenance table in `data/README.md` is keyed on it |
| source | str | yes | the curation key of the primary source, in the spelling the transcription carried (`WIEBE(1934)`, `Chabab2021_JCED66_T2`, `ALGHAFRI(2012) / EXP_NaCl_T298K.txt`). It is **not** a bibtex key; `tools/make_sources.py` owns the mapping onto citation keys and `SOURCES.md` prints it |
| gas | str | for gas properties | `co2, ch4, h2, n2, o2, c2h6, c3h8`; **empty** for brine-only properties (`rho`, `phi_osm`, `psat_ratio`, `eps_r`, `miac`) |
| property | str | yes | one of `solubility_molality, xc_saltfree, y_h2o, rho, phi_osm, psat_ratio, dh_sol, eps_r, miac`, and since v1.2 `rho_gas_loaded, visc, Cp_app` |
| T_K | float | yes | temperature [K] |
| P_bar | float | yes, except below | pressure [bar] (1.01325 for ambient). Blank only for `psat_ratio`, where the pressure *is* the measured quantity and is carried in `value` as a ratio, and (v1.2) for rows flagged `pressure-unstated` |
| m_Na, m_Cl, m_K, m_Ca, m_Mg, m_SO4 | float | yes | ion molalities [mol/kg water], fully dissociated basis; extend with new ion columns as needed (zeros for absent ions) |
| value | float | yes | the measured value in the family's canonical unit (see below) |
| uncertainty | float | no | standard uncertainty in the same unit; blank if the source states none. For the harness target sets it is the assigned 1-sigma weight — `data/README.md` says which is which |
| quality | str | yes | `R` (recommended: independently corroborated), `T` (tentative: plausible, single-source), `U` (uncertain: contradicted, author-flagged, or unverifiable) — justification in `data/QUALITY.md` |
| tag | str | yes | fit/test partition: `fit-eligible`, `test-only`, or `lle-regime` (see below) |
| flags | str | no (v1.2) | `;`-separated modifier flags, see *v1.2 additions* |
| data_origin | str | no (v1.2) | where the number comes from: `table` (printed in a table of the paper, converted by a documented rule), `figure` (read off a figure or smoothed curves; flag `figure-digitized`) or `calculated` (computed from an equation or a model, not measured; flag `calculated-not-measured`) |

## One family carries an extra column: `ternary.csv`

Every other family describes a system with one gas, so the gas-phase
composition is implied and needs no column. A ternary measurement does not
work that way: the same water at the same (T, P) dissolves different amounts
of CH4 and CO2 depending on how the gas phase is split between them. That
split is an independent state variable.

Rather than add a column that would be blank for the other 11,444 rows,
`data/ternary.csv` carries the schema above **plus one column**:

| column | type | required | meaning |
|---|---|---|---|
| y_co2_dry | float | yes (this family only) | CO2 mole fraction of the gas phase, water-free basis |

The row grammar is unchanged — one measurement per row, naming what it
measured:

| gas | property | what the row is |
|---|---|---|
| `ch4` | `xc_saltfree` | dissolved CH4 |
| `co2` | `xc_saltfree` | dissolved CO2 |
| `co2-ch4` | `y_h2o` | water content of the mixed gas phase |

`co2-ch4` is the only gas code outside the seven single gases, and it appears
only on the water-content rows, where the measurement is a property of the
mixture rather than of either component.

All ion columns are zero: **no ternary measurement in brine exists.** The CCB
tree of the upstream source materials holds only solver output, and the
upstream builder records that no experimental dataset is present. The ion
columns are carried so that such data would need no schema change.

`tools/validate.py` declares this in `EXTRA_COLS`; a family not named there
still rejects any column outside the standard set.

## v1.2 additions

### One optional column on every family: `flags`

`flags` holds `;`-separated modifier flags and is empty on rows that need none.
`tag` keeps its v1.1.1 meaning (`fit-eligible`, `test-only`, `lle-regime`); every
row added in v1.2 is `test-only` or `lle-regime`, because none was ever a fit
target. A flag says that a convention was applied, or that a row sits outside
the scored scope, so that a user can decide.

| flag | meaning | default loader |
|---|---|---|
| `gas-out-of-scope` | a single gas outside the seven benchmark gases (`ar, he, ne, kr, xe, c2h4, c2h2, c3h6, c-c3h6, 1-c4h8, n-c4h10, i-c4h10, neo-c5h12, c-c6h12, n-c6h14, i-c8h18, cf4, sf6, n2o, h2s, chf3, chclf2, c2h2f4, c2h4f2`) | dropped |
| `hydrate-regime` | the paper states a gas-hydrate-forming state or hydrate equilibrium | dropped |
| `condensed-phase-uncertain` | the paper does not settle whether the gas-rich phase is a liquid or a vapor | dropped |
| `fugacity-as-pressure` | the quantity is defined per unit fugacity (Weiss K0) and the fugacity is carried as the pressure | dropped |
| `subfreezing` | `T` is below a cryoscopic estimate (1.86 x 0.93 x total molality) of the brine's freezing point | dropped |
| `volume-basis-uncertain` | a per-volume concentration or coefficient whose volume basis (solution or solvent) the paper does not state; converted as per volume of solution, which can shift seawater values by up to about 2.6 % | dropped |
| `pressure-unstated` | the paper states no pressure; only for properties conventionally reported without one (enthalpies, osmotic coefficients, apparent molar heat capacities); `P_bar` is empty | dropped |
| `salinity-matrix` | composition given as seawater salinity or chlorinity, converted with reference-composition seawater (Millero et al. 2008) restricted to the six ions; bromide and bicarbonate are not carried, so the charge imbalance is up to about 0.014 mol/kg | kept |
| `source-caution` | the extraction recorded a caution about the values (misprint suspected, authors' own flag, adjusted values, ...); the text is in `data/provenance/provenance_v1_2.csv` | kept |
| `stp-assumed` | a gas volume per mass of water was converted to moles with 0 degC, 1 atm, 22.414 L/mol, because the paper does not define its standard conditions | kept |
| `solution-basis-converted` | a solubility given per mass of solution was converted to per kg of water from the stated composition | kept |
| `differential-pressure-converted` | a vapor-pressure lowering given as water minus solution was converted to the ratio with the IAPWS-95 vapor pressure of water | kept |
| `vapour-nonideality-by-authors` | a water activity above 373 K that the authors themselves corrected for vapor non-ideality | kept |
| `calculated-not-measured` | the source's values are output of an equation or a program, or are calculated from literature correlations, not measurements (SUSAK 1980: USGS program output extrapolated beyond its stated validity; SACHS 1995) | dropped |
| `smoothed-values` | the paper states that the tabulated values are smoothed, graphically interpolated or read from smoothed curves (Kobayashi and Katz 1953 Table VI, Todheide and Franck 1963, Takenouchi and Kennedy 1964-65, Amirijafari 1972); a table value, so informational | kept |
| `figure-digitized` | the values were read off a figure or smoothed curves because the paper prints no table (Jung 1971, Schlaikjer 2018); the reading accuracy is at best a few percent | dropped |
| `minor-species-omitted` | a composition given in g per kg of solution with minor species not carried by the six ions | kept |

Flags are the way a convention enters the database; none of them is applied
silently. `tools/validate.py` rejects an unknown flag, and rejects a row of a
gas outside the seven that lacks `gas-out-of-scope`.

### Three new families

| family file | property | unit | extra column | what it is |
|---|---|---|---|---|
| `rho_gas.csv` | `rho_gas_loaded` | kg/m3 | `m_gas` [mol gas / kg water] | density of a gas-loaded aqueous solution; `gas` is required |
| `visc.csv` | `visc` | mPa s | `m_gas` | viscosity; brine alone when `gas` is empty, gas-loaded when `gas` and `m_gas` are given |
| `thermo_brine.csv` | `Cp_app` | J/(mol K) | none | apparent molar heat capacity of the salt in solution (per mole of salt, as the authors define it) |

`rho_gas_loaded` and `Cp_app` follow the family grammar of the others: `gas` is
required for the first and empty for the second; `visc` may be either.
`m_gas` is the dissolved-gas loading derived from the paper's own statement
(gas mass fraction or gas mole fraction); a row whose loading is not stated is
not built.

### Pressure rule

`P_bar` is required, except for `psat_ratio` (the pressure is the value) and for
rows flagged `pressure-unstated`. Densities, density differences and
viscosities whose paper states no pressure are **not** in the database at all.

### Gas vocabulary

The seven benchmark gases and `co2-ch4` (ternary water-content rows) as before,
plus the 24 single gases listed under `gas-out-of-scope`. Gas-phase mixtures
other than the ternary family, and tables of two dissolved gases (CH4 + CO2
hydrate, N2 + CO2), are not in the database: their gas-phase composition has no
column. They are listed in `LEDGER.md`.

### The supplementary tier

`supplementary/supplementary_measurements.csv` is not a benchmark family and
has its own schema, documented in `supplementary/README.md`.

## `tag`, and where per-row provenance actually lives

`tag` records how a row may be used, not where it came from:

- `fit-eligible` — was a fit target in the parameterization the database grew
  out of, so it is training data rather than an independent test for that
  model; usable as training data by anyone refitting any model.
- `test-only` — never used as a fit target here.
- `lle-regime` — a row of a condensable gas (CO2 or a hydrocarbon) measured below
  the gas's critical temperature and at or above its own vapor pressure,
  so the gas-rich phase is a **liquid**: the point is a liquid–liquid
  mutual solubility, not a gas solubility. 354 rows (270 propane, 50 CO2, 26 butanes, 8 ethane). They are
  kept because they are good data about a different property, and consumers
  are expected to exclude them from gas-solubility scoring by default
  (`data/QUALITY.md` Sec. 7).

**Provenance — which table, figure or page a value came from — is recorded per
`dataset_id`, not per row.** It lives in two places, both in this repository:

1. `data/README.md`, *Provenance per dataset_id*: one row per block, naming
   the paper, the table or figure number, the page, the covered T/P/molality
   grid, the unit convention applied, and what was deliberately skipped.
2. `transcriptions/`: the 700 manually extracted source tables the curated blocks were
   built from, each opening with the `#AUTHOR(YEAR)` header that appears in
   the `source` column.

An earlier draft of this schema specified a per-row `provenance` string. The
database does not carry one and never did; this section describes what it
carries instead.

## Canonical units per family

- `solubility_molality`: mol gas / kg water
- `xc_saltfree`: salt-free-basis gas mole fraction (paired rows with
  `solubility_molality` where the source reports mole fraction; the
  validator checks the pair is consistent to 1e-9)
- `y_h2o`: water mole fraction in the gas-rich phase
- `rho`: kg/m3
- `phi_osm`: dimensionless (absolute-deviation scoring)
- `psat_ratio`: P_sat(brine)/P_sat(pure water) at the same T
- `dh_sol`: kJ/mol gas
- `eps_r`: static relative permittivity of the brine (dimensionless).
  An extension family, low-weight: see `data/README.md`
- `miac`: mean ionic activity coefficient (dimensionless). Declared, no
  rows yet
- `rho_gas_loaded`: kg/m3, density of a gas-loaded solution (v1.2)
- `visc`: mPa s (v1.2)
- `Cp_app`: J/(mol K) of salt, apparent molar heat capacity (v1.2)

## Rules

1. Values are transcribed from the SOURCE's tables wherever they
   exist; figure digitization is a last resort and must be flagged
   in the dataset's `data/README.md` entry with an accuracy estimate
   carried in `uncertainty`.
2. Unit conversions must be lossless and documented (the validator
   checks molality/mole-fraction sibling-row consistency to 1e-9).
3. No smoothed, correlated, or model-generated values — experimental
   points only. Evaluated compilations (e.g., steam tables) are
   admissible if flagged as evaluated in the dataset's provenance entry.
4. Duplicated sources (same lab, same data republished) keep the
   highest-precision copy; removals are ledgered. Two *different* sources
   printing the same value at the same state is independent corroboration,
   not a duplicate: the validator reports it and keeps both.
