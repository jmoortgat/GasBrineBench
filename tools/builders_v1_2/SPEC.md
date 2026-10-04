# Extraction specification v2 (GasBrineBench v1.2 additions)

v2 incorporates the comments of three pilot extractions (Chen 2020 HTML, Alvarez 1988 text-layer PDF,
Smith 1962 scanned PDF). Goal: turn a measured-data table into files with NO unit conversion and no
interpretation done by hand. A builder script reads the files and creates database rows, so every
conversion is code that can be tested and rerun.

## Output folder

`extract/<doi with / replaced by _>/` containing, for each in-scope table N, `table_N.csv` and `mapping_N.json`, plus one
`paper.json`. Pilot examples to copy the style from: `10.1002_bbpc.198800223/` (two gases in one table),
`10.1021_acs.jced.9b00993/` (HTML, group rows), `10.1016_0016-7037(62)90066-2/` (side-by-side blocks, normality, scan).

### table_N.csv  (the table AS PRINTED)
- First row = column headers. ASCII only (write `10^4 x`, `Phi_2`, `kH_inf`, `-` for minus, full stop for a printed
  mid-dot decimal such as 1·10; note any such change in `paper.json`). Join multi-line headers with a space. Keep units in the header text.
  Footnote letters glued to a header or number are NOT part of the name: strip them from the header and the number, and record them in a
  `note` column as `<column header>:<letter>` separated by `;`.
- One CSV row per printed data row. Values are strings exactly as printed (keep trailing zeros). Convert a printed en dash or minus sign to `-`.
- Label rows (repeated headers, "1 mol/kg NaCl solution", block headings) are KEPT, with the label text in the first column; describe them in the mapping.
- Side-by-side blocks (several concentration or gas blocks printed next to each other): STACK them into one long table
  with one label row per block (this is the standard layout, not a wide mostly-empty table). A table whose column groups have different
  headers may instead be written as `table_N_groupK.csv` with `mapping_N_groupK.json`; state the choice in `paper.json`.
- Exact replicate rows are legitimate data: keep them.
- Never drop a row because it looks odd, is flagged by the authors, or lies outside our scope (below 273 K, hydrate region, liquid
  hydrocarbon phase, salts outside the six-ion set). Keep it and mark it.

### Row indices
`skip_rows` and `group_rows` use 0-based indices over ALL CSV rows after the header row, label rows included.

### mapping_N.json
```json
{
  "table": "Table 1", "page_journal": 937, "title_as_printed": "...",
  "footnotes_as_printed": {"a": "text", "b": "text"},      // copy them; "not captured" if the source lacks them
  "property": "<native property, list below>",
  "gas": "n2",                      // co2 ch4 h2 n2 o2 c2h6 c3h8 | "" gas-free | "co2-ch4" only for mixture water content
  "regime": "",                     // "" | "hydrate" (hydrate phase present) | "lle" (hydrocarbon-rich phase is liquid)
  "temperature_scale": "not stated",   // ITS-90 | IPTS-68 | IPTS-48 | not stated
  "pressure_note": "total cell pressure incl. water vapour",  // as stated; "not stated" if not
  "columns": {
    "T": {"col": "T K", "unit": "K"},                         // unit K, C, F; for a constant T written only in the title:
                                                               //   {"col": "", "unit": "C", "constant": "30"}
    "P": {"col": "p MPa", "unit": "MPa", "basis": "total"},    // basis: total | gas_partial | saturation | unspecified
    "value": {"col": "10^4 x", "unit": "mole_fraction_gas_in_aqueous_phase", "scale": 1e-4},   // value = printed x scale
    "value2": {"col": "...", "unit": "...", "what": "...", "from_literature": true},         // from_literature: not measured by this paper
    "uncertainty": {"col": "...", "unit": "..."},
    "m_gas": {"col": "...", "unit": "mol/kg"}
  },
  "composition": {
    "basis": "molality",            // molality | mass_fraction | mass_percent | molarity | normality | mole_fraction | g_per_kg | ionic_strength | none
    "per_row": {"NaCl": {"col": "m", "unit": "mol/kg"}},
    "constant": {"Na2SO4": {"value": "1.0", "unit": "mol/kg"}},
    "other_species": "anything outside the six-ion set (LiCl, NH4NO3, NaOH, seawater ...), as printed"
  },
  "skip_rows": [{"rows": [0], "reason": "section label"}],
  "group_rows": [{"label_row": 0, "sets": [
      {"path": "gas", "value": "h2"},
      {"path": "composition.constant.NaCl", "value": "1.00", "unit": "N"}]}],
  "extra_unmapped": ["Phi_2 (calculated by authors)", "kH_inf (calculated)"],
  "conversion_needs": ["normality to molality needs solution density", "..."],
  "notes": ""
}
```
`group_rows`: a label row sets the listed paths for all following rows until the next label row; any path may be set this way,
including `gas`, `regime`, `T` constants and several salts at once. A normality of a 2-1 salt counts equivalents (1 N CaCl2 = 0.5 mol/L): record that in
`conversion_needs`, do not convert.

Native `property` names (the builder maps them): `solubility_x` (gas mole fraction in the aqueous phase; say whether salt-free basis),
`solubility_molality`, `bunsen`, `ostwald`, `henry` (state the exact definition), `y_h2o` (water mole fraction in the gas phase),
`water_content_mass`, `rho`, `rho_gas_loaded`, `rho_diff` (difference from pure water; state the reference), `visc`, `phi_osm`,
`isopiestic_molality` (state the reference salt), `psat_brine` (absolute pressure; also used for a pure-water reference table with
composition basis `none`), `bpe`, `dh_sol`, `dh_dilution`, `phi_L`, `phi_Cp`, `Cp_apparent`, `eps_r`, `pmv`, `other` (describe).

### paper.json
`doi`, `first_author`, `year`, `journal`, `source_key` (capitals, e.g. `SMITH(1962)`; a suffix such as `_T3` only when one paper
holds independent blocks the database should treat separately), `experimental_method` (one sentence), `uncertainties_stated`,
`quality_remarks` (anything on reliability, calibration, contamination, misprints, disagreement between text and tables),
`how_extracted` (html_cells | pdf_text_layer | ocr | image_read), `verified_against_page_image`
(`{"verified": true, "pdf_pages": [3], "journal_pages": [937]}`; false with a reason for HTML-only sources),
`not_extracted_tables` (derived, estimated, fitted or out-of-scope tables, each with a reason), `row_counts`
(printed vs written, per table), `changes_after_image_check` (`table row: old -> new`), `extraction_notes`.

## Rules

1. Numbers come only from the table (cells, text layer or page image). Never from memory, the abstract or an earlier summary.
2. HTML-sourced tables: exact cells are saved in `extract/htmlcap_*.json`, one record per paper with the table cells, the table
   footnotes, the abstract and the methods text. Convert with a script; do not retype. Copy the footnotes into the mapping.
3. PDF tables: try `pdftotext -layout`; if the columns come out scrambled use `pdftotext -bbox` and group words by y-coordinate;
   for scans use `pdftoppm -r 200 -png` and `tesseract`. Then read EVERY table page as an image (Read tool on the PNG) and fix
   every digit error (dropped decimal points, 0/O, 1/l, 5/6/8, minus signs, missing columns). When the text layer is unreliable a
   complete re-read from the image is expected and acceptable.
4. SECOND PASS for scans, OCR and any table whose text layer needed corrections: a different agent extracts the same table
   blind (without seeing the first CSV) and a script diffs the two; every disagreement is settled by looking at the image at high resolution
   and recorded. A table is `status: verified` only after the diff is clean.
5. State printed rows versus written rows. Run sanity checks in a scratch script and report: monotonic where the physics requires it,
   values in the stated ranges, replicate rows noted. List every post-check change.
6. Record exactly how pressure and composition are defined (total vs partial pressure; molality, molarity, normality or mass percent;
   salt-free basis or not; temperature scale). Write `not stated` when the paper does not say; never guess.
7. No web lookup: work only from the paper's own PDF or saved HTML capture, and write only into the paper's own folder
   (`extract/<doi_slug>/` in the maintainers' work area, `transcriptions_v1_2/<doi_slug>/` in this repository).
8. Do not extract tables that are derived, smoothed, spline- or model-generated, or estimated by the authors: list them in
   `not_extracted_tables`. Literature comparison columns inside a measured table are kept but marked `from_literature`.

---

# Conventions settled in the first extraction wave (v2.1, 2026-10-02)

These settle the questions the first extraction agents raised. Where an agent already used a different but documented form, it
stays valid; the builder reads both.

1. **Gases.** Any gas may appear in a mapping, including those outside the seven (`he`, `ne`, `ar`, `kr`, `xe`, `n-c4h10`, ...) and
   mixtures written `a-b` (`ch4-c2h6`, `co2-ch4`). Keep them; the builder decides what enters the database. Two gases in one row:
   `value` and `value2` each carry their own `gas` key; add `uncertainty2` if needed.
2. **group_rows may set any path**: `gas`, `regime`, `T.constant`, `value.constant` (a quantity printed only in a block label, such as a constant
   water mole fraction), `composition.constant.<salt>` (value and unit as separate keys), `composition.constant.salinity`.
3. **Carried-forward temperature or pressure** (printed only on the first row of a sub-block) may be filled down; document it in the mapping.
4. **`scale`** may be negative or fractional (value = printed x scale).
5. **Calculated companion columns.** `derived_by_authors: true` marks columns the authors computed from their own measurements (osmotic coefficient from
   isopiestic molalities, Henry constant per experiment, mole fraction from a Bunsen coefficient). `from_literature: true` marks other authors' values.
   Both stay in the CSV; the builder treats the primary measured quantity as the datum.
6. **Composition bases added:** `normality` (equivalents per litre; 1 N of a 2-1 salt is 0.5 mol/L), `salinity_permil` (give the matrix in
   `other_species`), `g_per_L`. A medium that fits none: describe it in `other_species` and use `none`.
7. **Native properties added:** `aw` (water activity = p / p0 of pure water, dimensionless), `gas_volume_solubility` (mL of gas per g water or per mL; give the reference
   state), `isopiestic_molality` (`value` = test salt, `value2` = reference salt, `reference_salt` field, authors' osmotic coefficient as
   `phi` with `derived_by_authors`).
8. **Unit strings the builder will map:** `mol_per_kg_water`, `mol_per_kg_solution`, `bunsen_cm3STP_per_cm3_per_atm`, `bar` (also for 10^5 Pa), `Pa`, `torr`,
   `psia`, `mole_fraction_gas_in_aqueous_phase`, `salinity_permil`. A pressure of 1 atm for atmospheric equilibration: constant P 101.325 kPa with basis `unspecified`
   and the wording from the paper in `pressure_note`.
9. **Pressure basis:** bubble-point (synthetic method) tables: `basis: saturation`; dew-point tables: `saturation`; add a vapour-pressure `P` column only
   if it is not already the `value`.
10. **Label rows and summary rows.** Every label row and every summary row ("Mean deviation", "Overall") is listed in `skip_rows`. Where a label is printed beside the first data
    row, write it as its own label row.
11. **Side-by-side blocks:** stack the left block first, then the right, within each label block; say so in the mapping notes.
12. **Tables with out-of-scope test salts and an NaCl reference** (e.g. SrCl2 or BaCl2 against NaCl): skipped, with the reason in `not_extracted_tables`.
13. **Sub-273 K rows and hydrate rows** are kept; mark `regime: hydrate` or note `below_273K`; the builder tags them.
14. **Second pass** is mandatory when `needs_pass2` is true. Any paper whose pass 1 had even one correction after the image check counts.
