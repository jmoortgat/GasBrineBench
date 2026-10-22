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
assert all(len(out[out.family == f]) <= n[f] for f in n), {f: (len(out[out.family == f]), n[f]) for f in n}
# rows added after the full audit (v1.2.2 on) follow the audited rows of each family: transcribed twice blind, not yet audited row by row
fams = [os.path.basename(x)[:-4] for x in glob.glob(os.path.join(a.repo, "data", "*.csv"))]
_rep2 = "release/audit_v1_2_2/fix_apply_report.csv"
_rm2 = {}
if os.path.exists(_rep2):
    _r = pd.read_csv(_rep2, keep_default_na=False, dtype=str)
    for r in _r[(_r.field == "__remove__") & (_r.status == "removal queued")].itertuples():
        _rm2[r.family] = _rm2.get(r.family, 0) + 1
extra = []
for f in fams:
    nf = len(pd.read_csv(os.path.join(a.repo, "data", f + ".csv"), usecols=["source"])) + _rm2.get(f, 0)  # positions before the v1.2.2 removals
    k = len(out[out.family == f])
    if nf > k:
        extra.append(pd.DataFrame({"family": f, "row_id_final": range(k, nf), "verdict": "", "status": "not-audited", "cause": "", "note": ""}))
if extra:
    out = pd.concat([out] + extra, ignore_index=True)
# the v1.2.2 audit of those added rows: row ids are positions in the released files before its own removals
A2 = "release/audit_v1_2_2"
if glob.glob(f"{A2}/results/*.csv"):
    r2 = pd.concat([pd.read_csv(f, keep_default_na=False, dtype=str).assign(cid=os.path.basename(f)[:-4]) for f in sorted(glob.glob(f"{A2}/results/*.csv"))],
                   ignore_index=True)
    r2["row_id"] = r2.row_id.astype(int)
    rep2 = pd.read_csv(f"{A2}/fix_apply_report.csv", keep_default_na=False, dtype=str) if os.path.exists(f"{A2}/fix_apply_report.csv") else pd.DataFrame(columns=["family", "row_id", "field", "status"])
    rep2["row_id"] = rep2.row_id.astype(int)
    ok2 = rep2[rep2.status.isin(["applied", "removal queued"])]
    ch2 = {(r.family, r.row_id) for r in ok2[ok2.field != "__remove__"].itertuples()}
    rm2 = {(r.family, r.row_id) for r in ok2[ok2.field == "__remove__"].itertuples()}
    v2 = {(r.family, r.row_id): r for r in r2.itertuples()}
    def st2(fam, rid):
        if (fam, rid) in rm2: return "removed", "", "", ""
        if (fam, rid) not in v2: return "not-audited", "", "", ""
        r = v2[(fam, rid)]
        if (fam, rid) in ch2: return "corrected", r.verdict, r.cause, r.note
        return {"correct": "verified", "unverifiable": "not-verifiable"}.get(r.verdict, "residual-difference"), r.verdict, r.cause, r.note
    rows = []
    for r in out.itertuples():
        if r.status == "not-audited":
            s_, v_, c_, n_ = st2(r.family, r.row_id_final)
            rows.append((r.family, r.row_id_final, v_, s_, c_, n_))
        else:
            rows.append((r.family, r.row_id_final, r.verdict, r.status, r.cause, r.note))
    out = pd.DataFrame(rows, columns=["family", "row_id_final", "verdict", "status", "cause", "note"])
    for fam in out.family.unique():
        rem = sorted(rid for f, rid in rm2 if f == fam)
        if rem:
            m = out.family == fam
            out.loc[m, "row_id_final"] = [rid - sum(1 for x in rem if x < rid) for rid in out.loc[m, "row_id_final"]]
    out = out[out.status != "removed"].reset_index(drop=True)
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
