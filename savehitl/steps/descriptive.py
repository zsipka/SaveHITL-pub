"""Step: descriptive figures on the alerts of the test month that the existing step outputs do not hold. They decide
nothing: no deciding result, range or verdict reads them.

1. FPR and FNR by age group among the alerts, at capacity 0.75, teams B and C, for the three policies (full automation
   has no team). Counts per group are means over the five random orders: FP = sum over the group's legitimate alerts of
   (seeds confirming) / 5; FN = sum over the group's frauds of (5 - seeds confirming) / 5. Per version and the mean of
   the five versions. The FPRs are checked against the cell measures of policies 2 and 3 (same figure, other route).
2. Each of the 50 reviewers' FPR and TPR on the 4,457 alerts of month 7, from the reviewer's own decision with no team
   rule: FPR = legitimate alerts confirmed / legitimate alerts; TPR = frauds confirmed / frauds.
3. Classifier h on month 7: its ROC curve from its score, and its operating point at its built-in cut-off.

Reads (each stopped on the sha256 its step recorded): policy1/p1_per_case.csv, policy2/p2_seed_avg_per_case.parquet,
policy2/p2_cell_measures.csv, policy3/p3_seed_avg_per_case.parquet, policy3/p3_cell_measures.csv,
generator/data/expert_predictions.parquet, summaries/P2-T1a_members_slot_order.csv.

Outputs: fpr_fnr_by_age_075.csv, reviewers_month7.csv, classifier_roc_month7.csv, classifier_point_month7.csv.
"""
import json
import os

import numpy as np
import pandas as pd

from . import _common as C

SEEDS = 5
CAP = "0.75"
ANCHOR = 0.057


def checked(a, A, step, name, folder):
    p = os.path.join(folder, name)
    rec = json.load(open(os.path.join(folder, "record.json")))
    want = (rec.get("outputs_sha256") or {}).get(os.path.basename(name))
    A.check(want is not None and C.sha256(p) == want, "input equal to the checksum its step recorded", step=step, file=name)
    return p


def group_counts(dec_sum, lab, old):
    """Means over seeds of FP and FN per age group, from the number of seeds that confirm each alert."""
    out = {}
    for grp, m in (("50 or over", old), ("under 50", ~old), ("all ages", np.ones_like(old))):
        leg = m & (lab == 0)
        fr = m & (lab == 1)
        fp = dec_sum[leg].sum() / SEEDS
        fn = (SEEDS - dec_sum[fr]).sum() / SEEDS
        out[grp] = {"n_legitimate": int(leg.sum()), "fp": float(fp), "fpr": float(fp / leg.sum()), "n_frauds": int(fr.sum()),
                    "fn": float(fn), "fnr": float(fn / fr.sum())}
    return out


def main():
    a = C.args([("--policy1", {"required": True}), ("--policy2", {"required": True}), ("--policy3", {"required": True}),
                ("--generator", {"required": True}), ("--summaries", {"required": True})])
    A = C.Asserts(a)
    p1 = pd.read_csv(checked(a, A, "policy1", "p1_per_case.csv", a.policy1))
    A.check(len(p1) == 4457 and p1["case_id"].is_unique, "4,457 alerts of month 7")
    p1 = p1.set_index("case_id")
    lab = p1["label_fraud"].to_numpy()
    old = p1["age_50_plus"].to_numpy() == 1
    rows = []
    g = group_counts(p1["p1_reject"].to_numpy() * SEEDS, lab, old)
    for grp, v in g.items():
        rows.append({"policy": "full automation", "team": "", "version": "", **{"age_group": grp}, **v})
    cm = {2: pd.read_csv(checked(a, A, "policy2", "p2_cell_measures.csv", a.policy2), dtype={"capacity_label": str, "version": str}),
          3: pd.read_csv(checked(a, A, "policy3", "p3_cell_measures.csv", a.policy3), dtype={"capacity_label": str, "version": str})}
    for pol, folder, fname, pname in ((2, a.policy2, "p2_seed_avg_per_case.parquet", "naive review"),
                                      (3, a.policy3, "p3_seed_avg_per_case.parquet", "analyst-aware deferral")):
        d = pd.read_parquet(checked(a, A, f"policy{pol}", fname, folder), columns=["team", "version", "capacity_label", "case_id", "sum_decision"])
        d["capacity_label"] = d["capacity_label"].astype(str)
        d["version"] = d["version"].astype(str)
        d = d.loc[(d["capacity_label"] == CAP) & d["team"].isin(["B", "C"])]
        c = cm[pol]
        c = c.loc[(c["capacity_label"] == CAP) & (pd.to_numeric(c["lambda"]).sub(ANCHOR).abs() < 1e-12)]
        for team in ("B", "C"):
            per_v = []
            for v in ["1", "2", "3", "4", "5"]:
                x = d.loc[(d["team"] == team) & (d["version"] == v)].set_index("case_id").reindex(p1.index)
                A.check(x["sum_decision"].notna().all(), "every alert present", policy=pol, team=team, version=v)
                gv = group_counts(x["sum_decision"].to_numpy().astype(float), lab, old)
                ref = c.loc[(c["team"] == team) & (c["version"] == v)]
                A.check(len(ref) == SEEDS, "five seeds in the cell measures", policy=pol, team=team, version=v)
                for grp, col in (("50 or over", "false_positive_rate_50_plus"), ("under 50", "false_positive_rate_under_50")):
                    A.check(abs(gv[grp]["fpr"] - ref[col].mean()) < 1e-12, "FPR equal to the mean of the cell measures",
                            policy=pol, team=team, version=v, group=grp)
                fn_all = gv["all ages"]["fn"]
                A.check(abs(fn_all - ref["regulatory_exposure_accepted_frauds_count"].mean()) < 1e-9,
                        "frauds accepted equal to the mean of the cell measures", policy=pol, team=team, version=v)
                for grp, vv in gv.items():
                    rows.append({"policy": pname, "team": team, "version": v, "age_group": grp, **vv})
                per_v.append(gv)
            for grp in ("50 or over", "under 50", "all ages"):
                fp = float(np.mean([x[grp]["fp"] for x in per_v]))
                fn = float(np.mean([x[grp]["fn"] for x in per_v]))
                nl, nf = per_v[0][grp]["n_legitimate"], per_v[0][grp]["n_frauds"]
                rows.append({"policy": pname, "team": team, "version": "mean of 5 versions", "age_group": grp, "n_legitimate": nl,
                             "fp": fp, "fpr": fp / nl, "n_frauds": nf, "fn": fn, "fnr": fn / nf})
    fpfn = pd.DataFrame(rows)
    A.check(bool((fpfn["n_legitimate"] >= 10).all() and (fpfn["n_frauds"] >= 10).all()), "every group holds at least 10 alerts")
    fpfn.insert(3, "capacity", CAP)
    fpfn.loc[fpfn["policy"] == "full automation", "capacity"] = ""

    # reviewers on month 7
    ep = pd.read_parquet(checked(a, A, "generator", os.path.join("data", "expert_predictions.parquet"), a.generator))
    A.check(set(p1.index).issubset(set(ep.index)), "every month-7 alert in the reviewers' decisions")
    ep = ep.reindex(p1.index)
    mem = pd.read_csv(checked(a, A, "summaries", "P2-T1a_members_slot_order.csv", a.summaries), dtype={"version": str})
    rows = []
    for _, r in mem.iterrows():
        for s in range(10):
            twin = r[f"slot {s}"]
            dec = ep[twin].to_numpy()
            A.check(set(np.unique(dec).tolist()) <= {0, 1}, "reviewer decisions are 0 or 1", twin=twin)
            fpr = ((dec == 1) & (lab == 0)).sum() / (lab == 0).sum()
            tpr = ((dec == 1) & (lab == 1)).sum() / (lab == 1).sum()
            rows.append({"version": r["version"], "slot": s, "reviewer": twin, "fpr": float(fpr), "tpr": float(tpr)})
    rev = pd.DataFrame(rows)
    A.check(len(rev) == 50 and rev["reviewer"].is_unique, "50 distinct reviewers")

    # Classifier h on month 7
    from sklearn.metrics import roc_curve
    fpr, tpr, _ = roc_curve(lab, p1["classifier_score"].to_numpy())
    roc = pd.DataFrame({"fpr": fpr, "tpr": tpr})
    dec = p1["p1_reject"].to_numpy()
    nl, nf = int((lab == 0).sum()), int((lab == 1).sum())
    pt = pd.DataFrame([{"fpr": ((dec == 1) & (lab == 0)).sum() / nl, "tpr": ((dec == 1) & (lab == 1)).sum() / nf, "n_legitimate": nl,
                        "n_frauds": nf, "lambda": ANCHOR, "equal_cost_slope": ANCHOR * nl / nf}])

    outs = {"fpr_fnr_by_age_075.csv": fpfn, "reviewers_month7.csv": rev, "classifier_roc_month7.csv": roc,
            "classifier_point_month7.csv": pt}
    for n, d in outs.items():
        d.to_csv(os.path.join(a.out, n), index=False, float_format="%.17g")
    C.write_record(a, {"step": a.step, "outputs_sha256": {n: C.sha256(os.path.join(a.out, n)) for n in outs}})


if __name__ == "__main__":
    main()
