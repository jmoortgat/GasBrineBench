"""Analyse the random audit (plan: release/random_audit/PLAN.md). Reads sample.csv, results/chunk_*.json and the optional adjudication.json
({"family:row_id": "correct|minor|major|unverifiable"}) written after every major or disputed point was re-read.
Prints the report numbers and writes release/random_audit/report.json."""
import glob, json, os, sys, math, collections
import numpy as np, pandas as pd

D = "release/random_audit"
samp = pd.read_csv(f"{D}/sample.csv")
samp["key"] = samp.family + ":" + samp.row_id.astype(str)
reads = collections.defaultdict(list)   # key -> list of (verdict, cause, group, source_type)
for f in sorted(glob.glob(f"{D}/results/chunk_*.json")):
    for gk, g in json.load(open(f)).items():
        for p in g["points"]:
            reads[f"{p['family']}:{p['row_id']}"].append((p["verdict"], p.get("cause"), gk.split("#")[0], g.get("source_type", "pdf")))
adj = json.load(open(f"{D}/adjudication.json")) if os.path.exists(f"{D}/adjudication.json") else {}
final, needs = {}, []
for k in samp.key:
    r = reads.get(k, [])
    if not r:
        needs.append((k, "no reading")); continue
    vs = {v for v, *_ in r}
    if k in adj: final[k] = adj[k]
    elif len(vs) == 1 and "major" not in vs: final[k] = vs.pop()
    else: needs.append((k, "major or disputed: " + "/".join(v for v, *_ in r)))
samp["verdict"] = samp.key.map(final)
samp["source_type"] = samp.key.map(lambda k: ("html_capture" if str(reads[k][0][3]).startswith("html") else "pdf") if reads.get(k) else None)
samp["group"] = samp.key.map(lambda k: reads[k][0][2] if reads.get(k) else None)
print(f"{len(samp)} sampled points; {len(final)} with a final verdict; {len(needs)} awaiting adjudication")
for k, why in needs: print("  adjudicate:", k, why)

def wilson(x, n, z=1.96):
    if n == 0: return (float("nan"), float("nan"))
    p = x / n; den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0, c - h), min(1, c + h))

def block(df, label):
    v = df[df.verdict.isin(["correct", "minor", "major"])]
    n = len(v); x = int((v.verdict == "major").sum()); m = int((v.verdict == "minor").sum())
    lo, hi = wilson(x, n)
    print(f"{label:28s} points {len(df):4d}  verifiable {n:4d}  unverifiable {int((df.verdict=='unverifiable').sum()):3d}  major {x:3d} ({x/max(n,1):.1%}, 95% CI {lo:.1%}-{hi:.1%})  minor {m:3d}")
    return {"points": len(df), "verifiable": n, "unverifiable": int((df.verdict == "unverifiable").sum()), "major": x, "minor": m, "major_ci": [lo, hi]}
rep = {"all": block(samp, "ALL")}
for o, g in samp.groupby("origin"): rep["origin:" + o] = block(g, "origin " + o)
for t, g in samp.groupby("source_type"): rep["type:" + str(t)[:4]] = block(g, "source " + str(t)[:12])
for f, g in samp.groupby("family"): rep["family:" + f] = block(g, "family " + f)
# stratified (population-weighted) estimate over verifiable points
v = samp[samp.verdict.isin(["correct", "minor", "major"])]
est = 0.0; var = 0.0; W = 0.0
for s, g in v.groupby("stratum"):
    Nh = g.weight.iloc[0] * (samp.stratum == s).sum()  # population size of the stratum
    ph = (g.verdict == "major").mean(); nh = len(g)
    est += Nh * ph; var += Nh ** 2 * ph * (1 - ph) / max(nh, 1); W += Nh
est /= W; se = math.sqrt(var) / W
print(f"stratified population estimate of the major-error rate: {est:.2%} (normal 95% CI {max(0,est-1.96*se):.2%}-{est+1.96*se:.2%}; use Wilson/rule of three when it is 0)")
rep["stratified_major"] = {"estimate": est, "se": se}
# table level
tab = v.groupby("group").verdict.apply(lambda s: (s == "major").any())
print(f"tables audited {len(tab)}; with at least one major error {int(tab.sum())} ({tab.mean():.1%})")
rep["tables"] = {"n": int(len(tab)), "with_major": int(tab.sum())}
# causes
causes = collections.Counter()
for k in v[v.verdict == "major"].key:
    c = [c for vv, c, *_ in reads[k] if vv == "major"]
    causes[c[0] if c else "?"] += 1
print("causes of major errors:", dict(causes)); rep["causes"] = dict(causes)
# inter-auditor agreement on double-read points
pairs = [(reads[k][0][0], reads[k][1][0]) for k in samp.key if len(reads.get(k, [])) >= 2]
if pairs:
    cats = ["correct", "minor", "major", "unverifiable"]
    agree = np.mean([a == b for a, b in pairs])
    po = agree; pe = sum((np.mean([a == c for a, _ in pairs])) * (np.mean([b == c for _, b in pairs])) for c in cats)
    kappa = (po - pe) / (1 - pe) if pe < 1 else float("nan")
    print(f"double-read points {len(pairs)}: raw agreement {agree:.1%}, Cohen kappa {kappa:.2f}")
    rep["agreement"] = {"n": len(pairs), "raw": agree, "kappa": kappa}
json.dump(rep, open(f"{D}/report.json", "w"), indent=1, default=float)
samp.to_csv(f"{D}/sample_with_verdicts.csv", index=False)
