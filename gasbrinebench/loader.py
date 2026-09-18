"""Reading the GasBrineBench CSVs into pandas.

The CSVs must be read with ``keep_default_na=False``: the ``gas`` column is
legitimately empty for brine-only properties and must not become ``NaN``
(``SCHEMA.md``). This module does that, then coerces the numeric columns
back to floats so that the genuinely blank cells -- ``P_bar`` on the
``psat_ratio`` rows, ``uncertainty`` wherever the source stated none -- become
``NaN`` and not the string ``''``. Getting that pair of conventions right by
hand is the first thing a new user gets wrong.

Examples
--------
>>> import gasbrinebench as gbb
>>> df = gbb.load()                      # every family, lle-regime excluded
>>> len(df)
11300
>>> gbb.load("solubility", gas="co2", T=(320, 330)).shape[0]
744
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import pandas as pd

from .derived import with_derived
from .vocab import COLUMNS, DEFAULT_EXCLUDED_TAGS, FAMILIES, NUMERIC_COLUMNS

__all__ = ["data_dir", "available_families", "load", "load_family"]

#: Environment variable that overrides data-directory discovery.
DATA_DIR_ENV = "GASBRINEBENCH_DATA"


def data_dir() -> Path:
    """Locate the ``data/`` directory holding the family CSVs.

    Resolution order:

    1. ``$GASBRINEBENCH_DATA`` if set;
    2. ``data/`` beside the installed package (the repository layout);
    3. ``data/`` in the current working directory or any of its parents.

    Raises
    ------
    FileNotFoundError
        If no candidate holds the expected CSVs, with the paths tried.
    """
    tried = []

    env = os.environ.get(DATA_DIR_ENV)
    if env:
        p = Path(env).expanduser().resolve()
        if _looks_like_data_dir(p):
            return p
        tried.append(f"{p} (from ${DATA_DIR_ENV})")

    here = Path(__file__).resolve().parent.parent / "data"
    if _looks_like_data_dir(here):
        return here
    tried.append(str(here))

    cwd = Path.cwd().resolve()
    for parent in [cwd, *cwd.parents]:
        cand = parent / "data"
        if _looks_like_data_dir(cand):
            return cand
    tried.append(f"{cwd}/data and its parents")

    raise FileNotFoundError(
        "could not find the GasBrineBench data/ directory. Tried:\n  "
        + "\n  ".join(tried)
        + f"\nSet ${DATA_DIR_ENV} to the data/ directory of a GasBrineBench "
        "clone, or run from inside the clone."
    )


def _looks_like_data_dir(p: Path) -> bool:
    return p.is_dir() and (p / "solubility.csv").is_file()


def available_families(where: Path | str | None = None) -> list[str]:
    """Family names for which a CSV is actually present, in schema order.

    Families declared in ``SCHEMA.md`` but not yet populated (``miac``) have
    no CSV and do not appear.
    """
    root = Path(where) if where is not None else data_dir()
    present = {p.stem for p in root.glob("*.csv")}
    known = [f for f in FAMILIES if f in present]
    return known + sorted(present - set(known))


@lru_cache(maxsize=None)
def _read_csv_cached(path: str, mtime: float) -> pd.DataFrame:
    """Read and type one family CSV. Cached on (path, mtime)."""
    df = pd.read_csv(path, keep_default_na=False, dtype=str)
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].str.strip(), errors="coerce")
    for col in df.columns:
        if col not in NUMERIC_COLUMNS:
            df[col] = df[col].str.strip()
    ordered = [c for c in COLUMNS if c in df.columns]
    extra = [c for c in df.columns if c not in ordered]
    return df[ordered + extra]


def load_family(
    family: str, *, where: Path | str | None = None
) -> pd.DataFrame:
    """Read one family CSV verbatim: no filtering, no derived columns.

    The returned frame carries a ``family`` column and the schema columns in
    ``SCHEMA.md`` order. Use it when you want the file as it is on disk;
    :func:`load` is the friendlier entry point.

    Parameters
    ----------
    family : str
        A name from :func:`available_families`, e.g. ``'solubility'``.
    where : path, optional
        Directory holding the CSVs. Defaults to :func:`data_dir`.

    Raises
    ------
    ValueError
        If ``family`` is not present, listing the ones that are.
    """
    root = Path(where) if where is not None else data_dir()
    path = root / f"{family}.csv"
    if not path.is_file():
        raise ValueError(
            f"no such property family {family!r}. Available: "
            f"{', '.join(available_families(root))}"
        )
    df = _read_csv_cached(str(path), path.stat().st_mtime).copy()
    df["family"] = family
    return df


def load(
    family: str | list[str] | tuple[str, ...] = "all",
    *,
    where: Path | str | None = None,
    exclude_tags: tuple[str, ...] | list[str] | None = DEFAULT_EXCLUDED_TAGS,
    derive: bool = True,
    **filters,
) -> pd.DataFrame:
    """Load one, several or all property families into a DataFrame.

    Parameters
    ----------
    family : str or sequence of str, default ``'all'``
        Family name(s) from :func:`available_families`, or ``'all'``.
    where : path, optional
        Directory holding the CSVs. Defaults to :func:`data_dir`.
    exclude_tags : sequence of str or None, default ``('lle-regime',)``
        Tags dropped before anything else. **The default matters.** The 144
        ``lle-regime`` rows are propane points whose heavy phase is a liquid:
        they are liquid-liquid mutual solubilities, not gas solubilities, and
        scoring them as the latter is a category error
        (``data/QUALITY.md`` Sec. 7). Pass ``exclude_tags=None`` to get every
        row, or ``exclude_tags=()`` equivalently.
    derive : bool, default True
        Attach the derived composition columns
        (:func:`gasbrinebench.with_derived`).
    **filters
        Forwarded to :func:`gasbrinebench.select`, so the common case is one
        call: ``load('solubility', gas='co2', quality='R')``.

    Returns
    -------
    DataFrame
        Schema columns in ``SCHEMA.md`` order, then ``family``, then the
        derived columns. The index is a fresh ``RangeIndex``.

    Examples
    --------
    >>> import gasbrinebench as gbb
    >>> co2 = gbb.load('solubility', gas='co2', property='solubility_molality')
    >>> int(co2['source'].nunique())
    56
    >>> everything = gbb.load(exclude_tags=None)
    >>> len(everything)
    11444
    """
    root = Path(where) if where is not None else data_dir()
    if family == "all":
        names = available_families(root)
    elif isinstance(family, str):
        names = [family]
    else:
        names = list(family)

    frames = [load_family(n, where=root) for n in names]
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    if exclude_tags:
        df = df[~df["tag"].isin(list(exclude_tags))]

    if derive:
        df = with_derived(df)

    if filters:
        from .filters import select

        df = select(df, **filters)

    return df.reset_index(drop=True)
