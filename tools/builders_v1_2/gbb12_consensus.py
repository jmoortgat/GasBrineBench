"""Inter-source consensus statistic for GasBrineBench.

For every benchmark row that other, independent sources also measured at about the same conditions, compare it with them.

Definition (leave-one-source-out, no transitive chaining):
  neighbours of row i = rows of the same family, property and gas, from a different source (canonical citation id of
      tools/make_sources.py), with |dT| <= TOL_T K, |dP| <= TOL_P (relative; ignored if either pressure is blank), and every ion
      molality within TOL_M (relative, plus 1e-9). Gas-loaded families also match m_gas within TOL_M.
  per-source value = median of that source's neighbour rows (a source with many neighbouring rows counts once);
  reference_i = median of the per-source values over the n_other independent neighbour sources;
  rel_dev_i = (value_i - reference_i) / |reference_i|  (abs_dev_i = value_i - reference_i, used where the reference is ~0);
  spread_i = (max - min) / |reference_i| of the per-source values (0 with one other source).
mean_other and sd_other (n_other >= 2) are the mean and sample standard deviation of the same per-source values.
A row with no neighbour gets no statistic (n_other = 0).

Per source and property group: n_rows, n_compared, median signed rel_dev (bias), robust scale 1.4826 x MAD of rel_dev, and
the share of compared rows beyond 3 x the property's pooled robust scale (outlier share). Rows with n_other >= 2 whose |rel_dev|
exceeds max(3 x pooled scale, MIN_OUTLIER) are listed as `consensus_outlier`; with one other source the disagreement cannot be
attributed to either side and the row is not listed.

Rows coded quality U are compared with their neighbours but are never used as neighbours; a smooth prediction outside
[min/2, 2 max] of its neighbouring values is discarded.

Limits, stated in the output header: sources are citation ids, not laboratories (two papers of one lab count as two sources);
tolerances put a floor under the resolution (a few per cent for solubility, whose value changes by 1-2 % per K); the statistic is
descriptive and changes no quality code.

Usage: python3 gbb12_consensus.py --repo PATH_TO_GasBrineBench --out DIR [--tol-t 1.0 --tol-p 0.02 --tol-m 0.02]
"""
from __future__ import annotations

import argparse
import os
import sys
import importlib.util

import numpy as np
import pandas as pd

ION = ["m_Na", "m_Cl", "m_K", "m_Ca", "m_Mg", "m_SO4"]
MIN_OUTLIER = 0.10
# (family, property) groups that take part; gas-loaded densities and viscosities of gas-loaded solutions are too sparse
GROUPS = [("solubility", "solubility_molality"), ("y_h2o", "y_h2o"), ("rho", "rho"), ("phi_osm", "phi_osm"),
          ("psat_ratio", "psat_ratio"), ("thermo_brine", "Cp_app"), ("dh_sol", "dh_sol"), ("visc", "visc"), ("rho_gas", "rho_gas_loaded")]


def load_ms(repo):
    spec = importlib.util.spec_from_file_location("ms", os.path.join(repo, "tools", "make_sources.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def neighbours_stats(df, tol_t, tol_p, tol_m):
    """df: rows of one (family, property, gas) group with columns src, T_K, P_bar, ions, value, m_gas. Returns arrays."""
    n = len(df)
    T = df["T_K"].to_numpy(float)
    P = df["P_bar"].to_numpy(float)
    M = df[ION].to_numpy(float)
    V = df["value"].to_numpy(float)
    G = df["m_gas"].to_numpy(float) if "m_gas" in df.columns else np.full(n, np.nan)
    src = df["src"].to_numpy(str)
    pool = (df["quality"].to_numpy(str) != "U")   # rows coded U are compared but never serve as a reference
    ref = np.full(n, np.nan)
    nother = np.zeros(n, int)
    spread = np.full(n, np.nan)
    mean_o = np.full(n, np.nan)
    sd_o = np.full(n, np.nan)
    for i in range(n):
        m = (np.abs(T - T[i]) <= tol_t) & (src != src[i]) & pool
        if not m.any():
            continue
        if not np.isnan(P[i]):
            pm = np.maximum(np.abs(P), abs(P[i]))
            okP = np.isnan(P) | (np.abs(P - P[i]) <= tol_p * np.where(pm > 0, pm, 1))
            m &= okP
        if not m.any():
            continue
        mm = np.maximum(np.abs(M), np.abs(M[i]))
        m &= (np.abs(M - M[i]) <= tol_m * np.where(mm > 0, mm, 1) + 1e-9).all(axis=1)
        if not np.isnan(G[i]):
            gm = np.maximum(np.abs(G), abs(G[i]))
            m &= np.isnan(G) | (np.abs(G - G[i]) <= tol_m * np.where(gm > 0, gm, 1) + 1e-9)
        idx = np.nonzero(m)[0]
        if idx.size == 0:
            continue
        per_src = pd.Series(V[idx]).groupby(src[idx]).median()
        nother[i] = len(per_src)
        r = float(np.median(per_src.to_numpy()))
        ref[i] = r
        mean_o[i] = float(per_src.mean())
        sd_o[i] = float(per_src.std(ddof=1)) if len(per_src) > 1 else np.nan
        if abs(r) > 0:
            spread[i] = (per_src.max() - per_src.min()) / abs(r)
    return ref, nother, spread, mean_o, sd_o


W_T, W_LNP, W_M = 10.0, 0.35, 0.20   # window half-widths: K, ln P, relative ion molality (+0.05 mol/kg)


def smooth_stats(df):
    """Leave-one-source-out local-linear prediction from the OTHER sources only (interpolation, never extrapolation).
    Features: T, ln P (when pressures exist), every ion molality that varies in the window. Response: ln(value) when all
    values in the group are positive, else value. Tricube weights on the largest normalised distance."""
    n = len(df)
    T = df["T_K"].to_numpy(float)
    P = df["P_bar"].to_numpy(float)
    lnP = np.log(np.where(P > 0, P, np.nan))
    M = df[ION].to_numpy(float)
    V = df["value"].to_numpy(float)
    src = df["src"].to_numpy(str)
    pool = (df["quality"].to_numpy(str) != "U")
    use_log = bool((V > 0).all())
    Y = np.log(V) if use_log else V
    pred = np.full(n, np.nan)
    nsrc = np.zeros(n, int)
    npts = np.zeros(n, int)
    for i in range(n):
        m = (np.abs(T - T[i]) <= W_T) & (src != src[i]) & pool
        if m.sum() < 3:
            continue
        if not np.isnan(lnP[i]):
            m &= np.isnan(lnP) | (np.abs(lnP - lnP[i]) <= W_LNP)
        tol = W_M * np.maximum(np.abs(M), np.abs(M[i])) + 0.05 * (np.abs(M[i]) > 0)
        m &= (np.abs(M - M[i]) <= np.maximum(tol, 1e-9)).all(axis=1)
        idx = np.nonzero(m)[0]
        if idx.size < 3:
            continue
        ns = len(set(src[idx]))
        # axis-wise bracketing of the target: interpolation only
        ok = T[idx].min() <= T[i] <= T[idx].max()
        if ok and not np.isnan(lnP[i]):
            lp = lnP[idx][~np.isnan(lnP[idx])]
            ok = lp.size > 0 and lp.min() <= lnP[i] <= lp.max()
        if ok:
            for k in range(len(ION)):
                col = M[idx, k]
                if col.max() - col.min() > 1e-9 and not (col.min() <= M[i, k] <= col.max()):
                    ok = False
                    break
        if not ok:
            continue
        # design matrix centred on the target
        cols, dist = [T[idx] - T[i]], [np.abs(T[idx] - T[i]) / W_T]
        if not np.isnan(lnP[i]):
            lpn = np.where(np.isnan(lnP[idx]), lnP[i], lnP[idx])
            cols.append(lpn - lnP[i]); dist.append(np.abs(lpn - lnP[i]) / W_LNP)
        for k in range(len(ION)):
            col = M[idx, k]
            if col.max() - col.min() > 1e-9:
                cols.append(col - M[i, k]); dist.append(np.abs(col - M[i, k]) / (W_M * max(abs(M[i, k]), 1.0) + 0.05))
        u = np.max(np.vstack(dist), axis=0)
        w = np.clip(1.0 - np.clip(u, 0, 1) ** 3, 0, 1) ** 3 + 1e-6
        X = np.column_stack([np.ones(len(idx))] + [c for c in cols if np.ptp(c) > 1e-12])
        if X.shape[0] < X.shape[1] + 1:
            continue
        sw = np.sqrt(w)
        beta, *_ = np.linalg.lstsq(X * sw[:, None], Y[idx] * sw, rcond=None)
        pv = float(np.exp(beta[0]) if use_log else beta[0])
        lo, hi = V[idx].min(), V[idx].max()
        if not (np.isfinite(pv) and min(lo / 2, lo * 2) <= pv <= max(hi * 2, hi / 2)):
            continue   # a local fit outside the range of its own neighbours is an extrapolation artefact
        pred[i] = pv
        nsrc[i] = ns
        npts[i] = idx.size
    return pred, nsrc, npts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tol-t", type=float, default=1.0)
    ap.add_argument("--tol-p", type=float, default=0.02)
    ap.add_argument("--tol-m", type=float, default=0.02)
    a = ap.parse_args()
    sys.path.insert(0, a.repo)
    import gasbrinebench as gbb
    ms = load_ms(a.repo)

    df = gbb.load(exclude_tags=None, exclude_flags=None, derive=False)
    df["row_id"] = df.groupby("family").cumcount()
    from gasbrinebench.vocab import DEFAULT_EXCLUDED_FLAGS
    bad = set(DEFAULT_EXCLUDED_FLAGS)
    keep = ~df["flags"].fillna("").map(lambda f: bool(bad & set(f.split(";")))) & (df["tag"] != "lle-regime")
    df = df[keep].copy()
    df["src"] = df["source"].map(lambda s: ms.canonical_id(*ms.parse_source_key(ms.apply_source_key_fix(s))))
    if "m_gas" not in df.columns:
        df["m_gas"] = np.nan

    out_rows = []
    for fam, prop in GROUPS:
        sub = df[(df["family"] == fam) & (df["property"] == prop)]
        for gas, g in sub.groupby("gas"):
            g = g.copy()
            ref, nother, spread, mean_o, sd_o = neighbours_stats(g, a.tol_t, a.tol_p, a.tol_m)
            g["reference"], g["n_other_sources"], g["spread_other"] = ref, nother, spread
            g["mean_other"], g["sd_other"] = mean_o, sd_o
            sp, sns, snp = smooth_stats(g)
            g["ref_smooth"], g["n_other_smooth"], g["n_points_smooth"] = sp, sns, snp
            g["rel_dev_smooth"] = (g["value"] - sp) / np.abs(sp)
            g["abs_dev"] = g["value"] - g["reference"]
            with np.errstate(divide="ignore", invalid="ignore"):
                g["rel_dev"] = np.where(np.abs(g["reference"]) > 0, g["abs_dev"] / np.abs(g["reference"]), np.nan)
            out_rows.append(g)
    allr = pd.concat(out_rows, ignore_index=True)

    def rscale(x):
        x = pd.Series(x).dropna()
        return 1.4826 * float(np.median(np.abs(x - np.median(x)))) if len(x) else np.nan

    stats = {"strict": ("n_other_sources", "rel_dev"), "smooth": ("n_other_smooth", "rel_dev_smooth")}
    for name, (nc, dc) in stats.items():
        have = allr[nc] > 0
        pooled = allr[have].groupby(["family", "property"])[dc].apply(rscale)
        allr["scale_" + name] = [pooled.get((f, p_), np.nan) for f, p_ in zip(allr["family"], allr["property"])]
        thr = np.maximum(3 * allr["scale_" + name], MIN_OUTLIER)
        allr["outlier_" + name] = have & (allr[nc] >= 2) & (allr[dc].abs() > thr)
    allr["consensus_outlier"] = allr["outlier_smooth"] | allr["outlier_strict"]
    cmp_ = allr[(allr["n_other_sources"] > 0) | (allr["n_other_smooth"] > 0)].copy()

    os.makedirs(a.out, exist_ok=True)
    cols = ["family", "row_id", "dataset_id", "source", "gas", "property", "T_K", "P_bar", *ION, "value",
            "reference", "mean_other", "sd_other", "n_other_sources", "spread_other", "rel_dev", "ref_smooth", "n_other_smooth", "n_points_smooth",
            "rel_dev_smooth", "outlier_strict", "outlier_smooth", "consensus_outlier"]
    cmp_[cols].sort_values(["family", "row_id"]).to_csv(os.path.join(a.out, "consensus_rows.csv"), index=False, lineterminator="\n", float_format="%.6g")

    n_all = allr.groupby(["source", "family", "property"]).size().rename("n_rows_in_default_view")
    recs = []
    for (src_, fam, prop), g in allr.groupby(["source", "family", "property"]):
        rec = {"source": src_, "family": fam, "property": prop, "n_rows_in_default_view": len(g)}
        for name, (nc, dc) in stats.items():
            gg = g[g[nc] > 0]
            rd = gg[dc].dropna()
            rec.update({f"{name}_n_compared": len(rd), f"{name}_bias_median": float(rd.median()) if len(rd) else np.nan,
                        f"{name}_scale_mad": rscale(rd),
                        f"{name}_share_beyond_10pct": float((rd.abs() > 0.10).mean()) if len(rd) else np.nan,
                        f"{name}_outliers": int(g["outlier_" + name].sum())})
        rec["n_consensus_outliers"] = int(g["consensus_outlier"].sum())
        recs.append(rec)
    summ = pd.DataFrame(recs).sort_values(["n_consensus_outliers", "smooth_n_compared"], ascending=False)
    summ.to_csv(os.path.join(a.out, "consensus_by_source.csv"), index=False, lineterminator="\n", float_format="%.4g")

    print(f"tolerances (strict): T {a.tol_t} K, P {a.tol_p:.0%}, ions {a.tol_m:.0%}; smooth window: T +-{W_T} K, lnP +-{W_LNP}, ions +-{W_M:.0%}")
    print(f"rows in the comparison set: {len(allr):,}")
    t = allr.groupby(["family", "property"]).apply(lambda g: pd.Series({
        "rows": len(g), "strict": int((g.n_other_sources > 0).sum()), "smooth": int((g.n_other_smooth > 0).sum()),
        "either": int(((g.n_other_sources > 0) | (g.n_other_smooth > 0)).sum())}))
    print(t.to_string())
    print("pooled robust scale (strict):", allr.groupby(["family", "property"])["scale_strict"].first().round(4).to_dict())
    print("pooled robust scale (smooth):", allr.groupby(["family", "property"])["scale_smooth"].first().round(4).to_dict())
    print("outliers strict/smooth/any:", int(allr.outlier_strict.sum()), int(allr.outlier_smooth.sum()), int(allr.consensus_outlier.sum()),
          "rows in", allr.loc[allr.consensus_outlier, "source"].nunique(), "sources")
    both = allr[(allr.n_other_sources > 0) & (allr.n_other_smooth > 0)]
    print("rows with both statistics:", len(both), "| corr of the two relative deviations:", round(float(both[["rel_dev", "rel_dev_smooth"]].corr().iloc[0, 1]), 3))


if __name__ == "__main__":
    main()
