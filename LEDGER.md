# Quality ledger

Every correction, deduplication, quality-code upgrade/downgrade, and
removal is recorded here with its justification. Regenerated entries
from automated passes are marked [auto].

The per-row justification record that this ledger summarises lives in
`data/QUALITY.md`, which is reproduced verbatim from the pass that assigned
the codes.

## 2026-09-18 — corrections carried into v1.0

Data values changed in this entry, which the 2026-09-14 entry could not say.
Every change was checked against the primary paper before it was applied; the
per-row record is in `data/QUALITY.md` and the narrative is in `CHANGELOG.md`
under v1.0.0. Row counts moved 5,846 -> 11,444 and sources 82 -> 109.

- **Duffy (1961), 48 rows: divalent molality in the wrong column.** The files
  carried the cation molality one column to the left, so `EXP_CaCl1_T303K.txt`
  read Na=0, Cl=2.8, K=1.4 for a 1.4 m CaCl2 brine — a composition that fails
  charge balance at 1.4 against 2.8 and lands exactly if the 1.4 is moved to
  Ca. Duffy's system is CH4–H2O–NaCl–CaCl2 and contains no potassium, which
  settles it. Moved to `m_Ca`; the directory was renamed `303K_X` -> `303K`.
  The superseded copies were removed from `transcriptions/` on 2026-09-18
  after the diff confirmed they differed from the corrected files in exactly
  the misplaced column and nothing else.

- **Nine isotherms at the wrong temperature.** Temperature was taken from the
  integer-kelvin directory name. That cannot represent a non-integer isotherm,
  and it maps two different measured temperatures onto one label whenever a
  Fahrenheit-grid source shares a directory with a Celsius-grid one. Files may
  now declare their own temperature on the source line with a free-text
  justification, so the claim is auditable. Applied only where the paper was
  read: Portier & Rochelle (2005) Table 2 at 18 and 37 degC; Jacob & Saylor
  (2016); Bastami (2014) figure legends; Culberson & McKetta (1951) Table I
  and Olds et al. (1942) at 160 and 340 degF; O'Sullivan & Smith (1970) at
  51.5, 102.5 and 125 degC.

  O'Sullivan was found from the data rather than from a paper: the same work
  supplies N2 rows through the PDF-extraction path, which had preserved
  324.65/375.65/398.15, while its CH4 rows came through the directory path and
  had been snapped to 323/375/398. The paper then confirmed the three values.

- **16 quality codes downgraded R -> T, as a consequence of the above.**
  O'Sullivan (6 rows) and Gao (1997) (6 rows) had been credited as
  corroborating each other at 323 K; O'Sullivan measured at 324.65 K.
  Culberson (2 rows) and Amirijafari (1972) (2 rows) likewise at 343 K;
  Culberson measured at 344.26 K. No row's value changed; what changed is that
  four groups stopped being counted as independent agreement, because they
  never were.

- **11 rows recovered that no build had ever read.** `443K/EXP2_T444K.txt`
  (Olds 1942, 340 degF) is filed in a directory named `443K`, and every
  builder globbed `EXP*_T{directory}K.txt`. The file therefore matched nothing.
  Its water-content rows appear in no other source.

- **One file excluded rather than read.** `CO2/CPA/PR/T478K/EXP1_T473K.txt` is
  byte-identical to `T473K/EXP1_T473K.txt` (Todheide & Franck 1963, 200 degC),
  a stray copy in the wrong directory. Reading it would have duplicated eight
  rows at a temperature nobody measured.

- **The superseded `CO2/CPA/SRK` tree is no longer extracted.** It and
  `CO2/CPA/PR` hold the same compilation filed under two cubic backbones. They
  were compared path by path: 10 of 89 shared paths differ, and in every case
  PR carries data SRK lacks — SRK has `X` where Hou (2013) Table 2 records
  y_CO2 = 0.97189 at 323.15 K / 1.089 MPa, and SRK's 538 K file stops at
  2500 bar where Todheide & Franck run to 3500. PR is canonical; SRK would
  have silently lost three y_h2o points. Transcriptions 819 -> 710.

- **Promotions, not corrections.** The salt-free CO2–H2O and CH4–H2O binaries
  (~1,400 rows), the Susak (1980) block above 573 K (64 rows), every isotherm
  directory rather than a hard-coded three (1,209 rows), and the `_X<author>`
  files, which had been skipped as duplicates of the canonical file at the same
  slot and are in fact a second author at a taken slot (115 rows). No value was
  altered; these had been transcribed and left unread.

## 2026-09-14 — the data brought into the repository

No data value changed. The seven family CSVs, their two provenance documents,
the builder scripts and the 819 raw transcriptions were moved in from the
working trees they were built in, so that this repository is the whole record
rather than a description of one. What is recorded here is the set of
*documentation* defects that surfaced when the scaffold met the real data.

- **The schema specified a per-row `provenance` column. The database has no
  such column and never had one.** What it carries in that position is `tag`
  (`fit-eligible` / `test-only` / `lle-regime`), which records how a row may be
  used, not where it came from. `SCHEMA.md` was written before the data
  existed and guessed wrong. It has been corrected to describe the column that
  exists, and to say where provenance actually lives: per `dataset_id`, in the
  provenance table of `data/README.md` (paper, table or figure, page, unit
  convention, deliberate omissions) and in `transcriptions/`, the typed source
  tables themselves. **No data was reshaped to fit the schema**; the schema was
  corrected to describe the data.
- **`eps_r` was an undeclared property.** Thirteen rows of NaCl static
  permittivity at 298.15 K are in the database as an extension family. The
  property vocabulary now declares it, and the README states plainly that
  those rows are not gas–brine equilibrium targets.
- **`psat_ratio` rows carry a blank `P_bar`, legitimately.** The property is a
  ratio of saturation pressures at one temperature: the pressure is the
  measured quantity and is carried in `value`. The validator's blanket
  "P_bar must be numeric" rule would have rejected all 21 rows of real data.
  It now permits a blank P only for `psat_ratio` and rejects it everywhere
  else.
- **The validator compared `source` cells to bibtex keys directly**, which no
  row satisfies: the `source` column holds curation spellings
  (`ALGHAFRI(2012) / EXP_NaCl_T298K.txt`, `Chabab2021_JCED66_T3_tech1`) that
  `tools/make_sources.py` owns the mapping for. The check now resolves through
  that same mapping, so it tests the invariant the manifest reports — every
  row reaches a real published source — rather than a spelling convention the
  data was never held to.
- **Three exact value coincidences between different sources are real data,
  not duplicates.** Ipatev (1934) and Jung (1968) both print x(H2) = 0.000574
  at 473 K and 36 bar; Takenouchi and Tödheide both print y(H2O) = 0.546 at
  573 K and 300 bar. Agreeing to the precision they printed is the
  cross-author corroboration that earned those rows their `R` codes. The
  duplicate check now fails only on the defect it was written for — the *same*
  source contributing the identical point twice, of which there are none — and
  reports cross-source coincidences without rejecting them. Portier (2005)
  likewise contributes 32 replicate measurements at 16 repeated nominal
  states; those are repeat experiments with different values and are kept.

The validator was strengthened in the same pass, not relaxed: it now also
checks that `gas` is present for gas properties and empty for brine-only ones,
that `uncertainty` is numeric and non-negative where given, that `value` is
finite, that no undeclared columns appear, and that the `tag` vocabulary is
respected. Ten deliberately corrupted copies of the data were checked to
confirm each rule fires.

## 2026-09-13 — bibliographic provenance closed out

No data value changed. The work was entirely on the `source` → citation
mapping, and it is recorded here because it changes what the manifest
asserts about where 2,489 rows came from.

- **Coverage** went from 3,357/5,846 rows (57.4 %) carrying a real
  reference to 5,846/5,846 (100 %). Four placeholder citations covering
  1,273 rows were replaced with verified records; 23 source keys with no
  bibliographic record at all, covering 1,216 rows, were resolved.
- **Every identification was made from the primary paper**, read from the
  local literature trove, and checked against the rows' own temperature,
  pressure, salt and composition grid. Every DOI was then confirmed
  against a Crossref record whose title, journal, volume and year match
  the paper identified. Nothing was recalled from memory.
- **Seventeen `source` cells name their paper wrongly** — a misspelt or
  truncated surname, a missing year, an online-first year, or a thesis
  year in place of the published article's. These are rewritten by
  `tools/make_sources.py` before matching, and each rewrite is printed
  with its evidence in the *Source-key corrections* section of
  `SOURCES.md`. The CSV cells are left untouched: their `source` column
  is copied from upstream curation artefacts and would be restored by the
  next rebuild, and two of the strings are asserted verbatim by the
  benchmark's test suite.
- **144 CO2-in-brine rows were cited as the wrong Hou paper.** The keys
  `Hou2013_JSCF78_T2` and `Hou2013_JSCF78_T3` name J. Supercrit. Fluids
  volume **78** — Hou, Maitland & Trusler's (CO2 + H2O + NaCl/KCl)
  study — but without the `b` they resolved to the same group's
  (CO2 + H2O) binary in volume 73. The rows are 2.5 and 4 mol/kg NaCl
  and KCl at 323.15/373.15/423.15 K: Tables 2 and 3 of the brine paper,
  whose gas-phase water content was already keyed `HOU(2013b)` in
  `y_h2o.csv`, and whose transcription module says as much in its own
  docstring. All 216 rows of that paper now share one citation, and the
  32 genuinely-binary y_H2O rows keyed `HOU` now point at volume 73.
- **`OSULLIVAN(1969)` and `OSULLIVAN(1970)` were the same paper** entered
  twice. O'Sullivan & Smith (1970) measured both nitrogen and methane in
  water and in aqueous NaCl over one grid; the 32 methane rows and the
  102 nitrogen rows now share a single citation.
- **Nothing was asserted on author-and-year alone.** `MOHAMMADI(2004)`
  and the bib record `Mohammadi2004eth` are the same authors in the same
  year but different papers; the 22 water-content rows were matched to
  Mohammadi et al., *Ind. Eng. Chem. Res.* **43**(22) 7148 only once the
  paper itself was read and its stated 282.98–313.12 K / 2.846 MPa and
  282.93–293.10 K / 2.99 MPa ranges were found to reproduce the rows'
  own 282.93–313.12 K and 5.06–29.9 bar span exactly.
- **Two generator defects were fixed** in the course of this. Bibtex keys
  whose variant suffix is longer than one letter fell out of the exact
  index and were being rescued by a looser lookup that could not tell
  `Mohammadi2004` from `Mohammadi2004eth`; and `\ce{...}` in a title was
  being read as a cedilla, which is where the manifest's old `eCO2` and
  `eSrCl2` came from.
- **Six works have no DOI** and are reported as such: two doctoral theses
  (Kobayashi 1951, Teymouri 2017 — the latter with its repository
  handle), two association research reports (Gillespie 1980, Devaney
  1978 — the former with its OSTI record), and two papers in journals
  never retrospectively registered (Umano & Nakano 1958, Ipatev 1934).
  No substitute identifier was supplied for any of them.
- **Umano & Nakano (1958) is recorded without a title.** The copy held is
  the reprint in IUPAC Solubility Data Series volume 24, whose house
  style omits titles, so none is known and none was invented.

## 2026-10-03 — v1.2.0: what was left out, merged, corrected or flagged

Every row extracted and verified for v1.2 that does not appear in a benchmark family is listed here with the reason, and every change to a v1.1.1 row. v1.1.1 itself (tag and Zenodo record) is unchanged.

Corrections to the first v1.2 build (no v1.1.1 row involved): MARCUS(1988) row 3 held (probable misprint of the MgCl2 molality; reported by a model-comparison study); DEBELIUS(2009) oxygen solubilities corrected (double micromole conversion; air-saturation not applied); the salt-free reference densities of KUMAR(1986), ROGERS(1982) and ROMANKIW(1983) held; the ternary water + hexadecane + CO2 rows of BRUNNER(1994) held. All but the first were found by the consensus check.

| action | rows | reason |
|---|---:|---|
| excluded | 545 | gas-phase mixture: the gas-phase composition has no column in the database |
| excluded | 194 | mixed-gas table (two dissolved gases): the gas-phase composition has no column in the database |
| flagged calculated-not-measured | 502 | USGS open-file report 80-371 prints output of a TI-59 program (Haas 1978 equation, stated valid to 10,000 psi), not measurements; extrapolated cells to 623 K and 20,000 psi include non-physical values |
| flagged calculated-not-measured | 22 | the methane mole fractions of this surface-tension study are calculated from literature solubility correlations, not measured |
| flagged hydrate-regime | 4 | CULBERSON(1951): the 77 F values above 6800 psia are printed in parentheses as non-equilibrium (hydrate present) |
| quality set to U | 2 | AWAN(2010) Table 8 prints x2 = 2.1e-4 and m2 = 0.013 mol/kg for one point, which disagree by 11 % |
| quality set to U | 30 | CAMPOS(2010): the data are not Henry-law consistent (x/P rises 2.5 times between 1.1 and 6.4 bar) |
| quality set to U | 14 | CARROLL(1998): the printed 125 C block repeats the 75 C block (seven identical solubilities, two pressures differ); a copied block is likely |
| quality set to U | 1 | FROST(2013) 4.78 MPa, y = 0.441e-3 is 40 % off the authors' own y.P trend; a misprint is likely but not provable |
| quality set to U | 6 | MOHAMMADIAN(2015) Table 2 low-pressure points (<= 2.1 MPa) disagree with the paper's own pure-water Table 1 (0.250 against 0.315 at 2.1 MPa) |
| quality set to U | 1 | OLDS(1942): 35 % above the authors' own smoothed table value |
| quality set to U | 8 | TODHEIDE(1963): water content printed as the complement of y_CO2 = 99.0 mol% (+-1 mol%), so y_H2O = 0.010 +- 0.010 carries no information |
| removed | 172 | exact duplicate of a row of the same source (same state, same value) |
| removed (duplicate copy) | 10 | CHABAB(2020) (Multi_Salt curation of the 6 m NaCl data, rounded temperatures) repeats Chabab et al. 2021 Table 2 to six digits at 303.55 K; the 303.0 K label hid the match from the v1.1.1 duplicate pass, which removed the other nine points of the same copy |
| removed (duplicate copy) | 38 | Millero, Huang & Laferiere GCA 66 (2002) 2349 (25 C) and Mar. Chem. 78 (2002) 217 (5-45 C) report the same oxygen measurements: the GCA values equal those the Marine Chemistry paper tabulates at 25.35-25.7 C, to the last digit; the copy with the printed measur |
| removed (duplicate copy) | 8 | the Yarrison thesis (2007) repeats values of the journal data of Yarrison et al. (2006) to the last digit; the journal copy is kept |
| removed (v1.1.1 row) | 2 | DOHRN(1986): the paper (Dohrn & Brunner 1986, hexadecane-water-hydrogen, Table 1) has no 523 K data: its temperatures are 200, 300 and 350 degC. The stored state (200 bar, aqueous x_H2 = 0.0020) is the aqueous composition of both the 200 degC and the 350 degC  |
| removed (v1.1.1 row) | 612 | WANG(2014): mislabelled copy of Wang, Junliang et al. 2019 (J. Chem. Eng. Data 64, 2484), Tables 6-8: the 306 points are CO2 in 1, 2 and 3 mol/kg NaCl at 303-353 K and 3-30 MPa, the grid of that paper, and every one agrees with its printed molality to rounding |
| source corrected | 78 | CHAPOY(2004) -> CHAPOY(2004d): the 78 propane-water rows were cited as the methane paper Chapoy 2004 (10.1016/j.fluid.2004.02.010); they are Chapoy, Mokraoui, Valtz, Richon, Mohammadi & Tohidi, Fluid Phase Equilib. 226 (2004) 213-220, 10.1016/j.fluid.2004.08.0 |
| state corrected | 16 | 206 C = 479.15 K, stored 478.0 |
| state corrected | 2 | 300 F = 422.04 K, stored as the 423.0 K label |
| state corrected | 3 | CHAPOY(2005): printed T 292.7, 297.9, 297.6 K, stored as the 293.0 and 298.0 labels |
| state corrected | 6 | SAKO Table 1: T printed 421.4, 420.9, 421.4 K, stored as the 423.0 label |
| state corrected | 8 | SAKO Table 1: T printed as 421.4/420.9 K and 348.3/348.2 K, stored as the 423.0 and 348.0 labels |
| state corrected | 15 | T printed 283.89 K (Table 2), stored as the isotherm label 283.0 |
| state corrected | 18 | T printed 298.31 K (Table 2), stored as the isotherm label 298.0 |
| state corrected | 8 | T printed 298.78 K (Table 8), stored 298.0 |
| state corrected | 15 | T printed 313.11 K (Table 2), stored as the isotherm label 313.0 |
| state corrected | 8 | T printed 314.25 K (Table 8), stored 313.0 |
| state corrected | 15 | T printed 323.56 K (Table 2), stored as the isotherm label 323.0 |
| state corrected | 10 | isotherm is 285.15 K (Table 2), stored 286.0 |
| state corrected | 20 | isotherm is 493.15 K (Table 2), stored 494.0 |
| value corrected | 4 | ADDICKS(2002) Table 3: the 139.2 and 178.2 bar points took the Carroll column instead of x_exp |
| value corrected | 30 | CHAPOY(2003): the authors' Corrigendum (Fluid Phase Equilib. 230 (2005) 210-214, Table 1) withdrew the original water contents (sampling-circuit adsorption made them too low) and gives corrected values; 30 of 39 rows change, isotherm temperatures taken as prin |
| value corrected | 2 | MICHELS(1936) ch4_water_binary 373 K: pressure printed 146.4 atm = 148.3 bar, transcribed 147.3 |
| value corrected | 2 | MULLER co2_water_binary 433 K: pressure printed 2.588 MPa = 25.9 bar, transcribed 25.6 |
| value corrected | 1 | TAKENOUCHI Table 1, 200 C and 1400 bar: 69.4 mol% CO2 printed, so y_H2O = 0.306; transcribed 0.316 |
| value corrected | 14 | Valtz (2004) 288 K isotherm: the transcribed mole-fraction column was P/1000; replaced by the printed x1 of Table 6 (and T 288.26 K as printed) |
| value corrected | 80 | WIEBE(1934): printed cm3 (S.T.P.) per g water converted with 22.711 L/mol (1 bar) instead of the paper's S.T.P. (0 C, 760 mm; 22.414 L/mol): all values 1.3 % low |
| value corrected | 6 | YOKOYAMA(1988) Table II (mg H2O per g CH4): converted with the molar mass of CO2 (44.01) instead of CH4 (16.04); every y was 2.746 times too large |

Per dataset block:

| dataset_id | rows | action |
|---|---:|---|
| `ch4_water_binary` | 2 | value corrected: MICHELS(1936) ch4_water_binary 373 K: pressure printed 146.4 atm = 148.3 bar, transcribed 147.3 |
| `co2_water_binary` | 2 | value corrected: MULLER co2_water_binary 433 K: pressure printed 2.588 MPa = 25.9 bar, transcribed 25.6 |
| `co2_water_binary` | 14 | value corrected: Valtz (2004) 288 K isotherm: the transcribed mole-fraction column was P/1000; replaced by the printed x1 of Table 6 (and T 288.26 K as printed) |
| `ch4_water_binary` | 4 | value corrected: ADDICKS(2002) Table 3: the 139.2 and 178.2 bar points took the Carroll column instead of x_exp |
| `yh2o_ch4_binary` | 6 | value corrected: YOKOYAMA(1988) Table II (mg H2O per g CH4): converted with the molar mass of CO2 (44.01) instead of CH4 (16.04); every y was 2.746 times too large |
| `yh2o_co2_binary` | 1 | value corrected: TAKENOUCHI Table 1, 200 C and 1400 bar: 69.4 mol% CO2 printed, so y_H2O = 0.306; transcribed 0.316 |
| `h2_water_binaries` | 80 | value corrected: WIEBE(1934): printed cm3 (S.T.P.) per g water converted with 22.711 L/mol (1 bar) instead of the paper's S.T.P. (0 C, 760 mm; 22.414 L/mol): all values 1.3 % low |
| `yh2o_ch4_binary` | 30 | value corrected: CHAPOY(2003): the authors' Corrigendum (Fluid Phase Equilib. 230 (2005) 210-214, Table 1) withdrew the original water contents (sampling-circuit adsorption made them too  |
| `FROST(2013)` | 10 | state corrected: T printed 283.89 K (Table 2), stored as the isotherm label 283.0 |
| `FROST(2013)` | 12 | state corrected: T printed 298.31 K (Table 2), stored as the isotherm label 298.0 |
| `FROST(2013)` | 10 | state corrected: T printed 313.11 K (Table 2), stored as the isotherm label 313.0 |
| `FROST(2013)` | 10 | state corrected: T printed 323.56 K (Table 2), stored as the isotherm label 323.0 |
| `FROST(2013)` | 5 | state corrected: T printed 283.89 K (Table 2), stored as the isotherm label 283.0 |
| `FROST(2013)` | 6 | state corrected: T printed 298.31 K (Table 2), stored as the isotherm label 298.0 |
| `FROST(2013)` | 5 | state corrected: T printed 313.11 K (Table 2), stored as the isotherm label 313.0 |
| `FROST(2013)` | 5 | state corrected: T printed 323.56 K (Table 2), stored as the isotherm label 323.0 |
| `AWAN(2010)` | 8 | state corrected: T printed 314.25 K (Table 8), stored 313.0 |
| `AWAN(2010)` | 8 | state corrected: T printed 298.78 K (Table 8), stored 298.0 |
| `OU(2015)` | 10 | state corrected: isotherm is 285.15 K (Table 2), stored 286.0 |
| `OU(2015)` | 20 | state corrected: isotherm is 493.15 K (Table 2), stored 494.0 |
| `PRICE(1979)` | 16 | state corrected: 206 C = 479.15 K, stored 478.0 |
| `GILLESPIE(1980)` | 2 | state corrected: 300 F = 422.04 K, stored as the 423.0 K label |
| `co2_water_binary` | 6 | state corrected: SAKO Table 1: T printed 421.4, 420.9, 421.4 K, stored as the 423.0 label |
| `yh2o_co2_binary` | 8 | state corrected: SAKO Table 1: T printed as 421.4/420.9 K and 348.3/348.2 K, stored as the 423.0 and 348.0 labels |
| `yh2o_ch4_binary` | 3 | state corrected: CHAPOY(2005): printed T 292.7, 297.9, 297.6 K, stored as the 293.0 and 298.0 labels |
| `SUSAK(1980)` | 502 | flagged calculated-not-measured: USGS open-file report 80-371 prints output of a TI-59 program (Haas 1978 equation, stated valid to 10,000 psi), not measurements; extrapolated cells to 623 K and 20,000 p |
| `SACHS(1995)` | 22 | flagged calculated-not-measured: the methane mole fractions of this surface-tension study are calculated from literature solubility correlations, not measured |
| `ch4_water_binary` | 4 | flagged hydrate-regime: CULBERSON(1951): the 77 F values above 6800 psia are printed in parentheses as non-equilibrium (hydrate present) |
| `yh2o_co2_binary` | 8 | quality set to U: TODHEIDE(1963): water content printed as the complement of y_CO2 = 99.0 mol% (+-1 mol%), so y_H2O = 0.010 +- 0.010 carries no information |
| `ch4_water_binary` | 14 | quality set to U: CARROLL(1998): the printed 125 C block repeats the 75 C block (seven identical solubilities, two pressures differ); a copied block is likely |
| `ch4_water_binary` | 30 | quality set to U: CAMPOS(2010): the data are not Henry-law consistent (x/P rises 2.5 times between 1.1 and 6.4 bar) |
| `yh2o_ch4_binary` | 1 | quality set to U: OLDS(1942): 35 % above the authors' own smoothed table value |
| `ch4_water_binary` | 2 | quality set to U: AWAN(2010) Table 8 prints x2 = 2.1e-4 and m2 = 0.013 mol/kg for one point, which disagree by 11 % |
| `yh2o_ch4_binary` | 1 | quality set to U: FROST(2013) 4.78 MPa, y = 0.441e-3 is 40 % off the authors' own y.P trend; a misprint is likely but not provable |
| `co2_part1` | 612 | removed (v1.1.1 row): WANG(2014): mislabelled copy of Wang, Junliang et al. 2019 (J. Chem. Eng. Data 64, 2484), Tables 6-8: the 306 points are CO2 in 1, 2 and 3 mol/kg NaCl at 303-353 K and 3- |
| `h2_water_binaries` | 2 | removed (v1.1.1 row): DOHRN(1986): the paper (Dohrn & Brunner 1986, hexadecane-water-hydrogen, Table 1) has no 523 K data: its temperatures are 200, 300 and 350 degC. The stored state (200 bar |
| `c3h8_water` | 78 | source corrected: CHAPOY(2004) -> CHAPOY(2004d): the 78 propane-water rows were cited as the methane paper Chapoy 2004 (10.1016/j.fluid.2004.02.010); they are Chapoy, Mokraoui, Valtz, Rich |
| `adeniyi2020_10.11575_prism_38486_tA.3.1` | 21 | excluded: gas-phase mixture 'h2s-co2': the gas-phase composition has no column in the database |
| `anthony1967_10.1021_je60032a007_t1` | 114 | excluded: gas-phase mixture 'c2h6-c2h4': the gas-phase composition has no column in the database |
| `burgass2021_10.1016_j.fluid.2020.112873_t6` | 7 | excluded: gas-phase mixture 'natural gas (n2 7.00, ch4 84.13, c2h6 4.67, c3h8 2.34, c4h10 0.93, c5h12 0.93 mole %)': the gas-phase composition has no column in the database |
| `folas2007_10.1016_j.fluid.2006.12.018_t3` | 10 | excluded: gas-phase mixture 'ch4-c2h6-c3h8-i-c4h10-n-c4h10': the gas-phase composition has no column in the database |
| `fouad2015_10.1002_aic.14885_t3_group1` | 36 | excluded: gas-phase mixture 'ch4-co2': the gas-phase composition has no column in the database |
| `fouad2015_10.1002_aic.14885_t3_group2` | 21 | excluded: gas-phase mixture 'c2h6-co2': the gas-phase composition has no column in the database |
| `fouad2015_10.1002_aic.14885_t3_group3` | 15 | excluded: gas-phase mixture 'ch4-co2': the gas-phase composition has no column in the database |
| `gil2006_10.1021_ie058068g_t3` | 20 | excluded: gas-phase mixture 'co2-c3h8': the gas-phase composition has no column in the database |
| `gil2006_10.1021_ie058068g_t3` | 19 | excluded: gas-phase mixture 'co2-n-c4h10': the gas-phase composition has no column in the database |
| `gil2006_10.1021_ie058068g_t4` | 45 | excluded: gas-phase mixture 'co2-c3h8-meoh': the gas-phase composition has no column in the database |
| `gil2006_10.1021_ie058068g_t4` | 54 | excluded: gas-phase mixture 'co2-n-c4h10-meoh': the gas-phase composition has no column in the database |
| `song1990_10.1021_je00061a026_t1` | 6 | excluded: gas-phase mixture 'co2-ch4': the gas-phase composition has no column in the database |
| `song1990_10.1021_je00061a026_t2` | 21 | excluded: gas-phase mixture 'co2-ch4': the gas-phase composition has no column in the database |
| `song2014_10.1021_es404618y_t1_group2` | 19 | excluded: gas-phase mixture 'co2-n2-o2': the gas-phase composition has no column in the database |
| `sun2023_10.1021_acs.jced.3c00096_t5` | 80 | excluded: gas-phase mixture 'ch4-c2h6': the gas-phase composition has no column in the database |
| `yarrison2006_Yarrison_2007_t13` | 36 | excluded: gas-phase mixture 'co2-ch4': the gas-phase composition has no column in the database |
| `yarrison2006_Yarrison_2007_t14` | 21 | excluded: gas-phase mixture 'c2h6-co2': the gas-phase composition has no column in the database |
| `bruusgaard2010_10.1016_j.fluid.2010.02.042_t1` | 24 | excluded: mixed-gas table (two dissolved gases): the gas-phase composition has no column in the database |
| `liu2012_10.1021_je3000958_t1` | 72 | excluded: mixed-gas table (two dissolved gases): the gas-phase composition has no column in the database |
| `liu2012_10.1021_je3000958_t2` | 12 | excluded: mixed-gas table (two dissolved gases): the gas-phase composition has no column in the database |
| `marinakis2013_10.1016_j.jct.2013.05.039_t1` | 86 | excluded: mixed-gas table (two dissolved gases): the gas-phase composition has no column in the database |
| `co2_part1` | 10 | removed (duplicate copy): CHABAB(2020) (Multi_Salt curation of the 6 m NaCl data, rounded temperatures) repeats Chabab et al. 2021 Table 2 to six digits at 303.55 K; the 303.0 K label hid the matc |
| `millero2002_10.1016_s0016-7037(02)00838-4` | 38 | removed (duplicate copy): Millero, Huang & Laferiere GCA 66 (2002) 2349 (25 C) and Mar. Chem. 78 (2002) 217 (5-45 C) report the same oxygen measurements: the GCA values equal those the Marine Chem |
| `yarrison2006b_Yarrison_2007` | 8 | removed (duplicate copy): the Yarrison thesis (2007) repeats values of the journal data of Yarrison et al. (2006) to the last digit; the journal copy is kept |
| `mohammadian2015_10.1021_je501172d_t2` | 6 | quality set to U: MOHAMMADIAN(2015) Table 2 low-pressure points (<= 2.1 MPa) disagree with the paper's own pure-water Table 1 (0.250 against 0.315 at 2.1 MPa) |
| `crozier1974_10.1021_je60062a007_t1` | 27 | removed: exact duplicate of a row of the same source (same state, same value) |
| `douglas1965_10.1021_j100892a021_t1` | 8 | removed: exact duplicate of a row of the same source (same state, same value) |
| `douglas1965_10.1021_j100892a021_t2` | 11 | removed: exact duplicate of a row of the same source (same state, same value) |
| `laracruz2019_LaraCruz_2019_t3` | 1 | removed: exact duplicate of a row of the same source (same state, same value) |
| `millero2002_10.1016_s0016-7037(02)00838-4_t5_group1` | 2 | removed: exact duplicate of a row of the same source (same state, same value) |
| `millero2002_10.1016_s0016-7037(02)00838-4_t5_group2` | 4 | removed: exact duplicate of a row of the same source (same state, same value) |
| `millero2002_10.1016_s0016-7037(02)00838-4_t6_group1` | 2 | removed: exact duplicate of a row of the same source (same state, same value) |
| `millero2002_10.1016_s0016-7037(02)00838-4_t6_group2` | 2 | removed: exact duplicate of a row of the same source (same state, same value) |
| `millero2002_10.1016_s0016-7037(02)00838-4_t6_group3` | 2 | removed: exact duplicate of a row of the same source (same state, same value) |
| `millero2002_10.1016_s0016-7037(02)00838-4_t6_group4` | 2 | removed: exact duplicate of a row of the same source (same state, same value) |
| `millero2002b_10.1016_s0304-4203(02)00034-8_t3` | 2 | removed: exact duplicate of a row of the same source (same state, same value) |
| `millero2002b_10.1016_s0304-4203(02)00034-8_t4` | 8 | removed: exact duplicate of a row of the same source (same state, same value) |
| `millero2002b_10.1016_s0304-4203(02)00034-8_t5` | 10 | removed: exact duplicate of a row of the same source (same state, same value) |
| `wiebe1932_10.1021_ie50272a023_t2` | 2 | removed: exact duplicate of a row of the same source (same state, same value) |
| `yamamoto1976_10.1021_je60068a029_t1` | 8 | removed: exact duplicate of a row of the same source (same state, same value) |
| `king1971_10.1021_ja00737a004_t1` | 1 | removed: exact duplicate of a row of the same source (same state, same value) |
| `song2014_10.1021_es404618y_t1_group1` | 2 | removed: exact duplicate of a row of the same source (same state, same value) |
| `crovetto1993_10.1006_jcht.1993.1013_t2` | 3 | removed: exact duplicate of a row of the same source (same state, same value) |
| `gates1989_10.1021_je00055a016_t1` | 17 | removed: exact duplicate of a row of the same source (same state, same value) |
| `majer1988_10.1016_0021-9614(88)90224-8_t2` | 27 | removed: exact duplicate of a row of the same source (same state, same value) |
| `surdo1982_10.1016_0021-9614(82)90080-5_t1` | 1 | removed: exact duplicate of a row of the same source (same state, same value) |
| `gruszkiewicz2005_10.1016_j.jct.2004.12.009_t1` | 1 | removed: exact duplicate of a row of the same source (same state, same value) |
| `chen2020_10.1021_acs.jced.9b00993_t2` | 4 | removed: exact duplicate of a row of the same source (same state, same value) |
| `chen2020_10.1021_acs.jced.9b00993_t3` | 2 | removed: exact duplicate of a row of the same source (same state, same value) |
| `chen2020_10.1021_acs.jced.9b00993_t4` | 2 | removed: exact duplicate of a row of the same source (same state, same value) |
| `chen2020_10.1021_acs.jced.9b00993_t5` | 5 | removed: exact duplicate of a row of the same source (same state, same value) |
| `crovetto1993_10.1006_jcht.1993.1013_t1` | 4 | removed: exact duplicate of a row of the same source (same state, same value) |
| `marliacy2002_10.1021_je0200766_t1` | 1 | removed: exact duplicate of a row of the same source (same state, same value) |
| `pearce1937_10.1021_ja01291a061_t2` | 1 | removed: exact duplicate of a row of the same source (same state, same value) |
| `rogers1981_10.1021_j150620a008_t1` | 1 | removed: exact duplicate of a row of the same source (same state, same value) |
| `white1987_10.1016_0021-9614(87)90132-7_t1` | 9 | removed: exact duplicate of a row of the same source (same state, same value) |

v1.1.1 rows removed: DOHRN(1986) (2 rows), the mislabelled WANG(2014) copy (612 rows) and five CHABAB(2020) points that duplicate Chabab 2021 (10 rows). 78 rows had their `source` corrected (Chapoy 2004). All other v1.1.1 rows keep their order; those whose value, temperature, pressure, flag or quality was corrected after checking them against the paper are listed above.

## 2026-10-04 — full row-by-row audit of v1.2-dev [auto]

Every row was compared with its paper (see `CHANGELOG.md`). Corrections applied, per paper (`data/provenance/audit_corrections.csv` has every line):

| paper (citation id) | lines | fields |
|---|---:|---|
| ALGHAFRI2012 | 787 | T_K 779, value 8 |
| ALGHAFRI2012_unc | 779 | uncertainty 779 |
| RUMPF1993B | 660 | T_K 180, value 180, m_Na 150, m_SO4 150 |
| TAKENOUCHI1964 | 648 | T_K 324, flags_add 324 |
| SUSAK1980 | 645 | T_K 502, value 143 |
| TODHEIDE1963 | 633 | T_K 315, flags_add 315, P_bar 3 |
| GUO2016 | 624 | T_K 312, value 312 |
| GUO | 524 | value 262, T_K 262 |
| TEYMOURI2017 | 522 | T_K 382, m_Cl 70, m_K 34, m_Na 18, m_Mg 12, m_Ca 6 |
| OU2015 | 378 | T_K 378 |
| KIEPE2002 | 358 | T_K 278, P_bar 36, m_K 22, m_Cl 22 |
| RUMPF1993 | 296 | T_K 134, value 126, P_bar 36 |
| BANDO2003 | 288 | m_Na 72, m_Cl 72, T_K 72, value 72 |
| KIEPE2003 | 286 | T_K 138, P_bar 52, m_K 48, m_Cl 48 |
| LIU2011 | 278 | T_K 246, m_Na 16, m_Cl 16 |
| UMANO1958 | 272 | T_K 270, value 2 |
| KOBAYASHI1951 | 272 | flags_add 272 |
| ALGHAFRI2013 | 252 | T_K 126, m_Na 63, m_SO4 63 |
| KAMPS2007 | 214 | value 170, m_K 22, m_Cl 22 |
| REMOVED_obscure_sources | 210 | __remove__ 210 |
| SANTOS2020 | 192 | T_K 96, value 96 |
| NIGHSWANDER1989 | 178 | T_K 72, m_Na 36, m_Cl 36, value 34 |
| MULLER | 176 | T_K 123, P_bar 52, value 1 |
| SULTANOV1972 | 171 | T_K 142, value 29 |
| MESSABEB2017 | 144 | T_K 72, value 72 |
| YAN2011 | 144 | T_K 72, value 72 |
| MESSABEB2016 | 144 | T_K 72, value 72 |
| ZHAO2015B | 144 | value 108, m_Cl 12, m_Ca 6, m_Mg 6, m_Na 6, m_SO4 6 |
| BAMBERGER2000 | 143 | T_K 87, P_bar 54, value 2 |
| DUFFY1961 | 134 | T_K 82, P_bar 50, value 2 |
| SANTOS2021 | 132 | T_K 66, value 66 |
| PRICE1979 | 128 | T_K 126, P_bar 2 |
| HOU2013 | 123 | T_K 105, P_bar 18 |
| ALGHAFRI2013_unc | 116 | uncertainty 116 |
| VALTZ | 112 | T_K 92, flags_add 15, P_bar 5 |
| CULBERSON1951 | 110 | T_K 96, P_bar 14 |
| POULAIN2019 | 108 | value 96, P_bar 12 |
| TAKENOUCHI1965 | 108 | T_K 54, flags_add 54 |
| STOESSELL1982 | 91 | T_K 63, P_bar 21, value 7 |
| WIEBE1934 | 90 | T_K 80, P_bar 10 |
| CARROLL1998 | 88 | T_K 72, __remove__ 14, P_bar 2 |
| ZHAO2015 | 72 | T_K 36, value 36 |
| YARRISON2006B | 71 | T_K 54, __remove__ 10, value 6, P_bar 1 |
| MEYER | 64 | T_K 58, P_bar 6 |
| MICHELS1936 | 62 | T_K 60, P_bar 2 |
| KING1992 | 62 | T_K 62 |
| CORTI1990 | 60 | T_K 20, m_Na 20, m_SO4 20 |
| OLDS1942 | 56 | T_K 56 |
| BOTGER2016 | 56 | T_K 28, value 28 |
| ALGHAFRI2014 | 54 | T_K 30, P_bar 24 |
| WANG1995 | 52 | T_K 42, P_bar 10 |
| CHABAB2024 | 48 | T_K 45, P_bar 2, value 1 |
| GILLESPIE1980 | 38 | T_K 30, P_bar 4, flags_add 2, value 2 |
| YARRISON2006 | 37 | T_K 37 |
| PRAY1952 | 36 | T_K 18, flags_add 18 |
| PORTIER2005 | 34 | T_K 34 |
| WANG2003 | 34 | T_K 34 |
| CHAPOY2004 | 32 | T_K 32 |
| AMIRIJAFARI1972 | 32 | T_K 16, flags_add 16 |
| BASTAMI2014 | 32 | T_K 32 |
| LEKVAM1997 | 30 | T_K 30 |
| BLANCO1978 | 30 | T_K 30 |
| CAMPOS2010 | 30 | T_K 30 |
| SACHS1995 | 30 | T_K 22, P_bar 8 |
| GAO1997 | 28 | T_K 28 |
| TONG2013 | 28 | T_K 28 |
| KOSCHEL2006 | 28 | T_K 28 |
| ELMAGHRABY2012 | 24 | T_K 12, value 12 |
| YANG2001 | 22 | T_K 22 |
| BRIONES | 21 | T_K 21 |
| HAAS1976 | 21 | flags_add 21 |
| FOX1909 | 20 | flags_add 20 |
| TORIN2021 | 20 | T_K 20 |
| KLING1991 | 18 | T_K 18 |
| DHIMA1999 | 18 | T_K 18 |
| YOKOYAMA1988 | 18 | T_K 18 |
| SCHLAIKJER2018 | 16 | flags_add 16 |
| CHAPOY2005 | 15 | T_K 15 |
| KIM2003 | 12 | T_K 12 |
| DSOUZA | 12 | T_K 12 |
| SAVARY2012 | 12 | T_K 12 |
| QIN2008 | 10 | T_K 10 |
| TONG | 10 | T_K 10 |
| DOHRN1993 | 9 | T_K 9 |
| AWAN2010 | 8 | T_K 8 |
| SAKO1991 | 8 | T_K 8 |
| ADDICKS2002 | 8 | T_K 8 |
| MILLERO2002B | 5 | P_bar 5 |
| KOBAYASHI1953 | 2 | flags_add 2 |
| JACOB2016 | 2 | P_bar 2 |
| REAMER1943 | 1 | __remove__ 1 |
| OAKES1995 | 1 | __remove__ 1 |
| LEOPOLD1927 | 1 | flags_add 1 |

Row status after the audit: {'verified': 17539, 'corrected': 8158, 'residual-difference': 596, 'not-verifiable': 522}.

## 2026-10-05 — sources of papers that could not be obtained [auto]

* Removed (rows deleted; all were `test-only`, none in the reliable set): CULBERSONMCKETTA(1950) 90 rows and CULBERSONHORN(1950) 60 rows (ethane in water, taken from compilation sheets; paper not obtainable), IPATEV(1934) 42 rows and DEVANEY(1978) 18 rows (hydrogen in water; no DOI, not obtainable), 210 rows in all, with their 10 hand-transcription files. The row removals are lines of `data/provenance/audit_corrections.csv` (field `__remove__`).
* Relabelled: KOBAYASHI(1951) (272 rows, propane in water) to KOBAYASHI(1953): the rows are Table VI of Kobayashi and Katz (1953), with which they were compared in the audit; the label had named a thesis that is not obtainable. SULTANOV(1972) (142 rows, methane in water, 423-633 K) to PRICE(1979): the rows were compared with Table 2 of Price (1979), which gives the Sultanov et al. data converted to SCF/bbl and psi; their temperatures and 29 values were set to the printed digits of that table.
* Relabelled: FROST(2013) (63 rows) to FROST(2014): the label carried the year of the online publication (December 2013); the paper is J. Chem. Eng. Data 59(4), 961-967 (2014).
