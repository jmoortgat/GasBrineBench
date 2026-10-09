"""Build the packets of the full row-by-row audit: one rows file per cited paper, papers binned into agent packets.
Usage: python3 builder/gbb12_fullaudit_packets.py --repo PATH"""
import argparse, glob, hashlib, importlib.util, json, os, sys
import pandas as pd
ap = argparse.ArgumentParser(); ap.add_argument("--repo", required=True); ap.add_argument("--target", type=int, default=700); a = ap.parse_args()
sys.path.insert(0, a.repo)
import gasbrinebench as gbb
spec = importlib.util.spec_from_file_location("ms", os.path.join(a.repo, "tools", "make_sources.py")); ms = importlib.util.module_from_spec(spec); spec.loader.exec_module(ms)
W = os.getcwd()
idx = pd.read_csv("papers_archive/INDEX.csv", keep_default_na=False).set_index("cid")
frames = []
for f in sorted(glob.glob(f"{a.repo}/data/*.csv")):
    d = pd.read_csv(f, keep_default_na=False); d["family"] = os.path.basename(f)[:-4]; d["row_id"] = range(len(d)); frames.append(d)
df = pd.concat(frames, ignore_index=True)
df["cid"] = df.source.map(lambda s: ms.canonical_id(*ms.parse_source_key(ms.apply_source_key_fix(s))))
sha = {os.path.basename(f): hashlib.sha256(open(f, "rb").read()).hexdigest()[:16] for f in sorted(glob.glob(f"{a.repo}/data/*.csv"))}
papers = []
for cid, g in df.groupby("cid"):
    r = idx.loc[cid]
    slugs = sorted({x.split("_t")[0] if False else x for x in g.dataset_id.unique()})
    ex = sorted({os.path.basename(p) for sl in set(s for ds in g.dataset_id.unique() for s in [ds]) for p in glob.glob(f"extract/*{r.doi.replace('/', '_')}*")}) if r.doi else []
    g.to_csv(f"release/full_audit/rows/{cid}.csv", index=False)
    papers.append({"cid": cid, "citekey": r.citekey, "doi": r.doi, "sources": sorted(g.source.unique()), "n_rows": len(g), "families": sorted(g.family.unique()),
                   "dataset_ids": sorted(g.dataset_id.unique()), "pdf": (f"{W}/{r.file}" if r.file else ""), "extract_dir": [f"{W}/{e}" for e in ex],
                   "rows_file": f"{W}/release/full_audit/rows/{cid}.csv", "result_file": f"{W}/release/full_audit/results/{cid}.csv"})
papers.sort(key=lambda p: -p["n_rows"])
bins = []
for p in papers:
    if p["n_rows"] >= a.target: bins.append([p]); continue
    for b in bins:
        if sum(q["n_rows"] for q in b) + p["n_rows"] <= a.target and sum(q["n_rows"] for q in b) < a.target and all(q["n_rows"] < a.target for q in b) and len(b) < 8:
            b.append(p); break
    else: bins.append([p])
for i, b in enumerate(bins):
    json.dump({"agent": i, "data_sha": sha, "papers": b}, open(f"release/full_audit/packets/a{i:02d}.json", "w"), indent=1)
print(len(papers), "papers;", len(bins), "packets; rows", sum(p["n_rows"] for p in papers), "max", max(sum(q["n_rows"] for q in b) for b in bins))
print(sorted((sum(q["n_rows"] for q in b), len(b)) for b in bins)[-12:])
