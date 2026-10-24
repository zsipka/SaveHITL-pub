# Section 6.5: as P2-T4, for analyst-aware deferral, against full automation and against naive review ([analyst-07],
# [analyst-15], [analyst-42]); then table P3-T4.df1. The file keeps the texts.
T43 = boundary_table(BND3, D3, ["vs_policy_1", "vs_policy_2"])
L.save(T43, "P3-T4_capacity_boundaries.csv")
verdict_colour_grid(T43, BND3, ["vs_policy_1", "vs_policy_2"], "Analyst-aware deferral against full automation and against naive review: the descriptive verdict at each capacity (average of the five versions)",
                    "P3-T4_verdict_grid.png")
_v3 = T43[T43["version"] == L.MEAN5]
V.md("P3-T4.reading", "(1) For each team and measure, the capacities at which the policy beats full automation (and naive review), does worse, or shows no difference. "
     "Descriptive: these ranges decide nothing. Where a cell at a realistic capacity is also a deciding result, the deciding verdict in section 3 governs.\n\n"
     "(2) " + " ".join(range_sentence(_v3, "against policy 1", "analyst-aware deferral", "full automation", m, s) + " " +
                       range_sentence(_v3, "against policy 2", "analyst-aware deferral", "naive review", m, s) for m, s in GRID_MEASURES) + "\n\n"
     "(3) The judging capacities of the project outline (team A at full capacity, teams B and C from 0.65 to 1) are fixed inputs to the design. "
     "These ranges show where each policy's advantage holds inside and outside them; they do not test the judging capacities.", {})
v = T43[T43["version"] == L.MEAN5].copy()
for c in [c for c in L.CAP_ORDER if c in v.columns]:
    v[c] = L.symbols(v[c])
V.show(v, 'P3-T4.df1', hide=[], rename={'point boundary': 'where the difference crosses zero (capacity)', 'interval summary': 'summary (can be misread; see the caveat in the technical section)'}, index_names={}, column_names={}, values={'comparison': {'against policy 1': 'against full automation', 'against policy 2': 'against naive review'}}, index={}, cells=[], empty_cells=True)
V.say('boundary.rows', 'The rows of each single version are in the accompanying table file ({n} rows in all).', {}, n=len(T43))
