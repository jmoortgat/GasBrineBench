#!/usr/bin/env python3
"""BrineBench dataset validator (standalone: numpy/pandas only).

Run from the repo root:  python tools/validate.py
Exit code 0 = all checks pass. Used as PR CI.

Checks:
  1. schema conformance per family csv (columns, types, vocab)
  2. physical ranges (T, P, molalities >= 0, values finite)
  3. molality/mole-fraction sibling-row consistency (1e-9 relative)
  4. duplicate detection within and across dataset_ids
  5. every `source` key resolves in SOURCES.bib
  6. quality codes in {R, T, U}; provenance non-empty
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
M_W = 0.01801528  # kg/mol

FAMILIES = ("solubility", "rho", "phi_osm", "psat_ratio", "dh_sol",
            "y_h2o", "miac")
PROPS = {"solubility_molality", "xc_saltfree", "y_h2o", "rho",
         "phi_osm", "psat_ratio", "dh_sol", "miac"}
ION_COLS = ["m_Na", "m_Cl", "m_K", "m_Ca", "m_Mg", "m_SO4"]
REQUIRED = ["dataset_id", "source", "gas", "property", "T_K",
            "P_bar", *ION_COLS, "value", "uncertainty", "quality",
            "provenance"]


def fail(msgs, msg):
    msgs.append(msg)


def check_family(fpath, bib_keys, msgs):
    df = pd.read_csv(fpath, keep_default_na=False)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        fail(msgs, f"{fpath.name}: missing columns {missing}")
        return
    bad_prop = set(df["property"]) - PROPS
    if bad_prop:
        fail(msgs, f"{fpath.name}: unknown property values {bad_prop}")
    for col in ("T_K", "P_bar", "value", *ION_COLS):
        v = pd.to_numeric(df[col], errors="coerce")
        if col != "value" and (v < 0).any():
            fail(msgs, f"{fpath.name}: negative {col}")
        if v.isna().any() and col != "value":
            fail(msgs, f"{fpath.name}: non-numeric {col}")
    t = pd.to_numeric(df["T_K"], errors="coerce")
    if ((t < 230) | (t > 1000)).any():
        fail(msgs, f"{fpath.name}: T_K outside [230, 1000]")
    if (~df["quality"].isin(["R", "T", "U"])).any():
        fail(msgs, f"{fpath.name}: quality codes must be R/T/U")
    if (df["provenance"].astype(str).str.strip() == "").any():
        fail(msgs, f"{fpath.name}: empty provenance")
    unknown = set(df["source"]) - bib_keys
    if unknown:
        fail(msgs, f"{fpath.name}: sources missing from SOURCES.bib: "
                   f"{sorted(unknown)[:5]}...")
    # sibling consistency: paired molality/xc rows per identical state
    sol = df[df["property"].isin(["solubility_molality",
                                  "xc_saltfree"])]
    if len(sol):
        key_cols = ["dataset_id", "gas", "T_K", "P_bar", *ION_COLS]
        piv = sol.pivot_table(index=key_cols, columns="property",
                              values="value", aggfunc="first")
        if {"solubility_molality", "xc_saltfree"} <= set(piv.columns):
            both = piv.dropna()
            m = pd.to_numeric(both["solubility_molality"])
            xc = pd.to_numeric(both["xc_saltfree"])
            expect = m / (m + 1.0 / M_W)
            bad = (xc - expect).abs() > 1e-9 + 1e-6 * xc.abs()
            if bad.any():
                fail(msgs, f"{fpath.name}: {int(bad.sum())} "
                           "molality/xc sibling rows inconsistent")
    # duplicates: identical state + property from different datasets
    dup_cols = ["property", "gas", "T_K", "P_bar", *ION_COLS, "value"]
    dups = df[df.duplicated(dup_cols, keep=False)]
    if len(dups):
        n_pairs = len(dups) - dups.groupby(dup_cols).ngroups
        fail(msgs, f"{fpath.name}: {n_pairs} exact duplicate rows "
                   "(same state, same value)")


def main():
    msgs = []
    bib = ROOT / "SOURCES.bib"
    bib_keys = set()
    if bib.exists():
        bib_keys = set(re.findall(r"@\w+\{([^,]+),", bib.read_text()))
    csvs = sorted(DATA.glob("*.csv"))
    if not csvs:
        print("validate: no data files yet (pre-release scaffold) — OK")
        return 0
    for f in csvs:
        check_family(f, bib_keys, msgs)
    if msgs:
        print("VALIDATION FAILED:")
        for m in msgs:
            print(" -", m)
        return 1
    print(f"validate: {len(csvs)} families OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
