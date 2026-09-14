"""Gas-phase water-content (y_h2o) transcription tables, 2026-09
acquisition batch (seven sources; consumed by build_y_h2o.py).

Same discipline as hou2013.py: every table below was transcribed from
the printed experimental tables of the source PDFs (papers/ directory)
and spot-verified against re-rendered page images.  Only experimental
tables are transcribed -- figures, smoothed/graphical values and
model columns are never used.  Author-flagged or physically
out-of-scope blocks are documented as SKIPPED, not silently dropped.

Sources
-------
1. TABASINEJAD(2011): F. Tabasinejad et al., "Water Solubility in
   Supercritical Methane, Nitrogen, and Carbon Dioxide: Measurement
   and Modeling from 422 to 483 K and Pressures from 3.6 to 134 MPa",
   IECR 50 (2011) 4029-4041, doi 10.1021/ie101218k.  **Table 1**
   (p. 4034): water content in mol % with per-point propagation-of-
   error uncertainties; u(T) = 0.06 K, u(P) = 0.25 %.  38 CH4 + 39 N2
   + 40 CO2 points, 422.44-483.15 K, 3.67-134.90 MPa.  Static
   pycnometer method (water-saturated gas transferred at constant
   pressure by positive-displacement pump).  Opens the N2 axis and
   extends CH4/CO2 y_H2O far beyond the previous 1103/3500 bar,
   511/623 K coverage of the binary family.

2. MOHAMMADI(2005): A.H. Mohammadi, A. Chapoy, B. Tohidi, D. Richon,
   "Water Content Measurement and Modeling in the Nitrogen + Water
   System", JCED 50 (2005) 541-545, doi 10.1021/je049676q.
   **Table 2** (p. 543): 35 points, y_H2O x 1e4, 282.86-363.08 K,
   0.425-4.962 MPa.  Static-analytic, ROLSI vapor sampling + GC-TCD;
   u(T) <= 0.02 K, u(P) <= 1 kPa; TCD water-calibration accuracy
   stated "in the worst case +/- 4 %" (Sec. 2.2) -- applied here as a
   per-point relative standard uncertainty (no per-point values are
   printed).  The y2prd model columns are NOT transcribed.

3. MOHAMMADI(2004): A.H. Mohammadi, A. Chapoy, D. Richon, B. Tohidi,
   "Gas Solubility: A Key to Estimating the Water Content of Natural
   Gases", IECR 43 (2004) 7148-7162, doi 10.1021/ie049843f.
   **Table 8** (p. 7157): 17 NEW experimental CH4 points (mol
   fraction x 1000), 282.98-313.12 K, 0.510-2.846 MPa.  **Table 9**
   (p. 7157): 5 NEW experimental C2H6 points, 282.93-293.10 K,
   0.506-2.990 MPa.  Same apparatus family as MOHAMMADI(2005); TCD
   water calibration "estimated in the worst case at +/- 5 %"
   (Sec. 4.2) -- applied as per-point relative standard uncertainty.
   Table 3 of the paper is a literature-review compilation of
   references and T/P RANGES only (no primary values) -- nothing to
   transcribe.  The model/AD% columns of Tables 8-9 are NOT
   transcribed.  NOTE: same laboratory (ENSMP/Heriot-Watt) as the
   CHAPOY(2003)/CHAPOY(2005) rows already in the family; their
   near-identical values at matched (T, P) are intra-lab replication,
   deliberately NOT counted as cross-source R agreement.

4. SONG(1994): K.Y. Song, R. Kobayashi, "The water content of ethane,
   propane and their mixtures in equilibrium with liquid water or
   hydrates", FPE 95 (1994) 281-298.  **Table 2** (p. 286,
   propane-water) and **Table 3** (p. 288, ethane-water): direct
   water-content measurements (splitter GC + ultrasonic detector) of
   the coexisting hydrocarbon-rich phases ALONG the three-phase
   locus; NOT dew-point measurements.  Stated accuracy of the
   reported water content: "within 5-6 %" (p. 289) -- applied here as
   a 6 % per-point relative standard uncertainty (conservative end).
   Only the G-L_w rows (gas-rich phase in equilibrium with liquid
   water; column 'Y_w x 10^3', the SMOOTHED column is not used) are
   transcribed: 4 C3H8 + 4 C2H6 points.  SKIPPED blocks (documented,
   not transcribed):
     * all hydrate-equilibrium rows (C3H8 159 psia L_HC-H block,
       7 pts; C2H6 360 psia G-H, 3 pts, and 500 psia L_HC-H, 5 pts):
       water content in equilibrium with HYDRATE, not liquid water --
       a different equilibrium that none of the benchmark models
       (vapor-aqueous flashes) represents;
     * all L_HC-L_w rows (water content of the liquid-hydrocarbon
       phase): not a gas-rich phase, outside the y_h2o property
       definition;
     * Table 4 (ethane-propane MIXTURES, x_C2 = 0.305/0.5/0.75):
       mixed-gas solvent, outside the single-gas schema;
     * Table 5: graphically smoothed chart values, partly reproduced
       from Parrish et al. (1982) -- not primary experimental data.
   No CO2 tables in this paper (its CO2 work is Song & Kobayashi
   1986/87, cited in the methods section only).
   T_K is computed from the printed deg-C column (+273.15); the
   printed psia/MPa pressures agree to <0.1 %; the MPa column is
   stored (x10 -> bar).

5. JOOSS(2026): Y. Jooss, A. Austegard, J.H. Stang, I.T. Roe,
   B. Strom, A. Aasen (SINTEF Energy Research), "Water content of
   the carbon dioxide-rich phase in CO2+H2O and CO2+H2O+NaCl
   systems", FPE 599 (2026) 114516.  **Table 4**: 54 CO2+H2O points,
   35-120 C (308.13-393.22 K), 1-70 MPa.  **Table 5**: 36
   CO2+H2O+NaCl points at salt mass ratios S ~ 78 and ~150
   g(NaCl)/kg(water) (~1.34 / ~2.55 mol/kg), 50/85/120 C, 1-70 MPa.
   Equilibrium cell + GC-TCD with gravimetric calibration mixtures;
   per-point EXPANDED uncertainties U_tot(y_w) at 95 % confidence
   (k = 2) are printed; stored here as STANDARD uncertainty
   U_tot / 2.  The per-row salt mass ratio S is the tracked
   liquid-phase value (see SALINITY note below) and is converted to
   molality via m = S / M_NaCl (M_NaCl = 58.44277 g/mol).
   SALINITY-CONVENTION note (paper Sec. 3.5 "Salt concentration",
   near-verbatim): the cell is filled to ~50 % of its volume with
   water/brine, then pressurized with CO2; "When CO2-Water mixtures
   are taken out of the cell, the water does not contain salt.  This
   means that the salt concentration increases slightly with every
   sample in the remaining brine.  The removed volume is tracked by
   following pressure, temperature in the cell and the volume of the
   bellow.  At high pressures the uncertainty increases due to
   slight gas leakage.  Thus the uncertainty increases when the
   brine has been in the cell for extended periods.  This is
   included in the uncertainty quantification."  I.e. the reported S
   is the CURRENT equilibrium-liquid salinity (feed corrected for
   cumulative water withdrawal), with its own per-point U(S) -- the
   drift is visible in the printed S column (e.g. 148.2 -> 155.3
   g/kg along the 85 C high-salt isotherm).  At least 7 independent
   samples per point; stirring 5 min + >= 1 min settling before
   sampling.

6. TORRES(2026): L.F. Torres et al., "Water Content of Hydrogen in
   Equilibrium with Ice or Liquid Water at Low Temperatures", JCED
   71 (2026) 2989-2995, doi 10.1021/acs.jced.6c00193 (CC-BY).
   **Table 3**: differential-scanning-hygrometry (DSH, frost-point)
   water content of H2; per-point expanded uncertainties U_c(y_w,
   k=2) printed (stored / 2); u(T) = 0.1 K, u(P) = 0.05 MPa.  Only
   the 9 VLE rows (283.15 K and 273.15 K, liquid-water equilibrium)
   are transcribed -- the 20 SVE rows (263.15-233.15 K, ICE-vapor
   equilibrium) are SKIPPED: outside the y_h2o property definition
   (water content over liquid water/brine) and outside every
   benchmark model's vapor-aqueous flash physics.  Opens the H2
   axis.  Measurement type: frost/dew-point (DSH) converted to water
   content at atmospheric analyzer pressure -- unlike the GC/
   gravimetric sources this is dew-point-derived; noted for
   provenance.

Row-tuple formats are documented above each table.
"""

# ---------------------------------------------------------------- 1.
# Tabasinejad et al. 2011, Table 1 (p. 4034).  (T_K, P_MPa, y_molpct,
# u_molpct); y_h2o = y_molpct / 100.
TABASINEJAD2011_CH4 = [
    (422.70,   3.67, 13.87, 1.07), (422.70,   7.18,  7.56, 0.35),
    (422.70,  14.24,  4.16, 0.13), (422.70,  21.26,  3.13, 0.08),
    (422.70,  27.91,  2.63, 0.06), (422.70,  35.32,  2.26, 0.05),
    (422.70,  41.62,  2.08, 0.04), (422.70,  68.66,  1.67, 0.03),
    (422.70, 107.03,  1.26, 0.03),
    (444.10,   3.87, 23.04, 1.61), (444.10,   7.31, 13.04, 0.52),
    (444.10,  14.60,  7.30, 0.17), (444.10,  19.83,  5.65, 0.11),
    (444.10,  27.86,  4.37, 0.08), (444.10,  34.53,  3.81, 0.06),
    (444.10,  40.36,  3.47, 0.05), (444.10,  69.29,  2.69, 0.03),
    (444.10,  96.24,  2.44, 0.03), (444.10, 133.39,  2.19, 0.02),
    (461.60,   4.10, 33.57, 2.21), (461.60,   7.65, 19.21, 0.74),
    (461.60,  14.66, 11.07, 0.25), (461.60,  21.62,  8.15, 0.14),
    (461.60,  29.29,  6.44, 0.09), (461.60,  36.62,  5.49, 0.07),
    (461.60,  42.33,  5.09, 0.06), (461.60,  68.37,  4.02, 0.04),
    (461.60, 102.15,  3.57, 0.03), (461.60, 121.13,  3.30, 0.03),
    (483.15,   7.40, 30.37, 1.17), (483.15,   7.78, 29.43, 1.08),
    (483.15,  14.85, 17.21, 0.36), (483.15,  21.17, 13.41, 0.21),
    (483.15,  29.47, 10.40, 0.13), (483.15,  37.06,  9.13, 0.10),
    (483.15,  45.66,  7.67, 0.07), (483.15,  73.30,  5.68, 0.05),
    (483.15, 104.08,  5.28, 0.04),
]

TABASINEJAD2011_N2 = [
    (422.44,   3.81, 13.12, 1.02), (422.44,   7.35,  7.09, 0.35),
    (422.44,  14.01,  3.97, 0.14), (422.44,  21.07,  2.90, 0.09),
    (422.44,  28.07,  2.35, 0.07), (422.44,  34.23,  1.95, 0.06),
    (422.44,  35.28,  1.90, 0.06), (422.44,  41.41,  1.73, 0.05),
    (422.44,  70.26,  1.32, 0.03), (422.44, 106.29,  0.92, 0.03),
    (445.60,   4.05, 22.89, 1.59), (445.60,   7.42, 13.00, 0.55),
    (445.60,  14.35,  7.44, 0.20), (445.60,  20.88,  5.74, 0.12),
    (445.60,  28.38,  4.57, 0.08), (445.60,  37.02,  3.80, 0.06),
    (445.60,  42.28,  3.48, 0.06), (445.60,  72.98,  2.64, 0.04),
    (445.60, 102.86,  2.14, 0.03), (445.60, 134.90,  1.81, 0.03),
    (461.60,   3.87, 33.85, 2.43), (461.60,   7.50, 18.77, 0.77),
    (461.60,  14.29, 10.97, 0.27), (461.60,  21.15,  8.05, 0.15),
    (461.60,  28.22,  6.90, 0.11), (461.60,  34.78,  5.80, 0.08),
    (461.60,  41.82,  5.08, 0.07), (461.60,  72.23,  3.79, 0.04),
    (461.60, 101.64,  2.89, 0.03), (461.60, 133.73,  2.60, 0.03),
    (483.15,   4.13, 51.15, 3.18), (483.15,   7.33, 31.16, 1.24),
    (483.15,  15.33, 16.87, 0.37), (483.15,  21.24, 12.93, 0.22),
    (483.15,  28.45, 10.29, 0.14), (483.15,  35.39,  8.91, 0.11),
    (483.15,  41.78,  8.01, 0.09), (483.15,  73.14,  5.60, 0.05),
    (483.15, 109.60,  4.33, 0.04),
]

TABASINEJAD2011_CO2 = [
    (422.98,   3.91, 13.85, 0.98), (422.98,   7.29,  8.22, 0.32),
    (422.98,  14.39,  5.57, 0.11), (422.98,  21.98,  4.59, 0.06),
    (422.98,  28.49,  4.47, 0.05), (422.98,  36.03,  4.47, 0.04),
    (422.98,  42.91,  4.58, 0.04), (422.98,  73.19,  4.82, 0.03),
    (422.98, 103.32,  5.07, 0.03), (422.98, 124.26,  5.18, 0.03),
    (445.74,   3.85, 25.00, 1.70), (445.74,   7.39, 14.29, 0.51),
    (445.74,  16.64,  8.78, 0.14), (445.74,  22.35,  7.45, 0.09),
    (445.74,  28.78,  7.07, 0.07), (445.74,  36.05,  7.04, 0.06),
    (445.74,  42.89,  7.10, 0.05), (445.74,  70.65,  7.37, 0.04),
    (445.74, 110.41,  7.52, 0.04), (445.74, 124.26,  7.57, 0.04),
    (461.62,   3.89, 34.60, 2.40), (461.62,   7.13, 21.18, 0.80),
    (461.62,  14.86, 12.99, 0.22), (461.62,  21.13, 10.56, 0.13),
    (461.62,  28.58,  9.87, 0.09), (461.62,  35.60,  9.65, 0.08),
    (461.62,  43.48,  9.46, 0.07), (461.62,  73.21,  9.67, 0.05),
    (461.62,  96.57,  9.83, 0.05), (461.62, 124.14, 10.03, 0.04),
    (478.35,   4.05, 47.04, 3.24), (478.35,   7.20, 29.96, 1.10),
    (478.35,  15.42, 17.45, 0.29), (478.35,  21.79, 14.76, 0.17),
    (478.35,  30.21, 12.98, 0.12), (478.35,  36.70, 13.08, 0.10),
    (478.35,  42.27, 12.91, 0.09), (478.35,  71.09, 13.00, 0.07),
    (478.35,  99.39, 13.32, 0.06), (478.35, 129.19, 13.24, 0.05),
]

# ---------------------------------------------------------------- 2.
# Mohammadi et al. 2005, Table 2 (p. 543).  (T_K, P_MPa, y_1e4);
# y_h2o = y_1e4 * 1e-4.  Relative std. uncertainty 4 % (see docstring).
MOHAMMADI2005_N2 = [
    (282.86, 0.607,   20.40), (282.99, 1.799,    7.14),
    (282.99, 3.036,    4.46), (283.03, 4.408,    3.17),
    (293.10, 0.558,   42.50), (293.19, 1.828,   13.60),
    (293.10, 2.991,    8.44), (293.10, 4.810,    5.58),
    (304.02, 0.578,   79.30), (304.36, 1.257,   37.00),
    (304.51, 2.539,   18.80), (304.61, 4.638,   11.20),
    (313.30, 0.498,  153.00), (313.15, 1.246,   60.90),
    (313.26, 2.836,   27.80), (313.16, 4.781,   17.50),
    (322.88, 0.499,  240.00), (323.10, 1.420,   87.20),
    (322.93, 3.397,   39.60), (322.93, 4.841,   29.20),
    (332.52, 0.461,  427.00), (332.45, 1.448,  134.00),
    (332.52, 2.454,   85.50), (332.52, 4.358,   48.80),
    (342.31, 0.425,  719.00), (342.31, 0.462,  658.00),
    (342.39, 1.466,  219.00), (342.42, 2.899,  103.00),
    (342.31, 4.962,   66.60), (351.87, 0.540,  849.00),
    (352.12, 1.480,  335.00), (351.92, 2.957,  162.00),
    (351.95, 4.797,  111.00), (363.00, 0.555, 1260.00),
    (363.08, 4.874,  161.00),
]

# ---------------------------------------------------------------- 3.
# Mohammadi et al. 2004, Tables 8-9 (p. 7157).  (T_K, P_MPa, y_1e3);
# y_h2o = y_1e3 * 1e-3.  Relative std. uncertainty 5 % (see docstring).
MOHAMMADI2004_CH4 = [
    (282.98, 1.147, 1.143), (283.08, 1.005, 1.240),
    (283.15, 1.003, 1.260), (288.11, 1.000, 1.780),
    (288.15, 1.005, 1.770), (293.01, 2.051, 1.170),
    (293.01, 0.992, 2.410), (293.01, 0.510, 4.640),
    (293.11, 0.990, 2.400), (297.97, 0.563, 5.690),
    (298.00, 1.697, 1.959), (298.01, 0.608, 5.193),
    (298.01, 2.846, 1.218), (298.11, 1.010, 3.270),
    (303.11, 1.030, 4.400), (308.11, 0.990, 5.820),
    (313.12, 1.090, 7.340),
]

MOHAMMADI2004_C2H6 = [
    (282.93, 0.506, 2.442), (288.11, 1.859, 1.031),
    (292.95, 1.049, 2.204), (293.10, 2.990, 0.832),
    (293.10, 1.926, 1.305),
]

# ---------------------------------------------------------------- 4.
# Song & Kobayashi 1994, Tables 2-3, G-L_w rows ONLY (see docstring
# for the skipped hydrate / liquid-phase / mixture blocks).
# (T_K, P_MPa, y_h2o); T_K = printed deg C + 273.15.  Relative std.
# uncertainty 6 % (stated 5-6 %, conservative end).
SONG1994_C3H8 = [
    (299.65, 0.897, 3.494e-3),     # 130   psia,  79.7 F / 26.5 C
    (292.65, 0.819, 2.668e-3),     # 118.7 psia,  67.1 F / 19.5 C
    (285.25, 0.679, 2.028e-3),     #  98.0 psia,  53.8 F / 12.1 C
    (281.95, 0.621, 2.000e-3),     #  90.0 psia,  47.9 F /  8.8 C
]

SONG1994_C2H6 = [
    (288.65, 3.421, 0.525e-3),     # 496   psia, 60.0 F / 15.5 C
    (294.45, 3.876, 0.650e-3),     # 562   psia, 70.4 F / 21.3 C
    (299.85, 4.345, 0.716e-3),     # 630   psia, 80.0 F / 26.7 C
    (303.75, 4.714, 0.736e-3),     # 683.5 psia, 87.0 F / 30.6 C
]

# ---------------------------------------------------------------- 5.
# Jooss et al. 2026, Table 4 (CO2 + H2O).  (T_C, P_MPa, y_pct,
# Utot_ppm); y_h2o = y_pct / 100; std. uncertainty = Utot_ppm/2 * 1e-6
# (printed value is expanded, k = 2).
JOOSS2026_CO2 = [
    (34.99,   1.0,  0.636, 150.7), (34.99,   2.0,  0.345, 226.2),
    (34.98,   4.0,  0.220, 370.4), (34.98,   6.0,  0.205, 403.2),
    (34.98,   7.0,  0.209, 392.3), (35.00,   8.0,  0.291, 270.9),
    (34.98,   9.0,  0.380, 203.2), (34.98,  19.0,  0.467, 165.4),
    (35.00,  30.0,  0.492, 156.0),
    (50.00,   1.0,  1.363, 731.8), (50.18,   3.5,  0.468, 170.9),
    (50.19,   6.0,  0.348, 226.5), (50.19,   7.3,  0.345, 228.7),
    (50.19,   7.8,  0.333, 235.9), (50.19,   8.4,  0.347, 223.5),
    (50.20,  12.0,  0.527, 152.1), (50.19,  17.5,  0.637, 285.0),
    (50.01,  42.0,  0.724, 156.3),
    (65.00,   1.0,  2.622, 193.7), (65.00,   2.0,  1.399, 170.5),
    (65.00,   6.0,  0.644, 154.5), (65.00,   9.0,  0.579, 155.4),
    (65.01,  11.0,  0.615, 149.5), (65.00,  17.0,  0.833, 150.4),
    (64.99,  27.0,  0.968, 156.0), (64.99,  42.0,  1.028, 151.8),
    (64.99,  52.0,  1.048, 151.4),
    (85.01,   1.0,  6.055, 265.1), (85.01,   2.0,  3.178, 203.1),
    (85.00,   6.0,  1.358,  82.1), (85.01,  10.0,  1.115,  68.6),
    (85.01,  14.0,  1.141,  58.1), (85.01,  19.0,  1.297,  86.5),
    (85.01,  27.0,  1.460,  77.7), (85.02,  42.0,  1.570, 100.2),
    (85.01,  70.0,  1.653, 112.1),
    (95.02,   1.0,  8.852, 536.0), (95.02,   2.0,  4.633, 272.9),
    (95.02,   4.0,  2.552, 214.7), (95.02,  10.0,  1.486, 207.1),
    (95.02,  13.0,  1.436, 190.4), (95.02,  18.0,  1.541, 175.6),
    (95.03,  27.0,  1.686, 169.2), (95.05,  42.0,  1.922, 247.4),
    (95.05,  70.0,  2.049, 227.3),
    (120.02,  2.0, 10.842, 253.9), (120.01,  4.0,  5.873, 211.5),
    (120.00,  8.0,  3.551, 297.3), (120.02, 11.0,  3.010, 273.2),
    (120.01, 16.0,  2.730, 222.1), (120.01, 22.0,  2.791, 191.6),
    (120.01, 27.0,  2.908, 168.4), (120.06, 42.0,  3.115, 241.9),
    (120.07, 70.0,  3.347, 260.6),
]

# Jooss et al. 2026, Table 5 (CO2 + H2O + NaCl).  (T_C, P_MPa,
# S_g_per_kg, y_pct, Utot_ppm); molality = S / 58.44277.
JOOSS2026_CO2_NACL = [
    (50.00,   1.0, 148.2, 1.262, 163.7), (50.01,  2.8, 148.9, 0.495, 156.4),
    (50.01,   3.5, 148.9, 0.424, 182.5), (50.00,  6.0, 148.9, 0.308, 254.8),
    (50.01,   7.3, 148.9, 0.291, 269.8), (50.01,  8.4, 148.9, 0.305, 256.8),
    (50.01,  12.0, 148.9, 0.460, 168.0), (50.01, 17.5, 148.9, 0.536, 155.6),
    (50.00,  42.0, 148.9, 0.634, 155.0),
    (84.99,   1.0,  77.7, 5.822, 272.4), (84.99,  2.0,  77.7, 3.068, 198.2),
    (84.98,   6.0,  77.7, 1.298, 155.0), (84.99, 10.0,  77.8, 1.043, 150.9),
    (84.99,  14.0,  77.8, 1.070, 160.4), (84.99, 19.0,  78.0, 1.217, 156.0),
    (84.99,  27.0,  78.4, 1.360, 159.2), (84.99, 42.0,  78.9, 1.477, 171.7),
    (85.00,  70.0,  79.5, 1.576, 318.6),
    (85.05,   1.0, 149.6, 5.479, 233.8), (85.05,  2.0, 149.6, 2.857, 183.3),
    (84.97,   6.0, 149.9, 1.185, 157.4), (84.97, 10.0, 150.3, 0.952, 153.6),
    (84.97,  14.0, 151.1, 0.966, 157.7), (84.97, 19.0, 152.0, 1.112, 155.1),
    (85.00,  27.0, 153.9, 1.256, 161.9), (85.00, 42.0, 155.3, 1.368, 178.0),
    (84.98,  70.0, 149.6, 1.470, 248.6),
    (120.03,  2.0, 145.3, 9.860, 262.6), (120.03,  4.0, 145.4, 5.350, 246.1),
    (120.02,  8.0, 145.7, 3.192, 206.6), (120.03, 11.0, 145.9, 2.696, 165.9),
    (120.02, 16.0, 146.3, 2.456, 200.7), (120.00, 21.5, 153.5, 2.459, 195.5),
    (120.03, 27.0, 147.0, 2.606, 171.3), (120.03, 42.0, 149.0, 2.759, 198.4),
    (120.04, 70.0, 152.0, 2.924, 253.8),
]

# ---------------------------------------------------------------- 6.
# Torres et al. 2026, Table 3, VLE rows ONLY (283.15 / 273.15 K; the
# 20 SVE ice-equilibrium rows are skipped -- see docstring).
# (T_K, P_MPa, y_ppm, Uc_k2_ppm); std. uncertainty = Uc/2 * 1e-6.
TORRES2026_H2 = [
    (283.15,  5.52, 262.0,  7.5), (283.15, 12.41, 134.3, 4.0),
    (283.15, 15.86, 110.7,  3.3), (283.15, 24.83,  88.9, 2.7),
    (273.15,  0.88, 745.9, 41.7), (273.15,  4.74, 143.2, 8.6),
    (273.15,  9.70,  76.3,  4.7), (273.15, 15.23,  52.8, 3.3),
    (273.15, 24.95,  38.3,  2.4),
]

M_NACL_G = 58.44277        # g/mol (IUPAC 2021), for Jooss S -> molality

#: dataset_id / source / gas registry for build_y_h2o.py
DATASETS = {
    "yh2o_ch4_tabasinejad2011":  ("TABASINEJAD(2011)", "ch4"),
    "yh2o_n2_tabasinejad2011":   ("TABASINEJAD(2011)", "n2"),
    "yh2o_co2_tabasinejad2011":  ("TABASINEJAD(2011)", "co2"),
    "yh2o_n2_mohammadi2005":     ("MOHAMMADI(2005)",   "n2"),
    "yh2o_ch4_mohammadi2004":    ("MOHAMMADI(2004)",   "ch4"),
    "yh2o_c2h6_mohammadi2004":   ("MOHAMMADI(2004)",   "c2h6"),
    "yh2o_c2h6_song1994":        ("SONG(1994)",        "c2h6"),
    "yh2o_c3h8_song1994":        ("SONG(1994)",        "c3h8"),
    "yh2o_co2_jooss2026":        ("JOOSS(2026)",       "co2"),
    "yh2o_co2_nacl_jooss2026":   ("JOOSS(2026)",       "co2"),
    "yh2o_h2_torres2026":        ("TORRES(2026)",      "h2"),
}


def points():
    """Yield (dataset_id, T_K, P_bar, y_h2o, u_y, m_nacl) for every
    transcribed point (m_nacl = 0 for the salt-free datasets)."""
    for tab, did in ((TABASINEJAD2011_CH4, "yh2o_ch4_tabasinejad2011"),
                     (TABASINEJAD2011_N2,  "yh2o_n2_tabasinejad2011"),
                     (TABASINEJAD2011_CO2, "yh2o_co2_tabasinejad2011")):
        for T, p_MPa, y_pct, u_pct in tab:
            yield did, T, p_MPa * 10.0, y_pct / 100.0, u_pct / 100.0, 0.0
    for T, p_MPa, y4 in MOHAMMADI2005_N2:
        y = y4 * 1e-4
        yield ("yh2o_n2_mohammadi2005", T, p_MPa * 10.0, y, 0.04 * y, 0.0)
    for tab, did in ((MOHAMMADI2004_CH4, "yh2o_ch4_mohammadi2004"),
                     (MOHAMMADI2004_C2H6, "yh2o_c2h6_mohammadi2004")):
        for T, p_MPa, y3 in tab:
            y = y3 * 1e-3
            yield did, T, p_MPa * 10.0, y, 0.05 * y, 0.0
    for tab, did in ((SONG1994_C2H6, "yh2o_c2h6_song1994"),
                     (SONG1994_C3H8, "yh2o_c3h8_song1994")):
        for T, p_MPa, y in tab:
            yield did, T, p_MPa * 10.0, y, 0.06 * y, 0.0
    for T_C, p_MPa, y_pct, u_ppm in JOOSS2026_CO2:
        yield ("yh2o_co2_jooss2026", T_C + 273.15, p_MPa * 10.0,
               y_pct / 100.0, u_ppm / 2.0 * 1e-6, 0.0)
    for T_C, p_MPa, S, y_pct, u_ppm in JOOSS2026_CO2_NACL:
        yield ("yh2o_co2_nacl_jooss2026", T_C + 273.15, p_MPa * 10.0,
               y_pct / 100.0, u_ppm / 2.0 * 1e-6, S / M_NACL_G)
    for T, p_MPa, y_ppm, u_ppm in TORRES2026_H2:
        yield ("yh2o_h2_torres2026", T, p_MPa * 10.0, y_ppm * 1e-6,
               u_ppm / 2.0 * 1e-6, 0.0)
