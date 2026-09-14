"""Hou, Maitland & Trusler 2013b transcription tables (shared by
build_v0.py and build_y_h2o.py).

Source: S.-X. Hou, G.C. Maitland, J.P.M. Trusler, "Phase equilibria
of (CO2 + H2O + NaCl) and (CO2 + H2O + KCl): Measurements and
modeling", J. Supercrit. Fluids 78 (2013) 78-88,
doi 10.1016/j.supflu.2013.03.022.  Local PDF:
EoS_Benchmark/papers/Hou2013_CO2_H2O_NaCl_KCl_phase_equilibria_JSCF
.pdf.  "2013b" distinguishes this ternary paper from the same
group's (CO2 + H2O) binary study (JSCF 73 (2013) 87-96, ref [22]
therein), whose data already sit in y_h2o.csv under source "HOU".

Tables transcribed (page-image verified, columns m / T / p_exp /
x1'_exp +/- sd / y1_exp +/- sd; the p_cal / y1_cal model columns are
NOT transcribed):

    Table 2 (paper p. 82): CO2 (1) + H2O (2) + NaCl (3), 36 points.
    Table 3 (paper p. 83): CO2 (1) + H2O (2) + KCl  (3), 36 points.

Both tables: brine molalities m = 2.5 and 4.0 mol/kg, isotherms
T = 323.15 / 373.15 / 423.15 K, p = 2.6-18.2 MPa (six pressures per
isotherm).  This is the FIRST brine (saline) gas-phase water-content
family in the benchmark database.

Reported quantities and units (Sec 2.3 of the paper):

* ``x1`` = x1', the SALT-FREE liquid-phase CO2 mole fraction,
  x1' = n1/(n1 + n2) (Eq 1) -- exactly the database's
  ``xc_saltfree`` convention; Eq 2 of the paper converts to the
  true (salt-inclusive) fraction, which we do not store.
* ``y1`` = vapor-phase CO2 mole fraction.  The vapor is binary
  (CO2 + H2O; the salts are involatile), so the water content is
  y_H2O = 1 - y1 exactly, with the same standard deviation.
* ``m`` = molality of the brine LOADED into the apparatus (mol salt
  per kg water).  The authors' mass-balance analysis bounds the
  equilibrium liquid molality shift at <= 0.8 % (worst case highest
  T and p); we store the stated feed molality.
* The +/- values are standard deviations of the ~10 replicate GC
  samples per phase per point (sampling reproducibility, which the
  authors state dominates over the GC-calibration uncertainty).
  Additional stated uncertainties: brine molality 0.4 % relative
  (gravimetric preparation + salt purity), T within +/- 0.03 K.

No author-flagged points in either table.  Quality "T" throughout
(single-lab measurement); tag "test-only" (published after every
fit lineage in this benchmark; never a fit target).  y_H2O is
complement-derived (1 - y1) but, unlike the U-coded complement rows
of the binary family, its precision IS verifiable here because the
per-point standard deviation of y1 is printed.

Row tuples: (m_salt, T_K, p_MPa, x1_sf, u_x1, y1_co2, u_y1).
"""

# Table 2 -- CO2 (1) + H2O (2) + NaCl (3), paper p. 82.
HOU2013_NACL = [
    # m = 2.5 mol/kg
    (2.5, 323.15,  2.782, 0.00492, 4.38e-5, 0.99637, 3.06e-5),
    (2.5, 323.15,  5.739, 0.00875, 7.45e-5, 0.99767, 2.67e-5),
    (2.5, 323.15,  8.730, 0.01146, 2.10e-4, 0.99782, 1.87e-5),
    (2.5, 323.15, 11.773, 0.01238, 3.54e-4, 0.99734, 1.56e-5),
    (2.5, 323.15, 15.020, 0.01293, 5.97e-5, 0.99626, 1.79e-5),
    (2.5, 323.15, 18.211, 0.01335, 5.59e-5, 0.99591, 1.70e-5),
    (2.5, 373.15,  2.613, 0.00261, 3.33e-5, 0.97097, 6.96e-5),
    (2.5, 373.15,  5.742, 0.00545, 1.79e-4, 0.98828, 2.84e-4),
    (2.5, 373.15,  8.789, 0.00745, 1.63e-4, 0.98936, 9.33e-5),
    (2.5, 373.15, 11.867, 0.00911, 2.37e-4, 0.99045, 7.16e-5),
    (2.5, 373.15, 14.921, 0.01039, 2.49e-4, 0.98917, 5.49e-5),
    (2.5, 373.15, 18.013, 0.01139, 1.44e-4, 0.98844, 1.27e-4),
    (2.5, 423.15,  2.643, 0.00193, 3.24e-5, 0.81441, 8.12e-4),
    (2.5, 423.15,  5.766, 0.00440, 1.17e-4, 0.89845, 2.08e-4),
    (2.5, 423.15,  8.600, 0.00640, 4.19e-5, 0.92433, 5.47e-4),
    (2.5, 423.15, 11.604, 0.00824, 2.32e-5, 0.93769, 1.98e-4),
    (2.5, 423.15, 14.881, 0.01014, 1.07e-4, 0.94636, 4.19e-4),
    (2.5, 423.15, 17.794, 0.01137, 1.26e-4, 0.94978, 2.65e-4),
    # m = 4.0 mol/kg
    (4.0, 323.15,  2.983, 0.00403, 3.54e-5, 0.99706, 2.16e-5),
    (4.0, 323.15,  5.954, 0.00697, 3.74e-5, 0.99809, 1.90e-5),
    (4.0, 323.15,  8.953, 0.00875, 2.23e-5, 0.99836, 2.26e-5),
    (4.0, 323.15, 12.017, 0.00956, 3.91e-5, 0.99760, 1.37e-5),
    (4.0, 323.15, 14.959, 0.00997, 9.14e-5, 0.99651, 1.85e-5),
    (4.0, 323.15, 17.954, 0.01025, 7.23e-5, 0.99609, 3.07e-5),
    (4.0, 373.15,  2.951, 0.00251, 3.48e-5, 0.98581, 2.03e-4),
    (4.0, 373.15,  6.068, 0.00466, 4.55e-5, 0.99098, 6.27e-5),
    (4.0, 373.15,  8.916, 0.00620, 7.85e-5, 0.99189, 4.94e-5),
    (4.0, 373.15, 12.003, 0.00752, 1.03e-4, 0.99258, 6.86e-5),
    (4.0, 373.15, 14.924, 0.00857, 1.57e-4, 0.99153, 7.87e-5),
    (4.0, 373.15, 18.162, 0.00924, 1.17e-4, 0.99055, 1.38e-4),
    (4.0, 423.15,  3.093, 0.00195, 1.40e-5, 0.84561, 1.13e-3),
    (4.0, 423.15,  5.816, 0.00375, 3.79e-5, 0.91331, 6.03e-4),
    (4.0, 423.15,  8.857, 0.00555, 3.53e-5, 0.93732, 1.99e-4),
    (4.0, 423.15, 11.922, 0.00709, 2.90e-5, 0.94690, 2.34e-4),
    (4.0, 423.15, 14.979, 0.00844, 1.13e-4, 0.95328, 1.81e-4),
    (4.0, 423.15, 18.079, 0.00965, 1.06e-4, 0.95696, 1.46e-4),
]

# Table 3 -- CO2 (1) + H2O (2) + KCl (3), paper p. 83.
HOU2013_KCL = [
    # m = 2.5 mol/kg
    (2.5, 323.15,  2.920, 0.00638, 1.98e-4, 0.99609, 3.65e-5),
    (2.5, 323.15,  5.895, 0.01139, 3.43e-4, 0.99759, 3.96e-5),
    (2.5, 323.15,  8.880, 0.01411, 2.20e-4, 0.99778, 2.02e-5),
    (2.5, 323.15, 11.774, 0.01545, 9.78e-5, 0.99728, 3.16e-5),
    (2.5, 323.15, 15.062, 0.01616, 1.06e-4, 0.99620, 1.73e-5),
    (2.5, 323.15, 18.078, 0.01671, 1.09e-4, 0.99587, 3.12e-5),
    (2.5, 373.15,  2.945, 0.00331, 3.47e-5, 0.96912, 1.65e-4),
    (2.5, 373.15,  6.080, 0.00629, 7.76e-5, 0.98756, 1.49e-4),
    (2.5, 373.15,  9.071, 0.00862, 8.07e-5, 0.98834, 1.58e-4),
    (2.5, 373.15, 12.032, 0.01035, 4.35e-5, 0.98930, 1.85e-4),
    (2.5, 373.15, 14.874, 0.01163, 7.29e-5, 0.98780, 1.26e-4),
    (2.5, 373.15, 17.883, 0.01273, 1.43e-4, 0.98734, 9.63e-5),
    (2.5, 423.15,  2.745, 0.00217, 2.27e-5, 0.81118, 4.25e-4),
    (2.5, 423.15,  6.074, 0.00510, 3.68e-5, 0.89888, 2.85e-4),
    (2.5, 423.15,  8.889, 0.00753, 1.73e-4, 0.92425, 1.64e-4),
    (2.5, 423.15, 11.957, 0.00939, 4.80e-5, 0.93775, 3.72e-4),
    (2.5, 423.15, 14.958, 0.01135, 1.83e-4, 0.94545, 2.89e-4),
    (2.5, 423.15, 17.858, 0.01282, 7.86e-5, 0.94906, 3.29e-4),
    # m = 4.0 mol/kg
    (4.0, 323.15,  3.027, 0.00552, 5.51e-5, 0.99660, 9.28e-5),
    (4.0, 323.15,  5.959, 0.00939, 7.34e-5, 0.99801, 7.21e-5),
    (4.0, 323.15,  8.998, 0.01167, 4.92e-5, 0.99823, 2.59e-5),
    (4.0, 323.15, 12.084, 0.01270, 4.26e-5, 0.99753, 5.13e-5),
    (4.0, 323.15, 15.036, 0.01312, 9.52e-5, 0.99638, 4.51e-5),
    (4.0, 323.15, 18.184, 0.01353, 6.87e-5, 0.99598, 4.21e-5),
    (4.0, 373.15,  3.025, 0.00301, 4.87e-5, 0.98351, 1.26e-4),
    (4.0, 373.15,  6.023, 0.00558, 5.83e-5, 0.99056, 1.14e-4),
    (4.0, 373.15,  8.978, 0.00757, 7.79e-5, 0.99156, 8.59e-5),
    (4.0, 373.15, 12.032, 0.00908, 4.37e-5, 0.99233, 9.25e-5),
    (4.0, 373.15, 15.103, 0.01041, 4.34e-5, 0.99062, 1.87e-4),
    (4.0, 373.15, 18.215, 0.01121, 7.28e-5, 0.98962, 1.02e-4),
    (4.0, 423.15,  2.908, 0.00198, 3.43e-5, 0.83993, 9.79e-4),
    (4.0, 423.15,  5.957, 0.00417, 9.12e-5, 0.91001, 6.40e-4),
    (4.0, 423.15,  8.984, 0.00612, 4.42e-5, 0.93520, 5.49e-4),
    (4.0, 423.15, 12.035, 0.00785, 7.95e-5, 0.94505, 5.48e-4),
    (4.0, 423.15, 14.991, 0.00942, 5.34e-5, 0.95233, 2.16e-4),
    (4.0, 423.15, 18.120, 0.01084, 4.28e-5, 0.95678, 9.41e-5),
]

TABLES = {"NaCl": HOU2013_NACL, "KCl": HOU2013_KCL}

#: y_h2o.csv identity per salt: (dataset_id, source)
Y_DATASETS = {"NaCl": "yh2o_co2_nacl_hou2013",
              "KCl": "yh2o_co2_kcl_hou2013"}
#: solubility.csv identity per salt (pdf-extraction convention of
#: build_v0.py: dataset_id hou2013_t<n>, source Hou2013_JSCF78_T<n>)
SOL_DATASETS = {"NaCl": ("hou2013_t2", "Hou2013_JSCF78_T2"),
                "KCl": ("hou2013_t3", "Hou2013_JSCF78_T3")}
Y_SOURCE = "HOU(2013b)"


def y_h2o_points():
    """Yield (dataset_id, salt, m, T_K, P_bar, y_h2o, u) with
    y_H2O = 1 - y1 (binary CO2+H2O vapor; salts involatile)."""
    for salt, table in TABLES.items():
        did = Y_DATASETS[salt]
        for m, T, p_MPa, _x, _ux, y1, u_y1 in table:
            yield did, salt, m, T, p_MPa * 10.0, 1.0 - y1, u_y1


def solubility_points():
    """Yield (dataset_id, source, salt, m, T_K, P_bar, x_sf, u) for
    the liquid-phase (salt-free basis) rows."""
    for salt, table in TABLES.items():
        did, src = SOL_DATASETS[salt]
        for m, T, p_MPa, x_sf, u_x, _y, _uy in table:
            yield did, src, salt, m, T, p_MPa * 10.0, x_sf, u_x
