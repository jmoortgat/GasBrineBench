# Inter-source consensus

Where several independent sources measured the same property at about the same conditions, how far is each source
from the others? Two files answer that, one per row and one per source. They are **descriptive metadata**: they
change no value and no quality code, and they say where sources disagree, not which one is right.

Produced by `tools/builders_v1_2/gbb12_consensus.py` (pandas and numpy only):

```
python3 tools/builders_v1_2/gbb12_consensus.py --repo . --out data/consensus
```

## What is compared

The rows in the default view (no default-excluded flag, no `lle-regime`) of the families `solubility`
(`solubility_molality`), `y_h2o`, `rho`, `phi_osm`, `psat_ratio`, `thermo_brine`, `dh_sol`, `visc` and `rho_gas`, grouped by
property and gas. A *source* is the citation id of `SOURCES.md`; rows of the same source are never compared with each
other.

**Strict statistic** (columns `reference`, `mean_other`, `sd_other`, `n_other_sources`, `spread_other`, `rel_dev`).
The neighbors of a row are the rows of other sources with |dT| <= 1 K, |dP| <= 2 % (ignored if a pressure is blank) and
every ion molality within 2 % (gas-loaded families: also `m_gas`). Each neighboring source counts once, through the
median of its own neighboring rows. `reference` is the median over those sources, `mean_other` and `sd_other` their mean
and sample standard deviation (`sd_other` needs two sources), `spread_other` their (max - min) / |reference|, and
`rel_dev = (value - reference) / |reference|`. These are the tolerances of the cross-source quality rule in
`data/QUALITY.md`.

**Smooth statistic** (`ref_smooth`, `n_other_smooth`, `n_points_smooth`, `rel_dev_smooth`). The same idea for sources that
rarely coincide exactly: a leave-one-source-out, distance-weighted local-linear fit through the *other* sources' rows within
+-10 K, +-0.35 in ln P and +-20 % in each ion molality, in T, ln P and the ion molalities (response ln value when all
values are positive). It interpolates only: if the row lies outside the range of the other sources' rows in any variable it
gets no value.

**Outliers.** `outlier_strict` / `outlier_smooth` mark rows whose relative deviation exceeds max(3 x the pooled robust
scale of the property, 10 %) **and** that have at least two other sources, because with a single other source the
disagreement cannot be assigned to either side. `consensus_outlier` is either flag. The pooled robust scale is
1.4826 x MAD of `rel_dev` over all compared rows of the property.

`consensus_by_source.csv` gives, per source and property: rows in the default view, number compared, the **median
signed relative deviation** (a source that reads high or low), the robust scale of its deviations, the share beyond
10 %, and the outlier counts, for each statistic.

## What it shows

Pooled robust scale of the strict relative deviation (sources agree to about this): solubility 3.8 %, `psat_ratio`
1.0 %, `rho` 0.1 %, `dh_sol` 0.6 %, gas-phase water content 9 %, apparent molar heat capacity 28 %.

Of the 17,942 rows in the comparison, 1,830 (10.2%) have an independent neighbor source under the strict rule and 3,691 (21%)
under at least one of the two statistics: different laboratories rarely measure the same salt at the same molality and state.
Coverage by family is in the table the script prints. `phi_osm`,
`visc` and the gas-loaded densities have no overlap at all; their quality rests on the cross-checks made at extraction.

## Limits

* Sources are citation ids, not laboratories. Two papers of one group count as two sources, so agreement between them is
  not independent confirmation (`data/README.md` already notes this for individual pairs, for example the Chapoy and Mohammadi papers).
* The tolerances put a floor under the resolution of about 3 % for solubility, which changes by 1-2 % per K.
* The smooth statistic can be misled where a property is not smooth (near a critical point, across a phase boundary).
  The two statistics agree with correlation 0.75 on the rows that have both.
* Row ids are the zero-based position in the family CSV of this release; they are not stable across releases, `dataset_id`
  with the state columns is.

## What it found while it was built

The 330 rows it listed in a first pass were each checked against the printed tables of their papers: 258 matched (genuine
inter-laboratory scatter, or a comparator that was itself wrong), 21 could not be checked (paper unavailable), and about 50
were defects of the database, corrected as listed in `CHANGELOG.md` and `LEDGER.md`. After those corrections (and the removal of a mislabeled duplicate, below) 175 rows remain
listed. Rows coded quality U are compared with their neighbors but never used as neighbors.

Further defects of v1.1.1 and v1.2 found by it: five CHABAB(2020) points, the Millero oxygen data printed in two papers (19 states) and eight Yarrison thesis values that repeat published values to the last digit; the salt-free reference densities of three density papers; and water + hexadecane + CO2 rows of Brunner et al. (1994) built as binary (all in `LEDGER.md`). One more defect of v1.1.1: 612 rows labeled WANG(2014) agreed with Wang, J. et al. (2019) to rounding at 306 states, which two
independent laboratories cannot do; they are a mislabeled copy of the 2019 tables and were removed (`LEDGER.md`).

Two defects of the first v1.2 build were found by the comparison alone:

Two defects in the first v1.2 build were found by this comparison, not by any other check, and are fixed in the release:
Debelius (2009) oxygen solubilities in seawater were a factor 10^6 too small (a micromole-to-mole conversion applied
twice) and, once that was corrected, a factor 4.8 too large because they are air-saturated values stored as if the
oxygen partial pressure were 1 atm; they now agree with Fox (1909), Cosgrove (1981) and Morrison (1952) within 3 %.
