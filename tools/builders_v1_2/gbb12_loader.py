"""Read one extracted table plus its mapping and resolve it into per-row records.

A record is a dict with raw printed strings resolved through the mapping:
  idx, T (str|None), T_unit, P, P_unit, P_basis, value (str|None), value_unit, value_scale,
  uncertainty, uncertainty_unit, gas, regime, comp (dict path->(str value, unit)), raw (dict header->str)
Resolution order for each quantity: the row's own column cell, else the group-row constant that applies to the row, else the mapping's
column constant. Label rows and skip_rows never produce records. Unknown mapping shapes raise MappingError.
"""
from __future__ import annotations

import csv
import json
import os
import re

from gbb12_core import parse_float, parse_scale, unit_scale_from_name


class MappingError(Exception):
    pass


def _norm(s):
    return re.sub(r"\s+", " ", (s or "").strip()).lower()


def _find_col(header, colname):
    """Locate a mapped column: exact header text first, then case-insensitive, then ignoring all non-alphanumerics.
    A looser level that matches more than one header is an error (for example `h_2,1` and `H_2,1` differ only by case)."""
    if colname in (None, ""):
        return None
    stripped = [(x or "").strip() for x in header]
    if colname.strip() in stripped:
        return stripped.index(colname.strip())
    h = [_norm(x) for x in header]
    n = _norm(colname)
    if h.count(n) == 1:
        return h.index(n)
    if h.count(n) > 1:
        raise MappingError(f"column {colname!r} is ambiguous in header {header}")
    key = lambda s: re.sub(r"[^a-z0-9]", "", s)
    hk = [key(x) for x in h]
    if hk.count(key(n)) == 1:
        return hk.index(key(n))
    if hk.count(key(n)) > 1:
        raise MappingError(f"column {colname!r} is ambiguous in header {header}")
    raise MappingError(f"column {colname!r} not found in header {header}")


def _split_value_unit(v):
    """'1.00 N' -> ('1.00', 'N'); {'value': '1', 'unit': 'mol/kg'} -> ('1','mol/kg'); '30' -> ('30', '')."""
    if isinstance(v, dict):
        return str(v.get("value", "")), str(v.get("unit", ""))
    s = str(v).strip()
    m = re.match(r"^([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*(.*)$", s)
    if m:
        return m.group(1), m.group(2).strip()
    return s, ""


def load_table(extract_dir: str, slug: str, n: str):
    """Return (mapping, paper, records). n is the table suffix as in table_<n>.csv (e.g. '3', '1a', '5_group2')."""
    base = os.path.join(extract_dir, slug)
    mapping = json.load(open(os.path.join(base, f"mapping_{n}.json")))
    paper = json.load(open(os.path.join(base, "paper.json")))
    rows = list(csv.reader(open(os.path.join(base, f"table_{n}.csv"), newline="", encoding="utf-8")))
    header, data = rows[0], rows[1:]

    cols = mapping.get("columns") or {}
    comp = mapping.get("composition") or {}

    skip = set()
    for s in mapping.get("skip_rows") or []:
        for r in s.get("rows", []):
            skip.add(int(r))

    # group rows: label_row -> sets (normalised to list of (path, value, unit)); applied to following rows until the next label row
    groups = []
    for g in mapping.get("group_rows") or []:
        sets = g.get("sets")
        items = []
        if isinstance(sets, dict):
            for path, v in sets.items():
                val, unit = _split_value_unit(v)
                items.append((path, val, unit))
        elif isinstance(sets, list):
            for x in sets:
                if isinstance(x.get("value"), dict) and "col" in x["value"]:
                    items.append((x["path"], dict(x["value"]), x["value"].get("unit", "")))
                    continue
                val, unit = _split_value_unit(x)
                items.append((x["path"], val, x.get("unit", unit)))
        else:
            raise MappingError(f"group_rows sets has unexpected form {type(sets)}")
        groups.append((int(g["label_row"]), items))
    groups.sort()
    label_rows = {g[0] for g in groups}

    def active_group_sets(i):
        out = {}
        # the latest label row at or before i, i exclusive
        cur = None
        for lr, items in groups:
            if lr < i:
                cur = items
            else:
                break
        if cur:
            for path, val, unit in cur:
                out[path] = (val, unit)
        return out

    def colspec(name):
        c = cols.get(name)
        if not isinstance(c, dict):
            return None
        return c

    idx = {}
    for key in ("T", "P", "value", "value2", "value3", "uncertainty", "uncertainty2", "m_gas"):
        c = colspec(key)
        if c is not None:
            idx[key] = _find_col(header, c.get("col"))

    # per-row overrides written by the extraction agents in several spellings; all normalised here to data-row indices
    def rowset(entries):
        out = {}
        if isinstance(entries, dict):
            entries = [entries]
        for e in entries or []:
            val = e.get("regime") or (e.get("set") or {}).get("regime")
            for r in e.get("rows", []):
                out[int(r)] = val
        return out
    regime_rows = {}
    for key in ("regime_by_row", "row_regime_overrides", "row_overrides"):
        regime_rows.update(rowset(mapping.get(key)))
    def row_entries(key):
        """Row-level lists must be lists of {rows: [...], reason: ...}; a malformed entry is an error, never silently ignored."""
        v = mapping.get(key) or []
        if isinstance(v, dict):
            v = [v]
        if not isinstance(v, list) or any(not isinstance(e, dict) or "rows" not in e for e in v):
            raise MappingError(f"{key} must be a list of {{rows, reason}} objects")
        return v
    dup_rows = set()
    for e in row_entries("row_duplicate_of"):
        dup_rows.update(int(r) for r in e.get("rows", []))
    held_rows = {}
    for e in row_entries("row_held"):
        for r in e.get("rows", []):
            held_rows[int(r)] = e.get("reason", "held by mapping")
    lit_rows = set()
    for e in row_entries("row_from_literature"):
        lit_rows.update(int(r) for r in e.get("rows", []))
    colmap = {}
    for key, kind in (("regime_per_row", "regime"), ("gas_per_row", "gas"), ("gas_from_column", "gas")):
        spec = mapping.get(key)
        if isinstance(spec, dict) and spec.get("col"):
            colmap[kind] = (_find_col(header, spec["col"]), spec.get("map") or {}, bool(spec.get("fill_down")), spec.get("default"))
    last_by_kind = {}
    xcols = {}
    for key, c in cols.items():
        if key not in idx and isinstance(c, dict) and c.get("col"):
            try:
                xcols[key] = _find_col(header, c.get("col"))
            except MappingError:
                xcols[key] = None
    records = []
    last_T = last_P = None
    for i, r in enumerate(data):
        if i in skip or i in label_rows:
            continue
        if not any(x.strip() for x in r):
            continue
        cells = [x.strip() for x in r]
        gs = active_group_sets(i)

        def cell(key):
            j = idx.get(key)
            if j is None or j >= len(cells):
                return None
            v = cells[j]
            return v if v != "" else None

        rec = {"idx": i, "raw": dict(zip(header, cells))}
        # temperature
        c = colspec("T") or {}
        T = cell("T")
        if T is None:
            if "T.constant" in gs:
                T = gs["T.constant"][0]
            elif "T" in gs:
                T = gs["T"][0]
            elif c.get("constant") not in (None, ""):
                T = str(c["constant"])
            elif last_T is not None:
                T = last_T  # carried forward (v2.1 rule 3)
        if T is not None:
            last_T = T
        rec["T"], rec["T_unit"] = T, (c.get("unit") or "K")
        # pressure
        c = colspec("P") or {}
        P = cell("P")
        if P is None:
            if "P.constant" in gs:
                P = gs["P.constant"][0]
            elif "P" in gs:
                P = gs["P"][0]
            elif c.get("constant") not in (None, ""):
                P = str(c["constant"])
        rec["P"], rec["P_unit"], rec["P_basis"] = P, (c.get("unit") or ""), (c.get("basis") or "unspecified")
        rec["P_scale"] = parse_scale(c.get("scale"))
        # value
        c = colspec("value") or {}
        V = cell("value")
        if V is None:
            if "value.constant" in gs:
                V = gs["value.constant"][0]
            elif "value" in gs:
                V = gs["value"][0]
            elif c.get("constant") not in (None, ""):
                V = str(c["constant"])
        rec["value"], rec["value_unit"] = V, c.get("unit") or ""
        rec["value_scale"] = parse_scale(c.get("scale")) * unit_scale_from_name(c.get("unit") or "")
        for k in ("value2", "value3"):
            cc = colspec(k)
            if cc is not None:
                rec[k], rec[k + "_unit"] = cell(k), cc.get("unit") or ""
                rec[k + "_scale"] = parse_scale(cc.get("scale")) * unit_scale_from_name(cc.get("unit") or "")
                rec[k + "_from_literature"] = bool(cc.get("from_literature"))
        c = colspec("uncertainty") or {}
        U = cell("uncertainty")
        if U is None and "uncertainty" in gs:
            U = gs["uncertainty"][0]
        rec["uncertainty"], rec["uncertainty_unit"] = U, c.get("unit") or ""
        rec["uncertainty_scale"] = parse_scale(c.get("scale")) * unit_scale_from_name(c.get("unit") or "")
        # m_gas
        c = colspec("m_gas")
        if c is not None:
            rec["m_gas"], rec["m_gas_unit"] = cell("m_gas"), c.get("unit") or ""
        # gas, regime
        rec["gas"] = (gs["gas"][0] if "gas" in gs else None) if "gas" in gs else (mapping.get("gas") or "")
        if "gas" in gs and gs["gas"][0] in (None, ""):
            rec["gas"] = ""
        rec["property"] = gs["property"][0] if "property" in gs and gs["property"][0] else mapping.get("property")
        rec["regime"] = (gs.get("regime", (None,))[0] if "regime" in gs else None) or mapping.get("regime") or ""
        # composition: per-row columns, constants, and group-row paths
        comp_vals = {}
        for salt, spec in (comp.get("per_row") or {}).items():
            if isinstance(spec, dict) and spec.get("col"):
                j = _find_col(header, spec["col"])
                v = cells[j] if j is not None and j < len(cells) else ""
                if v != "":
                    comp_vals[salt] = (v, spec.get("unit", ""))
        for salt, spec in (comp.get("constant") or {}).items():
            comp_vals.setdefault(salt, _split_value_unit(spec))
        for path, (val, unit) in gs.items():
            if isinstance(val, dict):  # concentration column chosen by the block label
                if path.startswith("composition.per_row."):
                    j = _find_col(header, val["col"])
                    if j is not None and j < len(cells) and cells[j] != "":
                        comp_vals[path.split(".", 2)[2]] = (cells[j], unit)
                continue
            if path.startswith("composition.constant."):
                comp_vals[path.split(".", 2)[2]] = (val, unit)
            elif path in ("composition.salt", "composition.salinity"):
                comp_vals[path.split(".", 1)[1]] = (val, unit)
        # a salt named by a label row (composition.salt) takes the concentration column that is listed under 'salt_from_label_row'
        if "salt_from_label_row" in comp_vals and "salt" in comp_vals:
            comp_vals[comp_vals.pop("salt")[0]] = comp_vals.pop("salt_from_label_row")
        # gas loading of a gas-loaded solution (mass fraction w or mole fraction x of the dissolved gas) is not a salt
        loading = {}
        for path, (val, unit) in gs.items():
            if path.startswith("gas_loading."):
                loading[path.split(".", 1)[1].lower()] = (val, unit)
        for key in list(comp_vals):
            if re.match(r"^(x|w)_", key, re.I):
                loading[key.lower()] = comp_vals.pop(key)
        rec["gas_loading"] = loading
        rec["comp"] = comp_vals
        for kind, (j, mp, fill, default) in colmap.items():
            v = cells[j] if j < len(cells) else ""
            if v == "" and fill:
                v = last_by_kind.get(kind, "")
            if v != "":
                last_by_kind[kind] = v
                if v in mp:
                    rec[kind] = mp[v]
                elif default is not None:
                    rec[kind] = default
                else:
                    raise MappingError(f"{kind} column value {v!r} not in the mapping's map")
        if i in regime_rows:
            rec["regime"] = regime_rows[i]
        rec["from_literature_row"] = i in lit_rows
        rec["duplicate_row"] = i in dup_rows
        rec["held_reason"] = held_rows.get(i)
        # any further mapped columns (e.g. phi, p1) by key
        rec["x"] = {}
        for key, j in xcols.items():
            rec["x"][key] = cells[j] if j is not None and j < len(cells) and cells[j] != "" else None
        rec["comp_basis"] = comp.get("basis") or "none"
        rec["comp_rule"] = comp.get("ionic_strength_rule")
        rec["comp_water_g"] = comp.get("water_g_per_kg_solution")
        rec["other_species"] = comp.get("other_species") or ""
        records.append(rec)
    return mapping, paper, records
