# BrineBench

A curated, community-extensible benchmark dataset of experimental
thermodynamic data for **gas–brine systems**: gas solubility, brine
density, water activity (osmotic coefficients, vapor-pressure
lowering), water content of the gas phase, and enthalpy of gas
dissolution, in single- and mixed-salt aqueous electrolyte
solutions.

Built to give equation-of-state and correlation developers one
verified, uniformly formatted, quality-coded target set — so model
comparisons stop depending on who curated which data.

**Status: pre-release scaffolding. No data published yet; v1.0 is
in preparation.**

## What will be in v1.0

- Gas solubility (CO2, CH4, H2, N2, O2, ...) in water and in
  single- and mixed-salt brines (Na+, K+, Ca2+, Mg2+, Cl-, SO4 2-)
- Brine densities, osmotic coefficients, vapor-pressure ratios
- Water content of the gas-rich phase
- Enthalpy of CO2 dissolution
- Every point with: full provenance (source citation), stated or
  assigned uncertainty, and an R/T/U quality code
  (recommended/tentative/uncertain) with a documented justification
  ledger, following the consistency methodology of Yang et al.
  (Ind. Eng. Chem. Res. 2022, 61, 15576).

## Design principles

1. **Facts with provenance.** Every row carries its source; data
   points are literature facts, the curation is ours, the credit is
   the original experimentalists'. Cite them.
2. **One schema.** All properties share one row format
   (see `SCHEMA.md`); new salts and gases are new rows, not new
   formats.
3. **Immutable citable versions.** GitHub is the living resource;
   every release is archived on Zenodo with a version DOI. Papers
   cite version DOIs, so results stay reproducible while the
   dataset grows.
4. **Quality is auditable.** All corrections, deduplications, and
   quality-code decisions live in `LEDGER.md` with reasons.

## Contributing

Contributions of additional experimental data — new sources for
existing systems, new salt compositions, new gases, new properties
— are welcome via pull request once v1.0 is released. See
`CONTRIBUTING.md` for the row schema, mandatory fields, and the
validation CI every PR must pass.

## Governance

Maintained by the Moortgat research group (The Ohio State
University). Quality-code decisions are documented in the ledger;
disputes about specific data points are handled via GitHub issues.

## Citation

Citation information (Zenodo DOI and data-descriptor paper) will be
added at v1.0 release. Until then this repository is pre-release
and should not be cited.

## License

Data: CC-BY-4.0. Code (validator/loader): MIT. See `LICENSE`.
