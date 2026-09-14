"""Inventory tables, the interop mapping, and the command-line front end."""

from __future__ import annotations

import pytest

import gasbrinebench as gbb
from gasbrinebench.__main__ import main
from gasbrinebench.vocab import (
    COLUMNS,
    GAS_FREE_PROPERTIES,
    PROPERTIES,
    QUALITY_CODES,
    TAGS,
    UNITS,
)


# --- vocabularies mirror SCHEMA.md ---------------------------------------

def test_vocabularies_cover_the_data(all_rows):
    assert set(all_rows["property"]) <= set(PROPERTIES)
    assert set(all_rows["quality"]) <= set(QUALITY_CODES)
    assert set(all_rows["tag"]) <= set(TAGS)
    assert set(UNITS) == set(PROPERTIES)


def test_gas_free_properties_carry_no_gas(all_rows):
    gas_free = all_rows[all_rows["property"].isin(GAS_FREE_PROPERTIES)]
    assert (gas_free["gas"] == "").all()
    gas_props = all_rows[~all_rows["property"].isin(GAS_FREE_PROPERTIES)]
    assert (gas_props["gas"] != "").all()


def test_columns_match_the_csv_header(repo_root):
    header = (repo_root / "data" / "solubility.csv").read_text().splitlines()[0]
    assert header.split(",") == COLUMNS


# --- inventory -----------------------------------------------------------

def test_inventory_columns(default_rows):
    inv = gbb.inventory(default_rows)
    assert list(inv.columns) == [
        "rows", "sources", "gases", "T_min", "T_max", "P_min", "P_max",
        "R", "T", "U",
    ]
    assert inv["rows"].sum() == len(default_rows)


def test_inventory_by_other_keys(default_rows):
    assert gbb.inventory(default_rows, by="gas")["rows"].sum() == len(default_rows)
    assert gbb.inventory(default_rows, by="quality").index.tolist() == ["R", "T", "U"]


def test_coverage_is_rectangular(default_rows):
    cov = gbb.coverage(default_rows)
    assert cov.values.sum() == len(default_rows)
    assert cov.columns[0] == "water"


def test_sources_table(default_rows):
    src = gbb.sources(default_rows)
    assert src["rows"].sum() == len(default_rows)
    assert src["rows"].is_monotonic_decreasing


# --- interop -------------------------------------------------------------

def test_phreeqc_map_covers_every_ion():
    from gasbrinebench.vocab import IONS

    assert set(gbb.phreeqc_column_map()) == set(IONS)
    assert gbb.phreeqc_column_map()["m_SO4"] == "S(6)"


def test_phreeqc_map_is_a_copy():
    m = gbb.phreeqc_column_map()
    m["m_Na"] = "wrong"
    assert gbb.phreeqc_column_map()["m_Na"] == "Na"


def test_no_exporter_is_shipped_for_speciation_codes():
    """interop documents a mapping; it must not grow a silent converter."""
    names = [n for n in dir(gbb.interop) if not n.startswith("_")]
    assert not [n for n in names if "write" in n or "to_phreeqc" in n]


# --- CLI -----------------------------------------------------------------

def test_cli_inventory(capsys):
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "GasBrineBench" in out
    assert "solubility" in out


def test_cli_filters_and_exports(tmp_path, capsys):
    path = tmp_path / "co2.csv"
    assert main(["--gas", "co2", "--quality", "R", "-o", str(path)]) == 0
    assert path.exists()
    assert "wrote" in capsys.readouterr().out


def test_cli_bad_gas_is_exit_2(capsys):
    assert main(["--gas", "CO_2"]) == 2
    assert "unknown gas" in capsys.readouterr().err


def test_cli_bad_suffix_is_exit_2(tmp_path, capsys):
    assert main(["-o", str(tmp_path / "x.txt")]) == 2
    assert "cannot infer" in capsys.readouterr().err


def test_cli_include_lle(capsys):
    assert main(["--by", "tag"]) == 0
    assert "lle-regime" not in capsys.readouterr().out
    assert main(["--include-lle", "--by", "tag"]) == 0
    assert "lle-regime" in capsys.readouterr().out


@pytest.mark.parametrize("args", [["--T", "300", "400"], ["--P", "10", "100"]])
def test_cli_windows(args, capsys):
    assert main(args) == 0
    assert "rows" in capsys.readouterr().out
