# GasBrineBench row schema

One csv per property family (`data/<family>.csv`), all sharing the
columns below. Encoding UTF-8, comma-separated, one header row.

| column | type | required | meaning |
|---|---|---|---|
| dataset_id | str | yes | short unique id for the (source, system) block, e.g. `RUMPF1994_CO2_NACL` |
| source | str | yes | citation key; full reference must exist in `SOURCES.bib` |
| gas | str | for gas properties | `co2, ch4, h2, n2, o2, ...`; empty for gas-free properties |
| property | str | yes | one of `solubility_molality, xc_saltfree, y_h2o, rho, phi_osm, psat_ratio, dh_sol, miac` |
| T_K | float | yes | temperature [K] |
| P_bar | float | yes | pressure [bar] (1.01325 for ambient; for psat_ratio the reference-state convention is documented in the family README) |
| m_Na, m_Cl, m_K, m_Ca, m_Mg, m_SO4 | float | yes | ion molalities [mol/kg water], fully dissociated basis; extend with new ion columns as needed (zeros for absent ions) |
| value | float | yes | the measured value in the family's canonical unit (see below) |
| uncertainty | float | no | standard uncertainty in the same unit; blank if the source states none |
| quality | str | yes | `R` (recommended: independently corroborated), `T` (tentative: plausible, single-source), `U` (uncertain: contradicted, author-flagged, or unverifiable) — justification in `LEDGER.md` |
| provenance | str | yes | where in the source the value lives (table/figure/page), and `digitized` if read from a figure |

## Canonical units per family

- `solubility_molality`: mol gas / kg water
- `xc_saltfree`: salt-free-basis gas mole fraction (paired rows with
  solubility_molality where the source reports mole fraction)
- `y_h2o`: water mole fraction in the gas-rich phase
- `rho`: kg/m3
- `phi_osm`: dimensionless (absolute-deviation scoring)
- `psat_ratio`: P_sat(brine)/P_sat(pure water) at the same T
- `dh_sol`: kJ/mol gas (P in MPa noted per family README)
- `miac`: mean ionic activity coefficient (dimensionless)

## Rules

1. Values are transcribed from the SOURCE's tables wherever they
   exist; figure digitization is a last resort and must be flagged
   in `provenance` with an accuracy estimate in `uncertainty`.
2. Unit conversions must be lossless and documented (the validator
   checks molality/mole-fraction sibling-row consistency to 1e-9).
3. No smoothed, correlated, or model-generated values — experimental
   points only. Evaluated compilations (e.g., steam tables) are
   admissible if flagged as `evaluated` in provenance.
4. Duplicated sources (same lab, same data republished) keep the
   highest-precision copy; removals are ledgered.
