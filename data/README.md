# Benchmark database v0 — per-dataset provenance

> **Where this file came from.** This is the build log of the database,
> written inside the model-comparison harness the data was assembled for
> (`EoS_Benchmark`), and it is reproduced here verbatim because it is the
> record of where every block of rows came from: which paper, which table,
> which page, which unit convention, and what was deliberately left out.
>
> It therefore refers to modules, tests and directories that are **not part of
> this repository** — `bench.core.*`, `code/tests/test_data.py`,
> `benchmark_v0.parquet`, `Multi_Salt/...`, `source_materials/...`. Those
> names are provenance, not instructions: nothing here needs them. The
> builder scripts named below are kept under `../tools/builders/` for the same
> reason, and they do not run standalone (see the repository `README.md`).
>
> Row-level provenance in this database is **per `dataset_id`**, and the table
> under *Provenance per dataset_id* below is where it lives. The raw
> hand-transcription each curated block was typed from is in
> `../transcriptions/`, keyed by its `#AUTHOR(YEAR)` header.

Built by `build_v0.py` (run: `PYTHONPATH=<repo>/code python3
bench/data/build_v0.py`; the curated blocks need the Multi_Salt tree,
default sibling checkout, override with env `ECPA_MS_CODE`).
Tests: `code/tests/test_data.py`.

## Files and schema

One csv per property family plus a combined parquet
(`benchmark_v0.parquet`, 4845 rows after the quality pass, the
Hou-2013b addition and the v0.4 transfer-gas solubility block).
Identical columns everywhere:

```
dataset_id, source, gas, property, T_K, P_bar,
m_Na, m_Cl, m_K, m_Ca, m_Mg, m_SO4,
value, uncertainty, quality, tag
```

- `gas` is `''` for gas-free rows (rho, phi_osm, psat_ratio, eps_r).
  Read the csvs with `keep_default_na=False` to preserve that.
- Gas codes: `co2`, `ch4`, `h2`, `n2`, `o2`, `c2h6`, `c3h8`.  Since
  v0.4 the solubility family covers all seven (transfer-gas block,
  Part C of `build_v0.py`); the y_h2o family covers all but `o2`.
  Codes follow the model adapters' conventions (soreide_whitson
  `_GAS_CONST` carries `n2`; e_pr_cpa `GASES_PRM` carries `h2`/`o2`;
  the ecpa adapters carry `n2`/`h2`/`c2h6`/`c3h8` through the
  Papers II/III transfer route); models without a gas raise
  `Unsupported`, which the scoring harness records per row.
- No v0.4 transfer-gas row is `fit-eligible`: the transfer gases are
  the benchmark's PREDICTION-ONLY transferability axis and are
  outside every refit objective (the c3/c5 refit rounds predate
  these rows; Part C is appended after all pre-existing rows so the
  positional row ids in the frozen refit checkpoints stay valid).
  They carry `test-only`, or `lle-regime` where the phase-regime
  screen finds the hydrocarbon-rich phase to be a liquid (see the
  `tag` entry below).
- Ion molalities are mol/kg-water in the frozen
  `bench.core.base.IONS` order.
- `property` vocabulary: `solubility_molality`, `xc_saltfree`,
  `y_h2o` (v0.1 addition, `y_h2o.csv` built by `build_y_h2o.py`,
  not part of `benchmark_v0.parquet`), `rho`, `phi_osm`,
  `psat_ratio`, `dh_sol`, plus the extension `eps_r` (static permittivity target
  set; kept because it is one of the Multi_Salt harness blocks even
  though it was not in the assigned enum).
- `quality`: R/T/U per Yang et al., IECR 2022, 61, 15576, Sec. 5.2
  (R = evaluated compilation verified against independent data,
  T = tentative/plausible [default], U = author-flagged or
  unverifiable).
- `tag`: `fit-eligible` = was a fit target in the Multi_Salt
  parameterization (so NOT an independent test for our eCPA;
  usable as training data by the refit harness for any model);
  `test-only` = never fitted by us; `lle-regime` = a condensable-
  hydrocarbon row measured below the hydrocarbon's critical
  temperature and at or above its own vapor pressure, so the
  hydrocarbon-rich phase is a LIQUID and the point is a
  liquid--liquid mutual solubility, not gas solubility (144 rows,
  all KOBAYASHI(1951) C3H8; assigned by `build_v0._regime_tag`
  against the reference-EoS saturation line and audited in
  QUALITY.md Sec. 7).  Both row loaders
  (`bench.core.scoring.load_rows`, `bench.core.refit.load_rows`)
  drop the `lle-regime` rows by default via
  `bench.core.conventions.EXCLUDED_TAGS`; pass `exclude_tags=()` to
  score them deliberately.  The rows are kept in the database: they
  are good data about a different property.
- `uncertainty`: experimental standard uncertainty where the source
  states one (Chabab tables, dos Santos, Koschel); for the harness
  target sets it is the harness-ASSIGNED 1-sigma weight
  (phi_osm 0.005 at 298 K / 0.01 digitized, rho 0.5 kg/m3,
  eps_r 2, psat_ratio 0.002), recovered exactly from the TargetsT
  weight vector; blank (empty) where unknown (Part-1 gas DBs).

## Provenance per dataset_id

| dataset_id | family | n | provenance | quality | tag |
|---|---|---|---|---|---|
| co2_part1 | solubility | 511 x2 | Multi_Salt `data/co2_brines.parquet` (Part-1 CO2 DB, 5 single salts, per-row author in `source`); reported as salt-free mole fraction `xc_saltfree`, converted `solubility_molality` row added via `bench.core.conventions.xc_saltfree_to_molality` | T | fit-eligible |
| ch4_part1 | solubility | 469 | Multi_Salt `data/ch4_brines.parquet`, filtered 284-532 K exactly as `phase4_cofit.load_ch4` (T_MIN/T_MAX line 142); `mh_W` is already molality | T | fit-eligible |
| co2_mixed_brines | solubility | 298 x2 | Multi_Salt `data/co2_mixed_brines.parquet` (9 authors: LIU_2011 99, WANG_2014 64, POULANI_2019 48, ZHAOc_2015 24, PORTIER_2005 19, TEYMOURI_2017 18, TONG_2013 14, ELMAGHRABY_2012 6, LI_2004 6); the phase3b_shyd stage-b3 prediction set | T | test-only |
| chabab2019_t2 | solubility | 21 x2 | NEW extraction: Chabab et al., IJGGC 2019, 91, 102825, **Table 2** (pp. 9-11), CO2 in NaCl brine (1.00-3.01 m, 323-373 K, to 230 bar), salt-free mole fraction with per-point u(x) | T | test-only |
| chabab2020_t4 | solubility | 37 x2 | NEW extraction: Chabab et al., IJHE 2020, 45, 32206, **Table 4** (pp. 14-15), H2 in NaCl brine (0-5 m, 323-373 K, to 230 bar), u(T)=0.02 K, u(P)=5 kPa. NOTE: printed table has 37 points (page-image verified), not the 40 in the assignment brief | T | test-only |
| chabab2021_t2 | solubility | 14 x2 | NEW extraction: Chabab et al., JCED 2021, 66, 609, **Table 2** (p. 14), CO2 in 6 m NaCl, rocking cell, u(T)=0.17 K, u(P)=0.068 MPa | T | test-only |
| chabab2021_t3 | solubility | 44 x2 | NEW extraction: same paper, **Table 3** (pp. 15-16), O2 in NaCl brine (0.5-4 m, 303-373 K, to 36 MPa), two techniques (tech in `source`); the starred 1* block (5 pts, Technique 1, ~373 K) is author-flagged for probable molality drift -> quality U | T (5 pts U) | test-only |
| dossantos2021_t7 | solubility | 30 | NEW extraction: dos Santos et al., Chem. Geol. 2021, 582, 120443, **Table 7** (pp. 28-29): 6 pts 6 m NaCl + 24 pts mixed 3 m NaCl + 1 m Na2SO4 (303-423 K, 1.5-20 MPa), DIRECT molality with u(m)=0.0228 m | T | test-only |
| hou2013_t2 | solubility | 36 x2 | NEW extraction (v0.2, tables in `hou2013.py`): Hou, Maitland, Trusler, JSCF 2013, 78, 78-88, **Table 2** (p. 82), CO2 in NaCl brine (2.5 / 4.0 mol/kg, 323.15-423.15 K, 2.8-18.2 MPa), aqueous x1' on the SALT-FREE basis with per-point sampling sd; brine molality u = 0.4% rel; the same points' vapor rows are yh2o_co2_nacl_hou2013 | T | test-only |
| hou2013_t3 | solubility | 36 x2 | same paper, **Table 3** (p. 83), CO2 in KCl brine (2.5 / 4.0 mol/kg, same grid); vapor rows are yh2o_co2_kcl_hou2013 | T | test-only |
| rho_alghafri | rho | 905 | Al Ghafri et al. 2012 (JCED 57:1288; NaCl/KCl/CaCl2/MgCl2) + 2013 (Na2SO4) full curated density frame = `TargetsT.rho_all` (per-row source file in `source`); 283-473 K, 9-686 bar. The Multi_Salt fit used a 126-pt 3x3 stratified subset, but the whole set is fit-provenance data | T | fit-eligible |
| phi_osm_harness | phi_osm | 101 | 75 pts at 298.15 K from Pitzer & Mayorga 1973 (JPC 77:2300, Tables I/VI) for NaCl/KCl/CaCl2/MgCl2/Na2SO4 — the Na2SO4 grid is capped at 2.2 mol/kg (TargetsT `TREND_SO4MAX`; Rard-Miller 1981 direct-data range, points above are correlation extrapolation); 26 pts Na2SO4 at 373.15 K digitized from Schlaikjer et al. 2018 Fig. 3 (P = 1.5 bar) | R (298 K) / T (373 K digitized) | fit-eligible |
| haas1976 | psat_ratio | 21 | Haas 1976, USGS Bulletin 1421-A, Tables 1/4/9/18: NaCl-brine vapor pressure P(m,T)/P(0,T) at m = 1, 3, 6 mol/kg and T = 373-523 K (7 isotherms); ratio construction identical to `TargetsT._append_vpsat`; 0-m column verified <0.1% vs IAPWS-95. `P_bar` left blank (pressure is the measured quantity, stored as ratio) | R | fit-eligible |
| koschel2006 | dh_sol | 22 | Koschel et al. 2006, FPE 247:107, Tables 4 (water) + 7 (1 m, 3 m NaCl): flow-calorimetric enthalpy of CO2 dissolution, kJ/mol CO2, 323/373 K, 2-20 MPa (stored in bar), author-stated ~5% (delta column) | T | test-only |
| yh2o_co2_binary | y_h2o | 452 | v0.1 addition (`build_y_h2o.py`): Multi_Salt `data/binaries_co2_water.parquet` (per-row author in `source`; raw per-isotherm tables under `source_materials/EoS/CO2/CPA/SRK/T*/EXP*.txt`, spot-verified). Gas-phase H2O mole fraction of the CO2-H2O binary, 278-623 K, 4.65-3500 bar, 12 authors (Todheide 1963, Takenouchi, Meyer 2015, Muller, Valtz 2004, Hou 2013, Bamberger 2000, King 1992, Sako 1991, Briones 1987, D'Souza, Dohrn). Hou/Muller/most-Todheide rows are complement-derived (source printed y_CO2; y_H2O = 1 - y_CO2, exact in a binary): those with y < 0.01 carry quality U (precision destroyed by the subtraction). R = cross-author agreement (dT<=2 K, dP<=2%, dy<=10%) | T (34 R, 12 U) | fit-eligible |
| yh2o_ch4_binary | y_h2o | 196 | same build: Multi_Salt `data/binaries_ch4_water.parquet` (raw tables `source_materials/EoS/CH4/CH4-Water/*/EXP*.txt`); all directly measured yw. CH4-H2O binary, 278-511 K, 4.9-1103 bar, 7 authors (Olds 1942, Chapoy 2003/2005, Yarrison 2006, Frost 2013, Qin 2008, Yokoyama 1988) | T (16 R) | fit-eligible |
| yh2o_co2_nacl_hou2013 | y_h2o | 36 | v0.2 addition, the FIRST brine water-content family (the salinity axis for y_H2O). Hou, Maitland, Trusler, JSCF 2013, 78, 78-88 ("HOU(2013b)"; distinct from the same group's binary "HOU" rows above), **Table 2** vapor column: y_H2O = 1 - y1(CO2) in the 2.5 / 4.0 mol/kg NaCl ternary, 323.15-423.15 K, 26-182 bar, per-point sampling sd carried in `uncertainty` (complement-derived but precision stated, so no U code). Transcription tables shared with the solubility rows in `hou2013.py` | T | test-only |
| yh2o_co2_kcl_hou2013 | y_h2o | 36 | same paper, **Table 3** vapor column: KCl ternary, same grid | T | test-only |
| yh2o_{ch4,n2,co2}_tabasinejad2011 | y_h2o | 38/39/40 | v0.3 (tables in `yh2o_sources_2026.py`): Tabasinejad et al., IECR 2011, 50, 4029, **Table 1** (p. 4034): water content of supercritical CH4 / N2 / CO2, 422.4-483.2 K, 3.7-134.9 MPa, per-point propagation-of-error uncertainties (mol %), u(T)=0.06 K, u(P)=0.25%. Opens the N2 axis; extends CH4/CO2 far beyond previous P coverage | T | test-only |
| yh2o_n2_mohammadi2005 | y_h2o | 35 | v0.3: Mohammadi, Chapoy, Tohidi, Richon, JCED 2005, 50, 541, **Table 2**: N2 water content 282.9-363.1 K, 0.43-4.96 MPa (GC-TCD, ROLSI sampling); author-stated worst-case TCD water-calibration accuracy 4% applied as per-point relative u | T | test-only |
| yh2o_ch4_mohammadi2004 | y_h2o | 17 | v0.3: Mohammadi, Chapoy, Richon, Tohidi, IECR 2004, 43, 7148, **Table 8** (NEW experimental block only; their Table 3 is a reference/range compilation with no primary values): CH4, 283.0-313.1 K, 0.51-2.85 MPa; stated worst-case 5% applied as per-point relative u. Same lab as CHAPOY(2003/2005) -- intra-lab agreement deliberately NOT counted as R | T | test-only |
| yh2o_c2h6_mohammadi2004 | y_h2o | 5 | same paper, **Table 9**: C2H6, 282.9-293.1 K, 0.51-2.99 MPa; opens the C2H6 axis | T | test-only |
| yh2o_c2h6_song1994 / yh2o_c3h8_song1994 | y_h2o | 4 + 4 | v0.3: Song & Kobayashi, FPE 1994, 95, 281, **Tables 3 / 2**: direct GC water content of the gas-rich phase along the three-phase locus, G-L_w rows ONLY (stated accuracy 5-6%, applied as 6% per-point relative u). SKIPPED: all hydrate-equilibrium rows (G-H, L_HC-H), all liquid-hydrocarbon-phase rows (L_HC-L_w), Table 4 (C2+C3 mixtures) and Table 5 (graphically smoothed values, partly from Parrish 1982) -- see `yh2o_sources_2026.py` | T | test-only |
| yh2o_co2_jooss2026 | y_h2o | 54 | v0.3: Jooss et al. (SINTEF), FPE 2026, 599, 114516, **Table 4**: CO2+H2O, 35-120 C, 1-70 MPa, GC with gravimetric calibration; printed EXPANDED (k=2) per-point uncertainties stored /2 as standard u | T | test-only |
| yh2o_co2_nacl_jooss2026 | y_h2o | 36 | same paper, **Table 5**: CO2+H2O+NaCl at tracked liquid-phase salt ratio S ~78 / ~150 g/kg (~1.34 / ~2.55 mol/kg; per-row S stored as molality m_Na=m_Cl=S/58.44277), 50/85/120 C, 1-70 MPa. SECOND independent lab on the brine y_H2O axis; S is the sample-withdrawal-corrected equilibrium value (paper Sec. 3.5), carried per row | T | test-only |
| yh2o_h2_torres2026 | y_h2o | 9 | v0.3: Torres et al., JCED 2026, 71, 2989, **Table 3**: H2 water content by differential scanning hygrometry (frost-point-derived, unlike the GC/gravimetric families), VLE rows only (283.15 / 273.15 K, 0.88-24.95 MPa); the 20 SVE rows (<= 263.15 K, ice equilibrium) are outside the y_h2o property scope and skipped. Printed U_c(k=2) stored /2. Opens the H2 axis | T | test-only |
| n2_osullivan1970 | solubility | 51 x2 | v0.4 (Part C of `build_v0.py`): O'Sullivan & Smith 1970, JPC 74:1460, **Table I** (p. 1461), N2 in water / 1 m / 4 m NaCl, 324.65-398.15 K, 100-608 atm (stored in bar). Printed X2 treats NaCl as UNDISSOCIATED; molality m = X2 (n_w + m_salt)/(1 - X2), xc_saltfree derived from m. Curated transcription: Multi_Salt `pilot_studies/n2_scoping_2026_07/n2_nacl_osullivan1970.csv` (400-dpi page-verified). The table's CH4 rows are already in ch4_part1 | T (some R) | test-only |
| c2h6_water | solubility | 116 x2 | v0.4: C2H6-H2O aqueous solubility -- Culberson-Horn-McKetta 1950 (30 pts) and Culberson-McKetta 1950 (45 pts) via the IUPAC SDS Vol 9 compiler sheets (Hayduk 1982, pp. 17-19; est. err 5% stored as u), plus Mohammadi et al. 2004 IECR 43:5418 Table 4 (41 pts, T >= 283 K). 283-444 K, 3.7-685 bar. Source csv: `pilot_studies/c2_pilot_2026_08/c2_water_data.csv`. NOTE: the C2H6 BRINE axis exists in IUPAC Vol 9 only as concentration-basis Setschenow constants (no per-point brine solubility), so c2h6 is water-only here | T (some R) | test-only |
| c3h8_water | solubility | 175 x2 | v0.4: C3H8-H2O aqueous solubility -- Kobayashi & Katz smoothed two-phase table (136 pts; Kobayashi 1951 PhD thesis / IEC 45:440) + Chapoy et al. 2004 FPE 226:213 (39 pts). 288-428 K, 3.9-207 bar. Source csv: `pilot_studies/c3_pilot_2026_08/c3_water_data.csv` (the exact Papers II/III fit/validation set). PHASE REGIME: 72 of the 136 Kobayashi points sit at or above propane's own vapor pressure below its critical temperature, i.e. the propane-rich phase is a LIQUID -- those 144 rows carry `lle-regime` and leave the gas-solubility set (QUALITY.md Sec. 7); the remaining Kobayashi points are either sub-saturation gas or supercritical (T > 369.89 K), and all 39 Chapoy points are sub-saturation | T (some R) | test-only (144 rows lle-regime) |
| c3h8_nacl_umano1958 | solubility | 135 x2 | v0.4: C3H8 in NaCl brines (0-5.32 mol/kg), Umano & Nakano 1958 via IUPAC SDS Vol 24 pp. 100-104 (`pilot_studies/c3_pilot_2026_08/raw/iupac24_propane_salts_umano_nacl.csv`). 273.2-298.2 K, ~0.1-1 atm total P (propane is well below its saturation pressure throughout: Psat(273.2 K) = 4.74 bar, so the whole block is genuine gas solubility). molality = printed mole ratio x n_w, verified against the source's own `p1_atm` propane partial-pressure column; `P_bar` stores the printed TOTAL pressure, the benchmark convention. sub-273 K isotherms not loaded; 5 transcriber-flagged misprint pts -> U. CAVEAT: within each isotherm the printed solubilities are not linear in propane partial pressure -- m/p1 rises by ~50 % from 0.1 to 1 atm and only flattens near 1 atm, where the values agree with the accepted Henry constant (Namiot 1961, 13800 atm at 273.15 K) to ~7 %. The sub-0.5 atm points are therefore the least reliable part of the block | T (5 pts U) | test-only |
| h2_nacl_brines | solubility | 40 | v0.4: direct H2 molality in NaCl brines, CHABAB(2024) 30 pts + TORIN(2022) 10 pts, 298-423 K, to 458 bar, 1-5 mol/kg (`pilot_studies/h2_scoping_2026_07/h2_nacl_brine.csv`; the file's CHABAB(2020) rows are the brine subset of chabab2020_t4 and are excluded as duplicates) | T | test-only |
| h2_water_binaries | solubility | 157 x2 | v0.4: aqueous H2 mole fraction of the salt-free binary, 10 authors, 273-589 K, to 1013 bar (`pilot_studies/h2_scoping_2026_07/h2_water_binaries.csv`; y-only rows skipped, CHABAB(2020) water pts excluded as duplicates; `h2_water_isobaric.csv` NOT loaded -- ZOSS(1952) is a secondary compilation, double-count risk) | T (some R) | test-only |
| eps_r_harness | eps_r | 13 | NaCl eps_r(m) at 298.15 K digitized from Maribo-Mogensen et al. 2013 Fig. 8 (+-2 units); LOW-WEIGHT harness block (kinetic-depolarization contamination) | T | fit-eligible |

## Construction notes

- The phi_osm / eps_r / psat_ratio rows are dumped from the trend_fix
  `TargetsT` object constructed with the exact `gate_tcoef.py`
  environment (`TREND_UNIFORM=1 TREND_TCOEF=1 TREND_VPSAT=1
  TREND_SO4MAX=2.2`); per-point sigma recovered from the weight
  vector via w_i = sqrt(B_k/N_k)/sigma_i.
- Molality <-> salt-free mole fraction conversions use
  `bench.core.conventions` only; u(molality) on converted rows is
  propagated as u_m = u_xc * n_w / (1-xc)^2.
- Chabab pressures reported in MPa (2021 tables) are stored in bar;
  the Hou 2013b MPa pressures likewise.
- Build/refresh order for the full database: `build_v0.py` (includes
  the Hou aqueous rows via `hou2013.py`), then `quality_pass.py`,
  then `build_y_h2o.py` (includes the Hou vapor rows and the v0.3
  batch from `yh2o_sources_2026.py`, and applies the Torres-2025 /
  Jooss-2026 review-based quality verdicts -- QUALITY.md Sec. 6).
- No numbers were invented: every new-extraction table was read from
  the rendered PDF pages and cross-checked against `pdftotext
  -layout` output; counts and spot values are locked in
  `tests/test_data.py`.

## Known deviations from the assignment brief

- Chabab 2020 Table 4 contains **37** H2 points, not 40.
- dos Santos Table 7 contains 30 rows; the "24 pts" of the brief are
  the mixed-salt subset (both included, distinguishable by m_SO4).
- `eps_r` added as a property beyond the assigned enum (harness
  block; drop the file if unwanted).
