#!/usr/bin/env python3
"""Build and execute the visualisation notebooks in notebooks/ (needs nbformat, nbconvert, matplotlib, pandas).

    python3 tools/make_notebooks.py            # write and execute all notebooks
    python3 tools/make_notebooks.py --no-exec  # write only

The notebooks are committed with their outputs. Rerun this script after any change of the data.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import nbformat as nbf
from nbformat.v4 import new_code_cell as code, new_markdown_cell as md, new_notebook

ROOT = pathlib.Path(__file__).resolve().parents[1]
NB = ROOT / "notebooks"

GITHUB = "jmoortgat/GasBrineBench"

BADGE = ('<a href="https://colab.research.google.com/github/{repo}/blob/main/notebooks/{name}.ipynb" target="_blank" rel="noopener noreferrer">'
         '<img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab"/></a>')

COLAB_NOTE = """> **Running on Google Colab?** Click the badge above and run the cells; nothing needs to be installed. The first code cell detects
> Colab, clones the repository into `/content/GasBrineBench`, checks that pandas, numpy and matplotlib are present (Colab already has them)
> and changes into `notebooks/`, so everything after it works as on a local checkout. Locally the cell does nothing but confirm the layout.
> To use a fork or a branch, set `GBB_REPO_URL` and `GBB_BRANCH` before the cell runs."""

BOOTSTRAP = '''# --- Colab / local bootstrap ---------------------------------------------------------------------------------
# On Colab this cell clones the repository and installs anything missing; on a local checkout it only confirms the layout.
# Re-running it is safe.
import os, subprocess, sys
from pathlib import Path

REPO_URL = os.environ.get("GBB_REPO_URL", "https://github.com/%s.git")
BRANCH = os.environ.get("GBB_BRANCH", "main")
try:
    import google.colab  # noqa: F401
    IN_COLAB = True
except ImportError:
    IN_COLAB = False

if IN_COLAB or os.environ.get("GBB_FORCE_BOOTSTRAP"):
    REPO_DIR = Path("/content/GasBrineBench") if IN_COLAB else Path(os.environ.get("GBB_CLONE_DIR", "GasBrineBench_clone")).resolve()
    if not REPO_DIR.exists():
        print(f"cloning {REPO_URL} ({BRANCH}) into {REPO_DIR}")
        subprocess.check_call(["git", "clone", "--depth", "1", "--branch", BRANCH, REPO_URL, str(REPO_DIR)])
    else:
        print(f"repository already cloned at {REPO_DIR}")
    missing = []
    for pkg, mod in [("pandas", "pandas"), ("numpy", "numpy"), ("matplotlib", "matplotlib")]:
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        print("pip install -q", " ".join(missing))
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", *missing])
    os.chdir(REPO_DIR / "notebooks")
    print("cwd =", os.getcwd())
else:
    print("local environment: using the existing checkout")''' % GITHUB

SETUP = '''import sys, pathlib, warnings
warnings.filterwarnings("ignore")
HERE = pathlib.Path.cwd()
ROOT = HERE if (HERE / "gasbrinebench").exists() else HERE.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "notebooks"))
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
import gasbrinebench as gbb
from gasbrinebench.vocab import DEFAULT_EXCLUDED_FLAGS
import gbb_viz as V
V.style()
# default view (what a benchmark user scores) and the view that also keeps rows without a stated pressure
df = gbb.load()
dfp = gbb.load(exclude_flags=tuple(f for f in DEFAULT_EXCLUDED_FLAGS if f != "pressure-unstated"))
dfall = gbb.load(exclude_tags=None, exclude_flags=None)
print(f"{len(dfall):,} rows in total, {len(df):,} in the default view, gasbrinebench {gbb.__version__}")'''


def nb01():
    c = [md("""# 1. Overview and coverage

What is in GasBrineBench v1.2, where it sits in temperature and pressure, how it divides between gases and brines, how the quality
codes and modifier flags are distributed, and which papers contribute. Later notebooks look at each kind of data in turn.

All figures follow one convention: colour **and** marker (and line style) carry the same information, so they can be read in grayscale.
Quality codes: R = independently corroborated, T = tentative, U = uncertain. The *default view* drops rows with a flag that
`SCHEMA.md` lists as default-excluded (other gases, hydrate regime, no stated pressure, ...)."""),
         code(SETUP),
         md("## Rows per family"),
         code('''inv = gbb.inventory(dfall, by="family")
inv["default view"] = df.groupby("family").size()
display(inv[["rows", "default view", "sources", "gases", "T_min", "T_max", "P_min", "P_max", "R", "T", "U"]].fillna(0).round(2))'''),
         code('''fig, ax = plt.subplots(figsize=(9, 4.4))
order = inv.sort_values("rows").index
ax.barh(order, inv.loc[order, "rows"], color="#bbbbbb", edgecolor="black", linewidth=1.4, hatch="//", label="all rows")
ax.barh(order, inv.loc[order, "default view"].fillna(0), color="#56B4E9", edgecolor="black", linewidth=1.4, label="default view")
ax.set_xscale("log"); V.lab(ax, "rows", "")
ax.legend(loc="lower right"); plt.show()'''),
         md("## Where the data are in temperature and pressure"),
         code('''fams = ["solubility", "y_h2o", "rho", "psat_ratio", "phi_osm", "thermo_brine"]
fig, axes = plt.subplots(2, 3, figsize=(15, 8.2), sharex=False)
for ax, f in zip(axes.ravel(), fams):
    g = dfall[(dfall.family == f)]
    p = g.P_bar.where(g.P_bar > 0)
    if f == "psat_ratio":
        m = gbb.total_molality(g)
        hb = ax.hexbin(g.T_K, m, gridsize=34, bins="log", cmap="viridis", mincnt=1, linewidths=0.2)
        plt.colorbar(hb, ax=ax, label="rows (log)")
        V.lab(ax, "T [K]", "total ion molality [mol/kg]", f"({chr(97 + fams.index(f))}) {f} (pressure is the value)")
        continue
    if p.notna().sum() == 0:
        ax.text(0.5, 0.5, "no pressure", ha="center", va="center", transform=ax.transAxes)
    else:
        hb = ax.hexbin(g.T_K[p.notna()], p[p.notna()], gridsize=38, yscale="log", bins="log", cmap="viridis", mincnt=1, linewidths=0.2)
        plt.colorbar(hb, ax=ax, label="rows (log)")
    V.lab(ax, "T [K]", "P [bar]", f"({chr(97 + fams.index(f))}) {f}")
plt.tight_layout(); plt.show()'''),
         md("""## Gases and salts

Rows of gas solubility (`solubility_molality`) by gas and by salt system. A zero is a gap in the literature we could transcribe, and is as
informative as a count."""),
         code('''cov = gbb.coverage(gbb.load("solubility", property="solubility_molality"))
cov = cov.loc[[g for g in ["co2", "ch4", "h2", "n2", "o2", "c2h6", "c3h8"] if g in cov.index]]
fig, ax = plt.subplots(figsize=(14, 4.2))
from matplotlib.colors import LogNorm
im = ax.imshow(cov.values.clip(min=0.5), aspect="auto", cmap="viridis", norm=LogNorm(vmin=1, vmax=cov.values.max()))
ax.set_xticks(range(cov.shape[1])); ax.set_xticklabels(cov.columns, rotation=60, ha="right")
ax.set_yticks(range(cov.shape[0])); ax.set_yticklabels([V.GAS_LABEL[g] for g in cov.index])
for i in range(cov.shape[0]):
    for j in range(cov.shape[1]):
        v = int(cov.values[i, j])
        ax.text(j, i, str(v) if v else "", ha="center", va="center", fontsize=9, color="white" if v < 300 else "black")
plt.colorbar(im, ax=ax, label="rows (log)"); plt.tight_layout(); plt.show()'''),
         md("## Quality codes and modifier flags"),
         code('''q = dfall.groupby(["family", "quality"]).size().unstack(fill_value=0).reindex(columns=["R", "T", "U"], fill_value=0)
q = q.loc[q.sum(axis=1).sort_values().index]
fig, axes = plt.subplots(1, 2, figsize=(15, 4.8), gridspec_kw={"width_ratios": [1, 1.25]})
left = np.zeros(len(q))
for k, (c, col, h) in enumerate([("R", "#009E73", ""), ("T", "#bbbbbb", "//"), ("U", "#D55E00", "xx")]):
    axes[0].barh(q.index, q[c], left=left, color=col, edgecolor="black", linewidth=1.3, hatch=h, label=c); left += q[c].values
axes[0].set_xscale("log"); axes[0].set_xlim(left=1); V.lab(axes[0], "rows", "", "(a)"); axes[0].legend(loc="lower right")
fl = dfall["flags"].str.split(";").explode()
fl = fl[fl != ""].value_counts().sort_values()
axes[1].barh(fl.index, fl.values, color=["#D55E00" if f in DEFAULT_EXCLUDED_FLAGS else "#56B4E9" for f in fl.index], edgecolor="black", linewidth=1.3)
V.lab(axes[1], "rows carrying the flag", "", "(b)")
axes[1].text(0.97, 0.05, "orange: dropped by the default view", transform=axes[1].transAxes, ha="right", fontsize=11)
plt.tight_layout(); plt.show()'''),
         md("## Which papers contribute, and when they were published"),
         code('''import re
src = dfall.groupby("source").size().sort_values(ascending=False)
display(src.head(20).to_frame("rows"))
yr = pd.Series([int(m.group(0)) if (m := re.search(r"(19|20)\\d\\d", s)) else np.nan for s in src.index]).dropna()
fig, ax = plt.subplots(figsize=(10, 4))
ax.hist(yr, bins=np.arange(1900, 2031, 5), color="#56B4E9", edgecolor="black", linewidth=1.4, hatch="//")
V.lab(ax, "year of publication of the source key", "source keys"); plt.show()
print(f"{src.size} source keys; the 20 largest hold {src.head(20).sum() / src.sum():.0%} of the rows")''')]
    return c


def nb02():
    c = [md("""# 2. Gas solubility

`solubility.csv`: the dissolved gas in mol per kg of water (`solubility_molality`; its mole-fraction sibling carries the same information).
For each gas, three views of the **pure-water** data:

* (a) solubility against pressure, one colour/marker per temperature bin, with the median trend of each bin and the stated uncertainty
  where a source gave one (13 % of the rows);
* (b) the same points coloured by **source**: spread between colours at the same state is the disagreement between laboratories;
* (c) solubility against temperature at fixed pressure windows.

Then the salting-out trend: solubility against salt molality, at fixed pressure windows. Only the default view is used, so hydrate-regime
and liquid-liquid points are not mixed into gas solubility."""),
         code(SETUP),
         code('''sol = df[(df.property == "solubility_molality")]
pure = sol[sol.total_molality == 0]
GASES = ["co2", "ch4", "h2", "n2", "o2", "c2h6", "c3h8"]
print(pure.groupby("gas").agg(rows=("value", "size"), sources=("source", "nunique"), T_min=("T_K", "min"), T_max=("T_K", "max"), P_max=("P_bar", "max")).round(1))

def pressure_windows(g, n=4):
    q = np.quantile(g.P_bar, np.linspace(0.12, 0.88, n))
    return [(p * 0.88, p * 1.12) for p in q]

def gas_figure(gas):
    g = pure[pure.gas == gas]
    fig, ax = plt.subplots(1, 3, figsize=(18, 5.3))
    V.isotherms(ax[0], g); V.lab(ax[0], "P [bar]", "dissolved gas [mol/kg water]", f"(a) {V.GAS_LABEL[gas]}")
    V.by_source(ax[1], g); V.lab(ax[1], "P [bar]", "dissolved gas [mol/kg water]", "(b)")
    for k, (lo, hi) in enumerate(pressure_windows(g)):
        w = g[(g.P_bar >= lo) & (g.P_bar <= hi)]
        if len(w) < 3: continue
        ax[2].scatter(w.T_K, w.value, s=30, color=V.WONG[(k + 1) % 7], marker=V.MARKERS[k], edgecolor="black", linewidth=0.5, alpha=0.85,
                      label=f"{np.sqrt(lo * hi):.0f} bar (n={len(w)})")
        tx, ty = V.trend(w.T_K, w.value, nbins=7, logx=False)
        if len(tx): ax[2].plot(tx, ty, color=V.WONG[(k + 1) % 7], ls=V.LINESTYLES[k % 5])
    ax[2].set_yscale("log"); ax[2].legend(loc="best"); V.lab(ax[2], "T [K]", "dissolved gas [mol/kg water]", "(c)")
    plt.tight_layout(); plt.show()'''),
         md("## CO2 in water"), code('gas_figure("co2")'),
         md("## CH4 in water"), code('gas_figure("ch4")'),
         md("## H2 in water"), code('gas_figure("h2")'),
         md("## N2 in water"), code('gas_figure("n2")'),
         md("## O2 in water"), code('gas_figure("o2")'),
         md("## C2H6 in water"), code('gas_figure("c2h6")'),
         md("## C3H8 in water"), code('gas_figure("c3h8")'),
         md("""## Salting out

Solubility against the molality of NaCl (single-salt brines, `Na-Cl`), at fixed pressure windows, one colour/marker per temperature bin.
A gas dissolves less in a brine than in water; the slope in log space is the Setschenow-type trend. Spread at one molality and colour is
the difference between datasets and temperatures within a bin."""),
         code('''nacl = sol[sol.salt_system.isin(["water", "Na-Cl"])].copy()
nacl["m_NaCl"] = nacl.m_Na

def best_window(g, width=0.12):
    """Pressure window (log-centred, +-12 %) that holds the most NaCl-brine points at the most molalities."""
    b = g[g.m_NaCl > 0]
    best = (0, None)
    for pc in np.geomspace(max(b.P_bar.min(), 0.1), b.P_bar.max(), 60):
        w = b[(b.P_bar >= pc * (1 - width)) & (b.P_bar <= pc * (1 + width))]
        score = len(w) * w.m_NaCl.round(1).nunique()
        if score > best[0]: best = (score, (pc * (1 - width), pc * (1 + width)))
    return best[1]

fig, axes = plt.subplots(2, 3, figsize=(18, 10.5))
for ax, gas in zip(axes.ravel(), ["co2", "ch4", "o2", "h2", "n2", "c3h8"]):
    g = nacl[nacl.gas == gas]
    win = best_window(g) if (g.m_NaCl > 0).sum() >= 5 else None
    if win is None:
        ax.text(0.5, 0.5, "too few NaCl-brine points", transform=ax.transAxes, ha="center"); V.lab(ax, "", "", V.GAS_LABEL[gas]); continue
    w = g[(g.P_bar >= win[0]) & (g.P_bar <= win[1])]
    V.isotherms(ax, w, x="m_NaCl", y="value", logx=False, logy=True, trend_line=True)
    V.lab(ax, "NaCl [mol/kg water]", "dissolved gas [mol/kg water]", f"{V.GAS_LABEL[gas]}, {win[0]:.3g}-{win[1]:.3g} bar")
plt.tight_layout(); plt.show()'''),
         md("""## Mixed salts and other salts

CO2 near 323 K and 100-250 bar against ionic strength, by salt system: how much of the salt effect is carried by ionic strength alone?"""),
         code('''g = sol[(sol.gas == "co2") & sol.T_K.between(318, 328) & sol.P_bar.between(90, 260) & (sol.total_molality >= 0)].copy()
g["I"] = g.ionic_strength
systems = g.salt_system.value_counts().head(7).index
fig, ax = plt.subplots(figsize=(10, 6))
for k, s in enumerate(systems):
    w = g[g.salt_system == s]
    ax.scatter(w.I, w.value, s=30, color=V.WONG[k % 7], marker=V.MARKERS[k], edgecolor="black", linewidth=0.5, alpha=0.8, label=f"{s} (n={len(w)})")
ax.set_yscale("log"); ax.legend(loc="best"); V.lab(ax, "ionic strength [mol/kg]", "CO2 [mol/kg water]"); plt.show()''')]
    return c


def nb03():
    c = [md("""# 3. Water content of the gas phase, mixed gases and enthalpy of solution

* `y_h2o.csv`: mole fraction of water in the gas-rich phase, against pressure and temperature, and as an **enhancement factor**
  f = y P / p_sat(T) that removes the leading temperature dependence and shows deviations from an ideal mixture.
* `ternary.csv`: CO2 + CH4 + water, with the gas-phase split as an explicit variable.
* `dh_sol.csv`: calorimetric enthalpy of dissolution of gases in water."""),
         code(SETUP),
         code('''y = df[(df.property == "y_h2o")]
yw = y[y.total_molality == 0].copy()
yw["psat"] = V.wagner_psat_bar(yw.T_K.clip(upper=647.0))
yw["enh"] = yw.value * yw.P_bar / yw.psat
print(yw.groupby("gas").agg(rows=("value", "size"), sources=("source", "nunique"), T_min=("T_K", "min"), T_max=("T_K", "max")).round(1))'''),
         md("## Water mole fraction against pressure, by temperature (pure water, per gas)"),
         code('''gases = [g for g in ["co2", "ch4", "n2", "c2h6", "c3h8", "h2"] if (yw.gas == g).sum() >= 8]
fig, axes = plt.subplots(2, 3, figsize=(18, 10))
for ax, gas in zip(axes.ravel(), gases):
    V.isotherms(ax, yw[yw.gas == gas], y="value", err=True)
    V.lab(ax, "P [bar]", "water in the gas [mole fraction]", V.GAS_LABEL[gas])
plt.tight_layout(); plt.show()'''),
         md("""## Enhancement factor

f = y P / p_sat(T) is 1 for an ideal gas mixture and rises with pressure through the fugacity coefficient of water and the
Poynting correction. On this scale the gases can be compared directly, and a source that disagrees with its neighbours stands out."""),
         code('''fig, axes = plt.subplots(1, 2, figsize=(16, 6))
for k, gas in enumerate(gases):
    g = yw[(yw.gas == gas) & yw.T_K.between(318, 328)]
    if len(g) == 0: continue
    axes[0].scatter(g.P_bar, g.enh, s=28, color=V.WONG[(k + 1) % 7], marker=V.MARKERS[k], edgecolor="black", linewidth=0.5, alpha=0.85, label=f"{V.GAS_LABEL[gas]} (n={len(g)})")
axes[0].set_xscale("log"); axes[0].set_yscale("log"); axes[0].legend(); V.lab(axes[0], "P [bar]", "enhancement factor y P / p_sat", "(a) 318-328 K")
g = yw[(yw.gas == "co2") & yw.T_K.between(318, 328)]
V.by_source(axes[1], g, y="enh", top=9); V.lab(axes[1], "P [bar]", "enhancement factor y P / p_sat", "(b) CO2, by source")
plt.tight_layout(); plt.show()'''),
         md("## Effect of salt on the water content (CO2 and CH4)"),
         code('''ys = y[(y.salt_system.isin(["water", "Na-Cl"]))]
fig, axes = plt.subplots(1, 2, figsize=(15, 5.5))
for ax, gas in zip(axes, ["co2", "ch4"]):
    g = ys[ys.gas == gas].copy(); g["m_NaCl"] = g.m_Na
    V.isotherms(ax, g, x="m_NaCl", y="value", logx=False, logy=True, trend_line=False)
    V.lab(ax, "NaCl [mol/kg water]", "water in the gas [mole fraction]", V.GAS_LABEL[gas])
plt.tight_layout(); plt.show()'''),
         md("""## CO2 + CH4 + water

`ternary.csv` carries the gas-phase CO2 fraction (water-free) `y_co2_dry`. The dissolved amounts of both gases and the water content of
the mixed gas change with it, which is why the split is a state variable and not a label."""),
         code('''t = gbb.load("ternary", exclude_tags=None, exclude_flags=None).copy()
t["y_co2_dry"] = pd.to_numeric(t["y_co2_dry"], errors="coerce")
fig, axes = plt.subplots(1, 3, figsize=(18, 5.2))
for ax, (gas, prop, lab_) in zip(axes, [("co2", "xc_saltfree", "dissolved CO2 [mole fraction]"), ("ch4", "xc_saltfree", "dissolved CH4 [mole fraction]"), ("co2-ch4", "y_h2o", "water in the mixed gas [mole fraction]")]):
    g = t[(t.gas == gas) & (t.property == prop)]
    sc = ax.scatter(g.y_co2_dry, g.value, c=g.P_bar, cmap="viridis", s=40, edgecolor="black", linewidth=0.6, marker="o")
    plt.colorbar(sc, ax=ax, label="P [bar]"); V.lab(ax, "CO2 in the dry gas [mole fraction]", lab_)
    ax.set_yscale("log")
plt.tight_layout(); plt.show()
print(t.groupby(["source", "gas", "property"]).size())'''),
         md("""## Enthalpy of solution of gases

`dh_sol` in kJ per mol of gas (negative: exothermic). Points carry the stated uncertainty where there is one (63 % of the rows)."""),
         code('''h = df[df.property == "dh_sol"]
print(h.groupby("gas").size().sort_values(ascending=False).to_dict())
fig, axes = plt.subplots(1, 2, figsize=(15, 5.5))
top = h.gas.value_counts().index[:8]
for k, gas in enumerate(top):
    g = h[h.gas == gas]
    axes[0].errorbar(g.T_K, g.value, yerr=g.uncertainty.fillna(0), fmt=V.MARKERS[k % 12], color=V.WONG[(k + 1) % 7], mec="black", ms=6, elinewidth=1.2, capsize=2, alpha=0.85, label=f"{gas} (n={len(g)})")
axes[0].legend(ncol=2); V.lab(axes[0], "T [K]", "enthalpy of solution [kJ/mol gas]", "(a)")
g = h[h.gas.isin(["co2", "ch4", "o2"])]
for k, gas in enumerate(["co2", "ch4", "o2"]):
    w = g[g.gas == gas]
    axes[1].scatter(w.P_bar, w.value, s=36, color=V.WONG[(k + 1) % 7], marker=V.MARKERS[k], edgecolor="black", linewidth=0.5, label=gas)
axes[1].set_xscale("log"); axes[1].legend(); V.lab(axes[1], "P [bar]", "enthalpy of solution [kJ/mol gas]", "(b)")
plt.tight_layout(); plt.show()''')]
    return c


def nb04():
    c = [md("""# 4. Brine properties

Density, osmotic coefficient, vapour-pressure ratio, apparent molar heat capacity, viscosity, density of CO2-loaded solutions and
permittivity. Osmotic coefficients, heat capacities and some vapour-pressure data are conventionally reported without a pressure; those
rows carry the flag `pressure-unstated` and are dropped by the default view, so this notebook uses the view `dfp` that keeps them
(everything else of the default exclusion still applies)."""),
         code(SETUP),
         md("""## Density of salt solutions

(a) NaCl: density against temperature, one colour/marker per molality bin (pressure up to 100 bar so that the pressure effect stays small);
(b) NaCl near 1 mol/kg: density against pressure, by temperature bin; (c) other salts at their commonest molalities."""),
         code('''rho = df[df.property == "rho"]
nacl = rho[rho.salt_system.eq("Na-Cl")].copy(); nacl["m"] = nacl.m_Na
fig, axes = plt.subplots(1, 3, figsize=(19, 5.5))
edges = [0, 0.3, 1.2, 2.5, 4.5, 6.5, 9]
g = nacl[nacl.P_bar <= 100]
cols = V.tbin_colors(len(edges) - 1)
for b in range(len(edges) - 1):
    w = g[g.m.between(edges[b], edges[b + 1], inclusive="left")]
    if len(w) < 5: continue
    axes[0].scatter(w.T_K, w.value, s=14, color=cols[b], marker=V.MARKERS[b], edgecolor="none", alpha=0.7, label=f"{edges[b]}-{edges[b+1]} mol/kg (n={len(w)})")
    tx, ty = V.trend(w.T_K, w.value, logx=False); axes[0].plot(tx, ty, color=cols[b], ls=V.LINESTYLES[b % 5])
axes[0].legend(loc="best"); V.lab(axes[0], "T [K]", "density [kg/m3]", "(a) NaCl, P <= 100 bar")
w = nacl[nacl.m.between(0.9, 1.1)]
V.isotherms(axes[1], w, x="P_bar", y="value", logx=False, logy=False, legend=True); V.lab(axes[1], "P [bar]", "density [kg/m3]", "(b) NaCl, 0.9-1.1 mol/kg")
for k, s in enumerate(["Cl-Ca", "Cl-Mg", "Na-SO4", "Cl-K", "Mg-SO4"]):
    w = rho[(rho.salt_system == s) & (rho.total_molality.between(2.5, 3.5)) & (rho.P_bar <= 100)]
    if len(w) < 4: continue
    axes[2].scatter(w.T_K, w.value, s=18, color=V.WONG[(k + 1) % 7], marker=V.MARKERS[k], edgecolor="none", alpha=0.75, label=f"{s} (n={len(w)})")
axes[2].legend(); V.lab(axes[2], "T [K]", "density [kg/m3]", "(c) total ion molality 2.5-3.5")
plt.tight_layout(); plt.show()'''),
         md("""## Source-to-source differences in density

At fixed temperature, density against molality for single salts. The difference between sources is far smaller than the signal; the useful
view is the **departure from a smooth trend**, per source, in parts per thousand."""),
         code('''g = nacl[nacl.T_K.between(293, 299) & (nacl.P_bar <= 20)].dropna(subset=["m"])
fig, axes = plt.subplots(1, 2, figsize=(15, 5.3))
V.by_source(axes[0], g, x="m", y="value", top=8, logx=False, logy=False); V.lab(axes[0], "NaCl [mol/kg]", "density [kg/m3]", "(a) NaCl, 293-299 K, P <= 20 bar")
cf = np.polyfit(g.m, g.value, 4)
g = g.assign(dev=(g.value - np.polyval(cf, g.m)) / np.polyval(cf, g.m) * 1000)
for k, (s, w) in enumerate(g.groupby("source")):
    if len(w) < 5: continue
    axes[1].scatter(w.m, w.dev, s=22, color=V.WONG[(k % 6) + 1], marker=V.MARKERS[k % 12], edgecolor="black", linewidth=0.4, alpha=0.8, label=s)
axes[1].axhline(0, color="black", lw=1.4); axes[1].legend(fontsize=8, ncol=2); V.lab(axes[1], "NaCl [mol/kg]", "departure from the pooled quartic fit [0.1 %]", "(b)")
plt.tight_layout(); plt.show()'''),
         md("## Osmotic coefficient"),
         code('''ph = dfp[dfp.property == "phi_osm"]
sysl = [s for s in ph.salt_system.value_counts().index if ph[ph.salt_system == s].shape[0] >= 12][:6]
fig, axes = plt.subplots(2, 3, figsize=(18, 10))
for ax, s in zip(axes.ravel(), sysl):
    g = ph[ph.salt_system == s].copy(); g["m"] = g.total_molality
    V.isotherms(ax, g, x="m", y="value", logx=False, logy=False, edges=[270, 300, 340, 400, 460, 520, 600])
    V.lab(ax, "total ion molality [mol/kg]", "osmotic coefficient", s)
plt.tight_layout(); plt.show()'''),
         md("## Vapour-pressure ratio of brines (water activity)"),
         code('''ps = dfp[dfp.property == "psat_ratio"]
sysl = [s for s in ps.salt_system.value_counts().index if ps[ps.salt_system == s].shape[0] >= 12][:6]
fig, axes = plt.subplots(2, 3, figsize=(18, 10))
for ax, s in zip(axes.ravel(), sysl):
    g = ps[ps.salt_system == s].copy(); g["m"] = g.total_molality
    V.isotherms(ax, g, x="m", y="value", logx=False, logy=False, trend_line=True, edges=[270, 300, 330, 370, 440, 520, 660])
    V.lab(ax, "total ion molality [mol/kg]", "p_sat(brine) / p_sat(water)", s)
plt.tight_layout(); plt.show()'''),
         md("## Apparent molar heat capacity"),
         code('''cp = dfp[dfp.property == "Cp_app"]
print(cp.groupby("source").size().sort_values(ascending=False).to_dict())
sysl = [s for s in cp.salt_system.value_counts().index if cp[cp.salt_system == s].shape[0] >= 10][:4]
fig, axes = plt.subplots(1, len(sysl), figsize=(5.2 * len(sysl), 5.2))
axes = np.atleast_1d(axes)
for ax, s in zip(axes, sysl):
    g = cp[cp.salt_system == s].copy(); g["m"] = g.total_molality
    V.isotherms(ax, g, x="m", y="value", logx=False, logy=False, edges=[270, 290, 310, 340, 400, 500, 620])
    V.lab(ax, "total ion molality [mol/kg]", "apparent molar Cp [J/(K mol)]", s)
plt.tight_layout(); plt.show()'''),
         md("""## Viscosity and the density of CO2-loaded solutions

Both families carry `m_gas`, the dissolved CO2 in mol per kg of water."""),
         code('''v = df[df.property == "visc"]; rg = df[df.property == "rho_gas_loaded"]
fig, axes = plt.subplots(1, 3, figsize=(18, 5.3))
for k, (lab_, g) in enumerate([("brine or water", v[v.gas == ""]), ("CO2-loaded", v[v.gas != ""])]):
    if len(g): axes[0].scatter(g.T_K, g.value, s=32, color=V.WONG[(k + 1) % 7], marker=V.MARKERS[k], edgecolor="black", linewidth=0.5, label=f"{lab_} (n={len(g)})")
axes[0].legend(); V.lab(axes[0], "T [K]", "viscosity [mPa s]", "(a)")
V.isotherms(axes[1], rg, x="P_bar", y="value", logx=False, logy=False); V.lab(axes[1], "P [bar]", "density of CO2-loaded water [kg/m3]", "(b)")
sc = axes[2].scatter(rg.m_gas, rg.value, c=rg.T_K, cmap="plasma", s=26, edgecolor="none"); plt.colorbar(sc, ax=axes[2], label="T [K]")
V.lab(axes[2], "dissolved CO2 [mol/kg water]", "density [kg/m3]", "(c)")
plt.tight_layout(); plt.show()'''),
         md("## Permittivity\n\n`eps_r` is a low-weight extension family (13 rows, 298 K, one source)."),
         code('display(df[df.property == "eps_r"][["source", "T_K", "P_bar", "m_Na", "m_Cl", "value", "uncertainty"]])')]
    return c


def nb05():
    c = [md("""# 5. Uncertainty and variance across datasets

Three kinds of uncertainty can be read from this database:

1. the **stated** uncertainty of a source (where there is one);
2. the **empirical** scatter between independent sources that measured the same property at about the same conditions
   (`data/consensus/`); and
3. the **quality code** (R, T, U), which records whether independent sources agree.

Stated uncertainties exist for only part of the data and describe repeatability within a laboratory; the scatter between laboratories is
usually larger. Both are shown. How the consensus statistic is defined, and its limits, is in `data/consensus/README.md`."""),
         code(SETUP),
         code('''rows = pd.read_csv(ROOT / "data" / "consensus" / "consensus_rows.csv")
bysrc = pd.read_csv(ROOT / "data" / "consensus" / "consensus_by_source.csv")
rows["outlier"] = rows.consensus_outlier.astype(str) == "True"
print(f"{len(rows):,} rows have at least one independent comparator ({len(rows) / len(df):.0%} of the default view)")'''),
         md("## Stated uncertainties"),
         code('''has = dfall.groupby("family").apply(lambda g: g.uncertainty.notna().mean()).sort_values()
u = dfall[dfall.uncertainty.notna() & (dfall.value != 0)].copy()
u["rel"] = (u.uncertainty / u.value.abs()).clip(lower=1e-5)
fig, axes = plt.subplots(1, 2, figsize=(15, 5.2))
axes[0].barh(has.index, has.values * 100, color="#56B4E9", edgecolor="black", linewidth=1.4, hatch="//")
V.lab(axes[0], "rows with a stated uncertainty [%]", "", "(a)")
for k, (p, g) in enumerate([("solubility_molality", u[u.property == "solubility_molality"]), ("y_h2o", u[u.property == "y_h2o"]), ("rho", u[u.property == "rho"]), ("phi_osm", u[u.property == "phi_osm"]), ("Cp_app", u[u.property == "Cp_app"])]):
    if len(g) < 5: continue
    x = np.sort(g.rel.values * 100)
    axes[1].plot(x, np.arange(1, len(x) + 1) / len(x), color=V.WONG[k % 7], ls=V.LINESTYLES[k % 5], label=f"{p} (n={len(g)})")
axes[1].set_xscale("log"); axes[1].legend(loc="lower right"); V.lab(axes[1], "stated relative uncertainty [%]", "cumulative share", "(b)")
plt.tight_layout(); plt.show()'''),
         md("""## Disagreement between independent sources

`rel_dev` is the signed relative difference between a row and the median of the other sources at about the same state (strict
tolerances: 1 K, 2 % in pressure and molalities); `rel_dev_smooth` comes from a leave-one-source-out local fit and covers more rows."""),
         code('''fig, axes = plt.subplots(2, 2, figsize=(16, 10))
for ax, (p, lab_) in zip(axes.ravel(), [("solubility_molality", "gas solubility"), ("y_h2o", "water in gas"), ("psat_ratio", "p_sat ratio"), ("rho", "brine density")]):
    g = rows[rows.property == p]
    for k, (c, name, ls) in enumerate([("rel_dev", "strict", "-"), ("rel_dev_smooth", "smooth", "--")]):
        x = g[c].dropna() * 100
        if len(x) < 10: continue
        lim = 60 if p in ("solubility_molality", "y_h2o") else 12
        ax.hist(x.clip(-lim, lim), bins=np.linspace(-lim, lim, 61), histtype="step", lw=2.4, ls=ls, color=V.WONG[k + 2], label=f"{name} (n={len(x)}, robust scale {1.4826 * np.median(np.abs(x - np.median(x))):.2g} %)")
    ax.axvline(0, color="black", lw=1.4); ax.legend(loc="upper right", fontsize=9.5); V.lab(ax, "deviation from the other sources [%]", "rows", lab_)
plt.tight_layout(); plt.show()'''),
         md("""## Does the disagreement depend on temperature, pressure, salinity?

Absolute deviation of gas-solubility rows from the consensus, with the median in bins. Disagreement that grows with a variable points to
a regime where the methods diverge (near the critical point, at high pressure, at high salinity)."""),
         code('''g = rows[(rows.property == "solubility_molality")].copy()
g["dev"] = g.rel_dev_smooth.fillna(g.rel_dev).abs() * 100
g["I"] = (g[["m_Na", "m_K", "m_Cl"]].sum(axis=1) + 3 * (g.m_Ca + g.m_Mg) + 2 * g.m_SO4) / 2
fig, axes = plt.subplots(1, 3, figsize=(19, 5.3))
for ax, (x, lab_, logx) in zip(axes, [("T_K", "T [K]", False), ("P_bar", "P [bar]", True), ("I", "ionic strength [mol/kg]", False)]):
    for k, gas in enumerate(["co2", "ch4", "h2", "n2", "o2"]):
        w = g[g.gas == gas]
        ax.scatter(w[x], w.dev.clip(lower=0.05), s=12, color=V.WONG[(k + 1) % 7], marker=V.MARKERS[k], alpha=0.45, edgecolor="none", label=gas if x == "T_K" else None)
    tx, tm, tlo, thi = V.qtrend(g[x], g.dev, nbins=9)
    if len(tx):
        ax.fill_between(tx, tlo, thi, color="black", alpha=0.18, label="quartiles" if x == "T_K" else None)
        ax.plot(tx, tm, color="black", lw=3, label="median" if x == "T_K" else None)
    ax.set_yscale("log");
    if logx: ax.set_xscale("log")
    V.lab(ax, lab_, "|deviation| [%]")
axes[0].legend(ncol=2, fontsize=9.5)
plt.tight_layout(); plt.show()'''),
         md("""## How far is each source from the others?

Median deviation of each source (sources with at least ten compared rows); the horizontal bar is the robust scatter of that source's own deviations.
A source on the zero line agrees with its neighbours on average; one far from it has a calibration, method or basis difference that a
user should know about. Marker shape separates the property families."""),
         code('''t = bysrc[(bysrc.smooth_n_compared >= 10) | (bysrc.strict_n_compared >= 10)].copy()
t["bias"] = t.smooth_bias_median.fillna(t.strict_bias_median) * 100
t["scale"] = t.smooth_scale_mad.fillna(t.strict_scale_mad) * 100
t = t.sort_values("bias").reset_index(drop=True)
fig, ax = plt.subplots(figsize=(8, 0.2 * len(t) + 2))
fm = {"solubility": ("o", "#000000"), "y_h2o": ("s", "#E69F00"), "psat_ratio": ("^", "#56B4E9"), "rho": ("D", "#009E73"), "thermo_brine": ("v", "#D55E00"), "dh_sol": ("P", "#CC79A7")}
for i, r in t.iterrows():
    m, c = fm.get(r.family, ("o", "gray"))
    ax.errorbar(r.bias, i, xerr=r.scale, fmt=m, color=c, mec="black", ms=7, elinewidth=1.2, capsize=2)
ax.set_yticks(range(len(t))); ax.set_yticklabels(t.source, fontsize=8); ax.axvline(0, color="black", lw=1.5); ax.axvline(-5, color="gray", ls=":"); ax.axvline(5, color="gray", ls=":")
ax.set_xlim(-60, 60)
from matplotlib.lines import Line2D
ax.legend(handles=[Line2D([], [], marker=m, color=c, mec="black", ls="", label=f) for f, (m, c) in fm.items() if f in set(t.family)], loc="lower right", fontsize=9)
V.lab(ax, "median deviation of the source [%]", ""); plt.tight_layout(); plt.show()'''),
         md("""## Variance across datasets at one state

States of pure-water CO2 solubility that several independent sources measured within 1 K and 2 % in pressure. For each state, the values
of the sources relative to their median: the vertical spread at a state is the between-laboratory variance, the horizontal line the median."""),
         code('''s = df[(df.property == "solubility_molality") & (df.gas == "co2") & (df.total_molality == 0)].copy()
s["src"] = s.source
best = []
for i, r in s.iterrows():
    w = s[(abs(s.T_K - r.T_K) <= 1) & (abs(s.P_bar - r.P_bar) <= 0.02 * r.P_bar)]
    best.append((w.src.nunique(), r.T_K, r.P_bar))
best = pd.DataFrame(best, columns=["n", "T", "P"]).sort_values("n", ascending=False).drop_duplicates(["T", "P"])
chosen = []
for _, r in best.iterrows():
    if all(abs(r["T"] - c["T"]) > 4 or abs(r["P"] - c["P"]) > 0.15 * c["P"] for c in chosen): chosen.append(r)
    if len(chosen) == 6: break
fig, axes = plt.subplots(2, 3, figsize=(18, 9.5))
for ax, r in zip(axes.ravel(), chosen):
    w = s[(abs(s.T_K - r["T"]) <= 1) & (abs(s.P_bar - r["P"]) <= 0.02 * r["P"])]
    med = w.groupby("src").value.median(); ref = med.median()
    names = list(med.sort_values().index)
    for k, n in enumerate(names):
        v = w[w.src == n]
        ax.scatter([k] * len(v), v.value / ref, s=60, color=V.WONG[(k % 6) + 1], marker=V.MARKERS[k % 12], edgecolor="black", linewidth=0.7)
    ax.axhline(1, color="black", lw=1.5)
    ax.set_xticks(range(len(names))); ax.set_xticklabels(names, rotation=70, ha="right", fontsize=8.5)
    V.lab(ax, "", "value / median of sources", f"{r['T']:.0f} K, {r['P']:.0f} bar: {len(names)} sources, sd {np.std(med / ref, ddof=1) * 100:.1f} %")
plt.tight_layout(); plt.show()'''),
         md("## Quality codes against deviation"),
         code('''d = rows.copy()
d["dev"] = d.rel_dev.fillna(d.rel_dev_smooth).abs() * 100
d = d.merge(dfall.groupby(["dataset_id"]).quality.agg(lambda x: x.mode().iloc[0]).rename("q"), left_on="dataset_id", right_index=True, how="left")
fig, ax = plt.subplots(figsize=(8, 5))
for k, q in enumerate(["R", "T", "U"]):
    x = np.sort(d[d.q == q].dev.dropna());
    if len(x): ax.plot(np.clip(x, 0.02, None), np.arange(1, len(x) + 1) / len(x), color=V.WONG[[3, 0, 4][k]], ls=V.LINESTYLES[k], label=f"{q} (n={len(x)})")
ax.set_xscale("log"); ax.legend(); V.lab(ax, "|deviation from other sources| [%]", "cumulative share"); plt.show()'''),
         md("## The rows that still disagree most\n\nListed, not removed: the disagreement is a property of the literature."),
         code('''o = rows[rows.outlier].copy(); o["dev"] = o.rel_dev_smooth.fillna(o.rel_dev)
display(o.reindex(o.dev.abs().sort_values(ascending=False).index).head(25)[["source", "dataset_id", "gas", "property", "T_K", "P_bar", "value", "reference", "ref_smooth", "dev", "n_other_sources", "n_other_smooth"]].round(4))
print(o.groupby("source").size().sort_values(ascending=False).head(12).to_dict())''')]
    return c


def nb06():
    c = [md("""# 6. The supplementary tier

`supplementary/supplementary_measurements.csv` holds measurements that the benchmark families cannot store without a model, an assumed
density or an assumed pressure: apparent molar volumes, enthalpies of dilution, isopiestic pairs, Ostwald and Bunsen coefficients, and so on.
Values are as printed, in the unit of the paper; read `value_what` before using a class. This notebook shows what is there."""),
         code(SETUP),
         code('''s = pd.read_csv(ROOT / "supplementary" / "supplementary_measurements.csv", keep_default_na=False)
for c in ["T_K", "P_bar", "value", "value2", "uncertainty"]:
    s[c] = pd.to_numeric(s[c], errors="coerce")
cls = s.groupby("property_class").agg(rows=("value", "size"), tables=("dataset_id", "nunique"), sources=("source", "nunique"), T_min=("T_K", "min"), T_max=("T_K", "max")).sort_values("rows", ascending=False)
display(cls.round(1))
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.barh(cls.index[::-1], cls.rows[::-1], color="#56B4E9", edgecolor="black", linewidth=1.4, hatch="//"); V.lab(ax, "rows", ""); plt.show()'''),
         md("""## Isopiestic pairs

Molality of a test solution against the molality of the reference salt (NaCl or KCl) in equilibrium with it, as printed. The osmotic
coefficient follows from the pair and a reference model; we leave that choice to the user."""),
         code('''iso = s[s.property_class == "isopiestic_pair"].copy()
iso = iso[iso.value2.notna() & (iso.value > 0) & (iso.value2 > 0)]
iso["ref"] = iso.reference_salt.replace("", "?")
fig, ax = plt.subplots(figsize=(8, 7))
for k, (r, g) in enumerate(iso.groupby("ref")):
    ax.scatter(g.value, g.value2, s=14, color=V.WONG[(k + 1) % 7], marker=V.MARKERS[k], alpha=0.6, edgecolor="none", label=f"reference {r} (n={len(g)})")
ax.plot([0, 12], [0, 12], color="black", ls=":"); ax.legend(); V.lab(ax, "test solution [mol/kg water]", "reference salt [mol/kg water]"); plt.show()
print(iso.groupby("source").size().sort_values(ascending=False).head(10).to_dict())'''),
         md("## Apparent molar volumes"),
         code('''pv = s[s.property_class == "apparent_molar_volume"].copy()
print(pv.groupby("source").size().sort_values(ascending=False).to_dict())
g = pv[pv.solutes_mol_per_kg_water != ""].copy()
g["salt"] = g.solutes_mol_per_kg_water.str.split(":").str[0]
g["m"] = pd.to_numeric(g.solutes_mol_per_kg_water.str.split(":").str[1].str.split(";").str[0], errors="coerce")
fig, ax = plt.subplots(figsize=(9, 6))
for k, (salt, w) in enumerate(g[g.value_unit == "cm3/mol"].groupby("salt")):
    if len(w) < 10: continue
    ax.scatter(np.sqrt(w.m), w.value, s=14, color=V.WONG[(k + 1) % 7], marker=V.MARKERS[k % 12], alpha=0.6, edgecolor="none", label=f"{salt} (n={len(w)})")
ax.legend(ncol=2, fontsize=9); V.lab(ax, "sqrt(molality) [sqrt(mol/kg)]", "apparent molar volume [cm3/mol]"); plt.show()'''),
         md("## Enthalpy of dilution and gas-solubility coefficients"),
         code('''fig, axes = plt.subplots(1, 2, figsize=(15, 5.2))
e = s[s.property_class == "enthalpy_of_dilution"]
for k, (src, w) in enumerate(e.groupby("source")):
    axes[0].scatter(w.T_K, w.value, s=18, color=V.WONG[(k + 1) % 7], marker=V.MARKERS[k], alpha=0.7, edgecolor="none", label=f"{src} [{w.value_unit.iloc[0]}]")
axes[0].legend(fontsize=8.5); V.lab(axes[0], "T [K]", "value as printed", "(a) enthalpy of dilution")
c = s[s.property_class == "gas_solubility_coefficient"]
for k, (g, w) in enumerate(c.groupby("gas")):
    axes[1].scatter(w.T_K, w.value, s=14, color=V.WONG[(k + 1) % 7], marker=V.MARKERS[k % 12], alpha=0.6, edgecolor="none", label=f"{g} (n={len(w)})")
axes[1].set_yscale("log"); axes[1].legend(ncol=2, fontsize=8.5); V.lab(axes[1], "T [K]", "Ostwald or Bunsen coefficient as printed", "(b)")
plt.tight_layout(); plt.show()''')]
    return c


NOTEBOOKS = [("01_overview_and_coverage", nb01), ("02_gas_solubility", nb02), ("03_water_content_mixtures_enthalpy", nb03),
             ("04_brine_properties", nb04), ("05_uncertainty_and_variance", nb05), ("06_supplementary_tier", nb06)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-exec", action="store_true")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--out", help="write the notebooks here instead of notebooks/ (the CI run does this to leave the tree clean)")
    a = ap.parse_args()
    outdir = pathlib.Path(a.out) if a.out else NB
    outdir.mkdir(parents=True, exist_ok=True)
    for name, fn in NOTEBOOKS:
        if a.only and not any(o in name for o in a.only):
            continue
        cells = fn()
        # badge under the title, a note on Colab, and the bootstrap cell before everything else
        head = cells[0].source.split("\n", 1)
        cells[0].source = head[0] + "\n\n" + BADGE.format(repo=GITHUB, name=name) + "\n\n" + (head[1] if len(head) > 1 else "") + "\n\n" + COLAB_NOTE
        cells.insert(1, code(BOOTSTRAP))
        nb = new_notebook(cells=cells, metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}})
        path = outdir / f"{name}.ipynb"
        if not a.no_exec:
            from nbconvert.preprocessors import ExecutePreprocessor
            ExecutePreprocessor(timeout=900, kernel_name="python3").preprocess(nb, {"metadata": {"path": str(NB)}})
        nbf.write(nb, path)
        print("wrote", path.name, f"{path.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    sys.exit(main())
