"""Step: what the applications show. Aggregate figures of FiFAR's `Base.csv` and of the alert files, for the notebook's
section "The data and the set-up". Descriptive only: no result, range or verdict reads them.

Every figure is a count, a rate or a correlation over a group of at least 10 applications (MIN_GROUP); a smaller group
is merged with its neighbour towards the middle of the scale, and the merge is written beside the figure. No
application row, no single value of a column, and no minimum or maximum of a column is written.

Reads (each stopped on its listed sha256): `FiFAR/alert_data/Base.csv`, `FiFAR/alert_data/processed_data/alerts.parquet`,
`FiFAR/alert_data/processed_data/BAF_alert_model_score.parquet`, `Code/alert_data/dataset_cfg.yaml`.

The alert-score file has no month column: its `case_id` is the row position after the framework sorts `Base.csv` by
month (`Code/alert_data/preprocess.py:24-28,39-40`), and the same sort is used here. The step stops if the 4,457 alerts
of the test month are not all applications of month 7 with the same label and age in `Base.csv`.

Outputs:
  applications_by_month.csv       per month 0 to 7: applications, frauds, fraud rate (with its 95% Wilson range), alerts
  applications_by_age.csv         per age group (decades as stored): applications, frauds, fraud rate, Wilson range
  applications_by_month_age.csv   per month and age group (under 50; 50 or over): applications, frauds, fraud rate
  applications_spearman.csv       Spearman coefficient of each pair of included columns, with the applications behind it
  applications_columns.csv        every column of `Base.csv`: in the correlation map or left out, and why; the
                                  missing-value code the dataset's datasheet declares
  alert_model_flag_by_age.csv     months 3 to 7: legitimate applicants per age group, how many the Alert Model flagged
  test_month_by_age.csv           month 7: applications and legitimate applicants per age group (50 or over, under 50,
                                  all ages), the denominators of the FPRs over every application
  checks.json                     the counts and the subset check, as computed
"""
import json
import os

import numpy as np
import pandas as pd

from . import _common as C

MIN_GROUP = 10
TEST_MONTH = 7
MONTHS = list(range(8))
PROTECTED_AGE = 50          # Code/alert_data/dataset_cfg.yaml:14-18, "higher", threshold 50
CATEGORICAL = ["payment_type", "employment_status", "housing_status", "source", "device_os"]   # dataset_cfg.yaml:20-25
LABEL = "fraud_bool"
# Missing-value codes declared in the dataset's datasheet (Bank Account Fraud dataset, `documents/datasheet.pdf`,
# question A7): column -> (rule, datasheet page). A column the datasheet does not declare is kept as it is.
# The datasheet's `device_distinct_emails` is the file's `device_distinct_emails_8w`.
MISSING = {
    "prev_address_months_count": ("-1", 2),
    "current_address_months_count": ("-1", 2),
    "intended_balcon_amount": ("negative", 2),
    "bank_months_count": ("-1", 2),
    "session_length_in_minutes": ("-1", 3),
    "device_distinct_emails_8w": ("-1", 3),
}


def wilson(k, n, z=1.959963984540054):
    k = np.asarray(k, dtype=float)
    n = np.asarray(n, dtype=float)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def merge_small(counts, order, label_of):
    """Groups in `order` (a list of keys); `counts[key]` is the denominator. A group with fewer than MIN_GROUP is merged
    with its neighbour towards the middle of the scale, repeatedly. Returns a list of (label, [keys])."""
    groups = [[k] for k in order]
    def n(g):
        return sum(counts.get(k, 0) for k in g)
    changed = True
    while changed and len(groups) > 1:
        changed = False
        for i, g in enumerate(groups):
            if n(g) < MIN_GROUP:
                j = i + 1 if i < len(groups) / 2 else i - 1
                j = min(max(j, 0), len(groups) - 1)
                a, b = sorted((i, j))
                groups[a:b + 1] = [groups[a] + groups[b]]
                changed = True
                break
    out = []
    for i, g in enumerate(groups):
        if len(g) == 1:
            out.append((label_of(g[0]), g))
        elif i == len(groups) - 1:
            out.append((f"{label_of(g[0])} and over", g))
        elif i == 0:
            out.append((f"{label_of(g[-1])} and under", g))
        else:
            out.append((f"{label_of(g[0])} to {label_of(g[-1])}", g))
    return out


def missing_mask(col, values):
    rule = MISSING.get(col, (None,))[0]
    if rule == "-1":
        return values == -1
    if rule == "negative":
        return values < 0
    return np.zeros(len(values), dtype=bool)


def spearman_pairwise(df, cols, A):
    """Spearman coefficient of each pair, over the applications where both columns hold a value (pairwise); ties take
    average ranks. Columns without missing values are ranked once."""
    from scipy.stats import rankdata
    valid = {c: ~missing_mask(c, df[c].to_numpy()) for c in cols}
    full_rank = {c: rankdata(df[c].to_numpy(), method="average") for c in cols if valid[c].all()}
    rows = []
    for i, a in enumerate(cols):
        for b in cols[: i + 1]:
            if a == b:
                rows.append({"row": a, "column": b, "spearman": 1.0, "n_applications": int(valid[a].sum())})
                continue
            m = valid[a] & valid[b]
            n = int(m.sum())
            if n < MIN_GROUP:
                rows.append({"row": a, "column": b, "spearman": np.nan, "n_applications": n})
                continue
            if m.all():
                ra, rb = full_rank[a], full_rank[b]
            else:
                ra = rankdata(df[a].to_numpy()[m], method="average")
                rb = rankdata(df[b].to_numpy()[m], method="average")
            r = float(np.corrcoef(ra, rb)[0, 1])
            rows.append({"row": a, "column": b, "spearman": r, "n_applications": n})
    return pd.DataFrame(rows)


def main():
    a = C.args()
    A = C.Asserts(a)
    L = a.L
    rels = {"base": "FiFAR/alert_data/Base.csv", "alerts": "FiFAR/alert_data/processed_data/alerts.parquet",
            "scores": "FiFAR/alert_data/processed_data/BAF_alert_model_score.parquet", "cfg": "Code/alert_data/dataset_cfg.yaml"}
    for rel in rels.values():
        A.check(C.sha256(os.path.join(L.framework, rel)) == C.input_sha(L, rel), "input at its checksum", file=rel)
    import yaml
    cfg = yaml.safe_load(open(os.path.join(L.framework, rels["cfg"])))
    A.check(sorted(cfg["data_cols"]["categorical"]) == sorted(CATEGORICAL), "categorical columns as the dataset's configuration")
    prot = cfg["data_cols"]["protected"][0]
    A.check(prot["protected_class"] == "higher" and prot["protected_threshold"] == PROTECTED_AGE, "protected group: age 50 or over")

    base = pd.read_csv(os.path.join(L.framework, rels["base"]), dtype={c: "category" for c in CATEGORICAL})
    A.check(len(base) == 1_000_000, "Base.csv holds 1,000,000 applications", n=len(base))
    A.check(base.shape[1] == 32, "Base.csv holds 32 columns", n=base.shape[1])
    A.check(sorted(base["month"].unique().tolist()) == MONTHS, "months 0 to 7")
    for c in MISSING:
        A.check(c in base.columns, "datasheet missing-value column present", column=c)
    # the framework's own ordering (Code/alert_data/preprocess.py:24-28): case_id = row position after the sort by month
    # (the sort is on the month column alone, so sorting that column gives the same order as sorting the frame)
    order = base["month"].sort_values().index.to_numpy()
    month_of = base["month"].to_numpy()[order]
    label_of = base[LABEL].to_numpy()[order]
    age_of = base["customer_age"].to_numpy()[order]
    del order

    alerts = pd.read_parquet(os.path.join(L.framework, rels["alerts"]), columns=["fraud_bool", "customer_age", "month"])
    A.check(alerts.index.name == "case_id" and alerts.index.is_unique and len(alerts) == 30622, "30,622 alerts, unique case_id",
            n=len(alerts))
    ids = alerts.index.to_numpy()
    A.check(bool((ids >= 0).all() and (ids < len(month_of)).all()), "alert case_id within the sorted Base.csv")
    same = (month_of[ids] == alerts["month"].to_numpy()) & (label_of[ids] == alerts["fraud_bool"].to_numpy()) & \
           (age_of[ids] == alerts["customer_age"].to_numpy())
    A.check(bool(same.all()), "every alert is the Base.csv application of the same month, label and age", n_differ=int((~same).sum()))
    t7 = alerts.loc[alerts["month"] == TEST_MONTH]
    A.check(len(t7) == 4457, "4,457 alerts in month 7", n=len(t7))
    A.check(int(t7["fraud_bool"].sum()) == 711 and int((t7["fraud_bool"] == 0).sum()) == 3746, "711 frauds and 3,746 legitimate in month 7")
    A.check(bool((month_of[t7.index.to_numpy()] == TEST_MONTH).all()), "the month-7 alerts are a subset of the month-7 applications")

    # D1: per month
    g = base.groupby("month")[LABEL].agg(["size", "sum"]).reindex(MONTHS)
    n_alerts = alerts.groupby("month").size().reindex(MONTHS).fillna(0).astype(int)
    A.check(bool((g["size"] >= MIN_GROUP).all()), "every month holds at least 10 applications")
    lo, hi = wilson(g["sum"], g["size"])
    by_month = pd.DataFrame({"month": MONTHS, "n_applications": g["size"].astype(int).to_numpy(), "n_frauds": g["sum"].astype(int).to_numpy(),
                             "fraud_rate": (g["sum"] / g["size"]).to_numpy(), "fraud_rate_wilson_low": lo, "fraud_rate_wilson_high": hi,
                             "n_alerts": n_alerts.to_numpy()})

    # D2: per age group (decades as stored)
    ages = sorted(base["customer_age"].unique().tolist())
    A.check(all(int(x) % 10 == 0 for x in ages), "customer_age stored in decades")
    cnt = base.groupby("customer_age").size().to_dict()
    frauds = base.groupby("customer_age")[LABEL].sum().to_dict()
    rows = []
    for lab, keys in merge_small(cnt, ages, lambda k: str(int(k))):
        n = sum(cnt[k] for k in keys)
        k = sum(frauds[k] for k in keys)
        rows.append({"age_group": lab, "ages_in_group": " ".join(str(int(x)) for x in keys), "age_50_plus": int(min(keys) >= PROTECTED_AGE),
                     "n_applications": int(n), "n_frauds": int(k), "fraud_rate": k / n})
    by_age = pd.DataFrame(rows)
    A.check(bool((by_age["n_applications"] >= MIN_GROUP).all()), "every age group holds at least 10 applications")
    A.check(bool(((by_age["age_50_plus"] == 1) | by_age["ages_in_group"].map(lambda s: max(int(x) for x in s.split()) < PROTECTED_AGE)).all()),
            "no age group spans 50")
    by_age["fraud_rate_wilson_low"], by_age["fraud_rate_wilson_high"] = wilson(by_age["n_frauds"], by_age["n_applications"])
    overall_rate = float(base[LABEL].mean())

    # D3: per month and age group
    old = base["customer_age"] >= PROTECTED_AGE
    rows = []
    for m in MONTHS:
        for grp, mask in (("under 50", ~old), ("50 or over", old)):
            sel = (base["month"] == m) & mask
            n = int(sel.sum())
            k = int(base.loc[sel, LABEL].sum())
            rows.append({"month": m, "age_group": grp, "n_applications": n, "n_frauds": k,
                         "fraud_rate": k / n if n >= MIN_GROUP else np.nan, "shown": n >= MIN_GROUP})
    by_month_age = pd.DataFrame(rows)

    # D4: Spearman, pairwise over the values the datasheet does not declare missing
    numeric = [c for c in base.columns if c not in CATEGORICAL and c != "month"]
    order = [LABEL, "customer_age"] + [c for c in numeric if c not in (LABEL, "customer_age")]
    col_rows, cols = [], []
    for c in base.columns:
        code, page = MISSING.get(c, ("", ""))
        if c in CATEGORICAL:
            col_rows.append({"column": c, "in_map": False, "reason": "categorical", "missing_code": code, "datasheet_page": page})
            continue
        if c == "month":
            col_rows.append({"column": c, "in_map": False, "reason": "month (left out by design)", "missing_code": code, "datasheet_page": page})
            continue
        v = base[c].to_numpy()
        ok = ~missing_mask(c, v)
        vals = np.unique(v[ok])
        if len(vals) < 2:
            col_rows.append({"column": c, "in_map": False, "reason": "one value only", "missing_code": code, "datasheet_page": page})
            continue
        if len(vals) == 2:
            rare = int(min((v[ok] == vals[0]).sum(), (v[ok] == vals[1]).sum()))
            if rare < MIN_GROUP:
                col_rows.append({"column": c, "in_map": False, "reason": "binary, rarer value in fewer than 10 applications",
                                 "missing_code": code, "datasheet_page": page})
                continue
        col_rows.append({"column": c, "in_map": True, "reason": "", "missing_code": code, "datasheet_page": page,
                         "n_missing": int((~ok).sum())})
        cols.append(c)
    cols = [c for c in order if c in cols]
    columns = pd.DataFrame(col_rows)
    columns["n_missing"] = columns.get("n_missing", pd.Series(dtype=float))
    spear = spearman_pairwise(base[cols], cols, A)
    A.check(bool((spear["n_applications"] >= MIN_GROUP).all()), "every coefficient over at least 10 applications")

    # D5: the Alert Model's share of legitimate applicants flagged, by age group, months 3 to 7 (alert-score file)
    sc = pd.read_parquet(os.path.join(L.framework, rels["scores"]), columns=["fraud_bool", "customer_age", "case_id"])
    if sc.index.name != "case_id":
        sc = sc.set_index("case_id")
    A.check(sc.index.is_unique and len(sc) == 602961, "alert-score file: 602,961 applications, unique case_id", n=len(sc))
    sid = sc.index.to_numpy()
    A.check(bool((label_of[sid] == sc["fraud_bool"].to_numpy()).all() and (age_of[sid] == sc["customer_age"].to_numpy()).all()),
            "alert-score file rows equal the sorted Base.csv rows (label, age)")
    sc_month = month_of[sid]
    A.check(sorted(np.unique(sc_month).tolist()) == [3, 4, 5, 6, 7], "alert-score file covers months 3 to 7")
    A.check(bool(np.isin(ids, sid).all()), "every alert is in the alert-score file")
    leg = sc["fraud_bool"].to_numpy() == 0
    flagged = np.isin(sid, ids)
    sages = sc["customer_age"].to_numpy()
    cntl = {k: int(((sages == k) & leg).sum()) for k in ages}
    rows = []
    for lab, keys in merge_small(cntl, ages, lambda k: str(int(k))):
        m = np.isin(sages, keys) & leg
        n, f = int(m.sum()), int((m & flagged).sum())
        rows.append({"age_group": lab, "ages_in_group": " ".join(str(int(x)) for x in keys), "age_50_plus": int(min(keys) >= PROTECTED_AGE),
                     "n_legitimate": n, "n_flagged": f, "share_flagged": f / n})
    flag = pd.DataFrame(rows)
    A.check(bool((flag["n_legitimate"] >= MIN_GROUP).all()), "every age group of D5 holds at least 10 legitimate applicants")
    flag["share_flagged_wilson_low"], flag["share_flagged_wilson_high"] = wilson(flag["n_flagged"], flag["n_legitimate"])
    A.check(int(flag["n_flagged"].sum()) == int((alerts["fraud_bool"] == 0).sum()), "D5 flagged legitimate = legitimate alerts")

    # denominators of the FPRs over every application of the test month
    b7 = base.loc[base["month"] == TEST_MONTH]
    rows = []
    for grp, mask in (("50 or over", b7["customer_age"] >= PROTECTED_AGE), ("under 50", b7["customer_age"] < PROTECTED_AGE),
                      ("all ages", b7["customer_age"] >= 0)):
        rows.append({"age_group": grp, "n_applications": int(mask.sum()), "n_legitimate": int((mask & (b7[LABEL] == 0)).sum()),
                     "n_alerts": int(((t7["customer_age"] >= PROTECTED_AGE) if grp == "50 or over" else
                                      (t7["customer_age"] < PROTECTED_AGE) if grp == "under 50" else t7["customer_age"] >= 0).sum()),
                     "n_legitimate_alerts": int((((t7["customer_age"] >= PROTECTED_AGE) if grp == "50 or over" else
                                                  (t7["customer_age"] < PROTECTED_AGE) if grp == "under 50" else t7["customer_age"] >= 0)
                                                 & (t7["fraud_bool"] == 0)).sum())})
    t7age = pd.DataFrame(rows)
    A.check(bool((t7age["n_legitimate"] >= MIN_GROUP).all()), "every test-month group holds at least 10 legitimate applicants")

    checks = {"n_applications": int(len(base)), "months": MONTHS, "n_alerts": int(len(alerts)),
              "n_alerts_by_month": {int(k): int(v) for k, v in n_alerts.items()}, "n_alerts_month_7": int(len(t7)),
              "n_frauds_alerts_month_7": int(t7["fraud_bool"].sum()), "n_legitimate_alerts_month_7": int((t7["fraud_bool"] == 0).sum()),
              "month_7_alerts_subset_of_month_7": True, "overall_fraud_rate": overall_rate, "min_group": MIN_GROUP,
              "missing_value_codes": {c: {"code": r, "datasheet_page": p} for c, (r, p) in MISSING.items()},
              "columns_in_map": cols}
    outs = {"applications_by_month.csv": by_month, "applications_by_age.csv": by_age, "applications_by_month_age.csv": by_month_age,
            "applications_spearman.csv": spear, "applications_columns.csv": columns, "alert_model_flag_by_age.csv": flag,
            "test_month_by_age.csv": t7age}
    for n, d in outs.items():
        d.to_csv(os.path.join(a.out, n), index=False, float_format="%.17g")
    with open(os.path.join(a.out, "checks.json"), "w") as f:
        json.dump(checks, f, indent=1)
    names = list(outs) + ["checks.json"]
    C.write_record(a, {"step": a.step, "outputs_sha256": {n: C.sha256(os.path.join(a.out, n)) for n in names}})


if __name__ == "__main__":
    main()
