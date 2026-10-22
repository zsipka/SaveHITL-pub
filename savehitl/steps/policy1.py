"""Step: policy 1, full automation. The framework's shipped Classifier h decides each of the 4,457 alerts of the test
month (file month 7): score h = sigmoid(raw score + init_score), as the framework's `Code/deferral/run_alert.py`;
rejected when h >= 0.5. Point measures at the four cost ratios, for policy 1 and for confirming every alert.

Outputs: p1_per_case.csv (per alert: label, age, h, decision, costs; read by the later steps),
         p1_t2_measures_by_lambda.csv.
"""
import csv
import os
import pickle

import numpy as np
import pandas as pd
import yaml

from . import _common as C

LAMBDAS = [0.035, 0.0537, 0.057, 0.171]
ANCHOR = 0.057
TEST_MONTH = 7
N_EXPECTED = 4457


def sig(x):
    return 1 / (1 + np.exp(-x))


def cat_checker(data, features, cat_dict):          # Code/classifier_h/training.py:13-18
    new_data = data.copy()
    for feature in features:
        if new_data[feature].dtype.categories.to_list() != cat_dict[feature]:
            new_data[feature] = pd.Categorical(new_data[feature].values, categories=cat_dict[feature])
    return new_data


def measures(dec, lab, old_mask, lam):
    leg = lab == 0
    fraud = lab == 1
    fp = int(((dec == 1) & leg).sum())
    fn = int(((dec == 0) & fraud).sum())
    n = len(lab)
    total = lam * fp + fn
    fpr_old = ((dec == 1) & leg & old_mask).sum() / (leg & old_mask).sum()
    fpr_yng = ((dec == 1) & leg & ~old_mask).sum() / (leg & ~old_mask).sum()
    miss = fn / fraud.sum()
    return {"expected_loss_total": float(total), "expected_loss_per_case": float(total / n),
            "regulatory_exposure_accepted_frauds_count": fn, "regulatory_exposure_miss_rate": float(miss),
            "regulatory_exposure_share_stopped": float(1 - miss), "fairness_exposure_age_gap": float(fpr_old - fpr_yng),
            "false_positive_rate_50_plus": float(fpr_old), "false_positive_rate_under_50": float(fpr_yng),
            "false_rejections_count": fp}


def main():
    a = C.args()
    A = C.Asserts(a)
    L = a.L
    rels = {"alerts": "FiFAR/alert_data/processed_data/alerts.parquet",
            "clf": "l2d_benchmarking/classifier_h/selected_model/best_model.pickle",
            "props": "l2d_benchmarking/classifier_h/selected_model/model_properties.yaml",
            "cfg": "Code/alert_data/dataset_cfg.yaml"}
    for rel in rels.values():
        A.check(C.sha256(os.path.join(L.framework, rel)) == C.input_sha(L, rel), "input at its checksum", file=rel)
    data_cfg = yaml.safe_load(open(os.path.join(L.framework, rels["cfg"])))
    props = yaml.safe_load(open(os.path.join(L.framework, rels["props"])))
    with open(os.path.join(L.framework, rels["clf"]), "rb") as f:
        model = pickle.load(f)
    A.check(props["threshold"] == 0.5, "classifier threshold 0.5")
    raw = pd.read_parquet(os.path.join(L.framework, rels["alerts"]))
    A.check(raw.index.name == "case_id" and raw.index.is_unique, "alerts indexed by unique case_id")
    test = raw.loc[raw["month"] == TEST_MONTH].sort_index()
    A.check(len(test) == N_EXPECTED, "4,457 alerts in the test month", n=len(test))
    s_b = sig(model.predict(test.drop(columns=["fraud_bool", "model_score", "month"]), raw_score=True) + props["init_score"])
    test_a = cat_checker(test, data_cfg["data_cols"]["categorical"], data_cfg["categorical_dict"])
    s_a = sig(model.predict(test_a.drop(columns=["fraud_bool", "model_score", "month"]), raw_score=True) + props["init_score"])
    A.check(bool(np.array_equal(s_a, s_b)), "the two scoring paths give the same scores")
    score = s_b
    reject = (score >= props["threshold"]).astype(int)
    y = test["fraud_bool"].to_numpy().astype(int)
    old = test["customer_age"].to_numpy() >= 50
    case_id = test.index.to_numpy()
    rows = []
    for pol, dec in (("policy_1", reject), ("confirm_every_alert", np.ones_like(reject))):
        for lam in LAMBDAS:
            for m, v in measures(dec, y, old, lam).items():
                rows.append({"policy": pol, "lambda": lam, "is_anchor": lam == ANCHOR, "measure": m, "value": v,
                             "ci95_low": "", "ci95_high": "", "interval_status": "not computed in this step",
                             "run_id": "this run"})
    per_case = pd.DataFrame({"case_id": case_id, "month": TEST_MONTH, "label_fraud": y,
                             "customer_age": test["customer_age"].to_numpy(), "age_50_plus": old.astype(int),
                             "classifier_score": score, "p1_reject": reject})
    for lam in LAMBDAS:
        per_case[f"p1_cost_lambda_{lam}"] = np.where((reject == 1) & (y == 0), lam, 0.0) + np.where((reject == 0) & (y == 1), 1.0, 0.0)
    for lam in LAMBDAS:
        per_case[f"confirm_every_alert_cost_lambda_{lam}"] = np.where(y == 0, lam, 0.0)
    for lam in LAMBDAS:
        tot = [r["value"] for r in rows if r["policy"] == "policy_1" and r["lambda"] == lam and r["measure"] == "expected_loss_total"][0]
        A.check(abs(per_case[f"p1_cost_lambda_{lam}"].sum() - tot) < 1e-9, "per-case costs sum to the total", lam=lam)
    per_case.to_csv(os.path.join(a.out, "p1_per_case.csv"), index=False, float_format="%.17g")
    with open(os.path.join(a.out, "p1_t2_measures_by_lambda.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    C.write_record(a, {"step": a.step, "init_score": props["init_score"],
                       "outputs_sha256": {n: C.sha256(os.path.join(a.out, n)) for n in ("p1_per_case.csv", "p1_t2_measures_by_lambda.csv")}})


if __name__ == "__main__":
    main()
