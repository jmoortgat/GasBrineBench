"""Row selection.

One function, :func:`select`, with a keyword per axis a user of gas-brine data
actually asks about: which gas, which property, which brine, which T/P window,
which quality code, which fit/test tag.

Two deliberate design choices:

* **Typos raise.** ``select(df, gas='CO_2')`` is a ``ValueError`` naming the
  seven gas codes, not an empty frame. A silently empty selection is the most
  expensive kind of mistake in a benchmark.
* **Case is normalised.** ``gas='CO2'`` and ``quality='r'`` work; the values
  are matched against the vocabulary in the case the CSVs use.

Examples
--------
>>> import gasbrinebench as gbb
>>> df = gbb.load()
>>> hot = gbb.select(df, property='solubility_molality', T=(400, None))
>>> sorted(hot['gas'].unique())
['c2h6', 'c3h8', 'ch4', 'co2', 'h2']
>>> gbb.select(df, salt_system='single-salt', gas='co2').shape[0]
3990
"""

from __future__ import annotations

from typing import Iterable, Sequence

import pandas as pd

from .derived import ionic_strength, salt_system, salt_system_kind, total_molality
from .vocab import GASES, IONS, PROPERTIES, QUALITY_CODES, TAGS

__all__ = ["select"]

_SYSTEM_KINDS = ("water", "single-salt", "mixed-salt")


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Iterable):
        return list(value)
    return [value]


def _normalise(values, vocab: Sequence[str], what: str, *, lower=True) -> list:
    """Case-fold ``values`` onto ``vocab``; raise naming ``vocab`` on a miss."""
    out = []
    lookup = {v.lower(): v for v in vocab}
    for v in values:
        key = str(v).strip()
        hit = lookup.get(key.lower()) if lower else (key if key in vocab else None)
        if hit is None:
            raise ValueError(
                f"unknown {what} {v!r}. Valid values: {', '.join(vocab)}"
            )
        out.append(hit)
    return out


def _window(series: pd.Series, bounds, what: str) -> pd.Series:
    """Boolean mask for an inclusive ``(lo, hi)`` window; ``None`` is open."""
    if isinstance(bounds, (int, float)):
        raise TypeError(
            f"{what} takes a (low, high) pair, not a single number. "
            f"Use {what}=({bounds}, {bounds}) for an exact match, or "
            f"{what}=({bounds}, None) for a lower bound."
        )
    lo, hi = bounds
    # Asking for a window on a quantity a row does not carry excludes it: the
    # psat_ratio rows have no P_bar, and they are not "inside" any pressure
    # window, not even an open one.
    mask = series.notna()
    if lo is not None:
        mask &= series >= lo
    if hi is not None:
        mask &= series <= hi
    return mask.fillna(False)


def select(
    df: pd.DataFrame,
    *,
    gas=None,
    family=None,
    property=None,
    source=None,
    dataset_id=None,
    quality=None,
    tag=None,
    exclude_tags=None,
    T=None,
    P=None,
    ionic_strength=None,
    total_molality=None,
    salt_system=None,
    ions=None,
    ions_exactly=None,
    salt_free=None,
) -> pd.DataFrame:
    """Filter a GasBrineBench frame. Every argument is optional and ANDed.

    Parameters
    ----------
    gas : str or sequence of str, optional
        One or more of ``co2, ch4, h2, n2, o2, c2h6, c3h8``. Case-insensitive.
        Pass ``''`` to select the brine-only rows, whose ``gas`` cell is empty.
    family : str or sequence of str, optional
        Property family (``'solubility'``, ``'rho'``, ...). Only meaningful on
        a frame loaded by :func:`gasbrinebench.load`, which adds the column.
    property : str or sequence of str, optional
        One or more of the ``property`` vocabulary, e.g.
        ``'solubility_molality'``, ``'xc_saltfree'``, ``'y_h2o'``.
    source, dataset_id : str or sequence of str, optional
        Exact match on the curation source key or the dataset block id.
    quality : str or sequence of str, optional
        ``'R'``, ``'T'`` and/or ``'U'``. Case-insensitive.
    tag : str or sequence of str, optional
        Keep only these tags.
    exclude_tags : sequence of str, optional
        Drop these tags. Applied after ``tag``.
    T, P : (low, high), optional
        Inclusive window on ``T_K`` [K] and ``P_bar`` [bar]. ``None`` on
        either side leaves it open. Rows with a blank ``P_bar`` (the
        ``psat_ratio`` family) never satisfy a ``P`` window.
    ionic_strength, total_molality : (low, high), optional
        Inclusive window on the derived composition quantities [mol/kg water].
    salt_system : str or sequence of str, optional
        Either a *kind* -- ``'water'``, ``'single-salt'``, ``'mixed-salt'`` --
        or an explicit ion-set label as produced by
        :func:`gasbrinebench.salt_system`, e.g. ``'Na-Cl'``, ``'Cl-Ca'``.
        Kinds and labels may be mixed in one list.
    ions : str or sequence of str, optional
        Keep rows in which *all* of these ions are present at nonzero
        molality, whatever else is there. Names without the ``m_`` prefix:
        ``'Na'``, ``'SO4'``.
    ions_exactly : str or sequence of str, optional
        Keep rows whose set of present ions is exactly this. Pass ``[]`` for
        the salt-free binaries.
    salt_free : bool, optional
        ``True`` keeps only rows with no ions; ``False`` keeps only rows with
        salt.

    Returns
    -------
    DataFrame
        A filtered view-copy with the original index preserved, so it can be
        aligned back against ``df``.

    Raises
    ------
    ValueError
        On a value outside the controlled vocabulary, naming the valid set.

    Examples
    --------
    >>> import gasbrinebench as gbb
    >>> df = gbb.load()
    >>> gbb.select(df, gas='co2', property='y_h2o', T=(320, 326)).shape[0]
    78
    >>> gbb.select(df, ions_exactly=['Na', 'Cl'], family='rho').shape[0]
    189
    >>> gbb.select(df, gas='h2', quality='R').shape[0]
    24
    """
    mask = pd.Series(True, index=df.index)

    if gas is not None:
        wanted = _as_list(gas)
        blank = [g for g in wanted if str(g).strip() == ""]
        named = _normalise(
            [g for g in wanted if str(g).strip() != ""], GASES, "gas"
        )
        col = df["gas"].astype(str).str.strip()
        m = col.isin(named)
        if blank:
            m |= col == ""
        mask &= m

    if family is not None:
        if "family" not in df.columns:
            raise KeyError(
                "this frame has no 'family' column; load it with "
                "gasbrinebench.load() or filter on 'property' instead"
            )
        mask &= df["family"].isin(_as_list(family))

    if property is not None:
        vals = _normalise(_as_list(property), PROPERTIES, "property")
        mask &= df["property"].isin(vals)

    if source is not None:
        mask &= df["source"].isin(_as_list(source))

    if dataset_id is not None:
        mask &= df["dataset_id"].isin(_as_list(dataset_id))

    if quality is not None:
        vals = _normalise(_as_list(quality), QUALITY_CODES, "quality code")
        mask &= df["quality"].isin(vals)

    if tag is not None:
        vals = _normalise(_as_list(tag), TAGS, "tag")
        mask &= df["tag"].isin(vals)

    if exclude_tags:
        vals = _normalise(_as_list(exclude_tags), TAGS, "tag")
        mask &= ~df["tag"].isin(vals)

    if T is not None:
        mask &= _window(pd.to_numeric(df["T_K"], errors="coerce"), T, "T")

    if P is not None:
        mask &= _window(pd.to_numeric(df["P_bar"], errors="coerce"), P, "P")

    if ionic_strength is not None:
        col = df["ionic_strength"] if "ionic_strength" in df.columns else _I(df)
        mask &= _window(col, ionic_strength, "ionic_strength")

    if total_molality is not None:
        col = (
            df["total_molality"]
            if "total_molality" in df.columns
            else _M(df)
        )
        mask &= _window(col, total_molality, "total_molality")

    if salt_system is not None:
        wanted = _as_list(salt_system)
        kinds = [w for w in wanted if w in _SYSTEM_KINDS and w != "water"]
        labels = [w for w in wanted if w not in _SYSTEM_KINDS]
        want_water = "water" in wanted
        label_col = (
            df["salt_system"] if "salt_system" in df.columns else _S(df)
        )
        m = pd.Series(False, index=df.index)
        if labels:
            unknown = [
                lbl for lbl in labels
                if not set(lbl.split("-")) <= {c[2:] for c in IONS}
            ]
            if unknown:
                raise ValueError(
                    f"unknown salt_system {unknown!r}. Use one of "
                    f"{', '.join(_SYSTEM_KINDS)}, or an ion-set label built "
                    f"from {', '.join(c[2:] for c in IONS)} such as 'Na-Cl'."
                )
            m |= label_col.isin(labels)
        if want_water:
            m |= label_col == "water"
        if kinds:
            kind_col = (
                df["salt_system_kind"]
                if "salt_system_kind" in df.columns
                else _K(df)
            )
            m |= kind_col.isin(kinds)
        mask &= m

    if ions is not None:
        wanted = _ion_cols(_as_list(ions))
        for c in wanted:
            mask &= pd.to_numeric(df[c], errors="coerce") > 0

    if ions_exactly is not None:
        wanted = set(_ion_cols(_as_list(ions_exactly)))
        for c in IONS:
            present = pd.to_numeric(df[c], errors="coerce") > 0
            mask &= present if c in wanted else ~present

    if salt_free is not None:
        col = df["total_molality"] if "total_molality" in df.columns else _M(df)
        mask &= (col == 0) if salt_free else (col > 0)

    return df[mask.fillna(False)]


def _ion_cols(names) -> list[str]:
    valid = {c[2:]: c for c in IONS}
    out = []
    for n in names:
        key = str(n).strip()
        key = key[2:] if key.startswith("m_") else key
        if key not in valid:
            raise ValueError(
                f"unknown ion {n!r}. Valid: {', '.join(valid)}"
            )
        out.append(valid[key])
    return out


# Local aliases so the keyword names above can shadow the derived functions.
_I = ionic_strength
_M = total_molality
_S = salt_system
_K = salt_system_kind
