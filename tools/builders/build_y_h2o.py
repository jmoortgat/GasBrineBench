#!/usr/bin/env python3
"""Build y_h2o.csv: gas-phase water content of the CO2-H2O and
CH4-H2O binaries (benchmark database v0.1 addition) PLUS the first
BRINE water-content family (Hou 2013b NaCl/KCl ternaries).

Source (converted, not re-curated -- same discipline as the Part A
blocks of build_v0.py):

    Multi_Salt/code/data/binaries_co2_water.parquet   452 y_H2O rows
    Multi_Salt/code/data/binaries_ch4_water.parquet   196 y_H2O rows

Those parquets are built by Multi_Salt/code/scripts/build_binaries.py
from the raw per-isotherm text tables
    source_materials/EoS/CO2/CPA/SRK/T{T}K/EXP{k}_T{T}K.txt
    source_materials/EoS/CH4/CH4-Water/{T}K/EXP{k}_T{T}K.txt
(one literature author per file, header ``P [bar]  xc_W  yw_C``).
Spot-verified against the raw files: Valtz 278 K / 5.01 bar /
y = 0.0015; Todheide 623 K / 200 bar / y = 0.945; Olds 511 K /
53.2 bar / y = 0.65459.

Provenance caveat carried into the quality codes: for CO2 the
column ``col3_orig`` distinguishes directly-measured water content
(``yw_C``) from files that printed the CO2 gas fraction (``yc_C``),
where the builder stored y_H2O = 1 - y_CO2 (exact in a binary, but
the subtraction destroys relative precision when y_H2O is small).
All CH4 rows are direct yw measurements.

Quality codes (R/T/U per Yang et al. 2022 IECR 61:15576 Sec 5.2):
    T  default (single-lab measurement)
    U  complement-derived (col3_orig == 'yc_C') rows with
       y_H2O < 0.01: the printed y_CO2 loses >= 99% of its digit
       budget in 1 - y_CO2, so the value's precision is unverifiable
    R  cross-source agreement: two rows from DIFFERENT authors, same
       gas, |dT| <= 2 K, |dP|/P <= 2 %, |dy|/y <= 10 % -> both
       upgraded (never applied to U rows)

Tag: fit-eligible (binaries).  These binary VLE tables are the data
the gas-water interaction parameters of the Multi_Salt eCPA lineage
were originally tuned/validated against (they live inside the legacy
eCPA fitting tree), so they are NOT an independent test for
ecpa_ours / ecpa_paperII; competitor models never saw them per se,
but several (SW, m-SW) fitted their own kij to overlapping
literature data.

Brine y_H2O (the salinity axis; v0.2 addition): Hou, Maitland &
Trusler 2013b, JSCF 78:78-88, Tables 2 (NaCl) and 3 (KCl) --
36 + 36 points at m = 2.5 / 4.0 mol/kg, T = 323.15 / 373.15 /
423.15 K, p to 18.2 MPa, transcribed per point (with the printed
standard deviations) in bench/data/hou2013.py and stored as
y_H2O = 1 - y1(CO2) with dataset_ids yh2o_co2_{nacl,kcl}_hou2013,
source HOU(2013b), quality T, tag test-only (published after every
fit lineage here; never a fit target).  These rows are complement-
derived like the U-coded binary rows, but their precision IS stated
(per-point sd of y1), so the U rule below is NOT applied to them.
The Multi_Salt tree itself still has no brine y_H2O
(ccb_ternary.parquet is an empty schema placeholder).

2026-09 acquisition batch (v0.3): eleven new datasets transcribed in
bench/data/yh2o_sources_2026.py (Tabasinejad 2011 CH4/N2/CO2,
Mohammadi 2005 N2, Mohammadi 2004 CH4/C2H6, Song & Kobayashi 1994
C2H6/C3H8 G-Lw rows, Jooss 2026 CO2 binary + CO2/NaCl brine,
Torres 2026 H2 VLE rows).  All salt-free except the Jooss NaCl set;
quality T, tag test-only (none was ever a fit target of any lineage
in this benchmark).  New gas codes: n2, c2h6, c3h8 (h2 existed).
See the transcription module for per-source provenance, uncertainty
conventions and deliberately skipped blocks.

Review-based quality verdicts (v0.3, applied by
_apply_review_verdicts below; ledger: QUALITY.md Sec. 6):

* Torres et al. 2025 (FPE 589:114259) Sec. 2.3 + Table 6: the Meyer
  & Harvey NIST gravimetric-hygrometer CO2 data (source 'Meyer')
  carry a systematic-deviation budget of 0.3 %, "significantly
  smaller than in any previous work", and agree with the independent
  Bamberger gravimetric set within 2-6 % at matched (T, P)
  -> all Meyer rows upgraded T -> R.
* Torres et al. 2025 Table 4: the two high-pressure low-content
  CHAPOY(2003) CH4 points at 283.08 K / 60.3 bar and 298.11 K /
  63.9 bar are contradicted ~2x by independent-technique
  measurements (Folas 2007 Karl-Fischer 240 vs 108 ppm; Barbalho
  2024 QCM 964 vs 484 ppm) -> those two rows T -> U (unverifiable);
  the review's low-pressure GC-consistency finding supports the rest.
* Jooss et al. 2026 (FPE 599:114516) Sec. 4.2 + Fig. 10: the Hou
  2013b NaCl-brine water contents at 50 C sit far below the Jooss
  measurements at matched salinity, with relative water-content
  reductions "above 30 %, far above our upper bound of 14.7 %";
  Jooss: the Hou brine data "may have unreported systematic errors"
  -> the 12 yh2o_co2_nacl_hou2013 rows at 323.15 K T -> U.  (The
  373/423 K NaCl rows and the KCl table have no independent
  counterpart yet; kept T with a ledger note.)

Run:
    PYTHONPATH=<repo>/code python3 bench/data/build_y_h2o.py
(defaults to the sibling Multi_Salt checkout; override with env
ECPA_MS_CODE).  Deterministic output: rows sorted by (dataset_id,
source, T_K, P_bar, value).
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent          # .../code/bench/data
CODE = HERE.parents[1]                          # .../code
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

# Curation artefacts held in a maintainer-local sibling checkout. Not part of
# this repository; the original default was an absolute path on the build
# machine and has been replaced by the environment variable it always honoured.
MS_CODE = Path(os.environ.get("ECPA_MS_CODE", "Multi_Salt/code"))

from bench.core.conventions import mi_from_salt      # noqa: E402
from bench.data import hou2013                       # noqa: E402
from bench.data import yh2o_sources_2026             # noqa: E402

COLUMNS = ["dataset_id", "source", "gas", "property", "T_K", "P_bar",
           "m_Na", "m_Cl", "m_K", "m_Ca", "m_Mg", "m_SO4",
           "value", "uncertainty", "quality", "tag"]
ION_COLS = ["m_Na", "m_Cl", "m_K", "m_Ca", "m_Mg", "m_SO4"]


def _load(gas):
    fname = {"co2": "binaries_co2_water.parquet",
             "ch4": "binaries_ch4_water.parquet"}[gas]
    df = pd.read_parquet(MS_CODE / "data" / fname)
    df = df[df["y_H2O_gas_exp"].notna()].copy()
    n0 = len(df)
    df = df[(df["y_H2O_gas_exp"] > 0.0) & (df["y_H2O_gas_exp"] < 1.0)
            & np.isfinite(df["T_K"]) & np.isfinite(df["P_bar"])
            & (df["P_bar"] > 0.0)]
    if len(df) != n0:
        print(f"  {gas}: dropped {n0 - len(df)} out-of-range rows")
    df["gas"] = gas
    df["dataset_id"] = f"yh2o_{gas}_binary"
    if "col3_orig" not in df.columns:      # CH4 parquet: all direct
        df["col3_orig"] = "yw_C"
    return df


def _quality(df):
    """Vector of R/T/U codes per the module-docstring rules."""
    q = np.array(["T"] * len(df), dtype=object)
    # U: complement-derived with y < 0.01
    u_mask = ((df["col3_orig"].values == "yc_C")
              & (df["y_H2O_gas_exp"].values < 0.01))
    q[u_mask] = "U"
    # R: cross-author agreement (O(n^2) within gas -- n <= 452, fine)
    T = df["T_K"].values.astype(float)
    P = df["P_bar"].values.astype(float)
    y = df["y_H2O_gas_exp"].values.astype(float)
    au = df["author"].values
    gas = df["gas"].values
    n = len(df)
    for i in range(n):
        if q[i] == "U":
            continue
        for j in range(i + 1, n):
            if q[j] == "U" or gas[i] != gas[j] or au[i] == au[j]:
                continue
            if (abs(T[i] - T[j]) <= 2.0
                    and abs(P[i] - P[j]) <= 0.02 * max(P[i], P[j])
                    and abs(y[i] - y[j]) <= 0.10 * max(y[i], y[j])):
                q[i] = q[j] = "R"
    return q


def _hou2013_frame():
    """Brine y_H2O rows from the Hou 2013b transcription module
    (see hou2013.py for provenance, basis and uncertainty notes)."""
    recs = []
    for did, salt, m, T, P_bar, y, u in hou2013.y_h2o_points():
        rec = {"dataset_id": did, "source": hou2013.Y_SOURCE,
               "gas": "co2", "property": "y_h2o", "T_K": T,
               "P_bar": P_bar, "value": y, "uncertainty": u,
               "quality": "T", "tag": "test-only"}
        for c, v in zip(ION_COLS, mi_from_salt(salt, m)):
            rec[c] = float(v)
        recs.append(rec)
    df = pd.DataFrame(recs)[COLUMNS]
    print(f"  hou2013 brine: {len(df)} rows  T {df.T_K.min():g}-"
          f"{df.T_K.max():g} K  P {df.P_bar.min():g}-"
          f"{df.P_bar.max():g} bar  y {df.value.min():g}-"
          f"{df.value.max():g}")
    return df


def _sources_2026_frame():
    """The 2026-09 acquisition batch (see yh2o_sources_2026.py for
    provenance, uncertainty conventions and skipped blocks)."""
    recs = []
    for did, T, P_bar, y, u, m_nacl in yh2o_sources_2026.points():
        src, gas = yh2o_sources_2026.DATASETS[did]
        rec = {"dataset_id": did, "source": src, "gas": gas,
               "property": "y_h2o", "T_K": T, "P_bar": P_bar,
               "value": y, "uncertainty": u, "quality": "T",
               "tag": "test-only"}
        for c, v in zip(ION_COLS, mi_from_salt("NaCl", m_nacl)):
            rec[c] = float(v)
        recs.append(rec)
    df = pd.DataFrame(recs)[COLUMNS]
    for did, grp in df.groupby("dataset_id"):
        print(f"  {did}: {len(grp)} rows  T {grp.T_K.min():g}-"
              f"{grp.T_K.max():g} K  P {grp.P_bar.min():g}-"
              f"{grp.P_bar.max():g} bar  y {grp.value.min():g}-"
              f"{grp.value.max():g}")
    return df


def _apply_review_verdicts(df):
    """Torres-2025 / Jooss-2026 review-based quality codes (module
    docstring + QUALITY.md Sec. 6).  Operates on the concatenated
    frame; every change is counted and printed."""
    # 1. Meyer & Harvey CO2 rows -> R (Torres 2025 Sec 2.3 + Table 6)
    m = (df.dataset_id == "yh2o_co2_binary") & (df.source == "Meyer")
    n_meyer = int((df.loc[m, "quality"] != "R").sum())
    df.loc[m, "quality"] = "R"
    # 2. CHAPOY(2003) high-P low-y CH4 points -> U (Torres 2025 T4)
    ch = ((df.dataset_id == "yh2o_ch4_binary")
          & (df.source == "CHAPOY(2003)")
          & (((np.abs(df.T_K - 283.0) < 0.5)
              & (np.abs(df.P_bar - 60.30) < 0.5))
             | ((np.abs(df.T_K - 298.0) < 0.5)
                & (np.abs(df.P_bar - 63.9) < 0.5))))
    n_chapoy = int(ch.sum())
    assert n_chapoy == 2, f"expected the 2 flagged Chapoy rows, got {n_chapoy}"
    df.loc[ch, "quality"] = "U"
    # 3. Hou 2013b NaCl brine rows at 323.15 K -> U (Jooss 2026)
    hb = ((df.dataset_id == "yh2o_co2_nacl_hou2013")
          & (np.abs(df.T_K - 323.15) < 1e-6))
    n_hou = int(hb.sum())
    assert n_hou == 12, f"expected 12 Hou NaCl 323 K rows, got {n_hou}"
    df.loc[hb, "quality"] = "U"
    print(f"  review verdicts: Meyer T->R {n_meyer}, "
          f"Chapoy(2003) T->U {n_chapoy}, Hou2013b-NaCl-323K T->U {n_hou}")
    return df


def main():
    frames = []
    for gas in ("co2", "ch4"):
        df = _load(gas)
        df["quality"] = _quality(df)
        out = pd.DataFrame({
            "dataset_id": df["dataset_id"],
            "source": df["author"],
            "gas": df["gas"],
            "property": "y_h2o",
            "T_K": df["T_K"].astype(float),
            "P_bar": df["P_bar"].astype(float),
            "value": df["y_H2O_gas_exp"].astype(float),
            "uncertainty": np.nan,          # not stated in the tables
            "quality": df["quality"],
            "tag": "fit-eligible",
        })
        for c in ION_COLS:
            out[c] = 0.0
        frames.append(out[COLUMNS])
        nq = out.quality.value_counts().to_dict()
        print(f"  {gas}: {len(out)} rows  T {out.T_K.min():g}-"
              f"{out.T_K.max():g} K  P {out.P_bar.min():g}-"
              f"{out.P_bar.max():g} bar  quality {nq}")
    frames.append(_hou2013_frame())
    frames.append(_sources_2026_frame())
    allrows = pd.concat(frames, ignore_index=True)
    allrows = _apply_review_verdicts(allrows)
    allrows = allrows.sort_values(
        ["dataset_id", "source", "T_K", "P_bar", "value"],
        kind="mergesort").reset_index(drop=True)
    allrows.to_csv(HERE / "y_h2o.csv", index=False, float_format="%.10g")
    print(f"y_h2o.csv        {len(allrows):5d} rows")


if __name__ == "__main__":
    main()
