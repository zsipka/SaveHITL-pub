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
L.save(out.reset_index(), "P3-T8_point_figures.csv")   # [analyst-03]: the table is no longer shown; its file stays