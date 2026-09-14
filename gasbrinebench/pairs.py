"""The molality / mole-fraction sibling rows, joined into one wide frame.

``data/solubility.csv`` stores a gas solubility twice when the source reports
both conventions: once as ``solubility_molality`` [mol gas / kg water] and
once as ``xc_saltfree``, the salt-free-basis gas mole fraction. They are
separate rows at the same state, and ``tools/validate.py`` checks that the
pair agrees to 1e-9.

Two rows per point is right for a long-format database and wrong for plotting
or scoring, so :func:`solubility_pairs` pivots them back together and adds the
salt-inclusive sibling, which nobody measures but many models expect.

Examples
--------
>>> import gasbrinebench as gbb
>>> pairs = gbb.solubility_pairs(gbb.load('solubility', gas='co2'))
>>> list(pairs.columns[-4:])
['solubility_molality', 'xc_saltfree', 'xc_saltfree_derived', 'xc_saltinclusive']
"""

from __future__ import annotations

import pandas as pd

from .derived import (
    xc_saltfree_from_molality,
    xc_saltinclusive_from_molality,
)
from .vocab import IONS

__all__ = ["solubility_pairs"]

#: Columns that identify one measured solubility point.
_KEY = ["dataset_id", "source", "gas", "T_K", "P_bar", *IONS]


def solubility_pairs(df: pd.DataFrame) -> pd.DataFrame:
    """One row per measured solubility point, both bases side by side.

    Parameters
    ----------
    df : DataFrame
        Any GasBrineBench frame. Rows of other properties are ignored.

    Returns
    -------
    DataFrame
        The key columns, the row metadata (``quality``, ``tag``, and the
        derived composition columns if present), then four value columns:

        ``solubility_molality``
            as stored [mol gas / kg water].
        ``xc_saltfree``
            as stored, or ``NaN`` where the source reported only a molality.
        ``xc_saltfree_derived``
            recomputed from ``solubility_molality``. Equal to ``xc_saltfree``
            to 1e-9 wherever both exist; it fills the gaps where the stored
            sibling is absent.
        ``xc_saltinclusive``
            derived, with the dissolved ions counted as species. Not a
            measured quantity -- see
            :func:`gasbrinebench.xc_saltinclusive_from_molality`.

    Notes
    -----
    ``uncertainty`` is not carried through: the two sibling rows may state it
    in different units (mol/kg against mole fraction), and silently picking
    one would misattribute it. Read it from the long frame.

    Pairing respects **row order**. The state columns are not a unique key --
    a few sources report replicate measurements at one state -- so the n-th
    molality row of a state group is matched with the n-th mole-fraction row
    of that group, which is the order the builders wrote them in. Pass a frame
    in file order (anything from :func:`gasbrinebench.load` or
    :func:`gasbrinebench.select` is); a shuffled frame will pair replicates
    arbitrarily.

    Examples
    --------
    >>> import gasbrinebench as gbb
    >>> p = gbb.solubility_pairs(gbb.load('solubility', gas='h2'))
    >>> bool((p['xc_saltfree'] - p['xc_saltfree_derived']).abs().max() < 1e-9)
    True
    """
    sol = df[df["property"] == "solubility_molality"].copy()
    xcs = df[df["property"] == "xc_saltfree"].copy()

    if sol.empty:
        return sol.drop(columns=["property", "value", "uncertainty"],
                        errors="ignore")

    keep = [
        c
        for c in sol.columns
        if c not in ("property", "value", "uncertainty")
    ]
    out = sol[keep].copy()
    out["solubility_molality"] = pd.to_numeric(sol["value"], errors="coerce")

    # The state columns do not uniquely identify a row: a few sources report
    # replicate measurements at one state (PORTIER_2005 has nine). The two
    # sibling rows of a point are written consecutively by the builders, so
    # the n-th molality row of a state group pairs with the n-th mole-fraction
    # row of the same group. Matching on the state alone would mis-pair the
    # replicates and silently break the 1e-9 identity.
    out["_occ"] = out.groupby(_KEY, dropna=False).cumcount()
    if xcs.empty:
        out["xc_saltfree"] = float("nan")
    else:
        xcs["_occ"] = xcs.groupby(_KEY, dropna=False).cumcount()
        lookup = xcs[[*_KEY, "_occ", "value"]].rename(
            columns={"value": "xc_saltfree"}
        )
        lookup["xc_saltfree"] = pd.to_numeric(
            lookup["xc_saltfree"], errors="coerce"
        )
        out = out.merge(lookup, on=[*_KEY, "_occ"], how="left")
    out = out.drop(columns="_occ")

    out["xc_saltfree_derived"] = xc_saltfree_from_molality(
        out["solubility_molality"]
    )
    out["xc_saltinclusive"] = xc_saltinclusive_from_molality(
        out["solubility_molality"], out
    )
    return out.reset_index(drop=True)
