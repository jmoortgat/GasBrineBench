"""The loader: discovery, typing conventions, and the lle-regime default."""

from __future__ import annotations

import math
import re
from pathlib import Path

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
    unstated = all_rows["flags"].str.contains("pressure-unstated")
    # psat_ratio carries the pressure as its value; every other blank is a row whose
    # paper states no pressure, and the builder says so with the flag
    assert set(all_rows.loc[blank & ~unstated, "property"]) == {"psat_ratio"}
    assert blank.sum() == (all_rows["property"] == "psat_ratio").sum() + (blank & unstated & (all_rows["property"] != "psat_ratio")).sum()
    assert (all_rows.loc[unstated, "P_bar"].isna()).all()


def test_numeric_columns_are_numeric(all_rows):
    for col in ["T_K", "P_bar", "value", "uncertainty", *IONS]:
        assert pd.api.types.is_numeric_dtype(all_rows[col]), col


def _readme_row_counts():
    """Per-family and total row counts as the README's table states them.

    Read rather than hard-coded. The counts here were frozen literals until
    2026-09-18, which meant they stopped describing the database the moment
    it grew and the test failed for the rest of its life without anyone
    learning anything from it. The invariant worth holding is the one the
    test is named for -- README and data agree -- and that one survives the
    database changing size.
    """
    row = re.compile(r"^\|\s*`data/(\w+)\.csv`\s*\|\s*([\d,]+)\s*\|")
    total = re.compile(r"^\|\s*\*\*total\*\*\s*\|\s*\*\*([\d,]+)\*\*\s*\|")
    per_family, grand = {}, None
    for line in (Path(__file__).resolve().parents[1] / "README.md").read_text().splitlines():
        m = row.match(line)
        if m:
            per_family[m.group(1)] = int(m.group(2).replace(",", ""))
        m = total.match(line)
        if m:
            grand = int(m.group(1).replace(",", ""))
    assert per_family and grand is not None, "README row-count table not found"
    return per_family, grand


def test_row_totals_match_the_repository_readme(all_rows):
    per_family, grand = _readme_row_counts()
    assert len(all_rows) == grand
    assert all_rows["family"].value_counts().to_dict() == per_family
    assert sum(per_family.values()) == grand


def test_lle_regime_excluded_by_default(default_rows, all_rows):
    """The default that matters: lle-regime rows are not gas solubilities."""
    assert "lle-regime" not in set(default_rows["tag"])
    only_tags = gbb.load(exclude_flags=None)
    assert len(all_rows) - len(only_tags) == (all_rows["tag"] == "lle-regime").sum() == 354
    dropped = all_rows[all_rows["tag"] == "lle-regime"]
    # the 144 propane rows of v1.1.1 plus 210 rows added in v1.2 (propane, butanes, ethane, CO2 below its critical temperature)
    assert {"c3h8", "c2h6", "n-c4h10", "i-c4h10", "co2"} == set(dropped["gas"])
    assert (dropped[dropped["dataset_id"] == "c3h8_water"]).shape[0] == 144


def test_default_flag_exclusion(default_rows, all_rows):
    from gasbrinebench.vocab import DEFAULT_EXCLUDED_FLAGS
    carried = all_rows["flags"].map(lambda f: bool(set(f.split(";")) & set(DEFAULT_EXCLUDED_FLAGS)))
    kept = all_rows[~carried & (all_rows["tag"] != "lle-regime")]
    assert len(default_rows) == len(kept)


def test_exclude_tags_none_keeps_everything():
    _, grand = _readme_row_counts()
    assert len(gbb.load(exclude_tags=None, exclude_flags=None)) == grand
    assert len(gbb.load(exclude_tags=(), exclude_flags=())) == grand


def test_derived_columns_attached_by_default(default_rows):
    for col in ("ionic_strength", "total_molality", "salt_system",
                "salt_system_kind"):
        assert col in default_rows.columns
    assert "ionic_strength" not in gbb.load(derive=False).columns


def test_load_accepts_a_list_of_families():
    df = gbb.load(["rho", "dh_sol"])
    assert set(df["family"]) == {"rho", "dh_sol"}


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
