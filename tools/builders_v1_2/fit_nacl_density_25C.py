"""Fit the apparent molar volume of NaCl(aq) at 298.15 K and 1 atm used by gbb12_core.NACL_VPHI_25C.

Data: every NaCl-only row of data/rho.csv at |T - 298.15| < 0.02 K and P < 2 bar (GasBrineBench v1.2.1: GATES(1985), ROMANKIW(1983),
SURDO(1982), ZEZIN(2014), 41 rows, 0.058-6.1 mol/kg). Model: V_phi = a + b m^0.5 + c m + d m^1.5 (cm3/mol), water density IAPWS-95 at
298.15 K and 1.01325 bar. Prints the coefficients and the residuals; the coefficients in gbb12_core must equal the printed ones.

Usage: python3 fit_nacl_density_25C.py --repo /path/to/GasBrineBench
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gbb12_core as C  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--repo", required=True)
a = ap.parse_args()
d = pd.read_csv(os.path.join(a.repo, "data", "rho.csv"), low_memory=False)
others = ["m_K", "m_Ca", "m_Mg", "m_SO4"]
s = d[(d.m_Na > 0) & (d[others].fillna(0).sum(axis=1) == 0) & ((d.T_K - 298.15).abs() < 0.02) & (d.P_bar < 2)].copy()
M = C.SALT["NaCl"][0]
rw = C.water_rho_kgm3(298.15, 1.01325)
m, rho = s.m_Na.to_numpy(float), s.value.to_numpy(float)
vphi = ((1000.0 + m * M) / rho - 1000.0 / rw) * 1000.0 / m
X = np.c_[np.ones_like(m), np.sqrt(m), m, m ** 1.5]
coef, *_ = np.linalg.lstsq(X, vphi, rcond=None)
pred = (1000.0 + m * M) / (1000.0 / rw + m * (X @ coef) / 1000.0)
res = (rho / pred - 1.0) * 100.0
print(f"{len(s)} rows from {s.source.nunique()} sources: {sorted(s.source.unique())}")
print("coefficients a, b, c, d:", ", ".join(f"{c:.8f}" for c in coef))
print(f"rms deviation {np.sqrt(np.mean(res ** 2)):.4f} %, largest {np.abs(res).max():.4f} %")
print("gbb12_core.NACL_VPHI_25C:", C.NACL_VPHI_25C)
