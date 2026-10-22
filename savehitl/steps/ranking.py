"""Step: how well the router ranks its reviewers, on file month 6 (the month that selected each model) and on the test
month (file month 7). Descriptive; no verdict, no threshold.

For each of the 250 router models (drawn team r, shuffle s, reviewer i), on all alerts of the month: the area under the
ROC curve of the model's score for reviewer i against c = 1 if reviewer i's decision equals the fraud label, else 0;
each alert weighted by its fraud label (0.057 if legitimate, 1 if fraud), computed exactly. Two routes
(`savehitl.boot.auc_routes`, the study's module): scikit-learn's weighted area, and a weighted rank sum written
without scikit-learn; they must agree within 1e-9 for every model. Month 6: the models' predictions on the month-6
alerts (router input as the framework's `run_ova.py:66-68`, alerts in the file's order). Month 7: the router's
predictions of the predict step. Weights asserted exactly 0.057 and 1 by fraud label; the auc_routes self-test runs
first; negative control: two reviewer columns swapped must change the result; near-tolerance controls of the
route rule: a route-2 value 2e-9 from route 1 must fail it, 5e-10 must not. Averages per team version are reported.

Outputs: p3_ranking_month6_per_model.csv, p3_ranking_month7_per_model.csv, p3_ranking_month7_by_version.csv.
"""
import os
import pickle

import numpy as np
import pandas as pd
import yaml

from ..boot import auc_routes as AR
from . import _chain as CH
from . import _common as C

ROUTE_TOL = 1e-9


def route_failures(per):
    """The two-route rule: rows whose |route 1 - route 2| is not within 1e-9 (an undefined value fails)."""
    d = (per["ranking_quality_route_1"] - per["ranking_quality_route_2"]).abs()
    return per.index[~(d <= ROUTE_TOL)].tolist()


def near_tolerance_controls(per):
    """On copies of the per-model table: one route-2 value set to route 1 + 2e-9 must fail the rule, and + 5e-10 must
    not."""
    i = per.index[0]
    out = per.copy(); out.loc[i, "ranking_quality_route_2"] = per.loc[i, "ranking_quality_route_1"] + 2e-9
    inside = per.copy(); inside.loc[i, "ranking_quality_route_2"] = per.loc[i, "ranking_quality_route_1"] + 5e-10
    return (i in route_failures(out)) and (i not in route_failures(inside))


def cat_checker(data, features, cat_dict):          # Code/expert_models/run_ova.py:9-15
    new_data = data.copy()
    for feature in features:
        if new_data[feature].dtype.categories.to_list() != cat_dict[feature]:
            new_data[feature] = pd.Categorical(new_data[feature].values, categories=cat_dict[feature])
    return new_data


def main():
    a = C.args([("--generator", {"required": True}), ("--draw", {"required": True}), ("--router", {"required": True}),
                ("--predict", {"required": True})])
    A = C.Asserts(a)
    L = a.L
    rels = {"alerts": "FiFAR/alert_data/processed_data/alerts.parquet", "cfg": "Code/alert_data/dataset_cfg.yaml"}
    for rel in rels.values():
        A.check(C.sha256(os.path.join(L.framework, rel)) == C.input_sha(L, rel), "input at its checksum", file=rel)
    cfg = yaml.safe_load(open(os.path.join(L.framework, rels["cfg"])))
    lam = float(cfg["lambda"])
    A.check(lam == 0.057, "lambda of the dataset configuration is 0.057")
    ok_self, self_out = AR.self_test()
    A.check(ok_self, "auc_routes self-test", **self_out)
    teams = CH.load_teams(A, a.draw)
    setups = [CH.setup_name(r, s) for r in CH.VERSIONS for s in CH.SEEDS]
    models = pd.read_csv(os.path.join(a.router, "router_models.csv"), dtype=str)
    alerts = pd.read_parquet(os.path.join(L.framework, rels["alerts"]))

    # ---- month 6: predictions of each model on the month-6 alerts (file order), as the study's P3-G (c)
    m6 = alerts.loc[alerts["month"] == 6]
    m6 = cat_checker(m6, cfg["data_cols"]["categorical"], cfg["categorical_dict"])
    y6 = m6["fraud_bool"].astype(int).to_numpy()
    x6 = m6.drop(columns=["month", "fraud_bool"])
    tw6 = CH.load_twins(A, L, a.generator, (6,)).loc[x6.index]
    w6 = np.where(y6 == 1, 1.0, lam)
    A.check(bool(np.all((w6 == 0.057) | (w6 == 1.0)) and np.array_equal(w6 == 1.0, y6 == 1)),
            "month 6: weights exactly 0.057 and 1 by fraud label")
    rows6, sc6 = [], {}
    for setup in setups:
        r = int(setup.split("#drawn_")[1])
        for twin in teams[r]:
            m = models.loc[(models["setup"] == setup) & (models["twin"] == twin)]
            A.check(len(m) == 1, "one router model per set-up and reviewer", setup=setup, twin=twin)
            mp = os.path.join(a.router, "models", setup, twin, "best_model.pickle")
            if C.sha256(mp) != m["best_model_sha256"].iloc[0]:
                A.check(False, "router model as written by step router", setup=setup, twin=twin)
            with open(mp, "rb") as fh:
                model = pickle.load(fh)
            if list(model.booster_.feature_name()) != list(x6.columns):
                A.check(False, "feature order equal to the model's", setup=setup, twin=twin)
            sc = model.predict_proba(x6)[:, 1].astype(np.float64)
            sc6[(setup, twin)] = sc
            c = (tw6[twin].to_numpy() == y6).astype(int)
            r1, r2 = AR.auc_sk(c, sc, w6), AR.auc_rank(c, sc, w6)
            rows6.append({"setup": setup, "drawn_team": r, "shuffle": int(setup.split("#")[0].split("_")[1]), "twin": twin,
                          "router_run": "this run", "model_sha256": m["best_model_sha256"].iloc[0], "n_alerts_month6": len(y6),
                          "ranking_quality_route_1": r1, "ranking_quality_route_2": r2, "route_difference": abs(r1 - r2)})
    per6 = pd.DataFrame(rows6)
    s0 = setups[0]; t0, t1 = teams[int(s0.split("#drawn_")[1])][:2]
    v_sw = AR.auc_sk((tw6[t1].to_numpy() == y6).astype(int), sc6[(s0, t0)], w6)
    ctl6 = bool(v_sw != float(per6.loc[(per6.setup == s0) & (per6.twin == t0), "ranking_quality_route_1"].iloc[0]))
    d6 = (per6["ranking_quality_route_1"] - per6["ranking_quality_route_2"]).abs()
    A.check(len(per6) == 250 and not route_failures(per6), "month 6: the two routes agree within 1e-9 for 250 models",
            largest=float(d6.max()))
    A.check(near_tolerance_controls(per6), "month 6: near-tolerance controls of the route rule (2e-9 fails, 5e-10 passes)")
    A.check(ctl6, "month 6: negative control (two reviewer columns swapped) changes the result")

    # ---- month 7: the predict step's tables, as the study's month-7 ranking
    preds = pickle.load(open(CH.step_output(A, a.predict, "p3_router_month7_predictions.pkl"), "rb"))
    twins = CH.load_twins(A, L, a.generator, (CH.TEST_MONTH,)).sort_index()
    al = alerts.loc[alerts["month"] == CH.TEST_MONTH, ["fraud_bool"]].sort_index()
    A.check(np.array_equal(al.index.to_numpy(), twins.index.to_numpy()), "month 7: reviewers' alerts equal the alerts")
    y = al["fraud_bool"].to_numpy().astype(int)
    w = np.where(y == 1, 1.0, lam)
    A.check(bool(np.all((w == 0.057) | (w == 1.0)) and np.array_equal(w == 1.0, y == 1)),
            "month 7: weights exactly 0.057 and 1 by fraud label")

    def ranking(P):
        rows = []
        for r in CH.VERSIONS:
            for s in CH.SEEDS:
                tb = P[CH.setup_name(r, s)]
                assert np.array_equal(tb.index.to_numpy(), twins.index.to_numpy())
                for t in [c for c in tb.columns if c != "classifier_h"]:
                    c = (twins[t].to_numpy().astype(int) == y).astype(int)
                    sc = tb[t].to_numpy(dtype=np.float64)
                    r1, r2 = AR.auc_sk(c, sc, w), AR.auc_rank(c, sc, w)
                    rows.append({"team_version": r, "shuffle_seed": s, "router_table": CH.setup_name(r, s), "twin": t,
                                 "ranking_quality_route_1": r1, "ranking_quality_route_2": r2, "route_difference": abs(r1 - r2),
                                 "n_alerts": len(c), "share_correct_weighted": float((w * c).sum() / w.sum())})
        return pd.DataFrame(rows)

    per = ranking(preds)
    k0 = CH.setup_name(1, 1); cols = [c for c in preds[k0].columns if c != "classifier_h"]
    alt = {k: v.copy() for k, v in preds.items()}
    alt[k0] = alt[k0].rename(columns={cols[0]: cols[1], cols[1]: cols[0]})
    per_alt = ranking(alt)
    changed = bool((per_alt.loc[per_alt.router_table == k0, "ranking_quality_route_1"].to_numpy()
                    != per.loc[per.router_table == k0, "ranking_quality_route_1"].to_numpy()).any())
    A.check(len(per) == 250 and not route_failures(per),
            "month 7: the two routes agree within 1e-9 for 250 models", largest=float(per["route_difference"].max()))
    A.check(near_tolerance_controls(per), "month 7: near-tolerance controls of the route rule (2e-9 fails, 5e-10 passes)")
    A.check(changed, "month 7: negative control (two reviewer columns swapped) changes the result")
    by_version = per.groupby("team_version", as_index=False)["ranking_quality_route_1"].mean().rename(
        columns={"ranking_quality_route_1": "average_over_the_50_models_of_the_version"})
    files = {}
    for df, name in ((per6, "p3_ranking_month6_per_model.csv"), (per, "p3_ranking_month7_per_model.csv"),
                     (by_version, "p3_ranking_month7_by_version.csv")):
        p = os.path.join(a.out, name)
        df.to_csv(p, index=False, float_format="%.17g")
        files[name] = C.sha256(p)
    C.write_record(a, {"step": a.step, "auc_routes_self_test": self_out, "outputs_sha256": files})


if __name__ == "__main__":
    main()
