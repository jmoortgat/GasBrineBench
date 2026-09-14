"""Inventory tables: what is in a selection, at a glance.

These are the frames you want in the first cell of an analysis, and the ones
that make a filtered selection auditable -- how many rows survived, from how
many sources, over what range.

Examples
--------
>>> import gasbrinebench as gbb
>>> inv = gbb.inventory(gbb.load())
>>> list(inv.columns)
['rows', 'sources', 'gases', 'T_min', 'T_max', 'P_min', 'P_max', 'R', 'T', 'U']
"""

from __future__ import annotations

import pandas as pd

from .derived import salt_system
from .vocab import QUALITY_CODES

__all__ = ["inventory", "coverage", "sources"]


def inventory(df: pd.DataFrame, by: str = "family") -> pd.DataFrame:
    """Rows, sources, gases, T/P range and quality mix, grouped by ``by``.

    Parameters
    ----------
    df : DataFrame
    by : str or list of str, default ``'family'``
        Column(s) to group on. ``'family'``, ``'property'``, ``'gas'`` and
        ``'salt_system'`` are the useful ones.

    Examples
    --------
    >>> import gasbrinebench as gbb
    >>> gbb.inventory(gbb.load('solubility'), by='gas').loc['co2', 'rows']
    1844
    """
    key = by if isinstance(by, str) else list(by)
    T = pd.to_numeric(df["T_K"], errors="coerce")
    P = pd.to_numeric(df["P_bar"], errors="coerce")
    work = df.assign(_T=T, _P=P)

    g = work.groupby(key, dropna=False)
    out = pd.DataFrame(
        {
            "rows": g.size(),
            "sources": g["source"].nunique(),
            "gases": g["gas"].apply(
                lambda s: ", ".join(sorted(v for v in set(s) if v)) or "-"
            ),
            "T_min": g["_T"].min().round(1),
            "T_max": g["_T"].max().round(1),
            "P_min": g["_P"].min().round(2),
            "P_max": g["_P"].max().round(2),
        }
    )
    for code in QUALITY_CODES:
        out[code] = g["quality"].apply(lambda s, c=code: int((s == c).sum()))
    return out


def coverage(df: pd.DataFrame) -> pd.DataFrame:
    """Row counts per (gas, salt system), as a rectangular table.

    Zeros mark the gaps -- which are as informative as the counts, and are the
    reason this is a table and not a list.

    Examples
    --------
    >>> import gasbrinebench as gbb
    >>> cov = gbb.coverage(gbb.load('solubility'))
    >>> cov.loc['co2', 'water']
    0
    """
    sysname = (
        df["salt_system"] if "salt_system" in df.columns else salt_system(df)
    )
    gas = df["gas"].replace("", "-")
    tab = pd.crosstab(gas, sysname)
    cols = ["water"] + [c for c in tab.columns if c != "water"]
    return tab[[c for c in cols if c in tab.columns]]


def sources(df: pd.DataFrame) -> pd.DataFrame:
    """One row per ``source``: rows contributed, families, gases, T/P range.

    Sorted by row count, descending. The ``source`` cell is the curation key,
    not a bibtex key; ``SOURCES.md`` maps it onto the citation.

    Examples
    --------
    >>> import gasbrinebench as gbb
    >>> gbb.sources(gbb.load('y_h2o')).head(1).index[0]
    'TABASINEJAD(2011)'
    """
    T = pd.to_numeric(df["T_K"], errors="coerce")
    P = pd.to_numeric(df["P_bar"], errors="coerce")
    work = df.assign(_T=T, _P=P)
    g = work.groupby("source")
    out = pd.DataFrame(
        {
            "rows": g.size(),
            "families": g["family"].apply(lambda s: ", ".join(sorted(set(s))))
            if "family" in df.columns
            else g["property"].apply(lambda s: ", ".join(sorted(set(s)))),
            "gases": g["gas"].apply(
                lambda s: ", ".join(sorted(v for v in set(s) if v)) or "-"
            ),
            "T_min": g["_T"].min().round(1),
            "T_max": g["_T"].max().round(1),
            "P_min": g["_P"].min().round(2),
            "P_max": g["_P"].max().round(2),
        }
    )
    return out.sort_values("rows", ascending=False)
