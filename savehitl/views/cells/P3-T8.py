# Section 3.3: table P3-T8, the difference on the alerts naive review confirms without review (teams B and C at 0.75).
t8 = L.csv("p3_t8", dtype={"version": str, "seed": str})
cols = ["difference_expected_loss_0.057_on_those_alerts", "difference_accepted_frauds_on_those_alerts"]
per_seed = t8[t8["seed"].isin(["1", "2", "3", "4", "5"])]
assert len(per_seed) == 50 and per_seed["n_alerts_policy_2_confirms_unreviewed"].nunique() == 1
means = t8[~t8["seed"].isin(["1", "2", "3", "4", "5"])].set_index(["team", "version"])[cols]     # the export's own means (step policy3)
rng = per_seed.groupby(["team", "version"])[cols].agg(["min", "max"])
rng.columns = [f"{c} seed {k}" for c, k in rng.columns]
out = means.join(rng, how="left")
out["alerts policy 2 confirms without review"] = int(per_seed["n_alerts_policy_2_confirms_unreviewed"].iloc[0])
out["label"] = L.L_T8
V.show(out, 'P3-T8.df1', hide=['label'], rename={'difference_expected_loss_0.057_on_those_alerts': 'difference in expected loss (0.057) on those alerts', 'difference_accepted_frauds_on_those_alerts': 'difference in frauds accepted on those alerts', 'difference_expected_loss_0.057_on_those_alerts seed min': 'expected loss: lowest of the five random orders', 'difference_expected_loss_0.057_on_those_alerts seed max': 'expected loss: highest of the five random orders', 'difference_accepted_frauds_on_those_alerts seed min': 'frauds accepted: lowest of the five random orders', 'difference_accepted_frauds_on_those_alerts seed max': 'frauds accepted: highest of the five random orders', 'alerts policy 2 confirms without review': 'alerts naive review confirms without review'}, index_names={}, column_names={}, values={}, index={'mean of 5 versions': 'average of the five versions'}, cells=[], empty_cells=True); L.save(out.reset_index(), "P3-T8_point_figures.csv")