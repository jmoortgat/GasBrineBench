"""Seeded, stratified random sample of benchmark points for the independent audit against the papers.

Population: every point of the benchmark families in the current repo data (all rows, every flag): solubility counted once per point
(the molality row; the mole-fraction sibling is the same measurement), every row of the other families.
Strata: family x origin (v1.1.1 rows vs rows added in v1.2). Allocation: proportional to stratum size with a floor, total N.
Output: release/random_audit/sample.csv (the frame, with weights), packets/chunk_*.json for the auditors.
Usage: python3 builder/gbb12_audit_sample.py --repo PATH --n 400 --seed 20261004
"""
import argparse, json, os, re, sys
import numpy as np, pandas as pd

ION = ["m_Na", "m_Cl", "m_K", "m_Ca", "m_Mg", "m_SO4"]
ap = argparse.ArgumentParser()
ap.add_argument("--repo", required=True); ap.add_argument("--n", type=int, default=400); ap.add_argument("--seed", type=int, default=20261004)
ap.add_argument("--dup", type=int, default=40, help="points read by two independent auditors")
ap.add_argument("--chunks", type=int, default=10)
a = ap.parse_args()
sys.path.insert(0, a.repo)
import gasbrinebench as gbb

df = gbb.load(exclude_tags=None, exclude_flags=None, derive=False)
df["row_id"] = df.groupby("family").cumcount()
prov = pd.read_csv(os.path.join(a.repo, "data", "provenance", "provenance_v1_2.csv"), keep_default_na=False)
new_ids = set(prov[~prov["family"].str.startswith("supplementary")]["dataset_id"])
df["origin"] = np.where(df["dataset_id"].isin(new_ids), "v1.2", "v1.1.1")
pop = df[~((df.family == "solubility") & (df.property == "xc_saltfree"))].copy()
pop["stratum"] = pop["family"] + "|" + pop["origin"]
sizes = pop.groupby("stratum").size()
alloc = (sizes / sizes.sum() * a.n).round().astype(int).clip(lower=4)
alloc = alloc.where(alloc <= sizes, sizes)
# trim or grow the largest strata so that the total is N
while alloc.sum() > a.n:
    alloc[alloc.idxmax()] -= 1
while alloc.sum() < a.n:
    alloc[(sizes - alloc).idxmax()] += 1
rng = np.random.default_rng(a.seed)
pick = []
for s, k in alloc.items():
    idx = pop.index[pop.stratum == s].to_numpy()
    pick.extend(rng.choice(idx, size=int(k), replace=False))
samp = pop.loc[pick].copy()
samp["weight"] = samp["stratum"].map(sizes / alloc)
dup_ids = set(rng.choice(samp.index.to_numpy(), size=a.dup, replace=False))
samp["double_read"] = samp.index.isin(dup_ids)

# sibling (xc_saltfree) row of a sampled solubility point
sol_rows = df[df.family == "solubility"].set_index("row_id")
def sibling(r):
    if r.family != "solubility":
        return None
    for j in (r.row_id - 1, r.row_id + 1):
        if j in sol_rows.index:
            s = sol_rows.loc[j]
            if (s.property == "xc_saltfree" and s.dataset_id == r.dataset_id and abs(s.T_K - r.T_K) < 1e-9
                    and all(abs(s[k] - getattr(r, k)) < 1e-9 for k in ION) and (np.isnan(r.P_bar) or abs(s.P_bar - r.P_bar) < 1e-9)):
                return int(j)
    return None
samp["sibling_row_id"] = [sibling(r) for r in samp.itertuples()]

# paper locations
ALL = []
for root in ["<papers>", "<papers>",
             "<papers>", "<papers>"]:
    for dp, dn, fn in os.walk(root):
        for f in fn:
            if f.lower().endswith(".pdf"):
                ALL.append((f.lower(), os.path.join(dp, f)))
pl = os.path.abspath("papers_local")
html_slugs = {sl for sl in os.listdir("extract") if os.path.isfile(f"extract/{sl}/paper.json") and json.load(open(f"extract/{sl}/paper.json")).get("status") == "verified_html"}
def find_pdf(source, dsid):
    m = re.search(r"_(10\.[^_]+_.+?)_t[\w.]+(?:_group\d)?$", dsid) or re.search(r"_(LaraCruz_2019|Yarrison_2007)_t[\w.]+$", dsid)
    if m:
        c = [f for f in os.listdir(pl) if m.group(1).lower() in f.lower()]
        if c: return [os.path.join(pl, c[0])]
    sn = re.match(r"[A-Za-z]+", source).group(0).lower(); yr = re.search(r"(19|20)\d\d", source)
    hits = [pth for nm, pth in ALL if nm.startswith(sn) and (not yr or yr.group(0) in nm)]
    if not hits and yr:
        hits = [pth for nm, pth in ALL if sn in nm and yr.group(0) in nm]
    out = []
    for h in hits:
        if h not in out: out.append(h)
    return out[:4]
def slug_of(dsid):
    m = re.search(r"_(10\.[^_]+_.+?)_t[\w.]+(?:_group\d)?$", dsid) or re.search(r"_(LaraCruz_2019|Yarrison_2007)_t[\w.]+$", dsid)
    return m.group(1) if m else None
pmap = prov.drop_duplicates("dataset_id").set_index("dataset_id")
packets = {}
for r in samp.itertuples():
    key = f"{r.source}|{r.dataset_id}"
    pk = packets.setdefault(key, {"source": r.source, "dataset_id": r.dataset_id, "origin": r.origin, "pdf_candidates": find_pdf(r.source, r.dataset_id), "points": []})
    if r.dataset_id in pmap.index:
        pk["doi"] = pmap.loc[r.dataset_id, "doi"]; pk["table"] = str(pmap.loc[r.dataset_id, "table"])
        sl = slug_of(r.dataset_id)
        if sl:
            pk["extract_dir"] = f"extract/{sl}/ (table_{pk['table']}.csv, mapping_{pk['table']}.json)"
            pk["source_type"] = "html_capture (no PDF: compare the database with table_N.csv and check the mapping and conversion)" if sl in html_slugs else "pdf"
    pk["points"].append({"family": r.family, "row_id": int(r.row_id), "sibling_row_id": r.sibling_row_id, "property": r.property, "gas": r.gas, "T_K": r.T_K,
                         "P_bar": None if pd.isna(r.P_bar) else r.P_bar, "ions": {k: getattr(r, k) for k in ION if getattr(r, k)}, "value": r.value,
                         "uncertainty": None if pd.isna(r.uncertainty) else r.uncertainty, "flags": r.flags, "quality": r.quality, "double_read": bool(r.double_read)})
samp.drop(columns=[c for c in samp.columns if c not in ("family","row_id","dataset_id","source","property","gas","T_K","P_bar","value","origin","stratum","weight","double_read","sibling_row_id")]).to_csv("release/random_audit/sample.csv", index=False)
# distribute groups over chunks (balanced by number of points); double-read points go to a second chunk as copies
items = sorted(packets.items(), key=lambda kv: -len(kv[1]["points"]))
chunks = [[] for _ in range(a.chunks)]; load = [0] * a.chunks
for k, p in items:
    i = load.index(min(load)); chunks[i].append((k, p)); load[i] += len(p["points"]) + 4
# second copies of the double-read points, placed in a different chunk than their first
second = [[] for _ in range(a.chunks)]
for ci, ch in enumerate(chunks):
    for k, p in ch:
        dp = [pt for pt in p["points"] if pt["double_read"]]
        if dp:
            cj = (ci + 1 + (sum(map(ord, k)) % (a.chunks - 1))) % a.chunks
            q = {kk: vv for kk, vv in p.items() if kk != "points"}; q["points"] = dp; second[cj].append((k + "#2", q))
for i in range(a.chunks):
    d = dict(chunks[i] + second[i])
    for k in d:
        for pt in d[k]["points"]: pt.pop("double_read", None)
    json.dump(d, open(f"release/random_audit/packets/chunk_{i}.json", "w"), indent=1)
print("sample", len(samp), "points in", len(packets), "table groups;", "no pdf for", sum(1 for p in packets.values() if not p["pdf_candidates"]))
print(alloc.to_string())
