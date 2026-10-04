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
['Cp_app', 'eps_r', 'miac', 'phi_osm', 'psat_ratio', 'rho']
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
    # v1.2 families
    "rho_gas",       # density of a gas-loaded solution (carries m_gas)
    "visc",          # viscosity, brine or gas-loaded (carries m_gas)
    "thermo_brine",  # apparent molar heat capacity of salt solutions
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
    "rho_gas_loaded",
    "visc",
    "Cp_app",
)

#: Properties of the brine alone: their rows carry an empty ``gas`` cell.
GAS_FREE_PROPERTIES = frozenset(
    {"rho", "phi_osm", "psat_ratio", "eps_r", "miac", "Cp_app"}
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

#: Single gases outside the seven that v1.2 adds. Their rows carry the flag
#: ``gas-out-of-scope`` and are excluded by the default loader.
OTHER_GASES = ("ar", "he", "ne", "kr", "xe", "c2h4", "c2h2", "c3h6", "c-c3h6",
               "1-c4h8", "n-c4h10", "i-c4h10", "neo-c5h12", "c-c6h12",
               "n-c6h14", "i-c8h18", "cf4", "sf6", "n2o", "h2s", "chf3",
               "chclf2", "c2h2f4", "c2h4f2")

#: Every gas code that can occur in the ``gas`` column.
ALL_GASES = GASES + OTHER_GASES

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

#: Modifier flags (column ``flags``, ``;``-separated, blank on most v1.1.1 rows).
#: See ``SCHEMA.md`` for the meaning of each.
FLAGS = (
    "gas-out-of-scope", "hydrate-regime", "condensed-phase-uncertain",
    "fugacity-as-pressure", "subfreezing", "volume-basis-uncertain",
    "pressure-unstated", "salinity-matrix", "source-caution", "stp-assumed",
    "solution-basis-converted", "differential-pressure-converted",
    "vapour-nonideality-by-authors", "minor-species-omitted",
    "calculated-not-measured", "figure-digitized", "smoothed-values",
)

#: Flags whose rows the default loader drops: rows outside the seven gases or
#: in a hydrate regime, rows with a doubtful phase or pressure basis, rows
#: below the brine's freezing point, rows whose volume basis (per litre of
#: solution or of solvent) the paper does not settle, and rows whose paper
#: states no pressure. The others (``stp-assumed``, ``source-caution``, ...)
#: are informational and the rows stay in.
DEFAULT_EXCLUDED_FLAGS = (
    "gas-out-of-scope", "hydrate-regime", "condensed-phase-uncertain",
    "fugacity-as-pressure", "subfreezing", "volume-basis-uncertain",
    "pressure-unstated", "calculated-not-measured", "figure-digitized",
)

#: Tags excluded by the default loader. ``lle-regime`` marks 354 rows (144 of them
#: propane) measured below the gas's critical temperature at or above its own
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

#: Optional column of every family CSV.
OPTIONAL_COLUMNS = ["flags", "data_origin"]

#: Audit status of a row (``data/provenance/audit_status.csv``): the result of the row-by-row comparison with the papers.
#: ``verified`` the printed digits equal the stored ones after the documented conversion; ``corrected`` the audit changed a field to the printed value;
#: ``not-verifiable`` no paper or table available, or the paper does not settle the basis; ``residual-difference`` a known difference that was not corrected.
AUDIT_STATUSES = ("verified", "corrected", "not-verifiable", "residual-difference")

#: ``load(reliable=True)`` keeps rows with audit status verified or corrected, quality not U, and without these informational flags in addition to
#: the default exclusions: each of them records a convention or caution that the paper does not settle.
RELIABLE_EXCLUDED_FLAGS = ("source-caution", "stp-assumed", "salinity-matrix", "solution-basis-converted")

#: Where a number comes from: ``table`` (printed in a table of the paper, possibly converted by a documented rule),
#: ``figure`` (read off a figure or smoothed curves because the paper prints no table) or ``calculated`` (computed
#: from an equation or a model, or estimated, and not measured).
DATA_ORIGINS = ("table", "figure", "calculated")

#: Columns the loader coerces to float. ``P_bar`` and ``uncertainty`` are
#: legitimately blank on some rows and become ``NaN``.
NUMERIC_COLUMNS = ["T_K", "P_bar", *IONS, "value", "uncertainty", "m_gas"]

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
    "rho_gas_loaded": "kg/m3",
    "visc": "mPa s",
    "Cp_app": "J/(mol K)",
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
    "rho_gas_loaded": "rho_gas",
    "visc": "visc",
    "Cp_app": "thermo_brine",
}
