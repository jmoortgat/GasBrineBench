"""Fetch bibliographic metadata (Crossref) and citation counts (OpenAlex) for the papers that contribute rows to v1.2.
Writes release/meta_cache.json (doi -> {crossref: ..., cited_by: int, fetched: date}). No credentials, no e-mail address is sent.
Usage: python3 gbb12_meta.py --dois-file FILE [--cache release/meta_cache.json]"""
import argparse, json, os, sys, time, urllib.request, urllib.parse
from datetime import date

def get(url, tries=3):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "GasBrineBench-metadata/1.0"}), timeout=30) as r:
                return json.load(r)
        except Exception as e:
            err = e
            time.sleep(2 * (k + 1))
    return {"_error": str(err)}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dois-file", required=True); ap.add_argument("--cache", default="release/meta_cache.json")
    a = ap.parse_args()
    dois = sorted({d.strip().lower() for d in open(a.dois_file) if d.strip()})
    cache = json.load(open(a.cache)) if os.path.exists(a.cache) else {}
    for i, d in enumerate(dois):
        c = cache.setdefault(d, {})
        if "crossref" not in c or "_error" in c["crossref"]:
            r = get("https://api.crossref.org/works/" + urllib.parse.quote(d))
            c["crossref"] = r.get("message", r)
            time.sleep(0.15)
    # OpenAlex counts, 40 DOIs per request
    todo = [d for d in dois if "cited_by" not in cache[d]]
    for i in range(0, len(todo), 40):
        batch = todo[i:i + 40]
        r = get("https://api.openalex.org/works?per_page=50&select=doi,cited_by_count&filter=doi:" + "|".join(urllib.parse.quote(x) for x in batch))
        found = {w["doi"].replace("https://doi.org/", "").lower(): w["cited_by_count"] for w in r.get("results", [])}
        for d in batch:
            cache[d]["cited_by"] = found.get(d)
            cache[d]["cited_by_date"] = str(date.today())
        time.sleep(0.2)
    json.dump(cache, open(a.cache, "w"), indent=1)
    miss = [d for d in dois if "_error" in cache[d].get("crossref", {}) or not cache[d].get("crossref")]
    print(len(dois), "dois;", len(miss), "without Crossref record:", miss[:20])
    print("without OpenAlex count:", sum(1 for d in dois if cache[d].get("cited_by") is None))
main()
