# Brief: independent audit of randomly sampled database points against the papers

You are an independent auditor. GasBrineBench (repo `<repo>/`, branch
`v1.2-dev`) holds experimental points transcribed from papers. A random sample of its points must be checked against the printed tables, one by
one, by someone who has not seen any earlier check. Do not look for earlier audit results, consensus files or ledgers: read the paper.

Your chunk file: `release/random_audit/packets/chunk_<N>.json` under
`<work>/` (work root). Each entry is one table group: source,
dataset_id, origin (`v1.1.1` or `v1.2`), `pdf_candidates`, and the sampled points: family, `row_id` (zero-based position in
`GasBrineBench/data/<family>.csv`, header excluded), stored values (property, gas, T_K, ion molalities in mol/kg water, P_bar, value, uncertainty,
flags), and for solubility the `sibling_row_id` (the mole-fraction row of the same point).

## What to check, for every point

1. Find the table of the paper that contains the point. Read the printed row from the page image (Read tool, `pages`); read every digit.
   For HTML-only papers (`source_type` says so; no PDF) compare with `extract_dir/table_N.csv` and `mapping_N.json` instead and say so.
2. Compare each stored quantity with the printed one after the documented conversion:
   * T: printed unit to K (C + 273.15). P: to bar (1 atm = 1.01325 bar, 1 MPa = 10 bar, psi = 0.0689476 bar). For gas-partial-pressure data the stored
     pressure may include the water vapour pressure; say what you see.
   * `solubility_molality`: mol gas per kg water. Printed mole fractions x of the gas are converted on the salt-free basis m = x/(1-x) x 55.508;
     printed molalities are used as printed; per-kg-solution values were converted with the stated composition; cm3 (STP) per g with 22.414 L/mol.
   * `y_h2o`: mole fraction of water in the gas-rich phase (a printed mol % is divided by 100; a complement 1 - y is acceptable if the paper prints y of the gas).
   * `rho`: kg/m3 (g/cm3 x 1000). `psat_ratio`: p(brine)/p(water) at the same T. `phi_osm`, `Cp_app` (J/(K mol)), `dh_sol` (kJ/mol gas), `visc` (mPa s).
   * Composition: ion molalities in mol/kg water (NaCl 1 m gives m_Na = m_Cl = 1; CaCl2 1 m gives m_Ca = 1, m_Cl = 2). Salts outside the six ions are not in the database.
3. The point is about the right TABLE ROW only if T, P, composition and gas all match. If you cannot find a matching printed row, that is a finding.
4. Also say whether the stored quantity is what the column of the paper really reports (the printed column could be a calculated, smoothed or
   literature value, or a ternary or non-aqueous system).

## Verdict per point (exactly one)

* `correct`: every quantity equals the printed value after the conversion (rounding to the printed digits is fine).
* `minor`: all quantities right except a printed temperature or pressure that differs from the stored one by <= 1 K or <= 2 %, or a conversion
  rounding of 0.5-1 % in the value.
* `major`: the value, pressure, composition, gas or property is wrong by more than that, no matching row exists, or the stored quantity is not what
  the paper's column reports. Name the cause (transcription, conversion, state, meaning).
* `unverifiable`: no paper or table could be read (say what you tried).

## Rules

* The folder `papers_archive/` under the work root holds one PDF per cited paper (named `<Citekey>__<doi slug>.pdf`); a few files there are the wrong paper (matched by author and year only), so confirm title, authors, journal and year on page 1 and, if wrong, search the legacy trees named below.

* Read-only on everything except your result file. No web access. Scratch only in
  `<scratch>/`.
* Papers: `pdf_candidates`; if empty or wrong search `<local path>,Multi_Salt/papers,EoS_Benchmark/papers,papers}`
  and `<work root>/papers_local/` for the author and year. For v1.1.1 points the hand transcription (`GasBrineBench/transcriptions/**/EXP*.txt`,
  header `#AUTHOR(YEAR)`) and `GasBrineBench/data/README.md` may help you find the table, but the paper decides.
* Do not guess: if two readings are possible, report both.
* Stored values: `python3 -c "import pandas as pd; d=pd.read_csv('<repo>/data/<family>.csv', keep_default_na=False); print(d.iloc[ROW_ID])"`.
* Be sceptical in both directions: an `correct` needs the printed digits, not plausibility.

## Result file

`release/random_audit/results/chunk_<N>.json`:
```
{"<source>|<dataset_id>": {"paper": "<path or 'not found'>", "source_type": "pdf|html_capture", "points": [
   {"family": "...", "row_id": 123, "verdict": "correct|minor|major|unverifiable", "cause": "transcription|conversion|state|meaning|null",
    "printed": "<what the paper prints for T, P, composition, value, with table and page>", "stored": "<what you read from the database>",
    "evidence": "<table, page, the comparison>", "confidence": "high|medium|low"}]}}
```
Entries whose key ends in `#2` are second readings of points another auditor also reads; treat them like any other, do not look for the other reading.
Finish with a short report: counts per verdict, and for every `major` or `minor` the row id and what is wrong.
