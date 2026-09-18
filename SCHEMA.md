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
| property | str | yes | one of `solubility_molality, xc_saltfree, y_h2o, rho, phi_osm, psat_ratio, dh_sol, eps_r, miac` |
| T_K | float | yes | temperature [K] |
| P_bar | float | yes, except below | pressure [bar] (1.01325 for ambient). Blank only for `psat_ratio`, where the pressure *is* the measured quantity and is carried in `value` as a ratio |
| m_Na, m_Cl, m_K, m_Ca, m_Mg, m_SO4 | float | yes | ion molalities [mol/kg water], fully dissociated basis; extend with new ion columns as needed (zeros for absent ions) |
| value | float | yes | the measured value in the family's canonical unit (see below) |
| uncertainty | float | no | standard uncertainty in the same unit; blank if the source states none. For the harness target sets it is the assigned 1-sigma weight — `data/README.md` says which is which |
| quality | str | yes | `R` (recommended: independently corroborated), `T` (tentative: plausible, single-source), `U` (uncertain: contradicted, author-flagged, or unverifiable) — justification in `data/QUALITY.md` |
| tag | str | yes | fit/test partition: `fit-eligible`, `test-only`, or `lle-regime` (see below) |

## `tag`, and where per-row provenance actually lives

`tag` records how a row may be used, not where it came from:

- `fit-eligible` — was a fit target in the parameterization the database grew
  out of, so it is training data rather than an independent test for that
  model; usable as training data by anyone refitting any model.
- `test-only` — never used as a fit target here.
- `lle-regime` — a condensable-hydrocarbon row measured below the
  hydrocarbon's critical temperature and at or above its own vapor pressure,
  so the hydrocarbon-rich phase is a **liquid**: the point is a liquid–liquid
  mutual solubility, not a gas solubility. 144 rows, all propane. They are
  kept because they are good data about a different property, and consumers
  are expected to exclude them from gas-solubility scoring by default
  (`data/QUALITY.md` Sec. 7).

**Provenance — which table, figure or page a value came from — is recorded per
`dataset_id`, not per row.** It lives in two places, both in this repository:

1. `data/README.md`, *Provenance per dataset_id*: one row per block, naming
   the paper, the table or figure number, the page, the covered T/P/molality
   grid, the unit convention applied, and what was deliberately skipped.
2. `transcriptions/`: the 710 hand-typed source tables the curated blocks were
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
