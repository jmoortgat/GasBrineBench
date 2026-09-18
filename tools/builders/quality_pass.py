#!/usr/bin/env python3
"""Data-quality pass on benchmark database v0 (Yang-2022-style, scoped).

Rewrites ``solubility.csv`` in place (backup ``solubility_pre_quality
.csv``), regenerates ``QUALITY.md`` (the ledger) and rebuilds
``benchmark_v0.parquet`` from the edited csvs.  The other five csvs
(rho, phi_osm, psat_ratio, dh_sol, eps_r) are single-provenance
harness/extraction sets with no cross-source overlap; the pass audits
but does not modify them, so no backups are made for them.

Run:
    cd EoS_Benchmark/code && PYTHONPATH=. python3 bench/data/quality_pass.py

Idempotency contract
--------------------
The pass is a pure, deterministic function of the PRE-quality state:

* if the current ``solubility.csv`` is *unprocessed* (detected by the
  presence of the co2_part1/CHABAB(2020) duplicate block), it becomes
  the input and is copied to ``solubility_pre_quality.csv`` (over-
  writing a stale backup: this covers "build_v0.py was rerun");
* otherwise the pass re-runs from the existing backup, so running the
  script twice (or after a partial edit) reproduces byte-identical
  outputs.

Interventions (each carries a ledger entry in QUALITY.md)
---------------------------------------------------------
1. TONG(2013) ion-vector fix (the epcsaft agent's flagged suspect).
   Row co2_part1 / TONG(2013) / 423 K / 126.3 bar has all mi = 0 with
   x_CO2 = 0.0098 -- too low for pure water (Duan/Held give ~0.014-
   0.015 there).  Traced to the curated raw file
   Multi_Salt/source_materials/EoS/CO2/eCPA/MIXED_SALTS/T423K/
   EXP_MgCl3_T423K.txt line 4: ms = 1 mol/kg with the six ion columns
   left 0, while every sibling 1 m row carries (Cl 2, Mg 1).  The
   point is the 1 m MgCl2 / 423 K / 126.3 bar point of Tong, Trusler
   & Vega-Maza 2013 (JCED 58:2116, CO2 in CaCl2/MgCl2 brines) and
   x = 0.0098 interpolates smoothly inside the 1 m isotherm
   (0.0035 @ 39.5 bar -> 0.0131 @ 197.4 bar).  This is a labeling
   artifact of OUR pipeline, not of the source compilation, so the
   fix is: set m_Cl = 2, m_Mg = 1 on both property rows; value kept;
   quality stays T.

2. Duplicate removal.  Two detectors:
   (a) the assignment-tolerance detector -- same gas, T within
       0.05 K, P within 0.5%, every mi within 1%, different
       dataset_id;
   (b) a value-identity detector for re-curated copies whose T was
       ROUNDED in one curation (so (a) misses them): same gas, mi
       within 1%, P within 0.5%, T within 0.5 K and identical
       reported x to all printed digits (rel diff < 1e-6).
   Detector (b) finds the only real duplication in v0: the nine
   co2_part1 "CHABAB(2020)" 6 m NaCl points are digit-identical to
   nine of the fourteen Chabab 2021 JCED 66:609 Table 2 points
   (323.10 K block rounded to 323.0, 373.29/373.39 K rounded to
   373.0).  Removal policy: keep the copy that carries per-point
   experimental uncertainty (chabab2021_t2; full-precision T/P),
   drop the rounded co2_part1 copy (9 points x 2 property rows =
   18 rows).  Because the removed copy was tag=fit-eligible (it was
   a Multi_Salt fit target), the nine kept chabab2021_t2 points are
   retagged fit-eligible so no fitted data masquerades as an
   independent test; the five unmatched 303.55 K points remain
   test-only.

3. Cross-source consistency (solubility only).  Condition-matched
   clusters are built by union-find over pairs from DIFFERENT sources
   with same gas, T within 1.0 K, P within 2%, every mi within 2%
   (chosen: wide enough that independent labs' near-coincident
   isotherm points cluster; narrow enough that the genuine
   P-dependence inside a cluster stays ~2%, well under the 5%
   agreement band).  For each cluster with >= 2 distinct sources:
   * UPGRADE to R when the whole cluster is mutually consistent:
     max relative span (max-min)/median <= 5% -> every clustered row
     (and its xc/molality sibling) gets quality R.  Partially
     agreeing clusters upgrade nothing (conservative: a clique rule
     would let one middle source drag disagreeing neighbours to R).
   * DOWNGRADE to U only when attribution is possible (cluster has
     >= 3 distinct sources): per-source deviation from the cluster
     median > max(3 x cluster spread, 5%) -- the 5% floor keeps the
     rule consistent with the agreement band -- collected per source;
     a source flagged in >= 3 such clusters has those clustered rows
     downgraded.  (On v0 no source meets this bar; KOSCHEL(2006)'s
     systematic -4..-6% low bias at 323 K is reported in the ledger
     but stays T.)

4. Author-flag verification: asserts the Chabab 2021 Table 3 "1*"
   molality-drift block is exactly 10 U rows (5 points x 2 property
   rows) and that no other U rows exist before this pass.

5. Rebuild ``benchmark_v0.parquet`` by concatenating the six csvs in
   the build_v0.py order (solubility, rho, phi_osm, psat_ratio,
   dh_sol, eps_r).

QUALITY.md is regenerated on every run and embeds a machine-readable
LEDGER-COUNTS block that tests/test_data_quality.py checks against
the actual csv/backup deltas.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent            # .../code/bench/data
# Moved into tools/builders/, where `HERE` is no longer the data directory;
# the pass would otherwise read and rewrite a copy beside the script.
DATA_DIR = HERE.parents[1] / "data"               # .../GasBrineBench/data
CODE = HERE.parents[1]
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

COLUMNS = ["dataset_id", "source", "gas", "property", "T_K", "P_bar",
           "m_Na", "m_Cl", "m_K", "m_Ca", "m_Mg", "m_SO4",
           "value", "uncertainty", "quality", "tag"]
ION_COLS = ["m_Na", "m_Cl", "m_K", "m_Ca", "m_Mg", "m_SO4"]
NUM_COLS = ["T_K", "P_bar", "value", "uncertainty"] + ION_COLS

CSV_ORDER = ["solubility.csv", "rho.csv", "phi_osm.csv",
             "psat_ratio.csv", "dh_sol.csv", "eps_r.csv"]

SOL = DATA_DIR / "solubility.csv"
# The pre-quality backup is an internal working artifact, not a
# published family: keep it beside the script so validate.py and
# make_sources.py do not scan it as an eighth csv.
SOL_BAK = HERE / "solubility_pre_quality.csv"
LEDGER = DATA_DIR / "QUALITY.md"

# duplicate detector tolerances (assignment spec)
DUP_T_K = 0.05
DUP_P_REL = 0.005
DUP_MI_REL = 0.01
# rounded-curation value-identity detector
DUPB_T_K = 0.5
DUPB_VAL_REL = 1e-6
# cross-source cluster tolerances (chosen; see docstring)
CL_T_K = 1.0
CL_P_REL = 0.02
CL_MI_REL = 0.02
AGREE_REL = 0.05          # mutual-agreement band -> R
DG_FACTOR = 3.0           # downgrade: dev > 3 x cluster spread ...
DG_FLOOR = 0.05           # ... and > 5% absolute
DG_MIN_CLUSTERS = 3       # ... in >= 3 clusters


def load_csv(path):
    df = pd.read_csv(path, keep_default_na=False)
    for c in NUM_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def write_csv(df, path):
    df[COLUMNS].to_csv(path, index=False, float_format="%.10g")


def is_unprocessed(sol):
    """The co2_part1/CHABAB(2020) duplicate block only exists in the
    pre-quality state."""
    return ((sol.dataset_id == "co2_part1")
            & (sol.source == "CHABAB(2020)")).any()


def _mi_close(a, b, rel):
    return all(abs(x - y) <= rel * max(abs(x), abs(y)) or
               abs(x - y) < 1e-9 for x, y in zip(a, b))


# ------------------------------------------------------------ task 1

def fix_tong(sol, log):
    mask = ((sol.dataset_id == "co2_part1")
            & (sol.source == "TONG(2013)")
            & (np.abs(sol.T_K - 423.0) < 1e-9)
            & (np.abs(sol.P_bar - 126.3) < 1e-9)
            & (sol[ION_COLS].sum(axis=1) == 0))
    n = int(mask.sum())
    assert n == 2, f"expected the 2 TONG rows, found {n}"
    sol.loc[mask, "m_Cl"] = 2.0
    sol.loc[mask, "m_Mg"] = 1.0
    log["ion_fixed"] = sol.loc[mask, ["property", "T_K", "P_bar",
                                      "value"]].copy()
    return sol


# ------------------------------------------------------------ task 2

def _pairs(m, t_tol, p_rel, mi_rel, cross_dataset, same_gas=True):
    """Index pairs of condition-matched molality rows."""
    T = m.T_K.values
    P = m.P_bar.values
    I = m[ION_COLS].values
    G = m.gas.values
    D = m.dataset_id.values
    S = m.source.values
    out = []
    n = len(m)
    order = np.argsort(T, kind="stable")
    for a in range(n):
        i = order[a]
        for b in range(a + 1, n):
            j = order[b]
            if T[j] - T[i] > t_tol:
                break
            if same_gas and G[i] != G[j]:
                continue
            if cross_dataset:
                if D[i] == D[j]:
                    continue
            else:
                if S[i] == S[j]:
                    continue
            if abs(P[i] - P[j]) > p_rel * max(P[i], P[j]):
                continue
            if not _mi_close(I[i], I[j], mi_rel):
                continue
            out.append((i, j))
    return out


def detect_duplicates(sol, log):
    """Both duplicate detectors on the molality rows; returns the
    verified same-measurement pairs (value-identity)."""
    m = sol[sol.property == "solubility_molality"].reset_index()
    strict = _pairs(m, DUP_T_K, DUP_P_REL, DUP_MI_REL,
                    cross_dataset=True)
    log["dup_strict_pairs"] = [
        (m.dataset_id[i], m.source[i], m.dataset_id[j], m.source[j],
         m.T_K[i], m.P_bar[i]) for i, j in strict]

    loose = _pairs(m, DUPB_T_K, DUP_P_REL, DUP_MI_REL,
                   cross_dataset=True)
    ident = [(i, j) for i, j in loose
             if abs(m.value[i] - m.value[j])
             <= DUPB_VAL_REL * max(m.value[i], m.value[j])]
    log["dup_ident_pairs"] = [
        dict(did_a=m.dataset_id[i], src_a=m.source[i],
             T_a=m.T_K[i], P_a=m.P_bar[i],
             did_b=m.dataset_id[j], src_b=m.source[j],
             T_b=m.T_K[j], P_b=m.P_bar[j], value=m.value[i])
        for i, j in ident]
    return m, ident


def remove_duplicates(sol, m, ident, log):
    """Keep the copy with per-point uncertainty (full-precision
    extraction), drop the other (both property rows).  If the removed
    copy was fit-eligible and the kept one test-only, retag the kept
    point fit-eligible."""
    drop_keys, retag_keys = [], []
    for i, j in ident:
        ri, rj = m.loc[i], m.loc[j]
        # keep the row that carries experimental uncertainty
        keep, drop = (ri, rj) if np.isfinite(ri.uncertainty) else \
                     (rj, ri)
        assert np.isfinite(keep.uncertainty) and \
            not np.isfinite(drop.uncertainty), \
            "ambiguous keep/drop -- inspect manually"
        drop_keys.append((drop.dataset_id, drop.source, drop.T_K,
                          drop.P_bar, tuple(drop[ION_COLS])))
        if drop.tag == "fit-eligible" and keep.tag == "test-only":
            retag_keys.append((keep.dataset_id, keep.source, keep.T_K,
                               keep.P_bar, tuple(keep[ION_COLS])))

    def key_mask(df, key):
        did, src, T, P, mi = key
        mk = ((df.dataset_id == did) & (df.source == src)
              & (np.abs(df.T_K - T) < 1e-9)
              & (np.abs(df.P_bar - P) < 1e-9))
        for c, v in zip(ION_COLS, mi):
            mk &= np.abs(df[c] - v) < 1e-9
        return mk

    drop_mask = pd.Series(False, index=sol.index)
    for k in drop_keys:
        drop_mask |= key_mask(sol, k)
    retag_mask = pd.Series(False, index=sol.index)
    for k in retag_keys:
        retag_mask |= key_mask(sol, k)

    log["rows_removed"] = sol.loc[drop_mask, ["dataset_id", "source",
                                              "property", "T_K",
                                              "P_bar", "value"]].copy()
    log["rows_retagged"] = sol.loc[retag_mask, ["dataset_id", "source",
                                                "property", "T_K",
                                                "P_bar"]].copy()
    sol = sol.loc[~drop_mask].copy()
    sol.loc[retag_mask.reindex(sol.index, fill_value=False),
            "tag"] = "fit-eligible"
    return sol.reset_index(drop=True)


# ------------------------------------------------------------ task 3

def cross_source(sol, log):
    """Cluster, report, upgrade mutually-consistent clusters to R,
    downgrade systematically-deviant sources to U (see docstring)."""
    m = sol[sol.property == "solubility_molality"].reset_index()
    pairs = _pairs(m, CL_T_K, CL_P_REL, CL_MI_REL, cross_dataset=False)

    parent = list(range(len(m)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i, j in pairs:
        parent[find(i)] = find(j)
    members = {}
    touched = set(k for p in pairs for k in p)
    for k in touched:
        members.setdefault(find(k), []).append(k)

    clusters = []
    for root in sorted(members):
        idx = sorted(members[root])
        srcs = sorted({m.source[k] for k in idx})
        if len(srcs) < 2:
            continue
        vals = m.value[idx].values
        med = float(np.median(vals))
        span = float((vals.max() - vals.min()) / med)
        clusters.append(dict(idx=idx, sources=srcs, median=med,
                             span=span))

    # ---- upgrades: whole cluster mutually consistent -> R
    up_rows = set()
    for cl in clusters:
        cl["upgrade"] = cl["span"] <= AGREE_REL
        if cl["upgrade"]:
            up_rows.update(m["index"][k] for k in cl["idx"])

    # ---- downgrades: attributable systematic deviants
    flags = {}          # source -> list of (cluster #, dev, spread)
    for ci, cl in enumerate(clusters):
        by_src = {}
        for k in cl["idx"]:
            by_src.setdefault(m.source[k], []).append(m.value[k])
        if len(by_src) < 3:
            continue
        sv = {s: float(np.median(v)) for s, v in by_src.items()}
        med = float(np.median(list(sv.values())))
        devs = {s: abs(v - med) / med for s, v in sv.items()}
        spread = float(np.median(list(devs.values())))
        for s, d in devs.items():
            if d > max(DG_FACTOR * spread, DG_FLOOR):
                flags.setdefault(s, []).append((ci, d, spread))
    down_sources = {s for s, f in flags.items()
                    if len(f) >= DG_MIN_CLUSTERS}
    down_rows = set()
    for s in down_sources:
        for ci, _, _ in flags[s]:
            for k in clusters[ci]["idx"]:
                if m.source[k] == s:
                    down_rows.add(m["index"][k])

    # propagate to xc siblings (same dataset/source/T/P/mi point)
    def sibling_mask(rows):
        mk = pd.Series(False, index=sol.index)
        for ridx in rows:
            r = sol.loc[ridx]
            sib = ((sol.dataset_id == r.dataset_id)
                   & (sol.source == r.source)
                   & (np.abs(sol.T_K - r.T_K) < 1e-9)
                   & (np.abs(sol.P_bar - r.P_bar) < 1e-9))
            for c in ION_COLS:
                sib &= np.abs(sol[c] - r[c]) < 1e-9
            mk |= sib
        return mk

    up_mask = sibling_mask(up_rows) & (sol.quality == "T")
    down_mask = sibling_mask(down_rows) & (sol.quality != "U")
    sol.loc[up_mask, "quality"] = "R"
    sol.loc[down_mask, "quality"] = "U"

    log["clusters"] = [
        dict(sources=cl["sources"], span=cl["span"],
             upgrade=cl["upgrade"], n=len(cl["idx"]),
             rows=[(m.source[k], m.gas[k], float(m.T_K[k]),
                    float(m.P_bar[k]),
                    [float(x) for x in m.loc[k, ION_COLS]],
                    float(m.value[k])) for k in cl["idx"]])
        for cl in clusters]
    log["n_up_rows"] = int(up_mask.sum())
    log["n_down_rows"] = int(down_mask.sum())
    log["down_sources"] = sorted(down_sources)
    log["near_flags"] = {s: f for s, f in flags.items()
                         if s not in down_sources}
    return sol


# ------------------------------------------------------------ task 4

def verify_author_flags(sol_pre):
    """Pre-pass state: the only U rows are (a) the Chabab 2021
    Table 3 '1*' molality-drift block (5 points x 2 property rows)
    and (b) the 5 Umano-1958 rows the IUPAC-Vol-24 transcription
    flagged as probable misprints (build_v0.build_c3h8_umano;
    5 points x 2 property rows)."""
    u = sol_pre[sol_pre.quality == "U"]
    assert len(u) == 20, len(u)
    ch = u[u.dataset_id == "chabab2021_t3"]
    assert len(ch) == 10, len(ch)
    assert (ch.source == "Chabab2021_JCED66_T3_tech1").all()
    assert ((ch.T_K > 372.9) & (ch.T_K < 373.2)).all()
    assert (ch.m_Na == 1.0).all()
    um = u[u.dataset_id == "c3h8_nacl_umano1958"]
    assert len(um) == 10, len(um)
    assert (um.source == "UMANO(1958)").all()


# ------------------------------------------------------------ output

def rebuild_parquet():
    frames = [load_csv(DATA_DIR / n)[COLUMNS] for n in CSV_ORDER]
    combined = pd.concat(frames, ignore_index=True)
    combined.to_parquet(DATA_DIR / "benchmark_v0.parquet", index=False)
    return len(combined)


def write_ledger(log, n_before, n_after, n_parquet):
    ion_fix = log["ion_fixed"]
    removed = log["rows_removed"]
    retag = log["rows_retagged"]
    lines = []
    a = lines.append
    a("# Data-quality ledger (benchmark database v0)")
    a("")
    a("Generated by `bench/data/quality_pass.py` -- edit that script,")
    a("not this file.  Quality codes per Yang et al., IECR 2022,")
    a("61:15576, Sec. 5.2: R = verified against independent data,")
    a("T = tentative (default), U = author-flagged/unverifiable.")
    a("The pass edits `solubility.csv` only (backup:")
    a("`solubility_pre_quality.csv`); the other five csvs are")
    a("single-provenance sets it audits but does not touch.")
    a("If `build_v0.py` is rerun, rerun this pass afterwards.")
    a("")
    a("<!-- LEDGER-COUNTS")
    a(f"solubility_rows_before: {n_before}")
    a(f"solubility_rows_after: {n_after}")
    a(f"rows_removed: {len(removed)}")
    a(f"rows_ion_fixed: {len(ion_fix)}")
    a(f"rows_retagged_fit_eligible: {len(retag)}")
    a(f"rows_upgraded_R: {log['n_up_rows']}")
    a(f"rows_downgraded_U: {log['n_down_rows']}")
    a(f"combined_parquet_rows: {n_parquet}")
    a("-->")
    a("")
    a("## 1. TONG(2013) ion-vector fix (flagged suspect resolved)")
    a("")
    a("Row co2_part1 / TONG(2013) / 423 K / 126.3 bar carried all")
    a("mi = 0 with x_CO2 = 0.0098 (flagged by the epcsaft agent:")
    a("pure-water x_CO2 there is ~0.014-0.015).  Traced to the")
    a("curated raw file `Multi_Salt/source_materials/EoS/CO2/eCPA/")
    a("MIXED_SALTS/T423K/EXP_MgCl3_T423K.txt` line 4: ms = 1 mol/kg")
    a("with the ion columns left 0 while every sibling 1 m row has")
    a("(Cl 2, Mg 1); the same zeros propagated into")
    a("`co2_brines.parquet` row 477.  The point is the 1 m MgCl2 /")
    a("423 K / 126.3 bar point of Tong, Trusler & Vega-Maza 2013")
    a("(JCED 58:2116) and its value interpolates smoothly inside the")
    a("1 m isotherm (0.0035 @ 39.5 bar -> 0.0131 @ 197.4 bar), i.e.")
    a("a labeling artifact of OUR pipeline, not the source.")
    a("FIX: m_Cl = 2, m_Mg = 1 on both property rows; value kept;")
    a("quality stays T.  (The Multi_Salt source files are outside")
    a("this repo and were left untouched.)")
    a("")
    a("## 2. Duplicates")
    a("")
    a(f"Strict detector (same gas, dT<=0.05 K, dP<=0.5%, d(mi)<=1%,")
    a(f"different dataset_id): {len(log['dup_strict_pairs'])} pairs.")
    a("Value-identity detector (dT<=0.5 K for rounded re-curation,")
    a("dP<=0.5%, d(mi)<=1%, identical printed value): "
      f"{len(log['dup_ident_pairs'])} pairs, all between co2_part1")
    a("`CHABAB(2020)` and `chabab2021_t2` -- the Multi_Salt curation")
    a("of the 6 m NaCl CO2 data (rounded T: 323.10->323.0,")
    a("373.29/373.39->373.0) duplicates 9 of the 14 points of")
    a("Chabab et al. 2021, JCED 66:609, Table 2:")
    a("")
    a("| T_a [K] | P_a [bar] | T_b [K] | P_b [bar] | m [mol/kg] |")
    a("|---|---|---|---|---|")
    for p in log["dup_ident_pairs"]:
        a(f"| {p['T_a']:.2f} | {p['P_a']:.3f} | {p['T_b']:.2f} "
          f"| {p['P_b']:.3f} | {p['value']:.6f} |")
    a("")
    a(f"REMOVED: the {len(removed)} rounded co2_part1/CHABAB(2020)")
    a("rows (9 points x 2 property rows; no per-point uncertainty).")
    a("KEPT: the full-precision chabab2021_t2 extraction (exact T,")
    a("stated u(x)).  RETAGGED fit-eligible: the 9 kept points")
    a(f"({len(retag)} rows) -- they were Multi_Salt fit targets via")
    a("the removed copy, so they are NOT an independent test for")
    a("ecpa_ours; the 5 unmatched 303.55 K points stay test-only.")
    a("NOTE for integrator: co2_part1 now has 502 solubility points")
    a("per property (was 511); tests/test_data.py's 511 and 3411")
    a("counts refer to the pre-quality build.")
    a("Same-author blocks checked and found NOT duplicated:")
    a("KOSCHEL(2006) solubility (co2_part1) vs koschel2006 dh_sol")
    a("(different property); TONG(2013) single-salt vs TONG_2013")
    a("mixed-brine (different systems); SANTOS(2021) MgCl2 vs")
    a("dossantos2021_t7 NaCl/Na2SO4 (different systems).")
    a("")
    a("## 3. Cross-source consistency (solubility)")
    a("")
    a("Clusters: union-find over pairs from different sources, same")
    a("gas, dT<=1.0 K, dP<=2%, d(mi)<=2%.  Whole-cluster span")
    a("(max-min)/median <= 5% -> all clustered rows (and xc/molality")
    a("siblings) upgraded R.  Downgrade to U requires >= 3 clusters")
    a("(each with >= 3 sources) in which the source deviates from")
    a("the cluster median by > max(3 x cluster spread, 5%).")
    a("")
    nup = sum(1 for c in log["clusters"] if c["upgrade"])
    a(f"{len(log['clusters'])} clusters ({nup} upgraded to R, "
      f"{log['n_up_rows']} rows incl. siblings; "
      f"{log['n_down_rows']} rows downgraded).")
    a("")
    a("| # | gas | T [K] | P [bar] | system | sources: values "
      "[mol/kg] | span | quality |")
    a("|---|---|---|---|---|---|---|---|")
    for ci, cl in enumerate(log["clusters"]):
        r0 = cl["rows"][0]
        mi = r0[4]
        sys_lbl = "+".join(
            f"{n}={v:g}" for n, v in zip(ION_COLS, mi) if v > 0) \
            or "pure water"
        vals = "; ".join(f"{s}: {v:.4f}"
                         for s, _, _, _, _, v in cl["rows"])
        Ts = sorted({f"{t:.1f}" for _, _, t, _, _, _ in cl["rows"]})
        Ps = sorted({round(p, 0) for _, _, _, p, _, _ in cl["rows"]})
        a(f"| {ci} | {r0[1]} | {'/'.join(Ts)} | "
          f"{'-'.join(str(int(p)) for p in Ps)} | {sys_lbl} | {vals} "
          f"| {cl['span']*100:.1f}% | "
          f"{'R' if cl['upgrade'] else 'T (span > 5%)'} |")
    a("")
    if log["down_sources"]:
        a(f"Downgraded sources: {', '.join(log['down_sources'])}.")
    else:
        a("No source met the downgrade bar.")
    if log["near_flags"]:
        a("Sources flagged in fewer than 3 attributable clusters")
        a("(reported, NOT downgraded):")
        for s, f in sorted(log["near_flags"].items()):
            det = "; ".join(f"cluster {ci}: dev {d*100:.1f}% vs "
                            f"spread {sp*100:.1f}%"
                            for ci, d, sp in f)
            a(f"* {s}: {det}")
    a("")
    a("Narrative finding: KOSCHEL(2006) solubility (a by-product of")
    a("their calorimetric study) runs systematically 4-6% LOW vs")
    a("YAN(2011)/MESSABEB(2016) at 323 K, 1-3 m NaCl, 50-200 bar,")
    a("but never exceeds max(3 x spread, 5%) in >= 3 attributable")
    a("clusters, so it stays T per the conservative rule.")
    a("")
    a("## 4. Known-literature flags (verified, unchanged)")
    a("")
    a("* chabab2021_t3 '1*' block: 5 O2 points (x 2 property rows)")
    a("  at ~373 K / 1 m NaCl, author-flagged molality drift")
    a("  (Chabab 2021 Sec. 4.2 footnote).")
    a("* c3h8_nacl_umano1958: 5 points (x 2 property rows) the")
    a("  IUPAC-Vol-24 transcription flagged as probable misprints")
    a("  (values kept as printed; note column of the raw csv).")
    a("  Both blocks verified: exactly 20 U rows before this pass.")
    a("* koschel2006 dh_sol and haas1976 psat_ratio spot values are")
    a("  asserted against the papers in tests/test_data_quality.py")
    a("  (reusing tests/test_data.py expectations).")
    a("")
    a("## 5. Rebuild")
    a("")
    a(f"benchmark_v0.parquet rebuilt from the six csvs: {n_parquet}")
    a("rows (pre-quality build: 3411).")
    a(YH2O_REVIEW_SECTION)
    a(regime_section(log["sol_final"]))
    LEDGER.write_text("\n".join(lines) + "\n")


def regime_section(sol):
    """Ledger section 7: audit of the phase-regime classification that
    `build_v0.py::_regime_tag` writes into the `tag` column.

    Recomputed here from the shipped csv so the ledger can never drift
    from the data: the counts, temperature/pressure spans and the
    margin to the saturation line are measured, not asserted."""
    from bench.data.build_v0 import HC_PSAT_ANCILLARY, LLE_TAG, \
        hc_psat_bar
    hc = sol[sol.gas.isin(HC_PSAT_ANCILLARY)].copy()
    hc["Psat"] = [hc_psat_bar(g, float(t))
                  for g, t in zip(hc.gas, hc.T_K)]
    hc["ratio"] = hc.P_bar.astype(float) / hc.Psat
    sub = hc[hc.Psat.notna()]
    lle = hc[hc.tag == LLE_TAG]
    out = [
        "",
        "## 7. Phase-regime classification of the hydrocarbon rows",
        "",
        "A solubility point is GAS solubility only if the gas-rich",
        "phase is a gas or a supercritical fluid.  Below a",
        "hydrocarbon's critical temperature and at or above its own",
        "vapor pressure the hydrocarbon-rich phase has condensed, and",
        "the measurement is the liquid--liquid mutual solubility of a",
        "hydrocarbon LIQUID with water: a different equilibrium, and",
        "one that no gas-solubility model in the benchmark claims.",
        "Such rows are tagged `lle-regime` by `build_v0.py`",
        "(`_regime_tag`) and are dropped by the default loaders",
        "(`bench.core.scoring.load_rows`, `bench.core.refit.load_rows`,",
        "via `bench.core.conventions.EXCLUDED_TAGS`); pass",
        "`exclude_tags=()` to score them deliberately.  They are NOT",
        "removed from the database and their quality codes are",
        "unchanged: they are good data about the wrong property.",
        "",
        "Reference line: the vapor-pressure ancillary of the reference",
        "multiparameter EoS (propane Lemmon, McLinden & Wagner 2009,",
        "JCED 54:3141; ethane Bucker & Wagner 2006, JPCRD 35:205),",
        "stated max. deviation 0.016 % / 0.024 % from the EoS",
        "saturation line.  A low-temperature Antoine fit must NOT be",
        "used here: extrapolated above its stated range it misses",
        "propane's saturation pressure by a factor of 4-6 near 273 K",
        "and, being unbounded, reports a 'vapor pressure' above the",
        "critical temperature where no saturation line exists.",
        "",
        "| gas | source | rows | of which lle-regime | T [K] | "
        "P [bar] |",
        "|---|---|---|---|---|---|",
    ]
    for (gas, src), g in hc.groupby(["gas", "source"]):
        n_lle = int((g.tag == LLE_TAG).sum())
        out.append(
            f"| {gas} | {src} | {len(g)} | {n_lle} | "
            f"{g.T_K.astype(float).min():.1f}--"
            f"{g.T_K.astype(float).max():.1f} | "
            f"{g.P_bar.astype(float).min():.3g}--"
            f"{g.P_bar.astype(float).max():.3g} |")
    keep_max = sub[sub.tag != LLE_TAG].ratio.max()
    out += [
        "",
        f"Total tagged `lle-regime`: {len(lle)} rows.  Supercritical",
        "rows (T above the hydrocarbon's critical temperature, where",
        "there is no liquid branch) are NOT tagged --- they stay gas",
        "solubility, exactly as dense-phase CO2 rows do.",
        "",
        "Margin to the saturation line (screen applied to the stored",
        "TOTAL pressure, the conservative reading): the highest",
        f"retained subcritical row sits at P/Psat = {keep_max:.3f} and",
        f"the lowest tagged one at P/Psat = {lle.ratio.min():.3f}, so",
        "no row lands inside the uncertainty of the locus and the",
        "verdict would be identical on hydrocarbon partial pressures.",
        "",
        "Not screened: the four SONG(1994) `y_h2o` rows for each of",
        "C2H6 and C3H8 sit ON the three-phase locus (P/Psat within 1 %",
        "of unity), but they are the G-Lw branch by construction ---",
        "Song & Kobayashi 1994 report the water content of the",
        "GAS-rich phase, and the curation skipped their",
        "liquid-hydrocarbon (L_HC-Lw) rows.  The gas-rich phase is",
        "therefore a vapor and the rows stay `test-only`; what they",
        "test is a model's phase selection at the locus, which is",
        "stated where they are used.",
    ]
    return "\n".join(out)


#: Static ledger section for the y_h2o.csv review-based codes.  The
#: codes themselves are APPLIED by bench/data/build_y_h2o.py
#: (_apply_review_verdicts); this pass does not touch y_h2o.csv.  The
#: text lives here so a ledger regeneration preserves it.
YH2O_REVIEW_SECTION = """
## 6. Water-content family (y_h2o.csv): review-based codes (v0.3)

Applied by `build_y_h2o.py` (this pass does not touch y_h2o.csv).
Two critical sources: Torres et al. 2025 (FPE 589:114259, water-
content review) and Jooss et al. 2026 (FPE 599:114516, SINTEF
CO2/brine measurements).

Code changes (verified by tests/test_data.py):

* Meyer & Harvey CO2 rows (source 'Meyer', 58 rows) T -> R.
  Torres Sec. 2.3: NIST gravimetric hygrometer, systematic
  deviations averaged 0.3%, "significantly smaller than in any
  previous work"; Torres Table 6: agrees with the independent
  Bamberger gravimetric set within 2-6% at 333/353 K.
* CHAPOY(2003) CH4 rows at 283.08 K/60.3 bar and 298.11 K/63.9 bar
  (2 rows) T -> U.  Torres Table 4: independent techniques read
  ~2x higher at matched conditions (Folas 2007 Karl-Fischer 240 vs
  108 ppm at 283 K/60 bar; Barbalho 2024 QCM 964 vs 484 ppm at
  298 K/64 bar).  Torres endorses the GC family's low-pressure
  consistency, so only these two contradicted high-P points move.
* yh2o_co2_nacl_hou2013 rows at 323.15 K (12 rows) T -> U.
  Jooss 2026 Sec. 4.2/Fig. 10: at 50 C and matched salinity the Hou
  2013b water contents imply relative reductions "above 30%, far
  above our upper bound of 14.7%", do not converge to the
  low-pressure Raoult limit, and "may have unreported systematic
  errors".  Every benchmark model also overshoots these rows by
  40-135%.  The 373.15/423.15 K NaCl rows and the whole KCl table
  (same apparatus) have no independent counterpart yet: kept T,
  flagged here as suspect pending replication.

Recorded verdicts WITHOUT code changes:

* DOHRN 323 K/101 bar (0.00547) sits 20% above Bamberger/Briones
  (Torres Table 6, STD 629 ppm) but agrees with DSOUZA (0.00550,
  our cluster-R match): a genuine two-camp disagreement, no
  adjudication -> codes unchanged.
* TODHEIDE 323 K/50 MPa and HOU(2013 binary) 323 K/1.089 MPa are
  called outliers by Jooss 2026 Sec. 4.1 ("should be disregarded"
  for the Hou point); NEITHER point is in our family (Todheide rows
  jump 200 -> 600 bar; Hou binary rows start at 29.8 bar).  The Hou
  binary 323 K rows already carry U from the complement rule.
* Torres Sec. 2: stated accuracies collected for family sources --
  Olds gravimetric <= 2% (author claim, Torres notes "clearly a
  dispersion" vs Culberson & McKetta at 310 K), Yarrison 2-6%,
  Frost GC 3%/2% calibration (Torres: gravimetric Rigby-Prausnitz
  reads considerably LOWER than Frost GC at 323 K, model sides
  with gravimetric -- watch this source), Valtz water calibration
  +/-7% (vapor phase).
* Jooss 2026 also flags Wang et al. (Raman, 120 C, not in family)
  ~60% high, and endorses Gillespie & Wilson at 120 C (not yet in
  family -- acquisition candidate).
"""


def main():
    cur = load_csv(SOL)
    if is_unprocessed(cur):
        # fresh (or rebuilt) v0 -> snapshot it as THE pre-quality state
        write_csv(cur, SOL_BAK)
        sol = cur
    elif SOL_BAK.exists():
        sol = load_csv(SOL_BAK)
        assert is_unprocessed(sol), \
            "backup does not look like a pre-quality build"
    else:
        raise SystemExit("solubility.csv already processed and no "
                         "backup found -- rebuild with build_v0.py "
                         "first")
    n_before = len(sol)
    log = {}

    verify_author_flags(sol)                       # task 4 (pre)
    sol = fix_tong(sol, log)                       # task 1
    m, ident = detect_duplicates(sol, log)         # task 2
    sol = remove_duplicates(sol, m, ident, log)
    sol = cross_source(sol, log)                   # task 3

    write_csv(sol, SOL)
    n_parquet = rebuild_parquet()                  # task 5
    log["sol_final"] = sol
    write_ledger(log, n_before, len(sol), n_parquet)

    print(f"solubility.csv: {n_before} -> {len(sol)} rows "
          f"(removed {len(log['rows_removed'])}, "
          f"ion-fixed {len(log['ion_fixed'])}, "
          f"retagged {len(log['rows_retagged'])}, "
          f"R-upgraded {log['n_up_rows']}, "
          f"U-downgraded {log['n_down_rows']})")
    print(f"benchmark_v0.parquet: {n_parquet} rows")
    print(f"ledger: {LEDGER}")


if __name__ == "__main__":
    main()
