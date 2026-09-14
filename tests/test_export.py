"""Export, and the promise that a missing backend is named, not guessed.

The optional-dependency tests run either way: with the backend installed they
check the round trip, without it they check the error message. The one thing
that must never happen -- a missing package surfacing as some unrelated
exception -- is asserted in both branches.
"""

from __future__ import annotations

import importlib.util

import pandas as pd
import pytest

import gasbrinebench as gbb
from gasbrinebench.export import MissingDependencyError

HAVE_PYARROW = importlib.util.find_spec("pyarrow") is not None
HAVE_TABLES = importlib.util.find_spec("tables") is not None


@pytest.fixture(scope="module")
def small():
    return gbb.load("phi_osm")


def test_to_pandas_is_a_copy(small):
    out = gbb.to_pandas(small)
    pd.testing.assert_frame_equal(out, small)
    assert out is not small


def test_csv_round_trip(small, tmp_path):
    path = gbb.write(small, tmp_path / "phi.csv")
    back = pd.read_csv(path, keep_default_na=False, dtype=str)
    assert len(back) == len(small)
    assert (back["gas"] == "").all()


def test_csv_writes_blanks_not_nan(tmp_path):
    path = gbb.write(gbb.load("psat_ratio"), tmp_path / "psat.csv")
    text = path.read_text()
    assert "NaN" not in text
    assert "nan" not in text


def test_format_inferred_from_suffix(small, tmp_path):
    assert gbb.write(small, tmp_path / "a.csv").exists()
    with pytest.raises(ValueError, match="cannot infer"):
        gbb.write(small, tmp_path / "a.txt")


def test_explicit_format_overrides_suffix(small, tmp_path):
    path = gbb.write(small, tmp_path / "a.txt", fmt="csv")
    assert path.exists()


def test_unknown_format_raises(small, tmp_path):
    with pytest.raises(ValueError, match="unknown export format"):
        gbb.write(small, tmp_path / "a.csv", fmt="feather")


def test_have_reports_backends():
    assert gbb.export.have("csv") is True
    assert gbb.export.have("parquet") is HAVE_PYARROW
    assert gbb.export.have("hdf5") is HAVE_TABLES


def test_missing_dependency_error_is_an_import_error():
    assert issubclass(MissingDependencyError, ImportError)


@pytest.mark.skipif(not HAVE_PYARROW, reason="pyarrow not installed")
def test_parquet_round_trip(small, tmp_path):
    path = gbb.write(small, tmp_path / "phi.parquet")
    back = pd.read_parquet(path)
    assert len(back) == len(small)
    assert list(back.columns) == list(small.columns)
    pd.testing.assert_series_equal(back["value"], small["value"])


@pytest.mark.skipif(not HAVE_TABLES, reason="tables not installed")
def test_hdf5_round_trip(small, tmp_path):
    path = gbb.write(small, tmp_path / "bench.h5", key="phi_osm")
    back = pd.read_hdf(path, key="phi_osm")
    assert len(back) == len(small)
    assert back["value"].to_numpy() == pytest.approx(small["value"].to_numpy())


@pytest.mark.parametrize(
    "suffix,package,installed",
    [(".parquet", "pyarrow", HAVE_PYARROW), (".h5", "tables", HAVE_TABLES)],
)
def test_missing_backend_names_the_package(
    small, tmp_path, monkeypatch, suffix, package, installed
):
    """Simulate the absence of the backend and read the message."""
    real = importlib.util.find_spec

    def fake(name, *a, **k):
        return None if name == package else real(name, *a, **k)

    monkeypatch.setattr(importlib.util, "find_spec", fake)
    with pytest.raises(MissingDependencyError) as exc:
        gbb.write(small, tmp_path / f"out{suffix}")
    msg = str(exc.value)
    assert package in msg
    assert f"pip install {package}" in msg
    assert "pandas" in msg


def test_csv_still_works_without_any_optional_backend(small, tmp_path, monkeypatch):
    monkeypatch.setattr(importlib.util, "find_spec", lambda *a, **k: None)
    assert gbb.write(small, tmp_path / "x.csv").exists()
