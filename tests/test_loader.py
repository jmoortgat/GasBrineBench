"""The loader: discovery, typing conventions, and the lle-regime default."""

from __future__ import annotations

import math

import pandas as pd
import pytest

import gasbrinebench as gbb
from gasbrinebench.vocab import COLUMNS, IONS


def test_data_dir_found(repo_root):
    assert gbb.data_dir() == repo_root / "data"


def test_available_families_are_the_seven_csvs(repo_root):
    fams = gbb.available_families()
    on_disk = sorted(p.stem for p in (repo_root / "data").glob("*.csv"))
    assert sorted(fams) == on_disk
    assert fams[0] == "solubility"


def test_schema_columns_present_and_ordered():
    df = gbb.load_family("solubility")
    assert list(df.columns)[: len(COLUMNS)] == COLUMNS


def test_gas_column_is_empty_string_not_nan():
    """SCHEMA.md: the gas cell is legitimately empty for brine-only rows."""
    rho = gbb.load_family("rho")
    assert (rho["gas"] == "").all()
    assert not rho["gas"].isna().any()


def test_blank_pressure_becomes_nan_only_for_psat_ratio(all_rows):
    blank = all_rows["P_bar"].isna()
    assert set(all_rows.loc[blank, "property"]) == {"psat_ratio"}
    assert blank.sum() == 21


def test_numeric_columns_are_numeric(all_rows):
    for col in ["T_K", "P_bar", "value", "uncertainty", *IONS]:
        assert pd.api.types.is_numeric_dtype(all_rows[col]), col


def test_row_totals_match_the_repository_readme(all_rows):
    assert len(all_rows) == 5846
    per_family = all_rows["family"].value_counts().to_dict()
    assert per_family == {
        "solubility": 3783,
        "y_h2o": 1001,
        "rho": 905,
        "phi_osm": 101,
        "dh_sol": 22,
        "psat_ratio": 21,
        "eps_r": 13,
    }


def test_lle_regime_excluded_by_default(default_rows, all_rows):
    """The default that matters: 144 propane rows are not gas solubilities."""
    assert "lle-regime" not in set(default_rows["tag"])
    assert len(all_rows) - len(default_rows) == 144
    dropped = all_rows[all_rows["tag"] == "lle-regime"]
    assert set(dropped["gas"]) == {"c3h8"}


def test_exclude_tags_none_keeps_everything():
    assert len(gbb.load(exclude_tags=None)) == 5846
    assert len(gbb.load(exclude_tags=())) == 5846


def test_derived_columns_attached_by_default(default_rows):
    for col in ("ionic_strength", "total_molality", "salt_system",
                "salt_system_kind"):
        assert col in default_rows.columns
    assert "ionic_strength" not in gbb.load(derive=False).columns


def test_load_accepts_a_list_of_families():
    df = gbb.load(["rho", "eps_r"])
    assert set(df["family"]) == {"rho", "eps_r"}


def test_load_forwards_filters():
    a = gbb.load("solubility", gas="co2")
    b = gbb.select(gbb.load("solubility"), gas="co2")
    assert len(a) == len(b) > 0


def test_unknown_family_lists_the_known_ones():
    with pytest.raises(ValueError, match="solubility"):
        gbb.load_family("solubilty")


def test_missing_data_dir_names_what_it_tried(tmp_path, monkeypatch):
    monkeypatch.setenv(gbb.loader.DATA_DIR_ENV, str(tmp_path))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        gbb.loader, "_looks_like_data_dir", lambda p: False
    )
    with pytest.raises(FileNotFoundError, match="GASBRINEBENCH_DATA"):
        gbb.data_dir()


def test_uncertainty_blank_is_nan_not_zero(all_rows):
    """A stated uncertainty of zero and no stated uncertainty differ."""
    assert all_rows["uncertainty"].isna().any()
    stated = all_rows["uncertainty"].dropna()
    assert (stated >= 0).all()
    assert math.isfinite(stated.max())
