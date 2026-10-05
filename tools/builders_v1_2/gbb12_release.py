"""Assemble the GasBrineBench v1.2 data directory from v1.1.1 (git ref `main` of the repository) plus the new build.

Reads : the v1.1.1 family CSVs (git show <ref>:data/<f>.csv), release/new_rows.csv (gbb12_build.py), release/meta_cache.json
        (gbb12_meta.py), the extract/ tree (paper.json).
Writes: <repo>/data/*.csv (old rows unchanged except for `quality` and the new `flags` column, new rows appended),
        <repo>/data/provenance/provenance_v1_2.csv, <repo>/bib/references_v1_2.bib, release/source_map.csv, release/ledger.csv.
Re-runnable: v1.1.1 is always read from git, never from the working tree.

Usage: python3 gbb12_release.py --repo PATH --new release/new_rows.csv [--ref main]
"""
from __future__ import annotations

import argparse
import csv
import html
import io
import json
import os
import re
import subprocess
import sys
import unicodedata
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gbb12_quality as Q  # noqa: E402
import gbb12_corrections as CORR  # noqa: E402

ION = ["m_Na", "m_Cl", "m_K", "m_Ca", "m_Mg", "m_SO4"]
STD = ["dataset_id", "source", "gas", "property", "T_K", "P_bar", *ION, "value", "uncertainty", "quality", "tag"]
OLD_FAMILIES = ["solubility", "y_h2o", "rho", "phi_osm", "dh_sol", "psat_ratio", "eps_r", "ternary"]
NEW_FAMILY_PROP = {"rho_gas": "rho_gas_loaded", "visc": "visc", "thermo_brine": "Cp_app"}
EXTRA = {"ternary": ["y_co2_dry"], "rho_gas": ["m_gas"], "visc": ["m_gas"]}
SEVEN = {"co2", "ch4", "h2", "n2", "o2", "c2h6", "c3h8"}
SINGLE_OTHER = {"ar", "he", "ne", "kr", "xe", "c2h4", "c2h2", "c3h6", "c-c3h6", "1-c4h8", "n-c4h10", "i-c4h10", "neo-c5h12", "c-c6h12",
                "n-c6h14", "i-c8h18", "cf4", "sf6", "n2o", "h2s", "chf3", "chclf2", "c2h2f4", "c2h4f2"}
PRIMARY_TAGS = {"lle-regime"}
# v1.1.1 rows removed after checking them against the paper: (dataset_id, source) -> reason; each is ledgered
REMOVE_OLD_ROWS = {
    ("co2_part1", "WANG(2014)"): (
        "mislabelled copy of Wang, Junliang et al. 2019 (J. Chem. Eng. Data 64, 2484), Tables 6-8: the 306 points are CO2 in 1, 2 and 3 mol/kg NaCl at "
        "303-353 K and 3-30 MPa, the grid of that paper, and every one agrees with its printed molality to rounding (0.2 %). Wang, Shen, Hu & Yu 2014 "
        "(Fluid Phase Equilib. 377, 45) measured synthetic formation brines at 318-348 K and 80-110 bar, not this grid. SCHEMA.md rule 4: the highest-precision "
        "copy is kept, which is the v1.2 transcription of the printed molalities with their uncertainties. Found by the inter-source consensus (612 near-identical "
        "pairs between two 'independent' sources)."),
    ("h2_water_binaries", "DOHRN(1986)"): (
        "the paper (Dohrn & Brunner 1986, hexadecane-water-hydrogen, Table 1) has no 523 K data: its temperatures are 200, 300 and 350 degC. "
        "The stored state (200 bar, aqueous x_H2 = 0.0020) is the aqueous composition of both the 200 degC and the 350 degC blocks, which print "
        "the same value, so the temperature cannot be assigned; flagged by a model-comparison study (3.4 times below every model)."),
}
# corrections of the `source` cell of v1.1.1 rows (dataset_id, old source) -> new source; each is ledgered
SOURCE_CELL_CORRECTIONS = {
    ("c3h8_water", "CHAPOY(2004)"): ("CHAPOY(2004d)",
        "the 78 propane-water rows were cited as the methane paper Chapoy 2004 (10.1016/j.fluid.2004.02.010); they are Chapoy, Mokraoui, Valtz, "
        "Richon, Mohammadi & Tohidi, Fluid Phase Equilib. 226 (2004) 213-220, 10.1016/j.fluid.2004.08.040 (data/README.md: 'Chapoy et al. 2004 "
        "FPE 226:213', 39 points x 2 properties)"),
}


def git_show(repo, ref, path):
    return subprocess.run(["git", "-C", repo, "show", f"{ref}:{path}"], capture_output=True, text=True, check=True).stdout


def read_old(repo, ref):
    out = {}
    for fam in OLD_FAMILIES:
        txt = git_show(repo, ref, f"data/{fam}.csv")
        out[fam] = pd.read_csv(io.StringIO(txt), keep_default_na=False, dtype=str)
    return out


def ascii_letters(s):
    s = unicodedata.normalize("NFKD", s or "")
    return re.sub(r"[^A-Za-z]", "", s)


def crossref_bits(cr):
    """(first-author family, year, authors list, title, journal, volume, issue, pages) from a Crossref message."""
    au = cr.get("author") or []
    fam = au[0].get("family") if au else ""
    iss = (cr.get("issued") or cr.get("published-print") or cr.get("published-online") or {}).get("date-parts", [[None]])[0][0]
    title = html.unescape((cr.get("title") or [""])[0])
    jr = html.unescape((cr.get("container-title") or [""])[0])
    return fam or "", iss, au, title, jr, cr.get("volume", ""), cr.get("issue", ""), cr.get("page", "")


def bibtex_escape(s):
    return s.replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--extract", default=os.path.join(HERE, "..", "extract"))
    ap.add_argument("--meta", default=os.path.join(HERE, "..", "release", "meta_cache.json"))
    ap.add_argument("--supp", default=os.path.join(HERE, "..", "release", "supp", "supplementary_measurements.csv"))
    ap.add_argument("--ref", default="main")
    ap.add_argument("--rel", default=os.path.join(HERE, "..", "release"))
    a = ap.parse_args()
    meta = json.load(open(a.meta))
    old = read_old(a.repo, a.ref)
    ledger = []
    CORR.apply_old(old, ledger)
    CORR.apply_json_fixes(old, ledger)
    for (ds, src), why in REMOVE_OLD_ROWS.items():
        for fam, df in old.items():
            m = (df["dataset_id"] == ds) & (df["source"] == src)
            if m.any():
                ledger.append({"dataset_id": ds, "rows": int(m.sum()), "action": "removed (v1.1.1 row)", "reason": f"{src}: {why}"})
                old[fam] = df[~m].reset_index(drop=True)
    for (ds, src), (new_src, why) in SOURCE_CELL_CORRECTIONS.items():
        for fam, df in old.items():
            m = (df["dataset_id"] == ds) & (df["source"] == src)
            if m.any():
                df.loc[m, "source"] = new_src
                ledger.append({"dataset_id": ds, "rows": int(m.sum()), "action": "source corrected", "reason": f"{src} -> {new_src}: {why}"})

    new = pd.read_csv(a.new, keep_default_na=False, dtype=str)
    # ---- map dataset_id -> (slug, table) --------------------------------------------------------------------------------
    papers, ds_map = {}, {}
    for slug in sorted(os.listdir(a.extract)):
        pj = os.path.join(a.extract, slug, "paper.json")
        if not os.path.isfile(pj):
            continue
        p = json.load(open(pj))
        p["slug"] = slug
        papers[slug] = p
        for fn in os.listdir(os.path.join(a.extract, slug)):
            m = re.match(r"mapping_(.+)\.json$", fn)
            if m:
                ds_map[f"{p['source_key'].lower()}_{slug}_t{m.group(1)}".replace("(", "").replace(")", "")] = (slug, m.group(1))
    new["slug"] = new["dataset_id"].map(lambda d: ds_map[d][0])
    new["table"] = new["dataset_id"].map(lambda d: ds_map[d][1])

    # ---- exclusions -----------------------------------------------------------------------------------------------------

    def gas_class(g):
        if g == "":
            return "none"
        if g in SEVEN:
            return "seven"
        if g in SINGLE_OTHER:
            return "single_other"
        return "mixture"

    new["gas_class"] = new["gas"].map(gas_class)
    mix = new["gas_class"] == "mixture"
    for _, r in new[mix].groupby(["dataset_id", "gas"]).size().reset_index(name="n").iterrows():
        ledger.append({"dataset_id": r["dataset_id"], "rows": r["n"], "action": "excluded", "reason": f"gas-phase mixture {r['gas']!r}: the gas-phase composition has no column in the database"})
    new = new[~mix].copy()
    # tables of a mixed-gas system whose rows are keyed by one of the seven gases (the other gas is a second dissolved species)
    mixtab = new["tag"].str.contains("gas-out-of-scope") & new["gas"].isin(SEVEN)
    for ds, n_ in new[mixtab].groupby("dataset_id").size().items():
        ledger.append({"dataset_id": ds, "rows": int(n_), "action": "excluded", "reason": "mixed-gas table (two dissolved gases): the gas-phase composition has no column in the database"})
    new = new[~mixtab].copy()

    # ---- source keys: SURNAME(YEAR) from Crossref, letter suffixes on collisions ----------------------------------------
    sys.path.insert(0, os.path.join(a.repo, "tools"))
    import make_sources as MS  # noqa: E402
    occupied = set()
    for fam, df in old.items():
        for s in df["source"].unique():
            sn, yr, sf = MS.parse_source_key(MS.apply_source_key_fix(s))
            occupied.add(MS.canonical_id(sn, yr, sf))
    for e in MS.parse_bib(os.path.join(a.repo, "bib", "references.bib")):
        m = MS._BIB_KEY_RE.match(e["key"])
        if m:
            occupied.add(f"{m.group(1).upper()}{m.group(2)}{m.group(3).upper()}")
    supp = pd.read_csv(a.supp, keep_default_na=False, dtype=str)
    supp["slug"] = supp["dataset_id"].map(lambda d: ds_map[d][0])
    supp["table"] = supp["dataset_id"].map(lambda d: ds_map[d][1])
    used_slugs = sorted(set(new["slug"]) | set(supp["slug"]))
    groups = defaultdict(list)
    info = {}
    for slug in used_slugs:
        p = papers[slug]
        doi = (p.get("doi") or "").lower()
        cr = (meta.get(doi) or {}).get("crossref") if doi.startswith("10.") else None
        if cr and "_error" not in cr and cr.get("title"):
            fam, yr, au, title, jr, vol, iss, pg = crossref_bits(cr)
            info[slug] = {"doi": doi, "fam": ascii_letters(fam).upper(), "year": str(yr), "crossref": cr}
        else:
            fk = p["source_key"]
            sn, yr, _ = MS.parse_source_key(fk)
            info[slug] = {"doi": doi if doi.startswith("10.") else "", "fam": sn, "year": yr or str(p.get("year", "")), "crossref": None}
        groups[(info[slug]["fam"], info[slug]["year"])].append(slug)
    source_map = {}
    for (fam, yr), slugs in sorted(groups.items()):
        slugs.sort(key=lambda s: info[s]["doi"] or s)
        letters = [""] + list("bcdefghij")
        li = 0
        for s in slugs:
            while f"{fam}{yr}{letters[li].upper()}" in occupied:
                li += 1
            suf = letters[li]
            occupied.add(f"{fam}{yr}{suf.upper()}")
            li += 1
            source_map[s] = {"source": f"{fam}({yr}{suf})", "bibkey": f"{fam.capitalize() if fam.isupper() else fam}{yr}{suf}"}
    new["source"] = new["slug"].map(lambda s: source_map[s]["source"])
    new["dataset_id"] = [f"{source_map[s]['source'].lower().replace('(', '').replace(')', '')}_{s}_t{t}" for s, t in zip(new["slug"], new["table"])]

    # ---- tag / flags ------------------------------------------------------------------------------------------------------
    def split_tag(t):
        parts = {x for x in (t or "").split(";") if x}
        tag = "lle-regime" if "lle-regime" in parts else "test-only"
        flags = sorted(parts - {"test-only", "lle-regime"})
        return tag, ";".join(flags)

    tf = new["tag"].map(split_tag)
    new["tag"] = [x[0] for x in tf]
    new["flags"] = [x[1] for x in tf]
    new["m_gas"] = [("" if v == "" else str(float(f"{float(v):.8g}"))) for v in new["m_gas"]]
    # families
    new["property"] = ["rho_gas_loaded" if f == "rho_gas" else p for f, p in zip(new["family"], new["property"])]
    fam_of = new["family"]
    # ---- merge per family ---------------------------------------------------------------------------------------------------
    merged = {}
    for fam in OLD_FAMILIES:
        o = old[fam].copy()
        if "flags" not in o.columns:
            o["flags"] = ""
        if "data_origin" not in o.columns:
            o["data_origin"] = ""
        n = new[new["family"] == fam]
        cols = list(o.columns)
        add = n.reindex(columns=cols, fill_value="")
        merged[fam] = pd.concat([o, add], ignore_index=True)
    for fam in NEW_FAMILY_PROP:
        n = new[new["family"] == fam]
        cols = STD + ["flags", "data_origin"] + EXTRA.get(fam, [])
        merged[fam] = n.reindex(columns=cols, fill_value="").reset_index(drop=True)

    CORR.apply_new(merged, ledger)
    # ---- same-source exact duplicates ---------------------------------------------------------------------------------------
    key_cols = ["source", "gas", "property", "T_K", "P_bar", *ION, "value"]
    for fam, df in merged.items():
        num = df[key_cols].copy()
        for c in ["T_K", "P_bar", *ION, "value"]:
            num[c] = pd.to_numeric(num[c], errors="coerce").round(8)
        dup = num.duplicated(keep="first") & df["dataset_id"].isin(set(new["dataset_id"]))  # v1.1.1 rows are never removed
        if dup.any():
            for ds, k in df[dup].groupby("dataset_id").size().items():
                ledger.append({"dataset_id": ds, "rows": int(k), "action": "removed", "reason": "exact duplicate of a row of the same source (same state, same value)"})
            merged[fam] = df[~dup].reset_index(drop=True)

    # ---- corrections from the full row-by-row audit (positions of the audited release; guarded by the old value) ---------------
    import gbb12_audit_fixes as AF  # noqa: E402
    AF.apply(merged, os.path.join(a.rel, "full_audit", "fixes"), ledger, os.path.join(a.rel, "full_audit", "fix_apply_report.csv"))
    # source labels that named a paper we do not hold, while the rows were verified against a paper we do hold
    RELABEL = {"KOBAYASHI(1951)": ("KOBAYASHI(1953)", "the rows are Table VI of Kobayashi and Katz (1953), with which they were compared in the audit; the label named the thesis"),
               "FROST(2013)": ("FROST(2014)", "the label carried the year of the online publication (December 2013); the paper is J. Chem. Eng. Data 59(4), 961-967 (2014)"),
               "SULTANOV(1972)": ("PRICE(1979)", "the rows are Table 2 of Price (1979), which reprints the data of Sultanov et al.; compared with that table in the audit")}
    for fam, df in merged.items():
        for old_lab, (new_lab, why) in RELABEL.items():
            m = df["source"] == old_lab
            if m.any():
                df.loc[m, "source"] = new_lab
                ledger.append({"dataset_id": old_lab, "rows": int(m.sum()), "action": f"source relabelled to {new_lab}", "reason": why})

    # ---- quality: cross-source rules on the solubility rows -----------------------------------------------------------------
    sol = merged["solubility"]
    num = sol.copy()
    for c in ["T_K", "P_bar", *ION, "value"]:
        num[c] = pd.to_numeric(num[c], errors="coerce")
    base = num.copy()
    base["quality"] = np.where(num["quality"] == "U", "U", "T")
    q, rep = Q.apply_rules(base)
    changed_old = (sol["quality"] != q) & sol["dataset_id"].isin(old["solubility"]["dataset_id"])
    print("quality rules:", rep, "| old solubility rows whose code changes:", int(changed_old.sum()))
    merged["solubility"]["quality"] = q.values

    # ---- data_origin: where the number comes from -----------------------------------------------------------------------------
    def origin(fl):
        t = set(str(fl).split(";"))
        return "figure" if "figure-digitized" in t else ("calculated" if "calculated-not-measured" in t else "table")
    for fam, df in merged.items():
        df["data_origin"] = df["flags"].map(origin)
    # ---- write -----------------------------------------------------------------------------------------------------------------
    data = os.path.join(a.repo, "data")
    os.makedirs(os.path.join(data, "provenance"), exist_ok=True)
    for fam, df in merged.items():
        cols = STD + ["flags", "data_origin"] + EXTRA.get(fam, [])
        if fam == "ternary":
            cols = STD[:6] + ["y_co2_dry"] + STD[6:] + ["flags", "data_origin"]
        df = df.reindex(columns=cols, fill_value="")
        df.to_csv(os.path.join(data, f"{fam}.csv"), index=False, lineterminator="\n")
    # ---- provenance --------------------------------------------------------------------------------------------------------
    notes = {}
    p = os.path.join(a.rel, "source_notes.csv")
    if os.path.exists(p):
        for r in csv.DictReader(open(p)):
            notes[(r["doi"], r["table"])] = r["caution"]
    prov = []
    allrows = pd.concat([df.assign(_fam=f) for f, df in merged.items()], ignore_index=True)
    new_ids = set(new["dataset_id"])
    cnt = allrows[allrows["dataset_id"].isin(new_ids)].groupby(["dataset_id", "_fam"]).size()
    d2slug = {d: (s, t) for d, s, t in zip(new["dataset_id"], new["slug"], new["table"])}
    for (ds, fam), k in cnt.items():
        slug, t = d2slug[ds]
        pp = papers[slug]
        prov.append({"dataset_id": ds, "family": fam, "source": source_map[slug]["source"], "doi": info[slug]["doi"], "table": t, "rows": int(k),
                     "verification": pp.get("status", ""), "how_extracted": pp.get("how_extracted", ""),
                     "experimental_method": (pp.get("experimental_method") or "")[:400],
                     "caution": notes.get((pp.get("doi", ""), t), "")[:400]})
    pd.DataFrame(prov).to_csv(os.path.join(data, "provenance", "provenance_v1_2.csv"), index=False, lineterminator="\n")
    # ---- bib --------------------------------------------------------------------------------------------------------------
    lines = ["% GasBrineBench v1.2: records for the sources added in v1.2. Generated by builder/gbb12_release.py from Crossref metadata",
             "% (records retrieved by DOI); theses are hand-entered from the paper's own title page. Do not edit by hand.", ""]
    for slug in used_slugs:
        inf, p = info[slug], papers[slug]
        bk = source_map[slug]["bibkey"]
        cr = inf["crossref"]
        if cr and cr.get("title"):
            fam, yr, au, title, jr, vol, iss, pg = crossref_bits(cr)
            authors = " and ".join(f"{x.get('family', '')}, {x.get('given', '')}".strip(", ") for x in au) or p.get("authors", "")
            lines += [f"@article{{{bk},", f"  author  = {{{bibtex_escape(authors)}}},", f"  title   = {{{bibtex_escape(title)}}},",
                      f"  journal = {{{bibtex_escape(jr)}}},", f"  year    = {{{yr}}},"]
            if vol:
                lines.append(f"  volume  = {{{vol}}},")
            if iss:
                lines.append(f"  number  = {{{iss}}},")
            if pg:
                lines.append(f"  pages   = {{{pg}}},")
            lines += [f"  doi     = {{{inf['doi']}}}", "}", ""]
        else:
            lines += [f"@misc{{{bk},", f"  author  = {{{bibtex_escape(p.get('authors', p.get('first_author', '')))}}},",
                      f"  title   = {{{bibtex_escape(p.get('title', ''))}}},", f"  year    = {{{inf['year']}}},",
                      f"  note    = {{{bibtex_escape(str(p.get('journal', ''))[:200])}}}", "}", ""]
    txt = "\n".join(lines)
    # a thesis whose title page was not captured in paper.json: filled from the title page of the PDF (checked 2026-10-04)
    txt = txt.replace("@misc{Adeniyi2020,\n  author  = {Adeniyi},\n  title   = {},",
                      "@phdthesis{Adeniyi2020,\n  author  = {Adeniyi, Kayode Israel},\n  school  = {University of Calgary},\n  title   = {Water content of liquid acid gas and liquid propane in the presence of a hydrate phase},")
    open(os.path.join(a.repo, "bib", "references_v1_2.bib"), "w").write(txt)
    # ---- supplementary tier -----------------------------------------------------------------------------------------------
    old_ds = list(supp["dataset_id"])
    supp["source"] = supp["slug"].map(lambda s_: source_map[s_]["source"])
    supp["dataset_id"] = [f"{source_map[s_]['source'].lower().replace('(', '').replace(')', '')}_{s_}_t{t}" if d == f"{papers[s_]['source_key'].lower()}_{s_}_t{t}".replace("(", "").replace(")", "")
                          else d for d, s_, t in zip(old_ds, supp["slug"], supp["table"])]
    sd = os.path.join(a.repo, "supplementary")
    os.makedirs(sd, exist_ok=True)
    supp.drop(columns=["slug", "table"]).to_csv(os.path.join(sd, "supplementary_measurements.csv"), index=False, lineterminator="\n")
    for (ds, cls), k in supp.groupby(["dataset_id", "property_class"]).size().items():
        slug = supp.loc[supp["dataset_id"] == ds, "slug"].iloc[0]
        t = supp.loc[supp["dataset_id"] == ds, "table"].iloc[0]
        pp = papers[slug]
        prov.append({"dataset_id": ds, "family": "supplementary:" + cls, "source": source_map[slug]["source"], "doi": info[slug]["doi"], "table": t, "rows": int(k),
                     "verification": pp.get("status", ""), "how_extracted": pp.get("how_extracted", ""),
                     "experimental_method": (pp.get("experimental_method") or "")[:400], "caution": notes.get((pp.get("doi", ""), t), "")[:400]})
    pd.DataFrame(prov).to_csv(os.path.join(data, "provenance", "provenance_v1_2.csv"), index=False, lineterminator="\n")
    print("supplementary rows:", len(supp), dict(Counter(supp["property_class"])))
    # ---- citation counts (OpenAlex) -------------------------------------------------------------------------------------------
    cc = [{"doi": d, "cited_by_openalex": "" if v.get("cited_by") is None else v["cited_by"], "retrieved": v.get("cited_by_date", "")}
          for d, v in sorted(meta.items()) if v.get("cited_by_date")]
    pd.DataFrame(cc).to_csv(os.path.join(data, "provenance", "citation_counts.csv"), index=False, lineterminator="\n")
    # ---- records for the work area -------------------------------------------------------------------------------------------
    os.makedirs(a.rel, exist_ok=True)
    pd.DataFrame([{"slug": s, "doi": info[s]["doi"], **source_map[s]} for s in used_slugs]).to_csv(os.path.join(a.rel, "source_map.csv"), index=False)
    pd.DataFrame(ledger).to_csv(os.path.join(a.rel, "ledger.csv"), index=False)
    tot = {f: len(d) for f, d in merged.items()}
    print("rows per family:", tot, "total", sum(tot.values()))
    print("new rows kept:", len(new), "| ledger entries:", len(ledger))
    print("flags:", Counter(x for f in new["flags"] for x in f.split(";") if x).most_common())


if __name__ == "__main__":
    main()
