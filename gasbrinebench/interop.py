"""Using GasBrineBench rows with geochemical speciation codes.

**No native exporter for PHREEQC, Geochemist's Workbench or any similar code
is provided, deliberately.** This module documents the column mapping instead,
and says why stopping there is the right call.

The obstacle is not the file syntax; it is what the syntax would have to
assert. A GasBrineBench solubility row is::

    (gas, T_K, P_bar, m_Na ... m_SO4)  ->  value [mol gas / kg water]

The brine half of that maps onto a PHREEQC ``SOLUTION`` block cleanly, and the
mapping is tabulated below. The other half does not. To reproduce the
measurement, a speciation code must be told the *gas-phase boundary
condition*: a fugacity, or a partial pressure, of the dissolved gas. The
database stores the **total** pressure of the experiment, as the sources
report it. Turning a total pressure into a gas fugacity requires

1. a water-content model, to remove water vapour from the gas phase, and
2. a fugacity coefficient for the gas at (T, P, composition), i.e. an
   equation of state.

Both are exactly the modelling steps a gas-solubility benchmark exists to
test. An exporter would have to pick one of each, bake the choice into the
emitted file, and hand the user a number that looks like data. Downstream, a
disagreement between PHREEQC and the measurement would then be partly an
artefact of the converter's own EoS choice, with nothing in the file to say
so. A wrong converter is worse than no converter.

Two smaller obstacles point the same way. PHREEQC needs a pH, and these
experiments do not report one: a CO2-charged brine sets its own pH through
the carbonate speciation the code is about to compute, so any value written
into the file is either an invention or a circularity. And the databases that
cover this pressure range at all (``pitzer.dat``, ``phreeqc.dat``) have stated
validity limits well inside the 0.1-3,500 bar span of these rows, so a
faithful export of the full database would be an export of mostly
out-of-range calculations.

What you get instead is the mapping, below and in
:func:`phreeqc_column_map`. Writing the ten lines that emit a ``SOLUTION``
block from it is easy; deciding what to put in the ``GAS_PHASE`` block is the
part that needs a person, and this module will not decide it for you.

PHREEQC ``SOLUTION`` mapping
----------------------------
Line identifiers per the PHREEQC version 3 manual, ``SOLUTION`` keyword
(U.S. Geological Survey, Techniques and Methods 6-A43).

==================  =========================  ==============================
GasBrineBench       PHREEQC SOLUTION entry     Conversion
==================  =========================  ==============================
``T_K``             ``temp``                   ``T_K - 273.15``; PHREEQC
                                               reads degrees Celsius
``P_bar``           ``pressure``               ``P_bar / 1.01325``; PHREEQC
                                               reads atmospheres
(all rows)          ``units mol/kgw``          the ``m_*`` columns already
                                               are mol per kg of water
(all rows)          ``-water 1.0``             molalities are per kg water,
                                               so one kg of water makes the
                                               molalities the amounts
``m_Na``            ``Na``                     identity
``m_K``             ``K``                      identity
``m_Ca``            ``Ca``                     identity
``m_Mg``            ``Mg``                     identity
``m_Cl``            ``Cl``                     identity
``m_SO4``           ``S(6)``                   identity; PHREEQC enters
                                               sulfate as the element S in
                                               oxidation state VI, and in
                                               molal units the number is mol
                                               S, not mol SO4
==================  =========================  ==============================

Caveats that belong in any script built from this table:

* **pH is yours to choose and to defend.** Nothing in the database constrains
  it.
* **Charge balance is not exact.** A few hundred rows carry a net charge of up
  to about 2e-3 eq/kg because the source printed rounded molalities; see
  :func:`gasbrinebench.charge_imbalance`. Either accept the residue or append
  ``charge`` to one ion, and record which.
* **The gas is missing.** The mapping above describes the brine only. Adding
  the gas is the modelling decision discussed above.

Geochemist's Workbench
----------------------
No mapping is asserted for GWB. The published input-script specification could
not be consulted while this module was written, and writing down a format from
memory is the failure mode the rest of this file argues against. The ion
columns correspond to basis species in the obvious way; the T, P and
gas-fugacity questions above are identical, and are the ones that actually
decide whether such a file is meaningful.

Examples
--------
>>> import gasbrinebench as gbb
>>> gbb.phreeqc_column_map()['m_SO4']
'S(6)'
"""

from __future__ import annotations

__all__ = ["phreeqc_column_map", "PHREEQC_COLUMN_MAP", "PHREEQC_NOTES"]

#: GasBrineBench ion column -> PHREEQC ``SOLUTION`` element name.
#: Concentrations go in unchanged under ``units mol/kgw``.
PHREEQC_COLUMN_MAP = {
    "m_Na": "Na",
    "m_K": "K",
    "m_Ca": "Ca",
    "m_Mg": "Mg",
    "m_Cl": "Cl",
    "m_SO4": "S(6)",
}

#: Unit conversions and fixed lines that go with :data:`PHREEQC_COLUMN_MAP`.
PHREEQC_NOTES = {
    "T_K": "temp = T_K - 273.15 (PHREEQC reads degrees Celsius)",
    "P_bar": "pressure = P_bar / 1.01325 (PHREEQC reads atmospheres)",
    "units": "units mol/kgw",
    "water": "-water 1.0 (molalities are per kg of water)",
    "pH": "not in the database; the user must choose and justify one",
    "gas": (
        "not exportable without a model: the database stores TOTAL pressure, "
        "and a GAS_PHASE block needs a fugacity, which requires a water-"
        "content model and an equation of state"
    ),
}


def phreeqc_column_map() -> dict:
    """The GasBrineBench ion column -> PHREEQC element-name mapping.

    Returns a copy of :data:`PHREEQC_COLUMN_MAP`. See the module docstring for
    the unit conversions, the caveats, and why no exporter is shipped.

    Examples
    --------
    >>> import gasbrinebench as gbb
    >>> sorted(gbb.phreeqc_column_map().values())
    ['Ca', 'Cl', 'K', 'Mg', 'Na', 'S(6)']
    """
    return dict(PHREEQC_COLUMN_MAP)
