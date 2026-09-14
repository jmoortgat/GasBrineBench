"""Writing a selection out again: CSV, Parquet, HDF5.

Only pandas is required. Parquet needs ``pyarrow`` and HDF5 needs ``tables``
(PyTables), and **the absence of either is reported by name, before anything
is attempted**::

    >>> gbb.write(df, 'out.parquet')        # doctest: +SKIP
    MissingDependencyError: writing Parquet needs the 'pyarrow' package,
    which is not installed. Install it with:  pip install pyarrow

That is the whole point of this module. ``DataFrame.to_parquet`` without an
engine raises an ``ImportError`` that names two candidate packages and reads
like a bug in your code; ``DataFrame.to_hdf`` without PyTables can surface as
an ``AttributeError`` from deep inside pandas. Guessing which of those means
"pip install something" costs more time than the export saves.

Examples
--------
>>> import gasbrinebench as gbb, tempfile, os
>>> df = gbb.load('phi_osm')
>>> d = tempfile.mkdtemp()
>>> _ = gbb.write(df, os.path.join(d, 'phi_osm.csv'))
>>> _ = gbb.write(df, os.path.join(d, 'phi_osm.parquet'))   # doctest: +SKIP
>>> _ = gbb.write(df, os.path.join(d, 'bench.h5'))          # doctest: +SKIP

The last two are skipped as doctests because they depend on an optional
backend; ``tests/test_export.py`` exercises both the present and the absent
case.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

__all__ = [
    "MissingDependencyError",
    "FORMATS",
    "to_pandas",
    "write",
    "write_csv",
    "write_parquet",
    "write_hdf5",
    "have",
]


class MissingDependencyError(ImportError):
    """An optional export backend is not installed.

    Subclasses :class:`ImportError`, so ``except ImportError`` still catches
    it, but the message names exactly one package and the command that
    installs it.
    """


#: Optional backend per format: (package, human name, pip command).
_BACKENDS = {
    "parquet": ("pyarrow", "Parquet", "pip install pyarrow"),
    "hdf5": ("tables", "HDF5", "pip install tables"),
}

#: File-name suffixes recognised by :func:`write`.
FORMATS = {
    ".csv": "csv",
    ".parquet": "parquet",
    ".pq": "parquet",
    ".h5": "hdf5",
    ".hdf5": "hdf5",
    ".hdf": "hdf5",
}


def have(fmt: str) -> bool:
    """Is the backend for ``fmt`` importable?

    >>> import gasbrinebench as gbb
    >>> gbb.export.have('csv')
    True
    """
    spec = _BACKENDS.get(fmt)
    if spec is None:
        return True
    return importlib.util.find_spec(spec[0]) is not None


def _require(fmt: str) -> None:
    spec = _BACKENDS.get(fmt)
    if spec is None:
        return
    package, human, how = spec
    if importlib.util.find_spec(package) is None:
        raise MissingDependencyError(
            f"writing {human} needs the {package!r} package, which is not "
            f"installed. Install it with:  {how}\n"
            "GasBrineBench itself needs only pandas; CSV export always works."
        )


def to_pandas(df: pd.DataFrame) -> pd.DataFrame:
    """Return the frame itself, as a copy.

    A no-op that exists so that ``to_pandas`` sits next to ``write`` in the
    API and code that dispatches on an output format has a case for "keep it
    in memory".
    """
    return df.copy()


def write_csv(df: pd.DataFrame, path, **kwargs) -> Path:
    """Write ``df`` to CSV, reproducing the repository's conventions.

    Blank rather than ``NaN`` for the empty cells, no index column, so the
    result round-trips through :func:`gasbrinebench.load_family`.
    """
    path = Path(path)
    kwargs.setdefault("index", False)
    kwargs.setdefault("na_rep", "")
    df.to_csv(path, **kwargs)
    return path


def write_parquet(df: pd.DataFrame, path, **kwargs) -> Path:
    """Write ``df`` to Parquet via pyarrow.

    Raises
    ------
    MissingDependencyError
        If ``pyarrow`` is not installed.
    """
    _require("parquet")
    path = Path(path)
    kwargs.setdefault("index", False)
    kwargs.setdefault("engine", "pyarrow")
    df.to_parquet(path, **kwargs)
    return path


def write_hdf5(df: pd.DataFrame, path, key: str = "gasbrinebench", **kwargs) -> Path:
    """Write ``df`` to HDF5 via PyTables.

    Written in PyTables ``table`` format so the file is queryable with
    ``pandas.read_hdf(..., where=...)`` and readable by other HDF5 tools.
    Object (string) columns are stored as fixed-width strings, so a later
    append with a longer string needs ``min_itemsize``; for a one-shot export
    of a selection that does not arise.

    Raises
    ------
    MissingDependencyError
        If ``tables`` is not installed.
    """
    _require("hdf5")
    path = Path(path)
    kwargs.setdefault("format", "table")
    kwargs.setdefault("mode", "w")
    frame = df.copy()
    for col in frame.columns:
        if frame[col].dtype == object:
            frame[col] = frame[col].map(
                lambda v: "-".join(v) if isinstance(v, tuple) else v
            ).astype(str)
    frame.to_hdf(path, key=key, **kwargs)
    return path


_WRITERS = {
    "csv": write_csv,
    "parquet": write_parquet,
    "hdf5": write_hdf5,
}


def write(df: pd.DataFrame, path, fmt: str | None = None, **kwargs) -> Path:
    """Write ``df``, choosing the format from ``path``'s suffix.

    Parameters
    ----------
    df : DataFrame
    path : path-like
        Destination. ``.csv``, ``.parquet``/``.pq``, ``.h5``/``.hdf5``/``.hdf``.
    fmt : {'csv', 'parquet', 'hdf5'}, optional
        Override the suffix.
    **kwargs
        Passed to the underlying writer (``key=`` for HDF5,
        ``compression=`` for Parquet, and so on).

    Returns
    -------
    Path
        The path written.

    Raises
    ------
    ValueError
        On an unrecognised suffix, listing the ones that are recognised.
    MissingDependencyError
        If the chosen format's optional backend is missing.

    Examples
    --------
    >>> import gasbrinebench as gbb, tempfile, os
    >>> p = gbb.write(gbb.load('eps_r'), os.path.join(tempfile.mkdtemp(), 'e.csv'))
    >>> p.name
    'e.csv'
    """
    path = Path(path)
    if fmt is None:
        fmt = FORMATS.get(path.suffix.lower())
        if fmt is None:
            raise ValueError(
                f"cannot infer an export format from {path.name!r}. "
                f"Known suffixes: {', '.join(sorted(FORMATS))}. "
                "Pass fmt='csv', 'parquet' or 'hdf5' explicitly."
            )
    if fmt not in _WRITERS:
        raise ValueError(
            f"unknown export format {fmt!r}. "
            f"Valid: {', '.join(sorted(_WRITERS))}"
        )
    return _WRITERS[fmt](df, path, **kwargs)
