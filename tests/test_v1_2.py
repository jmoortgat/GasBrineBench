"""The v1.2 additions: new families, flags, provenance, supplementary tier."""

from __future__ import annotations

import pandas as pd
import pytest

import gasbrinebench as gbb
from gasbrinebench import vocab


def test_new_families_load(all_rows):
    for fam, prop in [("rho_gas", "rho_gas_loaded"), ("visc", "visc"), ("thermo_brine", "Cp_app")]:
        sub = all_rows[all_rows["family"] == fam]
        assert len(sub) > 0, fam
        assert set(sub["property"]) == {prop}


def test_gas_loaded_rows_carry_their_loading(all_rows):
    for fam in ("rho_gas", "visc"):
        sub = all_rows[(all_rows["family"] == fam) & (all_rows["gas"] != "")]
        assert sub["m_gas"].notna().all() and (sub["m_gas"] >= 0).all(), fam


def test_default_excluded_flags_are_declared():
    assert set(vocab.DEFAULT_EXCLUDED_FLAGS) <= set(vocab.FLAGS)


def test_every_flag_in_the_data_is_declared(all_rows):
    used = {f for s in all_rows["flags"] for f in s.split(";") if f}
    assert used <= set(vocab.FLAGS)


def test_default_load_has_no_default_excluded_flag(default_rows):
    bad = set(vocab.DEFAULT_EXCLUDED_FLAGS)
    assert not default_rows["flags"].map(lambda f: bool(bad & set(f.split(";")))).any()
    assert not (default_rows["tag"] == "lle-regime").any()


def test_flags_filter_and_exclude(all_rows):
    stp = gbb.select(all_rows, flags="stp-assumed")
    carried = all_rows["flags"].str.contains("stp-assumed")
    assert len(stp) == carried.sum() == 499
    rest = gbb.select(all_rows, exclude_flags="stp-assumed")
    assert len(rest) == len(all_rows) - carried.sum()
    with pytest.raises(ValueError):
        gbb.select(all_rows, flags="stp-assumd")


def test_other_gases_are_selectable_and_flagged(all_rows):
    ar = gbb.select(all_rows, gas="ar")
    assert len(ar) > 0
    assert ar["flags"].str.contains("gas-out-of-scope").all()


def test_no_row_without_a_pressure_unless_flagged(all_rows):
    blank = all_rows["P_bar"].isna() & (all_rows["property"] != "psat_ratio")
    assert all_rows.loc[blank, "flags"].str.contains("pressure-unstated").all()
    # density, density difference and viscosity never go in without a pressure
    assert not all_rows.loc[blank, "property"].isin(["rho", "rho_gas_loaded", "visc"]).any()


def test_provenance_covers_every_new_dataset(repo_root, all_rows):
    prov = pd.read_csv(repo_root / "data" / "provenance" / "provenance_v1_2.csv", keep_default_na=False)
    main = prov[~prov["family"].str.startswith("supplementary")]
    # a v1.2 dataset is any dataset_id that carries a DOI-slug (they contain the DOI with '_')
    new_ids = set(main["dataset_id"])
    assert new_ids <= set(all_rows["dataset_id"])
    got = all_rows[all_rows["dataset_id"].isin(new_ids)].groupby("dataset_id").size()
    want = main.groupby("dataset_id")["rows"].sum()
    assert (got.sort_index() == want.sort_index()).all()


def test_supplementary_file_schema(repo_root):
    s = pd.read_csv(repo_root / "supplementary" / "supplementary_measurements.csv", keep_default_na=False)
    assert len(s) == 5174
    assert pd.to_numeric(s["value"], errors="coerce").notna().all()
    optional_p = {"isopiestic_pair", "enthalpy_of_dilution", "enthalpy_of_dissolution", "water_activity", "heat_capacity"}
    blank = s["P_bar"].astype(str) == ""
    assert s.loc[blank, "property_class"].isin(optional_p).all()
    assert (s["value_unit"] != "").all()


def test_citation_counts_file(repo_root):
    c = pd.read_csv(repo_root / "data" / "provenance" / "citation_counts.csv", keep_default_na=False)
    assert {"doi", "cited_by_openalex", "retrieved"} <= set(c.columns)
    assert c["doi"].is_unique


def test_consensus_files(repo_root, all_rows):
    rows = pd.read_csv(repo_root / "data" / "consensus" / "consensus_rows.csv", keep_default_na=False)
    src = pd.read_csv(repo_root / "data" / "consensus" / "consensus_by_source.csv")
    assert len(rows) > 0 and len(src) > 0
    # row_id is the position in the family CSV of this release
    fam = all_rows.groupby("family").cumcount()
    key = pd.Series(all_rows["dataset_id"].values, index=pd.MultiIndex.from_arrays([all_rows["family"], fam]))
    got = [key.get((f, int(r))) for f, r in zip(rows["family"], rows["row_id"])]
    assert got == list(rows["dataset_id"])
    # no comparison without an independent source
    assert ((pd.to_numeric(rows["n_other_sources"]) > 0) | (pd.to_numeric(rows["n_other_smooth"]) > 0)).all()


def test_audit_status_column_and_filter(repo_root):
    st = pd.read_csv(repo_root / "data" / "provenance" / "audit_status.csv", keep_default_na=False)
    everything = gbb.load(exclude_tags=None, exclude_flags=None)
    assert len(st) == len(everything)
    assert set(everything["audit_status"]) == {"verified", "corrected", "not-verifiable", "residual-difference"}
    ver = gbb.load(exclude_tags=None, exclude_flags=None, audit_status="verified")
    assert len(ver) == int((st["status"] == "verified").sum())
    with pytest.raises(ValueError):
        gbb.load(audit_status="verifed")


def test_reliable_shortcut():
    r = gbb.load(reliable=True)
    d = gbb.load()
    assert 0 < len(r) < len(d)
    assert set(r["audit_status"]) <= {"verified", "corrected"}
    assert (r["quality"] != "U").all()
    bad = {"source-caution", "stp-assumed", "salinity-matrix", "solution-basis-converted"}
    assert not r["flags"].map(lambda f: bool(bad & set(f.split(";")))).any()
    # reliable keeps the default exclusions even when the caller passes exclude_flags=None
    assert len(gbb.load(reliable=True, exclude_flags=None)) == len(r)
    assert len(gbb.load("solubility", gas="co2", reliable=True)) > 1000
