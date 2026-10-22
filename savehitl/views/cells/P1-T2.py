# Section 6.1: table P1-T2, full automation and "confirm every alert" at each cost ratio, with 95% ranges.
keep = ["expected_loss_total", "regulatory_exposure_accepted_frauds_count", "regulatory_exposure_miss_rate", "regulatory_exposure_share_stopped",
        "fairness_exposure_age_gap", "false_positive_rate_50_plus", "false_positive_rate_under_50", "false_rejections_count"]
t = p1[p1["measure"].isin(keep)].copy()
t["measure"] = t["measure"].map(L.mname)
t["policy"] = t["policy"].map({"policy_1": "policy 1", "confirm_every_alert": "confirm every alert (reference)"})
t["value (95% interval)"] = [f"{L.fmt(v)} ({L.fmt(lo)} to {L.fmt(hi)})" for v, lo, hi in zip(t["value"], t["ci95_low"], t["ci95_high"])]
t["label"] = L.L_P1
piv = t.pivot_table(index=["measure", "policy"], columns="lambda", values="value (95% interval)", aggfunc="first")
V.show(piv, 'P1-T2.df1', hide=[], rename={}, index_names={}, column_names={'lambda': 'cost ratio'}, values={}, index={'policy 1': 'full automation'}, cells=[], empty_cells=True)
L.save(t[["policy", "lambda", "is_anchor", "measure", "value", "ci95_low", "ci95_high", "B", "resamples_used", "bootstrap_seed", "label", "run_id"]], "P1-T2_baseline_by_cost_ratio.csv")
share_row = t[(t["measure"] == L.mname("regulatory_exposure_miss_rate")) & (t["policy"] == "policy 1")].iloc[0]
V.md('P1-T2.share-sentence', 'Full automation: {let_through:.1f}% of the frauds among the flagged applications were let through, that is, {stopped:.1f}% were stopped. The decisions do not change with the cost ratio; only expected loss does.', {}, let_through=100*share_row['value'], stopped=100*(1-share_row['value']))