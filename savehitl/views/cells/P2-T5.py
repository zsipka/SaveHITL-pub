# Section 8.3: table P2-T5, the full sweep at cost ratio 0.057 (verdict as a symbol in each cell);
# every row of the descriptive export goes to the table file.
T5 = D2.copy(); T5["measure name"] = T5["measure"].map(L.mname); T5["comparison name"] = T5["comparison"].map(lambda c: L.COMPARISON_NAMES.get(c, c))
T5["label"] = L.L_DESC
L.save(T5.drop(columns=["cap"]), "P2-T5_full_sweep.csv")
v = T5[(T5["comparison"] == "vs_policy_1") & (T5["version"] == L.MEAN5) & (T5["measure"].isin(["difference_expected_loss", "difference_accepted_frauds", "difference_age_gap_abs"])) &
       (T5["lambda"].isna() | L.lam_eq(T5["lambda"], 0.057))].copy()
v["cell"] = [f"{L.fmt(p)} [{L.fmt(lo)}, {L.fmt(hi)}] {L.symbol(vd)}; seeds {L.fmt(a_)} to {L.fmt(b_)}" for p, lo, hi, vd, a_, b_ in
             zip(v["point_estimate"], v["ci_low"], v["ci_high"], v["verdict"], v["seed_min"], v["seed_max"])]
piv = v.pivot_table(index=["measure name", "team"], columns="capacity_label", values="cell", aggfunc="first")[L.CAP_ORDER]
V.show(piv, 'P2-T5.df1', hide=[], rename={}, index_names={'measure name': 'measure'}, column_names={'capacity_label': 'capacity'}, values={}, index={}, cells=[], empty_cells=True)
V.md("fpr.reminder", "*" + L.FPR_REMINDER + "*", {})   # C14