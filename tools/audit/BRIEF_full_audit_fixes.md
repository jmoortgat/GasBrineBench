# Brief: turn your audit into a correction list (phase 2)

You audited the papers of your packet (`BRIEF.md`). The user now wants the database CORRECTED from the papers: every temperature re-keyed to the
printed value, and every major error fixed. You already hold the transcription of each table (your scratch scripts and tables are still on
disk in your scratch directory). Write, for each paper of your packet, `release/full_audit/fixes/<cid>.csv` under the work root
(`<work>/`), header exactly:

`family,row_id,field,old,new,reason,confidence`

One line per changed field of a stored row. `row_id` is the same position-in-`data/<family>.csv` you used in the audit (the data files have NOT changed
since). Include the `xc_saltfree` sibling rows of a solubility point as separate lines when their T, P or composition changes. Fields allowed:
`T_K, P_bar, value, uncertainty, m_Na, m_K, m_Ca, m_Mg, m_Cl, m_SO4, flags_add, __remove__`. `old` is the stored value you read (a guard: the
line is skipped at apply time if it does not match). `new` is the corrected value as a number (full precision of the printed digits, no unit text);
`__remove__` has `new` empty and is for rows that should not be in the database at all (reason required); `flags_add` has `new` = one flag word
from the vocabulary (`source-caution`, `smoothed-values`, `calculated-not-measured`, `figure-digitized`, `volume-basis-uncertain`, `salinity-matrix`, `stp-assumed`).

## What to include

1. **Temperatures, all rows.** Wherever the paper prints a temperature for the row (a per-run temperature, a per-isotherm mean, or a nominal isotherm
   such as 25 C) and the stored `T_K` differs from it by more than 0.005 K, give the printed temperature in K (C + 273.15, F: (F-32)/1.8 + 273.15,
   unless the paper states another scale). This applies whatever your earlier verdict was (also rows you called `correct` because the offset was 0.05-0.15 K).
   If the paper prints both a nominal isotherm T and per-run actual temperatures, use the per-run printed temperature. If a stored T comes from a
   legacy conversion you cannot reproduce, use the printed one anyway.
2. **Pressures.** Where the stored `P_bar` should equal a printed pressure (converted: MPa x 10, atm x 1.01325, psia x 0.0689476, kPa/100) and differs by more
   than 0.1 %, give the printed one. Do NOT touch pressures that are deliberately derived (1 atm of gas plus the water vapour pressure, pO2 + psat,
   pure-water saturation pressure for isopiestic/psat-ratio rows, dP + psat): those follow the documented convention.
3. **Compositions.** Where the paper prints the molality (or the wt%/mole fraction that determines it unambiguously) and the stored ion molalities differ
   by more than 0.3 %, give the corrected ion molalities (all affected `m_*` fields; remember NaCl 1 m gives m_Na = m_Cl = 1, CaCl2 1 m gives m_Ca = 1, m_Cl = 2;
   total m_Cl must equal the charge balance of the printed salts). Do not correct compositions that the paper does not print (assumed seawater matrices).
4. **Values.** Every `major` whose correct value is unambiguous from the paper (transcription slips, wrong column, wrong isotherm): give the correct `value`
   (and the sibling `xc_saltfree` row's value: printed x if the paper prints x; otherwise the mole fraction consistent with the molality,
   x = m/(m + 55.5084)). For a `solubility_molality` row whose x is printed: m = x/(1-x) x 55.5084. If the paper prints the molality directly and
   the stored molality sits a constant factor (about 0.9991) below it, correct the molality to the printed digits (sibling x = m/(m+55.5084)).
5. **Removals.** Rows that no printed point supports and that cannot be corrected (a point the paper does not contain; an obvious paper misprint that makes the
   stored value physically wrong; data from a different paper under this label): `__remove__` with the reason.
6. **Flags.** `smoothed-values` for tables the authors state are smoothed/graphically interpolated or read from smoothed curves (informational flag), `source-caution`
   for known problems of the source that stay in the data, `calculated-not-measured` / `figure-digitized` where the values are model-calculated or read from a
   figure (default-excluded flags). One line per row. Only where you have evidence from the paper.

## What NOT to do

* No guessing: where two readings of the paper are possible (per kg solution vs per kg water that the paper does not settle, nominal vs actual composition that
  the paper does not print) make NO change and say so in your final report. Ambiguous-basis papers stay as they are.
* Never invent a printed value; if the transcription of a row in your scratch files is missing, re-read the page image.
* Rows you marked `unverifiable` get no changes.

## Checks before you finish

* Your fix file must parse as CSV (quote text fields), every `row_id` must be a row of the right `family` file of the paper (`rows_file`), and `old` must equal the
  database value (a quick script comparing `old` with `data/<family>.csv` is required).
* Re-read your fix list once against the paper for a sample of at least 10 rows per paper (or all, if fewer), and for every row that you give a new T.
* Final report (under 200 words): per paper the number of lines per field, anything deliberately left unchanged and why.
