"""Row selection: every axis, and the promise that typos raise."""

from __future__ import annotations

import pytest

import gasbrinebench as gbb
from gasbrinebench.vocab import GASES, IONS


def test_gas_filter(default_rows):
    co2 = gbb.select(default_rows, gas="co2")
    assert set(co2["gas"]) == {"co2"}


def test_gas_filter_is_case_insensitive(default_rows):
    assert len(gbb.select(default_rows, gas="CO2")) == len(
        gbb.select(default_rows, gas="co2")
    )


def test_empty_gas_selects_the_brine_only_rows(default_rows):
    brine = gbb.select(default_rows, gas="")
    assert set(brine["property"]) <= {"rho", "phi_osm", "psat_ratio", "eps_r"}


def test_gas_typo_raises_and_names_the_vocabulary(default_rows):
    with pytest.raises(ValueError) as exc:
        gbb.select(default_rows, gas="CO_2")
    for g in GASES:
        assert g in str(exc.value)


def test_quality_and_tag_vocabularies(default_rows):
    assert set(gbb.select(default_rows, quality="r")["quality"]) == {"R"}
    assert set(gbb.select(default_rows, tag="test-only")["tag"]) == {
        "test-only"
    }
    with pytest.raises(ValueError, match="quality code"):
        gbb.select(default_rows, quality="A")
    with pytest.raises(ValueError, match="tag"):
        gbb.select(default_rows, tag="training")


def test_temperature_and_pressure_windows(default_rows):
    hot = gbb.select(default_rows, T=(400, 450))
    assert hot["T_K"].between(400, 450).all()
    deep = gbb.select(default_rows, P=(500, None))
    assert (deep["P_bar"] >= 500).all()


def test_pressure_window_drops_blank_pressure_rows(default_rows):
    """psat_ratio rows carry no P and must not sneak through an open window."""
    got = gbb.select(default_rows, P=(None, None))
    assert "psat_ratio" not in set(got["property"])


def test_scalar_window_is_a_helpful_type_error(default_rows):
    with pytest.raises(TypeError, match=r"\(low, high\)"):
        gbb.select(default_rows, T=323.0)


def test_ionic_strength_window(default_rows):
    strong = gbb.select(default_rows, ionic_strength=(6, None))
    assert (gbb.ionic_strength(strong) >= 6).all()
    assert len(strong) > 0


def test_total_molality_window_works_without_derived_columns():
    raw = gbb.load("rho", derive=False)
    got = gbb.select(raw, total_molality=(0, 2))
    assert (gbb.total_molality(got) <= 2).all()


def test_salt_system_kinds(default_rows):
    single = gbb.select(default_rows, salt_system="single-salt")
    assert set(gbb.salt_system_kind(single)) == {"single-salt"}
    mixed = gbb.select(default_rows, salt_system="mixed-salt")
    assert set(gbb.salt_system_kind(mixed)) == {"mixed-salt"}
    water = gbb.select(default_rows, salt_system="water")
    assert (gbb.total_molality(water) == 0).all()
    assert len(single) + len(mixed) + len(water) == len(default_rows)


def test_salt_system_explicit_label(default_rows):
    nacl = gbb.select(default_rows, salt_system="Na-Cl")
    assert set(gbb.salt_system(nacl)) == {"Na-Cl"}


def test_salt_system_typo_raises(default_rows):
    with pytest.raises(ValueError, match="unknown salt_system"):
        gbb.select(default_rows, salt_system="NaCl")


def test_ions_present_versus_exactly(default_rows):
    has_na = gbb.select(default_rows, ions="Na")
    assert (has_na["m_Na"] > 0).all()
    only_nacl = gbb.select(default_rows, ions_exactly=["Na", "Cl"])
    assert (only_nacl["m_K"] == 0).all()
    assert len(only_nacl) < len(has_na)
    binaries = gbb.select(default_rows, ions_exactly=[])
    assert (gbb.total_molality(binaries) == 0).all()


def test_ion_names_accept_the_column_spelling(default_rows):
    assert len(gbb.select(default_rows, ions="m_SO4")) == len(
        gbb.select(default_rows, ions="SO4")
    )


def test_unknown_ion_raises(default_rows):
    with pytest.raises(ValueError, match="unknown ion"):
        gbb.select(default_rows, ions="Br")


def test_salt_free_flag(default_rows):
    free = gbb.select(default_rows, salt_free=True)
    salty = gbb.select(default_rows, salt_free=False)
    assert len(free) + len(salty) == len(default_rows)
    assert (free[IONS].sum(axis=1) == 0).all()


def test_filters_are_anded(default_rows):
    got = gbb.select(
        default_rows, gas="co2", property="solubility_molality",
        T=(322, 324), salt_system="Na-Cl",
    )
    assert len(got) > 0
    assert set(got["gas"]) == {"co2"}
    assert got["T_K"].between(322, 324).all()


def test_index_is_preserved_for_realignment(default_rows):
    got = gbb.select(default_rows, gas="ch4")
    assert got.index.isin(default_rows.index).all()


def test_exclude_tags_argument(default_rows):
    got = gbb.select(default_rows, exclude_tags=["fit-eligible"])
    assert "fit-eligible" not in set(got["tag"])


def test_family_filter_needs_the_family_column():
    raw = gbb.load_family("rho").drop(columns=["family"])
    with pytest.raises(KeyError, match="family"):
        gbb.select(raw, family="rho")
