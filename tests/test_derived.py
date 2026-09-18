"""Derived quantities, checked against hand arithmetic and against the CSVs."""

from __future__ import annotations

import pandas as pd
import pytest

import gasbrinebench as gbb
from gasbrinebench.vocab import IONS, M_W


def _row(**kw):
    base = {c: 0.0 for c in IONS}
    base.update({f"m_{k}": v for k, v in kw.items()})
    return pd.DataFrame([base])


def test_ionic_strength_by_hand():
    assert float(gbb.ionic_strength(_row(Na=1, Cl=1)).iloc[0]) == 1.0
    assert float(gbb.ionic_strength(_row(Ca=1, Cl=2)).iloc[0]) == 3.0
    assert float(gbb.ionic_strength(_row(Mg=1, SO4=1)).iloc[0]) == 4.0
    assert float(gbb.ionic_strength(_row()).iloc[0]) == 0.0


def test_total_molality_counts_ions_not_salts():
    assert float(gbb.total_molality(_row(Na=1, Cl=1)).iloc[0]) == 2.0
    assert float(gbb.total_molality(_row(Ca=1, Cl=2)).iloc[0]) == 3.0


def test_charge_imbalance_zero_for_a_stoichiometric_brine():
    assert float(gbb.charge_imbalance(_row(Ca=1, Cl=2)).iloc[0]) == 0.0


def test_database_charge_imbalance_is_only_rounding(all_rows):
    """A documented fact the interop notes depend on."""
    assert gbb.charge_imbalance(all_rows).abs().max() < 5e-3


def test_ionic_strength_range_over_the_database(all_rows):
    I = gbb.ionic_strength(all_rows)
    assert I.min() == 0.0
    assert I.max() == 18.0


def test_salt_system_labels():
    assert gbb.salt_system(_row()).iloc[0] == "water"
    assert gbb.salt_system(_row(Na=1, Cl=1)).iloc[0] == "Na-Cl"
    assert gbb.salt_system(_row(Cl=2, Ca=1)).iloc[0] == "Cl-Ca"


def test_salt_system_kind():
    assert gbb.salt_system_kind(_row()).iloc[0] == "water"
    assert gbb.salt_system_kind(_row(Na=1, Cl=1)).iloc[0] == "single-salt"
    assert gbb.salt_system_kind(_row(Na=2, Cl=1, SO4=0.5)).iloc[0] == "mixed-salt"
    assert gbb.salt_system_kind(_row(Na=1, K=1, Cl=2)).iloc[0] == "mixed-salt"


def test_ions_present_is_a_canonical_tuple():
    assert gbb.ions_present(_row(Cl=2, Ca=1)).iloc[0] == ("Cl", "Ca")
    assert gbb.ions_present(_row()).iloc[0] == ()


def test_mole_fraction_round_trip():
    m = pd.Series([0.01, 0.5, 1.0, 2.0])
    back = gbb.molality_from_xc_saltfree(gbb.xc_saltfree_from_molality(m))
    pd.testing.assert_series_equal(
        back, m.rename("solubility_molality"), rtol=1e-12
    )


def test_xc_saltfree_matches_the_stored_sibling_rows():
    """SCHEMA.md rule 2, the same identity tools/validate.py checks."""
    pairs = gbb.solubility_pairs(gbb.load("solubility"))
    both = pairs.dropna(subset=["xc_saltfree"])
    assert len(both) > 1000
    dev = (both["xc_saltfree"] - both["xc_saltfree_derived"]).abs()
    tol = 1e-9 + 1e-6 * both["xc_saltfree"].abs()   # the validator's tolerance
    assert (dev <= tol).all()


def test_replicate_states_pair_by_row_order():
    """PORTIER_2005 repeats states; pairing on the state alone mis-matches."""
    rep = gbb.load("solubility", source="PORTIER_2005")
    pairs = gbb.solubility_pairs(rep)
    both = pairs.dropna(subset=["xc_saltfree"])
    dev = (both["xc_saltfree"] - both["xc_saltfree_derived"]).abs()
    assert (dev <= 1e-9 + 1e-6 * both["xc_saltfree"].abs()).all()
    assert rep.duplicated(
        ["dataset_id", "source", "T_K", "P_bar", "property"]
    ).any()


def test_saltinclusive_is_below_saltfree_in_brine():
    df = _row(Na=6, Cl=6)
    m = pd.Series([0.5], index=df.index)
    free = float(gbb.xc_saltfree_from_molality(m).iloc[0])
    incl = float(gbb.xc_saltinclusive_from_molality(m, df).iloc[0])
    assert incl < free
    expected = 0.5 / (0.5 + 1.0 / M_W + 12.0)
    assert incl == pytest.approx(expected)


def test_saltinclusive_reduces_to_saltfree_in_pure_water():
    df = _row()
    m = pd.Series([0.5], index=df.index)
    assert float(gbb.xc_saltinclusive_from_molality(m, df).iloc[0]) == pytest.approx(
        float(gbb.xc_saltfree_from_molality(m).iloc[0])
    )


def test_with_derived_is_idempotent(default_rows):
    once = gbb.with_derived(default_rows)
    twice = gbb.with_derived(once)
    pd.testing.assert_frame_equal(once, twice)


def test_derived_on_a_non_schema_frame_raises():
    with pytest.raises(KeyError, match="ion columns"):
        gbb.ionic_strength(pd.DataFrame({"x": [1]}))


def test_solubility_pairs_shape_and_columns():
    pairs = gbb.solubility_pairs(gbb.load("solubility", gas="co2"))
    assert list(pairs.columns[-4:]) == [
        "solubility_molality",
        "xc_saltfree",
        "xc_saltfree_derived",
        "xc_saltinclusive",
    ]
    assert len(pairs) == 2837
    assert "value" not in pairs.columns


def test_solubility_pairs_ignores_other_properties():
    pairs = gbb.solubility_pairs(gbb.load("rho"))
    assert len(pairs) == 0
