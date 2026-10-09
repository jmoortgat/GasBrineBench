# Screening criteria (title + abstract level)

Database scope: experimental data on gas + water/brine systems.
Gases in scope: CO2, CH4, H2, N2, O2, C2H6, C3H8 (and mixtures of these). Other gases (He, Ar, H2S, CO, NH3, noble gases,
natural-gas mixtures with heavier hydrocarbons) are flagged OTHER_GAS.
Temperature about 273-633 K, pressure up to about 3500 bar, salts among NaCl, KCl, CaCl2, MgCl2, Na2SO4 (and mixtures).

Properties in scope (A): gas solubility in water/brine; water content of the gas-rich phase; ternary gas-mixture + water;
brine density (gas-free or gas-saturated); osmotic/activity coefficient of the aqueous salts; brine vapor pressure/boiling-point elevation;
enthalpy of solution of gas in water/brine; static permittivity of aqueous electrolytes.
Extension properties (B): apparent molar enthalpy/heat capacity of brines, partial molar volume/heat capacity of dissolved gases,
speed of sound/compressibility of brines.

Decision codes, exactly one per work:
- INCLUDE: abstract states new experimental measurements of an (A) property for a gas/salt/range in scope.
- EXTENSION: new experimental measurements of a (B) property in scope.
- OTHER_GAS: new experimental data of an (A) property but for a gas outside the seven.
- MAYBE: plausibly reports experimental data in scope but the abstract does not make that clear (needs full text).
- EXCLUDE_MODEL: modelling, simulation, correlation or review without new measurements.
- EXCLUDE_SCOPE: experimental but out of scope (hydrates only, oil/organic/IL solvent, adsorption, geochemistry/mineral, below 273 K ice only, wrong property, etc.).
- EXCLUDE_UNRELATED: not about the topic at all.
A short reason (max 15 words) and, if INCLUDE/EXTENSION/OTHER_GAS/MAYBE, the gas(es) and property(ies).
