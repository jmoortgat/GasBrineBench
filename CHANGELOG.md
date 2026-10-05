# Changelog

## 1.2.0 — 146 further papers, three new families, a supplementary tier

**Not yet archived.** The Zenodo version DOI is minted at release.

v1.1.1 held 11,537 rows from 111 papers. v1.2.0 holds **26,815 rows from 249
published sources** (+15,278 rows, +146 papers, -8 sources of v1.1.1 that no longer count: 5 removed, 3 merged or relabelled) in 11 families, and a separate
supplementary tier of 5,174 measurements from 107 tables.

**How the new rows were made.** The papers were found by a documented
literature search (`search/` in the maintainers' work area; summarised in the
data descriptor). **No v1.2 value was typed by hand.** Each table was
transcribed from the paper twice, independently, from the page image and the PDF text layer
(the full statement of the tools used is added at release); the two
transcriptions were compared number by number by a script, every disagreement
was settled against a high-resolution crop of the page (or an independent OCR
of it), and a separate mapping file per table
(`transcriptions_v1_2/<doi>/mapping_N.json`) records how each column becomes a
schema column. A further, separate pass then audited every mapping
against the paper, and its proposals were applied to the mappings under written
rules. The v1.0-v1.1 transcriptions (`transcriptions/`) were typed by hand and
are untouched. Rows are built by `tools/builders_v1_2/` from
those files alone, with no hand-edited value, and the build is reproducible
byte for byte from this repository (`python3 tools/builders_v1_2/gbb12_build.py
--extract transcriptions_v1_2 --out OUT`). A row is held back, with the
reason on record, whenever its conversion would need a model, an assumed
density or an assumed pressure; of 477 extracted tables, 353 contribute rows.

Source labels: the bare labels `Guo` (262 rows of Guo et al. 2014, CO2 in pure water) and `TONG` are pinned to their papers in `tools/make_sources.py` (`Guo` had resolved to the 2016 NaCl paper); this removes two duplicate bibliography lines, so the database cites 255 distinct works.

Sources whose papers could not be obtained: the rows of four of them (Culberson and McKetta 1950, Culberson, Horn and McKetta 1950, Ipatev 1934, Devaney 1978; 210 rows, all test-only and none in the reliable set) were removed, and the two others were re-cited to the paper that was compared with them (KOBAYASHI(1951) to Kobayashi and Katz 1953, Table VI; SULTANOV(1972) to Price 1979, Table 2). `LEDGER.md` has the entries.

### Full row-by-row audit (2026-10-04)

Every one of the 27,051 rows then in the data was compared with its paper: 48 independent audit passes, one packet of papers each, read the printed
tables (page images and PDF text layers) and compared each row digit by digit with a script they wrote from their own transcription. Verdict per row:
correct, minor (a printed temperature or pressure that differs from the stored one by up to 1 K or 2 %), major, or unverifiable (paper or table not
available, or the paper does not settle the basis). 19,170 rows were correct, 6,606 minor, 501 major and 774 unverifiable. The same passes then wrote a
correction list: every stored temperature re-keyed to the printed one (the older blocks stored nominal whole-kelvin isotherm temperatures), pressures
that were rounded to 0.1 bar re-keyed, nominal compositions replaced by printed ones where the paper prints them, molalities set to the printed
digits where the stored value sat 0.09 % low, and every unambiguous major corrected. 12,916 field corrections and 26 row removals were applied (and, separately, the 210 rows of four unobtainable sources removed; see above) (rows
that no printed point supports, or paper misprints that make a stored value physically wrong); each line is in `data/provenance/audit_corrections.csv`
with its reason, and `data/provenance/audit_status.csv` gives every row its status: `verified`, `corrected`, `not-verifiable` or `residual-difference`.
Corrections the paper does not settle (per kg solution against per kg water, nominal against actual composition) were not made.
The inter-source consensus statistic was recomputed afterwards: rows more than three robust scales from the other laboratories fell from 338 to 170.
A second, blind random audit of the corrected data (500 points, 540 independent readings, fresh, independent readers that had seen no earlier result) found 8 majors in 531 verifiable readings (1.5 %, 95 % interval 0.8-2.9 %; the first round, before the corrections, found 6.1 %); six of the eight are rows that already carry a flag or follow a documented derived-pressure convention, the other two are a paper that gives no concentration basis and a paper whose own mole-fraction and molality columns disagree (0.4 % after adjudication).
`gbb.load(reliable=True)` returns the rows that passed the audit (status verified or corrected, quality not U, no unsettled-convention flag; 20,899 rows), and the column `audit_status` is attached by `load` so that `audit_status=` works as a filter.
A new informational flag, `smoothed-values`, marks tables the authors state are smoothed or graphically interpolated.

### Added

* **Three families**: `rho_gas.csv` (density of CO2-loaded solutions, 951 rows),
  `visc.csv` (viscosity, 85 rows), `thermo_brine.csv` (apparent molar heat
  capacity, 692 rows); and 15,278 rows in total over the 11 families.
* **An optional `flags` column** on every family, `;`-separated, and an optional
  `m_gas` column in `rho_gas.csv` and `visc.csv`. `SCHEMA.md` defines the 16
  flags. `tag` is unchanged.
* **24 further single gases**, flagged `gas-out-of-scope` and dropped by the
  default loader.
* **`supplementary/`**: 5,174 rows in 14 classes (apparent molar volumes,
  enthalpies of dilution and dissolution, isopiestic pairs, mixture volumes,
  compressions, Henry constants on a molality basis, Ostwald and Bunsen
  coefficients, salt solutions outside the six ions, ...), each with the value
  and unit as printed. See `supplementary/README.md`.
* **`data/provenance/provenance_v1_2.csv`**: paper, table, row count,
  verification status, experimental method and caution for every v1.2
  `dataset_id`; **`data/provenance/citation_counts.csv`**: OpenAlex citation
  counts of every cited paper, retrieved 2026-10-03, now a column of
  `SOURCES.md`. Counts are metadata, not a quality measure.
* **`data/consensus/`**: for every row that other independent sources also measured at about the same conditions, the
  deviation from their consensus (median, mean and standard deviation of the other sources; a strict-tolerance and a
  leave-one-source-out smooth statistic), and per source the median signed deviation, its robust scale and the share beyond 10 %.
  3,691 of 17,942 rows in the comparison have a comparator; 175 rows are listed as consensus outliers (after the corrections below). Descriptive only: no
  value or quality code was changed by it. See `data/consensus/README.md`.
* **`transcriptions_v1_2/`**: the 353 tables, their mappings and the papers'
  metadata, for the 207 papers behind the families and the supplementary tier.
* **`bib/references_v1_2.bib`**: Crossref records of the new sources.
* `gasbrinebench`: `exclude_flags`/`flags` filters, `OTHER_GASES`, `FLAGS`,
  `DEFAULT_EXCLUDED_FLAGS`; `load()` drops default-flagged rows.

### Changed

* **Defaults.** `load()` returns 23,090 rows: it drops the 354 `lle-regime` rows
  (144 propane rows of v1.1.1, 210 added: propane, butanes, ethane, and CO2 below
  its critical temperature) and every row carrying `gas-out-of-scope`,
  `hydrate-regime`, `condensed-phase-uncertain`, `fugacity-as-pressure`,
  `subfreezing`, `volume-basis-uncertain` or `pressure-unstated`. Pass
  `exclude_tags=None, exclude_flags=None` for all 26,815.
* **Quality codes** of solubility rows were recomputed over the enlarged set with
  the v1.1.1 rules (`data/QUALITY.md`, *v1.2 addendum*): 166 rows rose T to R
  because a new independent source agrees with them, and 44 rows fell R to T
  because a new source lies outside the 5 % band around them or a corrected value
  changed a cluster. No row went to U by rule; 62 rows (v1.1.1 solubility and water-content rows, and the low-pressure MOHAMMADIAN rows) were set to U by hand
  after the check against the papers (below), and 138 new rows are U because their
  mapping records an author flag or an unresolved doubt.
* **Chapoy 2004, split in two.** v1.1.1 cited two papers under one key,
  `CHAPOY(2004)`: the 32 methane-water rows (Fluid Phase Equilib. 220, 113,
  10.1016/j.fluid.2004.02.010) and the 78 propane-water rows of `c3h8_water`,
  which are Chapoy, Mokraoui, Valtz, Richon, Mohammadi & Tohidi, Fluid Phase
  Equilib. 226, 213 (2004), 10.1016/j.fluid.2004.08.040, and were being cited as
  the methane paper. The propane rows now read `CHAPOY(2004d)` and resolve to
  their own record. No value changed.
* `tools/make_sources.py`, `tools/validate.py`: read the second bib file, take
  the citation counts, and validate the new families, the `flags` column, the
  gas vocabulary and the supplementary file. Two source keys that the extra
  bibliography made ambiguous (`king`, `SAKO`) are pinned in
  `SOURCE_KEY_FIXES`.
* `tests/`: counts and conventions that described v1.1.1 now describe v1.2; the
  charge-imbalance test treats the seawater-matrix rows separately (bromide and
  bicarbonate are not carried).
* `README.md`, `SCHEMA.md`, `data/QUALITY.md`, `LEDGER.md`: updated.

### Corrections to v1.1.1 rows, found by checking the consensus outliers against the papers

The 330 rows listed by the first consensus pass were each read against the printed table of their paper. Most are real
inter-laboratory scatter. The rest were defects, now corrected in v1.2 (each is a line of `LEDGER.md`; the corrections are
code in `tools/builders_v1_2/gbb12_corrections.py`, each guarded by the value it expects to find). v1.1.1 itself is unchanged.

* **Wrong values:** YOKOYAMA(1988) CH4 water content (6 rows, molar mass of CO2 used for CH4, values 2.75 times too high);
  CHAPOY(2003) CH4 water content (30 rows, replaced by the authors' own Corrigendum values: the original table was withdrawn
  because sampling adsorption made it too low); Valtz (2004) 288 K isotherm (14 rows, the transcribed column held P/1000);
  ADDICKS(2002) (4 rows, wrong table column); TAKENOUCHI(1964) one digit; WIEBE(1934) H2 (all rows 1.3 % low, wrong molar volume
  for the paper's S.T.P.); MICHELS(1936) and MULLER one pressure each.
* **Wrong states:** nominal isotherm temperatures stored instead of the printed ones for FROST(2013), AWAN(2010), OU(2015),
  PRICE(1979), SAKO, GILLESPIE(1980) and CHAPOY(2005) (0.1 to 1.3 K). The same pattern, at 0.1 to 0.8 K, remains in other
  hand-transcribed isotherms (for example LEKVAM(1997)); the effect on a solubility is a few per cent at most and no row was
  found whose flag it caused.
* **The same data twice:** CHABAB(2020) five points (the 303 K label hid six-digit copies of Chabab 2021, which the v1.1.1 duplicate pass
  missed); the Millero, Huang and Laferiere oxygen data at 25 C, printed in both the Geochimica (2002) and the Marine Chemistry (2002) paper
  (19 states identical to the last digit: 38 rows of the Geochimica copy removed); the Yarrison thesis (8 rows that repeat the journal values).
  Found by listing every pair of sources whose rows at the same state agree to five digits.
* **Calculated references, not measurements:** the salt-free density rows of KUMAR(1986), ROGERS(1982) and ROMANKIW(1983) (the pure-water
  density used for apparent molar volumes; Kumar and Rogers print identical values at six states, and Romankiw states they were taken from Kell);
  34 rows held.
* **A ternary system built as binary:** BRUNNER(1994) water + n-hexadecane + CO2: the 14 rows whose vapour also contains hexadecane are held;
  only the four binary water-CO2 points remain.
* **Not measurements:** SUSAK(1980) (output of a USGS program extrapolated beyond its validity) and SACHS(1995) (calculated
  from literature correlations) are flagged `calculated-not-measured` and dropped by the default loader.
* **Removed:** the DOHRN(1986) point at 523 K and 200 bar, whose temperature does not exist in the paper; and the 612 rows labelled
  `WANG(2014)` in `co2_part1`, which are a mislabelled copy of Wang, J. et al. 2019 (J. Chem. Eng. Data 64, 2484) Tables 6-8 (306 points of CO2 in
  1, 2 and 3 m NaCl, 303-353 K, 3-30 MPa, agreeing with the printed molalities to rounding). Wang, Shen, Hu & Yu 2014 measured synthetic formation
  brines at 318-348 K and 80-110 bar. The two had been counted as independent sources, which inflated the R code: with the copy removed, the
  solubility R count falls from 591 to 503 retained plus 166 newly corroborated.
* **Hydrate regime / quality U:** CULBERSON(1951) two hydrate-region points; TODHEIDE water contents printed as the complement of
  99 mol% CO2; a copied CARROLL(1998) block; CAMPOS(2010) (not Henry-law consistent); other points listed in `LEDGER.md`.
* **Moved out of the benchmark:** KISHIMA(1984) H2 (52 states): the concentrations were measured at an H2 fugacity fixed by a
  buffer, not at the total pressure the schema carries; they are in the supplementary tier (104 rows).
* **Not changed, 21 rows unverifiable:** SULTANOV(1972), IPATEV(1934), DEVANEY(1978), LUCILE(2012), CHAPOY(2004b): the paper was
  not available; the database equals the hand transcription for every one.

### Corrections found while building v1.2

These are defects of the first v1.2 build, not of v1.1.1; none was in a published release.

* **Debelius (2009) oxygen solubility in seawater, 308 rows.** A micromole-to-mole conversion was applied twice (values 10^6 too
  small), and, once corrected, the values were a factor 4.8 too large because they are air-saturated (O2 at 0.20946 of the air at
  1 atm) and had been stored as if the O2 partial pressure were 1 atm. Found by the inter-source consensus check; they now
  agree with Fox (1909), Cosgrove (1981) and Morrison (1952) within 3 %. The correction also adds the mole-fraction sibling rows (+308).

### Not in the database, on purpose

* **One row held after a report from a model-comparison study:** MARCUS(1988), 25 degC, the row printed as 0.34 m NaCl + 0.99 m MgCl2 "saturated with halite", p = 1.35 kPa (ratio 0.43). Five models give about 0.92 for that composition. The composition cannot be halite-saturated, and the pressure fits a solution of about 4 m MgCl2 like its neighbours, so the MgCl2 molality is probably misprinted (3.99?). The row is held with the reason on record, not corrected.
* **Any measurement without a stated pressure** is excluded: no liquid density,
  density difference or viscosity whose paper gives no pressure, unless the
  property is conventionally measured without one (see `pressure-unstated`).
* **Gas mixtures**: 545 rows of gas-phase mixtures and 194 rows of tables with two
  dissolved gases were extracted and verified but have no home in a schema
  without a gas-phase composition column; they are in `LEDGER.md`.
* **1 v1.1.1 row removed** (DOHRN(1986), above) and **172 exact duplicates** of rows from the same source (the same table printed
  twice, or a thesis and its paper) are not repeated.

## 1.1.1 — three corrected mixed-brine ion vectors

Three recipes carried ion vectors that do not follow from their source
tables. All three were found by re-deriving every one of the 19 mixed-brine
compositions from the source papers, not by any internal check: each recipe
CHARGE-BALANCES, because in every case chloride was computed from the
cations, so the balance closes around whatever the cations say and cannot
detect an error in them. Recipes are given as
`m_Na m_Cl m_K m_Ca m_Mg m_SO4`, mol per kg of water.

**TEYMOURI_2017 (mixed brine, 18 measurements).** Magnesium was low by a
factor of 10.15.

    was  3.983 4.737 0.0422 0.326 0.029 0.000
    now  3.987 5.270 0.0421 0.326 0.294 0.000

The source table (Mousavi Belfeh Teymouri 2017 thesis Table 3.29, reproduced
identically as Mousavi et al. 2024 Table 5) gives NaCl 258.13, CaCl2 40.09,
MgCl2 31.05 and KCl 3.48 g "in 1 lit of water" at a stated total salinity of
23.1 wt%. Those two statements are not consistent with each other — taking
"1 lit of water" as 1 kg gives 24.97 wt% — and the transcription resolved it
by trusting the stated salinity, which puts 1.1077 kg of water behind the
quoted masses. On that basis NaCl, CaCl2 and KCl reproduce the carried values
to better than 0.5 % (factors 0.9018, 0.9025, 0.9040); MgCl2 gives 0.2944
against the 0.029 carried. Ionic strength 5.091 -> 5.890 mol/kg, so this is
no longer the set's most concentrated recipe by a small margin but by a
large one. NOTE: because the source table is self-inconsistent, the whole
recipe still carries an ~8 % basis ambiguity; the alternative reading (wt%
per kg of solution) would give NaCl 4.3166 rather than 3.9873.

**LI_2004 (6 measurements).** The entry mixed two bases: K, Ca, Mg and SO4
were molalities, Na and Cl were left as molarities.

    was  1.405 1.483 0.0120 0.049 0.023 0.040
    now  1.453 1.532 0.0120 0.051 0.024 0.041

Chloride is now the measured 52,640 mg/L on the molar mass 35.453 rather than
a rounded 35.5, converted to molality with 1000/(1061.9 - 92.95) = 1.03204.
Sodium remains a charge-balance value rather than the measured 29,140 mg/L:
Table 1 of the source does not charge-balance (8.94 % cation deficit) and its
reported ions sum to 88,570 mg/L against a stated TDS of 92,950. Sodium here
is therefore a reconciled quantity, not a measured one.

**WANG_2014 Liujiagou (16 measurements).** Chloride came from a typo in the
source's mass column.

    was  0.435 1.036 0.002 0.286 0.022 0.008
    now  0.359 0.960 0.002 0.286 0.022 0.008

Table 1 of the source gives Liujiagou chloride as 36,762.84 mg/L and
960.08 mmol/L, which implies a molar mass of 38.291 g/mol; the other three
samples in the same table all give exactly 35.500. Charge balance identifies
the mass entry as the bad one (the molarity column leaves -5.85 %, the mass
column -13.27 %). Sodium is re-derived by charge balance against the good
chloride, which is the convention two of the other three samples in this
cohort already follow.

**Not changed, but recorded.** PORTIER_2005 is tabulated per litre of
solution, so every ion in it is about 1.1 % below its true molality; its
chloride additionally absorbs 386 mg/L of bicarbonate, which has no column in
the six-ion schema. ELMAGHRABY_2012's source labels its brine both "5 wt%
NaCl and 1 wt% KCl" and "0.856 mol NaCl ... per kilogram water", which cannot
both hold; the carried values match the printed molalities. Neither is a
transcription error, and both are uniform across their recipe.

## v1.1.0 — 2026-09-18

### A ternary family: CO2 + CH4 + water

93 rows from 34 measured states, three sources: Dhima (1999) at 344 K,
Al Ghafri (2014) at 323 and 423 K, Qin (2008) at 376 K. Pressures 20 to
1,000 bar.

**Why it is a separate family rather than rows in `solubility.csv`.** Every
other family describes a system with one gas, so the gas-phase composition
is implied and needs no column. A ternary measurement does not work that
way: the same water at the same (T, P) dissolves different amounts of CH4
and CO2 depending on how the gas phase is split between them, and that split
is an independent state variable. Rather than add a column that would be
blank for the other 11,444 rows, `ternary.csv` carries the standard schema
plus one column, `y_co2_dry` — the CO2 mole fraction of the gas phase on a
water-free basis. `tools/validate.py` declares that in `EXTRA_COLS`; any
other family still rejects a column outside the standard set.

The row grammar is unchanged, one measurement per row: `gas=ch4` /
`gas=co2` with `property=xc_saltfree` for the two dissolved species, and
`gas=co2-ch4` with `property=y_h2o` for the water content of the mixed gas.
`co2-ch4` is the only new gas code and appears only on those rows, where the
measurement is a property of the mixture rather than of either component.

**No ternary measurement in brine exists.** All ion columns are zero. The
upstream CCB tree holds only solver output, and the upstream builder records
that no experimental dataset is present there. The ion columns are carried
so that such data would need no schema change.

**Not a duplication of Qin's binary rows.** Qin (2008) already appears in
`solubility.csv` and `y_h2o.csv` under `ch4_water_binary`. Those are his
CH4-H2O binary measurements and are different data: at 375 K / 302 bar the
binary gives x_CH4 = 0.0030, while the ternary at 376 K / 303 bar gives
0.00104-0.00188 depending on the gas split, lower because CO2 displaces CH4.

All 93 rows are `quality = T` and `tag = test-only`. The three sources sit at
different temperatures, so no two describe the same state and the
cross-source rule that awards `R` cannot fire; and the ternary set has only
ever been used to validate the mixed-gas capability, never as a fit target.

Two bibliography records added, both verified against Crossref rather than
recalled: Dhima et al., *Ind. Eng. Chem. Res.* **38**, 3144-3161 (1999),
doi:10.1021/ie980768g; Al Ghafri et al., *J. Phys. Chem. B* **118**,
14461-14478 (2014), doi:10.1021/jp509678g.

  rows      11,444 -> 11,537
  sources      109 -> 111
  families       7 -> 8

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
