# Section 4.5 (round 2): the colour grid of the descriptive verdict at each capacity ([analyst-07]; round-2 [analyst-39]:
# the graph only), with the caption line on capacity 0 (C3). The reading is a markdown cell of the notebook (C2). The
# table P2-T4.df1 (where each team's difference crosses zero, and the descriptive verdict at each capacity as a symbol;
# * marks a cell that is also a deciding result) is shown by the item "P2-T4-tables" (long notebook, appendix A.5).
# Both parts write the same table file, which keeps the texts.
T4 = boundary_table(BND2, D2, ["vs_policy_1"])
L.save(T4, "P2-T4_capacity_boundaries.csv")
if PART != "tables":
    verdict_colour_grid(T4, BND2, ["vs_policy_1"], "Naive review against full automation: the descriptive verdict at each capacity (average of the five versions)",
                        "P2-T4_verdict_grid.png", caption=GRID_CAPACITY0)
if PART != "graph":
    v = T4[T4["version"] == L.MEAN5].copy()
    for c in [c for c in L.CAP_ORDER if c in v.columns]:
        v[c] = L.symbols(v[c])
    V.show(v, 'P2-T4.df1', hide=[], rename={'point boundary': 'where the difference crosses zero (capacity)', 'interval summary': 'summary (can be misread; see the caveat in the technical section)'}, index_names={}, column_names={}, values={'comparison': {'against policy 1': 'against full automation', 'against policy 2': 'against naive review'}}, index={}, cells=[], empty_cells=True)
    V.say('boundary.rows', 'The rows of each single version are in the accompanying table file ({n} rows in all).', {}, n=len(T4))
