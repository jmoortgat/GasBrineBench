"""Unit tests for the unit and composition conversions of the v1.2 builder (tools/builders_v1_2/gbb12_core.py).

They need numpy, iapws and gsw and are skipped where those are not installed."""
import math
import os
import sys

import pytest

pytest.importorskip("numpy")
pytest.importorskip("iapws")
pytest.importorskip("gsw")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools", "builders_v1_2"))
import gbb12_core as C  # noqa: E402


def close(a, b, rel):
    assert abs(a / b - 1.0) < rel, f"{a} vs {b}"


def test_water_reference():
    close(C.water_psat_bar(373.1243), 1.01325, 1e-4)          # normal boiling point
    close(C.water_rho_kgm3(298.15, 1.0), 997.05, 1e-4)         # IAPWS-95 at 25 C, 0.1 MPa
    close(C.water_psat_bar(273.1599), C.water_psat_bar(273.16), 1e-3)  # supercooled branch joins the IAPWS-95 branch
    close(C.water_psat_bar(273.16), 0.00611657, 1e-5)


def test_units():
    close(C.to_bar(1.0, "atm"), 1.01325, 1e-12)
    close(C.to_bar(760.0, "torr"), 1.01325, 1e-6)
    close(C.to_bar(2.5, "MPa"), 25.0, 1e-12)
    close(C.to_K(25.0, "C"), 298.15, 1e-12)
    assert C.parse_float("-.065") == -0.065 and C.parse_float("n.d.") is None and C.parse_float("1.2a") == 1.2
    assert C.parse_scale("x1e-4 (printed x 10^4)") == 1e-4 and C.parse_scale(None) == 1.0
    assert C.unit_scale_from_name("mole_fraction_times_1e4") == 1e-4


def test_composition():
    close(C.molality_from_mass_fraction("NaCl", 0.10), 1000 * 0.1 / (58.4428 * 0.9), 1e-12)
    ions = C.salt_to_ions("CaCl2", 2.0)
    assert ions["m_Ca"] == 2.0 and ions["m_Cl"] == 4.0
    sw = C.seawater_ions(35.16504)
    close(C.SA_from_salinity(35.0), 35.16504, 1e-12)
    close(C.seawater_density_gcm3(288.15, 35.16504), 1.0259764, 1e-6)  # TEOS-10 check value for SA=35.16504, t=15 C
    # reference seawater: chloride 19.35271 g/kg seawater -> mol per kg water
    close(sw["m_Cl"], 19.35271 / 35.453 / (1 - 0.03516504), 1e-9)
    assert all(v == 0 for v in C.seawater_ions(0.0).values())


def test_mixture_mass_fraction():
    # Ahmadi 2018 Table 4 (mass %): NaCl 7.62, CaCl2 0.789, MgCl2 0.0946, KCl 0.0935 -> published molalities of the paper's recipe
    import gbb12_build as B
    rec = {"comp_basis": "mass_percent", "comp": {"NaCl": ("7.62", "%"), "CaCl2": ("0.789", "%"), "MgCl2": ("0.0946", "%"), "KCl": ("0.0935", "%")}}
    ions, _ = B.comp_to_ions(rec, None)
    tot = (7.62 + 0.789 + 0.0946 + 0.0935) / 100
    close(ions["m_Ca"], 1000 * 0.00789 / (110.984 * (1 - tot)), 1e-9)
    close(ions["m_Cl"], (1000 * 0.0762 / 58.4428 + 2 * 1000 * 0.00789 / 110.984 + 2 * 1000 * 0.000946 / 95.211 + 1000 * 0.000935 / 74.5513) / (1 - tot), 1e-9)


def test_gas_solubility():
    x = 2.761e-5
    close(C.x_saltfree_from_molality(C.molality_from_x_saltfree(x)), x, 1e-12)
    # Ostwald coefficient of methane from Serra et al. 2006: L = 0.03674 at 293.15 K, 101.325 kPa gas partial pressure,
    # printed mole fraction 2.761e-5 (independent of this code)
    ps = C.water_psat_bar(293.15)
    m = C.molality_from_ostwald(0.03674, 1.01325, 293.15, 1.01325 + ps)
    close(C.x_saltfree_from_molality(m), 2.761e-5, 5e-3)
    # Bunsen coefficient of oxygen in water at 25 C (0.02831 cm3/cm3/atm) corresponds to about 1.27e-3 mol/kg/atm
    ps = C.water_psat_bar(298.15)
    close(C.molality_from_bunsen(0.02831, 298.15, 1.01325 + ps), 1.267e-3, 5e-3)
    # Henry: x = f/H
    close(C.x_from_henry(1.0, 4.0e4), 2.5e-5, 1e-12)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
