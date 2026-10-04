"""Plotting helpers shared by the GasBrineBench notebooks (matplotlib and pandas only).

Style: bold text, thick frames and curves, no figure titles, colour AND marker/line style so that figures survive grayscale and
colour-vision deficiency (palette: Wong 2011).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

WONG = ["#000000", "#E69F00", "#56B4E9", "#009E73", "#D55E00", "#0072B2", "#CC79A7"]
MARKERS = ["o", "s", "^", "D", "v", "P", "X", "*", "<", ">", "h", "p"]
LINESTYLES = ["-", "--", "-.", ":", (0, (3, 1, 1, 1, 1, 1))]

GAS_LABEL = {"co2": "CO2", "ch4": "CH4", "h2": "H2", "n2": "N2", "o2": "O2", "c2h6": "C2H6", "c3h8": "C3H8"}

#: temperature bins [K] used to group isotherms; edges and labels
T_EDGES = [270, 285, 295, 305, 320, 340, 370, 420, 520, 800]


def style(dpi: int = 110) -> None:
    mpl.rcParams.update({
        "font.size": 13, "axes.labelsize": 15, "xtick.labelsize": 12, "ytick.labelsize": 12, "legend.fontsize": 10.5,
        "font.weight": "bold", "axes.labelweight": "bold", "axes.titleweight": "bold",
        "axes.linewidth": 1.6, "axes.edgecolor": "black",
        "xtick.major.width": 1.6, "ytick.major.width": 1.6, "xtick.major.size": 6, "ytick.major.size": 6,
        "xtick.color": "black", "ytick.color": "black", "xtick.direction": "in", "ytick.direction": "in",
        "lines.linewidth": 2.2, "lines.markersize": 6,
        "legend.frameon": True, "legend.edgecolor": "black",
        "figure.dpi": dpi, "savefig.dpi": 300, "savefig.bbox": "tight",
    })


def tbin_index(T, edges=T_EDGES):
    return np.clip(np.digitize(np.asarray(T, float), edges) - 1, 0, len(edges) - 2)


def tbin_label(i, edges=T_EDGES):
    return f"{edges[i]}-{edges[i + 1]} K"


def tbin_colors(n):
    cmap = plt.get_cmap("plasma")
    return [cmap(0.05 + 0.85 * k / max(n - 1, 1)) for k in range(n)]


def trend(x, y, nbins=8, logx=True):
    """Median of y in nbins bins of x (log-spaced if logx): the line that carries the eye through scatter."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y) & (x > 0 if logx else True)
    x, y = x[ok], y[ok]
    if len(x) < 4:
        return np.array([]), np.array([])
    edges = np.geomspace(x.min(), x.max(), nbins + 1) if logx else np.linspace(x.min(), x.max(), nbins + 1)
    idx = np.clip(np.digitize(x, edges) - 1, 0, nbins - 1)
    xs, ys = [], []
    for b in range(nbins):
        m = idx == b
        if m.sum() >= 2:
            xs.append(np.median(x[m])); ys.append(np.median(y[m]))
    return np.array(xs), np.array(ys)


def qtrend(x, y, nbins=8, min_n=12):
    """Equal-count bins of x: returns bin-median x, median y, 25th and 75th percentile of y (bins with fewer than min_n points are skipped)."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if len(x) < 2 * min_n:
        return [np.array([])] * 4
    order = np.argsort(x); x, y = x[order], y[order]
    nb = max(1, min(nbins, len(x) // min_n))
    xs, m, lo, hi = [], [], [], []
    for part in np.array_split(np.arange(len(x)), nb):
        xs.append(np.median(x[part])); m.append(np.median(y[part])); lo.append(np.percentile(y[part], 25)); hi.append(np.percentile(y[part], 75))
    return np.array(xs), np.array(m), np.array(lo), np.array(hi)


def isotherms(ax, df, x="P_bar", y="value", edges=T_EDGES, logx=True, logy=True, err=True, trend_line=True, min_n=3, legend=True):
    """Scatter coloured by temperature bin (colour AND marker), median trend per bin, stated uncertainty as error bars."""
    d = df.dropna(subset=[x, y]).copy()
    d["tb"] = tbin_index(d["T_K"], edges)
    bins = sorted(d["tb"].unique())
    cols = tbin_colors(len(edges) - 1)
    for k, b in enumerate(bins):
        g = d[d.tb == b]
        if len(g) < min_n:
            continue
        c = cols[b]; mk = MARKERS[b % len(MARKERS)]
        if err and "uncertainty" in g and g["uncertainty"].notna().any():
            e = g[g["uncertainty"].notna()]
            ax.errorbar(e[x], e[y], yerr=e["uncertainty"], fmt="none", ecolor=c, elinewidth=1.2, alpha=0.6, capsize=2)
        ax.scatter(g[x], g[y], s=26, color=c, marker=mk, edgecolor="black", linewidth=0.5, alpha=0.8, label=f"{tbin_label(b, edges)} (n={len(g)})", zorder=3)
        if trend_line:
            tx, ty = trend(g[x], g[y], logx=logx)
            if len(tx):
                ax.plot(tx, ty, color=c, ls=LINESTYLES[b % len(LINESTYLES)], lw=2.0, zorder=2)
    if logx: ax.set_xscale("log")
    if logy: ax.set_yscale("log")
    if legend and bins:
        ax.legend(loc="best", ncol=1, handletextpad=0.3, borderpad=0.4, labelspacing=0.25)
    return ax


def by_source(ax, df, x="P_bar", y="value", top=8, logx=True, logy=True, legend=True):
    """Same data, coloured by source: the top sources by row count get their own colour and marker, the rest are gray."""
    d = df.dropna(subset=[x, y])
    counts = d["source"].value_counts()
    names = list(counts.index[:top])
    rest = d[~d["source"].isin(names)]
    if len(rest):
        ax.scatter(rest[x], rest[y], s=16, color="#bbbbbb", marker="o", edgecolor="none", alpha=0.7, label=f"{rest['source'].nunique()} other sources", zorder=1)
    for k, n in enumerate(names):
        g = d[d["source"] == n]
        ax.scatter(g[x], g[y], s=28, color=WONG[(k + 1) % len(WONG)], marker=MARKERS[k % len(MARKERS)], edgecolor="black", linewidth=0.5, alpha=0.85,
                   label=f"{n} ({len(g)})", zorder=3)
    if logx: ax.set_xscale("log")
    if logy: ax.set_yscale("log")
    if legend:
        ax.legend(loc="best", handletextpad=0.3, borderpad=0.4, labelspacing=0.25)
    return ax


def wagner_psat_bar(T):
    """Saturation pressure of water [bar], IAPWS-IF97 region-4 equation (T in K, 273.15-647.096)."""
    n = [0.11670521452767e4, -0.72421316703206e6, -0.17073846940092e2, 0.12020824702470e5, -0.32325550322333e7,
         0.14915108613530e2, -0.48232657361591e4, 0.40511340542057e6, -0.23855557567849, 0.65017534844798e3]
    T = np.asarray(T, float)
    th = T + n[8] / (T - n[9])
    A = th ** 2 + n[0] * th + n[1]
    B = n[2] * th ** 2 + n[3] * th + n[4]
    C = n[5] * th ** 2 + n[6] * th + n[7]
    p = (2 * C / (-B + np.sqrt(B ** 2 - 4 * A * C))) ** 4
    return p * 10.0  # MPa -> bar


def lab(ax, xlabel, ylabel, panel=None):
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel)
    if panel:
        ax.text(0.0, 1.015, panel, transform=ax.transAxes, va="bottom", ha="left", fontsize=15)
    for s in ax.spines.values():
        s.set_linewidth(1.6)


def load_all(**kw):
    import gasbrinebench as gbb
    return gbb.load(**kw)
