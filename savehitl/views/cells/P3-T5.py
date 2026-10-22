# Section 8.3: table P3-T5, the full sweep at cost ratio 0.057 (verdict as a symbol in each cell);
# every row of the descriptive export goes to the table file.
T53 = D3.copy(); T53["measure name"] = T53["measure"].map(L.mname); T53["comparison name"] = T53["comparison"].map(lambda c: L.COMPARISON_NAMES.get(c, c))
T53["label"] = L.L_DESC
L.save(T53.drop(columns=["cap"]), "P3-T5_full_sweep.csv")
v = T53[(T53["comparison"].isin(["vs_policy_1", "vs_policy_2"])) & (T53["version"] == L.MEAN5) &
        (T53["measure"].isin(["difference_expected_loss", "difference_accepted_frauds", "difference_age_gap_abs"])) & (T53["lambda"].isna() | L.lam_eq(T53["lambda"], 0.057))].copy()
v["cell"] = [f"{L.fmt(p)} [{L.fmt(lo)}, {L.fmt(hi)}] {L.symbol(vd)}; seeds {L.fmt(a_)} to {L.fmt(b_)}" for p, lo, hi, vd, a_, b_ in
             zip(v["point_estimate"], v["ci_low"], v["ci_high"], v["verdict"], v["seed_min"], v["seed_max"])]
V.show(v.pivot_table(index=["comparison name", "measure name", "team"], columns="capacity_label", values="cell", aggfunc="first")[L.CAP_ORDER], 'P3-T5.df1', hide=[], rename={}, index_names={'comparison name': 'comparison', 'measure name': 'measure'}, column_names={'capacity_label': 'capacity'}, values={}, index={'against policy 1': 'against full automation', 'against policy 2': 'against naive review'}, cells=[], empty_cells=True)