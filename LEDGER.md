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
