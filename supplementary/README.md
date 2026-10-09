# Supplementary tier

`supplementary_measurements.csv` holds **5,174 verified measurements from 107
tables** that the benchmark families (`data/*.csv`) cannot store without a
model, an assumed density or an assumed pressure. They were extracted, checked
and mapped by the same pipeline as the benchmark rows (see `CHANGELOG.md`,
v1.2.1) and are published so that nothing verified is lost. **They are not
benchmark data**: they are not scored, carry no fit/test tag, and are not read
by the `gasbrinebench` loader.

## What was done to a value

Only what the paper itself prints: the printed scale of the column is applied
(`x 10^4` headers), the temperature is converted to K and the pressure to bar.
The **value keeps the unit the paper uses**, named in `value_unit`, and keeps
its printed sign convention, which `value_what` describes in the paper's own
terms. Read `value_what` before using a class: for example a printed column may
be minus the enthalpy of dilution, or a quantity multiplied by a power of ten
that the mapping has already undone. Nothing is converted between calories and
joules, litres of solution and kilograms of water, or isopiestic molality and
osmotic coefficient: each of those needs a convention or a reference model that
a user may want to choose.

## Columns

| column | meaning |
|---|---|
| `dataset_id`, `source`, `doi` | the block, the citation key (resolves in `SOURCES.md`), the paper's DOI |
| `property_class` | one of the 13 classes below |
| `property_native` | the extraction's own property name |
| `gas` | gas code when the measurement concerns a gas, else empty |
| `T_K`, `P_bar` | temperature [K], pressure [bar]; `P_bar` is empty only in the classes conventionally reported without one (isopiestic pairs, enthalpies, water activities) |
| `solutes_mol_per_kg_water` | `Salt:molality;Salt:molality`, built only when the paper's basis is a molality, a mass fraction or a mole fraction of salts of known molar mass; otherwise empty |
| `composition_as_printed` | the composition exactly as the mapping records it: basis, species, values and units |
| `value`, `value_unit`, `value_what` | the measured number, the paper's unit, and what the column is |
| `value2`, `value2_unit`, `value2_what` | a second printed quantity of the same row (the reference-salt molality of an isopiestic pair, the second molality of a dilution) |
| `reference_salt` | reference salt of an isopiestic series |
| `uncertainty` | as printed, in the unit of the paper's uncertainty column (see the mapping in `transcriptions_v1_2/`) |
| `quality`, `tag` | `T` for every row (single-source, not cross-checked), tag empty unless the mapping adds a flag such as `source-caution` |
| `src_table`, `row` | table and page; zero-based row of the transcribed table (`transcriptions_v1_2/<doi>/table_N.csv`) |

## Classes

| class | rows | what |
|---|---:|---|
| `isopiestic_pair` | 1,367 | molalities of two solutions in isopiestic equilibrium (`value`: test solution, `value2`: reference salt); no osmotic coefficient is computed |
| `gas_solubility_coefficient` | 966 | Ostwald and Bunsen coefficients, whose conversion needs a gas partial pressure the paper does not give |
| `apparent_molar_volume` | 706 | apparent and partial molar volumes [cm3/mol] |
| `gas_solubility_other_basis` | 468 | solubility as g per 100 g solvent, cm3 per litre of solution, mass percent, mole fraction on a basis the mapping states |
| `enthalpy_of_dilution` | 391 | enthalpies of dilution, with the two molalities |
| `density` | 358 | densities of solutions of salts outside the six-ion set, and density differences |
| `mixture_volume` | 233 | molar and excess volumes of water + gas mixtures |
| `other` | 203 | salt content of steam, hydrocarbon solubility in ppm by mass, fluid composition at the end of high-temperature runs |
| `compression` | 164 | bulk compression and dv/dP |
| `enthalpy_of_dissolution` | 87 | enthalpies of dissolution of salts in water |
| `heat_capacity` | 74 | specific and apparent molar heat capacities, in the paper's units |
| `water_activity` | 39 | water activities and vapor pressures of salt solutions at high temperature |
| `henry_constant` | 37 | Henry constants as pressure per mole fraction |
| `water_vapour_enhancement` | 14 | enhancement factor of water in a gas |

Excluded even from this tier: critical loci and phase boundaries, synthetic
filling compositions, gas-phase mixtures with no stated composition, and every
row with no stated pressure outside the three classes above.

## Using it

```python
import pandas as pd
s = pd.read_csv("supplementary/supplementary_measurements.csv", keep_default_na=False)
iso = s[s.property_class == "isopiestic_pair"]
```
