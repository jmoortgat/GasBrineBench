"""Quantities derived from the ion columns and from ``value``.

Nothing here is stored in the CSVs; all of it is computed from columns that
are. Each function takes a DataFrame in the GasBrineBench schema and returns a
Series aligned to its index, so they compose with ordinary pandas indexing.

:func:`with_derived` adds the cheap ones as columns; :func:`load` calls it for
you unless you pass ``derive=False``.

Examples
--------
>>> import gasbrinebench as gbb
>>> df = gbb.load("rho")
>>> float(gbb.ionic_strength(df).max())
18.0
>>> gbb.salt_system(df).value_counts().to_dict()['Na-Cl']
189
"""

from __future__ import annotations

import pandas as pd

from .vocab import ION_CHARGE, IONS, M_W

__all__ = [
    "ionic_strength",
    "total_molality",
    "charge_imbalance",
    "salt_system",
    "salt_system_kind",
    "ions_present",
    "xc_saltfree_from_molality",
    "xc_saltinclusive_from_molality",
    "molality_from_xc_saltfree",
    "with_derived",
]


def _ion_frame(df: pd.DataFrame) -> pd.DataFrame:
    """The six ion columns as floats, with a helpful error if any are gone."""
    missing = [c for c in IONS if c not in df.columns]
    if missing:
        raise KeyError(
            f"not a GasBrineBench frame: missing ion columns {missing}. "
            "Load with gasbrinebench.load() and keep the ion columns."
        )
    return df[IONS].apply(pd.to_numeric, errors="coerce")


def ionic_strength(df: pd.DataFrame) -> pd.Series:
    r"""Stoichiometric ionic strength :math:`I = \tfrac12 \sum_i m_i z_i^2`.

    Units mol/kg water, on the fully dissociated basis the ``m_*`` columns
    use. Zero for the salt-free binary rows.

    Examples
    --------
    >>> import pandas as pd, gasbrinebench as gbb
    >>> row = pd.DataFrame([{"m_Na": 0.0, "m_Cl": 2.0, "m_K": 0.0,
    ...                      "m_Ca": 1.0, "m_Mg": 0.0, "m_SO4": 0.0}])
    >>> float(gbb.ionic_strength(row).iloc[0])   # 1 mol/kg CaCl2
    3.0
    """
    ions = _ion_frame(df)
    out = 0.5 * sum(ions[c] * ION_CHARGE[c] ** 2 for c in IONS)
    return out.rename("ionic_strength")


def total_molality(df: pd.DataFrame) -> pd.Series:
    """Sum of all ion molalities [mol/kg water].

    This is the total *ion* molality, not the salt molality: 1 mol/kg NaCl
    gives 2.0, and 1 mol/kg CaCl2 gives 3.0.

    Examples
    --------
    >>> import pandas as pd, gasbrinebench as gbb
    >>> row = pd.DataFrame([{"m_Na": 1.0, "m_Cl": 1.0, "m_K": 0.0,
    ...                      "m_Ca": 0.0, "m_Mg": 0.0, "m_SO4": 0.0}])
    >>> float(gbb.total_molality(row).iloc[0])
    2.0
    """
    return _ion_frame(df).sum(axis=1).rename("total_molality")


def charge_imbalance(df: pd.DataFrame) -> pd.Series:
    r"""Net charge :math:`\sum_i m_i z_i` [eq/kg water].

    Zero for a stoichiometric brine. It is not identically zero across the
    database: a few hundred rows carry a residue of up to about 2e-3 eq/kg
    because the source printed rounded molalities. Codes that insist on an
    electrically neutral solution need to be told which ion to adjust; see
    :mod:`gasbrinebench.interop`.
    """
    ions = _ion_frame(df)
    out = sum(ions[c] * ION_CHARGE[c] for c in IONS)
    return out.rename("charge_imbalance")


def ions_present(df: pd.DataFrame) -> pd.Series:
    """Tuple of the ion names (``'Na'``, ``'SO4'``, ...) with nonzero molality.

    Empty tuple for the salt-free binaries. Ion order follows
    :data:`gasbrinebench.vocab.IONS`, so the tuple is a canonical key.
    """
    ions = _ion_frame(df)
    names = [c[2:] for c in IONS]
    out = [
        tuple(n for n, c in zip(names, IONS) if row[c] > 0)
        for _, row in ions.iterrows()
    ]
    return pd.Series(out, index=df.index, name="ions_present")


def salt_system(df: pd.DataFrame) -> pd.Series:
    """Hyphen-joined label of the ions present, ``'water'`` if there are none.

    Examples: ``'water'``, ``'Na-Cl'``, ``'Cl-Ca'``, ``'Na-Cl-K-Ca-Mg-SO4'``.

    The label names *ions*, not salts, on purpose. A brine containing Na, Cl,
    K and Ca cannot be resolved into salts without an assumption the
    measurement does not carry, so the database never makes one.
    """
    present = ions_present(df)
    out = present.map(lambda t: "-".join(t) if t else "water")
    return out.rename("salt_system")


def salt_system_kind(df: pd.DataFrame) -> pd.Series:
    """``'water'``, ``'single-salt'`` or ``'mixed-salt'`` per row.

    ``single-salt`` means exactly one cation species and one anion species are
    present, which is the composition a single dissolved salt produces.
    Anything with two or more of either is ``mixed-salt``.
    """
    ions = _ion_frame(df)
    cations = [c for c in IONS if ION_CHARGE[c] > 0]
    anions = [c for c in IONS if ION_CHARGE[c] < 0]
    n_cat = (ions[cations] > 0).sum(axis=1)
    n_an = (ions[anions] > 0).sum(axis=1)
    out = pd.Series("mixed-salt", index=df.index, dtype=object)
    out[(n_cat == 1) & (n_an == 1)] = "single-salt"
    out[(n_cat == 0) & (n_an == 0)] = "water"
    return out.rename("salt_system_kind")


# --------------------------------------------------------------------------
# molality <-> mole fraction
# --------------------------------------------------------------------------

def xc_saltfree_from_molality(m: pd.Series) -> pd.Series:
    r"""Salt-free-basis gas mole fraction from molality.

    :math:`x_c = m / (m + 1/M_W)`, with :math:`M_W` = 0.01801528 kg/mol. This
    is the identity the ``xc_saltfree`` rows in ``data/solubility.csv`` were
    built with and that ``tools/validate.py`` checks to 1e-9, so the value it
    returns should reproduce the stored sibling row.

    Examples
    --------
    >>> import pandas as pd, gasbrinebench as gbb
    >>> round(float(gbb.xc_saltfree_from_molality(pd.Series([1.0])).iloc[0]), 6)
    0.017696
    """
    m = pd.to_numeric(m, errors="coerce")
    return (m / (m + 1.0 / M_W)).rename("xc_saltfree")


def molality_from_xc_saltfree(xc: pd.Series) -> pd.Series:
    """Inverse of :func:`xc_saltfree_from_molality` [mol/kg water]."""
    xc = pd.to_numeric(xc, errors="coerce")
    return ((xc / (1.0 - xc)) / M_W).rename("solubility_molality")


def xc_saltinclusive_from_molality(
    m: pd.Series, df: pd.DataFrame
) -> pd.Series:
    r"""Salt-inclusive gas mole fraction, ions counted as separate species.

    :math:`x_c = m / (m + 1/M_W + \sum_i m_i)`, the dissolved ions being
    treated as fully dissociated solute species. For a salt-free row it
    reduces to :func:`xc_saltfree_from_molality`.

    This sibling is **derived, not measured**: the database stores only the
    salt-free basis, because that is what the sources report. Which basis a
    model expects is a convention it has to declare; converting between them
    here makes the convention explicit instead of implicit.

    Parameters
    ----------
    m : Series
        Gas molality [mol/kg water].
    df : DataFrame
        The rows ``m`` came from, for their ion columns. Must share ``m``'s
        index.
    """
    m = pd.to_numeric(m, errors="coerce")
    ms = total_molality(df).reindex(m.index)
    return (m / (m + 1.0 / M_W + ms)).rename("xc_saltinclusive")


def with_derived(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with the derived composition columns attached.

    Adds ``ionic_strength``, ``total_molality``, ``salt_system`` and
    ``salt_system_kind``. Existing columns of those names are overwritten, so
    calling it twice is harmless.
    """
    out = df.copy()
    out["ionic_strength"] = ionic_strength(df)
    out["total_molality"] = total_molality(df)
    out["salt_system"] = salt_system(df)
    out["salt_system_kind"] = salt_system_kind(df)
    return out
