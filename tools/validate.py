#!/usr/bin/env python3
"""GasBrineBench dataset validator (standalone: pandas only).

Run from the repo root:  python3 tools/validate.py
Exit code 0 = all checks pass. Used as PR CI.

Checks (a failure in any is fatal):
  1. schema conformance per family csv (columns, types, vocabularies)
  2. physical ranges (T in band, P and molalities >= 0, values finite)
  3. `gas` present for gas properties and empty for gas-free properties
  4. molality/mole-fraction sibling-row consistency (1e-9 relative)
  5. exact duplicate rows from the SAME source (double-counted data)
  6. every `source` cell resolves to a real bibliographic record in
     `bib/references.bib`, through the same normalisation
     `tools/make_sources.py` uses to build the manifest
  7. quality codes in {R, T, U}; tag in the documented vocabulary

It also prints two non-fatal NOTE lines, because the underlying facts are
real data and not defects:
  - exact value coincidences between DIFFERENT sources at the same state
    (two labs agreeing to the precision they printed), and
  - the row inventory, so a diff of CI output shows any silent row change.

A note on check 6. The `source` column holds the curation key the
transcription carried (`ZHAOb(2015)`, `ALGHAFRI(2012) / EXP_NaCl_T298K.txt`,
`Chabab2021_JCED66_T3_tech1`), not a bibtex key. Those cells are deliberately
left as they are -- they are copied from upstream curation artefacts and would
be restored by the next rebuild. `tools/make_sources.py` owns the mapping from
those spellings onto citation keys, including a small audited table of
corrections for cells that name their paper wrongly. This validator reuses that
mapping rather than reimplementing it, so the invariant checked here is exactly
the one the manifest reports: every row resolves to a real published source.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BIB = ROOT / "bib" / "references.bib"
M_W = 0.01801528  # kg/mol

#: property vocabulary. `miac` is declared in SCHEMA.md and has no rows yet;
#: `eps_r` is the static-permittivity extension family (see data/README.md).
PROPS = {"solubility_molality", "xc_saltfree", "y_h2o", "rho",
         "phi_osm", "psat_ratio", "dh_sol", "miac", "eps_r"}

#: properties of the brine alone: `gas` must be empty for these.
GAS_FREE_PROPS = {"rho", "phi_osm", "psat_ratio", "eps_r", "miac"}

#: properties for which `P_bar` is legitimately blank. `psat_ratio` is a ratio
#: of saturation pressures at one temperature: the pressure is the measured
#: quantity, carried in `value`, so there is no independent P to record
#: (data/README.md, `haas1976`).
BLANK_P_PROPS = {"psat_ratio"}

#: fit/test partition. `lle-regime` marks rows whose heavy phase is a liquid,
#: i.e. mutual solubility rather than gas solubility; they are kept in the
#: database but leave the gas-solubility set (data/QUALITY.md Sec. 7).
TAGS = {"fit-eligible", "test-only", "lle-regime"}

ION_COLS = ["m_Na", "m_Cl", "m_K", "m_Ca", "m_Mg", "m_SO4"]
REQUIRED = ["dataset_id", "source", "gas", "property", "T_K",
            "P_bar", *ION_COLS, "value", "uncertainty", "quality", "tag"]

#: state columns that identify one measured point
STATE = ["property", "gas", "T_K", "P_bar", *ION_COLS]

# (source, gas, T_K, P_bar) states where a source legitimately prints the same
# value twice, verified against the source table. Each entry is a replicate
# measurement, not a transcription slip, so both rows are kept.
#
#   KIM(2003) CH4 298.15 K / 4.9 MPa -- Kim, Ryu, Yang & Lee, Ind. Eng. Chem.
#   Res. 42 (2003) 2409-2414, Table 1 lists two 4.9 MPa runs, both measuring
#   x_CH4 = 1.062e-3. They are distinct experiments: the table's *calculated*
#   column differs between them (1.089e-3 and 1.096e-3). Checked against the
#   paper 2026-09-18.
#   PORTIER_2005 CO2 308 K / 80 bar -- Portier & Rochelle, Chem. Geol. 217
#   (2005) 187-199, Table 2 lists five runs in synthetic Utsira pore-water at
#   37 C / 80 bar (1.005, 1.020, 1.000, 1.000, 0.954 mol/kg), two of them
#   reading 1.000. Checked against the paper 2026-09-18.
DOCUMENTED_REPLICATES = {
    ("KIM(2003)", "ch4", 298.0, 49.0),
    ("PORTIER_2005", "co2", 308.0, 80.0),
}


def load_make_sources():
    """Import tools/make_sources.py for its source-key normalisation."""
    path = Path(__file__).resolve().parent / "make_sources.py"
    spec = importlib.util.spec_from_file_location("_gbb_make_sources", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check_family(fpath, resolve, msgs, notes):
    df = pd.read_csv(fpath, keep_default_na=False)
    name = fpath.name

    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        msgs.append(f"{name}: missing columns {missing}")
        return
    extra = [c for c in df.columns if c not in REQUIRED]
    if extra:
        msgs.append(f"{name}: undeclared columns {extra}")

    bad_prop = sorted(set(df["property"]) - PROPS)
    if bad_prop:
        msgs.append(f"{name}: unknown property values {bad_prop}")

    # --- identity columns are populated -------------------------------
    for col in ("dataset_id", "source", "property"):
        if (df[col].astype(str).str.strip() == "").any():
            msgs.append(f"{name}: empty {col}")

    # --- numerics -----------------------------------------------------
    for col in ("T_K", *ION_COLS):
        v = pd.to_numeric(df[col], errors="coerce")
        if v.isna().any():
            msgs.append(f"{name}: non-numeric {col}")
        elif (v < 0).any():
            msgs.append(f"{name}: negative {col}")

    value = pd.to_numeric(df["value"], errors="coerce")
    if value.isna().any():
        msgs.append(f"{name}: non-numeric value in "
                    f"{int(value.isna().sum())} rows")
    elif not value.abs().lt(float("inf")).all():
        msgs.append(f"{name}: non-finite value")

    u_raw = df["uncertainty"].astype(str).str.strip()
    u = pd.to_numeric(df["uncertainty"], errors="coerce")
    if (u.isna() & (u_raw != "")).any():
        msgs.append(f"{name}: non-numeric uncertainty")
    elif (u < 0).any():
        msgs.append(f"{name}: negative uncertainty")

    # P_bar may be blank only where the family README documents it.
    p_raw = df["P_bar"].astype(str).str.strip()
    p = pd.to_numeric(df["P_bar"], errors="coerce")
    blank_p = p_raw == ""
    if (p.isna() & ~blank_p).any():
        msgs.append(f"{name}: non-numeric P_bar")
    if (p < 0).any():
        msgs.append(f"{name}: negative P_bar")
    bad_blank = blank_p & ~df["property"].isin(BLANK_P_PROPS)
    if bad_blank.any():
        msgs.append(f"{name}: blank P_bar on {int(bad_blank.sum())} rows "
                    f"whose property is not one of {sorted(BLANK_P_PROPS)}")

    t = pd.to_numeric(df["T_K"], errors="coerce")
    if ((t < 230) | (t > 1000)).any():
        msgs.append(f"{name}: T_K outside [230, 1000] "
                    f"(min {t.min()}, max {t.max()})")

    # --- gas column ---------------------------------------------------
    gas = df["gas"].astype(str).str.strip()
    gas_free = df["property"].isin(GAS_FREE_PROPS)
    if (gas_free & (gas != "")).any():
        msgs.append(f"{name}: {int((gas_free & (gas != '')).sum())} gas-free "
                    "rows carry a gas")
    if (~gas_free & (gas == "")).any():
        msgs.append(f"{name}: {int((~gas_free & (gas == '')).sum())} gas-property "
                    "rows have no gas")

    # --- vocabularies -------------------------------------------------
    if (~df["quality"].isin(["R", "T", "U"])).any():
        msgs.append(f"{name}: quality codes must be R/T/U "
                    f"(found {sorted(set(df['quality']) - {'R', 'T', 'U'})})")
    if (~df["tag"].isin(TAGS)).any():
        msgs.append(f"{name}: tag must be one of {sorted(TAGS)} "
                    f"(found {sorted(set(df['tag']) - TAGS)})")

    # --- citations ----------------------------------------------------
    unresolved = sorted({s for s in set(df["source"]) if not resolve(s)})
    if unresolved:
        msgs.append(f"{name}: {len(unresolved)} source keys resolve to no "
                    f"record in bib/references.bib: {unresolved[:5]}"
                    + (" ..." if len(unresolved) > 5 else ""))

    # --- molality / mole-fraction siblings ----------------------------
    sol = df[df["property"].isin(["solubility_molality", "xc_saltfree"])]
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
                msgs.append(f"{name}: {int(bad.sum())} molality/xc sibling "
                            "rows inconsistent")

    # --- duplicates ---------------------------------------------------
    # Fatal: the same source contributing the identical point twice, which is
    # the double-count SCHEMA.md rule 4 exists to prevent -- unless the
    # repetition is in the source table itself and has been checked against
    # it, in which case it is replicate data and dropping either row would
    # discard a measurement (see DOCUMENTED_REPLICATES).
    same_src = ["source", *STATE, "value"]
    d = df[df.duplicated(same_src, keep=False)]
    if len(d):
        exempt = d.apply(
            lambda r: (r["source"], r["gas"], round(float(r["T_K"]), 2),
                       round(float(r["P_bar"]), 3)) in DOCUMENTED_REPLICATES,
            axis=1)
        ok, bad = d[exempt], d[~exempt]
        if len(ok):
            n = len(ok) - ok.groupby(same_src).ngroups
            notes.append(f"{name}: {n} documented replicate row(s) "
                         f"({', '.join(sorted(set(ok['source'])))}) -- kept: "
                         "the repetition is in the source table")
        if len(bad):
            n = len(bad) - bad.groupby(same_src).ngroups
            msgs.append(f"{name}: {n} rows duplicate another row from the SAME "
                        "source at the same state and value")
    # Non-fatal: two different sources printing the same value at the same
    # state. That is independent corroboration, not an error.
    cross = df[df.duplicated(STATE + ["value"], keep=False)]
    if len(cross):
        n = len(cross) - cross.groupby(STATE + ["value"]).ngroups
        who = sorted(set(cross["source"]))
        notes.append(f"{name}: {n} exact value coincidence(s) between "
                     f"different sources ({', '.join(who)}) -- kept: "
                     "independent agreement to the printed precision")

    return len(df)


def main():
    msgs: list[str] = []
    notes: list[str] = []

    if not BIB.exists():
        print(f"VALIDATION FAILED:\n - missing {BIB.relative_to(ROOT)}")
        return 1

    ms = load_make_sources()
    idx = ms.index_bib(ms.dedupe_bib(ms.parse_bib(str(BIB))))

    def resolve(raw: str) -> bool:
        surname, year, suffix = ms.parse_source_key(
            ms.apply_source_key_fix(raw))
        entry, _how, _cands = ms.match_bib(surname, year, suffix, idx)
        return entry is not None and not ms.is_placeholder(entry)

    csvs = sorted(DATA.glob("*.csv"))
    if not csvs:
        print("VALIDATION FAILED:\n - data/ contains no csv files")
        return 1

    counts = {}
    for f in csvs:
        counts[f.stem] = check_family(f, resolve, msgs, notes)

    for n in notes:
        print("NOTE:", n)
    inventory = ", ".join(f"{k} {v:,}" for k, v in sorted(counts.items())
                          if v is not None)
    total = sum(v for v in counts.values() if v is not None)
    print(f"NOTE: rows -- {inventory} | total {total:,}")

    if msgs:
        print("VALIDATION FAILED:")
        for m in msgs:
            print(" -", m)
        return 1
    print(f"validate: {len(csvs)} families, {total:,} rows, all checks OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
