"""Step: the summary tables the notebook reads, from this run's own outputs: P2-T1 (the drawn teams, the reviewers'
targets and regenerated figures, team B's and team C's test-month items), P3-T9 (access to a reviewer by age group,
policies 2 and 3) and P3-T1's ranking part (month 7 beside month 6).

No result is computed afresh: every figure is copied from an earlier step's output or formed here from such values by a
mean, minimum, maximum, sum, ratio of two counts or difference, as the study's summary script; each table's provenance
is in the step's record. The reviewers' per-reviewer figures (P2-T1c, P2-T1d) are formed here as the study's check
P2-G (d) formed them (false positive rate, miss rate, cost per case at 0.057, age gap, on file months 3 to 6 and on file
month 6), for the regenerated reviewers only; the dataset's reviewers are not compared.

Outputs: P2-T1a_members_slot_order.csv, P2-T1b_draw.csv, P2-T1c_team_version_rates.csv, P2-T1d_twins.csv,
P2-T1e_month7_items.csv, P3-T9a_per_seed.csv, P3-T9_access_by_age.csv, P3-T1_ranking_month6_month7.csv.
"""
import json
import os

import numpy as np
import pandas as pd

from . import _chain as CH
from . import _common as C

OLD, YNG = "50 or over", "under 50"
CAPS_T9 = ["1.00", "10/11", "0.75", "0.65"]
MEAN5 = "mean of 5 versions"
LAMBDA = 0.057
# Cell labels of P3-T9, word for word from the policy 3 design's P3-T9 row
LAB = {"C_ZERO": "0 by construction", "B_EQUAL": "identical to team A by construction",
       "P2_C_CELL": ("Reviewed, but the outcome is fixed by team C's rule: every such alert is confirmed under policies 1, 2 and 3 "
                     "(policy 2 and policy 3 designs, section 2.1). The share is review capacity spent without effect on the decision: "
                     "access to a reviewer, not a better outcome."),
       "ROW_I_NOTE": "Policy 2's overall share for applicants aged 50 or over includes these alerts.",
       "NOT_DEFINED": "Not defined"}


def measures(dec, y, old):
    """As the study's P2-G (d): dec decisions (0/1) of one reviewer; y fraud_bool; old aged 50 or over."""
    leg, fr = y == 0, y == 1
    fp = int(((dec == 1) & leg).sum()); fn = int(((dec == 0) & fr).sum())
    fpr_old = float(((dec == 1) & leg & old).sum() / (leg & old).sum())
    fpr_young = float(((dec == 1) & leg & ~old).sum() / (leg & ~old).sum())
    return {"fpr": fp / int(leg.sum()), "miss_rate": fn / int(fr.sum()),
            "cost_per_case_lambda_0.057": (LAMBDA * fp + fn) / len(y),
            "fpr_age_50_plus": fpr_old, "fpr_age_under_50": fpr_young, "age_gap": fpr_old - fpr_young}


def main():
    a = C.args([("--generator", {"required": True}), ("--draw", {"required": True}), ("--policy2", {"required": True}),
                ("--policy3", {"required": True}), ("--ranking", {"required": True})])
    A = C.Asserts(a)
    L = a.L
    tables = {}

    def save(df, name, provenance):
        p = os.path.join(a.out, name)
        df.to_csv(p, index=False, float_format="%.17g")
        tables[name] = {"rows": int(len(df)), "provenance": provenance, "sha256": C.sha256(p)}

    # ---- teams
    draw = json.load(open(os.path.join(a.draw, "teams.json")))
    slots = CH.load_teams(A, a.draw)
    p2rec = json.load(open(os.path.join(a.policy2, "record.json")))
    A.check({int(v): list(m) for v, m in p2rec["team_versions_slot_order"].items()} == slots,
            "policy 2's team versions equal the draw's")
    members = sorted({m for ms in slots.values() for m in ms}, key=lambda s: int(s.split("#")[1]))
    A.check(len(members) == 50 and sum(len(m) for m in slots.values()) == 50, "50 reviewers, each in exactly one team")
    save(pd.DataFrame([{"version": v, **{f"slot {i}": m for i, m in enumerate(slots[v])}} for v in sorted(slots)]),
         "P2-T1a_members_slot_order.csv", "copied from the draw step's teams.json (equal to policy 2's record)")
    t1draw = pd.DataFrame([
        {"item": "seed", "value": str(draw["seed"])}, {"item": "call", "value": draw["call"]},
        {"item": "generator", "value": draw["generator"]}, {"item": "NumPy version", "value": draw["numpy_version"]},
        {"item": "permutation", "value": " ".join(str(x) for x in draw["permutation"])}, {"item": "rule", "value": draw["rule"]},
        *[{"item": f"drawn team {v}, twins in slot order", "value": " ".join(slots[v])} for v in sorted(slots)],
        {"item": "twins used, of 50", "value": str(len(members))}, {"item": "twins in two versions", "value": "0"}])
    save(t1draw, "P2-T1b_draw.csv", "copied from the draw step's teams.json; the two counts formed here from the five lists")

    # ---- per-reviewer figures, as P2-G (d), regenerated reviewers only
    alerts = pd.read_parquet(os.path.join(L.fifar, "alert_data", "processed_data", "alerts.parquet"),
                             columns=["month", "fraud_bool", "customer_age"])
    alerts = alerts.loc[alerts["month"].isin([3, 4, 5, 6])]
    tpred = CH.load_twins(A, L, a.generator, (3, 4, 5, 6))
    A.check(set(tpred.index) == set(alerts.index), "reviewers' alerts equal the months 3 to 6 alerts")
    tpred = tpred.loc[alerts.index]
    A.check(bool(np.isin(tpred.to_numpy(), [0, 1]).all()) and not alerts["customer_age"].isna().any(),
            "decisions only 0 or 1; no missing age")
    grec = json.load(open(os.path.join(a.generator, "record.json")))
    tpath = os.path.join(a.generator, "targets.csv")
    A.check(C.sha256(tpath) == grec["targets_sha256"], "targets equal to the checksum the generator step recorded")
    tg = pd.read_csv(tpath).set_index("expert")
    prev, lam = grec["fit"]["prevalence_fit_set"], grec["fit"]["lambda"]
    periods = {"months_3_6": np.ones(len(alerts), bool), "month_6": (alerts["month"] == 6).to_numpy()}
    rows = []
    for i in range(50):
        tw = f"unbiased#{i}"
        r = {"expert_index": i, "twin": tw, "twin_target_fpr": float(tg.at[tw, "target_fpr"]),
             "twin_target_miss_rate": float(tg.at[tw, "target_fnr"]),
             "twin_target_cost_per_case": float(lam * (1 - prev) * tg.at[tw, "target_fpr"] + prev * tg.at[tw, "target_fnr"])}
        for pname, mask in periods.items():
            y = alerts["fraud_bool"].to_numpy()[mask]
            old = alerts["customer_age"].to_numpy()[mask] >= 50
            for k, v in measures(tpred[tw].to_numpy()[mask], y, old).items():
                r[f"twin_{k}_{pname}"] = v
        rows.append(r)
    ex = pd.DataFrame(rows)
    NUM = [c for c in ex.columns if c not in ("expert_index", "twin")]
    t1c = pd.DataFrame([{"team_version": v, "members_twin": " ".join(ms),
                         **{c: float(ex.set_index("twin").loc[ms][c].mean()) for c in NUM}} for v, ms in slots.items()])
    save(t1c, "P2-T1c_team_version_rates.csv",
         "formed here: mean of the 10 members' per-reviewer figures (P2-G (d) definitions, regenerated reviewers only)")
    pars = pd.read_parquet(os.path.join(a.generator, "data", "expert_parameters.parquet"))
    ver_of = {m: v for v, ms in slots.items() for m in ms}
    cols_e = ["twin", "twin_target_fpr", "twin_target_miss_rate", "twin_target_cost_per_case", "twin_fpr_months_3_6",
              "twin_fpr_month_6", "twin_miss_rate_months_3_6", "twin_miss_rate_month_6",
              "twin_cost_per_case_lambda_0.057_months_3_6", "twin_cost_per_case_lambda_0.057_month_6",
              "twin_age_gap_months_3_6", "twin_age_gap_month_6"]
    e = ex[cols_e].copy()
    e.insert(0, "drawn_team", e["twin"].map(ver_of))
    e.insert(1, "slot", [slots[ver_of[t]].index(t) for t in e["twin"]])
    e["twin_weight_model_score"] = e["twin"].map(pars["model_score"])
    e["twin_weight_customer_age"] = e["twin"].map(pars["customer_age"])
    A.check(bool(e["twin_weight_model_score"].notna().all() and e["twin_weight_customer_age"].notna().all()),
            "every reviewer has its two weights")
    save(e.sort_values(["drawn_team", "slot"]).reset_index(drop=True), "P2-T1d_twins.csv",
         "formed here as P2-G (d) (per reviewer); weights copied from the generator's expert_parameters.parquet")

    # ---- test-month items (policy 2 cells), capacities 1 and 0.75
    cells = pd.read_csv(CH.step_output(A, a.policy2, "p2_cell_measures.csv"), dtype={"capacity_label": str})
    c7 = cells[np.isclose(cells["lambda"], 0.057, rtol=0, atol=1e-12) & cells["capacity_label"].isin(["1.00", "0.75"])].copy()
    A.check(len(c7) == 3 * 5 * 2 * 5, "150 cells at 0.057, capacities 1 and 0.75")
    c7["team_b_measured_agreement_with_classifier"] = 1 - c7["override_rate_differs_from_classifier"]
    c7["team_b_share_reviewed_twin_differs_from_classifier"] = c7["n_reviewed_twin_classifier_disagree"] / c7["n_reviewed"]
    ITEMS = {"C": [("rule_c_changes_fraud", "copied"), ("rule_c_changes_legitimate", "copied")],
             "B": [("team_b_measured_agreement_with_classifier", "formed here: 1 - override_rate_differs_from_classifier"),
                   ("team_b_share_reviewed_twin_differs_from_classifier",
                    "formed here: n_reviewed_twin_classifier_disagree / n_reviewed (base of the share deferred)"),
                   ("team_b_share_disagreements_deferred", "copied")]}
    rows = []
    for team, its in ITEMS.items():
        for it, how in its:
            for cap in ["1.00", "0.75"]:
                for v in [1, 2, 3, 4, 5]:
                    g = c7[(c7["team"] == team) & (c7["version"] == v) & (c7["capacity_label"] == cap)]
                    if not (len(g) == 5 and sorted(g["seed"]) == [1, 2, 3, 4, 5]):
                        A.check(False, "five seeds per cell", team=team, item=it, capacity=cap, version=v)
                    rows.append({"team": team, "item": it, "capacity": cap, "version": v, "per-seed value": how,
                                 "mean over 5 seeds": float(g[it].mean()), "lowest seed": float(g[it].min()),
                                 "highest seed": float(g[it].max()), **{f"seed {s}": float(x) for s, x in zip(g["seed"], g[it])}})
    save(pd.DataFrame(rows), "P2-T1e_month7_items.csv",
         "policy 2's cell measures at lambda 0.057; mean, lowest and highest over the 5 seeds formed here")

    # ---- P3-T9 (policy 3's access-by-age counts)
    AA = pd.read_csv(CH.step_output(A, a.policy3, "p3_access_by_age.csv"), dtype={"version": str, "capacity_label": str})
    AA = AA[AA["capacity_label"].isin(CAPS_T9)]
    A.check(set(AA["age_group"]) == {OLD, YNG} and set(AA["classifier_decision"]) == {"confirm", "dismiss"}
            and len(AA) == 2 * 3 * 5 * 5 * 4 * 4, "access-by-age counts: 2 policies x 3 teams x 5 versions x 5 seeds x 4 "
            "capacities x 4 groups")

    def share(n_sent, n):
        return np.where(n > 0, n_sent / np.where(n > 0, n, 1), np.nan)

    k7 = ["policy", "team", "version", "seed", "capacity_label", "age_group"]
    g = AA.groupby(k7 + ["classifier_decision"])[["n_alerts", "n_sent_to_reviewer"]].sum().reset_index()
    ov = g.groupby(k7)[["n_alerts", "n_sent_to_reviewer"]].sum().reset_index().assign(classifier_decision="all")
    g = pd.concat([g, ov], ignore_index=True)
    g["share"] = share(g["n_sent_to_reviewer"].to_numpy(), g["n_alerts"].to_numpy())
    SH = {"all": "(i) overall", "confirm": "(ii) classifier would confirm", "dismiss": "(iii) classifier would dismiss"}
    g["share kind"] = g["classifier_decision"].map(SH)
    save(g.sort_values(k7 + ["share kind"])[k7 + ["share kind", "n_alerts", "n_sent_to_reviewer", "share"]],
         "P3-T9a_per_seed.csv", "counts copied from policy 3's access-by-age file (group (i) summed from (ii) and (iii)); "
         "share = sent / alerts, formed here")
    pv = g.groupby(["policy", "team", "version", "capacity_label", "share kind", "age_group"]).agg(
        n_alerts=("n_alerts", "first"), n_alerts_n_values=("n_alerts", "nunique"), n_sent_pooled=("n_sent_to_reviewer", "sum"),
        share_mean=("share", "mean"), share_seed_low=("share", "min"), share_seed_high=("share", "max"),
        n_seeds=("seed", "nunique")).reset_index()
    A.check(bool((pv["n_alerts_n_values"] == 1).all() and (pv["n_seeds"] == 5).all()), "alert counts equal across seeds; 5 seeds")
    pv = pv.drop(columns=["n_alerts_n_values", "n_seeds"]).assign(routings_pooled=5)
    m5 = pv.groupby(["policy", "team", "capacity_label", "share kind", "age_group"]).agg(
        share_mean=("share_mean", "mean"), n_alerts=("n_alerts", "first"), n_sent_pooled=("n_sent_pooled", "sum"),
        share_version_low=("share_mean", "min"), share_version_high=("share_mean", "max")).reset_index().assign(
        version=MEAN5, routings_pooled=25)
    allv = pd.concat([pv, m5], ignore_index=True, sort=False)
    wide = allv.pivot_table(index=["policy", "team", "version", "capacity_label", "share kind"], columns="age_group",
                            values=["share_mean", "share_seed_low", "share_seed_high", "share_version_low", "share_version_high",
                                    "n_alerts", "n_sent_pooled", "routings_pooled"], aggfunc="first", dropna=False)
    wide.columns = [f"{x} [{y}]" for x, y in wide.columns]
    wide = wide.reset_index()
    wide["difference, percentage points (50 or over minus under 50)"] = 100 * (wide[f"share_mean [{OLD}]"] - wide[f"share_mean [{YNG}]"])

    def cell_label(r):
        labs = []
        if r["policy"] == "policy 3" and r["team"] == "C" and r["share kind"] == SH["confirm"]:
            labs.append(f"[{OLD}]: " + LAB["C_ZERO"])
        if r["policy"] == "policy 3" and r["team"] == "B":
            labs.append(LAB["B_EQUAL"])
        if r["policy"] == "policy 2" and r["team"] == "C" and r["share kind"] == SH["confirm"]:
            labs.append(f"[{OLD}]: " + LAB["P2_C_CELL"])
        if r["policy"] == "policy 2" and r["team"] == "C" and r["share kind"] == SH["all"]:
            labs.append("note: " + LAB["ROW_I_NOTE"])
        for grp in (OLD, YNG):
            if not (r[f"n_alerts [{grp}]"] > 0):
                labs.append(f"[{grp}]: " + LAB["NOT_DEFINED"])
        return " | ".join(labs)

    wide["cell labels"] = wide.apply(cell_label, axis=1)
    c0 = wide[(wide["policy"] == "policy 3") & (wide["team"] == "C") & (wide["share kind"] == SH["confirm"])][f"n_sent_pooled [{OLD}]"]
    A.check(int((c0 > 0).sum()) == 0, "policy 3, team C, aged 50 or over, classifier would confirm: no alert sent")
    kcols = [c for c in wide.columns if c.startswith(("share_", "n_", "difference"))]
    a3 = wide[(wide["policy"] == "policy 3") & (wide["team"] == "A")].set_index(["version", "capacity_label", "share kind"])[kcols]
    b3 = wide[(wide["policy"] == "policy 3") & (wide["team"] == "B")].set_index(["version", "capacity_label", "share kind"])[kcols]
    A.check(bool(((a3 - b3.reindex(a3.index)).abs().fillna(0).to_numpy() == 0).all()),
            "policy 3: team B equal to team A in every figure")
    wide["capacity_label"] = pd.Categorical(wide["capacity_label"], CAPS_T9, ordered=True)
    vorder = {str(v): v for v in range(1, 6)}
    vorder[MEAN5] = 6
    wide["_v"] = wide["version"].map(vorder)
    T9 = wide.sort_values(["team", "capacity_label", "_v", "share kind", "policy"]).drop(columns="_v")
    T9["capacity_label"] = T9["capacity_label"].astype(str)
    save(T9, "P3-T9_access_by_age.csv",
         "counts copied from policy 3's access-by-age file; formed here: overall counts (i) = (ii) + (iii); counts summed "
         "over seeds and versions; shares; seed lowest and highest per version; means over seeds and over versions; lowest "
         "and highest version mean; differences in percentage points. Labels word for word from the design's P3-T9 row")

    # ---- P3-T1, ranking part: month 7 beside month 6
    m6 = pd.read_csv(CH.step_output(A, a.ranking, "p3_ranking_month6_per_model.csv"))
    m7r = pd.read_csv(CH.step_output(A, a.ranking, "p3_ranking_month7_per_model.csv"))
    m7v = pd.read_csv(CH.step_output(A, a.ranking, "p3_ranking_month7_by_version.csv"))
    A.check(len(m6) == 250 and len(m7r) == 250, "250 models on each month")
    rk = []
    for v in [1, 2, 3, 4, 5]:
        a6 = m6.loc[m6["drawn_team"] == v, "ranking_quality_route_1"].to_numpy()
        a7 = m7r.loc[m7r["team_version"] == v, "ranking_quality_route_1"].to_numpy()
        avg7 = float(m7v.loc[m7v["team_version"] == v, "average_over_the_50_models_of_the_version"].iloc[0])
        A.check(len(a6) == 50 and len(a7) == 50 and abs(avg7 - a7.mean()) <= 1e-12,
                "50 models per version; month-7 average equal to the mean of the models", version=v)
        rk.append({"team_version": v, "month 6 average of 50 models": float(a6.mean()), "month 6 lowest model": float(a6.min()),
                   "month 6 highest model": float(a6.max()), "month 6 models at or below 0.5": int((a6 <= 0.5).sum()),
                   "month 7 average of 50 models": avg7, "month 7 lowest model": float(a7.min()),
                   "month 7 highest model": float(a7.max()), "month 7 models at or below 0.5": int((a7 <= 0.5).sum())})
    a6, a7 = m6["ranking_quality_route_1"].to_numpy(), m7r["ranking_quality_route_1"].to_numpy()
    rk.append({"team_version": "all 250 models", "month 6 average of 50 models": float(a6.mean()),
               "month 6 lowest model": float(a6.min()), "month 6 highest model": float(a6.max()),
               "month 6 models at or below 0.5": int((a6 <= 0.5).sum()), "month 7 average of 50 models": float(a7.mean()),
               "month 7 lowest model": float(a7.min()), "month 7 highest model": float(a7.max()),
               "month 7 models at or below 0.5": int((a7 <= 0.5).sum())})
    save(pd.DataFrame(rk), "P3-T1_ranking_month6_month7.csv",
         "route-1 values copied from the ranking step's per-model files; month-7 version averages copied from its by-version "
         "file; month-6 averages, lowest, highest and counts at or below 0.5 formed here. The 'all 250 models' row's average "
         "is over 250 models, not 50")
    C.write_record(a, {"step": a.step, "tables": tables, "outputs_sha256": {n: v["sha256"] for n, v in tables.items()}})


if __name__ == "__main__":
    main()
