#!/usr/bin/env python3
"""Build benchmark database v0 (gas-brine EoS comparison paper).

Writes one csv per property family into this directory, plus a
combined parquet:

    solubility.csv   solubility_molality + xc_saltfree rows
    rho.csv          brine density rows
    phi_osm.csv      osmotic-coefficient rows
    psat_ratio.csv   Haas (1976) NaCl vapor-pressure ratios
    dh_sol.csv       Koschel (2006) CO2 enthalpy of solution
    eps_r.csv        NaCl static-permittivity rows (schema extension)
    benchmark_v0.parquet   all of the above concatenated

Schema (every csv, identical column order):
    dataset_id, source, gas, property, T_K, P_bar,
    m_Na, m_Cl, m_K, m_Ca, m_Mg, m_SO4,
    value, uncertainty, quality, tag

Conventions:
    - gas = '' for gas-free rows (rho, phi_osm, psat_ratio, eps_r).
    - property in {solubility_molality, xc_saltfree, y_h2o, rho,
      phi_osm, psat_ratio, dh_sol, eps_r}  (eps_r is an extension
      beyond the assigned enum; see README.md).
    - molalities mol/kg-water in the frozen (Na, Cl, K, Ca, Mg, SO4)
      ion order of bench.core.base.IONS.
    - uncertainty: experimental standard uncertainty where the source
      states one; for the Multi_Salt harness targets it is the
      harness-ASSIGNED 1-sigma weight (see README.md); blank where
      unknown.
    - quality: R/T/U per Yang et al. 2022 IECR 61:15576 Sec 5.2
      (R = evaluated/verified compilation, T = tentative/plausible
      single source [default], U = author-flagged or unverifiable).
    - tag: fit-eligible (was a fit target in the Multi_Salt work),
      test-only (never fitted; prediction/benchmark data), or
      lle-regime (see below).

Sources of the curated blocks (converted, not re-curated):
    - CO2/CH4 single-salt DBs:  Multi_Salt/code/data/{co2,ch4}_brines
      .parquet (Part-1 databases; CO2 511 pts as salt-free mole
      fraction xc_W, CH4 469 pts in 284-532 K as molality mh_W) --
      the exact frames returned by phase4_cofit.load_co2/load_ch4.
    - mixed-brine CO2: Multi_Salt/code/data/co2_mixed_brines.parquet
      (298 pts, 9 authors; the phase3b_shyd stage-b3 prediction set).
    - phi_osm / rho / eps_r / psat_ratio: the trend_fix TargetsT
      harness target sets (gate_tcoef.py env: TREND_UNIFORM=1,
      TREND_TCOEF=1, TREND_VPSAT=1, TREND_SO4MAX=2.2), plus the full
      905-point Al Ghafri density frame (TargetsT.rho_all).
    - dh_sol: koschel_enthalpy_2026_08/koschel_data.csv (22 pts,
      Koschel et al. 2006 FPE 247:107 Tables 4 and 7).

NEW per-point extractions from PDFs in EoS_Benchmark/papers (each
literal table below carries its own citation; page-image verified):
    - Chabab et al. 2019 IJGGC 91:102825, Table 2 (21 CO2 pts).
    - Chabab et al. 2020 IJHE 45:32206, Table 4 (37 H2 pts).
    - Chabab et al. 2021 JCED 66:609, Table 2 (14 CO2 pts at 6 m)
      and Table 3 (44 O2 pts).
    - dos Santos et al. 2021 Chem. Geol. 582:120443, Table 7
      (30 pts: 6 single-salt 6m NaCl + 24 mixed 3m NaCl + 1m Na2SO4).
    - Hou, Maitland, Trusler 2013 JSCF 78:78-88, Tables 2 and 3
      (36 NaCl + 36 KCl CO2 pts; aqueous-phase x1' salt-free rows.
      The tables' VAPOR-phase y1 rows go to y_h2o.csv via
      build_y_h2o.py; both draw on the shared transcription module
      bench/data/hou2013.py).

Part C (v0.4, 2026-09): transfer-gas solubility (N2, C2H6, C3H8 +
new H2 water/brine sources), converted from the curated Multi_Salt
pilot-study CSVs (the Papers II/III additional-gas validation data;
converted, not re-curated -- same discipline as Part A).  Every
Part-C row is tag=test-only: these gases are the PREDICTION-ONLY
transferability axis of the benchmark and are outside every refit
objective (the c3/c5 refit rounds were frozen before these rows
existed).  Per-builder provenance and basis conversions are in the
build_* docstrings below; the C2H6 brine axis exists in the IUPAC
compilation only as concentration-basis Setschenow constants (no
per-point brine solubility), so C2H6 enters water-only.

PHASE-REGIME SCREEN (v0.5, 2026-09): the condensable hydrocarbons
carry rows on BOTH sides of their own vapor-pressure line.  Below the
hydrocarbon's critical temperature and at or above its saturation
pressure the hydrocarbon-rich phase is a LIQUID, and the measurement
is liquid-liquid mutual solubility rather than gas solubility.  Those
rows are retagged tag="lle-regime" by _regime_tag() against the
reference-EoS saturation line and are excluded from the default
scored set; see QUALITY.md ("Phase-regime classification").

Run (needs the Multi_Salt tree for the curated blocks):
    PYTHONPATH=/path/to/EoS_Benchmark/code \
        python3 bench/data/build_v0.py
The Multi_Salt code root defaults to the sibling checkout and can be
overridden with env ECPA_MS_CODE.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent          # .../code/bench/data
# The builders moved from the old bench/data tree into tools/builders/,
# where `HERE` is no longer the data directory; writing the CSVs beside the
# script left data/*.csv stale. Target the repository's data/ explicitly.
DATA_DIR = HERE.parents[1] / "data"             # .../GasBrineBench/data
CODE = HERE.parents[1]                          # .../code
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from bench.core.base import IONS                            # noqa: E402
from bench.core.conventions import (                        # noqa: E402
    M_W, mi_from_salt, molality_to_xc_saltfree,
    xc_saltfree_to_molality)

# Curation artefacts held in a maintainer-local sibling checkout. Not part of
# this repository; the original default was an absolute path on the build
# machine and has been replaced by the environment variable it always honoured.
MS_CODE = Path(os.environ.get("ECPA_MS_CODE", "Multi_Salt/code"))

COLUMNS = ["dataset_id", "source", "gas", "property", "T_K", "P_bar",
           "m_Na", "m_Cl", "m_K", "m_Ca", "m_Mg", "m_SO4",
           "value", "uncertainty", "quality", "tag"]

N_W = 1.0 / M_W          # mol water per kg water


def row(dataset_id, source, gas, prop, T_K, P_bar, mi, value,
        uncertainty=None, quality="T", tag="test-only"):
    r = dict(dataset_id=dataset_id, source=source, gas=gas,
             property=prop, T_K=float(T_K),
             P_bar=(float(P_bar) if P_bar is not None else np.nan),
             value=float(value),
             uncertainty=(float(uncertainty)
                          if uncertainty is not None else np.nan),
             quality=quality, tag=tag)
    for k, v in zip(IONS, mi):
        r["m_" + k] = float(v)
    return r


def u_molality_from_u_xc(u_xc, xc):
    """Propagate u(xc_saltfree) -> u(molality): dm/dxc = n_w/(1-xc)^2."""
    return u_xc * N_W / (1.0 - xc) ** 2


# --------------------------------------------------------------------
# Part A -- curated Multi_Salt assets (converted, not re-curated)
# --------------------------------------------------------------------

def build_co2_part1():
    """511-pt Part-1 CO2 single-salt DB (xc_W = salt-free mole
    fraction). Emits BOTH an xc_saltfree and a converted
    solubility_molality row per point."""
    df = pd.read_parquet(MS_CODE / "data" / "co2_brines.parquet")
    assert len(df) == 511, len(df)
    out = []
    for r in df.itertuples():
        mi = [r.m_Na, r.m_Cl, r.m_K, r.m_Ca, r.m_Mg, r.m_SO4]
        common = dict(dataset_id="co2_part1", source=r.author,
                      gas="co2", T_K=r.T_K, P_bar=r.P_bar, mi=mi,
                      quality="T", tag="fit-eligible")
        out.append(row(prop="xc_saltfree", value=r.xc_W, **common))
        out.append(row(prop="solubility_molality",
                       value=xc_saltfree_to_molality(r.xc_W), **common))
    return out


FIT_T_MIN, FIT_T_MAX = 284.0, 532.0     # phase4_cofit.load_ch4 T_MIN/T_MAX


def build_ch4_part1():
    """533-pt Part-1 CH4 single-salt DB (mh_W is molality already).

    The whole compilation is published; the fit window is carried in
    `tag` rather than by dropping rows. Inside 284-532 K
    (phase4_cofit.load_ch4, line 142) the 469 points are the set the
    gas-ion energies were fitted against -> fit-eligible. Outside it,
    the 64 Susak & McGee 1980 points on the 548/573/598 K isotherms
    (16 per isotherm at m_NaCl = 0.9/1.9/3.0/4.3) were never in any
    fit: the `solve_elv` guess table is only valid to 533 K, so they
    are reachable only through the stability_flash path -> test-only.
    They are the only gas-brine solubility data above 523 K anywhere
    in this database.
    """
    df = pd.read_parquet(MS_CODE / "data" / "ch4_brines.parquet")
    assert len(df) == 533, len(df)
    in_fit = df.T_K.between(FIT_T_MIN, FIT_T_MAX)
    assert int(in_fit.sum()) == 469, int(in_fit.sum())
    return [row("ch4_part1", r.author, "ch4", "solubility_molality",
                r.T_K, r.P_bar,
                [r.m_Na, r.m_Cl, r.m_K, r.m_Ca, r.m_Mg, r.m_SO4],
                r.mh_W, quality="T",
                tag=("fit-eligible"
                     if FIT_T_MIN <= r.T_K <= FIT_T_MAX else "test-only"))
            for r in df.itertuples()]


def _binary_water_rows(parquet, xcol, gas, dataset_id):
    """Salt-free gas-water solubility from a Multi_Salt binaries parquet.

    `xcol` is an aqueous mole fraction; with no salt present it is the
    salt-free mole fraction by definition, so each point emits an
    `xc_saltfree` row and its exact molality conversion, matching the
    treatment of the brine compilations above. Rows carrying only a
    gas-phase water content (y_H2O) are skipped -- those belong to
    y_h2o.csv and are built by build_y_h2o.py.
    """
    df = pd.read_parquet(MS_CODE / "data" / parquet)
    df = df[df[xcol].notna() & (df[xcol] > 0.0) & (df[xcol] < 1.0)]
    mi = [0.0] * 6
    out = []
    for r in df.itertuples():
        xc = float(getattr(r, xcol))
        common = dict(dataset_id=dataset_id, source=r.author, gas=gas,
                      T_K=r.T_K, P_bar=r.P_bar, mi=mi,
                      quality="T", tag="fit-eligible")
        out.append(row(prop="xc_saltfree", value=xc, **common))
        out.append(row(prop="solubility_molality",
                       value=xc_saltfree_to_molality(xc), **common))
    return out


def build_co2_water_binary():
    """Salt-free CO2-H2O solubility (16 sources, 273-623 K, to 3500 bar).

    Transcribed under CO2/CPA/PR; previously only its y_H2O column was
    promoted, so the solubility axis of the CO2 binary was absent from
    solubility.csv while y_h2o.csv carried the matching water contents.
    """
    return _binary_water_rows("binaries_co2_water.parquet",
                              "x_CO2_aq_exp", "co2", "co2_water_binary")


def build_ch4_water_binary():
    """Salt-free CH4-H2O solubility (31 sources, 275-633 K, to 1973 bar).

    Same asymmetry as the CO2 binary: transcribed under CH4/CH4-Water
    and promoted to y_h2o.csv only.
    """
    return _binary_water_rows("binaries_ch4_water.parquet",
                              "x_CH4_aq_exp", "ch4", "ch4_water_binary")


def build_co2_mixed():
    """298-pt mixed-brine CO2 compilation (phase3b_shyd stage b3
    prediction set; xc_W salt-free basis)."""
    df = pd.read_parquet(MS_CODE / "data" / "co2_mixed_brines.parquet")
    assert len(df) == 298, len(df)
    out = []
    for r in df.itertuples():
        mi = [r.m_Na, r.m_Cl, r.m_K, r.m_Ca, r.m_Mg, r.m_SO4]
        common = dict(dataset_id="co2_mixed_brines", source=r.author,
                      gas="co2", T_K=r.T_K, P_bar=r.P_bar, mi=mi,
                      quality="T", tag="test-only")
        out.append(row(prop="xc_saltfree", value=r.xc_W, **common))
        out.append(row(prop="solubility_molality",
                       value=xc_saltfree_to_molality(r.xc_W), **common))
    return out


def build_koschel():
    """22-pt Koschel 2006 CO2 enthalpy of solution (dh_sol, kJ/mol
    CO2; Tables 4 and 7). P stored in bar (source P_MPa * 10)."""
    df = pd.read_csv(MS_CODE / "pilot_studies" / "koschel_enthalpy_2026_08"
                     / "koschel_data.csv", comment="#")
    assert len(df) == 22, len(df)
    return [row("koschel2006", "Koschel2006_FPE247_T4_T7", "co2",
                "dh_sol", r.T_K, r.P_MPa * 10.0,
                mi_from_salt("NaCl", r.m_NaCl),
                r.dH_kJ_mol, r.delta_kJ_mol,
                quality="T", tag="test-only")
            for r in df.itertuples()]


def _targets_t():
    """Construct the trend_fix TargetsT exactly as gate_tcoef.py does
    (env first, then imports)."""
    os.environ["TREND_UNIFORM"] = "1"
    os.environ["TREND_TCOEF"] = "1"
    os.environ["TREND_VPSAT"] = "1"
    os.environ["TREND_SO4MAX"] = "2.2"
    for k in ("TREND_SLOPE", "TREND_SCALES", "TREND_PERION",
              "TREND_PAIR"):
        os.environ.setdefault(k, "0")
    for p in (str(MS_CODE),
              str(MS_CODE / "pilot_studies" / "trend_fix_2026_09")):
        if p not in sys.path:
            sys.path.insert(0, p)
    import trend_model as tm
    return tm, tm.TargetsT()


def build_harness_targets():
    """phi_osm (75 + 26), eps_r (13) and psat_ratio (21) rows dumped
    from the TargetsT spec/target arrays; rho (905) from the full
    TargetsT.rho_all Al Ghafri frame.

    Per-point sigma is recovered exactly from the harness weights,
    w_i = sqrt(B_k/N_k)/sigma_i  (cofit_model.Targets._build_tasks),
    with B_k = data_loader_cofit.BLOCK_WEIGHTS[k], N_k = _block_N[k].
    """
    tm, tg = _targets_t()
    import data_loader_cofit as dl
    phi, eps, vps = [], [], []
    pos = 0
    for spec in tg.specs:
        n = tg._npts(spec)
        blk = tg.block[pos]
        if spec[0] == "phi":
            _, salt, T, Pp, ms = spec
            Bk, Nk = dl.BLOCK_WEIGHTS[blk], tg._block_N[blk]
            sig = np.sqrt(Bk / Nk) / tg.weight[pos:pos + n]
            src = ("PitzerMayorga1973_TI_TVI" if blk == "phi_osm_298K"
                   else "Schlaikjer2018_Fig3_digitized")
            qual = "R" if blk == "phi_osm_298K" else "T"
            for m, v, s in zip(ms, tg.target[pos:pos + n], sig):
                phi.append(row("phi_osm_harness", src, "", "phi_osm",
                               T, Pp / 1e5, mi_from_salt(salt, m), v,
                               s, quality=qual, tag="fit-eligible"))
        elif spec[0] == "eps":
            Bk, Nk = dl.BLOCK_WEIGHTS[blk], tg._block_N[blk]
            sig = np.sqrt(Bk / Nk) / tg.weight[pos:pos + n]
            for m, v, s in zip(spec[1], tg.target[pos:pos + n], sig):
                eps.append(row("eps_r_harness",
                               "MariboMogensen2013_Fig8_digitized",
                               "", "eps_r", 298.15, 1.0,
                               mi_from_salt("NaCl", m), v, s,
                               quality="T", tag="fit-eligible"))
        elif spec[0] == "vpsat":
            _, salt, m, T_C = spec
            vps.append(row("haas1976", "Haas1976_USGS1421A_T1_4_9_18",
                           "", "psat_ratio", T_C + 273.15, None,
                           mi_from_salt(salt, m), tg.target[pos],
                           tm.SIGMA_VPSAT, quality="R",
                           tag="fit-eligible"))
        pos += n
    assert len(phi) == 101 and len(eps) == 13 and len(vps) == 21, \
        (len(phi), len(eps), len(vps))

    rho = [row("rho_alghafri", r.source, "", "rho", r.T_K, r.P_bar,
               mi_from_salt(r.salt, r.m), r.value, r.sigma_weight,
               quality="T", tag="fit-eligible")
           for r in tg.rho_all.itertuples()]
    assert len(rho) == 905, len(rho)
    return phi, eps, vps, rho


# --------------------------------------------------------------------
# Part B -- NEW per-point extractions from the benchmark-paper PDFs
# --------------------------------------------------------------------

# Chabab, Theveneau, Coquelet, Corvisier, Paricaud, IJGGC 91 (2019)
# 102825, Table 2 (paper pp. 9-11): measured CO2 solubility in
# H2O + NaCl, salt-free mole fraction x_CO2^sf with standard
# uncertainty u(x).  Columns: m_NaCl [mol/kg-w], T [K], P [bar],
# x_sf, u(x_sf).  21 points, transcribed from the page images.
CHABAB2019_T2 = [
    (1.13, 372.33,  31.148, 0.00390, 2.0e-4),
    (1.13, 372.31,  60.500, 0.00750, 2.0e-4),
    (1.13, 372.29, 108.840, 0.01130, 2.5e-4),
    (1.13, 372.29, 151.920, 0.01360, 3.5e-4),
    (1.13, 372.25, 191.980, 0.01570, 6.0e-4),
    (1.13, 323.02,  53.450, 0.01030, 3.0e-4),
    (1.13, 322.97,  75.550, 0.01290, 3.0e-4),
    (1.13, 323.03, 100.350, 0.01510, 7.5e-4),
    (1.13, 323.04, 145.080, 0.01700, 4.5e-4),
    (1.00, 373.38,  16.983, 0.00237, 1.0e-4),
    (1.00, 373.37,  32.527, 0.00426, 2.0e-4),
    (1.00, 373.41,  68.182, 0.00833, 2.0e-4),
    (3.01, 342.82,  30.391, 0.00441, 1.0e-4),
    (3.01, 342.81,  72.559, 0.00880, 2.0e-4),
    (3.01, 342.82, 100.910, 0.01057, 3.0e-4),
    (3.01, 372.39,  25.556, 0.00292, 8.0e-5),
    (3.01, 372.42,  71.417, 0.00707, 1.5e-4),
    (3.01, 372.41, 100.517, 0.00878, 3.0e-4),
    (3.01, 372.43, 152.433, 0.01141, 2.5e-4),
    (3.01, 372.45, 199.597, 0.01258, 3.0e-4),
    (3.01, 372.45, 229.817, 0.01337, 3.0e-4),
]

# Chabab, Theveneau, Coquelet, Corvisier, Paricaud, Int. J. Hydrogen
# Energy 45 (2020) 32206, Table 4 (paper pp. 14-15): measured H2
# solubility in H2O + NaCl, salt-free mole fraction, u(T)=0.02 K,
# u(P)=5 kPa.  Columns: m_NaCl, T [K], P [bar], x_sf, u(x_sf).
# NOTE: the table contains 37 points (page-image verified), not the
# 40 stated in the assignment brief.
CHABAB2020_T4 = [
    (0.0, 323.18,  37.108, 0.000461, 2.0e-5),
    (0.0, 323.18,  79.366, 0.001030, 3.0e-5),
    (0.0, 323.19, 121.706, 0.001544, 4.0e-5),
    (0.0, 372.71,  29.272, 0.000396, 2.5e-5),
    (0.0, 372.73,  60.213, 0.000857, 3.5e-5),
    (0.0, 372.72,  93.426, 0.001368, 6.0e-5),
    (1.0, 323.20,  30.828, 0.000309, 1.0e-5),
    (1.0, 323.21,  66.068, 0.000648, 2.0e-5),
    (1.0, 323.21, 100.354, 0.000972, 3.5e-5),
    (1.0, 323.21, 149.657, 0.001419, 4.0e-5),
    (1.0, 323.21, 200.093, 0.001855, 6.0e-5),
    (1.0, 347.90,  42.907, 0.000444, 1.0e-5),
    (1.0, 347.91,  80.673, 0.000827, 2.0e-5),
    (1.0, 347.90, 125.504, 0.001255, 4.0e-5),
    (1.0, 347.90, 170.730, 0.001667, 4.5e-5),
    (1.0, 347.91, 216.205, 0.002076, 6.0e-5),
    (1.0, 372.73,  19.884, 0.000217, 1.0e-5),
    (1.0, 372.76,  60.987, 0.000659, 2.0e-5),
    (1.0, 372.76, 100.677, 0.001071, 3.5e-5),
    (1.0, 372.78, 153.553, 0.001595, 4.5e-5),
    (1.0, 372.72, 208.620, 0.002132, 7.0e-5),
    (3.0, 323.20,  32.736, 0.000201, 1.5e-5),
    (3.0, 323.18,  66.733, 0.000400, 2.0e-5),
    (3.0, 323.20, 100.832, 0.000631, 2.0e-5),
    (3.0, 323.21, 150.342, 0.000938, 3.5e-5),
    (3.0, 323.20, 196.595, 0.001204, 4.0e-5),
    (3.0, 372.75,  33.387, 0.000215, 1.5e-5),
    (3.0, 372.74,  66.536, 0.000456, 1.5e-5),
    (3.0, 372.74, 100.855, 0.000702, 3.0e-5),
    (3.0, 372.76, 151.296, 0.001050, 4.0e-5),
    (3.0, 372.75, 196.178, 0.001333, 4.0e-5),
    (3.0, 372.76, 229.720, 0.001549, 5.0e-5),
    (5.0, 323.19,  28.623, 0.000127, 5.0e-6),
    (5.0, 323.19,  66.385, 0.000293, 1.0e-5),
    (5.0, 323.19, 100.979, 0.000440, 1.0e-5),
    (5.0, 323.20, 149.900, 0.000662, 2.0e-5),
    (5.0, 323.19, 193.702, 0.000838, 3.5e-5),
]

# Chabab et al., J. Chem. Eng. Data 66 (2021) 609, Table 2 (paper
# p. 14): CO2 solubility in 6 m NaCl brine, rocking-cell setup,
# salt-free mole fraction; u(T)=0.17 K, u(P)=0.068 MPa.
# Columns: T [K], P [MPa], x_sf, u(x_sf).  14 points.
CHABAB2021_T2 = [
    (303.55,  3.6721, 0.00572, 0.00010),
    (303.55,  7.1333, 0.00890, 0.00008),
    (303.55, 15.1857, 0.00936, 0.00010),
    (303.55, 24.6777, 0.01012, 0.00010),
    (303.55, 36.0196, 0.01077, 0.00010),
    (323.10,  3.5818, 0.00418, 0.00010),
    (323.10,  8.9744, 0.00760, 0.00007),
    (323.10, 14.3618, 0.00866, 0.00009),
    (323.10, 24.5798, 0.00939, 0.00010),
    (323.10, 39.4477, 0.01046, 0.00010),
    (373.29,  4.676,  0.00333, 0.00010),
    (373.39, 12.0603, 0.00654, 0.00006),
    (373.39, 20.5905, 0.00846, 0.00008),
    (373.39, 35.0185, 0.00978, 0.00010),
]

# Chabab et al., J. Chem. Eng. Data 66 (2021) 609, Table 3 (paper
# pp. 15-16): O2 solubility in H2O + NaCl, salt-free mole fraction.
# Technique 1 (static-analytic): u(T)=0.02 K, u(P)=0.005 MPa;
# Technique 2 (rocking cell): u(T)=0.17 K, u(P)=0.068 MPa.
# Columns: technique, m_NaCl, T [K], P [MPa], x_sf, u(x_sf), quality.
# The starred 1* block (Technique 1, 373 K) is author-flagged: the
# NaCl molality likely increased during the run (footnote, Sec 4.2)
# -> quality U.  44 points.
CHABAB2021_T3 = [
    (1, 0.5, 324.00,  4.3540, 0.00064, 2.0e-5, "T"),
    (1, 0.5, 323.95,  9.9310, 0.00140, 1.0e-4, "T"),
    (1, 0.5, 323.94, 13.6330, 0.00180, 1.0e-4, "T"),
    (1, 0.5, 323.93, 17.0180, 0.00210, 1.0e-4, "T"),
    (1, 0.5, 323.93, 20.0710, 0.00240, 1.0e-4, "T"),
    (1, 1.0, 323.16,  3.1210, 0.00038, 1.0e-5, "T"),
    (1, 1.0, 323.17,  7.3479, 0.00085, 2.0e-5, "T"),
    (1, 1.0, 323.14,  4.8790, 0.00059, 1.0e-5, "T"),
    (1, 1.0, 323.14, 11.2857, 0.00125, 4.0e-5, "T"),
    (1, 1.0, 323.17, 15.2399, 0.00160, 5.0e-5, "T"),
    (1, 4.0, 323.18,  3.0720, 0.00018, 1.0e-5, "T"),
    (1, 4.0, 323.16,  7.2104, 0.00042, 1.0e-5, "T"),
    (1, 4.0, 323.13, 15.0404, 0.00080, 3.0e-5, "T"),
    (1, 4.0, 323.16, 19.6893, 0.00098, 3.0e-5, "T"),
    (1, 1.0, 372.92,  3.0516, 0.00029, 1.0e-5, "U"),   # 1* block
    (1, 1.0, 373.11,  7.2294, 0.00070, 1.0e-5, "U"),   # 1* block
    (1, 1.0, 373.07, 11.1250, 0.00106, 2.0e-5, "U"),   # 1* block
    (1, 1.0, 373.10, 15.1719, 0.00139, 2.0e-5, "U"),   # 1* block
    (1, 1.0, 373.09, 20.2617, 0.00175, 4.0e-5, "U"),   # 1* block
    (1, 2.0, 333.30,  3.1964, 0.00029, 1.0e-5, "T"),
    (1, 2.0, 333.53,  6.6156, 0.00057, 1.0e-5, "T"),
    (1, 2.0, 333.53, 10.2178, 0.00083, 6.0e-5, "T"),
    (1, 2.0, 333.52, 15.2950, 0.00118, 4.0e-5, "T"),
    (1, 2.0, 333.53, 20.2640, 0.00146, 8.0e-5, "T"),
    (2, 1.0, 303.74, 10.4249, 0.00141, 5.0e-5, "T"),
    (2, 1.0, 303.74, 16.8653, 0.00206, 5.3e-5, "T"),
    (2, 1.0, 303.55, 25.9464, 0.00290, 5.5e-5, "T"),
    (2, 1.0, 303.55, 35.4577, 0.00350, 5.8e-5, "T"),
    (2, 1.0, 323.20, 11.8555, 0.00131, 5.0e-5, "T"),
    (2, 1.0, 323.20, 20.5567, 0.00201, 5.4e-5, "T"),
    (2, 1.0, 323.20, 27.9341, 0.00256, 5.5e-5, "T"),
    (2, 1.0, 323.20, 35.6287, 0.00304, 5.6e-5, "T"),
    (2, 1.0, 373.10, 29.1304, 0.00245, 5.4e-5, "T"),
    (2, 1.0, 373.10, 21.5461, 0.00197, 5.4e-5, "T"),
    (2, 1.0, 373.19, 12.3554, 0.00129, 5.3e-5, "T"),
    (2, 1.0, 373.19, 35.5839, 0.00286, 5.5e-5, "T"),
    (2, 4.0, 303.26, 13.5379, 0.00078, 5.0e-5, "T"),
    (2, 4.0, 303.26, 20.8808, 0.00112, 5.3e-5, "T"),
    (2, 4.0, 303.26, 27.9272, 0.00134, 5.3e-5, "T"),
    (2, 4.0, 303.64, 32.3123, 0.00153, 5.4e-5, "T"),
    (2, 4.0, 323.10, 13.8274, 0.00075, 5.0e-5, "T"),
    (2, 4.0, 323.01, 21.0325, 0.00102, 5.3e-5, "T"),
    (2, 4.0, 323.01, 28.4305, 0.00125, 5.4e-5, "T"),
    (2, 4.0, 323.01, 36.0630, 0.00150, 5.4e-5, "T"),
]

# dos Santos, Lassin, Andre, Lach, Cezac, Chem. Geol. 582 (2021)
# 120443, Table 7 (paper pp. 28-29): CO2 solubility in NaCl and
# NaCl + Na2SO4 solutions, DIRECT molality m_CO2 [mol/kg-w] with
# per-point u(m_CO2) = 0.0228*m_CO2; u(T)=0.06 K, u(P)=0.03 MPa.
# Columns: m_NaCl, m_Na2SO4, T [K], P [MPa], m_CO2, u(m_CO2).
# 30 rows = 6 single-salt (6m NaCl) + 24 mixed (3m NaCl + 1m Na2SO4).
DOSSANTOS2021_T7 = [
    (6.0, 0.0, 303.15,  1.55, 0.148, 0.003),
    (6.0, 0.0, 303.15,  3.02, 0.270, 0.006),
    (6.0, 0.0, 303.15,  5.02, 0.401, 0.009),
    (6.0, 0.0, 303.15, 10.02, 0.500, 0.011),
    (6.0, 0.0, 303.15, 15.06, 0.525, 0.012),
    (6.0, 0.0, 303.15, 20.18, 0.543, 0.012),
    (3.0, 1.0, 303.15,  1.53, 0.140, 0.003),
    (3.0, 1.0, 303.15,  3.04, 0.259, 0.006),
    (3.0, 1.0, 303.15,  5.03, 0.375, 0.009),
    (3.0, 1.0, 303.15, 10.02, 0.466, 0.011),
    (3.0, 1.0, 303.15, 15.03, 0.483, 0.011),
    (3.0, 1.0, 303.15, 20.12, 0.514, 0.012),
    (3.0, 1.0, 323.15,  1.56, 0.102, 0.002),
    (3.0, 1.0, 323.15,  3.04, 0.186, 0.004),
    (3.0, 1.0, 323.15,  5.03, 0.284, 0.006),
    (3.0, 1.0, 323.15, 10.04, 0.416, 0.009),
    (3.0, 1.0, 323.15, 15.08, 0.454, 0.010),
    (3.0, 1.0, 323.15, 20.07, 0.495, 0.011),
    (3.0, 1.0, 373.15,  1.54, 0.063, 0.001),
    (3.0, 1.0, 373.15,  3.07, 0.123, 0.003),
    (3.0, 1.0, 373.15,  5.03, 0.191, 0.004),
    (3.0, 1.0, 373.15, 10.16, 0.330, 0.008),
    (3.0, 1.0, 373.15, 15.10, 0.421, 0.010),
    (3.0, 1.0, 373.15, 20.12, 0.476, 0.011),
    (3.0, 1.0, 423.15,  1.54, 0.044, 0.001),
    (3.0, 1.0, 423.15,  3.03, 0.096, 0.002),
    (3.0, 1.0, 423.15,  5.04, 0.164, 0.004),
    (3.0, 1.0, 423.15, 10.01, 0.299, 0.007),
    (3.0, 1.0, 423.15, 15.02, 0.405, 0.009),
    (3.0, 1.0, 423.15, 20.05, 0.482, 0.011),
]


def _xc_rows(dataset_id, source, gas, pts, tag="test-only"):
    """Rows for a literal (m_NaCl, T, P_bar, x_sf, u) table: one
    xc_saltfree + one converted solubility_molality row per point."""
    out = []
    for m, T, P_bar, xc, u in pts:
        mi = mi_from_salt("NaCl", m)
        out.append(row(dataset_id, source, gas, "xc_saltfree",
                       T, P_bar, mi, xc, u, quality="T", tag=tag))
        out.append(row(dataset_id, source, gas, "solubility_molality",
                       T, P_bar, mi, xc_saltfree_to_molality(xc),
                       u_molality_from_u_xc(u, xc),
                       quality="T", tag=tag))
    return out


def build_pdf_extractions():
    out = []
    out += _xc_rows("chabab2019_t2", "Chabab2019_IJGGC91_T2", "co2",
                    CHABAB2019_T2)
    out += _xc_rows("chabab2020_t4", "Chabab2020_IJHE45_T4", "h2",
                    CHABAB2020_T4)
    out += _xc_rows("chabab2021_t2", "Chabab2021_JCED66_T2", "co2",
                    [(6.0, T, P_MPa * 10.0, xc, u)      # 6 m NaCl
                     for T, P_MPa, xc, u in CHABAB2021_T2])
    for tech, m, T, P_MPa, xc, u, qual in CHABAB2021_T3:
        mi = mi_from_salt("NaCl", m)
        src = f"Chabab2021_JCED66_T3_tech{tech}"
        out.append(row("chabab2021_t3", src, "o2", "xc_saltfree",
                       T, P_MPa * 10.0, mi, xc, u, quality=qual))
        out.append(row("chabab2021_t3", src, "o2",
                       "solubility_molality", T, P_MPa * 10.0, mi,
                       xc_saltfree_to_molality(xc),
                       u_molality_from_u_xc(u, xc), quality=qual))
    for mna, mso4, T, P_MPa, mco2, u in DOSSANTOS2021_T7:
        # ion vector: NaCl + Na2SO4 (Na = mna + 2*mso4, Cl = mna,
        # SO4 = mso4) -- conventions.SALT_STOICH bookkeeping
        mi = [mna + 2.0 * mso4, mna, 0.0, 0.0, 0.0, mso4]
        out.append(row("dossantos2021_t7", "dosSantos2021_ChemGeol582_T7",
                       "co2", "solubility_molality", T, P_MPa * 10.0,
                       mi, mco2, u, quality="T"))
    # Hou 2013b Tables 2/3 aqueous-phase rows (transcription tables,
    # provenance and uncertainty semantics in bench/data/hou2013.py)
    from bench.data import hou2013
    for did, src, salt, m, T, P_bar, xc, u in hou2013.solubility_points():
        mi = mi_from_salt(salt, m)
        out.append(row(did, src, "co2", "xc_saltfree",
                       T, P_bar, mi, xc, u, quality="T"))
        out.append(row(did, src, "co2", "solubility_molality",
                       T, P_bar, mi, xc_saltfree_to_molality(xc),
                       u_molality_from_u_xc(u, xc), quality="T"))
    return out


# --------------------------------------------------------------------
# Part C -- transfer-gas solubility (v0.4).  Sources are the curated
# Multi_Salt pilot-study CSVs (read-only; every file carries a header
# block with the literature citation and transcription-verification
# note).  All rows: tag="test-only" (prediction-only transferability
# axis; never in any refit objective).
# --------------------------------------------------------------------

PILOTS = MS_CODE / "pilot_studies"

ATM_TO_BAR = 1.01325


# ------------------------------------------------- phase-regime screen
# Vapor-pressure ancillary of the REFERENCE (multiparameter Helmholtz)
# equation of state for each condensable hydrocarbon, in the standard
# Wagner form
#
#     p_sat(T) = p_c * exp( (T_c/T) * sum_i n_i * (1 - T/T_c)**t_i )
#
# Coefficients as distributed with the reference EoS (CoolProp/teqp
# fluid files, "ANCILLARIES/pS"): propane from Lemmon, McLinden &
# Wagner 2009 (JCED 54:3141), ethane from Bucker & Wagner 2006
# (JPCRD 35:205).  Stated maximum deviation from the full EoS
# saturation line: 0.016 % (propane), 0.024 % (ethane) -- four orders
# of magnitude tighter than the screen needs, and (unlike an Antoine
# fit) valid over the whole database span up to T_c.  The constants
# are inlined so the build is deterministic and needs no thermodynamic
# library; tests/test_data.py checks them against teqp when available.
HC_PSAT_ANCILLARY = {
    "c3h8": dict(
        Tc=369.89, pc_bar=42.512,
        n=(-23.998635747391152, 18.313017605233238, -0.42240851966839504,
           -2.7378298813798962, 0.257888414168987, -1.3113462226130785),
        t=(1.05, 1.084, 2.259, 4.287, 7.66, 18.584)),
    "c2h6": dict(
        Tc=305.322, pc_bar=48.722,
        n=(9.344483558228339, -14.812636376983514, -0.6873077210086483,
           0.7942400572322573, -2.447274904672986, 0.04047591478430641),
        t=(0.871, 0.902, 1.663, 2.045, 3.946, 14.704)),
}

#: tag for rows whose gas-rich phase is NOT a gas (see _regime_tag)
LLE_TAG = "lle-regime"


def hc_psat_bar(gas, T_K):
    """Saturation pressure [bar] of a pure condensable hydrocarbon from
    its reference-EoS ancillary; NaN at or above the critical
    temperature (no saturation line there)."""
    a = HC_PSAT_ANCILLARY[gas]
    if T_K >= a["Tc"]:
        return float("nan")
    th = 1.0 - T_K / a["Tc"]
    s = sum(ni * th ** ti for ni, ti in zip(a["n"], a["t"]))
    return a["pc_bar"] * np.exp(a["Tc"] / T_K * s)


def _regime_tag(gas, T_K, P_bar, default="test-only"):
    """Tag a hydrocarbon row by the STATE OF THE GAS-RICH PHASE.

    A solubility point is gas solubility only if the hydrocarbon-rich
    phase is a gas (or a supercritical fluid).  Below the hydrocarbon's
    critical temperature and at or above its own vapor pressure the
    hydrocarbon-rich phase has condensed: the measurement is then
    liquid--liquid mutual solubility of a hydrocarbon LIQUID with
    water.  Those rows are genuine and valuable (they are the aqueous
    branch of the three-phase locus) but they are a different property
    from gas solubility, so they get their own tag and are excluded
    from the default scored set (bench/core/scoring.load_rows).  At
    T >= T_c there is no liquid branch at all and the row stays a
    (supercritical-fluid) solubility row, exactly as dense-phase
    \\ce{CO2} rows do.

    Comparison uses the TOTAL pressure stored in the row, which is the
    conservative reading: the hydrocarbon partial pressure is slightly
    lower, so borderline rows are flagged rather than kept.  The
    classification is not sensitive to that choice --- across the whole
    database the highest unflagged subcritical row sits 1.6 % below the
    saturation line and the lowest flagged one 3.8 % above it, so no
    row lands inside the uncertainty of the locus and the verdict would
    be identical on partial pressures.
    """
    if gas not in HC_PSAT_ANCILLARY:
        return default
    ps = hc_psat_bar(gas, float(T_K))
    if ps != ps:                      # T >= Tc: supercritical fluid
        return default
    return LLE_TAG if float(P_bar) >= ps else default


def _pair_rows(dataset_id, source, gas, T_K, P_bar, mi, m_gas,
               u_m=None, quality="T"):
    """One solubility_molality + one consistent xc_saltfree row from a
    molality value (xc derived via molality_to_xc_saltfree so the pair
    satisfies the exact-inverse consistency check in tests).

    Condensable-hydrocarbon rows are regime-screened (_regime_tag): a
    point whose hydrocarbon-rich phase is a liquid is tagged
    ``lle-regime`` instead of ``test-only`` and leaves the scored gas
    solubility set."""
    xc = molality_to_xc_saltfree(m_gas)
    u_xc = (u_m * (1.0 - xc) ** 2 / N_W) if u_m is not None else None
    tag = _regime_tag(gas, T_K, P_bar)
    return [row(dataset_id, source, gas, "solubility_molality",
                T_K, P_bar, mi, m_gas, u_m, quality=quality, tag=tag),
            row(dataset_id, source, gas, "xc_saltfree",
                T_K, P_bar, mi, xc, u_xc, quality=quality, tag=tag)]


def build_n2_osullivan():
    """51-pt N2 solubility in water / 1 m / 4 m NaCl, O'Sullivan &
    Smith 1970 (JPC 74:1460, Table I p. 1461), from the verified
    transcription pilot_studies/n2_scoping_2026_07/
    n2_nacl_osullivan1970.csv (N2 rows; the CH4 rows of the same
    table are already in ch4_part1 via ch4_brines.parquet).

    Printed X2 treats NaCl as UNDISSOCIATED (single component;
    csv header note): X2 = n_g/(n_g + n_w + m_salt) per kg water, so
    the exact molality is m_g = X2*(n_w + m_salt)/(1 - X2); the
    xc_saltfree sibling is derived from m_g.  P printed in atm
    (TOTAL pressure), stored in bar."""
    df = pd.read_csv(PILOTS / "n2_scoping_2026_07"
                     / "n2_nacl_osullivan1970.csv", comment="#")
    df = df[df.gas == "N2"].reset_index(drop=True)
    assert len(df) == 51, len(df)
    out = []
    for r in df.itertuples():
        m_salt = float(r.m_NaCl_mol_kg)
        x2 = float(r.x_molefrac)
        m_gas = x2 * (N_W + m_salt) / (1.0 - x2)
        out += _pair_rows("n2_osullivan1970", "OSULLIVAN(1970)", "n2",
                          r.T_K, r.P_atm * ATM_TO_BAR,
                          mi_from_salt("NaCl", m_salt), m_gas)
    return out


def build_c2h6_water():
    """116-pt C2H6-H2O aqueous solubility (salt-free), from
    pilot_studies/c2_pilot_2026_08/c2_water_data.csv:
    Culberson, Horn & McKetta 1950 (Trans AIME 189:1, 30 pts) and
    Culberson & McKetta 1950 (Trans AIME 189:319, 45 pts), both via
    the IUPAC SDS Vol 9 compilation sheets (Hayduk 1982, pp. 17-19;
    compiler C.L. Young, stated est. err +-5 % -> uncertainty
    0.05*x); Mohammadi, Chapoy, Tohidi & Richon 2004 (IECR 43:5418,
    Table 4, T >= 283 K, 41 pts; no stated per-point u).  x is the
    aqueous mole fraction of the salt-free binary; P stored in bar
    (source MPa * 10)."""
    df = pd.read_csv(PILOTS / "c2_pilot_2026_08" / "c2_water_data.csv",
                     comment="#")
    assert len(df) == 116, len(df)
    src = {"CM1950lo": "CULBERSONHORN(1950)",
           "CM1950hi": "CULBERSONMCKETTA(1950)",
           "Mohammadi2004": "MOHAMMADI(2004eth)"}
    out = []
    for r in df.itertuples():
        xc = float(r.x_molefrac)
        m_gas = xc_saltfree_to_molality(xc)
        u_m = (u_molality_from_u_xc(0.05 * xc, xc)
               if r.source.startswith("CM1950") else None)
        out += _pair_rows("c2h6_water", src[r.source], "c2h6",
                          r.T_K, r.P_MPa * 10.0, [0.0] * 6, m_gas, u_m)
    return out


def build_c3h8_water():
    """175-pt C3H8-H2O aqueous solubility (salt-free), from
    pilot_studies/c3_pilot_2026_08/c3_water_data.csv (the exact
    Papers II/III fit/validation set assembled by c3_pilot.stage_data):
    136 pts Kobayashi & Katz smoothed two-phase table (Kobayashi 1951
    Univ. Michigan PhD thesis / Kobayashi & Katz 1953 IEC 45:440;
    graphically smoothed values, flagged rows already dropped by the
    pilot) + 39 pts Chapoy et al. 2004 (FPE 226:213).  x is the
    aqueous mole fraction of the salt-free binary; P already bar."""
    df = pd.read_csv(PILOTS / "c3_pilot_2026_08" / "c3_water_data.csv",
                     comment="#")
    assert len(df) == 175, len(df)
    src = {"Kobayashi1951sm": "KOBAYASHI(1951)",
           "Chapoy2004": "CHAPOY(2004)"}
    out = []
    for r in df.itertuples():
        m_gas = xc_saltfree_to_molality(float(r.x_molefrac))
        out += _pair_rows("c3h8_water", src[r.source], "c3h8",
                          r.T_K, r.P_bar, [0.0] * 6, m_gas)
    return out


def build_c3h8_umano():
    """C3H8 solubility in NaCl brines (0-5.315 mol/kg), Umano &
    Nakano 1958 (Kogyo Kagaku Zasshi 61:536) via IUPAC SDS Vol 24
    (Hayduk 1986, pp. 100-104), transcription
    pilot_studies/c3_pilot_2026_08/raw/iupac24_propane_salts_umano_
    nacl.csv.  Printed solubility is 1e5 * (mol C3H8 / mol H2O), so
    molality = ratio * n_w exactly (csv header: 'multiply by 55.51');
    P stored as the printed TOTAL pressure in bar.  Rows below
    273.15 K (supercooled-region isotherms at 264.7/268.2 K, 16 pts)
    are outside the database's stated 273-623 K span and are not
    loaded.  The 5 rows the transcriber flagged as probable misprints
    (note column; values kept as printed) enter with quality U."""
    df = pd.read_csv(PILOTS / "c3_pilot_2026_08" / "raw"
                     / "iupac24_propane_salts_umano_nacl.csv",
                     comment="#")
    assert len(df) == 151, len(df)
    df = df[df.T_K >= 273.15].reset_index(drop=True)
    assert len(df) == 135, len(df)
    out = []
    for r in df.itertuples():
        ratio = float(r.x1e5_mol_ratio) * 1e-5
        m_gas = ratio * N_W
        qual = "U" if isinstance(r.note, str) and r.note.strip() else "T"
        out += _pair_rows("c3h8_nacl_umano1958", "UMANO(1958)", "c3h8",
                          r.T_K, r.p_total_atm * ATM_TO_BAR,
                          mi_from_salt("NaCl",
                                       float(r.NaCl_molality_mol_kg)),
                          m_gas, quality=qual)
    return out


def build_h2_pilot():
    """New H2 solubility rows from the Papers II/III H2 pilot
    curation (pilot_studies/h2_scoping_2026_07/, per-row author +
    source-file provenance columns), deduplicated against the
    chabab2020_t4 rows already in this database:

    * h2_nacl_brine.csv -- direct H2 molality in NaCl brines
      (1-5 mol/kg, 298-423 K, to 458 bar).  The CHABAB(2020) rows
      are the brine subset of Chabab 2020 IJHE Table 4 (already
      present) and are EXCLUDED; kept: CHABAB(2024) 30 pts +
      TORIN(2022) 10 pts.  Molality rows only (native basis).
    * h2_water_binaries.csv -- aqueous H2 mole fraction of the
      salt-free binary, 273-589 K, to 1013 bar; rows without an
      aqueous x (y-only rows, e.g. the Bartlett/Maslennikova blocks)
      are skipped and the 6 CHABAB(2020) pure-water points (Table 4
      duplicates) are EXCLUDED -> 157 pts from 10 authors, stored as
      molality + xc pairs.
      (h2_water_isobaric.csv is NOT loaded: ZOSS(1952) is itself a
      secondary compilation -- double-counting risk with the Wiebe
      lineage -- and the 1-atm Morrison set is outside the pressure
      scope.)"""
    br = pd.read_csv(PILOTS / "h2_scoping_2026_07" / "h2_nacl_brine.csv")
    assert len(br) == 71, len(br)
    br = br[br.author != "CHABAB(2020)"].reset_index(drop=True)
    assert len(br) == 40, len(br)
    out = [row("h2_nacl_brines", r.author, "h2", "solubility_molality",
               r.T_K, r.P_bar, mi_from_salt("NaCl", float(r.m_NaCl_molkg)),
               float(r.m_H2_molkg), quality="T")
           for r in br.itertuples()]

    wa = pd.read_csv(PILOTS / "h2_scoping_2026_07"
                     / "h2_water_binaries.csv")
    assert len(wa) == 216, len(wa)
    wa = wa[wa.x_H2_aq.notna()
            & (wa.author != "CHABAB(2020)")].reset_index(drop=True)
    assert len(wa) == 157, len(wa)
    for r in wa.itertuples():
        m_gas = xc_saltfree_to_molality(float(r.x_H2_aq))
        out += _pair_rows("h2_water_binaries", r.author, "h2",
                          r.T_K, r.P_bar, [0.0] * 6, m_gas)
    return out


def build_transfer_gases():
    """All Part-C rows, in a frozen builder order.  APPEND-ONLY
    contract: Part C comes last in solubility.csv so that the
    positional 'file.csv#idx' row ids stored in the frozen c3/c5
    refit checkpoints (bench/core/refit.load_rows) remain valid for
    every pre-existing row."""
    return (build_n2_osullivan() + build_c2h6_water()
            + build_c3h8_water() + build_c3h8_umano()
            + build_h2_pilot())


# --------------------------------------------------------------------

def main():
    sol = (build_co2_part1() + build_ch4_part1() + build_co2_mixed()
           + build_co2_water_binary() + build_ch4_water_binary()
           + build_pdf_extractions() + build_transfer_gases())
    phi, eps, vps, rho = build_harness_targets()
    dh = build_koschel()

    frames = {
        "solubility.csv": pd.DataFrame(sol),
        "rho.csv": pd.DataFrame(rho),
        "phi_osm.csv": pd.DataFrame(phi),
        "psat_ratio.csv": pd.DataFrame(vps),
        "dh_sol.csv": pd.DataFrame(dh),
        "eps_r.csv": pd.DataFrame(eps),
    }
    all_rows = []
    for name, df in frames.items():
        df = df[COLUMNS]
        df.to_csv(DATA_DIR / name, index=False, float_format="%.10g")
        all_rows.append(df)
        print(f"{name:16s} {len(df):5d} rows")
        for did, g in df.groupby("dataset_id"):
            props = {p: int(n) for p, n in
                     g.property.value_counts().items()}
            print(f"    {did:22s} {props}")
    combined = pd.concat(all_rows, ignore_index=True)
    combined.to_parquet(DATA_DIR / "benchmark_v0.parquet", index=False)
    print(f"combined parquet: {len(combined)} rows")


if __name__ == "__main__":
    main()
