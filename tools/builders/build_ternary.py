#!/usr/bin/env python3
"""Build ``data/ternary.csv`` -- the CO2 + CH4 + water ternary family.

Why this is a separate family
-----------------------------
Every other family in this database describes a system with ONE gas, so the
gas-phase composition is implied and needs no column. A ternary measurement
does not work that way: the same brine at the same (T, P) dissolves different
amounts of CH4 and CO2 depending on how the gas phase is split between them.
That split is an independent state variable, and there is nowhere to put it
in the seven-family schema.

Rather than add a column that would be empty for 11,444 of 11,478 rows, the
ternary data lives here with the standard schema **plus one column**:

    y_co2_dry -- CO2 mole fraction of the gas phase on a water-free basis.

Everything else is unchanged, so ``gbb.load('ternary')`` behaves like any
other family. The ion columns are present and all zero: no ternary
measurement in brine exists (see *Scope* below), and they are carried so that
such data needs no schema change if it ever appears.

Row grammar
-----------
One measured state yields up to three rows, each naming what it measured:

    gas=ch4      property=xc_saltfree   dissolved CH4, salt-free mole fraction
    gas=co2      property=xc_saltfree   dissolved CO2, salt-free mole fraction
    gas=co2-ch4  property=y_h2o         water content of the mixed gas phase

``co2-ch4`` is the only new gas code, and it is used only for the water-content
rows, where the measurement is a property of the mixture rather than of either
component.

Scope -- what does NOT exist
----------------------------
There are no ternary measurements in brine. The CCB tree of the source
materials (``EoS/CH4/CCB/``) holds only ``ELV_CCB_*_ms?m.dat`` solver output
from ``eCPA_ELV.py``; the upstream project's own builder records that "no
embedded experimental dataset exists in the upstream tree". So this family is
pure water only, and its absence of brine rows is a fact about the
literature, not an omission here.

Provenance
----------
All three sources are transcribed from the same upstream compilation,
``source_materials/EoS/CH4/CCW/CPA_ELV_EXP.py``, at the line ranges noted
against each block. Values are reproduced exactly as printed there.

Qin (2008) also reports CH4-H2O *binary* measurements, and those are already
in ``solubility.csv`` / ``y_h2o.csv`` under ``ch4_water_binary``. They are
different measurements, not duplicates: at 375 K / 302 bar the binary gives
x_CH4 = 0.0030, while the ternary at 376 K / 303 bar gives 0.00104-0.00188
depending on the gas split, lower because CO2 displaces CH4.

Usage: python3 tools/builders/build_ternary.py
"""
from __future__ import annotations

import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE.parents[1] / "data"

COLUMNS = ["dataset_id", "source", "gas", "property", "T_K", "P_bar",
           "y_co2_dry", "m_Na", "m_Cl", "m_K", "m_Ca", "m_Mg", "m_SO4",
           "value", "uncertainty", "quality", "tag"]

# --- transcribed data -------------------------------------------------------
# Each "Yc" entry is the list of gas splits measured at that (T, P); the
# x_CH4_aq / x_CO2_aq / y_H2O_gas lists line up with it element by element.
# ``None`` means the author does not report that quantity at all.

DHIMA = {                                    # CPA_ELV_EXP.py lines 280-284
    "source": "DHIMA(1999)",
    "dataset_id": "ternary_ccw_dhima1999",
    "temps": [344],
    "press": [100.0, 200.0, 500.0, 750.0, 1000.0],
    "Yc": [[[0.4330, 0.1955], [0.4300, 0.1898], [0.4150, 0.1795],
            [0.4130, 0.1740], [0.4060]]],
    "x_CH4_aq": [[[0.000776, 0.0011], [0.00131, 0.00182],
                  [0.002434, 0.00319], [0.003027, 0.003893], [0.00361]]],
    "x_CO2_aq": [[[0.008346, 0.003555], [0.0113, 0.00539],
                  [0.01267, 0.006265], [0.014347, 0.007105], [0.015071]]],
    "y_H2O_gas": None,                       # not reported
}

ALGHAFRI = {                                 # CPA_ELV_EXP.py lines 516-525
    "source": "ALGHAFRI(2014)",
    "dataset_id": "ternary_ccw_alghafri2014",
    "temps": [323, 423],
    "press": [20.0, 60.0, 100.0, 140.0, 180.0],
    "Yc": [[[0.4965], [0.5113], [0.5067], [0.4957], [0.5011]],
           [[0.5013], [0.5001], [0.4877], [0.4962], [0.4892]]],
    "x_CH4_aq": [[[0.000320], [0.000707], [0.000989], [0.001303], [0.001512]],
                 [[0.000281], [0.001029], [0.001635], [0.001811], [0.001915]]],
    "x_CO2_aq": [[[0.003121], [0.00851], [0.01159], [0.01310], [0.01420]],
                 [[0.001271], [0.00430], [0.00723], [0.00880], [0.01029]]],
    "y_H2O_gas": [[[0.01267], [0.00378], [0.00411], [0.00487], [0.00556]],
                  [[0.3445], [0.1145], [0.0689], [0.0489], [0.04694]]],
}

QIN = {                                      # CPA_ELV_EXP.py lines 800-803
    "source": "QIN(2008)",
    "dataset_id": "ternary_ccw_qin2008",
    "temps": [376],
    "press": [105.0, 205.0, 303.0, 402.0, 500.0],
    "Yc": [[[0.7436, 0.5765, 0.4450], [0.7402, 0.5248, 0.4252],
            [0.7289, 0.5432, 0.4213], [0.7237, 0.5260, 0.4103],
            [0.7224, 0.5286, 0.4057]]],
    "x_CH4_aq": [[[0.00038, 0.00074, 0.00084], [0.00077, 0.00127, 0.00136],
                  [0.00104, 0.00166, 0.00188], [0.00127, 0.00199, 0.00222],
                  [0.00152, 0.00215, 0.00258]]],
    "x_CO2_aq": [[[0.01065, 0.00855, 0.00627], [0.01524, 0.01186, 0.0094],
                  [0.01801, 0.01369, 0.01074], [0.01882, 0.01414, 0.01172],
                  [0.01971, 0.01549, 0.01179]]],
    "y_H2O_gas": [[[0.0208, 0.01906, 0.01747], [0.02296, 0.01765, 0.01581],
                   [0.02317, 0.01905, 0.01681], [0.0252, 0.01923, 0.01695],
                   [0.02676, 0.02199, 0.01821]]],
}

SOURCES = (DHIMA, ALGHAFRI, QIN)

#: (gas, property) emitted for each measured quantity.
_EMIT = (("x_CH4_aq",  "ch4",     "xc_saltfree"),
         ("x_CO2_aq",  "co2",     "xc_saltfree"),
         ("y_H2O_gas", "co2-ch4", "y_h2o"))


def build_rows() -> list[dict]:
    rows = []
    for blk in SOURCES:
        for iT, T in enumerate(blk["temps"]):
            for iP, P in enumerate(blk["press"]):
                splits = blk["Yc"][iT][iP]
                for k, yc in enumerate(splits):
                    for field, gas, prop in _EMIT:
                        table = blk[field]
                        if table is None:
                            continue
                        val = table[iT][iP][k]
                        rows.append({
                            "dataset_id": blk["dataset_id"],
                            "source": blk["source"],
                            "gas": gas,
                            "property": prop,
                            "T_K": float(T),
                            "P_bar": float(P),
                            "y_co2_dry": float(yc),
                            "m_Na": 0.0, "m_Cl": 0.0, "m_K": 0.0,
                            "m_Ca": 0.0, "m_Mg": 0.0, "m_SO4": 0.0,
                            "value": float(val),
                            "uncertainty": "",      # not stated upstream
                            # Single-lab measurements. The three sources sit at
                            # different temperatures (344 / 323+423 / 376 K), so
                            # no two of them describe the same state and the
                            # cross-source agreement rule that awards R can
                            # never fire here.
                            "quality": "T",
                            # Never a fit target of any lineage: the ternary
                            # set has only ever been used to validate the
                            # mixed-gas capability.
                            "tag": "test-only",
                        })
    return rows


def main() -> int:
    rows = build_rows()
    out = DATA_DIR / "ternary.csv"
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    states = {(r["source"], r["T_K"], r["P_bar"], r["y_co2_dry"]) for r in rows}
    print(f"ternary.csv      {len(rows)} rows from {len(states)} measured states")
    for blk in SOURCES:
        n = sum(1 for r in rows if r["source"] == blk["source"])
        ns = len({(r["T_K"], r["P_bar"], r["y_co2_dry"])
                  for r in rows if r["source"] == blk["source"]})
        print(f"    {blk['source']:20s} {n:3d} rows / {ns:2d} states")
    print(f"  -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
