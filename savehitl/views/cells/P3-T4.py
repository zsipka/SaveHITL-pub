# Section 6.5: table P3-T4.df1, where each team's difference crosses zero, and the descriptive verdict at each capacity as
# a symbol; * marks a cell that is also a deciding result (entry 5). The file keeps the texts.
T43 = boundary_table(BND3, D3, ["vs_policy_1", "vs_policy_2"])
L.save(T43, "P3-T4_capacity_boundaries.csv")
v = T43[T43["version"] == L.MEAN5].copy()
for c in [c for c in L.CAP_ORDER if c in v.columns]:
    v[c] = L.symbols(v[c])
V.show(v, 'P3-T4.df1', hide=[], rename={'point boundary': 'where the difference crosses zero (capacity)', 'interval summary': 'summary (can be misread; see the caveat in the technical section)'}, index_names={}, column_names={}, values={'comparison': {'against policy 1': 'against full automation', 'against policy 2': 'against naive review'}}, index={}, cells=[], empty_cells=True)
V.say('boundary.rows', 'The rows of each single version are in the accompanying table file ({n} rows in all).', {}, n=len(T43))
