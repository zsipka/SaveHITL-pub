"""Step: policy 1's bootstrap intervals (95% percentile intervals, descriptive).

From policy 1's per-case file (ascending case_id): the first 1,000 rows of the shared index matrix, drawn by the exact
call numpy.random.RandomState(2026).randint(0, 4457, size=(1000, 4457)) (64-bit integers); for each resample the
measures of policy 1 and of confirming every alert at the four cost ratios; 95% percentile intervals with NumPy's
default linear interpolation; a resample with no legitimate alert in one age group is dropped for the age gap only and
counted. The checksum of these 1,000 index rows is recorded: the policy 2 bootstrap requires its own first 1,000 rows
to give the same checksum.

Output: p1_t2_measures_by_lambda_with_intervals.csv.
"""
import csv
import hashlib
import os

import numpy as np
import pandas as pd

from . import _chain as K
from . import _common as C

LAMBDAS = [0.035, 0.0537, 0.057, 0.171]
ANCHOR = 0.057
N = 4457
B = 1000
SEED = 2026
CALL = "numpy.random.RandomState(2026).randint(0, 4457, size=(1000, 4457))"
ORDER = ["expected_loss_total", "expected_loss_per_case", "regulatory_exposure_accepted_frauds_count",
         "regulatory_exposure_miss_rate", "regulatory_exposure_share_stopped", "fairness_exposure_age_gap",
         "false_positive_rate_50_plus", "false_positive_rate_under_50", "false_rejections_count"]


def main():
    a = C.args([("--policy1", {"required": True})])
    A = C.Asserts(a)
    pc = pd.read_csv(K.step_output(A, a.policy1, "p1_per_case.csv"), float_precision="round_trip")
    A.check(len(pc) == N and pc["case_id"].is_unique and pc["case_id"].is_monotonic_increasing,
            "policy 1 per-case file: 4,457 alerts in ascending case_id")
    dec = pc["p1_reject"].to_numpy().astype(np.int64)
    lab = pc["label_fraud"].to_numpy().astype(np.int64)
    old = pc["age_50_plus"].to_numpy().astype(bool)
    A.check(np.array_equal(old, pc["customer_age"].to_numpy() >= 50), "age group equal to age 50 or over")
    for lam in LAMBDAS:
        c = np.where((dec == 1) & (lab == 0), lam, 0.0) + np.where((dec == 0) & (lab == 1), 1.0, 0.0)
        A.check(np.array_equal(c, pc[f"p1_cost_lambda_{lam}"].to_numpy())
                and np.array_equal(np.where(lab == 0, lam, 0.0), pc[f"confirm_every_alert_cost_lambda_{lam}"].to_numpy()),
                "per-case costs recomputed from decision and label equal the file's", lam=lam)

    idx = np.random.RandomState(SEED).randint(0, N, size=(B, N))
    A.check(idx.dtype == np.int64 and idx.shape == (B, N), "index rows: int64, 1,000 x 4,457")
    idx_sha = hashlib.sha256(np.ascontiguousarray(idx).tobytes()).hexdigest()

    def counts(d):
        leg = lab == 0
        fraud = lab == 1
        ind = {"fp": ((d == 1) & leg), "fn": ((d == 0) & fraud), "fraud": fraud, "fp_old": ((d == 1) & leg & old),
               "leg_old": (leg & old), "fp_yng": ((d == 1) & leg & ~old), "leg_yng": (leg & ~old)}
        return {k: v.astype(np.int64)[idx].sum(axis=1) for k, v in ind.items()}

    def point_and_boot(d):
        c = counts(d)
        defined = (c["leg_old"] > 0) & (c["leg_yng"] > 0)
        with np.errstate(invalid="ignore", divide="ignore"):
            fpr_old = c["fp_old"] / c["leg_old"]
            fpr_yng = c["fp_yng"] / c["leg_yng"]
            miss = c["fn"] / c["fraud"]
        miss_defined = c["fraud"] > 0
        out = {}
        for lam in LAMBDAS:
            tot = lam * c["fp"] + c["fn"]
            out[(lam, "expected_loss_total")] = (tot, np.ones(B, bool))
            out[(lam, "expected_loss_per_case")] = (tot / N, np.ones(B, bool))
            out[(lam, "regulatory_exposure_accepted_frauds_count")] = (c["fn"].astype(float), np.ones(B, bool))
            out[(lam, "regulatory_exposure_miss_rate")] = (miss, miss_defined)
            out[(lam, "regulatory_exposure_share_stopped")] = (1 - miss, miss_defined)
            out[(lam, "fairness_exposure_age_gap")] = (fpr_old - fpr_yng, defined)
            out[(lam, "false_positive_rate_50_plus")] = (fpr_old, defined)
            out[(lam, "false_positive_rate_under_50")] = (fpr_yng, defined)
            out[(lam, "false_rejections_count")] = (c["fp"].astype(float), np.ones(B, bool))
        return out

    def point(d, lam, m):
        leg, fraud = lab == 0, lab == 1
        fp = int(((d == 1) & leg).sum()); fn = int(((d == 0) & fraud).sum())
        fo = ((d == 1) & leg & old).sum() / (leg & old).sum()
        fy = ((d == 1) & leg & ~old).sum() / (leg & ~old).sum()
        miss = fn / fraud.sum()
        return {"expected_loss_total": lam * fp + fn, "expected_loss_per_case": (lam * fp + fn) / N,
                "regulatory_exposure_accepted_frauds_count": fn, "regulatory_exposure_miss_rate": miss,
                "regulatory_exposure_share_stopped": 1 - miss, "fairness_exposure_age_gap": fo - fy,
                "false_positive_rate_50_plus": fo, "false_positive_rate_under_50": fy, "false_rejections_count": fp}[m]

    rows, dropped = [], {}
    for pol, d in (("policy_1", dec), ("confirm_every_alert", np.ones_like(dec))):
        res = point_and_boot(d)
        for lam in LAMBDAS:
            for m in ORDER:
                vals, ok = res[(lam, m)]
                lo, hi = np.percentile(vals[ok], [2.5, 97.5])
                n_drop = int(B - ok.sum())
                dropped[(pol, m)] = n_drop
                rows.append({"policy": pol, "lambda": lam, "is_anchor": lam == ANCHOR, "measure": m,
                             "value": float(point(d, lam, m)), "ci95_low": float(lo), "ci95_high": float(hi),
                             "interval_status": "95% case bootstrap, descriptive", "B": B, "resamples_used": int(ok.sum()),
                             "resamples_dropped": n_drop, "bootstrap_seed": SEED, "percentile_method": "linear",
                             "run_id": "this run"})
    pt = pd.read_csv(K.step_output(A, a.policy1, "p1_t2_measures_by_lambda.csv"), float_precision="round_trip")
    worst = 0.0
    for r in rows:
        q = pt[(pt.policy == r["policy"]) & (pt["lambda"] == r["lambda"]) & (pt.measure == r["measure"])]
        A.check(len(q) == 1, "one point figure per policy, cost ratio and measure", policy=r["policy"], measure=r["measure"])
        worst = max(worst, abs(float(q["value"].iloc[0]) - r["value"]))
    A.check(worst <= 1e-12, "point figures equal to policy 1's within 1e-12", largest=worst)
    name = "p1_t2_measures_by_lambda_with_intervals.csv"
    with open(os.path.join(a.out, name), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    C.write_record(a, {"step": a.step, "bootstrap": {"call": CALL, "B": B, "seed": SEED, "dtype": str(idx.dtype),
                                                     "index_rows_sha256_int64_bytes": idx_sha,
                                                     "first_row_first_5": idx[0, :5].tolist(),
                                                     "age_gap_resamples_dropped": {k[0]: v for k, v in dropped.items()
                                                                                   if k[1] == "fairness_exposure_age_gap"}},
                       "outputs_sha256": {name: C.sha256(os.path.join(a.out, name))}})


if __name__ == "__main__":
    main()
