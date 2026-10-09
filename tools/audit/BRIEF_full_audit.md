# Brief: full row-by-row audit of GasBrineBench v1.2 against the papers

Context. GasBrineBench (repo `<repo>/`, branch `v1.2-dev`, 27,051 rows) holds experimental
points transcribed from papers. A random audit found about 4 % of the points with a major error (mostly wrong meaning of a column, a wrong
temperature or pressure unit, or a wrong composition), concentrated in the older v1.0-v1.1.1 blocks. Now EVERY row must be checked against its
paper. You get one packet of papers: `release/full_audit/packets/a<NN>.json` under the work root
`<work>/`.

Per paper the packet gives: `pdf` (the paper; empty if we have none), `extract_dir` (v1.2 papers: `table_N.csv` is the machine-read table and
`mapping_N.json` says how columns became schema columns), `rows_file` (every database row of this paper: family, `row_id` = zero-based position in
`GasBrineBench/data/<family>.csv` with the header excluded, source, dataset_id, property, gas, T_K, P_bar, ion molalities m_Na m_K m_Ca m_Mg m_Cl m_SO4 in mol/kg water,
value, uncertainty, flags, quality, data_origin) and `result_file` (where you write).

Do not use earlier audit results (`release/random_audit`, `release/outlier_check`, consensus files, the ledger): read the paper. The data files do
not change while you work; do not edit anything except your own results and scratch.

## What to do for each paper

1. Find every printed table or figure that the rows come from (dataset_id tells the table for v1.2 papers, e.g. `..._t3` is Table 3; v1.0-v1.1.1
   dataset_ids such as `co2_part1` or `ch4_water_binary` mix several papers: use T, P, composition to find the printed rows). Legacy hand
   transcriptions are in `GasBrineBench/transcriptions/**/EXP*.txt` (header `#AUTHOR(YEAR)`) and the conversions in `GasBrineBench/data/README.md`
   and `GasBrineBench/tools/builders/*.py`; they help you find the table, but the PAPER decides.
2. Read the printed values. Use `pdftotext -layout` for a first machine read when the PDF has a text layer, but a text layer is not
   proof: look at the page image (Read tool with `pages`) for every table at least once, check every column heading and unit, footnotes and
   the table caption (what the quantity really is: measured or calculated, molality or molarity, per kg water or per kg solution, mole fraction
   of the gas on a salt-free basis or not, total pressure or partial pressure, absolute or gauge, fugacity or pressure, temperature scale).
   Scanned PDFs: read the images. Write a script that compares the stored rows with the values you have transcribed from the paper so that
   EVERY row is compared digit by digit; then look at the page image again for every row the script flags and for a sample of the rows it passes.
3. Compare each stored quantity with the printed one after the documented conversion:
   * T to K (C + 273.15, F: (F-32)/1.8 + 273.15). P to bar (1 atm = 1.01325 bar, 1 MPa = 10 bar, psi = 0.0689476 bar, kPa = 0.01 bar).
     For gas-partial-pressure data the stored pressure may include the water vapour pressure; say what you see.
   * `solubility_molality` (mol gas per kg water): printed gas mole fractions x convert on the salt-free basis m = x/(1-x) x 55.508 (check which basis the paper
     prints); printed molalities are used as printed; per-kg-solution or per-volume values were converted with the stated composition or density.
     The `xc_saltfree` rows are the stored mole-fraction sibling of a molality row (printed x, or derived from the molality): audit the molality row, and compare the
     sibling to the paper only where the paper prints x.
   * `y_h2o`: mole fraction of water in the gas-rich phase (printed mol % divided by 100; the complement 1 - y of a printed gas mole fraction is acceptable).
   * `rho` kg/m3, `psat_ratio` = p(brine)/p(water), `phi_osm`, `Cp_app` J/(K mol), `dh_sol` kJ/mol gas, `visc` mPa s, `eps_r`, ternary rows (gas + brine + a second gas).
   * Composition: ion molalities in mol/kg water (NaCl 1 m gives m_Na = m_Cl = 1; CaCl2 1 m gives m_Ca = 1, m_Cl = 2).
4. A row is right only if T, P, composition, gas, property AND value match one printed point. No matching printed point is a finding.
5. Say, for every table, how the values were obtained in the paper: `table` (printed in a table), `figure` (only in a figure: the database values would be
   digitized or smoothed), `calculated` (the paper's own model or correlation, not a measurement). Compare with the stored `data_origin` and `flags`.

## Verdict per row (exactly one)

* `correct`: every quantity equals the printed value after the conversion (rounding to the printed digits is fine).
* `minor`: all quantities right except a printed temperature or pressure that differs from the stored one by <= 1 K or <= 2 %, or a conversion rounding of 0.5-1 % in the value.
  (Whole-kelvin isotherm temperatures stored for a paper that prints a nominal temperature such as 25 C = 298.15 K are `correct`; if the stored one is e.g. 298 for 298.15 say `minor`.)
* `major`: the value, pressure, composition, gas or property is wrong by more than that, no matching row exists, or the stored quantity is not what the paper's column reports.
  Give the cause: `transcription`, `conversion`, `state`, `meaning`.
* `unverifiable`: the paper or the table could not be read (say what you tried). Never use it for a row whose table you did read.

## Rules

* No web access. Read-only on data. Scratch only in `<scratch>/`.
* No guessing and no pattern-extrapolation: a verdict of `correct` needs printed digits for THAT row. If two readings are possible, report both and mark `unverifiable`
  with the reason. Be sceptical in both directions, and audit your own transcription as hard as the database (a mismatch can be your misread).
* If a paper has no PDF (`pdf` empty): v1.2 papers can be compared with `extract_dir/table_N.csv` + mapping (say `source_type=html_capture`, and mark the verdicts
  `correct` only when the CSV matches AND the mapping/conversion is right; the CSV itself was read twice by machine); legacy papers without a PDF: `unverifiable`.
* Work through ALL rows of ALL papers in your packet. Do not stop early, do not sample. If the packet is too large for the context left, finish what you can
  and say exactly which papers/tables are not done.
* Do not treat the opinion of another agent or of this brief as evidence.

## Result files

For each paper write `result_file` (CSV, header exactly): `family,row_id,verdict,cause,printed,note`
(one line per database row of that paper, in `rows_file` order; `cause` empty unless minor or major; `printed` = what the paper prints for that point
(T, P, composition, value; table and page); `note` empty unless there is something to say). Write it with a script from your comparison table, then re-read
the counts. Also write `release/full_audit/results/<cid>.json` with
`{"paper": "<path>", "source_type": "pdf|html_capture|none", "tables": [{"table": "Table 2, p. 412", "how_obtained": "table|figure|calculated", "stored_data_origin_ok": true,
"quality_comment": "...", "rows": <n>}], "caveats": "..."}`.
Finish with a short report (under 250 words): per paper the counts per verdict, every `major` with row id and cause, anything systematic (whole table off by a unit, basis,
temperature scale), and any table you could not finish.
