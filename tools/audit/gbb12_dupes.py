"""Find new rows that repeat rows already in v1.1.1 (same property, gas, T within 0.5 K, P within 0.5 %, ions within 1 %, value within a tolerance).
Usage: python3 gbb12_dupes.py --old DIR --new new_rows.csv [--tol 0.002]"""
import argparse, glob, os
import numpy as np
import pandas as pd
ION = ["m_Na", "m_Cl", "m_K", "m_Ca", "m_Mg", "m_SO4"]
ap = argparse.ArgumentParser(); ap.add_argument("--old", required=True); ap.add_argument("--new", required=True); ap.add_argument("--tol", type=float, default=0.002)
a = ap.parse_args()
old = pd.concat([pd.read_csv(f) for f in glob.glob(os.path.join(a.old, "*.csv")) if os.path.basename(f) not in ("QUALITY.csv",)], ignore_index=True)
new = pd.read_csv(a.new)
res = []
for prop, g in new.groupby("property"):
    o = old[old["property"] == prop]
    if o.empty: continue
    oT, oP, oV = o["T_K"].to_numpy(float), o["P_bar"].to_numpy(float), o["value"].to_numpy(float)
    oM = o[ION].to_numpy(float); og = o["gas"].fillna("").to_numpy(str)
    for i, r in g.iterrows():
        m = (og == str(r["gas"]) if pd.notna(r["gas"]) else og == "") & (np.abs(oT - r["T_K"]) <= 0.5)
        if pd.notna(r["P_bar"]): m &= np.abs(oP - r["P_bar"]) <= 0.005 * np.maximum(np.abs(oP), abs(r["P_bar"]))
        m &= (np.abs(oM - r[ION].to_numpy(float)) <= 0.01 * np.maximum(np.abs(oM), np.abs(r[ION].to_numpy(float)).max()) + 1e-9).all(axis=1)
        m &= np.abs(oV - r["value"]) <= a.tol * np.maximum(np.abs(oV), abs(r["value"]))
        if m.any():
            j = o.index[np.nonzero(m)[0][0]]
            res.append((r["dataset_id"], o.loc[j, "source"], r["property"], r["gas"], r["T_K"], r["P_bar"], r["value"]))
df = pd.DataFrame(res, columns=["new_dataset", "old_source", "property", "gas", "T_K", "P_bar", "value"])
print(len(df), "new rows repeat an old row")
print(df.groupby(["new_dataset", "old_source"]).size().to_string())
