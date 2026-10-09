"""Documented literature gap check for GasBrineBench.

Runs a fixed list of OpenAlex queries (title+abstract), logs every query string, the number
of hits and the date, keeps the top N hits per query by relevance, removes works whose DOI is
already in GasBrineBench/bib/references.bib, and writes:
  query_log.csv   one row per query (id, openalex filter string, total hits, kept, run date)
  candidates.csv  one row per distinct candidate work not already in the database
  candidates.json same plus abstracts, for screening
"""
import csv
import datetime
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = __file__.rsplit("/", 1)[0]
BIB = HERE.rsplit("/", 2)[0] + "/bib/references.bib"   # this script lives in tools/search/
TOPN = int(sys.argv[1]) if len(sys.argv) > 1 else 100
import os
MAILTO = os.environ.get("OPENALEX_MAILTO", "")   # OpenAlex asks API users to identify themselves with an e-mail address

GAS = {
    "co2": '("carbon dioxide" OR CO2)',
    "ch4": '(methane OR CH4)',
    "h2": '(hydrogen OR H2)',
    "n2": '(nitrogen OR N2)',
    "o2": '(oxygen OR O2)',
    "c2h6": '(ethane OR C2H6)',
    "c3h8": '(propane OR C3H8)',
    "mix": '("natural gas" OR "gas mixture" OR "acid gas" OR "flue gas")',
}
LIQ = '(water OR brine OR aqueous OR NaCl OR seawater OR "salt solution")'
MEAS = '(measurement OR measured OR experimental OR "experimental data" OR determination)'

Q = {}
for g, t in GAS.items():
    Q[f"sol_{g}"] = f'{t} AND (solubility OR "phase equilibria" OR "phase equilibrium" OR "vapor-liquid" OR "vapour-liquid") AND {LIQ} AND {MEAS}'
    Q[f"wc_{g}"] = f'{t} AND ("water content" OR "mutual solubility" OR "mutual solubilities" OR "water vapor content" OR "water vapour content" OR "dew point" OR "water in the gas phase" OR "gas-phase composition") AND {MEAS}'
Q["salts_co2"] = f'("carbon dioxide" OR CO2) AND solubility AND (CaCl2 OR MgCl2 OR KCl OR Na2SO4 OR "calcium chloride" OR "magnesium chloride" OR "potassium chloride" OR "sodium sulfate" OR "mixed brine" OR "formation water")'
Q["salts_ch4"] = f'(methane OR CH4) AND solubility AND (CaCl2 OR MgCl2 OR KCl OR Na2SO4 OR "calcium chloride" OR "magnesium chloride" OR "potassium chloride" OR "sodium sulfate" OR "mixed brine" OR "formation water")'
Q["salts_h2"] = f'(hydrogen OR H2) AND solubility AND (CaCl2 OR MgCl2 OR KCl OR Na2SO4 OR "mixed brine" OR "formation water" OR NaCl)'
Q["ternary"] = f'("carbon dioxide" OR CO2) AND (methane OR CH4) AND (water OR brine) AND (solubility OR "phase equilibria" OR "phase equilibrium") AND {MEAS}'
Q["rho"] = f'(density OR "volumetric properties") AND (aqueous OR brine) AND (NaCl OR CaCl2 OR MgCl2 OR KCl OR Na2SO4 OR "sodium chloride") AND ("high pressure" OR "high temperature" OR "elevated pressure") AND {MEAS}'
Q["rho_gas"] = f'(density OR "partial molar volume") AND ("carbon dioxide" OR methane OR hydrogen OR nitrogen) AND (brine OR "aqueous solution" OR "saline") AND {MEAS}'
Q["phi_osm"] = '("osmotic coefficient" OR "activity coefficient" OR "water activity") AND (NaCl OR CaCl2 OR MgCl2 OR KCl OR Na2SO4 OR "aqueous electrolyte") AND ("high temperature" OR "elevated temperature") AND (measurement OR measured OR experimental)'
Q["psat"] = '("vapor pressure" OR "vapour pressure" OR "boiling point elevation") AND (NaCl OR CaCl2 OR MgCl2 OR KCl OR brine OR "aqueous electrolyte") AND (measurement OR measured OR experimental)'
Q["dhsol"] = '("enthalpy of solution" OR "heat of solution" OR "enthalpy of dissolution" OR calorimetry OR calorimetric) AND (gas OR "carbon dioxide" OR methane OR hydrogen) AND (water OR brine)'
Q["eps"] = '("static permittivity" OR "dielectric constant" OR "relative permittivity") AND (aqueous OR brine OR electrolyte) AND (NaCl OR salt) AND (measurement OR measured OR experimental)'
Q["hydrate_free"] = f'("Henry constant" OR "Setschenow" OR "salting-out") AND (gas OR "carbon dioxide" OR methane OR hydrogen OR nitrogen OR ethane OR propane) AND {LIQ} AND {MEAS}'

Q["cp_brine"] = '("apparent molar heat capacity" OR "apparent molar enthalpy" OR "enthalpy of dilution" OR "heat capacity of aqueous") AND (NaCl OR KCl OR CaCl2 OR MgCl2 OR Na2SO4 OR brine OR "aqueous electrolyte") AND (measurement OR measured OR experimental)'
Q["pmv_gas"] = '("partial molar volume" OR "partial molar heat capacity" OR "infinite dilution") AND (aqueous OR water) AND ("carbon dioxide" OR methane OR hydrogen OR nitrogen OR ethane OR propane) AND (measurement OR measured OR experimental)'
Q["sound"] = '("speed of sound" OR "sound velocity" OR compressibility) AND (brine OR "aqueous NaCl" OR "aqueous electrolyte" OR "saline water") AND ("high pressure" OR "high temperature") AND (measurement OR measured OR experimental)'


def known_dois():
    txt = open(BIB, encoding="utf-8").read()
    return {m.group(1).lower().strip() for m in re.finditer(r'doi\s*=\s*[{"]\s*(?:https?://(?:dx\.)?doi\.org/)?([^}"\s]+)', txt, re.I)}


def abstract(idx):
    if not idx:
        return ""
    pos = {}
    for w, ps in idx.items():
        for p in ps:
            pos[p] = w
    return " ".join(pos[i] for i in sorted(pos))


def fetch(search, n):
    out, cursor, total = [], "*", None
    sel = "id,doi,title,publication_year,type,primary_location,cited_by_count,abstract_inverted_index,authorships"
    while len(out) < n:
        url = ("https://api.openalex.org/works?filter=" + urllib.parse.quote(f"title_and_abstract.search:{search},type:article|book|dissertation|report|book-chapter", safe=":,|") +
               f"&per-page={min(100, n - len(out))}&cursor={urllib.parse.quote(cursor)}&select={sel}&mailto={MAILTO}")
        for attempt in range(6):
            try:
                with urllib.request.urlopen(url, timeout=60) as r:
                    d = json.load(r)
                break
            except urllib.error.HTTPError as e:
                if e.code != 429 or attempt == 5:
                    raise RuntimeError(e.read()[:400])
                time.sleep(3 * (attempt + 1))
        time.sleep(1.2)
        total = d["meta"]["count"]
        out += d["results"]
        cursor = d["meta"].get("next_cursor")
        if not cursor or not d["results"]:
            break
        time.sleep(1.2)
    return total, out[:n]


def main():
    known = known_dois()
    print(f"{len(known)} DOIs in GasBrineBench bib")
    today = datetime.date.today().isoformat()
    cands, log = {}, []
    for qid, s in Q.items():
        total, res = fetch(s, TOPN)
        new = 0
        for w in res:
            doi = (w.get("doi") or "").replace("https://doi.org/", "").lower()
            if doi and doi in known:
                continue
            key = doi or w["id"]
            c = cands.setdefault(key, {
                "key": key, "doi": doi, "openalex": w["id"], "title": w["title"], "year": w["publication_year"],
                "type": w["type"], "journal": ((w.get("primary_location") or {}).get("source") or {}).get("display_name"),
                "cited_by": w["cited_by_count"],
                "first_author": (w["authorships"][0]["author"]["display_name"] if w.get("authorships") else ""),
                "abstract": abstract(w.get("abstract_inverted_index")), "queries": []})
            if qid not in c["queries"]:
                c["queries"].append(qid)
                new += 1
        log.append({"query_id": qid, "openalex_search": s, "total_hits": total, "retrieved": len(res), "run_date": today})
        print(f"{qid:14s} total {total:7d}  retrieved {len(res):4d}  new-to-pool {new}")
    with open(f"{HERE}/query_log.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(log[0]))
        wr.writeheader()
        wr.writerows(log)
    rows = sorted(cands.values(), key=lambda c: -len(c["queries"]))
    with open(f"{HERE}/candidates.csv", "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["key", "doi", "first_author", "year", "title", "journal", "type", "cited_by", "queries"])
        for c in rows:
            wr.writerow([c["key"], c["doi"], c["first_author"], c["year"], c["title"], c["journal"], c["type"], c["cited_by"], "|".join(c["queries"])])
    json.dump(rows, open(f"{HERE}/candidates.json", "w"))
    print(f"{len(rows)} candidate works not in the database")


main()
