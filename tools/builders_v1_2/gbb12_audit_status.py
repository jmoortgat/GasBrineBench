"""Per-row audit status of the final data (data/provenance/audit_status.csv) and the merged correction list (audit_corrections.csv).
Usage: python3 builder/gbb12_audit_status.py --repo PATH. Row ids of the audit refer to the release before the corrections; removals shift them, so ids are re-mapped."""
import argparse, glob, os
import pandas as pd
ap = argparse.ArgumentParser(); ap.add_argument("--repo", required=True); a = ap.parse_args()
res = []
for f in sorted(glob.glob("release/full_audit/results/*.csv")):
    d = pd.read_csv(f, keep_default_na=False, dtype=str); d["cid"] = os.path.basename(f)[:-4]; res.append(d)
res = pd.concat(res, ignore_index=True); res["row_id"] = res.row_id.astype(int)
fx = []
for f in sorted(glob.glob("release/full_audit/fixes/*.csv")):
    d = pd.read_csv(f, keep_default_na=False, dtype=str)
    if len(d): d["cid"] = os.path.basename(f)[:-4]; fx.append(d)
fx = pd.concat(fx, ignore_index=True); fx["row_id"] = fx.row_id.astype(int)
rep = pd.read_csv("release/full_audit/fix_apply_report.csv", keep_default_na=False, dtype=str); rep["row_id"] = rep.row_id.astype(int)
okfx = rep[rep.status.isin(["applied", "removal queued"])]
changed = {(r.family, r.row_id) for r in okfx[okfx.field != "__remove__"].itertuples()}
removed = {(r.family, r.row_id) for r in okfx[okfx.field == "__remove__"].itertuples()}
def status(r):
    k = (r.family, r.row_id)
    if k in removed: return "removed"
    if k in changed: return "corrected"
    if r.verdict == "unverifiable": return "not-verifiable"
    if r.verdict == "correct": return "verified"
    return "residual-difference"
res["status"] = [status(r) for r in res.itertuples()]
# re-map row ids to the final files
out = []
for fam, g in res.groupby("family"):
    rem = sorted(r for f, r in removed if f == fam)
    g = g[g.status != "removed"].copy()
    g["row_id_final"] = [r - sum(1 for x in rem if x < r) for r in g.row_id]
    out.append(g)
out = pd.concat(out, ignore_index=True)
n = {f: len(pd.read_csv(os.path.join(a.repo, "data", f + ".csv"), usecols=["source"])) for f in out.family.unique()}
assert all(len(out[out.family == f]) == n[f] for f in n), {f: (len(out[out.family == f]), n[f]) for f in n}
cols = out[["family", "row_id_final", "verdict", "status", "cause", "note"]].rename(columns={"row_id_final": "row_id", "verdict": "audit_verdict", "note": "audit_note"})
cols = cols.sort_values(["family", "row_id"])
os.makedirs(os.path.join(a.repo, "data", "provenance"), exist_ok=True)
cols.drop(columns=["audit_note"]).to_csv(os.path.join(a.repo, "data", "provenance", "audit_status.csv"), index=False, lineterminator="\n")
fx["reason"] = fx["reason"].str.slice(0, 300)
fx[["cid", "family", "row_id", "field", "old", "new", "reason", "confidence"]].to_csv(os.path.join(a.repo, "data", "provenance", "audit_corrections.csv"), index=False, lineterminator="\n")
print(out.status.value_counts().to_dict())
print(out.groupby(["status", "verdict"]).size())
res[(res.verdict == "major") & (res.status == "residual-difference")].to_csv("release/full_audit/residual_majors.csv", index=False)
