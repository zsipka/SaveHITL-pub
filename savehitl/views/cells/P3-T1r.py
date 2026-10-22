# Section 4.1: the router's ranking quality per team version, test month beside the previous month, as formed by the
# summaries step from the ranking step's per-model figures (no third row). The per-model figures are
# written to the table files.
rk7 = L.csv("p3_rank_model"); rk6 = L.csv("p3_rank_month6_model")
L.save(rk7, "P3-T1b_ranking_quality_per_model_month7.csv"); L.save(rk6, "P3-T1b_ranking_quality_per_model_month6.csv")
byv = L.csv("s_ranking", dtype={"team_version": str}).set_index("team_version")
L.save(byv.reset_index(), "P3-T1c_ranking_quality_by_version.csv")
cols = pd.MultiIndex.from_tuples([(m, s) for m in ("test month", "previous month") for s in ("average", "lowest", "highest", "models at or below 0.5")])
src_cols = [f"month {k} {s}" for k in (7, 6) for s in ("average of 50 models", "lowest model", "highest model", "models at or below 0.5")]
view = byv[src_cols].copy()
view.columns = cols
for c in view.columns:
    if c[1] != "models at or below 0.5":
        view[c] = view[c].astype(float).round(4)
V.show(view, 'P3-T1.df2', hide=[], rename={}, index_names={'team_version': 'team version'}, column_names={}, values={}, index={}, cells=[], empty_cells=True)
