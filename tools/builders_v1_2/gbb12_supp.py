"""GasBrineBench v1.2 supplementary builder.

The main database (gbb12_build.py) holds properties with an unambiguous, model-free conversion to its schema (six-ion brines).
This module collects the in-scope measurements that the main database cannot represent and writes them, WITHOUT any model-based
conversion, to a separate long-format file `supplementary_measurements.csv`:

  - properties without a main-database slot (apparent molar volume, enthalpy of dilution, Henry constants on a molality basis,
    isopiestic molality pairs, specific heat, mixing volumes, ...): value and unit as printed (the printed scale is applied, the unit
    is kept as a string);
  - solutions of salts outside the six-ion set (NaBr, LiCl, KBr, SrCl2, ...): the solutes are listed with their molalities.

Rules, all inherited from the main build: temperature in K, pressure in bar and REQUIRED (an empty pressure is allowed only for
properties that are conventionally reported without one: enthalpies, isopiestic molalities, activities, osmotic coefficients);
rows held by the mapping (misprints, literature values, duplicates, D2O, pure gases) are never exported; no value is derived
from a model or from a density that the paper does not give. Composition that cannot be turned into mol per kg of water without a
density is kept as printed in `composition_as_printed`.

Usage: python3 gbb12_supp.py [--extract DIR] [--out DIR]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gbb12_build as B
import gbb12_core as C
from gbb12_loader import MappingError, load_table

# molar masses (g/mol) of salts outside the six-ion set that occur in the transcribed tables
EXTRA_SALT_M = {"NaBr": 102.894, "LiCl": 42.394, "KBr": 119.002, "SrCl2": 158.53, "LiBr": 86.845, "CsCl": 168.358, "NaNO3": 84.995,
                "KNO3": 101.103, "NaI": 149.894, "KI": 166.003, "Li2SO4": 109.94, "BaCl2": 208.23, "NaF": 41.988, "KF": 58.097,
                "NH4Cl": 53.491, "CaBr2": 199.89, "MgBr2": 184.11, "RbCl": 120.921, "LiNO3": 68.946, "NaOH": 39.997, "KOH": 56.106,
                "NaHCO3": 84.007, "Na2CO3": 105.989, "MgSO4": 120.366}
SALT_M = {k: v[0] for k, v in C.SALT.items()}
SALT_M.update(EXTRA_SALT_M)

# properties that are conventionally reported without a pressure
P_OPTIONAL = {"isopiestic_molality", "dh_sol", "dh_dilution", "aw", "phi_osm", "phi_Cp", "gamma", "activity_coefficient", "psat_brine"}

# hold reasons of the main build that make a record eligible for the supplement (anything else stays out)
ELIGIBLE = (
    "has no converter yet",
    "outside the six-ion set",
    "no printed osmotic coefficient",
    "needs a solution density that the paper does not give",
    "osmotic coefficient of a mixture",
    "composition basis ionic_strength without an ionic_strength_rule",
    "no converter for property",
    "enthalpy of solution of a salt",
)

COLUMNS = ["dataset_id", "source", "doi", "property_class", "property_native", "gas", "T_K", "P_bar", "solutes_mol_per_kg_water", "composition_as_printed",
           "value", "value_unit", "value_what", "value2", "value2_unit", "value2_what", "reference_salt", "uncertainty", "quality", "tag",
           "src_table", "row"]


def norm_salt_name(name):
    n = re.sub(r"[\s_\-]", "", name or "").replace("₂", "2").replace("₄", "4")
    for k in SALT_M:
        if n.lower() == k.lower():
            return k
    return None


def solutes_string(rec):
    """Return (mol per kg water string or '', composition as printed). The string is built only for a molality basis or for
    mass or mole fractions of salts with a known molar mass."""
    comp, basis = rec.get("comp") or {}, rec.get("comp_basis") or "none"
    printed = "; ".join(f"{k}={v[0]} {v[1]}".strip() for k, v in comp.items())
    printed = f"basis={basis}; {printed}" if printed else (f"none; {rec.get('other_species') or ''}".strip("; "))
    if not comp or basis not in ("molality", "mass_percent", "mass_fraction", "mole_fraction"):
        return "", printed
    vals = {}
    for name, (val, unit) in comp.items():
        salt = norm_salt_name(name)
        x = B.f(val)
        if salt is None or x is None:
            return "", printed
        vals[salt] = (x, unit)
    if basis == "molality":
        try:
            out = {s: x * B.mol_unit_factor(u) for s, (x, u) in vals.items()}
        except B.Hold:
            return "", printed
    else:
        scale = 0.01 if basis == "mass_percent" else 1.0
        total = sum(x for x, _ in vals.values()) * scale
        if not 0.0 <= total < 1.0:
            return "", printed
        if basis == "mole_fraction":
            out = {s: 1000.0 * x / ((1.0 - total) * C.M_W) for s, (x, _) in vals.items()}
        else:
            out = {s: 1000.0 * (x * scale) / (SALT_M[s] * (1.0 - total)) for s, (x, _) in vals.items()}
    return ";".join(f"{s}:{float(f'{m:.8g}')}" for s, m in out.items()), printed


NOT_A_MEASUREMENT = re.compile(r"critical (pressure|temperature|locus)|fluid-phase boundary|filling composition|\(synthetic|synthetic rows|overall (water )?mole fraction", re.I)


def property_class(prop, unit, gas, what=""):
    """Coarse class for the supplement, from the native property, the printed unit and the mapping's description of the column."""
    u, w = (unit or "").lower(), (what or "").lower()
    if prop == "isopiestic_molality":
        return "isopiestic_pair"
    if re.search(r"excess molar volume|molar volume of (the |a )?(homogeneous )?(water-)?\w*[- ]?(water )?mixture|molar volume of homogeneous", w):
        return "mixture_volume"
    if prop == "pmv" or (prop == "other" and re.search(r"cm3/mol|m3/mol", u) and "apparent" in w or prop == "pmv"):
        return "apparent_molar_volume"
    if prop == "other" and re.search(r"cm3/mol|m3/mol", u):
        return "mixture_volume" if "mixture" in w else "apparent_molar_volume"
    if prop == "dh_dilution":
        return "enthalpy_of_dilution"
    if prop == "dh_sol":
        return "enthalpy_of_dissolution"
    if prop == "henry":
        return "henry_constant"
    if prop in ("aw", "phi_osm", "psat_brine"):
        return "water_activity"
    if re.search(r"bulk compression|dv/dp|\(dv/dp\)", w) or "relative volume decrease" in u or "cm3_per_g_per_atm" in u:
        return "compression"
    if "enhancement factor" in w or "enhancement" in u:
        return "water_vapour_enhancement"
    if prop in ("phi_Cp",) or re.search(r"j_per_kg_k|j/\(kg|j/\(mol", u):
        return "heat_capacity"
    if prop in ("rho", "rho_diff") or re.search(r"kg/m3|g/cm3", u):
        return "density"
    if prop in ("bunsen", "ostwald"):
        return "gas_solubility_coefficient"
    if prop in ("solubility_x", "y_h2o", "solubility_molality") or gas:
        return "gas_solubility_other_basis"
    return "other"


def eligible(reason):
    return reason is not None and any(e in reason for e in ELIGIBLE)


def _reference_salt(mapping, rec):
    """The reference salt of an isopiestic series: a name, or the name of the column that holds it in each row."""
    r = mapping.get("reference_salt", "")
    if isinstance(r, dict):
        return str((rec.get("raw") or {}).get(r.get("col", ""), "")).strip()
    return r


def build_supp_table(extract_dir, slug, n):
    raw_map = json.load(open(os.path.join(extract_dir, slug, f"mapping_{n}.json")))
    if raw_map.get("hold_table") or raw_map.get("duplicate_of"):
        return [], []
    mapping, paper, recs = load_table(extract_dir, slug, n)
    paper["slug_"] = slug
    rows, skipped = [], []
    for rec in recs:
        if rec.get("held_reason") or rec.get("duplicate_row") or rec.get("from_literature_row"):
            continue
        prop = rec.get("property")
        # the main build decides first: only records it held back for an eligible reason enter the supplement
        try:
            conv = B.CONVERTERS.get(prop)
            if conv is not None:
                T_K, P_bar = B.convert_T_P(rec, need_P=(prop not in B.NO_PRESSURE_OK))
                ions, ctags = B.comp_to_ions(rec, None)
                conv(rec, mapping, T_K, P_bar, ions, ctags)
                continue  # built by the main database
        except B.Hold as h:
            if not eligible(str(h)):
                skipped.append((rec["idx"], str(h)))
                continue
        except (NotImplementedError, ValueError, MappingError):
            continue
        gas = (rec.get("gas") or "").lower()
        if gas == "mixture":
            skipped.append((rec["idx"], "gas-phase mixture"))
            continue
        try:
            T_K, P_bar = B.convert_T_P(rec, need_P=(prop not in P_OPTIONAL))
        except B.Hold as h:
            skipped.append((rec["idx"], str(h)))
            continue
        v = B.f(rec["value"])
        if v is None:
            skipped.append((rec["idx"], "value missing"))
            continue
        P_out = "" if P_bar is None else round(B.total_pressure(rec, P_bar, T_K), 4)
        sol, printed = solutes_string(rec)
        cols = mapping.get("columns", {})
        v2 = B.f(rec.get("value2")) if rec.get("value2") is not None else None
        unc = B.f(rec.get("uncertainty"))
        tags = set(mapping.get("row_tag_all") or [])
        if mapping.get("caution"):
            tags.add("source-caution")
        if (rec.get("regime") or "") in ("hydrate", "lle"):
            tags.add(rec["regime"] + "-regime")
        what1 = (cols.get("value") or {}).get("what", "")
        if NOT_A_MEASUREMENT.search(what1):
            skipped.append((rec["idx"], "critical locus, phase boundary or synthetic filling composition: not a property of the solution"))
            continue
        row = B.row_template(paper, mapping, n, rec)
        row.update({"doi": paper.get("doi", slug), "property_class": property_class(prop, rec["value_unit"], gas, what1), "property_native": prop, "gas": gas, "T_K": round(T_K, 3), "P_bar": P_out,
                    "solutes_mol_per_kg_water": sol, "composition_as_printed": printed,
                    "value": float(f"{v * rec['value_scale']:.10g}"), "value_unit": rec["value_unit"],
                    "value_what": (cols.get("value") or {}).get("what", ""),
                    "value2": "" if v2 is None else float(f"{v2 * rec.get('value2_scale', 1.0):.10g}"),
                    "value2_unit": rec.get("value2_unit", "") if v2 is not None else "",
                    "value2_what": (cols.get("value2") or {}).get("what", "") if v2 is not None else "",
                    "reference_salt": _reference_salt(mapping, rec),
                    "uncertainty": "" if unc is None else unc, "tag": ";".join(sorted(tags)), "row": rec["idx"]})
        rows.append(row)
    return rows, skipped


def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--extract", default=os.path.join(here, "..", "extract"))
    ap.add_argument("--out", default=os.path.join(here, "out"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    all_rows, report = [], []
    for pj in sorted(os.listdir(a.extract)):
        base = os.path.join(a.extract, pj)
        if not os.path.isfile(os.path.join(base, "paper.json")):
            continue
        paper = json.load(open(os.path.join(base, "paper.json")))
        if paper.get("status") not in ("verified_pass2", "verified_html"):
            continue
        for fn in sorted(os.listdir(base)):
            m = re.match(r"mapping_(.+)\.json$", fn)
            if not m or not os.path.exists(os.path.join(base, f"table_{m.group(1)}.csv")):
                continue
            try:
                rows, skipped = build_supp_table(a.extract, pj, m.group(1))
            except (MappingError, ValueError, KeyError) as e:
                report.append({"slug": pj, "table": m.group(1), "exported": 0, "not_exported": 0, "reasons": f"TABLE ERROR: {str(e)[:150]}"})
                continue
            if rows or skipped:
                reasons = Counter(r for _, r in skipped)
                report.append({"slug": pj, "table": m.group(1), "exported": len(rows), "not_exported": len(skipped),
                               "reasons": "; ".join(f"{k} (x{v})" for k, v in reasons.most_common(3))})
            all_rows.extend(rows)
    with open(os.path.join(a.out, "supplementary_measurements.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for r in all_rows:
            w.writerow({k: r.get(k, "") for k in COLUMNS})
    with open(os.path.join(a.out, "supplementary_report.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["slug", "table", "exported", "not_exported", "reasons"])
        w.writeheader()
        w.writerows(report)
    print(f"{len(all_rows)} supplementary rows from {sum(1 for r in report if r['exported'])} tables")
    print("by class:", dict(Counter(r["property_class"] for r in all_rows)))


if __name__ == "__main__":
    main()
