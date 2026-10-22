"""Step: the router's predictions on the 4,457 alerts of the test month (file month 7).

The classifier's score h is computed as in policy 1 and must equal policy 1's per-case score bit for bit; its
confidence max(h, 1 - h) as the framework's `Code/expert_models/run_ova.py:81`. The router's input as
`run_ova.py:66-68` (cat_checker, then drop month and fraud_bool; the alert score stays a feature), in the column order
of each model. For each of the 25 set-ups shuffle_<s>#drawn_<r>: one table, index the case_ids (ascending), one column
per regenerated reviewer of team r (predict_proba[:, 1] of its model), then classifier_h; as the framework's OvA scores
file (run_ova.py:72-87): a dict of 25 tables, pickled.

Output: p3_router_month7_predictions.pkl.
"""
import json
import os
import pickle

import numpy as np
import pandas as pd
import yaml

from . import _common as C

TEST_MONTH = 7
N = 4457


def sig(x):
    return 1 / (1 + np.exp(-x))


def cat_checker(data, features, cat_dict):          # Code/expert_models/run_ova.py:9-15
    new_data = data.copy()
    for feature in features:
        if new_data[feature].dtype.categories.to_list() != cat_dict[feature]:
            new_data[feature] = pd.Categorical(new_data[feature].values, categories=cat_dict[feature])
    return new_data


def main():
    a = C.args([("--policy1", {"required": True}), ("--router", {"required": True})])
    A = C.Asserts(a)
    L = a.L
    rels = {"alerts": "FiFAR/alert_data/processed_data/alerts.parquet", "cfg": "Code/alert_data/dataset_cfg.yaml",
            "clf": "l2d_benchmarking/classifier_h/selected_model/best_model.pickle",
            "props": "l2d_benchmarking/classifier_h/selected_model/model_properties.yaml"}
    for rel in rels.values():
        A.check(C.sha256(os.path.join(L.framework, rel)) == C.input_sha(L, rel), "input at its checksum", file=rel)
    cfg = yaml.safe_load(open(os.path.join(L.framework, rels["cfg"])))
    props = yaml.safe_load(open(os.path.join(L.framework, rels["props"])))
    with open(os.path.join(L.framework, rels["clf"]), "rb") as f:
        clf = pickle.load(f)
    models = pd.read_csv(os.path.join(a.router, "router_models.csv"), dtype=str)
    raw = pd.read_parquet(os.path.join(L.framework, rels["alerts"]))
    test = raw.loc[raw["month"] == TEST_MONTH].sort_index()
    A.check(len(test) == N, "4,457 alerts in the test month")
    case_id = test.index.to_numpy()
    h = sig(clf.predict(test.drop(columns=["fraud_bool", "model_score", "month"]), raw_score=True) + props["init_score"])
    p1 = pd.read_csv(os.path.join(a.policy1, "p1_per_case.csv"), float_precision="round_trip").sort_values("case_id")
    A.check(np.array_equal(p1["case_id"].to_numpy(), case_id) and np.array_equal(h, p1["classifier_score"].to_numpy()),
            "h equal to policy 1's score, bit for bit")
    conf = np.maximum(h, 1 - h)
    X = cat_checker(test, cfg["data_cols"]["categorical"], cfg["categorical_dict"]).drop(columns=["month", "fraud_bool"])
    preds, info = {}, {}
    for r in range(1, 6):
        for s in range(1, 6):
            setup = f"shuffle_{s}#drawn_{r}"
            m = models.loc[models["setup"] == setup]
            twins = sorted(m["twin"], key=lambda t: int(t.split("#")[1]))
            A.check(len(twins) == 10, "10 models per set-up", setup=setup)
            tab = pd.DataFrame(index=pd.Index(case_id, name="case_id"))
            for t in twins:
                mp = os.path.join(a.router, "models", setup, t, "best_model.pickle")
                A.check(C.sha256(mp) == m.loc[m["twin"] == t, "best_model_sha256"].iloc[0], "router model as written by step router",
                        setup=setup, twin=t)
                with open(mp, "rb") as fh:
                    model = pickle.load(fh)
                A.check(list(X.columns) == model.booster_.feature_name(), "feature order equal to the model's", setup=setup, twin=t)
                tab[t] = model.predict_proba(X)[:, 1].astype(np.float64)
            tab["classifier_h"] = conf
            preds[setup] = tab
            info[setup] = list(tab.columns)
    path = os.path.join(a.out, "p3_router_month7_predictions.pkl")
    with open(path, "wb") as f:
        pickle.dump(preds, f, protocol=4)
    C.write_record(a, {"step": a.step, "tables": info, "outputs_sha256": {"p3_router_month7_predictions.pkl": C.sha256(path)}})


if __name__ == "__main__":
    main()
