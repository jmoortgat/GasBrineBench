"""Standalone cross-source quality coding (R / T / U) following the rules of GasBrineBench v1.1.1 (data/QUALITY.md, Yang et al. 2022 Sec. 5.2).

Rules (solubility rows only; `solubility_molality` rows decide, the `xc_saltfree` sibling of each point follows):
  clusters: union-find over pairs of points from DIFFERENT sources with the same gas, |dT| <= 1.0 K, |dP| <= 2 % (relative), every ion molality within 2 %;
  R (upgrade): a cluster with >= 2 distinct sources whose relative span (max - min) / median of the values is <= 5 % -> all its rows get R;
  U (downgrade): in a cluster with >= 3 distinct sources, a source whose deviation from the cluster median exceeds max(3 x cluster spread, 5 %);
                 a source flagged in >= 3 such clusters gets those rows downgraded to U.
Rows keep their incoming code (T by default, U when the mapping says so) unless a rule applies; U assigned by authors/mappings is never upgraded.

Usage: python3 gbb12_quality.py --old DIR_WITH_v1.1.1_CSVS --new new_rows.csv --out DIR
  --validate-old   run the rules on the old rows only (starting from quality T everywhere) and compare with the codes stored in v1.1.1
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd

ION = ["m_Na", "m_Cl", "m_K", "m_Ca", "m_Mg", "m_SO4"]


def find(parent, i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


def cluster_points(pts):
    """pts: DataFrame of molality rows with columns source, gas, T_K, P_bar, ions. Returns cluster label array (int)."""
    n = len(pts)
    parent = list(range(n))
    T = pts["T_K"].to_numpy(float)
    P = pts["P_bar"].to_numpy(float)
    M = pts[ION].to_numpy(float)
    src = pts["source"].to_numpy(str)
    gas = pts["gas"].to_numpy(str)
    for i in range(n):
        cand = np.nonzero((gas == gas[i]) & (np.abs(T - T[i]) <= 1.0) & (src != src[i]))[0]
        cand = cand[cand > i]
        if cand.size == 0:
            continue
        pm = np.maximum(np.abs(P[cand]), np.abs(P[i]))
        okP = np.abs(P[cand] - P[i]) <= 0.02 * np.where(pm > 0, pm, 1)
        mm = np.maximum(np.abs(M[cand]), np.abs(M[i]))
        okM = (np.abs(M[cand] - M[i]) <= 0.02 * np.where(mm > 0, mm, 1)).all(axis=1)
        for j in cand[okP & okM]:
            a, b = find(parent, i), find(parent, int(j))
            if a != b:
                parent[a] = b
    return np.array([find(parent, i) for i in range(n)])


def apply_rules(df):
    """df: solubility rows (both properties). Returns (new quality Series, report dict)."""
    q = df["quality"].copy()
    mol = df[df["property"] == "solubility_molality"].copy()
    mol = mol.dropna(subset=["T_K", "P_bar"])
    mol["lab"] = cluster_points(mol)
    key = ["dataset_id", "gas", "T_K", "P_bar"] + ION
    upgrade_idx, flagged = [], {}
    clusters = 0
    for lab, g in mol.groupby("lab"):
        srcs = g["source"].nunique()
        if srcs < 2:
            continue
        clusters += 1
        v = g["value"].to_numpy(float)
        med = np.median(v)
        if med <= 0:
            continue
        span = (v.max() - v.min()) / med
        if span <= 0.05:
            upgrade_idx.extend(g.index)
        elif srcs >= 3:
            dev = g.assign(dev=np.abs(g["value"] - med) / med).groupby("source")["dev"].max()
            for s, d in dev.items():
                if d > max(3 * span, 0.05):
                    flagged.setdefault(s, []).append(list(g.index))
    down_idx = []
    for s, lst in flagged.items():
        if len(lst) >= 3:
            for idxs in lst:
                down_idx.extend(i for i in idxs if mol.loc[i, "source"] == s)
    # siblings (xc_saltfree rows of the same point) follow
    sib = df.copy()
    sib["kp"] = list(zip(*[sib[c] for c in key]))
    kp_mol = {tuple(r): i for i, r in zip(mol.index, zip(*[mol[c] for c in key]))}

    def expand(idx):
        keys = {tuple(df.loc[i, key]) for i in idx}
        return sib.index[sib["kp"].isin(keys)]

    up = expand(upgrade_idx)
    dn = expand(down_idx)
    q.loc[up] = np.where(q.loc[up] == "U", "U", "R")
    q.loc[dn] = "U"
    return q, {"clusters_ge2_sources": clusters, "rows_R": int((q.loc[up] == "R").sum()), "rows_U": int(len(dn)), "sources_flagged": {s: len(l) for s, l in flagged.items()}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True)
    ap.add_argument("--new")
    ap.add_argument("--out")
    ap.add_argument("--validate-old", action="store_true")
    a = ap.parse_args()
    old = pd.read_csv(os.path.join(a.old, "solubility.csv"))
    if a.validate_old:
        base = old.copy()
        base["quality"] = np.where(old["quality"] == "U", "U", "T")  # remove the cross-source R, keep the author-flag U
        q, rep = apply_rules(base)
        same = (q == old["quality"]).mean()
        print("old rows:", len(old), "stored R:", int((old.quality == "R").sum()), "recomputed R:", int((q == "R").sum()),
              "stored U:", int((old.quality == "U").sum()), "recomputed U:", int((q == "U").sum()), "agreement:", round(float(same), 4))
        diff = old[q != old["quality"]]
        print("rows with different code:", len(diff))
        print(diff.groupby(["source", "quality"]).size().head(20))
        print(rep)
        return
    new = pd.read_csv(a.new)
    new_sol = new[new["family"] == "solubility"].drop(columns=[c for c in new.columns if c not in old.columns])
    comb = pd.concat([old.assign(_new=False), new_sol.assign(_new=True)], ignore_index=True)
    base = comb.copy()
    base["quality"] = np.where(comb["quality"] == "U", "U", "T")
    q, rep = apply_rules(base)
    # new rows keep a stronger code only through the rules; old rows: report changes
    changed_old = comb[(~comb["_new"]) & (q != comb["quality"])]
    print(rep)
    print("old rows whose code changes:", len(changed_old))
    print(changed_old.groupby(["source", "quality"]).size().head(30))
    comb["quality_new"] = q
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        comb.to_csv(os.path.join(a.out, "solubility_quality_coded.csv"), index=False)


if __name__ == "__main__":
    sys.exit(main())
