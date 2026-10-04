"""GasBrineBench v1.2 builder, core: read extracted tables, resolve mappings, convert units and compositions.

Input: extract/<doi_slug>/table_N.csv + mapping_N.json + paper.json (see extract/SPEC.md).
Nothing here is hand-converted: every conversion is a function with a unit test (test_gbb12_core.py).
Anything the code does not understand raises or is returned as a held-back row with a reason; nothing is guessed.
"""
from __future__ import annotations

import csv
import functools
import json
import math
import os
import re
from dataclasses import dataclass, field

M_W = 18.01528  # g/mol, water
R_GAS = 8.314462618  # J/(mol K)

# ---------------------------------------------------------------------------------------------
# water reference (IAPWS-95): saturation pressure and density
# ---------------------------------------------------------------------------------------------


@functools.lru_cache(maxsize=None)
def water_psat_bar(T_K: float) -> float:
    T = round(T_K, 3)
    if T < 273.16:
        # supercooled liquid below the triple point: Murphy and Koop (2005), Q. J. R. Meteorol. Soc. 131, eq. 10 (matches IAPWS-95 at 273.16 K)
        lnp = (54.842763 - 6763.22 / T - 4.210 * math.log(T) + 0.000367 * T
               + math.tanh(0.0415 * (T - 218.8)) * (53.878 - 1331.22 / T - 9.44523 * math.log(T) + 0.014025 * T))
        return math.exp(lnp) / 1e5
    from iapws import IAPWS95
    return IAPWS95(T=T, x=0).P * 10.0  # MPa -> bar


@functools.lru_cache(maxsize=None)
def water_rho_kgm3(T_K: float, P_bar: float) -> float:
    import warnings
    warnings.filterwarnings("ignore", message="Using extrapolated values")
    from iapws import IAPWS95
    return IAPWS95(T=round(T_K, 3), P=round(P_bar, 4) / 10.0).rho


# ---------------------------------------------------------------------------------------------
# simple unit conversions
# ---------------------------------------------------------------------------------------------

_P_TO_BAR = {"bar": 1.0, "pa": 1e-5, "kpa": 1e-2, "mpa": 10.0, "gpa": 1e4, "atm": 1.01325,
             "kbar": 1000.0, "kgf/cm2": 0.980665, "kgf_per_cm2": 0.980665, "kg/cm2": 0.980665, "dbar": 0.1, "psia": 0.0689475729, "psi": 0.0689475729, "torr": 0.00133322368, "mmhg": 0.00133322368}


def to_K(x: float, unit: str) -> float:
    u = unit.strip().lower()
    if u in ("k", "kelvin"):
        return x
    if u in ("c", "degc", "celsius"):
        return x + 273.15
    if u in ("f", "degf", "fahrenheit"):
        return (x - 32.0) * 5.0 / 9.0 + 273.15
    raise ValueError(f"unknown temperature unit {unit!r}")


def to_bar(x: float, unit: str) -> float:
    u = unit.strip().lower()
    if u in _P_TO_BAR:
        return x * _P_TO_BAR[u]
    raise ValueError(f"unknown pressure unit {unit!r}")


_NUM = re.compile(r"^\s*([-+−–]?\d*\.?\d+(?:[eE][-+]?\d+)?)")


def parse_float(s):
    """Parse a printed number; return None for blanks and dashes. Handles unicode minus and a trailing footnote letter."""
    if s is None:
        return None
    t = str(s).strip()
    if t in ("", "-", "--", "–", "—", "n.d.", "nd", "n.a.", "NA"):
        return None
    t = t.replace("−", "-").replace("–", "-")
    m = _NUM.match(t)
    if not m:
        return None
    return float(m.group(1))


def parse_scale(s) -> float:
    """scale may be a number or a string such as 'x1e-4 (printed x 10^4)' or '1e-6'."""
    if s is None or s == "":
        return 1.0
    if isinstance(s, (int, float)):
        return float(s)
    m = re.match(r"^\s*[xX*]?\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)", str(s))
    if m:
        return float(m.group(1))
    raise ValueError(f"cannot parse scale {s!r}")


def unit_scale_from_name(unit: str) -> float:
    """A unit name such as 'mole_fraction..._times_1e4' means the printed number is 1e4 x the quantity; return the factor to multiply with."""
    m = re.search(r"times_?1e(\d+)", unit or "")
    if m:
        return 10.0 ** (-int(m.group(1)))
    return 1.0


# ---------------------------------------------------------------------------------------------
# composition: salts to ion molalities (mol per kg water)
# ---------------------------------------------------------------------------------------------

IONS = ["m_Na", "m_Cl", "m_K", "m_Ca", "m_Mg", "m_SO4"]
SALT = {  # formula -> (molar mass g/mol, {ion column: stoichiometric count})
    "NaCl": (58.4428, {"m_Na": 1, "m_Cl": 1}),
    "KCl": (74.5513, {"m_K": 1, "m_Cl": 1}),
    "CaCl2": (110.984, {"m_Ca": 1, "m_Cl": 2}),
    "MgCl2": (95.211, {"m_Mg": 1, "m_Cl": 2}),
    "Na2SO4": (142.042, {"m_Na": 2, "m_SO4": 1}),
    "MgSO4": (120.366, {"m_Mg": 1, "m_SO4": 1}),
    "K2SO4": (174.259, {"m_K": 2, "m_SO4": 1}),
}
# Reference seawater (Millero et al. 2008), g of ion per kg of seawater at S = 35.16504
SEAWATER_REF_S = 35.16504
SEAWATER_ION_G = {"m_Na": 10.78145, "m_Mg": 1.28372, "m_Ca": 0.41208, "m_K": 0.39910, "m_Cl": 19.35271, "m_SO4": 2.71235}
ION_MASS = {"m_Na": 22.98977, "m_Mg": 24.305, "m_Ca": 40.078, "m_K": 39.0983, "m_Cl": 35.453, "m_SO4": 96.0626}


def normalise_salt(name: str):
    n = re.sub(r"[\s_\-]", "", name or "")
    n = n.replace("₂", "2").replace("₄", "4")
    for k in SALT:
        if n.lower() == k.lower():
            return k
    return None


def salt_to_ions(salt: str, molality: float) -> dict:
    out = {k: 0.0 for k in IONS}
    _, st = SALT[salt]
    for ion, n in st.items():
        out[ion] += n * molality
    return out


def add_ions(a: dict, b: dict) -> dict:
    return {k: a.get(k, 0.0) + b.get(k, 0.0) for k in IONS}


def molality_from_mass_fraction(salt: str, w: float) -> float:
    """w = mass of salt per mass of solution (0-1); returns mol salt per kg water."""
    M = SALT[salt][0]
    return 1000.0 * w / (M * (1.0 - w))


def molality_from_salt_mole_fraction(x_s: float) -> float:
    """x_s = mole fraction of the (undissociated) salt in the salt+water mixture."""
    return 1000.0 * x_s / ((1.0 - x_s) * M_W)


def seawater_ions(S_permil: float) -> dict:
    """Ion molalities of reference-composition seawater of practical salinity S (per mil), mol per kg water."""
    f = S_permil / SEAWATER_REF_S
    water_kg = 1.0 - S_permil / 1000.0
    return {k: (SEAWATER_ION_G[k] * f / ION_MASS[k]) / water_kg for k in IONS}


def SA_from_salinity(S_permil: float) -> float:
    """Absolute salinity (g/kg) of reference-composition seawater from a practical or Knudsen-type salinity (per mil):
    SA = S x 35.16504/35 (Millero et al. 2008)."""
    return S_permil * SEAWATER_REF_S / 35.0


def seawater_density_gcm3(T_K: float, SA: float) -> float:
    """Seawater density at 1 atm (sea pressure 0) from the TEOS-10 equation of state, g/cm3."""
    import gsw
    return float(gsw.rho_t_exact(SA, T_K - 273.15, 0.0)) / 1000.0


# ---------------------------------------------------------------------------------------------
# gas solubility conversions
# ---------------------------------------------------------------------------------------------


def molality_from_x_saltfree(x: float) -> float:
    """Gas mole fraction on the salt-free basis (n_g / (n_g + n_w)) to mol gas per kg water."""
    return x / (1.0 - x) * 1000.0 / M_W


def x_saltfree_from_molality(m: float) -> float:
    n_w = 1000.0 / M_W
    return m / (m + n_w)


def molality_from_bunsen(alpha: float, T_K: float, P_bar_total: float, rho_w=None) -> float:
    """Bunsen coefficient (cm3 gas at STP per cm3 solvent at the gas partial pressure 1 atm) to mol/kg water.
    Pure-water solvent only. Molar volume of the gas at STP taken as 22414 cm3/mol (ideal gas)."""
    rho = rho_w if rho_w is not None else water_rho_kgm3(T_K, P_bar_total) / 1000.0  # g/cm3
    return alpha * 1000.0 / (22414.0 * rho)


def molality_from_ostwald(L: float, p_gas_bar: float, T_K: float, P_bar_total: float, rho_w=None) -> float:
    """Ostwald coefficient (gas concentration in liquid / gas concentration in gas phase, ideal gas) to mol/kg water, at gas partial pressure p_gas."""
    rho = rho_w if rho_w is not None else water_rho_kgm3(T_K, P_bar_total) / 1000.0  # g/cm3
    c_gas = (p_gas_bar * 1e5) / (R_GAS * T_K) / 1e6  # mol/cm3
    return L * c_gas / (rho / 1000.0)  # mol per kg water (rho g/cm3 -> kg/cm3 = rho/1000)


def x_from_henry(f_gas_bar: float, H_bar: float) -> float:
    """Henry's law x = f / H with H = f/x in the limit (same units)."""
    return f_gas_bar / H_bar
