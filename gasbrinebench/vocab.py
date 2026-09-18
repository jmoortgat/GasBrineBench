"""The controlled vocabularies of the GasBrineBench row schema.

Everything here mirrors ``SCHEMA.md`` and the constants ``tools/validate.py``
enforces. Import these rather than retyping string literals, so that a typo in
a filter argument is an error instead of a silently empty result.

Examples
--------
>>> from gasbrinebench import vocab
>>> vocab.IONS
['m_Na', 'm_Cl', 'm_K', 'm_Ca', 'm_Mg', 'm_SO4']
>>> vocab.ION_CHARGE['m_SO4']
-2
>>> sorted(vocab.GAS_FREE_PROPERTIES)
['eps_r', 'miac', 'phi_osm', 'psat_ratio', 'rho']
"""

from __future__ import annotations

#: Molar mass of water [kg/mol], the constant the molality/mole-fraction
#: sibling rows were built with (``tools/validate.py`` checks the pair to
#: 1e-9 using this value).
M_W = 0.01801528

#: Property-family CSVs, one per ``data/<family>.csv``.
FAMILIES = (
    "solubility",
    "y_h2o",
    "rho",
    "phi_osm",
    "dh_sol",
    "psat_ratio",
    "eps_r",
    # CO2 + CH4 + water. Carries one extra column, `y_co2_dry`, because the
    # gas-phase split is an independent state variable in a ternary and has
    # nowhere to live in the single-gas schema. See data/README.md.
    "ternary",
)

#: The ``property`` vocabulary. ``miac`` is declared in ``SCHEMA.md`` and has
#: no rows yet.
PROPERTIES = (
    "solubility_molality",
    "xc_saltfree",
    "y_h2o",
    "rho",
    "phi_osm",
    "psat_ratio",
    "dh_sol",
    "eps_r",
    "miac",
)

#: Properties of the brine alone: their rows carry an empty ``gas`` cell.
GAS_FREE_PROPERTIES = frozenset(
    {"rho", "phi_osm", "psat_ratio", "eps_r", "miac"}
)

#: Properties for which ``P_bar`` is legitimately blank. For ``psat_ratio``
#: the pressure *is* the measured quantity and is carried in ``value``.
BLANK_PRESSURE_PROPERTIES = frozenset({"psat_ratio"})

#: Gas codes used in the ``gas`` column.
GASES = ("co2", "ch4", "h2", "n2", "o2", "c2h6", "c3h8",
         # Mixed gas phase, used only by the ternary family and only
         # for its water-content rows, where the measurement is a
         # property of the mixture rather than of either component.
         "co2-ch4")

#: Ion molality columns, in the order the CSVs carry them. Units are
#: mol per kg of water, fully dissociated basis.
IONS = ["m_Na", "m_Cl", "m_K", "m_Ca", "m_Mg", "m_SO4"]

#: Formal charge of each ion, keyed by its molality column.
ION_CHARGE = {
    "m_Na": +1,
    "m_Cl": -1,
    "m_K": +1,
    "m_Ca": +2,
    "m_Mg": +2,
    "m_SO4": -2,
}

#: Quality codes. ``R`` recommended (independently corroborated), ``T``
#: tentative (plausible, single-source), ``U`` uncertain (contradicted,
#: author-flagged or unverifiable). See ``data/QUALITY.md``.
QUALITY_CODES = ("R", "T", "U")

#: Fit/test partition. See ``SCHEMA.md``.
TAGS = ("fit-eligible", "test-only", "lle-regime")

#: Tags excluded by the default loader. ``lle-regime`` marks the 144 propane
#: rows measured below propane's critical temperature at or above its own
#: vapour pressure: the hydrocarbon-rich phase is a *liquid*, so the point is
#: a liquid-liquid mutual solubility and not a gas solubility
#: (``data/QUALITY.md`` Sec. 7). They are good data about a different
#: property; scoring them as gas solubility is a category error, so they are
#: dropped unless asked for.
DEFAULT_EXCLUDED_TAGS = ("lle-regime",)

#: The row schema, in CSV column order.
COLUMNS = [
    "dataset_id",
    "source",
    "gas",
    "property",
    "T_K",
    "P_bar",
    *IONS,
    "value",
    "uncertainty",
    "quality",
    "tag",
]

#: Columns the loader coerces to float. ``P_bar`` and ``uncertainty`` are
#: legitimately blank on some rows and become ``NaN``.
NUMERIC_COLUMNS = ["T_K", "P_bar", *IONS, "value", "uncertainty"]

#: Columns the loader adds; see :mod:`gasbrinebench.derived`.
DERIVED_COLUMNS = ["family", "ionic_strength", "total_molality", "salt_system"]

#: Canonical unit of ``value`` in each property family.
UNITS = {
    "solubility_molality": "mol gas / kg water",
    "xc_saltfree": "mole fraction (salt-free basis)",
    "y_h2o": "mole fraction",
    "rho": "kg/m3",
    "phi_osm": "dimensionless",
    "psat_ratio": "dimensionless",
    "dh_sol": "kJ/mol gas",
    "eps_r": "dimensionless",
    "miac": "dimensionless",
}

#: Which family CSV each property lives in.
PROPERTY_FAMILY = {
    "solubility_molality": "solubility",
    "xc_saltfree": "solubility",
    "y_h2o": "y_h2o",
    "rho": "rho",
    "phi_osm": "phi_osm",
    "psat_ratio": "psat_ratio",
    "dh_sol": "dh_sol",
    "eps_r": "eps_r",
    "miac": "miac",
}
