"""Apply the correction lists written by the full row-by-row audit (release/full_audit/fixes/<cid>.csv).

Each line: family,row_id,field,old,new,reason,confidence. row_id is the position in data/<family>.csv (header excluded) of the release this audit read;
the lists are applied to the merged frames at the same stage of gbb12_release.py (after the same-source dedupe, before the quality rules), so positions agree.
`old` is a guard: a line whose `old` does not equal the current value is skipped and reported. Removals are applied last."""
import glob, os
import pandas as pd

NUM_FIELDS = {"T_K", "P_bar", "value", "uncertainty", "m_Na", "m_K", "m_Ca", "m_Mg", "m_Cl", "m_SO4"}
FIELDS = NUM_FIELDS | {"flags_add", "__remove__"}


def _same(a, b):
    try:
        a, b = float(a), float(b)
        return abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))
    except (TypeError, ValueError):
        return str(a).strip() == str(b).strip()


def _fmt(x):
    return f"{float(x):.10g}"


def apply(merged, fixes_dir, ledger, report_path=None):
    frames = []
    for f in sorted(glob.glob(os.path.join(fixes_dir, "*.csv"))):
        d = pd.read_csv(f, dtype=str, keep_default_na=False)
        if len(d):
            d["cid"] = os.path.basename(f)[:-4]
            frames.append(d)
    if not frames:
        return
    fx = pd.concat(frames, ignore_index=True)
    rep, remove = [], {}
    n_applied = {}
    seen = set()
    for _, r in fx.iterrows():
        fam, field = r["family"], r["field"]
        if field not in FIELDS or fam not in merged:
            rep.append({**r, "status": "skipped: unknown family or field"}); continue
        df = merged[fam]
        i = int(r["row_id"])
        if not 0 <= i < len(df):
            rep.append({**r, "status": "skipped: row out of range"}); continue
        key = (fam, i, field)
        if key in seen and field != "flags_add":
            rep.append({**r, "status": "skipped: duplicate line for this row and field"}); continue
        seen.add(key)
        if field == "__remove__":
            remove.setdefault(fam, set()).add(i)
            rep.append({**r, "status": "removal queued"}); continue
        if field == "flags_add":
            cur = [t for t in str(df.at[i, "flags"]).split(";") if t]
            if r["new"] == "calculated-not-measured":
                cur = [t for t in cur if t != "figure-digitized"]   # one origin per row: calculated wins over figure
            elif r["new"] == "figure-digitized" and "calculated-not-measured" in cur:
                continue
            if r["new"] not in cur:
                cur = cur + [r["new"]]
            df.at[i, "flags"] = ";".join(sorted(cur))
            n_applied[r["cid"]] = n_applied.get(r["cid"], 0) + 1
            rep.append({**r, "status": "applied"}); continue
        cur = df.at[i, field]
        if not _same(cur, r["old"]):
            rep.append({**r, "status": f"skipped: guard failed (current {cur})"}); continue
        df.at[i, field] = _fmt(r["new"])
        n_applied[r["cid"]] = n_applied.get(r["cid"], 0) + 1
        rep.append({**r, "status": "applied"})
    # molality / mole-fraction siblings must stay consistent: m = x/(1-x)/M_W. Where a correction changed only one row of a pair, the other
    # follows; where both printed digits were applied (the paper rounds m and x separately) the molality is kept and x is derived.
    if "solubility" in merged:
        df = merged["solubility"]
        ION = ["m_Na", "m_K", "m_Ca", "m_Mg", "m_Cl", "m_SO4"]
        changed_val = {(r["family"], int(r["row_id"])) for r in rep if r.get("field") == "value" and r.get("status") == "applied"}
        pr = df["property"].values
        keycols = ["dataset_id", "gas", "T_K", "P_bar", *ION]
        sub = df[df["property"].isin(["solubility_molality", "xc_saltfree"])]
        n_sib = 0
        for _, g in sub.groupby(keycols, sort=False):
            mrows = [i for i in g.index if pr[i] == "solubility_molality"]
            xrows = [i for i in g.index if pr[i] == "xc_saltfree"]
            for mi, xi in zip(mrows, xrows):
                m = float(df.at[mi, "value"]); x = float(df.at[xi, "value"])
                if abs(x - m / (m + (1.0 / 0.01801528))) <= 1e-9 + 1e-6 * abs(x):
                    continue
                xc = ("solubility", xi) in changed_val
                mc = ("solubility", mi) in changed_val
                if xc and not mc:
                    df.at[mi, "value"] = _fmt(x / (1.0 - x) * (1.0 / 0.01801528))
                else:
                    df.at[xi, "value"] = _fmt(m / (m + (1.0 / 0.01801528)))
                n_sib += 1
        print("audit fixes: sibling rows re-derived:", n_sib)
    for fam, rows in remove.items():
        df = merged[fam]
        merged[fam] = df.drop(index=sorted(rows)).reset_index(drop=True)
    for cid, n in sorted(n_applied.items()):
        ledger.append({"dataset_id": cid, "rows": n, "action": "corrected from the paper (full audit)", "reason": f"{n} field corrections from the row-by-row audit"})
    rp = pd.DataFrame(rep)
    if report_path:
        rp.to_csv(report_path, index=False)
    print("audit fixes:", rp["status"].str.split(":").str[0].value_counts().to_dict())
