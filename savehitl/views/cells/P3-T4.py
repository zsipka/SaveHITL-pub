# Section 4.5 (round 2): as P2-T4, for analyst-aware deferral, in two figures one below the other (round-2 [analyst-39]):
# against full automation, then against naive review; each with the caption line on capacity 0 (C3). The readings are
# one markdown cell of the notebook, under the second figure (C2). The table P3-T4.df1 is shown by the item
# "P3-T4-tables" (long notebook, appendix A.5). Both parts write the same table file, which keeps the texts.
T43 = boundary_table(BND3, D3, ["vs_policy_1", "vs_policy_2"])
L.save(T43, "P3-T4_capacity_boundaries.csv")
if PART != "tables":
    verdict_colour_grid(T43, BND3, ["vs_policy_1"], "Analyst-aware deferral against full automation: the descriptive verdict at each capacity",
                        "P3-T4_verdict_grid_against_full_automation.png", caption=GRID_CAPACITY0)
    verdict_colour_grid(T43, BND3, ["vs_policy_2"], "Analyst-aware deferral against naive review: the descriptive verdict at each capacity",
                        "P3-T4_verdict_grid_against_naive_review.png", caption=GRID_CAPACITY0)
if PART != "graph":
    v = T43[T43["version"] == L.MEAN5].copy()
    for c in [c for c in L.CAP_ORDER if c in v.columns]:
        v[c] = L.symbols(v[c])
    V.show(v, 'P3-T4.df1', hide=[], rename={'point boundary': 'where the difference crosses zero (capacity)', 'interval summary': 'summary (can be misread; see the caveat in the technical section)'}, index_names={}, column_names={}, values={'comparison': {'against policy 1': 'against full automation', 'against policy 2': 'against naive review'}}, index={}, cells=[], empty_cells=True)
    V.say('boundary.rows', 'The rows of each single version are in the accompanying table file ({n} rows in all).', {}, n=len(T43))
