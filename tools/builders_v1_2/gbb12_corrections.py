"""Corrections to v1.1.1 rows and quality/flag edits found by checking the consensus outliers against the papers (2026-10-03).

Every entry was verified against the printed table of the paper (see release/outlier_check/results/*.json for the evidence). Old rows are
addressed by their zero-based position in the v1.1.1 family CSV (the old rows come first in every v1.2 file and keep their order);
each edit carries the value it expects to find, so a position that no longer holds the row it was written for raises an error.
Nothing here changes a row silently: every group is returned as a ledger entry.

apply_old(old, ledger)  -> edits the dict of v1.1.1 DataFrames (all columns str) in place
apply_new(merged, ledger) -> edits flags/quality of v1.2 rows in the merged frames
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

M_W = 18.01528
ION = ["m_Na", "m_Cl", "m_K", "m_Ca", "m_Mg", "m_SO4"]


CHAPOY2003_CORRIGENDUM = {  # y_h2o.csv position: (corrected y, stored value); Fluid Phase Equilib. 230 (2005) 210-214, Table 1
    14: (0.000292, 0.000108),
    16: (0.000382, 0.000208),
    17: (0.000273, 8.76e-05),
    19: (0.000483, 0.00032),
    20: (0.000338, 0.000159),
    21: (0.000267, 7.99e-05),
    23: (0.000631, 0.000484),
    24: (0.000471, 0.000307),
    25: (0.000355, 0.000178),
    26: (0.000313, 0.000132),
    27: (0.000265, 7.79e-05),
    29: (0.000889, 0.000771),
    30: (0.000625, 0.000478),
    31: (0.000456, 0.00029),
    32: (0.000371, 0.000196),
    33: (0.000331, 0.000151),
    35: (0.001114, 0.00102),
    36: (0.000807, 0.00068),
    37: (0.000577, 0.000424),
    38: (0.000495, 0.000334),
    39: (0.000447, 0.00028),
    42: (0.001045, 0.000972),
    43: (0.000715, 0.000588),
    44: (0.000626, 0.000484),
    45: (0.000575, 0.000424),
    47: (0.001985, 0.00218),
    48: (0.001326, 0.00128),
    49: (0.00089, 0.000791),
    50: (0.000763, 0.000644),
    51: (0.000691, 0.00056),
}
CHAPOY2003_T = {13: 283.08, 14: 283.08, 15: 288.11, 16: 288.11, 17: 288.11, 18: 293.11, 19: 293.11, 20: 293.11, 21: 293.11, 22: 298.11, 23: 298.11, 24: 298.11, 25: 298.11, 26: 298.11, 27: 298.11, 28: 303.11, 29: 303.11, 30: 303.11, 31: 303.11, 32: 303.11, 33: 303.11, 34: 308.11, 35: 308.11, 36: 308.11, 37: 308.11, 38: 308.11, 39: 308.11, 40: 313.12, 41: 313.12, 42: 313.12, 43: 313.12, 44: 313.12, 45: 313.12, 46: 318.12, 47: 318.12, 48: 318.12, 49: 318.12, 50: 318.12, 51: 318.12}  # printed isotherm temperatures (K)

def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return np.nan


def _close(a, b, rel=1e-6):
    a, b = _f(a), _f(b)
    return (np.isnan(a) and np.isnan(b)) or abs(a - b) <= rel * max(abs(a), abs(b), 1e-300)


def _fmt(v):
    return repr(float(f"{v:.10g}"))


def _sib(df, i):
    """Index of the sibling row (the other solubility property of the same point) or None."""
    r = df.iloc[i]
    for j in (i - 1, i + 1):
        if 0 <= j < len(df):
            s = df.iloc[j]
            if (s["dataset_id"] == r["dataset_id"] and s["source"] == r["source"] and s["gas"] == r["gas"] and s["property"] != r["property"]
                    and _close(s["T_K"], r["T_K"]) and _close(s["P_bar"], r["P_bar"]) and all(_close(s[k], r[k]) for k in ION)):
                return j
    return None


def _set(df, i, col, new, expect=None):
    if expect is not None and not _close(df.at[i, col], expect, rel=2e-3):
        raise AssertionError(f"row {i} {col}: expected {expect}, found {df.at[i, col]}")
    df.at[i, col] = new if isinstance(new, str) else _fmt(new)


def _x_to_m(x):
    return x / (1.0 - x) * 1000.0 / M_W


def _add_flag(df, i, flag):
    cur = [t for t in str(df.at[i, "flags"]).split(";") if t]
    if flag not in cur:
        df.at[i, "flags"] = ";".join(sorted(cur + [flag]))


def apply_old(old, ledger):
    sol, yh, = old["solubility"], old["y_h2o"]
    for d in old.values():
        if "flags" not in d.columns:
            d["flags"] = ""

    def log(ds, n, action, why):
        ledger.append({"dataset_id": ds, "rows": n, "action": action, "reason": why})

    # ---- 1. printed values the hand transcription or the conversion got wrong --------------------------------------------------
    for fam, df, idx, newP, oldP, who, why in [
        ("solubility", sol, 6874, 148.3, 147.3, "MICHELS(1936) ch4_water_binary 373 K", "pressure printed 146.4 atm = 148.3 bar, transcribed 147.3"),
        ("solubility", sol, 5498, 25.9, 25.6, "MULLER co2_water_binary 433 K", "pressure printed 2.588 MPa = 25.9 bar, transcribed 25.6"),
    ]:
        n = 0
        for i in (idx, _sib(df, idx)):
            _set(df, i, "P_bar", newP, oldP)
            n += 1
        log(df.at[idx, "dataset_id"], n, "value corrected", f"{who}: {why}")

    # Valtz 288 K isotherm: the hand file held P/1000 where the mole fraction belongs (Table 6, p. 340)
    xs = [0.00401, 0.00867, 0.01434, 0.01882, 0.02343, 0.02673, 0.02797]
    for p, x in enumerate(xs):
        ix, im = 4897 + 2 * p, 4898 + 2 * p
        assert sol.at[ix, "property"] == "xc_saltfree" and sol.at[im, "property"] == "solubility_molality" and sol.at[im, "source"] == "Valtz"
        _set(sol, ix, "xc_saltfree" if False else "value", x)
        _set(sol, im, "value", _x_to_m(x))
        for i in (ix, im):
            _set(sol, i, "T_K", 288.26, 288.0)
    log("co2_water_binary", 14, "value corrected", "Valtz (2004) 288 K isotherm: the transcribed mole-fraction column was P/1000; replaced by the printed x1 of Table 6 (and T 288.26 K as printed)")

    for pair, x_old, x_new in [((6341, 6342), 0.00237, 0.00240), ((6343, 6344), 0.00279, 0.00274)]:
        ix, im = pair
        _set(sol, ix, "value", x_new, x_old)
        _set(sol, im, "value", _x_to_m(x_new), _x_to_m(x_old))
    log("ch4_water_binary", 4, "value corrected", "ADDICKS(2002) Table 3: the 139.2 and 178.2 bar points took the Carroll column instead of x_exp")

    for i, yv, yold in [(214, 0.001183, 0.003241), (215, 0.000742, 0.002035), (216, 0.000431, 0.001182), (217, 0.004468, 0.01217), (218, 0.002788, 0.007617), (219, 0.002106, 0.00576)]:
        assert yh.at[i, "source"] == "YOKOYAMA(1988)"
        _set(yh, i, "value", yv, yold)
    log("yh2o_ch4_binary", 6, "value corrected", "YOKOYAMA(1988) Table II (mg H2O per g CH4): converted with the molar mass of CO2 (44.01) instead of CH4 (16.04); every y was 2.746 times too large")

    assert yh.at[501, "source"] == "TAKENOUCHI"
    _set(yh, 501, "value", 0.306, 0.316)
    log("yh2o_co2_binary", 1, "value corrected", "TAKENOUCHI Table 1, 200 C and 1400 bar: 69.4 mol% CO2 printed, so y_H2O = 0.306; transcribed 0.316")

    # WIEBE(1934): the transcribed mole fractions used 22.711 L/mol (1 bar) for the cm3 (S.T.P.) per g printed; Wiebe and Gaddy's S.T.P. is 0 C, 760 mm
    fac = 22.711 / 22.414
    n = 0
    for i in sol.index[(sol["source"] == "WIEBE(1934)") & (sol["property"] == "solubility_molality")]:
        m_new = _f(sol.at[i, "value"]) * fac
        _set(sol, i, "value", m_new)
        j = _sib(sol, i)
        assert j is not None
        _set(sol, j, "value", m_new / (m_new + 1000.0 / M_W))
        n += 2
    log("h2_water_binaries", n, "value corrected", "WIEBE(1934): printed cm3 (S.T.P.) per g water converted with 22.711 L/mol (1 bar) instead of the paper's S.T.P. (0 C, 760 mm; 22.414 L/mol): all values 1.3 % low")

    for i, (yv, yold) in CHAPOY2003_CORRIGENDUM.items():
        assert yh.at[i, "source"] == "CHAPOY(2003)"
        _set(yh, i, "value", yv, yold)
    for i, T in CHAPOY2003_T.items():
        assert yh.at[i, "source"] == "CHAPOY(2003)"
        _set(yh, i, "T_K", T)
    log("yh2o_ch4_binary", len(CHAPOY2003_CORRIGENDUM), "value corrected", "CHAPOY(2003): the authors' Corrigendum (Fluid Phase Equilib. 230 (2005) 210-214, Table 1) withdrew the original water contents "
        "(sampling-circuit adsorption made them too low) and gives corrected values; 30 of 39 rows change, isotherm temperatures taken as printed to 0.01 K")

    # ---- 2. temperatures printed per isotherm or per point, stored as isotherm labels ----------------------------------------------
    def retemp(df, mask, newT, who, why):
        for i in df.index[mask]:
            df.at[i, "T_K"] = _fmt(newT)
        if mask.sum():
            log(who, int(mask.sum()), "state corrected", why)

    def t(df, src, T, ds=None):
        m = (df["source"] == src) & df["T_K"].map(lambda v: _close(v, T))
        return m if ds is None else m & (df["dataset_id"] == ds)

    for df in (sol, yh):
        for nom, printed in [(283.0, 283.89), (298.0, 298.31), (313.0, 313.11), (323.0, 323.56)]:
            retemp(df, t(df, "FROST(2013)", nom), printed, "FROST(2013)", f"T printed {printed} K (Table 2), stored as the isotherm label {nom}")
    retemp(sol, t(sol, "AWAN(2010)", 313.0), 314.25, "AWAN(2010)", "T printed 314.25 K (Table 8), stored 313.0")
    retemp(sol, t(sol, "AWAN(2010)", 298.0), 298.78, "AWAN(2010)", "T printed 298.78 K (Table 8), stored 298.0")
    retemp(sol, t(sol, "OU(2015)", 286.0), 285.15, "OU(2015)", "isotherm is 285.15 K (Table 2), stored 286.0")
    retemp(sol, t(sol, "OU(2015)", 494.0), 493.15, "OU(2015)", "isotherm is 493.15 K (Table 2), stored 494.0")
    retemp(sol, t(sol, "PRICE(1979)", 478.0), 479.15, "PRICE(1979)", "206 C = 479.15 K, stored 478.0")
    for df in old.values():
        retemp(df, t(df, "GILLESPIE(1980)", 423.0), 422.04, "GILLESPIE(1980)", "300 F = 422.04 K, stored as the 423.0 K label")
    for i, T in [(5428, 421.4), (5430, 420.9), (5432, 421.4)]:
        for k in (i, _sib(sol, i)):
            _set(sol, k, "T_K", T, 423.0)
    log("co2_water_binary", 6, "state corrected", "SAKO Table 1: T printed 421.4, 420.9, 421.4 K, stored as the 423.0 label")
    for i, T in [(453, 421.4), (454, 420.9), (455, 421.4), (456, 420.9), (457, 421.4)]:
        _set(yh, i, "T_K", T, 423.0)
    for i, T in [(450, 348.3), (451, 348.3), (452, 348.2)]:
        _set(yh, i, "T_K", T)
    log("yh2o_co2_binary", 8, "state corrected", "SAKO Table 1: T printed as 421.4/420.9 K and 348.3/348.2 K, stored as the 423.0 and 348.0 labels")
    for i, T in [(68, 292.7), (71, 297.9), (72, 297.6)]:
        assert yh.at[i, "source"] == "CHAPOY(2005)"
        _set(yh, i, "T_K", T)
    log("yh2o_ch4_binary", 3, "state corrected", "CHAPOY(2005): printed T 292.7, 297.9, 297.6 K, stored as the 293.0 and 298.0 labels")

    # ---- 3. rows that are not measurements of the stated quantity, or that the source retracted or contradicts ------------------
    for df in (sol, yh):
        for src, flag, why in [
            ("SUSAK(1980)", "calculated-not-measured", "USGS open-file report 80-371 prints output of a TI-59 program (Haas 1978 equation, stated valid to 10,000 psi), not measurements; "
             "extrapolated cells to 623 K and 20,000 psi include non-physical values"),
            ("SACHS(1995)", "calculated-not-measured", "the methane mole fractions of this surface-tension study are calculated from literature solubility correlations, not measured"),
        ]:
            m = df["source"] == src
            for i in df.index[m]:
                _add_flag(df, i, flag)
            if m.sum():
                log(src, int(m.sum()), f"flagged {flag}", why)

    for i in (6410, 6412):
        for k in (i, _sib(sol, i)):
            assert sol.at[k, "source"] == "CULBERSON(1951)"
            _add_flag(sol, k, "hydrate-regime")
    log("ch4_water_binary", 4, "flagged hydrate-regime", "CULBERSON(1951): the 77 F values above 6800 psia are printed in parentheses as non-equilibrium (hydrate present)")

    # whole blocks that are not experimental points of the stated quantity (found by the random audit, 2026-10-04)
    FLAG_RULES = [
        ("PitzerMayorga1973", None, "calculated-not-measured", "T",
         "Pitzer-Mayorga (1973) prints Pitzer parameters, not osmotic coefficients: the stored values are the Pitzer equation evaluated with the printed parameters (reproduced to 10 digits)"),
        ("MariboMogensen2013", None, "figure-digitized", None,
         "Maribo-Mogensen et al. (2013) Fig. 8 has no table: the values are read from the plotted literature points (refs 47, 48) of a figure, and the paper does not print them or the temperature"),
        ("QIN(2008)", "y_h2o", "calculated-not-measured", None,
         "Qin et al. (2008) did not measure the water content of the vapour: the printed y_H2O are estimated with Duan's model from binary data"),
        ("JUNG", None, "figure-digitized", None,
         "Jung, Knacke & Neuschuetz (1971, labelled 1968) has no data table: the hydrogen solubilities are read from smoothed curves of x against the differential pressure (Figs. 6 and 7)"),
        ("LI_2004", None, "salinity-matrix", None,
         "Li et al. (2004) Table 1 prints a Weyburn brine analysis whose six ions leave a cation deficit of 0.15 mol/kg (sum of ions 88570 mg/L against TDS 92950 mg/L): the brine carries unlisted species"),
        ("Schlaikjer2018", None, "figure-digitized", None,
         "Schlaikjer et al. (2018) Fig. 3 digitized from a figure"),
    ]
    for pref, prop, flag, newq, why in FLAG_RULES:
        n = 0
        for fam, df in old.items():
            m = df["source"].str.startswith(pref)
            if prop:
                m &= df["property"] == prop
            for i in df.index[m]:
                _add_flag(df, i, flag)
                if newq and df.at[i, "quality"] == "R":
                    df.at[i, "quality"] = newq
            n += int(m.sum())
        if n:
            log(pref, n, f"flagged {flag}", why)

    # the brine compositions of Wang et al. (2014) are printed in mmol/L and the paper gives no density: they cannot be converted to mol per kg of water
    for fam, df in old.items():
        m = df["source"] == "WANG_2014"
        for i in df.index[m]:
            _add_flag(df, i, "volume-basis-uncertain")
        if m.sum():
            log("WANG_2014", int(m.sum()), "flagged volume-basis-uncertain",
                "Wang et al. (2014) Table 1 prints the brine composition in mmol/L and mg/L at 298 K and gives no density, so the stored molalities (about the printed mmol/L divided by 1000, one of them 18 % above the print) cannot be verified or converted")

    def to_U(df, mask, who, why):
        for i in df.index[mask]:
            df.at[i, "quality"] = "U"
        if mask.sum():
            log(who, int(mask.sum()), "quality set to U", why)

    y = yh["value"].map(_f)
    to_U(yh, (yh["source"] == "TODHEIDE") & (y.sub(0.01).abs() < 5e-4), "yh2o_co2_binary",
         "TODHEIDE(1963): water content printed as the complement of y_CO2 = 99.0 mol% (+-1 mol%), so y_H2O = 0.010 +- 0.010 carries no information")
    to_U(sol, (sol["source"] == "CARROLL(1998)") & sol["T_K"].map(lambda v: _close(v, 398.0, 1e-3)), "ch4_water_binary",
         "CARROLL(1998): the printed 125 C block repeats the 75 C block (seven identical solubilities, two pressures differ); a copied block is likely")
    to_U(sol, sol["source"] == "CAMPOS(2010)", "ch4_water_binary", "CAMPOS(2010): the data are not Henry-law consistent (x/P rises 2.5 times between 1.1 and 6.4 bar)")
    assert yh.at[95, "source"] == "OLDS(1942)"
    to_U(yh, yh.index == 95, "yh2o_ch4_binary", "OLDS(1942): 35 % above the authors' own smoothed table value")
    to_U(sol, (sol["source"] == "AWAN(2010)") & sol["P_bar"].map(lambda v: True) & (sol.index.isin([6503, 6504])), "ch4_water_binary",
         "AWAN(2010) Table 8 prints x2 = 2.1e-4 and m2 = 0.013 mol/kg for one point, which disagree by 11 %")
    to_U(sol, sol["source"].eq("SABIRZYANOV(2002)") & sol.index.isin([1749, 1750]), "co2_water_binary",
         "SABIRZYANOV(2002): printed as stored, but 5-6 times below the authors' own fit and every other source")
    to_U(yh, (yh["source"] == "FROST(2013)") & yh.index.isin([73]), "yh2o_ch4_binary", "FROST(2013) 4.78 MPa, y = 0.441e-3 is 40 % off the authors' own y.P trend; a misprint is likely but not provable")
    to_U(yh, (yh["source"] == "HOU") & yh.index.isin([321]) & (yh["quality"] == "R"), "yh2o_co2_binary",
         "HOU(2013) 323.15 K, 1.089 MPa: the authors' own model gives 0.98626 where 0.97189 is printed")


def _apply_fixes_hook(old, ledger):
    apply_json_fixes(old, ledger)


def apply_new(merged, ledger):
    """Edits to v1.2 rows (already merged). Row selection by dataset_id and state, not by position."""
    remove_duplicate_copies(merged, ledger)
    sol = merged["solubility"]
    m = sol["dataset_id"].str.startswith("mohammadian2015_10.1021_je501172d_t2") & (pd.to_numeric(sol["P_bar"], errors="coerce") <= 21.5)
    for i in sol.index[m]:
        sol.at[i, "quality"] = "U"
    if m.sum():
        ledger.append({"dataset_id": "mohammadian2015_10.1021_je501172d_t2", "rows": int(m.sum()), "action": "quality set to U",
                       "reason": "MOHAMMADIAN(2015) Table 2 low-pressure points (<= 2.1 MPa) disagree with the paper's own pure-water Table 1 (0.250 against 0.315 at 2.1 MPa)"})


# ---------------------------------------------------------------------------------------------------------------------------------
# the same measurement published twice (same laboratory): the rows of the lower-precision copy that match a row of the kept copy exactly
# ---------------------------------------------------------------------------------------------------------------------------------
# (family, victim: (dataset_id prefix, source) , keeper: (dataset_id prefix, source), reason)
DUPLICATE_COPIES = [
    ("solubility", ("co2_part1", "CHABAB(2020)"), ("chabab2021_t2", None),
     "CHABAB(2020) (Multi_Salt curation of the 6 m NaCl data, rounded temperatures) repeats Chabab et al. 2021 Table 2 to six digits at 303.55 K; "
     "the 303.0 K label hid the match from the v1.1.1 duplicate pass, which removed the other nine points of the same copy"),
    ("solubility", ("millero2002_10.1016_s0016-7037(02)00838-4", None), ("millero2002b_10.1016_s0304-4203(02)00034-8", None),
     "Millero, Huang & Laferiere GCA 66 (2002) 2349 (25 C) and Mar. Chem. 78 (2002) 217 (5-45 C) report the same oxygen measurements: the GCA values equal "
     "those the Marine Chemistry paper tabulates at 25.35-25.7 C, to the last digit; the copy with the printed measurement temperatures is kept"),
    ("y_h2o", ("yarrison2006b_Yarrison_2007", None), ("yh2o_ch4_binary", "YARRISON(2006)"),
     "the Yarrison thesis (2007) repeats values of the journal data of Yarrison et al. (2006) to the last digit; the journal copy is kept"),
]


def remove_duplicate_copies(merged, ledger, tol=1e-5):
    ION_ = ["m_Na", "m_Cl", "m_K", "m_Ca", "m_Mg", "m_SO4"]
    for fam, (vds, vsrc), (kds, ksrc), why in DUPLICATE_COPIES:
        df = merged[fam]
        num = {c: pd.to_numeric(df[c], errors="coerce").to_numpy() for c in ["T_K", "P_bar", "value", *ION_]}
        vic = df["dataset_id"].str.startswith(vds) & (df["source"] == vsrc if vsrc else True) & (df["property"] != "xc_saltfree")
        kep = df["dataset_id"].str.startswith(kds) & (df["source"] == ksrc if ksrc else True) & (df["property"] != "xc_saltfree")
        kidx = np.nonzero(kep.to_numpy())[0]
        drop_keys = set()
        for i in np.nonzero(vic.to_numpy())[0]:
            m = np.abs(num["T_K"][kidx] - num["T_K"][i]) <= 1.0
            m &= df["gas"].to_numpy()[kidx] == df["gas"].to_numpy()[i]
            if not np.isnan(num["P_bar"][i]):
                pm = np.maximum(np.abs(num["P_bar"][kidx]), abs(num["P_bar"][i]))
                m &= np.isnan(num["P_bar"][kidx]) | (np.abs(num["P_bar"][kidx] - num["P_bar"][i]) <= 0.02 * np.where(pm > 0, pm, 1))
            for c in ION_:
                mm = np.maximum(np.abs(num[c][kidx]), abs(num[c][i]))
                m &= np.abs(num[c][kidx] - num[c][i]) <= 0.02 * np.where(mm > 0, mm, 1) + 1e-9
            m &= np.abs(num["value"][kidx] - num["value"][i]) <= tol * np.maximum(np.abs(num["value"][kidx]), abs(num["value"][i]))
            if m.any():
                drop_keys.add((df.at[df.index[i], "dataset_id"], df.at[df.index[i], "gas"], num["T_K"][i], num["P_bar"][i], tuple(num[c][i] for c in ION_)))
        if not drop_keys:
            continue
        keys = list(zip(df["dataset_id"], df["gas"], num["T_K"], num["P_bar"], [tuple(num[c][j] for c in ION_) for j in range(len(df))]))
        drop = np.array([(k in drop_keys) and (df["source"].iat[j] == (vsrc or df["source"].iat[j])) for j, k in enumerate(keys)])
        n = int(drop.sum())
        merged[fam] = df[~drop].reset_index(drop=True)
        ledger.append({"dataset_id": vds, "rows": n, "action": "removed (duplicate copy)", "reason": why})


# ---------------------------------------------------------------------------------------------------------------------------------
# corrections read from the papers by independent readers (release/fixes/results/*.json): each record names the stored row by its exact
# values and gives the printed ones. A record that matches no row, or more than one, stops the build.
# ---------------------------------------------------------------------------------------------------------------------------------
FIX_FILES = ["kamp_tong.json", "prutton_li_wang.json", "hou_liu_qin.json"]
FIX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "release", "fixes", "results")
M_KEYS = ["m_Na", "m_Cl", "m_K", "m_Ca", "m_Mg", "m_SO4"]


def _records(path):
    d = json.load(open(path))
    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k.startswith("corrections") and isinstance(v, list):
                    yield from v
                else:
                    yield from walk(v)
    yield from walk(d)


def apply_json_fixes(old, ledger, files=None):
    files = files or FIX_FILES
    for fn in files:
        path = os.path.join(FIX_DIR, fn)
        if not os.path.exists(path):
            continue
        n_rows, groups = 0, {}
        for rec in _records(path):
            mt, st = rec["match"], rec["set"]
            hits = []
            for fam, df in old.items():
                m = pd.Series(True, index=df.index)
                for k in ("dataset_id", "source", "property", "gas"):
                    if k in mt:
                        m &= df[k] == mt[k]
                for k in ["T_K", "P_bar", "value", "y_co2_dry", *M_KEYS]:
                    if k in mt and k in df.columns and mt[k] is not None:
                        m &= df[k].map(lambda v, t=mt[k]: _close(v, t, 5e-6))
                hits += [(fam, i) for i in df.index[m]]
            if len(hits) != 1:
                raise AssertionError(f"{fn}: {len(hits)} rows match {mt}")
            fam, i = hits[0]
            df = old[fam]
            sib = _sib(df, i) if fam == "solubility" else None
            others = []
            if fam == "ternary":   # the other rows of the same ternary state take the same T and P
                same = (df["dataset_id"] == df.at[i, "dataset_id"]) & df["T_K"].map(lambda v: _close(v, df.at[i, "T_K"])) \
                    & df["P_bar"].map(lambda v: _close(v, df.at[i, "P_bar"])) & df["y_co2_dry"].map(lambda v: _close(v, df.at[i, "y_co2_dry"]))
                others = [j for j in df.index[same] if j != i]
            sibval = None
            for k, v in st.items():
                if k == "value":
                    df.at[i, "value"] = _fmt(v)
                    if sib is not None:
                        df.at[sib, "value"] = _fmt(v / (v + 1000.0 / M_W))
                elif k == "xc_saltfree_sibling_value":
                    if sib is not None:
                        sibval = v
                elif k == "uncertainty_xc_saltfree_sibling":
                    if sib is not None:
                        df.at[sib, "uncertainty"] = _fmt(v)
                elif k in df.columns:
                    df.at[i, k] = _fmt(v)
                    if sib is not None and k != "uncertainty":
                        df.at[sib, k] = _fmt(v)
                    if k in ("T_K", "P_bar"):
                        for j in others:
                            df.at[j, k] = _fmt(v)
                else:
                    raise AssertionError(f"{fn}: unknown field {k}")
            if sibval is not None and sib is not None:
                df.at[sib, "value"] = _fmt(sibval)
                df.at[i, "value"] = _fmt(sibval / (1.0 - sibval) * 1000.0 / M_W)   # exact from the printed mole fraction
            n_rows += 1 + (sib is not None)
            groups.setdefault(mt.get("source", "?"), []).append(rec.get("printed", ""))
        for src, pr in groups.items():
            ledger.append({"dataset_id": src, "rows": 0, "action": "corrected from the paper", "reason": f"{len(pr)} points of {src} re-read against the printed table ({fn}): e.g. {pr[0][:200]}"})
        ledger.append({"dataset_id": fn, "rows": n_rows, "action": "corrected from the paper (rows touched)", "reason": f"{sum(len(v) for v in groups.values())} correction records applied"})
