"""GasBrineBench v1.2 builder: turn extracted, verified tables into database rows.

Usage: python3 gbb12_build.py [--extract DIR] [--out DIR]
Reads every extract/<slug>/ whose paper.json status is `verified_pass2` (HTML-sourced papers with status `verified_html`).
Writes out/new_rows.csv (all rows, schema columns + `m_gas` and `src_table`) and out/build_report.csv (one line per table:
rows built, rows held back, reasons). A table or row is HELD BACK, never guessed, when: the native property has no converter,
the composition basis is not usable, a unit is unknown, or a converted value fails the plausibility range of its property.
Held-back items are listed with the reason so the build report can be reviewed.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gbb12_core as C
from gbb12_loader import MappingError, load_table

SEVEN = {"co2", "ch4", "h2", "n2", "o2", "c2h6", "c3h8"}
COLUMNS = ["dataset_id", "source", "gas", "property", "T_K", "P_bar", "m_Na", "m_Cl", "m_K", "m_Ca", "m_Mg", "m_SO4",
           "value", "uncertainty", "quality", "tag", "m_gas", "src_table", "family"]

# plausibility ranges of converted values (inclusive); a value outside raises a hold-back with the reason
RANGE = {
    "solubility_molality": (0.0, 40.0),     # mol gas per kg water
    "xc_saltfree": (0.0, 0.6),
    "y_h2o": (0.0, 1.0),
    "rho": (150.0, 1500.0),                  # kg/m3 (water above 670 K and 28 MPa is about 250)
    "psat_ratio": (0.2, 1.2),
    "phi_osm": (0.1, 6.0),
    "visc": (0.02, 100.0),                   # mPa s
    "dh_sol": (-100.0, 100.0),               # kJ/mol
    "Cp_app": (-3000.0, 1000.0),             # J/(K mol)
}


# free-text composition remarks that only say "no salt" (seawater and real extra species are not benign)
BENIGN = re.compile(r"^\s*(none|pure[ \w,.()%-]*water|deioni[sz]ed|milli-?q|no salt|salt-free|degassed|pure ethane)", re.I)


SALTWORDS = re.compile(r"NaCl|KCl|CaCl|MgCl|SO4|NaBr|CaBr|brine|sea ?water|saline|salinity|salt(?!-free)|\bppt\b", re.I)


def mol_unit_factor(unit):
    """Factor to mol/kg water for a molality unit string; anything that is not clearly per kg of water is held back."""
    u = re.sub(r"[\s_]", "", (unit or "").strip().lower())
    if u in ("", "m", "molal", "mol/kg", "mol/kgh2o", "mol/(kgh2o)", "molperkgwater", "mol/kgwater", "mol.kg-1", "molkg-1", "mol/(kgwater)", "molality",
             "molperkgh2o", "mol/kgsolvent", "molkgh2o"):
        return 1.0
    if u.startswith(("mmol/kg", "mmol/(kg", "mmolperkg", "mmol.kg", "mmolkg")):
        return 1e-3
    if u.startswith(("umol/kg", "\u00b5mol/kg", "\u03bcmol/kg", "umolperkg")):
        return 1e-6
    raise Hold(f"molality unit {unit!r} not recognised")


class Hold(Exception):
    pass


def f(s):
    v = C.parse_float(s)
    return v


ION_CHARGE = {"m_Na": 1, "m_K": 1, "m_Ca": 2, "m_Mg": 2, "m_Cl": -1, "m_SO4": -2}


def ionic_weight(salt):
    """Ionic-strength weight of a salt: I = sum_i w_i m_i, w = 1/2 sum_j n_j z_j^2 (1 for 1-1, 3 for 2-1, 4 for 2-2 salts)."""
    return 0.5 * sum(n * ION_CHARGE[ion] ** 2 for ion, n in C.SALT[salt][1].items())


def ionic_strength_to_ions(rec, comp, tags):
    """Binary salt mixture given by the molal ionic strength I and the ionic-strength fraction y of one salt:
    m_y = I y / w_y, m_other = I (1 - y) / w_other. The mapping names the keys in composition.ionic_strength_rule."""
    rule = rec.get("comp_rule") or {}
    try:
        I = f(comp[rule["I"]][0])
        y = f(comp[rule["y"]][0])
    except KeyError:
        raise Hold("composition basis ionic_strength without an ionic_strength_rule in the mapping")
    if I is None or y is None or not 0.0 <= y <= 1.0:
        raise Hold("ionic strength or ionic-strength fraction not numeric")
    names = []
    for k in ("salt_y", "salt_other"):
        nm = rule.get(k, "")
        nm = comp[nm][0] if nm in comp else nm
        salt = C.normalise_salt(nm)
        if salt is None:
            raise Hold(f"salt {nm!r} outside the six-ion set")
        names.append(salt)
    s_y, s_o = names
    ions = {k: 0.0 for k in C.IONS}
    if y > 0:
        ions = C.add_ions(ions, C.salt_to_ions(s_y, I * y / ionic_weight(s_y)))
    if y < 1:
        ions = C.add_ions(ions, C.salt_to_ions(s_o, I * (1.0 - y) / ionic_weight(s_o)))
    return ions, tags


def comp_to_ions(rec, notes):
    """Resolve rec['comp'] into six ion molalities. Returns (ions dict, tags set). Raises Hold when it cannot be done safely."""
    basis = rec["comp_basis"]
    comp = rec["comp"]
    tags = set()
    ions = {k: 0.0 for k in C.IONS}
    has_sal = any("salinity" in k.lower() or "chlorinity" in k.lower() for k in comp)
    if (basis == "none" or not comp) and not has_sal:
        os_ = rec.get("other_species") or ""
        # for water-in-gas tables the remark describes the gas side; only a salt or brine word keeps the row out
        os_clean = re.sub(r"\bno salts?\b|salt-free|without salt", "", os_, flags=re.I)
        gas_side = rec.get("property") in ("y_h2o", "rho_gas_loaded", "visc") and not SALTWORDS.search(os_clean)
        if os_ and re.search(r"\bno water\b|water-free|pure (co2|ch4|h2|n2|o2|ethane|propane|c2h6|c3h8)\b", os_, re.I) and rec.get("property") in ("rho", "rho_diff", "visc", "psat_brine", "aw", "phi_osm", "phi_Cp"):
            raise Hold(f"composition is not an aqueous solution: {rec['other_species'][:60]}")
        if os_ and not BENIGN.search(os_) and not gas_side:
            raise Hold(f"composition not representable: {rec['other_species'][:60]}")
        return ions, tags
    skey = next((k for k in comp if "salinity" in k.lower() or "chlorinity" in k.lower()), None)
    if skey is not None and not re.search(r"sea ?water|ocean|marine|sea salt|\bsw\b", rec.get("other_species") or "", re.I):
        raise Hold("a salinity or chlorinity value is converted with reference seawater ions only when the mapping says the liquid is seawater")
    if skey is not None:
        S = f(comp[skey][0])
        if S is None:
            raise Hold("salinity not numeric")
        if "chlorinity" in skey.lower():
            S *= 1.80655  # Knudsen relation S = 1.80655 Cl, as stated in the paper
        ions = C.seawater_ions(C.SA_from_salinity(S))
        ions["_SA"] = C.SA_from_salinity(S)
        tags.add("salinity-matrix")
        return ions, tags
    if basis == "ionic_strength":
        return ionic_strength_to_ions(rec, comp, tags)
    # mass percent / mass fraction / mole fraction of several salts share one denominator (1 - sum of the fractions)
    vals, units = {}, {}
    for name, (val, unit) in comp.items():
        salt = C.normalise_salt(name)
        if salt is None:
            raise Hold(f"salt {name!r} outside the six-ion set")
        x = f(val)
        if x is None:
            raise Hold(f"composition value {val!r} not numeric")
        vals[salt] = vals.get(salt, 0.0) + x
        units[salt] = unit
    if basis == "g_per_kg" and rec.get("comp_water_g"):
        # grams of salt per kg of SOLUTION with the water mass per kg of solution given by the paper: no density is needed
        wg = f(str(rec["comp_water_g"]))
        if wg is None or wg <= 0:
            raise Hold("water mass per kg of solution not numeric")
        ions = {k: 0.0 for k in C.IONS}
        for salt, x in vals.items():
            ions = C.add_ions(ions, C.salt_to_ions(salt, (x / C.SALT[salt][0]) * 1000.0 / wg))
        tags.add("minor-species-omitted")
        return ions, tags
    if basis in ("normality", "g_per_kg", "g_per_L", "molarity", "ionic_strength"):
        raise Hold(f"composition basis {basis} needs a solution density that the paper does not give")
    if basis not in ("molality", "mass_percent", "mass_fraction", "mole_fraction"):
        raise Hold(f"unknown composition basis {basis!r}")
    scale = 0.01 if basis == "mass_percent" else 1.0
    total = sum(vals.values()) * scale
    if basis != "molality" and not 0.0 <= total < 1.0:
        raise Hold(f"salt fractions sum to {total:.4g}")
    for salt, x in vals.items():
        if basis == "molality":
            m = x * mol_unit_factor(units[salt])
        elif basis in ("mass_percent", "mass_fraction"):
            m = 1000.0 * (x * scale) / (C.SALT[salt][0] * (1.0 - total))
        else:  # mole_fraction of undissociated salt in the salt + water mixture
            m = 1000.0 * x / ((1.0 - total) * C.M_W)
        ions = C.add_ions(ions, C.salt_to_ions(salt, m))
    return ions, tags


def row_template(paper, mapping, n, rec):
    return {"dataset_id": f"{paper['source_key'].lower()}_{paper['slug_']}_t{n}".replace("(", "").replace(")", ""),
            "source": paper["source_key"], "quality": mapping.get("quality", "T"), "m_gas": "",
            "src_table": f"{mapping.get('table', 'Table ' + n)} p.{mapping.get('page_journal') or mapping.get('page') or '?'}"}


def tags_for(rec, mapping, T_K, gas, extra, ions=None):
    tags = set(extra)
    reg = (rec.get("regime") or mapping.get("regime") or "").lower()
    if reg == "hydrate":
        tags.add("hydrate-regime")
    if reg == "lle":
        tags.add("lle-regime")
    if T_K is not None:
        depression = 1.86 * 0.93 * sum(ions[k] for k in C.IONS) if ions else 0.0  # cryoscopic estimate of the freezing point of the brine
        if T_K < 273.15 - depression - 1e-9:
            tags.add("subfreezing")
    if (gas and gas not in SEVEN) or mapping.get("gas_mixture"):
        tags.add("gas-out-of-scope")
    return tags


def convert_T_P(rec, need_P=True):
    T = f(rec["T"])
    if T is None:
        raise Hold("temperature missing")
    T_K = C.to_K(T, rec["T_unit"])
    P = f(rec["P"])
    P_bar = None
    if P is not None:
        if not rec["P_unit"]:
            raise Hold("pressure unit missing")
        P_bar = C.to_bar(P * rec["P_scale"], rec["P_unit"])
    elif need_P:
        raise Hold("pressure missing")
    return T_K, P_bar


def total_pressure(rec, P_bar, T_K):
    """Return the total pressure in bar. For gas-partial-pressure data add the pure-water vapour pressure."""
    if rec["P_basis"] == "gas_partial":
        return P_bar + C.water_psat_bar(T_K)
    return P_bar


# ------------------------------------------------------------------------------------------------
# property converters: each returns a list of (property, family, value, uncertainty) tuples or raises Hold
# ------------------------------------------------------------------------------------------------


def rel_or_abs_unc(rec, value_native):
    """Uncertainty column -> (absolute uncertainty of the native value, relative uncertainty). Percent or relative units are relative."""
    u = f(rec["uncertainty"])
    if u is None:
        return None, None
    unit = (rec["uncertainty_unit"] or "").lower()
    if "percent" in unit or "%" in unit or "relative" in unit:
        rel = u * rec["uncertainty_scale"] / 100.0 if "percent" in unit or "%" in unit else u * rec["uncertainty_scale"]
        return rel * value_native, rel
    absu = u * rec["uncertainty_scale"]
    return absu, (absu / value_native if value_native else None)


def conv_solubility_x(rec, mapping, T_K, P_bar, ions, tags):
    x = f(rec["value"])
    if x is None:
        raise Hold("value missing")
    x *= rec["value_scale"]
    has_salt = any(ions[k] > 0 for k in C.IONS)
    if has_salt and mapping.get("gas_basis") != "salt_free":
        raise Hold("gas mole fraction in a salt solution: mapping does not state gas_basis = salt_free (basis of x not established)")
    unc, rel = rel_or_abs_unc(rec, x)
    x_other = 0.0
    if mapping.get("value2_gas_in_liquid"):
        x2 = f(rec.get("value2"))
        x_other = (x2 * rec["value2_scale"]) if x2 is not None else 0.0
    if x + x_other >= 1.0:
        raise Hold("liquid mole fractions of the gases exceed 1")
    mol = x / (1.0 - x - x_other) * 1000.0 / C.M_W  # per kg water; water fraction excludes all dissolved gases
    out = [("xc_saltfree", "solubility", x, unc),
           ("solubility_molality", "solubility", mol, (rel * mol) if rel is not None else None)]
    return out


def conv_solubility_molality(rec, mapping, T_K, P_bar, ions, tags):
    m = f(rec["value"])
    if m is None:
        raise Hold("value missing")
    m *= rec["value_scale"]
    unit = (rec["value_unit"] or "").lower()
    if "solution" not in unit and rec["value_scale"] == 1.0:
        # micro- and millimolal units printed in the unit string (mapping has no scale): convert once; a mapping that already carries
        # a scale is left alone so nothing is scaled twice
        pref = unit.replace("_", "").replace(" ", "")
        if pref.startswith(("umol", "\u00b5mol", "\u03bcmol")):
            m *= 1e-6
        elif pref.startswith("mmol"):
            m *= 1e-3
    if "solution" in unit:
        # amount of gas per kg of solution -> per kg of water: n(1 + s) / (1 - n M_gas/1000), s = kg salt per kg water
        pref = unit.replace("_", "").replace(" ", "")
        # the unit prefix is applied only when the mapping carries no scale of its own (never scale twice)
        fac = 1.0
        if rec["value_scale"] == 1.0:
            fac = 1e-6 if pref.startswith(("umol", "µmol", "μmol")) else (1e-3 if pref.startswith("mmol") else 1.0)
        gas = (rec["gas"] or "").lower()
        Mg = GAS_M.get(gas)
        if Mg is None:
            raise Hold(f"molar mass of gas {gas!r} unknown for the solution-to-water conversion")
        n = m * fac
        s = sum(ions[k] * C.ION_MASS[k] for k in C.IONS) / 1000.0
        if ions.get("_SA"):
            s = ions["_SA"] / (1000.0 - ions["_SA"])
        if n * Mg / 1000.0 >= 1.0:
            raise Hold("dissolved gas mass exceeds the solution mass")
        m = n * (1.0 + s) / (1.0 - n * Mg / 1000.0)
        tags.add("solution-basis-converted")
    u = rec["uncertainty"]
    unc = f(u) * rec["uncertainty_scale"] if f(u) is not None else None
    air = mapping.get("air_equilibrated")
    if air:
        # solution equilibrated with air at the stated total pressure: stored as the binary gas-water equivalent
        # (total = gas partial pressure + water vapour pressure), gas partial pressure = air fraction x (P - psat)
        if P_bar is None:
            raise Hold("pressure missing")
        ps = C.water_psat_bar(T_K)
        p_gas = float(air["y"]) * (P_bar - ps)
        return [("solubility_molality", "solubility", m, unc, p_gas + ps),
                ("xc_saltfree", "solubility", C.x_saltfree_from_molality(m), None, p_gas + ps)]
    return [("solubility_molality", "solubility", m, unc)]


def conv_y_h2o(rec, mapping, T_K, P_bar, ions, tags):
    y = f(rec["value"])
    if y is None:
        raise Hold("value missing")
    y *= rec["value_scale"]
    if "ppm_basis_not_stated" in (rec["value_unit"] or ""):
        raise Hold("ppm basis (mole or mass) not stated")
    if "water" not in (rec["value_unit"] or "").lower():
        raise Hold(f"unit {rec['value_unit']!r} is not a water mole fraction")
    return [("y_h2o", "y_h2o", y, None)]


def conv_psat_brine(rec, mapping, T_K, P_bar, ions, tags):
    """Brine vapor pressure: ratio to IAPWS-95 saturation pressure of pure water at the same T."""
    p = f(rec["value"]) if rec["value"] is not None else None
    if p is None:
        # when the pressure column holds the vapour pressure (value empty)
        p = f(rec["P"])
        p = p * rec["P_scale"] if p is not None else None
        unit = rec["P_unit"]
    else:
        unit = rec["value_unit"]
    if p is None:
        raise Hold("vapor pressure missing")
    p_bar = C.to_bar(p * (rec["value_scale"] if rec["value"] is not None else 1.0), unit)
    ps = C.water_psat_bar(T_K)
    if mapping.get("value_is_differential") == "water_minus_solution":
        # the tabulated quantity is dP = P(pure water) - P(solution) at the same T: the solution pressure is psat(T) - dP
        tags.add("differential-pressure-converted")
        return [("psat_ratio", "psat_ratio", (ps - p_bar) / ps, None)]
    return [("psat_ratio", "psat_ratio", p_bar / ps, None)]


def p_gas_total(rec, P_bar, T_K):
    """Return (gas partial pressure, total pressure) in bar from the stated pressure and its basis."""
    if P_bar is None:
        raise Hold("pressure missing")
    ps = C.water_psat_bar(T_K)
    b = rec["P_basis"]
    if b == "gas_partial":
        return P_bar, P_bar + ps
    if b == "total":
        if P_bar - ps <= 0:
            raise Hold("total pressure not above water vapour pressure")
        return P_bar - ps, P_bar
    raise Hold(f"pressure basis {b!r} (partial or total) not stated")


def require_pure(ions, why):
    if any(ions[k] > 0 for k in C.IONS):
        raise Hold(f"{why} needs the brine density, which is not available for a salt solution")


def two_x_rows(m, unc_m=None):
    """A solubility given as mol/kg water yields both stored solubility properties (as the v1.1.1 solubility file does)."""
    return [("solubility_molality", "solubility", m, unc_m), ("xc_saltfree", "solubility", C.x_saltfree_from_molality(m), None)]


def conv_henry(rec, mapping, T_K, P_bar, ions, tags):
    """Henry constant H = f/x (pure water, dilute) to the gas solubility at the stated gas partial pressure.
    Valid when the gas partial pressure is low (ideal-gas fugacity, no Poynting correction); otherwise held back."""
    require_pure(ions, "Henry constant")
    H = f(rec["value"])
    if H is None:
        raise Hold("value missing")
    unit = (rec["value_unit"] or "").lower()
    if unit.startswith("ln("):
        raise Hold("Henry constant at zero pressure without a measurement pressure")
    H_bar = C.to_bar(H * rec["value_scale"], rec["value_unit"])
    p_g, p_tot = p_gas_total(rec, P_bar, T_K)
    if p_g > 3.0:
        raise Hold(f"gas partial pressure {p_g:.2f} bar too high for x = p/H (gas fugacity needed)")
    x = p_g / H_bar
    m = C.molality_from_x_saltfree(x)
    # ideal-gas fugacity and no Poynting correction bias x by up to about 1 % (0.3 % CH4, 0.8 % C2H6 at 1 atm): 1 % relative uncertainty is stored
    return [("xc_saltfree", "solubility", x, 0.01 * x),
            ("solubility_molality", "solubility", m, 0.01 * m)]


def volume_basis_tag(mapping, tags):
    """Per-volume quantities of seawater: `solution` (stated) is used as is; anything else is converted as if per volume of solution
    and flagged with the tag volume-basis-uncertain (the effect is the seawater density, up to about 2.6 % at S = 35)."""
    vb = mapping.get("volume_basis", "not_stated")
    if vb != "solution":
        tags.add("volume-basis-uncertain")
    return vb


def conv_bunsen(rec, mapping, T_K, P_bar, ions, tags):
    """Bunsen coefficient (cm3 gas at STP per cm3 of solvent or solution at 1 atm gas partial pressure); solubility is scaled to the stated
    gas partial pressure. Pure water, or seawater when the mapping states volume_basis = solution (then TEOS-10 density gives the water mass)."""
    SA = ions.get("_SA", 0.0)
    if SA == 0 and any(ions[k] > 0 for k in C.IONS):
        raise Hold("Bunsen coefficient of a single-salt solution needs the solution density")
    if SA > 0:
        vb = volume_basis_tag(mapping, tags)
    a = f(rec["value"])
    if a is None:
        raise Hold("value missing")
    a *= rec["value_scale"]
    if rec["P_basis"] != "gas_partial":
        raise Hold("Bunsen coefficient needs the gas partial pressure")
    p_g, p_tot = p_gas_total(rec, P_bar, T_K)
    if SA > 0:
        rho = C.seawater_density_gcm3(T_K, SA)
        m = a * 1000.0 / (22414.0 * rho * (1.0 - SA / 1000.0)) * p_g / 1.01325
    else:
        m = C.molality_from_bunsen(a, T_K, p_tot) * p_g / 1.01325
    return two_x_rows(m)


def conv_ostwald(rec, mapping, T_K, P_bar, ions, tags):
    """Ostwald coefficient (ideal gas) to mol/kg water, pure water. The authors' own mole fraction (value2), when printed, is a cross-check."""
    require_pure(ions, "Ostwald coefficient")
    L = f(rec["value"])
    if L is None:
        raise Hold("value missing")
    L *= rec["value_scale"]
    p_g, p_tot = p_gas_total(rec, P_bar, T_K)
    m = C.molality_from_ostwald(L, p_g, T_K, p_tot)
    x_auth = f(rec.get("value2"))
    if x_auth is not None and "mole_fraction" in (rec.get("value2_unit") or ""):
        x_auth *= rec["value2_scale"]
        x_mine = C.x_saltfree_from_molality(m)
        if abs(x_mine / x_auth - 1.0) > 0.02:
            raise Hold(f"converted mole fraction {x_mine:.4g} differs from the authors' {x_auth:.4g} by more than 2 %")
    return two_x_rows(m)


def conv_gas_volume(rec, mapping, T_K, P_bar, ions, tags):
    """Oxygen (ml STP per litre of water) from air of 20.94 % O2 at 100 % relative humidity and 1 atm; pure water only.
    Stored as the binary O2-water equivalent: total pressure = O2 partial pressure + water vapour pressure."""
    unit = rec["value_unit"] or ""
    if re.search(r"(cm3|ml)_?(gas_)?stp.*per_g_?(of_)?water", unit.lower().replace(" ", "")):
        return conv_gas_volume_per_mass(rec, mapping, T_K, P_bar, ions, tags)
    SA = ions.get("_SA", 0.0)
    if SA == 0 and any(ions[k] > 0 for k in C.IONS):
        raise Hold("ml/l of a single-salt solution needs the solution density")
    if SA > 0:
        volume_basis_tag(mapping, tags)
    if "from_air_20.94pct_O2_100pct_RH" not in unit or not unit.startswith("ml_O2_per_litre"):
        raise Hold(f"unit {unit!r} not recognised")
    v = f(rec["value"])
    if v is None:
        raise Hold("value missing")
    P_atm = 1.01325 if P_bar is None else P_bar
    ps = C.water_psat_bar(T_K)
    p_o2 = 0.2094 * (P_atm - ps)
    if SA > 0:
        rho = C.seawater_density_gcm3(T_K, SA) * (1.0 - SA / 1000.0)  # kg water per litre of solution
    else:
        rho = C.water_rho_kgm3(T_K, P_atm) / 1000.0  # kg per litre
    m = (v / 1000.0 / 22.414) / rho
    return [(pn, fam, val, unc, p_o2 + ps) for pn, fam, val, unc in two_x_rows(m)]


STP_MOLAR_VOLUME_L = 22.414  # litres per mole at 0 C and 1 atm; old papers rarely define "S.T.P." and this convention is tagged `stp-assumed`


def conv_gas_volume_per_mass(rec, mapping, T_K, P_bar, ions, tags):
    """cm3 (or mL) of gas at STP per gram of water -> mol gas per kg water. Per mass of water, so no solution density is needed.
    The standard-state convention (0 C, 1 atm) is assumed and tagged; the pressure is carried as stated (total or gas partial)."""
    v = f(rec["value"])
    if v is None:
        raise Hold("value missing")
    v *= rec["value_scale"]
    if P_bar is None:
        raise Hold("pressure missing")
    m = v / STP_MOLAR_VOLUME_L  # (cm3/g) = (mL/g) -> mol/kg: v*1e-3 L/g * 1000 g/kg / 22.414 L/mol
    tags.add("stp-assumed")
    return two_x_rows(m)


def conv_water_content_mass(rec, mapping, T_K, P_bar, ions, tags):
    """Water content of a compressed gas given as a mass ratio or as grams per litre of the dry gas expanded to STP -> mole fraction of water."""
    v = f(rec["value"])
    if v is None:
        raise Hold("value missing")
    v *= rec["value_scale"]
    unit = (rec["value_unit"] or "").lower()
    gas = (rec["gas"] or "").lower()
    n_w = None
    if "per_g_gas" in unit:
        Mg = GAS_M.get(gas)
        if Mg is None:
            raise Hold(f"molar mass of gas {gas!r} unknown")
        if not 0.0 <= v < 1.0:
            raise Hold("water mass fraction outside 0-1")
        n_w, n_g = v / C.M_W, (1.0 - v) / Mg
    elif "per_l" in unit and "stp" in unit:
        n_w, n_g = v / C.M_W, 1.0 / STP_MOLAR_VOLUME_L
        tags.add("stp-assumed")
    else:
        raise Hold(f"unit {rec['value_unit']!r} not recognised")
    y = n_w / (n_w + n_g)
    return [("y_h2o", "y_h2o", y, None)]


def conv_phi_osm_value(rec, mapping, T_K, P_bar, ions, tags):
    """Osmotic coefficient printed in the value column for a single salt of the six-ion set."""
    v = f(rec["value"])
    if v is None:
        raise Hold("value missing")
    salts = [k for k in rec["comp"] if C.normalise_salt(k)]
    if len(salts) != 1:
        raise Hold("osmotic coefficient of a mixture or of a salt outside the six-ion set")
    return [("phi_osm", "phi_osm", v * rec["value_scale"], None)]


def conv_k0(rec, mapping, T_K, P_bar, ions, tags):
    """Solubility coefficient K0 (mol per litre of solution per atm of gas fugacity) -> solubility at 1 atm gas fugacity (approximated by pressure),
    in mol per kg water, using the solution density (TEOS-10 for seawater, IAPWS-95 for pure water)."""
    v = f(rec["value"])
    if v is None:
        raise Hold("value missing")
    c = v * rec["value_scale"]  # mol/L at 1 atm
    SA = ions.get("_SA", 0.0)
    if SA == 0 and any(ions[k] > 0 for k in C.IONS):
        raise Hold("K0 of a single-salt solution needs the solution density")
    if SA > 0:
        rho_sol = C.seawater_density_gcm3(T_K, SA)  # kg/L
        water_kg_per_L = rho_sol * (1.0 - SA / 1000.0)
    else:
        water_kg_per_L = C.water_rho_kgm3(T_K, 1.01325) / 1000.0
    tags.add("fugacity-as-pressure")
    return two_x_rows(c / water_kg_per_L)


def density_factor(unit):
    """Factor to kg/m3 for a density unit string; anything else is held back (never assume a scale)."""
    u = (unit or "").lower().replace(" ", "")
    if u in ("kg/m3", "kgm-3", "kg.m-3", "kg_per_m3", "kg/m^3"):
        return 1.0
    if u in ("g/cm3", "gcm-3", "g.cm-3", "g_per_cm3", "g.cm^-3", "g/cm^3", "g/ml"):
        return 1000.0
    raise Hold(f"density unit {unit!r} not recognised")


def conv_rho_diff(rec, mapping, T_K, P_bar, ions, tags):
    """Density difference to density: IAPWS-95 water density at the reference state plus the measured difference.
    When the authors print the density itself (value2), it is stored and cross-checked against the IAPWS-based value within 0.3 %."""
    d = f(rec["value"])
    if d is None:
        raise Hold("value missing")
    d *= rec["value_scale"] * density_factor(rec["value_unit"])
    if P_bar is None:
        raise Hold("pressure missing")
    p1 = f(rec["x"].get("p1")) if rec.get("x") else None
    P_ref = C.to_bar(p1, "MPa") if p1 is not None else P_bar
    rho_mine = C.water_rho_kgm3(T_K, P_ref) + d
    rho = rho_mine
    r2 = f(rec.get("value2"))
    if r2 is not None:
        try:
            r2_fac = density_factor(rec.get("value2_unit"))  # value2 is the authors' density only when its unit is a density unit
        except Hold:
            r2 = None
    if r2 is not None:
        r2 *= r2_fac
        if abs(rho_mine / r2 - 1.0) > 0.003:
            raise Hold(f"IAPWS-based density {rho_mine:.1f} differs from the authors' {r2:.1f} by more than 0.3 %")
        rho = r2
    return [("rho", "rho", rho, None)]


def conv_phi_osm(rec, mapping, T_K, P_bar, ions, tags):
    """Osmotic coefficient printed by the authors for a single-salt solution of the six-ion set."""
    key = next((k for k in (rec.get("x") or {}) if k.lower().startswith("phi")), None)
    v = None
    if key is not None:
        v = f(rec["x"][key])
    if v is None and "osmotic" in (rec.get("value2_unit") or "").lower():
        v = f(rec.get("value2"))
    if v is None:
        raise Hold("no printed osmotic coefficient")
    salts = [k for k in rec["comp"] if C.normalise_salt(k)]
    if len(salts) != 1:
        raise Hold("osmotic coefficient of a mixture or of a salt outside the six-ion set")
    if key is not None and key.lower() not in ("phi", "phi_" + salts[0].lower()):
        raise Hold(f"osmotic-coefficient column {key!r} belongs to a different salt")
    return [("phi_osm", "phi_osm", v, None)]


def conv_dh_sol(rec, mapping, T_K, P_bar, ions, tags):
    """Calorimetric enthalpy of solution (first value column only; values taken from the literature or derived from solubility fits are not used)."""
    v = f(rec["value"])
    if v is None:
        raise Hold("value missing")
    if not (rec.get("gas") or "").strip():
        raise Hold("enthalpy of solution of a salt (no gas): kept in the supplementary tier, not a gas enthalpy of solution")
    v *= rec["value_scale"]
    unit = (rec["value_unit"] or "").lower()
    if unit.startswith("j_per_mol") or unit.startswith("j/mol"):
        unit = "j/mol"  # J per mole of the named salt or gas
    if unit in ("kj/mol",):
        pass
    elif unit in ("j/mol",):
        v /= 1000.0
    else:
        raise Hold(f"unit {rec['value_unit']!r} not recognised")
    u = rec["uncertainty"]
    unc = f(u) * rec["uncertainty_scale"] if f(u) is not None else None
    return [("dh_sol", "dh_sol", v, unc)]


def conv_phi_cp(rec, mapping, T_K, P_bar, ions, tags):
    """Apparent molar heat capacity of a salt solution (thermo_brine family)."""
    v = f(rec["value"])
    if v is None:
        raise Hold("value missing")
    if re.sub(r"[\s_]", "", rec["value_unit"] or "").lower() not in ("j/(molk)", "j/(kmol)", "jperkpermol", "jpermolperk", "jk-1mol-1", "jmol-1k-1", "j/molk", "j/kmol"):
        raise Hold(f"unit {rec['value_unit']!r} not recognised")
    u = rec["uncertainty"]
    unc = f(u) if f(u) is not None else None
    return [("Cp_app", "thermo_brine", v * rec["value_scale"], unc)]


def conv_rho(rec, mapping, T_K, P_bar, ions, tags):
    """Directly measured density of a salt solution (kg/m3 or g/cm3)."""
    v = f(rec["value"])
    if v is None:
        raise Hold("value missing")
    fac = density_factor(rec["value_unit"])
    if P_bar is None:
        raise Hold("pressure missing")
    return [("rho", "rho", v * rec["value_scale"] * fac, None)]


def conv_unsupported(reason):
    def _c(rec, mapping, T_K, P_bar, ions, tags):
        raise Hold(reason)
    return _c


GAS_M = {"co2": 44.0095, "ch4": 16.0425, "h2": 2.01588, "n2": 28.0134, "o2": 31.9988, "c2h6": 30.069, "c3h8": 44.0956}


def m_gas_from_loading(rec, ions, gas):
    """Dissolved gas in mol per kg water from the loading of a gas-loaded solution (mass fraction w of the gas in the solution, or the
    salt-free mole fraction x of the gas)."""
    load = rec.get("gas_loading") or {}
    if not load:
        raise Hold("gas loading not stated")
    M = GAS_M.get(gas)
    if M is None:
        raise Hold(f"molar mass of gas {gas!r} unknown")
    wkey = next((k for k in load if k.startswith("w_")), None)
    xkey = next((k for k in load if k.startswith("x_")), None)
    salt_per_kg_water = sum(ions[k] * C.ION_MASS[k] for k in C.IONS) / 1000.0
    if wkey is not None:
        w = f(load[wkey][0])
        if w is None or not 0.0 <= w < 1.0:
            raise Hold("gas mass fraction not numeric")
        water_mass = (1.0 - w) / (1.0 + salt_per_kg_water)
        return (w / M * 1000.0) / water_mass if w > 0 else 0.0
    x = f(load[xkey][0])
    if x is None or not 0.0 <= x < 1.0:
        raise Hold("gas mole fraction not numeric")
    if any(ions[k] > 0 for k in C.IONS):
        raise Hold("gas mole fraction in a salt solution: basis not established")
    return C.molality_from_x_saltfree(x)


def conv_rho_gas(rec, mapping, T_K, P_bar, ions, tags):
    """Density of a gas-loaded solution; m_gas = dissolved gas in mol/kg water."""
    v = f(rec["value"])
    if v is None:
        raise Hold("value missing")
    fac = density_factor(rec["value_unit"])
    if P_bar is None:
        raise Hold("pressure missing")
    gas = (rec["gas"] or "").lower()
    mg = m_gas_from_loading(rec, ions, gas)
    return [("rho", "rho_gas", v * rec["value_scale"] * fac, None, None, {"m_gas": mg, "gas": gas})]


def conv_visc(rec, mapping, T_K, P_bar, ions, tags):
    v = f(rec["value"])
    if v is None:
        raise Hold("value missing")
    unit = (rec["value_unit"] or "").lower().replace(" ", "")
    if unit not in ("mpa_s", "mpa.s", "mpas", "mpa*s"):
        raise Hold(f"viscosity unit {rec['value_unit']!r} not recognised")
    if P_bar is None:
        raise Hold("pressure missing")
    gas = (rec["gas"] or "").lower()
    if gas and not rec.get("gas_loading"):
        raise Hold("viscosity of a gas-loaded solution without a stated gas loading")
    mg = m_gas_from_loading(rec, ions, gas) if rec.get("gas_loading") else ""
    return [("visc", "visc", v * rec["value_scale"], None, None, {"m_gas": mg, "gas": gas})]


def conv_aw(rec, mapping, T_K, P_bar, ions, tags):
    """Water activity to the vapour-pressure ratio; only below the normal boiling point where vapour non-ideality is small."""
    if T_K > 373.15 and not mapping.get("vapour_nonideality_corrected"):
        raise Hold("water activity above 373 K: vapour non-ideality not handled")
    if T_K > 373.15:
        tags.add("vapour-nonideality-by-authors")
    v = f(rec["value"])
    if v is None:
        raise Hold("value missing")
    return [("psat_ratio", "psat_ratio", v * rec["value_scale"], None)]


CONVERTERS = {
    "solubility_x": conv_solubility_x,
    "solubility_molality": conv_solubility_molality,
    "y_h2o": conv_y_h2o,
    "psat_brine": conv_psat_brine,
    "henry": conv_henry,
    "bunsen": conv_bunsen,
    "ostwald": conv_ostwald,
    "gas_volume_solubility": conv_gas_volume,
    "rho_diff": conv_rho_diff,
    "isopiestic_molality": conv_phi_osm,
    "dh_sol": conv_dh_sol,
    "phi_Cp": conv_phi_cp,
    "aw": conv_aw,
    "rho": conv_rho,
    "rho_gas_loaded": conv_rho_gas,
    "visc": conv_visc,
    "water_content_mass": conv_water_content_mass,
    "phi_osm": conv_phi_osm_value,
    "k0_molar_per_atm": conv_k0,
    "bpe": conv_unsupported("boiling-point elevation of a mixed-salt solution given in mol/L: needs the solution density; not converted"),
}
NO_PRESSURE_OK = {"psat_brine", "dh_sol", "isopiestic_molality", "gas_volume_solubility", "aw", "phi_osm", "phi_Cp"}
# properties of liquid solutions that hardly depend on pressure: with --allow-unstated-pressure a row without any stated pressure at
# T <= 373.15 K is built at 1 atm for the conversion, stored with an EMPTY pressure and tagged `pressure-unstated`
PRESSURE_FLEX = {"rho", "rho_diff", "visc"}
ALLOW_UNSTATED_P = False


def build_table(extract_dir, slug, n):
    # a table held or marked as a duplicate by its mapping is not loaded at all (its layout may not be readable by the loader)
    raw_map = json.load(open(os.path.join(extract_dir, slug, f"mapping_{n}.json")))
    if raw_map.get("hold_table") or raw_map.get("duplicate_of"):
        paper = json.load(open(os.path.join(extract_dir, slug, "paper.json")))
        paper["slug_"] = slug
        if raw_map.get("hold_table"):
            return raw_map, paper, [], [(None, "held by mapping: " + str(raw_map["hold_table"])[:120])]
        return raw_map, paper, [], [(None, f"not built: duplicate of {raw_map['duplicate_of'][:40]}")]
    mapping, paper, recs = load_table(extract_dir, slug, n)
    paper["slug_"] = slug
    prop = mapping.get("property")
    rows, held = [], []
    if prop not in CONVERTERS and not any(r.get("property") in CONVERTERS for r in recs):
        return mapping, paper, [], [(None, f"native property {prop!r} has no converter yet")]
    for rec in recs:
        try:
            conv = CONVERTERS.get(rec.get("property"))
            if conv is None:
                raise Hold(f"native property {rec.get('property')!r} has no converter yet")
            prop = rec["property"]
            gas = (rec["gas"] or "").lower()
            if gas == "mixture":
                raise Hold("gas-phase mixture: the composition of the gas phase has no column in the database")
            if rec.get("held_reason"):
                raise Hold("held by mapping: " + rec["held_reason"][:80])
            if rec.get("duplicate_row"):
                raise Hold("same measurement as a row of another table already built (duplicate)")
            if rec.get("from_literature_row"):
                raise Hold("value taken by the authors from other literature, not their own measurement")
            unstated_P = False
            try:
                T_K, P_bar = convert_T_P(rec, need_P=(prop not in NO_PRESSURE_OK))
            except Hold as h:
                if str(h) == "pressure missing" and ALLOW_UNSTATED_P and prop in PRESSURE_FLEX and f(rec["T"]) is not None \
                        and C.to_K(f(rec["T"]), rec["T_unit"]) <= 373.15:
                    T_K, P_bar, unstated_P = C.to_K(f(rec["T"]), rec["T_unit"]), 1.01325, True
                else:
                    raise
            ions, ctags = comp_to_ions(rec, None)
            if unstated_P or (P_bar is None and prop in NO_PRESSURE_OK and prop != "psat_brine" and rec["P_basis"] != "saturation"):
                ctags = set(ctags) | {"pressure-unstated"}
            if prop == "psat_brine":
                P_out = None
            elif unstated_P:
                P_out = None
            elif P_bar is None:
                # no printed pressure: saturation-pressure data get the IAPWS-95 water value, others stay empty
                P_out = C.water_psat_bar(T_K) if rec["P_basis"] == "saturation" and T_K < 640 else None
            else:
                P_out = total_pressure(rec, P_bar, T_K)
            outs = conv(rec, mapping, T_K, P_bar, ions, ctags)
            for o in outs:
                pname, fam, val, unc = o[:4]
                P_row = o[4] if len(o) > 4 and o[4] is not None else P_out
                extras = o[5] if len(o) > 5 else {}
                lo, hi = RANGE[pname]
                if not (lo <= val <= hi):
                    raise Hold(f"{pname} value {val:.4g} outside plausible range {lo}-{hi}")
                tg = tags_for(rec, mapping, T_K, gas, ctags | {"test-only"} | set(mapping.get("row_tag_all") or []) | ({"source-caution"} if mapping.get("caution") else set()), ions)
                tg.discard("test-only") if len(tg) > 1 else None
                row = row_template(paper, mapping, n, rec)
                row.update({"gas": "" if fam in ("psat_ratio", "rho", "phi_osm", "thermo_brine") else gas, "property": pname, "T_K": round(T_K, 3),
                            "P_bar": "" if P_row is None else round(P_row, 4), "value": float(f"{val:.10g}"), "uncertainty": "" if unc is None else unc,
                            "tag": ";".join(sorted(tg)), "family": fam})
                row.update({k: round(ions[k], 8) for k in C.IONS})
                row.update(extras)
                rows.append(row)
        except Hold as h:
            held.append((rec["idx"], str(h)))
        except NotImplementedError:
            held.append((rec["idx"], "state outside the range of the IAPWS-95 reference (T or P)"))
        except (ValueError, MappingError) as e:
            held.append((rec["idx"], f"error: {e}"))
    return mapping, paper, rows, held


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extract", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "extract"))
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
    ap.add_argument("--include-unverified", action="store_true", help="also build papers with status extracted_html (for audits only)")
    ap.add_argument("--allow-unstated-pressure", action="store_true",
                    help="build density, density-difference and viscosity rows of liquid solutions (T <= 373.15 K) whose paper states no pressure: "
                         "converted at 1 atm, stored with an empty pressure and tagged pressure-unstated")
    a = ap.parse_args()
    global ALLOW_UNSTATED_P
    ALLOW_UNSTATED_P = a.allow_unstated_pressure
    os.makedirs(a.out, exist_ok=True)
    ok_status = ("verified_pass2", "verified_html") + (("extracted_html",) if a.include_unverified else ())
    all_rows, report, notes = [], [], []
    for pj in sorted(os.listdir(a.extract)):
        base = os.path.join(a.extract, pj)
        if not os.path.isfile(os.path.join(base, "paper.json")):
            continue
        paper = json.load(open(os.path.join(base, "paper.json")))
        if paper.get("status") not in ok_status:
            continue
        for fn in sorted(os.listdir(base)):
            m = re.match(r"mapping_(.+)\.json$", fn)
            if not m or not os.path.exists(os.path.join(base, f"table_{m.group(1)}.csv")):
                continue
            n = m.group(1)
            try:
                mapping, paper, rows, held = build_table(a.extract, pj, n)
            except (MappingError, ValueError, KeyError) as e:
                report.append({"slug": pj, "table": n, "property": None, "built": 0, "held": 0,
                               "reasons": f"TABLE ERROR: {str(e)[:150]}"})
                continue
            reasons = Counter(r for _, r in held)
            report.append({"slug": pj, "table": n, "property": mapping.get("property"), "built": len(rows), "held": len(held),
                           "reasons": "; ".join(f"{k} (x{v})" for k, v in reasons.most_common(4))})
            all_rows.extend(rows)
            if mapping.get("caution") and rows:
                notes.append({"source": paper["source_key"], "doi": paper.get("doi", pj), "table": n, "rows_built": len(rows),
                              "quality": mapping.get("quality", "T"), "caution": mapping["caution"]})
    with open(os.path.join(a.out, "new_rows.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(all_rows)
    with open(os.path.join(a.out, "build_report.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["slug", "table", "property", "built", "held", "reasons"])
        w.writeheader()
        w.writerows(report)
    with open(os.path.join(a.out, "source_notes.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["source", "doi", "table", "rows_built", "quality", "caution"])
        w.writeheader()
        w.writerows(notes)
    print(f"{len(all_rows)} rows from {len(report)} tables; held back: {sum(r['held'] for r in report)}")
    byprop = Counter(r["property"] for r in report if r["built"] == 0)
    print("tables with nothing built, by native property:", dict(byprop))


if __name__ == "__main__":
    main()
